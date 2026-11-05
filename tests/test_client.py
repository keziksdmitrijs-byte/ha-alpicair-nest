"""The Modbus client, against the simulator."""

from __future__ import annotations

import pytest

from custom_components.alpicair_nest.client import (
    ModbusClient,
    ModbusConnectionError,
    ModbusResponseError,
    crc16,
)
from custom_components.alpicair_nest.discovery import async_probe, format_mac

from .simulator import Simulator


def test_crc() -> None:
    # the example from the Modbus serial line specification
    assert crc16(bytes.fromhex("0207")) == 0x1241


def test_format_mac() -> None:
    assert format_mac([2, 172, 16, 32, 48, 64]) == "02:ac:10:20:30:40"
    assert format_mac([0, 0, 0, 0, 0, 0]) is None
    assert format_mac([300, 0, 0, 0, 0, 1]) is None


@pytest.mark.parametrize("framing", ["tcp", "rtu"])
async def test_read_and_write(socket_enabled, framing: str) -> None:
    unit = Simulator(framing=framing)
    await unit.start()
    client = ModbusClient("127.0.0.1", unit.port, 1, framing)
    try:
        assert await client.read_holding(475, 1) == [1234]
        assert (await client.read_input(0, 2)) == [1820, 1760]
        await client.write_register(391, 170)
        await client.write_registers(392, [181, 201])
        assert await client.read_holding(391, 3) == [170, 181, 201]
    finally:
        await client.close()
        await unit.stop()


async def test_exception_is_reported(socket_enabled) -> None:
    unit = Simulator()
    unit.refused_input = {5}
    await unit.start()
    client = ModbusClient("127.0.0.1", unit.port)
    try:
        with pytest.raises(ModbusResponseError) as err:
            await client.read_input(0, 10)
        assert err.value.code == 2
    finally:
        await client.close()
        await unit.stop()


async def test_nothing_there(socket_enabled) -> None:
    unit = Simulator()
    await unit.start()
    port = unit.port
    await unit.stop()
    client = ModbusClient("127.0.0.1", port, timeout=0.5)
    with pytest.raises(ModbusConnectionError):
        await client.read_input(0, 1)


async def test_reconnects_after_a_broken_connection(socket_enabled) -> None:
    unit = Simulator()
    await unit.start()
    client = ModbusClient("127.0.0.1", unit.port)
    try:
        await client.read_input(0, 1)
        client._writer.close()
        assert await client.read_input(0, 1) == [1820]
    finally:
        await client.close()
        await unit.stop()


@pytest.mark.parametrize(("unit_id", "framing"), [(1, "tcp"), (20, "tcp"), (20, "rtu")])
async def test_probe_finds_address_and_framing(socket_enabled, unit_id: int, framing: str) -> None:
    unit = Simulator(unit=unit_id, framing=framing)
    await unit.start()
    # the simulator's port setting says 502, its IP registers say 127.0.0.1: the IP is what matches here
    found = await async_probe("127.0.0.1", unit.port)
    await unit.stop()
    assert found is not None
    assert found.matched
    assert (found.unit, found.framing) == (unit_id, framing)
    assert found.mac == "02:ac:10:20:30:40"
    assert found.firmware == 48012


async def test_probe_tells_another_device_apart(socket_enabled) -> None:
    unit = Simulator()
    unit.holding[576] = 0  # no plausible serial address
    await unit.start()
    found = await async_probe("127.0.0.1", unit.port)
    await unit.stop()
    assert found is not None
    assert not found.matched
