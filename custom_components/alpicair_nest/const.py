"""Constants of the AlpicAir NEST integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "alpicair_nest"
NAME: Final = "AlpicAir NEST"
MANUFACTURER: Final = "AlpicAir"
MODEL: Final = "NEST"

CONF_UNIT: Final = "unit"
CONF_FRAMING: Final = "framing"
CONF_MAC: Final = "mac"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_SHOW_PANEL: Final = "show_panel"

DEFAULT_PORT: Final = 502
DEFAULT_SCAN_INTERVAL: Final = 10
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

FRAMING_TCP: Final = "tcp"
FRAMING_RTU: Final = "rtu"

# the unit ids a device can answer on: the usual one for Modbus TCP, then the table's serial address
UNIT_IDS: Final = (1, 20, 255, 0)

# how often the slower register groups are read, in polling cycles
SETPOINT_EVERY: Final = 6
SCHEDULE_EVERY: Final = 60

SCHEDULE_BASE: Final = 700
SCHEDULE_DAYS: Final = 7
SCHEDULE_EVENTS: Final = 10
SCHEDULE_FIELDS: Final = 4

# read-only setpoints the integration uses but does not offer as a setting
SP_SERVICE_PIN: Final = 475
SP_CONFIG_ID: Final = 471
SP_MODBUS_ENABLED: Final = 563
SP_MODBUS_PORT: Final = 566
SP_RTU_ADDRESS: Final = 576
SP_RTU_BAUD: Final = 577
SP_RTU_PARITY: Final = 578
SP_FILTER_RUNTIME: Final = 463
SP_RUNNING_HOURS: Final = 465
# the unit's clock has its own control in the panel, not one field per register
CLOCK_REGISTERS: Final = frozenset({"Min", "Hour", "Day", "Date", "Month", "Year"})

DP_FIRMWARE: Final = 312
DP_BOOTLOADER: Final = 313
DP_MAC: Final = 316
DP_IP: Final = 328

OPERATING_MODES: Final = ("standby", "unoccupied", "economy", "comfort", "boost", "kitchen_hood")
MODE_NAMES: Final = {
    "en": ("Standby", "Unoccupied", "Economy", "Comfort", "Boost", "Kitchen hood"),
    "ru": ("Ожидание", "Никого нет", "Эконом", "Комфорт", "Буст", "Кухонная вытяжка"),
    "lv": ("Gaidstāve", "Neviena nav", "Ekonomija", "Komforts", "Boost", "Virtuves tvaika nosūcējs"),
}

VIRTUAL_LABELS: Final = {
    "running_hours": {"en": "Running hours", "ru": "Моточасы", "lv": "Darba stundas"},
    "recovery_efficiency": {
        "en": "Heat recovery efficiency",
        "ru": "Эффективность рекуперации",
        "lv": "Siltuma atguves efektivitāte",
    },
    "active_faults": {"en": "Active faults", "ru": "Активные неисправности", "lv": "Aktīvie bojājumi"},
    "sync_clock": {
        "en": "Set unit clock from Home Assistant",
        "ru": "Установить часы установки по Home Assistant",
        "lv": "Iestatīt iekārtas pulksteni no Home Assistant",
    },
}

CONTROL_AUTO: Final = 0
CONTROL_MANUAL: Final = 1

EVENT_FAULT: Final = f"{DOMAIN}_fault"
STORAGE_VERSION: Final = 1
FAULT_LOG_SIZE: Final = 200
SERVICE_UNLOCK_SECONDS: Final = 900
PIN_MAX_TRIES: Final = 5
PIN_LOCK_SECONDS: Final = 60

PANEL_URL: Final = "alpicair-nest"
PANEL_ELEMENT: Final = "alpicair-nest-panel"
PANEL_ICON: Final = "mdi:air-filter"
STATIC_URL: Final = "/alpicair_nest_static"
