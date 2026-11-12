#!/usr/bin/env python3
"""Build custom_components/alpicair_nest/registers_nest.json from the MCB Modbus table.

Usage: build_registers_nest.py <MCB_*_Modbus_table_*.xlsx>

This is the map of the NEST units (MCB controller). The NEST LS map comes from build_registers.py.
The workbook itself is not part of this repository. Passwords, factory functions, forced outputs,
the I/O map and the registers a building management system writes sensor values to are left out
here, so they never reach the integration.

The table gives its addresses as they go on the wire: register 1 is asked for as address 1.
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from labels_nest import ALARMS, LABELS, OPTIONS, STATES

OUT = Path(__file__).parent.parent / "custom_components" / "alpicair_nest" / "registers_nest.json"

HOLDING, INPUT, COIL, DISCRETE = "h", "i", "c", "d"

# registers that mean the same as one of the NEST LS: the same name, so the panels, the entities
# and automations find them in both
ALIASES = {
    "HR_USER_CONFIG_CURRENT_SYSTEM_MODE": "OperatingMode",
    "HR_USER_CONFIG_COMFORT_MODE_TEMPERATURE_SET_POINT": "AirTemp_SupplyTarget_Comfort",
    "HR_USER_CONFIG_ECONOMY_MODE_TEMPERATURE_SET_POINT": "AirTemp_SupplyTarget_Economy",
    "HR_USER_CONFIG_BUILDING_PROTECTION_MODE_TEMPERATURE_SET_POINT": "AirTemp_SupplyTarget_Unoccupied",
    "HR_ALARMS_RESET": "ResetErrors",
    "HR_AIR_FLOW_1_SUPPLY": "Linear_Fan1_Fanspeed_Unoccupied",
    "HR_AIR_FLOW_2_SUPPLY": "Linear_Fan1_Fanspeed_Economy",
    "HR_AIR_FLOW_3_SUPPLY": "Linear_Fan1_Fanspeed_Comfort",
    "HR_AIR_FLOW_4_SUPPLY": "Linear_Fan1_Fanspeed_Boost",
    "HR_AIR_FLOW_1_EXTRACT": "Linear_Fan2_Fanspeed_Unoccupied",
    "HR_AIR_FLOW_2_EXTRACT": "Linear_Fan2_Fanspeed_Economy",
    "HR_AIR_FLOW_3_EXTRACT": "Linear_Fan2_Fanspeed_Comfort",
    "HR_AIR_FLOW_4_EXTRACT": "Linear_Fan2_Fanspeed_Boost",
    "HR_SERVICE_FILTERS_TIMER_LIMIT": "Filter_TimerPeriod_Days",
    "HR_SERVICE_TEMPERATURE_CONTROL_TYPE": "AirTemp_ControlStrategy",
    "COIL_FILTER_TIMER_RESET": "Filter_Reset",
    "COIL_NIGHT_COOLING_FUNCTION": "FreeCooling_Enable",
    "COIL_INTENSIVE_AIR_FLOW_BOOST": "BoostMode_Active",
    "COIL_SYSTEM_RESTART": "RestartUnit",
    "IR_CURRENT_SYSTEM_STATE": "SystemState",
    "IR_SOFTWARE_VERSION": "FirmwareVerMain",
    "IR_BOOTLOADER_VERSION": "FirmwareVerBootloader",
    "IR_CURRENT_SYSTEM_MODE": "CurrentOperatingMode",
    "IR_REQUIRED_SUPPLY_TEMPERATURE": "AirTemp_SupplyControl_PresentSetpoint",
    "IR_SUPPLY_AIR_TEMPERATURE": "T_Supply",
    "IR_EXTRACT_AIR_TEMPERATURE": "T_Extract",
    "IR_EXHAUST_AIR_TEMPERATURE": "T_Exhaust",
    "IR_OUTDOOR_AIR_TEMPERATURE": "T_Outdoor",
    "IR_AIR_SUPPLY_AIR_RH": "AI_SupplyAirHumidity",
    "IR_AIR_SUPPLY_AIR_CO2": "AI_SupplyAirCO2",
    "IR_AIR_EXTRACT_AIR_RH": "AI_ExtractAirHumidity",
    "IR_AIR_EXTRACT_AIR_CO2": "AI_ExtractAirCO2",
    "IR_FILTERS_TIMER_DAYS_LEFT": "Filter_RemainingDays",
    "IR_SUPPLY_FAN_SPREED_RPM": "Fan1_RPM",
    "IR_EXTRACT_FAN_SPREED_RPM": "Fan2_RPM",
    "IR_CURRENT_SUPPLY_AIR_FLOW": "Fan1_Output",
    "IR_CURRENT_EXTRACT_AIR_FLOW@62": "Fan2_Output",
    "IR_CURRENT_SUPPLY_AIR_FLOW_M_H": "Airflow_Supply",
    "IR_CURRENT_EXTRACT_AIR_FLOW@64": "Airflow_Exhaust",
    "IR_BYPASS_POSITION": "AirTemp_ERC_Passive_BypassPosition",
    "IR_ROTOR_CONTROL_OUTPUT": "AirTemp_ERC_Rotary_Speed",
    "HR_USER_CONFIG_INTENSIVE_AIR_FLOW_TIME_SET": "BoostMode_Timer_Seconds",
    "IR_INTENSIVE_AIR_FLOW_TIME_LEFT": "BoostMode_RemainingTimer_Seconds",
    "IR_PREATER_CONTROL_OUTPUT": "Preheater_Control_Output",
    "IR_EX1_MODULE": "Ex1_Module_Version",
    "IR_EX2_MODULE": "Ex2_Module_Version",
    "IR_COMUNICATION_MODULE": "Communication_Module_Version",
    "DI_CRITICAL_ALARM": "AnyErrorActive",
    "DI_WARNING": "AnyWarningActive",
    "DI_NIGHT_COOLING_FUNCTION": "FreeCooling_ActiveOrNot",
}

for _side in ("SUPPLY", "EXTRACT"):
    for _step in range(1, 5):
        ALIASES[f"IR_{_step}_{_side}_AIR_FLOW_FLOW_PRESSURE"] = f"{_side.capitalize()}_Air_Flow_{_step}_Pressure"
        ALIASES[f"IR_{_step}_{_side}_AIR_FLOW_FLOW"] = f"{_side.capitalize()}_Air_Flow_{_step}"

# never read and never offered: passwords, alarm flags that have a discrete input of their own,
# the countdown that is also an input register
SKIP = {
    "HR_ADJUSTER_PASSWORD", "HR_SERVICE_PASSWORD", "HR_ALARM_A", "HR_ALARM_B",
    "HR_USER_CONFIG_INTENSIVE_AIR_FLOW_TIME_LEFT", "COIL_CHANGE_PASSWORD", "COIL_SHOW_ALARMS_ON_COOKING_HOOD",
}
UNNAMED_ALARMS = {
    71: "ALARM_AFTER_HX_TEMPERATURE_SENSOR_FAILURE_EMERGENCY_RUN",
    72: "ALARM_AFTER_HX_TEMPERATURE_SENSOR_FAILURE_SYSTEM_STOPPED",
}
# whole blocks of holding registers: clock setting (it has its own command), alarm history pages,
# forced outputs, values written by a building management system, factory functions, the I/O map
SKIP_HOLDING = [(100, 106), (330, 390), (400, 435), (800, 828), (850, 863), (900, 997)]
SKIP_COILS = [(2, 2), (55, 63)]
SKIP_DISCRETE = [(190, 192)]
HIDDEN = {"IR_AHU_ID_1", "IR_AHU_ID_2", "IR_AHU_ID_3", "IR_AHU_ID_4", "IR_AHU_ID_5"}
CLOCK = {"IR_YEARS", "IR_MONTH", "IR_DAY", "IR_WEEK_DAY", "IR_HOURS", "IR_MINUTES", "IR_SECONDS"}

# coils and registers that do something once when written
TRIGGERS = {
    "COIL_FILTER_TIMER_RESET", "COIL_DO_FIRE_DAMPER_TEST", "COIL_SAVE_TO_EEPROM", "COIL_SYSTEM_RESTART", "COIL_GO_BACK",
    "COIL_CALIBRATE_PRESSURE_LIMITS", "COIL_RESTOR_FACTORY_DEFAULTS", "HR_ALARMS_RESET",
}
DANGER = {
    "COIL_SYSTEM_RESTART", "COIL_RESTOR_FACTORY_DEFAULTS", "COIL_CALIBRATE_PRESSURE_LIMITS",
    "HR_SERVICE_Comunication_1_ADDRESS", "HR_SERVICE_Comunication_1_BAUDRATE", "HR_SERVICE_Comunication_1_SETTINGS",
    "HR_SERVICE_Comunication_2_ADDRESS", "HR_SERVICE_Comunication_2_BAUDRATE", "HR_SERVICE_Comunication_2_SETTINGS",
    "COIL_COMM_MODULE",
}
ON_OFF = [{"Disabled", "Enabled"}, {"Not Active", "Active"}, {"No", "Yes"}]
COIL_OPTIONS = {
    "COIL_HEATER_PREHEATER": {0: "Heater on the main board, pre-heater on EX1", 1: "Pre-heater on the main board, heater on EX1"},
}
LEVELS = {"user": "user", "adjuster": "adjuster", "service": "service"}

# what the table words differently for each register, or leaves out
OVERRIDES: dict[str, dict] = {
    "HR_USER_CONFIG_COMFORT_MODE_TEMPERATURE_SET_POINT": {"min": 16, "max": 30, "d": 1, "u": "°C"},
    "HR_USER_CONFIG_ECONOMY_MODE_TEMPERATURE_SET_POINT": {"min": 0, "max": 30, "d": 1, "u": "°C", "o": None, "t": "0: energy saving, otherwise 16–30 °C"},
    "HR_USER_CONFIG_BUILDING_PROTECTION_MODE_TEMPERATURE_SET_POINT": {"min": 0, "max": 30, "d": 1, "u": "°C", "o": None, "t": "0: energy saving, otherwise 16–30 °C"},
    "HR_USER_CONFIG_AIR_FLOW_BY_PERCENTS": {"t": "0: air flow of the current mode"},
    "HR_USER_CONFIG_FIRE_DAMPER_TESTING_HOUR": {"u": "h"},
    "HR_SERVICE_FIRE_DAMPER_TESTING_DAYS_INTERVAL": {"u": "d"},
    "HR_COOKING_HOOD_SPEED": {"min": 0, "max": 4, "t": "Speed 4 is a boost and is limited in time"},
    "HR_SERVICE_ANTIFROST_OUTSIDE_SET": {"min": -40, "max": 0, "d": 1, "u": "°C", "s": 1, "o": None, "t": "0: not used"},
    "HR_SERVICE_ANTIFROST_EXHAUST_SET": {"min": 0, "max": 20, "d": 1, "u": "°C", "o": None, "t": "0: not used"},
    "HR_SERVICE_ANTIFROST_EXHAUST_DIFF": {"min": 0, "max": 10, "d": 1, "u": "°C", "o": None, "t": "0: not used"},
    "HR_AUTO_ALARM_RESET_TIME": {"min": 0, "max": 24, "u": "h", "o": None, "t": "0: not used"},
    "HR_SERVICE_EL_PREHEATER_SET_POINT": {"min": -30, "max": 10, "d": 1, "u": "°C", "s": 1, "o": None, "t": "-0.1: automatic"},
    "HR_SERVICE_MAXIMAL_SUPPLY_FAN_VOLTAGE": {"min": 0, "max": 10, "d": 2, "u": "V"},
    "HR_SERVICE_MINIMAL_FAN_VOLTAGE": {"min": 0, "max": 10, "d": 2, "u": "V"},
    "HR_SERVICE_K_FACTOR_SUPPLY": {"min": 0, "max": 1000, "d": 1, "u": ""},
    "HR_SERVICE_K_FACTOR_EXTRACT": {"min": 0, "max": 1000, "d": 1, "u": ""},
    "HR_SERVICE_HEATER_PWM_TIME": {"u": "s"},
    "HR_SERVICE_PREHEATER_PWM_TIME": {"u": "s"},
    "HR_SERVICE_DX_COOLER_DEFROST_TIME": {"u": "s"},
    "HR_SERVICE_CRITICAL_TEMP": {"min": -50, "max": 0, "d": 1, "u": "°C", "s": 1},
    "HR_SERVICE_DX_COOLER_MIN_TEMP": {"min": -50, "max": 20, "d": 1, "u": "°C", "s": 1},
    "HR_SERVICE_HYDRONIC_HEATER_REQUIRED_RETURN_WATER_TEMPERATURE": {"min": -10, "max": 30, "u": "°C", "s": 1},
    "HR_SERVICE_HYDRONIC_PREHEATER_REQUIRED_RETURN_WATER_TEMPERATURE": {"min": -10, "max": 30, "u": "°C", "s": 1},
    "HR_SERVICE_HEAT_EXCHANGER_DAMPER_TYPE": {"min": 1, "max": 4},
    "HR_TACHO_PULSES_PER_REVOLUTION": {"min": 1, "max": 10, "u": ""},
    "HR_AIR_FLOW_EXTRACT_SUPPLY_DIFERENCE": {"min": -100, "max": 100, "d": 1, "u": "%", "s": 1},
    "HR_USER_CONFIG_WINTER_SUMMER_TSET_CORRECTION": {"min": -15, "max": 15, "d": 1, "u": "°C", "s": 1},
    "HR_SERVICE_AIR_QUALITY_SENSOR_1_MIN": {"min": 0, "max": 3000, "d": 0, "u": "", "t": "ppm, 0.1 % or Pa, by the kind of sensor"},
    "HR_SERVICE_AIR_QUALITY_SENSOR_1_MAX": {"min": 0, "max": 3000, "d": 0, "u": "", "t": "ppm, 0.1 % or Pa, by the kind of sensor"},
    "HR_SERVICE_AIR_QUALITY_SENSOR_2_MIN": {"min": 0, "max": 3000, "d": 0, "u": "", "t": "ppm, 0.1 % or Pa, by the kind of sensor"},
    "HR_SERVICE_AIR_QUALITY_SENSOR_2_MAX": {"min": 0, "max": 3000, "d": 0, "u": "", "t": "ppm, 0.1 % or Pa, by the kind of sensor"},
    "IR_WORKING_HOURS": {"u": "h"},
    "IR_WORKING_DAYS": {"u": "d"},
    "IR_FILTERS_TIMER_DAYS_LEFT": {"u": "d"},
    "IR_TIME_TO_NEXT_SCHEDULER_EVENT_HOURS": {"u": "h"},
    "IR_TIME_TO_NEXT_SCHEDULER_EVENT_MINUTES": {"u": "min"},
    "IR_STANDBY_BLOCKING_TIME_LEFT_THIS_DAY": {"u": "min"},
    "IR_CURRENT_SUPPLY_AIR_FAN_OUTPUT": {"d": 2, "u": "V"},
    "IR_CURRENT_EXTRACT_AIR_FAN_OUTPUT": {"d": 2, "u": "V"},
    "IR_CURRENT_SUPPLY_AIR_DUCT_PRESSURE": {"d": 1, "u": "Pa", "t": "Ten times higher when the air pressure factor is 1"},
    "IR_CURRENT_EXTRACT_AIR_DUCT_PRESSURE": {"d": 1, "u": "Pa", "t": "Ten times higher when the air pressure factor is 1"},
    "IR_ROTOR_SPEED_RPM": {"u": "rpm"},
    "IR_POOL_FUNCTION_MODE": {"d": 1, "u": ""},
    "IR_TEMP_TRANSFER_EFFICIENCY": {"u": "%"},
    "IR_ACTIVE_ALARMS_COUNT": {"u": ""},
    "IR_SOFTWARE_VERSION": {"u": ""}, "IR_CONFIGURATION_VERSION": {"u": ""}, "IR_BOOTLOADER_VERSION": {"u": ""},
    "IR_EX1_MODULE": {"u": ""}, "IR_EX2_MODULE": {"u": ""}, "IR_COMUNICATION_MODULE": {"u": ""},
}
for _sensor in (
    "SUPPLY_AIR", "EXTRACT_AIR", "EXHAUST_AIR", "OUTDOOR_AIR", "HYDRONIC_HEATER_WATER", "HYDRONIC_PREHEATER_WATER",
    "HYDRONIC_COOLER_WATER", "CONTROL_BOX", "AFTER_HX",
):
    OVERRIDES[f"HR_SERVICE_{_sensor}_TEMPERATURE_SENSOR_TYPE"] = {"min": 0, "max": 5000, "o": None, "t": "0: none, 1: remote, 2: NTC 10K 3997, 2750–5000: the beta of another NTC"}
    OVERRIDES[f"HR_SENSORS_{_sensor}_TEMPERATURE_SENSOR_CORRECTION"] = {"min": -100, "max": 100, "d": 1, "u": "°C", "s": 1}
for _port in (1, 2):
    OVERRIDES[f"HR_SERVICE_Comunication_{_port}_SETTINGS"] = {"o": {0: "N,8,1", 1: "E,8,1", 2: "O,8,1", 3: "N,8,2", 4: "E,8,2", 5: "O,8,2"}}
for _fan in ("SUPPLY", "EXTRACT"):
    for _step in range(1, 5):
        OVERRIDES[f"HR_AIR_FLOW_{_step}_{_fan}"] = {"min": 0.1, "max": 100, "d": 1, "u": "%", "t": "Each step must be above the one before it"}
for _event in range(1, 11):
    OVERRIDES[f"HR_WEEKLY_SCHEDULER_EVENT_{_event}_SYSTEM_MODE"] = {"min": 0, "max": 100, "u": "", "t": "0–4: mode, above that: air flow in %"}
    OVERRIDES[f"HR_WEEKLY_SCHEDULER_EVENT_{_event}_TEMPERATURE"] = {"min": -0.1, "max": 30, "d": 1, "u": "°C", "s": 1, "o": None, "t": "-0.1: automatic, 0: energy saving, otherwise 16–30 °C"}
    OVERRIDES[f"HR_WEEKLY_SCHEDULER_EVENT_{_event}_WEEK_DAYS"] = {"min": 0, "max": 127, "u": "", "t": "Sum of the days: Monday 1, Tuesday 2, Wednesday 4, Thursday 8, Friday 16, Saturday 32, Sunday 64"}
for _mode in ("BUILDING_PROTECTION", "ECONOMY", "COMFORT"):
    OVERRIDES[f"HR_USER_CONFIG_{_mode}_MODE_RECIRCULATION_POSITION"] = {"min": -0.1, "max": 100, "d": 1, "u": "%", "s": 1, "o": None, "t": "-0.1: automatic"}

# holding registers by address: (section, ...)
HOLDING_SECTIONS = [
    ((1, 1), "operation"), ((2, 2), "temperature"), ((3, 3), "operation"), ((4, 6), "temperature"),
    ((7, 11), "digital_inputs"), ((12, 12), "fire"), ((14, 14), "operation"), ((15, 20), "season"),
    ((21, 24), "air_quality"), ((25, 32), "free_cooling"), ((33, 37), "pool"), ((38, 40), "dampers"),
    ((41, 41), "season"), ((202, 202), "system"), ((203, 205), "cooker_hood"), ((210, 249), "holidays"),
    ((250, 309), "week_schedule"), ((450, 464), "fans"), ((480, 491), "temp_sensors"), ((500, 523), "pid"),
    ((600, 611), "coils"), ((612, 620), "fan_hw"), ((621, 623), "recovery"), ((624, 625), "coils"),
    ((626, 641), "temp_sensors"), ((642, 646), "fire"), ((647, 649), "dampers"), ((650, 650), "pressure"),
    ((651, 651), "system"), ((652, 657), "analog_inputs"), ((658, 658), "coils"), ((659, 660), "system"),
    ((661, 664), "temperature"), ((665, 666), "coils"), ((667, 668), "system"), ((670, 671), "temperature"),
    ((672, 677), "fieldbus"), ((678, 678), "recovery"), ((679, 680), "air_quality"), ((681, 682), "fan_hw"),
    ((683, 683), "coils"), ((684, 694), "recovery"), ((695, 700), "analog_inputs"), ((701, 703), "coils"),
    ((704, 723), "pressure"), ((724, 724), "coils"), ((725, 726), "fan_hw"), ((727, 729), "coils"), ((730, 731), "dampers"), ((732, 736), "fire"),
    ((737, 737), "temperature"), ((738, 739), "coils"), ((740, 747), "fan_hw"), ((748, 748), "pressure"),
    ((749, 752), "coils"), ((753, 754), "temp_sensors"), ((755, 758), "coils"), ((759, 760), "temperature"),
    ((761, 761), "coils"),
]
COIL_SECTIONS = {
    1: "system", 3: "air_quality", 4: "free_cooling", 5: "operation", 6: "dampers", 7: "dampers", 8: "air_quality", 9: "pool",
    50: "fire", 51: "maintenance", 52: "maintenance", 53: "operation", 54: "maintenance",
    100: "digital_inputs", 101: "digital_inputs", 102: "digital_inputs", 103: "digital_inputs", 104: "digital_inputs",
    105: "digital_inputs", 106: "digital_inputs", 107: "digital_inputs", 108: "digital_inputs", 109: "digital_inputs",
    110: "digital_inputs", 111: "digital_inputs", 112: "digital_inputs", 113: "digital_inputs", 114: "digital_inputs",
    115: "digital_inputs", 116: "fan_hw", 117: "fan_hw", 118: "temp_sensors", 119: "fan_hw", 120: "fire", 121: "fire",
    122: "dampers", 123: "system", 124: "fire", 125: "system", 126: "recovery", 127: "recovery", 128: "analog_inputs",
    129: "fan_hw", 130: "digital_inputs", 131: "coils", 132: "dampers", 133: "system", 135: "coils",
    136: "digital_inputs", 137: "system", 138: "system", 139: "fieldbus", 140: "digital_inputs", 141: "pressure",
    142: "digital_inputs", 143: "digital_inputs", 144: "digital_inputs", 145: "fan_hw", 146: "fan_hw", 147: "dampers",
    148: "coils", 149: "coils", 150: "digital_inputs", 151: "digital_inputs", 152: "coils", 153: "digital_inputs",
    154: "recovery", 200: "maintenance",
}
INPUT_SECTIONS = [
    ((1, 1), "operation"), ((2, 3), "device"), ((4, 10), "system"), ((11, 12), "device"), ((13, 16), "operation"),
    ((17, 21), "temperature"), ((22, 25), "air"), ((26, 27), "schedule"), ((28, 30), "operation"), ((31, 31), "device"),
    ((32, 32), "air"), ((50, 52), "device"), ((55, 88), "fans"), ((89, 92), "coils"), ((93, 95), "temperature"),
    ((96, 97), "coils"), ((98, 101), "dampers"), ((102, 104), "temperature"), ((105, 105), "coils"),
    ((106, 111), "device"), ((112, 123), "air"), ((124, 125), "temperature"), ((126, 126), "dampers"),
    ((127, 127), "operation"), ((128, 128), "dampers"), ((129, 130), "air"), ((131, 132), "temperature"),
]

UNIT_PATTERNS = [
    (r"°\s*C", "°C"), (r"\bppm\b", "ppm"), (r"m3/h", "m³/h"), (r"(?<![A-Za-z])Pa\b", "Pa"), (r"\bVolts?\b", "V"), (r"\bRPM\b", "rpm"),
    (r"%", "%"), (r"\(seconds\)|\bsec\b|\bs$", "s"), (r"\(minutes\)|\bmin\.?", "min"), (r"\(days\)", "d"), (r"\d\s*h\b", "h"),
]


def in_ranges(address: int, ranges: list[tuple[int, int]]) -> bool:
    return any(low <= address <= high for low, high in ranges)


def section_of(address: int, table: list) -> str:
    for (low, high), section in table:
        if low <= address <= high:
            return section
    raise KeyError(address)


def name_of(define: str) -> str:
    """HR_USER_CONFIG_WINTER_START_MONTH -> Winter_Start_Month"""
    text = re.sub(r"^(HR|IR|COIL|DI|ALARM)_", "", define.strip())
    text = re.sub(r"^(USER_CONFIG|USER|SERVICE)_", "", text)
    return "_".join(part.capitalize() if not part.isdigit() else part for part in re.split(r"[_\s]+", text) if part)


def parse_options(text: str) -> dict[int, str]:
    """"0:None, 1:Electrical 0-10, 2:On/Off" and "(-1):Auto , 0:Off ,1:On" as a dict."""
    found = re.findall(r"\(?(-?\d+)\)?\s*[:.]\s*([^,;:]+?)\s*(?=[,;]\s*\(?-?\d+\)?\s*[:.]|[;,]?\s*$)", text)
    options = {int(key): value.strip() for key, value in found}
    return options if len(options) >= 2 else {}


def parse_values(text: str) -> dict:
    """What the Values column says: range, scale, unit and named values."""
    text = (text or "").replace("…", "..").replace(",", ",").strip()
    result: dict = {}
    scale = re.search(r"\*\s*0[.,](0?1)", text)
    decimals = len(scale[1]) if scale else 0
    span = re.search(r"\(?(-?\d+)\)?\s*(?:\.\.+|-|\s-\s)\s*\(?(-?\d+)\)?", text)
    if span and not re.match(r"\s*\(?-?\d+\)?\s*:", text):
        result["min"], result["max"] = int(span[1]) / 10**decimals, int(span[2]) / 10**decimals
    result["d"] = decimals
    result["u"] = next((unit for pattern, unit in UNIT_PATTERNS if re.search(pattern, text)), "")
    options = parse_options(text)
    if options and "min" not in result:
        result["o"] = options
    return result


def labels_of(define: str, english: str, missing: list[str]) -> dict[str, str]:
    found = LABELS.get(define)
    if found is None:
        missing.append(define)
        return {"en": english, "ru": english, "lv": english}
    return {"en": found[0] or english, "ru": found[1], "lv": found[2]}


def options_of(options: dict[int, str], missing: list[str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {"en": {}, "ru": {}, "lv": {}}
    for key, value in options.items():
        found = OPTIONS.get(value)
        if found is None:
            missing.append(f"option {value!r}")
            found = (value, value, value)
        out["en"][str(key)], out["ru"][str(key)], out["lv"][str(key)] = found[0] or value, found[1], found[2]
    return out


def rows(ws):
    """(define, address, name, values, default, level) of every register row of a sheet."""
    for row in ws.iter_rows(values_only=True):
        cells = list(row[1:]) + [None] * 6
        define, address, name = cells[0], cells[1], cells[2]
        if not isinstance(address, (int, float)) or not name or re.fullmatch(r"Reserve?r?d", str(name).strip()):
            continue
        yield str(define or "").strip(), int(address), str(name).strip(), str(cells[3] or ""), cells[4], str(cells[5] or "")


def main() -> None:
    warnings.filterwarnings("ignore")
    wb = openpyxl.load_workbook(Path(sys.argv[1]), data_only=True)
    missing: list[str] = []
    names: dict[str, str] = {}

    def unique(define: str, name: str) -> str:
        if name in names:
            raise SystemExit(f"{define} and {names[name]} both come out as {name}")
        names[name] = define
        return name

    setpoints: list[dict] = []
    for define, address, title, values, default, level in rows(wb["Holding registers"]):
        if not define or define in SKIP or in_ranges(address, SKIP_HOLDING):
            continue
        parsed = parse_values(values)
        parsed.update(OVERRIDES.get(define, {}))
        options = parsed.get("o")
        decimals = parsed.get("d", 0)
        low, high = parsed.get("min"), parsed.get("max")
        if options:
            low, high = min(options), max(options)
        if low is None:
            raise SystemExit(f"{define}: no range in {values!r}")
        kind = "button" if define in TRIGGERS else "select" if options else "number"
        if kind == "number" and (low, high) == (0, 1) and not parsed.get("u"):
            kind = "switch"
        if kind == "select" and set(options.values()) in ON_OFF:
            kind, options = "switch", None
        if kind == "button":
            options = None
        start = default if isinstance(default, (int, float)) else 0
        entry = {
            "n": unique(define, ALIASES.get(define) or name_of(define)),
            "a": address,
            "s": 1 if parsed.get("s") or low < 0 or start < 0 else 0,
            "d": decimals,
            "u": "" if kind != "number" else parsed.get("u", ""),
            "min": low,
            "max": high,
            "def": start if options else start / 10**decimals,
            "k": kind,
            "sec": section_of(address, HOLDING_SECTIONS),
            "lvl": LEVELS.get(level.strip().lower(), "service"),
            "mem": "ram" if kind == "button" else "eeprom",
            "l": labels_of(define, title, missing),
            "tb": HOLDING,
        }
        if define in DANGER:
            entry["danger"] = 1
        if kind == "button":
            entry["cmd"] = 1
        if options:
            entry["o"] = options_of(options, missing)
        if parsed.get("t"):
            entry["t"] = parsed["t"]
        setpoints.append(entry)

    for define, address, title, values, default, level in rows(wb["Coils"]):
        if define in SKIP or in_ranges(address, SKIP_COILS):
            continue
        options = COIL_OPTIONS.get(define) or parse_options(values)
        plain = set(options.values()) in ON_OFF or set(options.values()) == {"Nothing", "Activate"}
        kind = "button" if define in TRIGGERS else "switch" if plain else "select"
        entry = {
            "n": unique(define, ALIASES.get(define) or name_of(define) + ("_Contact" if set(options.values()) == {"NO", "NC"} else "")),
            "a": address,
            "s": 0,
            "d": 0,
            "u": "",
            "min": 0,
            "max": 1,
            "def": int(default or 0),
            "k": kind,
            "sec": COIL_SECTIONS[address],
            "lvl": LEVELS.get(level.strip().lower(), "service"),
            "mem": "ram" if kind == "button" else "eeprom",
            "l": labels_of(define, title, missing),
            "tb": COIL,
        }
        if define in DANGER:
            entry["danger"] = 1
        if kind == "button":
            entry["cmd"] = 1
        if kind == "select":
            entry["o"] = options_of(options, missing)
        setpoints.append(entry)

    datapoints: list[dict] = []
    seen: dict[str, int] = {}
    for define, address, title, values, level, _ in rows(wb["Input register"]):
        seen[define] = seen.get(define, 0) + 1
        key = f"{define}@{address}" if f"{define}@{address}" in ALIASES else define
        if define == "IR_CURRENT_EXTRACT_AIR_FLOW" and key == define:
            raise SystemExit("the two extract air flow registers have changed places")
        parsed = parse_values(values if "Value*0,1" not in values else "*0,1 °C")
        if re.search(r"Value\*0,1\s*°C", values):
            parsed.update(d=1, u="°C")
        parsed.update(OVERRIDES.get(define, {}))
        signed = parsed.get("u") == "°C"
        entry = {
            "n": unique(key, ALIASES.get(key) or name_of(define)),
            "a": address,
            "s": 1 if signed else 0,
            "d": parsed.get("d", 0),
            "u": parsed.get("u", ""),
            "sec": section_of(address, INPUT_SECTIONS),
            "l": labels_of(key, title, missing),
            "tb": INPUT,
        }
        if define == "IR_CURRENT_SYSTEM_STATE":
            entry["o"] = {lang: {str(k): v[i] for k, v in STATES.items()} for i, lang in enumerate(("en", "ru", "lv"))}
        elif define == "IR_CURRENT_SYSTEM_MODE":
            entry["o"] = options_of({0: "Standby", 1: "Building protection", 2: "Economy", 3: "Comfort", 4: "Boost"}, missing)
        elif define == "IR_ACTIVE_ACCESS_LEVEL":
            entry["o"] = options_of({0: "User", 1: "Adjuster", 2: "Service"}, missing)
        if define in HIDDEN or define in CLOCK:
            entry["hidden"] = 1
        if parsed.get("t"):
            entry["t"] = parsed["t"]
        datapoints.append(entry)

    faults: dict[str, dict[str, str]] = {}
    for row in wb["Discrete inputs"].iter_rows(values_only=True):
        define, address, title = str(row[1] or "").strip(), row[2], str(row[3] or "").strip()
        if not isinstance(address, (int, float)) or not title or re.fullmatch(r"Reserve?r?d", title):
            continue
        address = int(address)
        if define in SKIP or in_ranges(address, SKIP_DISCRETE):
            continue
        entry = {"a": address, "s": 0, "d": 0, "u": "", "tb": DISCRETE}
        severity = re.match(r"(Warning|Alarm)!", title)
        if address < 188 and severity:
            # the last rows of the alarm list have a message but no name
            define = define or UNNAMED_ALARMS[address]
            code = f"{severity[1][0]}.{address:02d}"
            name = unique(define, f"{severity[1][0]}{address:02d}_{name_of(define)}")
            en, ru, lv = ALARMS[address]
            faults[name] = {"en": f"{code} {en}", "ru": f"{code} {ru}", "lv": f"{code} {lv}"}
            entry.update(n=name, sec="operation", hidden=1, fault=severity[1].lower(), l=faults[name])
        else:
            key = ALIASES.get(define)
            prefix = "State_" if address >= 300 else "" if key or address < 188 else "Status_"
            entry.update(
                n=unique(define, key or prefix + name_of(define)),
                sec="inputs" if address >= 300 else "dampers" if address < 188 else "operation",
                flag=1,
                l=labels_of(define, title, missing),
            )
        datapoints.append(entry)
    if missing:
        print("no translation:", *sorted(set(missing)), sep="\n  ")
    data = {
        "version": 1,
        "model": "nest",
        "dp": sorted(datapoints, key=lambda r: (r["tb"], r["a"])),
        "sp": sorted(setpoints, key=lambda r: (r["tb"], r["a"])),
        "faults": faults,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(datapoints)} data points, {len(setpoints)} setpoints, {len(faults)} faults, {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
