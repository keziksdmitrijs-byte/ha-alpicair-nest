"""On/off settings."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NestConfigEntry
from .entity import NestRegisterEntity, exposed_setpoints

MAIN = {"FreeCooling_Enable"}


async def async_setup_entry(
    hass: HomeAssistant, entry: NestConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        NestSwitch(coordinator, "switch", register, register.name in MAIN)
        for register in exposed_setpoints(coordinator, "switch")
    )


class NestSwitch(NestRegisterEntity, SwitchEntity):
    """One setpoint that is off or on."""

    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool | None:
        value = self.raw_value
        return None if value is None else bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self.register.name, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self.register.name, 0)
