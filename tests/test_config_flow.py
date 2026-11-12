"""Adding a unit."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.alpicair_nest.const import DOMAIN
from custom_components.alpicair_nest.discovery import FoundUnit

from .conftest import MAC


async def _start(hass, model: str = "nest_ls"):
    """Chooses the kind of unit; what follows is the same for both."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["nest", "nest_ls"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": model})
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "method"
    assert result["menu_options"] == ["manual", "discover"]
    return result


async def test_manual(hass, unit) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "manual"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "127.0.0.1", "port": unit.port})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == MAC
    assert result["data"]["unit"] == 1
    assert result["data"]["framing"] == "tcp"
    assert result["data"]["model"] == "nest_ls"
    assert result["title"] == "AlpicAir NEST LS (127.0.0.1)"
    await hass.async_block_till_done()
    assert hass.states.get("climate.alpicair_nest") is not None
    await hass.config_entries.async_unload(result["result"].entry_id)
    await hass.async_block_till_done()


async def test_manual_nothing_there(hass, socket_enabled) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "manual"})
    with patch("custom_components.alpicair_nest.config_flow.async_probe", AsyncMock(return_value=None)):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "192.0.2.1", "port": 502})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_other_modbus_device_asks_first(hass, unit) -> None:
    unit.holding[576] = 0
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "manual"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": unit.port, "unit": 1}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(result["result"].entry_id)
    await hass.async_block_till_done()


async def test_same_unit_twice(hass, loaded, unit) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "manual"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "127.0.0.1", "port": unit.port})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def _search(hass, found):
    """Runs the search, then reloads the flow the way the dialog does when progress ends."""

    async def search(*_):
        await asyncio.sleep(0)
        return found

    result = await _start(hass)
    with patch("custom_components.alpicair_nest.config_flow.async_discover", search):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "discover"})
        assert result["type"] is FlowResultType.SHOW_PROGRESS
        await hass.async_block_till_done()
    return await hass.config_entries.flow.async_configure(result["flow_id"])


async def test_search_finds_a_unit(hass, unit) -> None:
    found = FoundUnit("127.0.0.1", unit.port, 1, "tcp", MAC, 48012, True)
    result = await _search(hass, [found])
    assert result["step_id"] == "discovered"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"device": "127.0.0.1"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "127.0.0.1"
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(result["result"].entry_id)
    await hass.async_block_till_done()


async def test_search_finds_nothing(hass) -> None:
    result = await _search(hass, [])
    assert result["step_id"] == "nothing_found"
    # the dialog reloads the flow after a progress step, which runs the step again
    again = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert again["type"] is FlowResultType.MENU
    assert again["menu_options"] == ["discover", "manual"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "manual"})
    assert result["step_id"] == "manual"


async def test_search_walks_the_network(hass, unit) -> None:
    """The real search, with the local network narrowed to the simulator."""
    from custom_components.alpicair_nest import discovery

    with (
        patch.object(discovery, "async_local_hosts", AsyncMock(return_value=["127.0.0.1"])),
    ):
        seen: list[float] = []
        found = await discovery.async_discover(hass, unit.port, seen.append)
    assert [u.host for u in found] == ["127.0.0.1"]
    assert seen[-1] == 1


async def test_options(hass, loaded) -> None:
    result = await hass.config_entries.options.async_init(loaded.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 30, "show_panel": False, "show_wall": True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert loaded.options["scan_interval"] == 30
    assert "alpicair-nest" not in hass.data["frontend_panels"]
    assert "alpicair-nest-wall" in hass.data["frontend_panels"]


async def test_reconfigure(hass, loaded, unit) -> None:
    result = await loaded.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": unit.port, "unit": 1}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
