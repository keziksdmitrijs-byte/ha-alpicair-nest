"""The units' register maps.

registers.json is the NEST LS (scripts/build_registers.py), registers_nest.json the NEST
(scripts/build_registers_nest.py); both are generated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .const import MODEL_NEST_LS, REGISTER_FILES

KIND_DATAPOINT = "dp"
KIND_SETPOINT = "sp"

# where a register lives: the Modbus table, named after the place its raw value is kept in
STORE_INPUT = "dp"
STORE_HOLDING = "sp"
STORE_COIL = "co"
STORE_DISCRETE = "di"
STORES = (STORE_INPUT, STORE_HOLDING, STORE_COIL, STORE_DISCRETE)
_TABLES = {"i": STORE_INPUT, "h": STORE_HOLDING, "c": STORE_COIL, "d": STORE_DISCRETE}


@dataclass(frozen=True, slots=True)
class Register:
    """One named register."""

    kind: str
    name: str
    address: int
    signed: bool
    decimals: int
    unit: str
    section: str
    labels: dict[str, str]
    options: dict[str, dict[str, str]] = field(default_factory=dict)
    # setpoints
    entity: str = ""
    minimum: float = 0
    maximum: float = 65535
    default: float = 0
    level: str = "service"
    memory: str = "ram"
    read_only: bool = False
    danger: bool = False
    command: int | None = None
    hint: str = ""
    # data points
    hidden: bool = False
    flag: bool = False
    fault: str | None = None
    bits: dict[str, str] = field(default_factory=dict)
    store: str = STORE_HOLDING

    @property
    def single_bit(self) -> bool:
        """A coil or a discrete input."""
        return self.store in (STORE_COIL, STORE_DISCRETE)

    def label(self, language: str) -> str:
        return self.labels.get(language) or self.labels["en"]

    def option_labels(self, language: str) -> dict[int, str]:
        table = self.options.get(language) or self.options.get("en") or {}
        return {int(k): v for k, v in table.items()}

    def decode(self, raw: int | None) -> float | int | None:
        """The value of a raw register; None when there is none."""
        if raw is None:
            return None
        value = raw
        if self.signed:
            if raw == 0x8000 or raw == 0x7FFF:
                return None
            if raw >= 0x8000:
                value = raw - 0x10000
        if self.decimals:
            return round(value / 10**self.decimals, self.decimals)
        return value

    def encode(self, value: float) -> int:
        """The raw register for a value; raises ValueError outside the register's range."""
        number = float(value)
        if not self.minimum - 1e-9 <= number <= self.maximum + 1e-9:
            raise ValueError(f"{self.name}: {value} is outside {self.minimum}..{self.maximum}")
        return round(number * 10**self.decimals) & 0xFFFF


@dataclass(frozen=True, slots=True)
class RegisterMap:
    """All registers, by name and by kind."""

    datapoints: dict[str, Register]
    setpoints: dict[str, Register]
    faults: dict[str, dict[str, str]]
    raw: dict[str, Any]

    def get(self, name: str) -> Register:
        return self.setpoints.get(name) or self.datapoints[name]

    def find(self, name: str) -> Register | None:
        """A register this kind of unit may not have."""
        return self.setpoints.get(name) or self.datapoints.get(name)

    def addresses(self, store: str) -> set[int]:
        return {r.address for table in (self.datapoints, self.setpoints) for r in table.values() if r.store == store}


def _load_sync(file: str) -> RegisterMap:
    raw = json.loads((Path(__file__).parent / file).read_text(encoding="utf-8"))
    datapoints = {
        r["n"]: Register(
            kind=KIND_DATAPOINT,
            name=r["n"],
            address=r["a"],
            signed=bool(r["s"]),
            decimals=r["d"],
            unit=r["u"],
            section=r["sec"],
            labels=r["l"],
            options=r.get("o", {}),
            hint=r.get("t", ""),
            hidden=bool(r.get("hidden")),
            flag=bool(r.get("flag")),
            fault=r.get("fault"),
            bits=r.get("bits", {}),
            store=_TABLES[r.get("tb", "i")],
        )
        for r in raw["dp"]
    }
    setpoints = {
        r["n"]: Register(
            kind=KIND_SETPOINT,
            name=r["n"],
            address=r["a"],
            signed=bool(r["s"]),
            decimals=r["d"],
            unit=r["u"],
            section=r["sec"],
            labels=r["l"],
            options=r.get("o", {}),
            entity=r["k"],
            minimum=r["min"],
            maximum=r["max"],
            default=r["def"],
            level=r["lvl"],
            memory=r["mem"],
            read_only=bool(r.get("ro")),
            danger=bool(r.get("danger")),
            command=r.get("cmd"),
            hint=r.get("t", ""),
            store=_TABLES[r.get("tb", "h")],
        )
        for r in raw["sp"]
    }
    return RegisterMap(datapoints, setpoints, raw["faults"], raw)


_CACHE: dict[str, RegisterMap] = {}


async def async_load_registers(hass, model: str = MODEL_NEST_LS) -> RegisterMap:
    """Load a model's map once, away from the event loop."""
    if model not in _CACHE:
        _CACHE[model] = await hass.async_add_executor_job(_load_sync, REGISTER_FILES[model])
    return _CACHE[model]


def read_blocks(addresses: list[int], max_gap: int = 12, max_length: int = 100) -> list[tuple[int, int]]:
    """Addresses merged into (start, count) reads; short gaps are cheaper to read than to skip."""
    blocks: list[tuple[int, int]] = []
    start = last = None
    for address in sorted(set(addresses)):
        if start is None:
            start = last = address
        elif address - last - 1 > max_gap or address - start + 1 > max_length:
            blocks.append((start, last - start + 1))
            start = last = address
        else:
            last = address
    if start is not None:
        blocks.append((start, last - start + 1))
    return blocks
