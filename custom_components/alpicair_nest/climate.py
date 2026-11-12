"""The unit as a climate entity: on/off, mode as preset, and the air temperature target."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import PRECISION_TENTHS, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NestConfigEntry
from .const import CONTROL_AUTO
from .coordinator import NestCoordinator
from .entity import NestEntity

STANDBY = 0
COMFORT = 3
PRESET_SCHEDULE = "schedule"
EXTRACT_STRATEGY = 1
PHASE_HEATING = 0
PHASE_COOLING = 2
# modes with a target of their own; the others fall back to Comfort's
TARGET_SUFFIX = {1: "Unoccupied", 2: "Economy", 3: "Comfort"}


async def async_setup_entry(
    hass: HomeAssistant, entry: NestConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([NestClimate(entry.runtime_data)])


class NestClimate(NestEntity, ClimateEntity):
    """The unit."""

    _attr_translation_key = "nest"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.FAN_ONLY]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_TENTHS
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator: NestCoordinator) -> None:
        super().__init__(coordinator, "climate", "unit", None)
        self.entity_id = "climate.alpicair_nest"
        self._resume = COMFORT
        modes = [coordinator.modes[mode] for mode in coordinator.selectable if mode != STANDBY]
        self._attr_preset_modes = [PRESET_SCHEDULE, *modes] if coordinator.has_auto else modes

    @property
    def _extract_control(self) -> bool:
        return self.coordinator.value("AirTemp_ControlStrategy") == EXTRACT_STRATEGY

    @property
    def _mode(self) -> int | None:
        return self.coordinator.value("CurrentOperatingMode")

    def _target_name(self) -> str:
        suffix = TARGET_SUFFIX.get(self._mode, "Comfort")
        name = f"AirTemp_{'Extract' if self._extract_control else 'Supply'}Target_{suffix}"
        # a NEST has one target for each mode, whichever air it is held by
        return name if name in self.coordinator.registers.setpoints else f"AirTemp_SupplyTarget_{suffix}"

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.value("T_Extract" if self._extract_control else "T_Supply")

    @property
    def target_temperature(self) -> float | None:
        target = self.coordinator.value(self._target_name())
        # on a NEST, 0 in place of a target means energy saving
        return None if self.coordinator.target_limits and not target else target

    @property
    def min_temp(self) -> float:
        if self.coordinator.target_limits:
            return self.coordinator.target_limits[0]
        return self.coordinator.value("AirTemp_MinAllowedSetpoint") or 0

    @property
    def max_temp(self) -> float:
        if self.coordinator.target_limits:
            return self.coordinator.target_limits[1]
        return self.coordinator.value("AirTemp_MaxAllowedSetpoint") or 50

    @property
    def hvac_mode(self) -> HVACMode | None:
        mode = self._mode
        if mode is None:
            return None
        return HVACMode.OFF if mode == STANDBY else HVACMode.FAN_ONLY

    @property
    def hvac_action(self) -> HVACAction | None:
        mode = self._mode
        if mode is None:
            return None
        if mode == STANDBY:
            return HVACAction.OFF
        phase = self.coordinator.value("AirTemp_PhaseControl_WhatPhase")
        if phase == PHASE_HEATING and self.coordinator.value("AirTemp_PhaseControl_HeatingDemand"):
            return HVACAction.HEATING
        if phase == PHASE_COOLING and self.coordinator.value("AirTemp_PhaseControl_CoolingDemand"):
            return HVACAction.COOLING
        if self.coordinator.value("Heater_Control_Output"):
            return HVACAction.HEATING
        if any(self.coordinator.value(name) for name in ("Hydronic_Cooler_Control_Output", "Dx_Cooler_Control_Output")):
            return HVACAction.COOLING
        return HVACAction.FAN

    @property
    def preset_mode(self) -> str | None:
        if self.coordinator.value("ControlMode") == CONTROL_AUTO:
            return PRESET_SCHEDULE
        mode = self._mode
        if mode in (None, STANDBY) or not 0 <= mode < len(self.coordinator.modes):
            return None
        return self.coordinator.modes[mode]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            if self._mode not in (None, STANDBY):
                self._resume = self._mode
            await self.coordinator.async_set_operating_mode(STANDBY)
        else:
            await self.coordinator.async_set_operating_mode(self._resume)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_SCHEDULE:
            await self.coordinator.async_set_auto()
        else:
            await self.coordinator.async_set_operating_mode(self.coordinator.modes.index(preset_mode))

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self.coordinator.async_write(self._target_name(), temperature)
