"""AlpicAir NEST heat-recovery ventilation units over Modbus."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .client import ModbusClient, ModbusError
from .const import (
    CONF_FRAMING,
    CONF_SHOW_PANEL,
    CONF_UNIT,
    DOMAIN,
    FRAMING_TCP,
    NAME,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_URL,
    STATIC_URL,
)
from .coordinator import NestCoordinator
from .registers import async_load_registers
from .websocket import async_setup_websocket

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type NestConfigEntry = ConfigEntry[NestCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up what does not depend on a unit."""
    async_setup_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: NestConfigEntry) -> bool:
    """Connect to one unit."""
    client = ModbusClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_UNIT],
        entry.data.get(CONF_FRAMING, FRAMING_TCP),
    )
    try:
        await client.connect()
    except ModbusError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = NestCoordinator(hass, entry, client, await async_load_registers(hass))
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await client.close()
        raise
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # this entry only counts as loaded once setup returns
    await _async_update_panel(hass, [*hass.config_entries.async_loaded_entries(DOMAIN), entry])
    entry.async_on_unload(entry.add_update_listener(_async_options_changed))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NestConfigEntry) -> bool:
    """Disconnect from one unit."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.close()
        loaded = hass.config_entries.async_loaded_entries(DOMAIN)
        await _async_update_panel(hass, [e for e in loaded if e.entry_id != entry.entry_id])
    return unloaded


async def _async_options_changed(hass: HomeAssistant, entry: NestConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_update_panel(hass: HomeAssistant, entries: list[ConfigEntry]) -> None:
    """The sidebar item exists while a loaded unit wants it."""
    wanted = any(entry.options.get(CONF_SHOW_PANEL, True) for entry in entries)
    state = hass.data.setdefault(DOMAIN, {})

    if wanted and not state.get("panel"):
        version = (await async_get_integration(hass, DOMAIN)).version
        if not state.get("static"):
            folder = Path(__file__).parent / "frontend"
            await hass.http.async_register_static_paths(
                [StaticPathConfig(STATIC_URL, str(folder), cache_headers=False)]
            )
            state["static"] = True
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name=PANEL_ELEMENT,
            frontend_url_path=PANEL_URL,
            module_url=f"{STATIC_URL}/{PANEL_ELEMENT}.js?v={version}",
            sidebar_title=NAME,
            sidebar_icon=PANEL_ICON,
            require_admin=False,
        )
        state["panel"] = True
    elif not wanted and state.get("panel"):
        frontend.async_remove_panel(hass, PANEL_URL)
        state["panel"] = False
