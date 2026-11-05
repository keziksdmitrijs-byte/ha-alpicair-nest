"""Sensors: every visible data point, the everyday ones switched on."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NestConfigEntry
from .const import VIRTUAL_LABELS
from .coordinator import NestCoordinator
from .entity import NestEntity, NestRegisterEntity, language
from .registers import Register

MAIN = {
    "T_Outdoor",
    "T_Supply",
    "T_Extract",
    "T_Exhaust",
    "AirTemp_SupplyControl_PresentSetpoint",
    "Fan1_RPM",
    "Fan2_RPM",
    "Fan1_Output",
    "Fan2_Output",
    "Airflow_Supply",
    "Airflow_Exhaust",
    "Pressure_1",
    "Pressure_2",
    "CurrentOperatingMode",
    "AirTemp_PhaseControl_WhatPhase",
    "AirTemp_PhaseControl_HeatingDemand",
    "AirTemp_PhaseControl_CoolingDemand",
    "Filter_RemainingDays",
    "BoostMode_RemainingTimer_Minutes",
}

# sensors that exist only when an analog input is set up for them: register -> input function
ANALOG = {
    "AI_ExtractAirHumidity": 1,
    "AI_ExtractAirCO2": 2,
    "AI_SupplyAirHumidity": 3,
    "AI_VOC": 4,
    "AI_SupplyDuctPressure": 5,
    "AI_ExtractDuctPressure": 6,
}
ANALOG_INPUTS = ("AI1_Configuration", "AI2_Configuration", "AI3_Configuration")
ROTARY = 0
PLATE = 1

BY_UNIT = {
    "°C": SensorDeviceClass.TEMPERATURE,
    "Pa": SensorDeviceClass.PRESSURE,
    "m³/h": SensorDeviceClass.VOLUME_FLOW_RATE,
    "V": SensorDeviceClass.VOLTAGE,
    "mA": SensorDeviceClass.CURRENT,
    "s": SensorDeviceClass.DURATION,
    "min": SensorDeviceClass.DURATION,
    "h": SensorDeviceClass.DURATION,
    "d": SensorDeviceClass.DURATION,
}
BY_NAME = {
    "AI_ExtractAirHumidity": SensorDeviceClass.HUMIDITY,
    "AI_SupplyAirHumidity": SensorDeviceClass.HUMIDITY,
    "AI_ExtractAirCO2": SensorDeviceClass.CO2,
    "AI_VOC": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
}


def _is_main(coordinator: NestCoordinator, name: str) -> bool:
    """The everyday sensors, with the one that fits the installed exchanger."""
    exchanger = coordinator.value("AirTemp_ERC_TypeInstalled")
    if name == "AirTemp_ERC_Rotary_Speed":
        return exchanger == ROTARY
    if name == "AirTemp_ERC_Passive_BypassPosition":
        return exchanger == PLATE
    return name in MAIN


def _configured_functions(coordinator: NestCoordinator) -> set[int]:
    return {coordinator.value(name) for name in ANALOG_INPUTS}


async def async_setup_entry(
    hass: HomeAssistant, entry: NestConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    functions = _configured_functions(coordinator)
    entities: list[SensorEntity] = []
    for register in coordinator.registers.datapoints.values():
        if register.hidden or register.flag:
            continue
        if register.name in ANALOG:
            entities.append(NestAnalogSensor(coordinator, register, ANALOG[register.name] in functions))
        else:
            entities.append(NestSensor(coordinator, register, _is_main(coordinator, register.name)))
    entities += [NestRecovery(coordinator), NestRunningHours(coordinator), NestFaults(coordinator)]
    async_add_entities(entities)


class NestSensor(NestRegisterEntity, SensorEntity):
    """One data point."""

    def __init__(self, coordinator: NestCoordinator, register: Register, enabled: bool) -> None:
        super().__init__(coordinator, "sensor", register, enabled)
        if not enabled:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._labels = register.option_labels(language(coordinator.hass))
        if self._labels:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(dict.fromkeys(self._labels.values()))
            return
        self._attr_native_unit_of_measurement = register.unit or None
        self._attr_device_class = BY_NAME.get(register.name) or BY_UNIT.get(register.unit)
        if register.unit:
            self._attr_suggested_display_precision = register.decimals
        if register.unit in ("°C", "Pa", "m³/h", "%", "rpm", "V", "mA", "ppm"):
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | int | str | None:
        value = self.raw_value
        if self._labels:
            return self._labels.get(value)
        return value


class NestAnalogSensor(NestSensor):
    """A sensor wired to an analog input; unavailable while no input is set up for it."""

    @property
    def available(self) -> bool:
        return super().available and ANALOG[self.register.name] in _configured_functions(self.coordinator)


class NestVirtualSensor(NestEntity, SensorEntity):
    """A value that takes more than one register."""

    key: str

    def __init__(self, coordinator: NestCoordinator) -> None:
        name = VIRTUAL_LABELS[self.key]
        super().__init__(coordinator, "sensor", self.key, name.get(language(coordinator.hass), name["en"]))


class NestRecovery(NestVirtualSensor):
    key = "recovery_efficiency"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:heat-wave"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.virtual.get(self.key)


class NestRunningHours(NestVirtualSensor):
    key = "running_hours"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.virtual.get(self.key)


class NestFaults(NestVirtualSensor):
    key = "active_faults"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:alert-circle-outline"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.faults)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        lang = language(self.hass)
        names = self.coordinator.registers.faults
        return {
            "faults": [
                {
                    "kind": fault["kind"],
                    "name": names.get(fault["name"] or "", {}).get(lang)
                    or names.get(fault["name"] or "", {}).get("en")
                    or f"{fault['word']} bit {fault['bit']}",
                }
                for fault in self.coordinator.data.faults
            ]
        }
