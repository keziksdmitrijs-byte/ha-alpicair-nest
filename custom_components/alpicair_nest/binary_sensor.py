"""On/off data points."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NestConfigEntry
from .coordinator import NestCoordinator
from .entity import NestRegisterEntity
from .registers import Register

PROBLEMS = {"AnyErrorActive", "AnyWarningActive", "FilterTimerExpired", "FireProtection_Active"}
MAIN = PROBLEMS | {
    "FreeCooling_ActiveOrNot",
    "AirTemp_ERC_Deicing_HeatExchangerActive",
    "AirQ_CO2_ControlActiveOrNot",
    "AirQ_Humidity_ControlActiveOrNot",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: NestConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        NestBinarySensor(coordinator, register, register.name in MAIN)
        for register in coordinator.registers.datapoints.values()
        if register.flag and not register.hidden
    )


class NestBinarySensor(NestRegisterEntity, BinarySensorEntity):
    """One flag."""

    def __init__(self, coordinator: NestCoordinator, register: Register, enabled: bool) -> None:
        super().__init__(coordinator, "binary_sensor", register, enabled)
        if register.name in PROBLEMS:
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        if not enabled:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        value = self.raw_value
        return None if value is None else bool(value)
