"""What all entities share."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CLOCK_REGISTERS, DOMAIN
from .coordinator import NestCoordinator
from .registers import Register


def language(hass: HomeAssistant) -> str:
    """The language entity names are written in; register names exist in English and Russian."""
    return hass.config.language.split("-")[0]


# a NEST keeps its schedules as a hundred plain settings: those are for the panel
PANEL_ONLY_SECTIONS = {"week_schedule", "holidays"}


def exposed_setpoints(coordinator: NestCoordinator, entity: str) -> list[Register]:
    """Setpoints offered as entities: everyday ones. Service settings live in the panel only."""
    return [
        register
        for register in coordinator.registers.setpoints.values()
        if register.entity == entity
        and register.level != "service"
        and register.section not in PANEL_ONLY_SECTIONS
        and not register.danger
        and not register.read_only
        and register.name not in CLOCK_REGISTERS
    ]


class NestEntity(CoordinatorEntity[NestCoordinator]):
    """An entity of the unit, with an entity id that does not depend on the language."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NestCoordinator, platform: str, key: str, name: str | None) -> None:
        super().__init__(coordinator)
        slug = key.lower()
        self._attr_unique_id = f"{coordinator.unique_id}_{slug}"
        self._attr_device_info = coordinator.device_info
        self._attr_name = name
        self.entity_id = f"{platform}.{DOMAIN}_{slug}"


class NestRegisterEntity(NestEntity):
    """An entity showing one register."""

    def __init__(self, coordinator: NestCoordinator, platform: str, register: Register, enabled: bool = False) -> None:
        super().__init__(coordinator, platform, register.name, register.label(language(coordinator.hass)))
        self.register = register
        self._attr_entity_registry_enabled_default = enabled

    @property
    def raw_value(self) -> float | int | None:
        return self.coordinator.value(self.register.name)
