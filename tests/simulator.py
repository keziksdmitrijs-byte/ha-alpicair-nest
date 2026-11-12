"""A pretend unit: speaks Modbus TCP or RTU over TCP on localhost, seeded from the register table.

    python -m tests.simulator --port 5020
    python -m tests.simulator --port 5020 --model nest

Good enough to run Home Assistant against without a real unit. It answers with the table's defaults
and plausible readings, keeps what is written, and can be told to refuse addresses or functions.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import struct
from pathlib import Path

FOLDER = Path(__file__).parent.parent / "custom_components" / "alpicair_nest"
TABLES = {"nest_ls": FOLDER / "registers.json", "nest": FOLDER / "registers_nest.json"}
TEST_PIN = 1234  # a test value, not any unit's PIN

READINGS = {
    "Fan1_RPM": 1820,
    "Fan2_RPM": 1760,
    "Fan1_Output": 450,
    "Fan2_Output": 430,
    "T_Exhaust": 62,
    "T_Extract": 214,
    "T_Outdoor": 28,
    "T_Supply": 193,
    "AirTemp_SupplyControl_PresentSetpoint": 200,
    "AirTemp_ExtractControl_PresentSetpoint": 210,
    "AirTemp_RawTargetSetpoint": 200,
    "AirTemp_Season_CurrentIsWinter": 1,
    "AirTemp_PhaseControl_WhatPhase": 1,
    "AirTemp_PhaseControl_PassiveDemand": 830,
    "AirTemp_ERC_Rotary_Speed": 760,
    "AirTemp_ERC_Passive_BypassPosition": 0,
    "Pressure_1": 1420,
    "Pressure_2": 1310,
    "Airflow_Supply": 245,
    "Airflow_Exhaust": 235,
    "CurrentOperatingMode": 3,
    "CurrentBaseOperatingMode": 3,
    "Filter_RemainingDays": 121,
    "AI_ExtractAirHumidity": 42,
    "AI_ExtractAirCO2": 640,
    "FirmwareVerMain": 48012,
    "FirmwareVerBootloader": 12,
    "LAN_State": 1,
    "Preheater_TargetTemperature": 40,
}
SETTINGS = {
    "OperatingMode": 3,
    "ControlMode": 1,
    "ModbusTCP_ONOFF": 1,
    "ModbusTCP_Port": 502,
    "Modbus_RTU1_Address": 20,
    "AI1_Configuration": 1,
    "AI2_Configuration": 2,
    "AirTemp_SupplyTarget_Unoccupied": 160,
    "AirTemp_SupplyTarget_Economy": 180,
    "AirTemp_SupplyTarget_Comfort": 200,
    "AirTemp_MinAllowedSetpoint": 120,
    "AirTemp_MaxAllowedSetpoint": 300,
    "Filter_TimerPeriod_Days": 180,
}


# the same for a NEST (MCB controller)
NEST_READINGS = {
    "SystemState": 3,
    "FirmwareVerMain": 127,
    "Configuration_Version": 312,
    "Years": 26,
    "Month": 11,
    "Day": 12,
    "Week_Day": 4,
    "Hours": 8,
    "Minutes": 38,
    "Working_Days": 130,
    "Working_Hours": 5,
    "CurrentOperatingMode": 3,
    "Current_Air_Flow": 70,
    "AirTemp_SupplyControl_PresentSetpoint": 210,
    "T_Supply": 193,
    "T_Extract": 214,
    "T_Exhaust": 62,
    "T_Outdoor": 28,
    "AI_ExtractAirHumidity": 420,
    "AI_ExtractAirCO2": 640,
    "Filter_RemainingDays": 61,
    "FirmwareVerBootloader": 12,
    "Fan1_RPM": 1820,
    "Fan2_RPM": 1760,
    "Fan1_Output": 700,
    "Fan2_Output": 700,
    "Airflow_Supply": 245,
    "Airflow_Exhaust": 235,
    "AirTemp_ERC_Passive_BypassPosition": 0,
    "Ahu_Id_1": 12,
    "Ahu_Id_2": 3456,
    "Ahu_Id_5": 7,
}
NEST_SETTINGS = {"OperatingMode": 3, "Air_Quality_Sensor_1": 0, "Air_Quality_Sensor_2": 3}
NEST_SERVICE_PASSWORD = 199
NEST_ACCESS_LEVEL = 106


class Simulator:
    """One pretend unit."""

    def __init__(self, unit: int = 1, framing: str = "tcp", host: str = "127.0.0.1", model: str = "nest_ls") -> None:
        self.unit = unit
        self.framing = framing
        self.host = host
        self.model = model
        self.port = 0
        self.holding: dict[int, int] = {}
        self.input: dict[int, int] = {}
        self.coils: dict[int, int] = {}
        self.discrete: dict[int, int] = {}
        self.writes: list[tuple[int, int]] = []
        self.coil_writes: list[tuple[int, int]] = []
        self.refused_input: set[int] = set()
        self.no_single_write = False
        self.no_multiple_write = False
        self._server: asyncio.Server | None = None
        self._tasks: set[asyncio.Task] = set()
        table = json.loads(TABLES[model].read_text(encoding="utf-8"))
        self.addresses = {r["n"]: r["a"] for r in table["sp"]}
        self.addresses_dp = {r["n"]: r["a"] for r in table["dp"]}
        for register in table["sp"]:
            store = self.coils if register.get("tb") == "c" else self.holding
            store[register["a"]] = round(register["def"] * 10 ** register["d"]) & 0xFFFF
        if model == "nest":
            for name, value in NEST_SETTINGS.items():
                self.holding[self.addresses[name]] = value
            for name, value in NEST_READINGS.items():
                self.input[self.addresses_dp[name]] = value
            return
        self.holding[475] = TEST_PIN
        self.holding[563] = 1
        self.holding[566] = 502
        self.holding[576] = 20
        self.holding[577] = 3
        self.holding[578] = 0
        self.holding.update({463: 3400, 464: 1, 465: 3120, 466: 1})
        for name, value in SETTINGS.items():
            if name in self.addresses:
                self.holding[self.addresses[name]] = value
        for name, value in READINGS.items():
            self.input[self.addresses_dp[name]] = value
        self.input.update(dict(zip(range(316, 322), (0x02, 0xAC, 0x10, 0x20, 0x30, 0x40), strict=True)))
        self.input.update(dict(zip(range(328, 332), (127, 0, 0, 1), strict=True)))
        # Monday: one working-day pattern
        for day in range(5):
            base = 700 + day * 40
            self.holding.update(
                {base: 6, base + 1: 30, base + 2: 4, base + 3: 20, base + 4: 22, base + 5: 0, base + 6: 3, base + 7: 18}
            )

    async def start(self, port: int = 0) -> None:
        self._server = await asyncio.start_server(self._serve, self.host, port)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server:
            self._server.close()
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._server:
            await self._server.wait_closed()

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        self._tasks.add(task)
        try:
            while True:
                if self.framing == "tcp":
                    head = await reader.readexactly(7)
                    transaction, _, length, unit = struct.unpack(">HHHB", head)
                    answer = self._answer(unit, await reader.readexactly(length - 1))
                    if answer is None:
                        continue
                    writer.write(struct.pack(">HHHB", transaction, 0, len(answer) + 1, unit) + answer)
                else:
                    frame = await self._read_rtu(reader)
                    answer = self._answer(frame[0], frame[1:-2])
                    if answer is None:
                        continue
                    body = bytes([frame[0]]) + answer
                    writer.write(body + struct.pack("<H", _crc(body)))
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError, asyncio.CancelledError):
            pass
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            self._tasks.discard(task)

    @staticmethod
    async def _read_rtu(reader: asyncio.StreamReader) -> bytes:
        head = await reader.readexactly(2)
        if head[1] == 16:
            rest = await reader.readexactly(5)
            return head + rest + await reader.readexactly(rest[4] + 2)
        return head + await reader.readexactly(6)

    def _answer(self, unit: int, pdu: bytes) -> bytes | None:
        if unit != self.unit:
            return None
        function = pdu[0]
        if function in (1, 2):
            address, count = struct.unpack(">HH", pdu[1:5])
            table = self.coils if function == 1 else self.discrete
            packed = bytearray((count + 7) // 8)
            for index in range(count):
                if table.get(address + index):
                    packed[index // 8] |= 1 << (index % 8)
            return bytes([function, len(packed)]) + bytes(packed)
        if function == 5:
            address, value = struct.unpack(">HH", pdu[1:5])
            self._store_coil(address, 1 if value else 0)
            return pdu[:5]
        if function in (3, 4):
            address, count = struct.unpack(">HH", pdu[1:5])
            table = self.holding if function == 3 else self.input
            addresses = range(address, address + count)
            if function == 4 and self.refused_input.intersection(addresses):
                return bytes([function | 0x80, 2])
            words = [table.get(a, 0) for a in addresses]
            return bytes([function, count * 2]) + struct.pack(f">{count}H", *words)
        if function == 6:
            if self.no_single_write:
                return bytes([function | 0x80, 1])
            address, value = struct.unpack(">HH", pdu[1:5])
            self._store(address, value)
            return pdu[:5]
        if function == 16:
            if self.no_multiple_write:
                return bytes([function | 0x80, 1])
            address, count = struct.unpack(">HH", pdu[1:5])
            words = struct.unpack(f">{count}H", pdu[6 : 6 + count * 2])
            for offset, value in enumerate(words):
                self._store(address + offset, value)
            return pdu[:5]
        return bytes([function | 0x80, 1])

    def _store_coil(self, address: int, value: int) -> None:
        """A NEST's commands."""
        self.coil_writes.append((address, value))
        self.coils[address] = value
        mode, state = self.addresses_dp["CurrentOperatingMode"], self.addresses_dp["SystemState"]
        if address == self.addresses["BoostMode_Active"]:
            chosen = self.holding[self.addresses["OperatingMode"]]
            self.input[mode], self.input[state] = (4, 7) if value else (chosen, chosen)
        elif address == self.addresses["Filter_Reset"] and value:
            period = self.holding[self.addresses["Filter_TimerPeriod_Days"]]
            self.input[self.addresses_dp["Filter_RemainingDays"]] = period
            self.coils[address] = 0
        elif address == 2 and value:
            # the clock takes the date and time that were written for it
            self.input.update({4: self.holding.get(100, 0), 5: self.holding.get(101, 0), 6: self.holding.get(102, 0)})
            self.input.update({8: self.holding.get(104, 0), 9: self.holding.get(105, 0), 10: self.holding.get(106, 0)})
            self.coils[address] = 0

    def _store(self, address: int, value: int) -> None:
        self.writes.append((address, value))
        self.holding[address] = value
        if self.model == "nest":
            if address == NEST_SERVICE_PASSWORD:
                # the unit takes the password and shows what it opened; a wrong one changes nothing
                self.holding[address] = 0
                if value == TEST_PIN:
                    self.input[NEST_ACCESS_LEVEL] = 2
            elif address == self.addresses["OperatingMode"] and not self.coils.get(self.addresses["BoostMode_Active"]):
                self.input[self.addresses_dp["CurrentOperatingMode"]] = value
                self.input[self.addresses_dp["SystemState"]] = value
            return
        if address == self.addresses.get("OperatingMode"):
            self.input[self.addresses_dp["CurrentOperatingMode"]] = value
        if address == self.addresses.get("Filter_Reset"):
            self.input[self.addresses_dp["Filter_RemainingDays"]] = self.holding.get(
                self.addresses["Filter_TimerPeriod_Days"], 0
            )
            self.holding[address] = 0


def _crc(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


async def _main(port: int, faults: bool, model: str) -> None:
    simulator = Simulator(host="0.0.0.0", model=model)
    if faults and model == "nest":
        simulator.discrete.update({14: 1, 38: 1, 188: 1, 189: 1})
    elif faults:
        simulator.input[simulator.addresses_dp["ErrorStatus1"]] = 1 << 0
        simulator.input[simulator.addresses_dp["WarningStatus2"]] = 1 << 13
        simulator.input[simulator.addresses_dp["AnyErrorActive"]] = 1
        simulator.input[simulator.addresses_dp["AnyWarningActive"]] = 1
    await simulator.start(port)
    print(f"Simulated {model} unit on port {simulator.port}, unit id {simulator.unit}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5020)
    parser.add_argument("--faults", action="store_true", help="start with a fault and a warning active")
    parser.add_argument("--model", choices=sorted(TABLES), default="nest_ls", help="the kind of unit to pretend to be")
    args = parser.parse_args()
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_main(args.port, args.faults, args.model))
