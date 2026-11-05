"""Adding a unit: by its address, or by searching the local network."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_FRAMING,
    CONF_MAC,
    CONF_SCAN_INTERVAL,
    CONF_SHOW_PANEL,
    CONF_SHOW_WALL,
    CONF_UNIT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FRAMING_TCP,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    NAME,
)
from .discovery import FoundUnit, async_discover, async_probe

CONF_DEVICE = "device"


def _manual_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=65535, mode=selector.NumberSelectorMode.BOX)
            ),
            # left empty, the search tries the usual ids
            vol.Optional(CONF_UNIT, description={"suggested_value": defaults.get(CONF_UNIT)}): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=255, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
        }
    )


def _title(host: str) -> str:
    return f"{NAME} ({host})"


class NestConfigFlow(ConfigFlow, domain=DOMAIN):
    """One unit per config entry; the MAC address tells them apart."""

    VERSION = 1

    def __init__(self) -> None:
        self._found: list[FoundUnit] = []
        self._scan: asyncio.Task[list[FoundUnit]] | None = None
        self._progress_shown = 0.0
        self._unconfirmed: FoundUnit | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NestOptionsFlow:
        return NestOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Type an address or search for the unit."""
        return self.async_show_menu(step_id="user", menu_options=["manual", "discover"])

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The address is known."""
        errors: dict[str, str] = {}
        if user_input is not None:
            unit = await self._async_probe_input(user_input, errors)
            if unit is not None:
                if unit.matched:
                    return await self._async_finish(unit)
                self._unconfirmed = unit
                return await self.async_step_confirm()
        return self.async_show_form(
            step_id="manual",
            data_schema=self.add_suggested_values_to_schema(_manual_schema({}), user_input or {}),
            errors=errors,
        )

    async def _async_probe_input(self, user_input: dict[str, Any], errors: dict[str, str]) -> FoundUnit | None:
        host = user_input[CONF_HOST].strip()
        port = int(user_input[CONF_PORT])
        unit_id = user_input.get(CONF_UNIT)
        found = await async_probe(host, port, None if unit_id is None else int(unit_id))
        if found is None:
            errors["base"] = "cannot_connect"
        return found

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Something answers on Modbus, but it does not look like this unit."""
        assert self._unconfirmed is not None
        if user_input is not None:
            return await self._async_finish(self._unconfirmed)
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "host": self._unconfirmed.host,
                "unit": str(self._unconfirmed.unit),
            },
        )

    async def async_step_discover(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Search the local networks; the form shows how far it has got."""
        if self._scan is None:
            self._progress_shown = 0.0

            def progress(share: float) -> None:
                # the dialog only needs a few updates, not one per address
                if share - self._progress_shown >= 0.02 or share >= 1:
                    self._progress_shown = share
                    self.async_update_progress(share)

            self._scan = self.hass.async_create_task(async_discover(self.hass, DEFAULT_PORT, progress))
        if not self._scan.done():
            return self.async_show_progress(
                step_id="discover",
                progress_action="scanning",
                progress_task=self._scan,
            )
        try:
            self._found = self._scan.result()
        except Exception:
            self._found = []
        self._scan = None
        return self.async_show_progress_done(next_step_id="discovered")

    async def async_step_discovered(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose from what was found."""
        configured = {entry.unique_id for entry in self._async_current_entries()}
        fresh = [unit for unit in self._found if unit.unique_id not in configured]
        if not fresh:
            return await self.async_step_nothing_found()
        if user_input and CONF_DEVICE in user_input:
            chosen = next(u for u in fresh if u.host == user_input[CONF_DEVICE])
            return await self._async_finish(chosen)
        options = [
            selector.SelectOptionDict(
                value=unit.host,
                label=f"{unit.host}" + (f"  ·  {unit.mac}" if unit.mac else ""),
            )
            for unit in fresh
        ]
        return self.async_show_form(
            step_id="discovered",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE, default=options[0]["value"]): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.LIST)
                    )
                }
            ),
            description_placeholders={"count": str(len(fresh))},
        )

    async def async_step_nothing_found(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Search again or type the address."""
        return self.async_show_menu(step_id="nothing_found", menu_options=["discover", "manual"])

    async def _async_finish(self, unit: FoundUnit) -> ConfigFlowResult:
        await self.async_set_unique_id(unit.unique_id)
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: unit.host, CONF_PORT: unit.port, CONF_UNIT: unit.unit, CONF_FRAMING: unit.framing}
        )
        return self.async_create_entry(
            title=_title(unit.host),
            data={
                CONF_HOST: unit.host,
                CONF_PORT: unit.port,
                CONF_UNIT: unit.unit,
                CONF_FRAMING: unit.framing or FRAMING_TCP,
                CONF_MAC: unit.mac,
            },
            options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL, CONF_SHOW_PANEL: True, CONF_SHOW_WALL: True},
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The unit has a new address."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            unit = await self._async_probe_input(user_input, errors)
            if unit is not None:
                await self.async_set_unique_id(unit.unique_id)
                # an entry that never learned the MAC cannot tell the units apart
                if entry.data.get(CONF_MAC):
                    self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    title=_title(unit.host),
                    unique_id=unit.unique_id,
                    data_updates={
                        CONF_HOST: unit.host,
                        CONF_PORT: unit.port,
                        CONF_UNIT: unit.unit,
                        CONF_FRAMING: unit.framing,
                        CONF_MAC: unit.mac,
                    },
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_manual_schema(
                {
                    CONF_HOST: entry.data[CONF_HOST],
                    CONF_PORT: entry.data[CONF_PORT],
                    CONF_UNIT: entry.data[CONF_UNIT],
                }
            ),
            errors=errors,
        )


class NestOptionsFlow(OptionsFlow):
    """How often to poll, and the sidebar item."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_SHOW_PANEL: user_input[CONF_SHOW_PANEL],
                    CONF_SHOW_WALL: user_input[CONF_SHOW_WALL],
                }
            )
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_SHOW_PANEL, default=options.get(CONF_SHOW_PANEL, True)
                    ): selector.BooleanSelector(),
                    vol.Required(CONF_SHOW_WALL, default=options.get(CONF_SHOW_WALL, True)): selector.BooleanSelector(),
                }
            ),
        )
