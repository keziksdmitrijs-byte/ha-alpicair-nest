"""A small Modbus client on asyncio, for Modbus TCP and for RTU frames over TCP.

Only what the unit needs: holding and input registers, one write of each kind. It has no outside
dependency, so it cannot clash with the pymodbus version Home Assistant's own modbus integration pins.
"""

from __future__ import annotations

import asyncio
import logging
import struct

from .const import DEFAULT_PORT, FRAMING_RTU, FRAMING_TCP

_LOGGER = logging.getLogger(__name__)

READ_HOLDING = 3
READ_INPUT = 4
WRITE_SINGLE = 6
WRITE_MULTIPLE = 16

MAX_READ = 125
MAX_WRITE = 123


class ModbusError(Exception):
    """A request failed."""


class ModbusConnectionError(ModbusError):
    """The unit could not be reached or the connection broke."""


class ModbusResponseError(ModbusError):
    """The unit answered with a Modbus exception."""

    def __init__(self, function: int, code: int) -> None:
        super().__init__(f"Function {function}: Modbus exception {code}")
        self.function = function
        self.code = code


def crc16(data: bytes) -> int:
    """The CRC of an RTU frame."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


class ModbusClient:
    """One connection to one unit; requests run one at a time."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        unit: int = 1,
        framing: str = FRAMING_TCP,
        timeout: float = 3.0,
    ) -> None:
        self.host = host
        self.port = port
        self.unit = unit
        self.framing = framing
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._transaction = 0

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self) -> None:
        """Open the connection if it is not open."""
        if self.connected:
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), self.timeout
            )
        except (OSError, TimeoutError) as err:
            self._reader = self._writer = None
            raise ModbusConnectionError(f"Cannot connect to {self.host}:{self.port}: {err}") from err

    async def close(self) -> None:
        """Close the connection."""
        writer, self._reader, self._writer = self._writer, None, None
        if writer is None:
            return
        try:
            writer.close()
            await asyncio.wait_for(writer.wait_closed(), 1)
        except (OSError, TimeoutError):
            pass

    async def read_holding(self, address: int, count: int) -> list[int]:
        return await self._read(READ_HOLDING, address, count)

    async def read_input(self, address: int, count: int) -> list[int]:
        return await self._read(READ_INPUT, address, count)

    async def write_register(self, address: int, value: int) -> None:
        """Write one register."""
        await self._request(struct.pack(">BHH", WRITE_SINGLE, address, value & 0xFFFF))

    async def write_registers(self, address: int, values: list[int]) -> None:
        """Write consecutive registers in one request."""
        if not 1 <= len(values) <= MAX_WRITE:
            raise ValueError("A write holds 1 to 123 registers")
        words = [v & 0xFFFF for v in values]
        pdu = struct.pack(">BHHB", WRITE_MULTIPLE, address, len(words), len(words) * 2)
        await self._request(pdu + struct.pack(f">{len(words)}H", *words))

    async def _read(self, function: int, address: int, count: int) -> list[int]:
        if not 1 <= count <= MAX_READ:
            raise ValueError("A read holds 1 to 125 registers")
        answer = await self._request(struct.pack(">BHH", function, address, count))
        if len(answer) < 2 or answer[1] != count * 2 or len(answer) < 2 + count * 2:
            raise ModbusError(f"Short answer to read of {count} registers at {address}")
        return list(struct.unpack(f">{count}H", answer[2 : 2 + count * 2]))

    async def _request(self, pdu: bytes) -> bytes:
        """Send one PDU and return the answer's PDU; a broken connection is retried once."""
        async with self._lock:
            for attempt in (1, 2):
                try:
                    await self.connect()
                    return await asyncio.wait_for(self._exchange(pdu), self.timeout)
                except ModbusResponseError:
                    raise
                except (OSError, TimeoutError, asyncio.IncompleteReadError, ModbusConnectionError) as err:
                    await self.close()
                    if attempt == 2:
                        raise ModbusConnectionError(f"{self.host}:{self.port}: {err!r}") from err
            raise ModbusConnectionError("unreachable")

    async def _exchange(self, pdu: bytes) -> bytes:
        assert self._reader and self._writer
        if self.framing == FRAMING_RTU:
            return await self._exchange_rtu(pdu)
        self._transaction = (self._transaction + 1) & 0xFFFF
        self._writer.write(struct.pack(">HHHB", self._transaction, 0, len(pdu) + 1, self.unit) + pdu)
        await self._writer.drain()
        while True:
            transaction, protocol, length, _unit = struct.unpack(">HHHB", await self._reader.readexactly(7))
            if protocol != 0 or not 2 <= length <= 256:
                raise ModbusConnectionError("Not a Modbus TCP answer")
            answer = await self._reader.readexactly(length - 1)
            # an answer to an earlier, timed-out request is dropped
            if transaction == self._transaction:
                return self._check(pdu, answer)

    async def _exchange_rtu(self, pdu: bytes) -> bytes:
        assert self._reader and self._writer
        frame = bytes([self.unit]) + pdu
        self._writer.write(frame + struct.pack("<H", crc16(frame)))
        await self._writer.drain()
        head = await self._reader.readexactly(2)
        function = head[1]
        if function & 0x80:
            rest = await self._reader.readexactly(3)
        elif function in (READ_HOLDING, READ_INPUT):
            size = await self._reader.readexactly(1)
            rest = size + await self._reader.readexactly(size[0] + 2)
        else:
            rest = await self._reader.readexactly(6)
        body = head + rest
        if struct.unpack("<H", body[-2:])[0] != crc16(body[:-2]):
            raise ModbusConnectionError("Wrong CRC")
        return self._check(pdu, body[1:-2])

    @staticmethod
    def _check(pdu: bytes, answer: bytes) -> bytes:
        if not answer:
            raise ModbusConnectionError("Empty answer")
        if answer[0] == pdu[0] | 0x80:
            raise ModbusResponseError(pdu[0], answer[1] if len(answer) > 1 else 0)
        if answer[0] != pdu[0]:
            raise ModbusConnectionError(f"Answer to function {answer[0]} instead of {pdu[0]}")
        return answer
