"""Settings with a list of choices."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NestConfigEntry
from .coordinator import NestCoordinator
from .entity import NestRegisterEntity, exposed_setpoints, language
from .registers import Register

OPERATING_MODE = "OperatingMode"
MAIN = {OPERATING_MODE, "ControlMode"}


async def async_setup_entry(
    hass: HomeAssistant, entry: NestConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        NestSelect(coordinator, register, register.name in MAIN)
        for register in exposed_setpoints(coordinator, "select")
    )


class NestSelect(NestRegisterEntity, SelectEntity):
    """One setpoint with named values."""

    def __init__(self, coordinator: NestCoordinator, register: Register, enabled: bool) -> None:
        super().__init__(coordinator, "select", register, enabled)
        if not enabled:
            self._attr_entity_category = EntityCategory.CONFIG
        self._labels = register.option_labels(language(coordinator.hass))
        self._values = {label: value for value, label in self._labels.items()}
        self._attr_options = list(self._values)

    @property
    def current_option(self) -> str | None:
        return self._labels.get(self.raw_value)

    async def async_select_option(self, option: str) -> None:
        value = self._values[option]
        if self.register.name == OPERATING_MODE:
            await self.coordinator.async_set_operating_mode(value)
        else:
            await self.coordinator.async_write(self.register.name, value)
