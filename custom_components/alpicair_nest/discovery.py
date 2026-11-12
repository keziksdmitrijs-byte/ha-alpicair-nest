"""Finding units on the local network: who has the Modbus port open and answers like one."""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components import network
from homeassistant.core import HomeAssistant

from .client import ModbusClient, ModbusError
from .const import (
    DEFAULT_PORT,
    DP_FIRMWARE,
    DP_IP,
    DP_MAC,
    FRAMING_RTU,
    FRAMING_TCP,
    MODEL_NEST,
    MODEL_NEST_LS,
    NEST_HR_MODE,
    NEST_HR_SERIAL_PORT,
    NEST_IR_STATE,
    NEST_IR_UNIT_ID,
    NEST_LAST_STATE,
    SP_MODBUS_ENABLED,
    SP_MODBUS_PORT,
    SP_RTU_ADDRESS,
    SP_RTU_BAUD,
    SP_RTU_PARITY,
    UNIT_IDS,
)

_LOGGER = logging.getLogger(__name__)

SCAN_PARALLEL = 48
CONNECT_TIMEOUT = 0.7
PROBE_TIMEOUT = 1.5
# a /16 would take minutes and is rarely all in use: wider networks are searched around our own address
MAX_HOSTS_PREFIX = 22


@dataclass(frozen=True, slots=True)
class FoundUnit:
    """A unit that answered."""

    host: str
    port: int
    unit: int
    framing: str
    mac: str | None
    firmware: int | None
    matched: bool
    model: str = MODEL_NEST_LS
    serial: str | None = None

    @property
    def unique_id(self) -> str:
        return self.mac or self.serial or f"{self.host}:{self.port}"


def format_mac(words: list[int]) -> str | None:
    """Six registers, one byte each, as a MAC address."""
    if len(words) != 6 or not any(words) or any(w > 255 for w in words):
        return None
    return ":".join(f"{w:02x}" for w in words)


def format_serial(words: list[int]) -> str | None:
    """The five registers of a NEST's unit ID as one number; None while none is set."""
    if len(words) != 5 or not any(words) or any(w > 9999 for w in words):
        return None
    return "-".join(f"{w:04d}" for w in words)


async def _read_signature_nest(client: ModbusClient, host: str, port: int) -> FoundUnit | None:
    """A NEST by what its MCB controller keeps where: state and versions, mode, serial port settings."""
    state, firmware, _configuration = await client.read_input(NEST_IR_STATE, 3)
    mode = (await client.read_holding(NEST_HR_MODE, 1))[0]
    address, baud, frame = await client.read_holding(NEST_HR_SERIAL_PORT, 3)
    port_plausible = 1 <= address <= 247 and baud <= 7 and frame <= 5
    matched = state <= NEST_LAST_STATE and firmware > 0 and mode <= 3 and port_plausible
    serial = None
    try:
        serial = format_serial(await client.read_input(NEST_IR_UNIT_ID, 5))
    except ModbusError as err:
        _LOGGER.debug("%s: no unit ID: %s", host, err)
    return FoundUnit(host, port, client.unit, client.framing, None, firmware, matched, MODEL_NEST, serial)


async def _read_signature(client: ModbusClient, host: str, port: int) -> FoundUnit | None:
    """Reads the registers only this kind of unit has; nothing is written."""
    settings = await client.read_holding(SP_MODBUS_ENABLED, SP_MODBUS_PORT - SP_MODBUS_ENABLED + 1)
    serial = await client.read_holding(SP_RTU_ADDRESS, SP_RTU_PARITY - SP_RTU_ADDRESS + 1)
    enabled, tcp_port = settings[0], settings[SP_MODBUS_PORT - SP_MODBUS_ENABLED]
    plausible = (
        1 <= serial[0] <= 247
        and serial[SP_RTU_BAUD - SP_RTU_ADDRESS] <= 7
        and serial[SP_RTU_PARITY - SP_RTU_ADDRESS] <= 2
    )
    mac = own_ip = firmware = None
    try:
        mac = format_mac(await client.read_input(DP_MAC, 6))
        own_ip = await client.read_input(DP_IP, 4)
        firmware = (await client.read_input(DP_FIRMWARE, 1))[0]
    except ModbusError as err:
        _LOGGER.debug("%s: no data points: %s", host, err)
    try:
        address = ipaddress.ip_address(host)
        same_ip = own_ip is not None and address.version == 4 and own_ip == list(address.packed)
    except ValueError:
        same_ip = False
    matched = plausible and ((enabled == 1 and tcp_port == port) or same_ip)
    return FoundUnit(host, port, client.unit, client.framing, mac, firmware, matched)


SIGNATURES = {MODEL_NEST_LS: _read_signature, MODEL_NEST: _read_signature_nest}


async def async_probe(
    host: str, port: int = DEFAULT_PORT, unit: int | None = None, model: str = MODEL_NEST_LS
) -> FoundUnit | None:
    """Tries the unit ids and framings; the best answer, None when nothing answers.

    Raises nothing: a host that does not speak Modbus simply gives None.
    """
    read_signature = SIGNATURES[model]
    best: FoundUnit | None = None
    units = (unit,) if unit is not None else UNIT_IDS
    for framing in (FRAMING_TCP, FRAMING_RTU):
        for candidate in units:
            client = ModbusClient(host, port, candidate, framing, timeout=PROBE_TIMEOUT)
            try:
                found = await read_signature(client, host, port)
            except ModbusError as err:
                _LOGGER.debug("%s unit %s %s: %s", host, candidate, framing, err)
                found = None
            finally:
                await client.close()
            if found and found.matched:
                return found
            best = best or found
    return best


async def _port_open(host: str, port: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), CONNECT_TIMEOUT)
    except (OSError, TimeoutError):
        return False
    writer.close()
    with contextlib.suppress(OSError, TimeoutError):
        await asyncio.wait_for(writer.wait_closed(), 0.5)
    return True


async def async_local_hosts(hass: HomeAssistant) -> list[str]:
    """The addresses of the networks Home Assistant is connected to."""
    hosts: dict[str, None] = {}
    for adapter in await network.async_get_adapters(hass):
        if not adapter["enabled"]:
            continue
        for info in adapter["ipv4"]:
            own = ipaddress.ip_address(info["address"])
            if own.is_loopback:
                continue
            prefix = max(info["network_prefix"], MAX_HOSTS_PREFIX)
            net = ipaddress.ip_network(f"{own}/{prefix}", strict=False)
            for address in net.hosts():
                if address != own:
                    hosts[str(address)] = None
    return list(hosts)


async def async_discover(
    hass: HomeAssistant,
    port: int = DEFAULT_PORT,
    progress: Callable[[float], None] | None = None,
    model: str = MODEL_NEST_LS,
) -> list[FoundUnit]:
    """All units of one kind on the local networks, nearest address first."""
    hosts = await async_local_hosts(hass)
    gate = asyncio.Semaphore(SCAN_PARALLEL)
    done = 0
    found: list[FoundUnit] = []

    async def visit(host: str) -> None:
        nonlocal done
        async with gate:
            if await _port_open(host, port):
                unit = await async_probe(host, port, model=model)
                if unit and unit.matched:
                    found.append(unit)
        done += 1
        if progress:
            progress(done / len(hosts))

    await asyncio.gather(*(visit(host) for host in hosts))
    return sorted(found, key=lambda u: tuple(int(p) for p in u.host.split(".")))
