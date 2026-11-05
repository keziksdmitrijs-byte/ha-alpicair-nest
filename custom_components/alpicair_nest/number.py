"""Numeric settings."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NestConfigEntry
from .coordinator import NestCoordinator
from .entity import NestRegisterEntity, exposed_setpoints
from .registers import Register

MAIN = {
    "AirTemp_SupplyTarget_Unoccupied",
    "AirTemp_SupplyTarget_Economy",
    "AirTemp_SupplyTarget_Comfort",
    "BoostMode_Timer",
    "Filter_TimerPeriod_Days",
}
BY_UNIT = {"°C": NumberDeviceClass.TEMPERATURE, "Pa": NumberDeviceClass.PRESSURE}


async def async_setup_entry(
    hass: HomeAssistant, entry: NestConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        NestNumber(coordinator, register, register.name in MAIN)
        for register in exposed_setpoints(coordinator, "number")
    )


class NestNumber(NestRegisterEntity, NumberEntity):
    """One numeric setpoint."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: NestCoordinator, register: Register, enabled: bool) -> None:
        super().__init__(coordinator, "number", register, enabled)
        self._attr_native_min_value = register.minimum
        self._attr_native_max_value = register.maximum
        self._attr_native_step = 10**-register.decimals if register.decimals else 1
        self._attr_native_unit_of_measurement = register.unit or None
        self._attr_device_class = BY_UNIT.get(register.unit)

    @property
    def native_value(self) -> float | None:
        return self.raw_value

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write(self.register.name, value)
