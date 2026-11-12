"""Polling the unit, writing to it, and keeping the fault history."""

from __future__ import annotations

import asyncio
import hmac
import logging
import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, ClassVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import ModbusClient, ModbusError, ModbusResponseError
from .const import (
    BOOST,
    CONF_MAC,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONTROL_AUTO,
    CONTROL_MANUAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    DP_IP,
    DP_MAC,
    EVENT_FAULT,
    FAULT_LOG_SIZE,
    MANUFACTURER,
    MODEL_NAMES,
    MODEL_NEST,
    MODEL_NEST_LS,
    NAME,
    NEST_ACCESS_SERVICE,
    NEST_COIL_CLOCK_SET,
    NEST_HR_CLOCK_DATE,
    NEST_HR_CLOCK_TIME,
    NEST_HR_SERVICE_PASSWORD,
    NEST_IR_ACCESS_LEVEL,
    NEST_IR_UNIT_ID,
    NEST_OPERATING_MODES,
    NEST_TARGET_LIMITS,
    OPERATING_MODES,
    SCHEDULE_BASE,
    SCHEDULE_DAYS,
    SCHEDULE_EVENTS,
    SCHEDULE_EVERY,
    SCHEDULE_FIELDS,
    SETPOINT_EVERY,
    SP_FILTER_RUNTIME,
    SP_RUNNING_HOURS,
    SP_SERVICE_PIN,
    STORAGE_VERSION,
)
from .discovery import format_mac, format_serial
from .registers import (
    STORE_COIL,
    STORE_DISCRETE,
    STORE_HOLDING,
    STORE_INPUT,
    STORES,
    Register,
    RegisterMap,
    read_blocks,
)

_LOGGER = logging.getLogger(__name__)

SCHEDULE_REGISTERS = SCHEDULE_DAYS * SCHEDULE_EVENTS * SCHEDULE_FIELDS
SAVE_DELAY = 30
# below this difference the recovery figure is mostly measurement noise
MIN_DELTA_FOR_EFFICIENCY = 3.0
ILLEGAL_FUNCTION = 1
ILLEGAL_ADDRESS = 2
CLOCK_START = 602  # Min, Hour, Day, Date, Month, Year
FAULT_ORDER = ("error", "warning", "alarm")
# what an analog input of the NEST LS is set up to measure, and an air quality sensor of the NEST
LS_ANALOG = {
    1: "extract_humidity",
    2: "extract_co2",
    3: "supply_humidity",
    4: "voc",
    5: "supply_pressure",
    6: "extract_pressure",
}
LS_ANALOG_INPUTS = ("AI1_Configuration", "AI2_Configuration", "AI3_Configuration")
LS_EXCHANGERS = {0: "rotor", 1: "plate"}
NEST_ANALOG = {1: "supply_humidity", 2: "supply_co2", 3: "extract_humidity", 4: "extract_co2"}
NEST_ANALOG_INPUTS = ("Air_Quality_Sensor_1", "Air_Quality_Sensor_2")
# a value written from a building management system shows without an input being set up for it
NEST_READINGS = {
    "AI_SupplyAirHumidity": "supply_humidity",
    "AI_SupplyAirCO2": "supply_co2",
    "AI_ExtractAirHumidity": "extract_humidity",
    "AI_ExtractAirCO2": "extract_co2",
}
NEST_EXCHANGERS = {1: "plate", 2: "rotor"}
NEST_CLOCK = {"Year": "Years", "Month": "Month", "Date": "Day", "Day": "Week_Day", "Hour": "Hours", "Min": "Minutes"}


@dataclass(slots=True)
class NestData:
    """The latest raw registers, by address, and what is worked out from them.

    dp: input registers, sp: holding registers, co: coils, di: discrete inputs.
    """

    dp: dict[int, int] = field(default_factory=dict)
    sp: dict[int, int] = field(default_factory=dict)
    co: dict[int, int] = field(default_factory=dict)
    di: dict[int, int] = field(default_factory=dict)
    schedule: dict[int, int] = field(default_factory=dict)
    faults: list[dict[str, Any]] = field(default_factory=list)
    virtual: dict[str, Any] = field(default_factory=dict)


class NestCoordinator(DataUpdateCoordinator[NestData]):
    """One unit. What only the NEST LS does is here too; NestMcbCoordinator replaces it for the NEST."""

    config_entry: ConfigEntry
    model = MODEL_NEST_LS
    modes: tuple[str, ...] = OPERATING_MODES
    # the modes a user can pick
    selectable: tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    has_schedule = True
    has_auto = True
    target_limits: tuple[float, float] | None = None
    # read on every poll, and only now and then
    fast: tuple[str, ...] = (STORE_INPUT,)
    slow: tuple[str, ...] = (STORE_HOLDING,)
    extra_addresses: ClassVar[dict[str, set[int]]] = {
        STORE_HOLDING: {SP_FILTER_RUNTIME, SP_FILTER_RUNTIME + 1, SP_RUNNING_HOURS, SP_RUNNING_HOURS + 1}
    }
    # addresses of the unit itself, kept out of diagnostics
    private_addresses: ClassVar[dict[str, set[int]]] = {STORE_INPUT: set(range(316, 344))}

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
        self._unreadable: dict[str, set[int]] = {store: set() for store in STORES}
        self._single_write_missing = False
        self._multiple_write_missing = False
        # a poll and a write must not interleave, or the poll puts the old value back on screen
        self._lock = asyncio.Lock()

        # blocks span short gaps, and the gaps hold things that must not be kept, such as the service PIN
        self._wanted = {
            store: registers.addresses(store) | self.extra_addresses.get(store, set()) for store in STORES
        }
        self._blocks = {store: read_blocks(list(addresses)) for store, addresses in self._wanted.items()}
        self._words = [r for r in registers.datapoints.values() if r.fault and r.bits]
        self._flags = [r for r in registers.datapoints.values() if r.fault and not r.bits]

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
        firmware = self.value("FirmwareVerMain")
        bootloader = self.value("FirmwareVerBootloader")
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            connections={(CONNECTION_NETWORK_MAC, mac)} if mac else set(),
            manufacturer=MANUFACTURER,
            model=MODEL_NAMES[self.model],
            name=NAME,
            serial_number=self.data.virtual.get("serial"),
            sw_version=str(firmware) if firmware is not None else None,
            hw_version=f"bootloader {bootloader}" if bootloader is not None else None,
        )

    # reading

    def value(self, name: str) -> float | int | None:
        """The current value of a named register; None too when this kind of unit has no such register."""
        register = self.registers.find(name)
        return None if register is None else register.decode(self.raw(register))

    def raw(self, register: Register, data: NestData | None = None) -> int | None:
        """The register as it was read."""
        return getattr(data or self.data, register.store).get(register.address)

    def _decoded(self, data: NestData, name: str) -> float | int | None:
        """A named register in data that is still being put together."""
        register = self.registers.find(name)
        return None if register is None else register.decode(self.raw(register, data))

    def clock(self) -> dict[str, float | int | None]:
        """The unit's clock where it is not among the settings, under the names of the settings."""
        return {}

    def _reader(self, kind: str):
        return {
            STORE_INPUT: self.client.read_input,
            STORE_HOLDING: self.client.read_holding,
            STORE_COIL: self.client.read_coils,
            STORE_DISCRETE: self.client.read_discrete,
        }[kind]

    async def _read_block(self, kind: str, start: int, count: int, into: dict[int, int]) -> None:
        """Reads a block; an address the unit refuses is found by halving and then left out."""
        unreadable = self._unreadable[kind]
        addresses = [a for a in range(start, start + count) if a not in unreadable]
        if not addresses:
            return
        first, length = addresses[0], addresses[-1] - addresses[0] + 1
        try:
            words = await self._reader(kind)(first, length)
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
        data = NestData(schedule=self.data.schedule)
        for store in self.slow:
            setattr(data, store, getattr(self.data, store))
        try:
            async with self._lock:
                for store in self.fast:
                    for start, count in self._blocks[store]:
                        await self._read_block(store, start, count, getattr(data, store))
                if read_setpoints:
                    for store in self.slow:
                        fresh = dict(getattr(self.data, store))
                        for start, count in self._blocks[store]:
                            await self._read_block(store, start, count, fresh)
                        setattr(data, store, fresh)
                if read_schedule and self.has_schedule:
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
        measured = {LS_ANALOG.get(self._decoded(data, name)) for name in LS_ANALOG_INPUTS}
        virtual["sensors"] = sorted(measured - {None})
        virtual["exchanger"] = LS_EXCHANGERS.get(self._decoded(data, "AirTemp_ERC_TypeInstalled"))
        self._add_efficiency(data, virtual)
        data.virtual = virtual

    def _add_efficiency(self, data: NestData, virtual: dict[str, Any]) -> None:
        """Heat recovery, measured on the exhaust side: a heater after the exchanger does not count towards it."""
        extract, exhaust, outdoor = (self._decoded(data, name) for name in ("T_Extract", "T_Exhaust", "T_Outdoor"))
        if (
            None not in (extract, exhaust, outdoor)
            and abs(extract - outdoor) >= MIN_DELTA_FOR_EFFICIENCY
            and self._decoded(data, "Fan1_Output")
        ):
            share = (extract - exhaust) / (extract - outdoor) * 100
            virtual["recovery_efficiency"] = round(min(max(share, 0), 100), 1)

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
        for flag in self._flags:
            if data.di.get(flag.address):
                active[flag.name] = {
                    "id": f"{flag.fault}:{flag.name}",
                    "name": flag.name,
                    "kind": flag.fault,
                    "word": flag.name,
                    "bit": 0,
                }
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

    async def _write_many(self, address: int, values: list[int]) -> None:
        """Consecutive registers, in one request where the unit takes that."""
        if not self._multiple_write_missing:
            try:
                await self.client.write_registers(address, values)
                return
            except ModbusResponseError as err:
                if err.code != ILLEGAL_FUNCTION:
                    raise
                self._multiple_write_missing = True
        for offset, value in enumerate(values):
            await self.client.write_register(address + offset, value)

    async def _put(self, register: Register, raw: int) -> None:
        if register.store == STORE_COIL:
            await self.client.write_coil(register.address, bool(raw))
        else:
            await self._write(register.address, raw)

    async def async_write(self, name: str, value: float, force: bool = False) -> float | int | None:
        """Writes a setpoint and returns what the unit holds afterwards.

        A value that is already there is not written again: much of the table is kept in EEPROM,
        which wears out. A value the unit changes by itself is written anyway, with force.
        """
        register = self.registers.setpoints[name]
        if register.read_only:
            raise ValueError(f"{name} is read only")
        raw = register.encode(value)
        if not force and self.raw(register) == raw:
            return register.decode(raw)
        async with self._lock:
            await self._put(register, raw)
            value = await self._read_back(register, raw)
        self.async_update_listeners()
        return value

    async def _read_back(self, register: Register, expected: int) -> float | int | None:
        try:
            raw = (await self._reader(register.store)(register.address, 1))[0]
        except ModbusError as err:
            _LOGGER.debug("No read back of %s: %s", register.name, err)
            raw = expected
        if raw != expected:
            _LOGGER.warning("%s: wrote %s, the unit holds %s", register.name, expected, raw)
        getattr(self.data, register.store)[register.address] = raw
        return register.decode(raw)

    async def async_press(self, name: str) -> None:
        """Runs a command register."""
        register = self.registers.setpoints[name]
        async with self._lock:
            await self._put(register, register.command if register.command is not None else 1)
        self._setpoints_due = True
        await self.async_request_refresh()

    async def async_set_operating_mode(self, mode: int) -> None:
        """Puts the unit in a mode; the schedule keeps its hands off until it is set back to auto."""
        if self.value("ControlMode") != CONTROL_MANUAL:
            await self.async_write("ControlMode", CONTROL_MANUAL)
        await self.async_write("OperatingMode", mode)
        await self._read_now("CurrentOperatingMode", "OutsideDamper_State")
        await self.async_request_refresh()

    async def _read_now(self, *names: str) -> None:
        """Readings a command has just changed, without waiting for the next poll."""
        async with self._lock:
            for name in names:
                register = self.registers.find(name)
                if register is None:
                    continue
                try:
                    raw = (await self._reader(register.store)(register.address, 1))[0]
                except ModbusError as err:
                    _LOGGER.debug("No %s after the command: %s", name, err)
                    continue
                getattr(self.data, register.store)[register.address] = raw
        self.async_update_listeners()

    async def async_set_auto(self) -> None:
        """Hands the unit back to its schedule."""
        await self.async_write("ControlMode", CONTROL_AUTO)
        await self._read_now("CurrentOperatingMode", "OutsideDamper_State")
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
        self._need_schedule()
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
        self._need_schedule()
        async with self._lock:
            self.data.schedule = await self._read_schedule()
        return self.data.schedule

    def _need_schedule(self) -> None:
        if not self.has_schedule:
            raise ValueError("This unit's schedule is among its settings")

    async def async_check_service_pin(self, pin: int) -> bool:
        """Whether this is the unit's service PIN: it is compared with the one the unit holds, and kept nowhere."""
        async with self._lock:
            stored = (await self.client.read_holding(SP_SERVICE_PIN, 1))[0]
        return hmac.compare_digest(str(pin).encode(), str(stored).encode())


class NestMcbCoordinator(NestCoordinator):
    """A NEST: the MCB controller, with coils and discrete inputs beside the registers."""

    model = MODEL_NEST
    modes = NEST_OPERATING_MODES
    selectable = (0, 1, 2, 3, 4)
    has_schedule = False
    has_auto = False
    target_limits = NEST_TARGET_LIMITS
    fast = (STORE_INPUT, STORE_DISCRETE)
    slow = (STORE_HOLDING, STORE_COIL)
    extra_addresses: ClassVar[dict[str, set[int]]] = {}
    private_addresses: ClassVar[dict[str, set[int]]] = {STORE_INPUT: set(range(NEST_IR_UNIT_ID, NEST_IR_UNIT_ID + 5))}

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ModbusClient, registers: RegisterMap) -> None:
        super().__init__(hass, entry, client, registers)
        # an accepted PIN is remembered as a keyed digest, for as long as Home Assistant runs
        self._pin_key = secrets.token_bytes(16)
        self._pin_digest: bytes | None = None

    def clock(self) -> dict[str, float | int | None]:
        return {setting: self.value(reading) for setting, reading in NEST_CLOCK.items()}

    def _work_out(self, data: NestData) -> None:
        virtual: dict[str, Any] = {}
        words = [data.dp.get(a) for a in range(NEST_IR_UNIT_ID, NEST_IR_UNIT_ID + 5)]
        if None not in words:
            virtual["serial"] = format_serial(words)
        days, hours = self._decoded(data, "Working_Days"), self._decoded(data, "Working_Hours")
        if days is not None and hours is not None:
            virtual["running_hours"] = days * 24 + hours
        measured = {NEST_ANALOG.get(self._decoded(data, name)) for name in NEST_ANALOG_INPUTS}
        measured |= {sensor for name, sensor in NEST_READINGS.items() if self._decoded(data, name)}
        virtual["sensors"] = sorted(measured - {None})
        virtual["exchanger"] = NEST_EXCHANGERS.get(self._decoded(data, "Heat_Exchanger_Type"))
        self._add_efficiency(data, virtual)
        data.virtual = virtual

    async def async_set_operating_mode(self, mode: int) -> None:
        """Puts the unit in a mode. Boost is a command of its own, and ends by itself."""
        if mode not in self.selectable:
            raise ValueError(f"This unit has no mode {mode}")
        if mode == BOOST:
            await self.async_write("BoostMode_Active", 1, force=True)
        else:
            if self.value("BoostMode_Active") or self.value("CurrentOperatingMode") == BOOST:
                await self.async_write("BoostMode_Active", 0, force=True)
            await self.async_write("OperatingMode", mode)
        await self._read_now("CurrentOperatingMode", "SystemState")
        await self.async_request_refresh()

    async def async_set_auto(self) -> None:
        raise ValueError("This unit follows its schedule by itself")

    async def async_sync_clock(self) -> None:
        """Sets the unit's clock to Home Assistant's local time: the new time, then the command that takes it."""
        now = dt_util.now()
        async with self._lock:
            await self._write_many(NEST_HR_CLOCK_DATE, [now.year % 100, now.month, now.day])
            await self._write_many(NEST_HR_CLOCK_TIME, [now.hour, now.minute, now.second])
            await self.client.write_coil(NEST_COIL_CLOCK_SET, True)
        await self.async_request_refresh()

    async def _access_level(self) -> int:
        return (await self.client.read_input(NEST_IR_ACCESS_LEVEL, 1))[0]

    async def async_check_service_pin(self, pin: int) -> bool:
        """The unit checks the PIN itself: it is entered there, and the access level the unit opens tells.

        While the unit still has service access open from before, it tells nothing; then the PIN
        has to be the one that opened it.
        """
        async with self._lock:
            before = await self._access_level()
            await self._write(NEST_HR_SERVICE_PASSWORD, pin)
            after = await self._access_level()
        digest = hmac.new(self._pin_key, str(pin).encode(), "sha256").digest()
        if before < NEST_ACCESS_SERVICE or self._pin_digest is None:
            accepted = after >= NEST_ACCESS_SERVICE
        else:
            accepted = hmac.compare_digest(digest, self._pin_digest)
        if accepted:
            self._pin_digest = digest
        return accepted


COORDINATORS: dict[str, type[NestCoordinator]] = {MODEL_NEST_LS: NestCoordinator, MODEL_NEST: NestMcbCoordinator}


def coordinator_class(entry: ConfigEntry) -> type[NestCoordinator]:
    """The coordinator for the kind of unit an entry is; entries from before there were two are NEST LS."""
    return COORDINATORS[entry.data.get(CONF_MODEL, MODEL_NEST_LS)]
