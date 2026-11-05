"""The register table and its arithmetic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.alpicair_nest.registers import KIND_DATAPOINT, Register, read_blocks

TABLE = Path(__file__).parent.parent / "custom_components" / "alpicair_nest" / "registers.json"


def _register(**values) -> Register:
    base = {
        "kind": KIND_DATAPOINT,
        "name": "x",
        "address": 0,
        "signed": True,
        "decimals": 1,
        "unit": "",
        "section": "",
        "labels": {"en": "X"},
    }
    return Register(**(base | values))


def test_decode() -> None:
    register = _register()
    assert register.decode(215) == 21.5
    assert register.decode(0xFFF6) == -1.0
    assert register.decode(None) is None
    # a sensor that is not connected
    assert register.decode(0x8000) is None
    assert register.decode(0x7FFF) is None
    assert _register(signed=False, decimals=0).decode(0xFFF6) == 0xFFF6


def test_encode() -> None:
    register = _register(minimum=-30, maximum=70)
    assert register.encode(21.5) == 215
    assert register.encode(-1) == 0xFFF6
    with pytest.raises(ValueError):
        register.encode(71)


def test_blocks() -> None:
    assert read_blocks([0, 1, 2, 20, 21]) == [(0, 3), (20, 2)]
    assert read_blocks([0, 5, 10]) == [(0, 11)]
    assert read_blocks([0, 99, 100], max_gap=200) == [(0, 100), (100, 1)]
    assert read_blocks([]) == []


def test_table_has_no_secrets() -> None:
    text = TABLE.read_text(encoding="utf-8").lower()
    for word in ("servicelock", "nabto", "crypt", "accesslevelcode", "private_key"):
        assert word not in text
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    # the service PIN's register must not be offered as a setting, or its default published
    assert 475 not in {register["a"] for register in table["sp"]}


def test_table_is_consistent() -> None:
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    names = [r["n"] for r in table["sp"]]
    assert len(names) == len(set(names))
    assert not set(names) & {r["n"] for r in table["dp"]}
    addresses = [r["a"] for r in table["sp"]]
    assert len(addresses) == len(set(addresses))
    for register in table["sp"]:
        assert register["l"]["ru"]
        assert register["min"] <= register["max"], register["n"]
        assert register["k"] in ("number", "select", "switch", "button")
        if register["k"] == "select":
            assert len(register["o"]["ru"]) >= 2, register["n"]
