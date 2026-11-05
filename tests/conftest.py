"""Shared fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alpicair_nest.const import CONF_FRAMING, CONF_MAC, CONF_UNIT, DOMAIN

from .simulator import Simulator

MAC = "02:ac:10:20:30:40"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load this integration."""


@pytest.fixture
async def unit(socket_enabled) -> AsyncIterator[Simulator]:
    simulator = Simulator()
    await simulator.start()
    yield simulator
    await simulator.stop()


@pytest.fixture
def entry(hass, unit: Simulator) -> MockConfigEntry:
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="AlpicAir NEST (127.0.0.1)",
        unique_id=MAC,
        data={"host": "127.0.0.1", "port": unit.port, CONF_UNIT: 1, CONF_FRAMING: "tcp", CONF_MAC: MAC},
        options={"scan_interval": 10, "show_panel": True},
    )
    config_entry.add_to_hass(hass)
    return config_entry


@pytest.fixture
async def loaded(hass, entry: MockConfigEntry) -> AsyncIterator[MockConfigEntry]:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
