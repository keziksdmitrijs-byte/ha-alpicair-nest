"""Polling the unit, writing to it, and keeping the fault history."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import ModbusClient, ModbusError, ModbusResponseError
from .const import (
    CONF_MAC,
    CONF_SCAN_INTERVAL,
    CONTROL_AUTO,
    CONTROL_MANUAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    DP_BOOTLOADER,
    DP_FIRMWARE,
    DP_IP,
    DP_MAC,
    EVENT_FAULT,
    FAULT_LOG_SIZE,
    MANUFACTURER,
    MODEL,
    NAME,
    SCHEDULE_BASE,
    SCHEDULE_DAYS,
    SCHEDULE_EVENTS,
    SCHEDULE_EVERY,
    SCHEDULE_FIELDS,
    SETPOINT_EVERY,
    SP_FILTER_RUNTIME,
    SP_RUNNING_HOURS,
    STORAGE_VERSION,
)
from .discovery import format_mac
from .registers import Register, RegisterMap, read_blocks

_LOGGER = logging.getLogger(__name__)

SCHEDULE_REGISTERS = SCHEDULE_DAYS * SCHEDULE_EVENTS * SCHEDULE_FIELDS
SAVE_DELAY = 30
# below this difference the recovery figure is mostly measurement noise
MIN_DELTA_FOR_EFFICIENCY = 3.0
ILLEGAL_FUNCTION = 1
ILLEGAL_ADDRESS = 2
CLOCK_START = 602  # Min, Hour, Day, Date, Month, Year
FAULT_ORDER = ("error", "warning", "alarm")


@dataclass(slots=True)
class NestData:
    """The latest raw registers, by address, and what is worked out from them."""

    dp: dict[int, int] = field(default_factory=dict)
    sp: dict[int, int] = field(default_factory=dict)
    schedule: dict[int, int] = field(default_factory=dict)
    faults: list[dict[str, Any]] = field(default_factory=list)
    virtual: dict[str, Any] = field(default_factory=dict)


class NestCoordinator(DataUpdateCoordinator[NestData]):
    """One unit."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: ModbusClient,
        registers: RegisterMap,
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.registers = registers
        self.data = NestData()
        self.fault_log: list[dict[str, Any]] = []
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._known_faults: set[str] = set()
        self._loaded = False
        self._cycle = 0
        self._schedule_due = True
        self._setpoints_due = True
        self._unreadable: dict[str, set[int]] = {"dp": set(), "sp": set()}
        self._single_write_missing = False
        # a poll and a write must not interleave, or the poll puts the old value back on screen
        self._lock = asyncio.Lock()

        # blocks span short gaps, and the gaps hold things that must not be kept, such as the service PIN
        self._wanted = {
            "dp": {r.address for r in registers.datapoints.values()},
            "sp": {r.address for r in registers.setpoints.values()}
            | {SP_FILTER_RUNTIME, SP_FILTER_RUNTIME + 1, SP_RUNNING_HOURS, SP_RUNNING_HOURS + 1},
        }
        self._dp_blocks = read_blocks(list(self._wanted["dp"]))
        self._sp_blocks = read_blocks(list(self._wanted["sp"]))
        self._words = [r for r in registers.datapoints.values() if r.fault]

    @property
    def unique_id(self) -> str:
        return self.config_entry.unique_id or self.config_entry.entry_id

    @property
    def unreadable(self) -> dict[str, list[int]]:
        """Addresses this unit refused, for diagnostics."""
        return {kind: sorted(addresses) for kind, addresses in self._unreadable.items()}

    @property
    def device_info(self) -> DeviceInfo:
        mac = self.config_entry.data.get(CONF_MAC) or self.data.virtual.get("mac")
        firmware = self.data.dp.get(DP_FIRMWARE)
        bootloader = self.data.dp.get(DP_BOOTLOADER)
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            connections={(CONNECTION_NETWORK_MAC, mac)} if mac else set(),
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=NAME,
            sw_version=str(firmware) if firmware is not None else None,
            hw_version=f"bootloader {bootloader}" if bootloader is not None else None,
        )

    # reading

    def value(self, name: str) -> float | int | None:
        """The current value of a named register."""
        register = self.registers.get(name)
        return register.decode(self._raw(register))

    def _raw(self, register: Register) -> int | None:
        table = self.data.sp if register.kind == "sp" else self.data.dp
        return table.get(register.address)

    async def _read_block(self, kind: str, start: int, count: int, into: dict[int, int]) -> None:
        """Reads a block; an address the unit refuses is found by halving and then left out."""
        unreadable = self._unreadable[kind]
        addresses = [a for a in range(start, start + count) if a not in unreadable]
        if not addresses:
            return
        first, length = addresses[0], addresses[-1] - addresses[0] + 1
        read = self.client.read_input if kind == "dp" else self.client.read_holding
        try:
            words = await read(first, length)
        except ModbusResponseError as err:
            if err.code != ILLEGAL_ADDRESS:
                raise
            if length == 1:
                _LOGGER.debug("%s register %s is not available on this unit", kind, first)
                unreadable.add(first)
                return
            half = length // 2
            await self._read_block(kind, first, half, into)
            await self._read_block(kind, first + half, length - half, into)
            return
        wanted = self._wanted[kind]
        into.update((a, w) for a, w in zip(range(first, first + length), words, strict=True) if a in wanted)

    async def _async_update_data(self) -> NestData:
        if not self._loaded:
            await self._async_load_store()
        read_setpoints = self._setpoints_due or self._cycle % SETPOINT_EVERY == 0
        read_schedule = self._schedule_due or self._cycle % SCHEDULE_EVERY == 0
        data = NestData(sp=self.data.sp, schedule=self.data.schedule)
        try:
            async with self._lock:
                for start, count in self._dp_blocks:
                    await self._read_block("dp", start, count, data.dp)
                if read_setpoints:
                    data.sp = dict(self.data.sp)
                    for start, count in self._sp_blocks:
                        await self._read_block("sp", start, count, data.sp)
                if read_schedule:
                    data.schedule = await self._read_schedule()
        except ModbusError as err:
            await self.client.close()
            raise UpdateFailed(f"{self.client.host}: {err}") from err
        self._setpoints_due = self._schedule_due = False
        self._cycle += 1
        self._work_out(data)
        self._track_faults(data)
        return data

    async def _read_schedule(self) -> dict[int, int]:
        table: dict[int, int] = {}
        for offset in range(0, SCHEDULE_REGISTERS, 100):
            start = SCHEDULE_BASE + offset
            count = min(100, SCHEDULE_REGISTERS - offset)
            table.update(zip(range(start, start + count), await self.client.read_holding(start, count), strict=True))
        return table

    def _work_out(self, data: NestData) -> None:
        """Values that take more than one register."""
        raw = data.dp.get
        virtual: dict[str, Any] = {}
        mac_words = [raw(a) for a in range(DP_MAC, DP_MAC + 6)]
        if None not in mac_words:
            virtual["mac"] = format_mac(mac_words)
        ip_words = [raw(a) for a in range(DP_IP, DP_IP + 4)]
        if None not in ip_words:
            virtual["ip"] = ".".join(str(w) for w in ip_words)
        hours = [data.sp.get(SP_RUNNING_HOURS), data.sp.get(SP_RUNNING_HOURS + 1)]
        if None not in hours:
            virtual["running_hours"] = hours[0] + hours[1] * 10000
        minutes = [data.sp.get(SP_FILTER_RUNTIME), data.sp.get(SP_FILTER_RUNTIME + 1)]
        if None not in minutes:
            virtual["filter_runtime_hours"] = round((minutes[0] + (minutes[1] << 16)) / 60, 1)

        def reading(name: str) -> float | None:
            register = self.registers.datapoints[name]
            return register.decode(data.dp.get(register.address))

        # measured on the exhaust side: a heater after the exchanger does not count towards it
        extract, exhaust, outdoor = reading("T_Extract"), reading("T_Exhaust"), reading("T_Outdoor")
        if (
            None not in (extract, exhaust, outdoor)
            and abs(extract - outdoor) >= MIN_DELTA_FOR_EFFICIENCY
            and reading("Fan1_Output")
        ):
            share = (extract - exhaust) / (extract - outdoor) * 100
            virtual["recovery_efficiency"] = round(min(max(share, 0), 100), 1)
        data.virtual = virtual

    # faults

    async def _async_load_store(self) -> None:
        stored = await self._store.async_load()
        if stored:
            self.fault_log = stored.get("log", [])
            self._known_faults = set(stored.get("active", []))
        self._loaded = True

    def _active_faults(self, data: NestData) -> list[dict[str, Any]]:
        """The bits that are set. A unit repeats its errors and warnings in the alarm words: one line each."""
        active: dict[str, dict[str, Any]] = {}
        for word in sorted(self._words, key=lambda w: FAULT_ORDER.index(w.fault)):
            raw = data.dp.get(word.address)
            if not raw:
                continue
            for bit in range(16):
                if raw & (1 << bit):
                    name = word.bits.get(str(bit))
                    active.setdefault(
                        name or f"{word.name}.{bit}",
                        {
                            "id": f"{word.fault}:{name or f'{word.name}.{bit}'}",
                            "name": name,
                            "kind": word.fault,
                            "word": word.name,
                            "bit": bit,
                        },
                    )
        return list(active.values())

    def _track_faults(self, data: NestData) -> None:
        data.faults = self._active_faults(data)
        active = {fault["id"]: fault for fault in data.faults}
        appeared = active.keys() - self._known_faults
        cleared = self._known_faults - active.keys()
        if not appeared and not cleared:
            return
        now = dt_util.utcnow().isoformat()
        for key in appeared:
            fault = active[key]
            self.fault_log.append({"at": now, "id": key, "kind": fault["kind"], "name": fault["name"], "on": True})
            self.hass.bus.async_fire(EVENT_FAULT, {"entry_id": self.config_entry.entry_id, **fault})
        for key in cleared:
            kind, _, name = key.partition(":")
            self.fault_log.append({"at": now, "id": key, "kind": kind, "name": name, "on": False})
        del self.fault_log[:-FAULT_LOG_SIZE]
        self._known_faults = set(active)
        self._save_store()

    def _save_store(self) -> None:
        self._store.async_delay_save(lambda: {"log": self.fault_log, "active": sorted(self._known_faults)}, SAVE_DELAY)

    async def async_clear_log(self) -> None:
        self.fault_log = []
        self._save_store()

    # writing

    async def _write(self, address: int, raw: int) -> None:
        try:
            if self._single_write_missing:
                await self.client.write_registers(address, [raw])
            else:
                await self.client.write_register(address, raw)
        except ModbusResponseError as err:
            if err.code != ILLEGAL_FUNCTION or self._single_write_missing:
                raise
            self._single_write_missing = True
            await self.client.write_registers(address, [raw])

    async def async_write(self, name: str, value: float) -> float | int | None:
        """Writes a setpoint and returns what the unit holds afterwards.

        A value that is already there is not written again: much of the table is kept in EEPROM,
        which wears out.
        """
        register = self.registers.setpoints[name]
        if register.read_only:
            raise ValueError(f"{name} is read only")
        raw = register.encode(value)
        if self.data.sp.get(register.address) == raw:
            return register.decode(raw)
        async with self._lock:
            await self._write(register.address, raw)
            value = await self._read_back(register, raw)
        self.async_update_listeners()
        return value

    async def _read_back(self, register: Register, expected: int) -> float | int | None:
        try:
            raw = (await self.client.read_holding(register.address, 1))[0]
        except ModbusError as err:
            _LOGGER.debug("No read back of %s: %s", register.name, err)
            raw = expected
        if raw != expected:
            _LOGGER.warning("%s: wrote %s, the unit holds %s", register.name, expected, raw)
        self.data.sp[register.address] = raw
        return register.decode(raw)

    async def async_press(self, name: str) -> None:
        """Runs a command register."""
        register = self.registers.setpoints[name]
        async with self._lock:
            await self._write(register.address, register.command if register.command is not None else 1)
        self._setpoints_due = True
        await self.async_request_refresh()

    async def async_set_operating_mode(self, mode: int) -> None:
        """Puts the unit in a mode; the schedule keeps its hands off until it is set back to auto."""
        if self.value("ControlMode") != CONTROL_MANUAL:
            await self.async_write("ControlMode", CONTROL_MANUAL)
        await self.async_write("OperatingMode", mode)
        await self.async_request_refresh()

    async def async_set_auto(self) -> None:
        """Hands the unit back to its schedule."""
        await self.async_write("ControlMode", CONTROL_AUTO)
        await self.async_request_refresh()

    async def async_sync_clock(self) -> None:
        """Sets the unit's clock to Home Assistant's local time, in one write so it cannot tear."""
        now = dt_util.now()
        words = [now.minute, now.hour, now.isoweekday(), now.day, now.month, now.year % 100]
        async with self._lock:
            await self.client.write_registers(CLOCK_START, words)
        self.data.sp.update(zip(range(CLOCK_START, CLOCK_START + 6), words, strict=True))
        self.async_update_listeners()

    async def async_write_schedule(self, changes: dict[int, int]) -> None:
        """Writes schedule registers, runs of neighbours together."""
        table = self.data.schedule
        for address in changes:
            if not SCHEDULE_BASE <= address < SCHEDULE_BASE + SCHEDULE_REGISTERS:
                raise ValueError(f"{address} is not a schedule register")
        pending = sorted(a for a, v in changes.items() if table.get(a) != v)
        async with self._lock:
            while pending:
                start = pending.pop(0)
                run = [changes[start]]
                while pending and pending[0] == start + len(run) and len(run) < 100:
                    run.append(changes[pending.pop(0)])
                await self.client.write_registers(start, run)
                table.update(zip(range(start, start + len(run)), run, strict=True))

    async def async_read_schedule_now(self) -> dict[int, int]:
        """Reads the schedule at once."""
        async with self._lock:
            self.data.schedule = await self._read_schedule()
        return self.data.schedule

    async def async_read_register(self, address: int) -> int:
        """One holding register that is not part of the polled table."""
        async with self._lock:
            return (await self.client.read_holding(address, 1))[0]
