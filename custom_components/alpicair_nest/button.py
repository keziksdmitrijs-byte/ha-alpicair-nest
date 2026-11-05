"""Commands."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NestConfigEntry
from .const import VIRTUAL_LABELS
from .coordinator import NestCoordinator
from .entity import NestEntity, NestRegisterEntity, exposed_setpoints, language

MAIN = {"Filter_Reset", "ResetErrors"}


async def async_setup_entry(
    hass: HomeAssistant, entry: NestConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[ButtonEntity] = [
        NestButton(coordinator, "button", register, register.name in MAIN)
        for register in exposed_setpoints(coordinator, "button")
    ]
    entities.append(NestClockButton(coordinator))
    async_add_entities(entities)


class NestButton(NestRegisterEntity, ButtonEntity):
    """One command register."""

    _attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        await self.coordinator.async_press(self.register.name)


class NestClockButton(NestEntity, ButtonEntity):
    """Sets the unit's clock."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: NestCoordinator) -> None:
        name = VIRTUAL_LABELS["sync_clock"]
        super().__init__(coordinator, "button", "sync_clock", name.get(language(coordinator.hass), name["en"]))

    async def async_press(self) -> None:
        await self.coordinator.async_sync_clock()
