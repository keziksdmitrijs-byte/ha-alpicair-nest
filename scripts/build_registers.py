#!/usr/bin/env python3
"""Build custom_components/alpicair_nest/registers.json from the manufacturer's data point workbook.

Usage: build_registers.py <Set_Data_Points_*.xlsm>

The workbook itself is not part of this repository. Anything that is no business of a home
automation (encryption keys, pairing data, factory flash records, PIN codes, output overrides)
is left out here, so it never reaches the integration.
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from labels import english, russian

OUT = Path(__file__).parent.parent / "custom_components" / "alpicair_nest" / "registers.json"

UNITS = {
    "None": "", "Temp": "°C", "Pa": "Pa", "ms": "ms", "%": "%", "Volt": "V", "Sec": "s", "OnOff": "",
    "ppm": "ppm", "bar": "bar", "user": "", "Monate": "mo", "min": "min", "rpm": "rpm", "hour": "h",
    "A": "A", "Binary": "", "m3h": "m³/h", "weekday": "d", "YesNo": "", "Hour x 2": "h",
}
ON_OFF_UNITS = {"OnOff", "YesNo"}

# setpoint groups that are left out completely, they are never read
SKIP_GROUPS = {"Bluetooth", "Nabto", "Overrides", "Modbus_BT"}
SKIP_NAMES = {
    "AccessLevelCode", "DisableErrorDetect", "ServiceLock", "DisplayLock", "DisplayLock_Enable",
    "DisplayVersion", "FireProtection_ConfirmNotUsed", "LastOperatingMode_Persistent",
    "Filter_RuntimeMinutes_Lo", "Filter_RuntimeMinutes_Hi", "RunningTime_Hours_1x", "RunningTime_Hours_10000x",
    "Config_ID",
}
KEEP_MAINTENANCE = {
    "RestartUnit", "ResetEventLog", "Create_FactoryRestorePoint", "Restore_FactoryRestorePoint",
    "Create_UserRestorePoint", "Restore_UserRestorePoint",
}
# the data points of the factory group that mean something to a user
KEEP_DP_LSC = {
    "Pressure_1_CommValidCount", "Pressure_2_CommValidCount", "Event_log_number", "Panel_Comm_Error",
    "FirmwareVerMain", "FirmwareVerBootloader", "WriteToEepromCounter", "LAN_State", "BT_Version", "BT_Status",
    "BT_ErrorStatus", "RestorePoint_Status", "RestorePoint_Progress",
}

# writing one of these does something once, they are buttons
TRIGGERS = {
    "Filter_Reset": 1, "ResetErrors": 1, "TimeSync_PerformSyncNow": 1, "Bypass_CalibrationTrigger": 1,
    "Bypass_PositionRetry": 1, "FireDamper_TestStart": 1, "CH_ResetFilterTimer": 1, "CH_DamperCmd": 1,
    "RestartUnit": 11223, "ResetEventLog": 1, "Create_FactoryRestorePoint": 1, "Restore_FactoryRestorePoint": 1,
    "Create_UserRestorePoint": 1, "Restore_UserRestorePoint": 1,
}

# where each setpoint group shows in the panel, and who may change it there:
# user: everybody, adjuster: administrators, service: administrators with the service PIN
SECTIONS = {
    "Operation": ("operation", "user"),
    "TemperatureControl": ("temperature", "user"),
    "AirQualityControl": ("air_quality", "user"),
    "FreeCoolingControl": ("free_cooling", "user"),
    "FanControl": ("fans", "adjuster"),
    "TemporaryMode": ("temporary", "adjuster"),
    "CookerHood": ("cooker_hood", "adjuster"),
    "TimeKeeping": ("time", "user"),
    "Scheduler": ("schedule", "user"),
    "System": ("system", "user"),
    "Fan1": ("fan_hw", "service"),
    "Fan2": ("fan_hw", "service"),
    "TemperatureSensors": ("temp_sensors", "service"),
    "PressureSensors": ("pressure", "service"),
    "AnalogInputs": ("analog_inputs", "service"),
    "DigitalInputs": ("digital_inputs", "service"),
    "Dampers": ("dampers", "service"),
    "FireProtection": ("fire", "service"),
    "CoilControl": ("coils", "service"),
    "Preheater": ("coils", "service"),
    "ElectricHeater": ("coils", "service"),
    "CombinedCoil": ("coils", "service"),
    "EnergyRecoveryControl": ("recovery", "service"),
    "BypassDamper": ("recovery", "service"),
    "Modbus_TCP": ("network", "service"),
    "Modbus_HMI": ("fieldbus", "service"),
    "Modbus_RTU1": ("fieldbus", "service"),
    "Modbus_RTU2_Slave": ("fieldbus", "service"),
    "Modbus_RTU2_Master": ("fieldbus", "service"),
    "LSC": ("maintenance", "service"),
}
DP_SECTIONS = {
    "Fans": "fans", "Temperature": "temperature", "AirControl": "air", "Coils & Preheater": "coils",
    "AI & DI": "inputs", "Dampers & FireProt": "dampers", "Operation": "operation", "Scheduler": "schedule",
    "TemporaryMode": "temporary", "System": "system", "LSC": "device",
}
# things the group's level is too low or too high for
LEVELS = {
    "AirTemp_ControlStrategy": "service",
    "AirTemp_MinAllowedSetpoint": "adjuster",
    "AirTemp_MaxAllowedSetpoint": "adjuster",
    "SystemStabilisingTime_StandbyToActive": "service",
    "UnitConfiguration": "service",
    "Bluetooth_OnOff": "adjuster",
    "DisplayLanguage": "adjuster",
    "Filter_Reset": "user",
    "ResetErrors": "user",
    "Timezone": "adjuster",
    "DST_State": "adjuster",
}
PID_PATTERN = re.compile(r"(_Coeff_[PID]|PIDRegulatingInterval|PIDSamplingRate)$")
# writing these can cost the connection or stop the unit: the panel asks first
DANGER_GROUPS = {"Modbus_TCP", "Modbus_HMI", "Modbus_RTU1", "Modbus_RTU2_Slave", "Modbus_RTU2_Master"}
DANGER_NAMES = {"RestartUnit", "Restore_FactoryRestorePoint", "Restore_UserRestorePoint", "Create_FactoryRestorePoint", "ResetEventLog", "Bypass_CalibrationTrigger"}

OPTION_RU = {
    "Tacho": "Тахометр", "Thermo": "Термоконтакт", "NO": "Нормально разомкнут", "NC": "Нормально замкнут",
    "Only warning": "Только предупреждение", "alarm + shutdown": "Авария и остановка",
    "stop functionality tied to sensor + warning & continue": "Отключить связанную функцию и продолжить",
    "MA": "Скользящее среднее", "EMA": "Экспоненциальное среднее", "+/- Ratelimiter": "Ограничитель скорости",
    "None": "Нет", "Extract RH": "Влажность вытяжки", "Extract CO2": "CO₂ вытяжки", "Supply RH": "Влажность притока",
    "VOC": "VOC", "Supply Pressure": "Давление притока", "Extract Pressure": "Давление вытяжки",
    "0-10V Ext. Fancontrol": "Внешнее управление 0–10 В", "OFF": "Выключено", "System Mode": "Режим установки",
    "Fan Speed": "Скорость вентиляторов", "Kitchen Hood": "Кухонная вытяжка", "User Interface Button": "Кнопка интерфейса",
    "BypassDamper": "Заслонка байпаса", "KitchenHood": "Кухонная вытяжка", "Disabled": "Отключено",
    "Outside Damper": "Наружная заслонка", "Fire Damper": "Огнезадерживающий клапан", "Spring-return": "С пружинным возвратом",
    "Open/Close": "Открыть/закрыть", "Preheater": "Преднагреватель", "Electric Heater": "Электронагреватель",
    "0-10V": "0–10 В", "Slow PWM": "Медленный ШИМ", "Test": "Тест", "Manual": "Вручную", "Outdoor": "По наружной температуре",
    "Calendar": "По календарю", "WaterTemp": "По температуре воды", "DI": "По цифровому входу", "Heating": "Нагрев",
    "Cooling": "Охлаждение", "Rotary": "Роторный", "Passive": "Пластинчатый", "SlowPWM": "Медленный ШИМ", "On/Off": "Вкл/выкл",
    "On/Off with AI": "Вкл/выкл с аналоговым входом", "Exhaust sensor": "Датчик выброса", "Outdoor sensor": "Наружный датчик",
    "Standby": "Ожидание", "Unoccupied": "Никого нет", "Economy": "Эконом", "Comfort": "Комфорт", "Boost": "Буст",
    "Continuous": "Постоянный", "EdgeTriggered": "Импульсный", "Linear": "Постоянная скорость", "Constant flow": "Постоянный расход",
    "Constant pressure": "Постоянное давление", "External 0-10V": "Внешние 0–10 В", "Both Sensors": "Оба датчика",
    "Supply Sensor": "Датчик притока", "Exhaust Sensor": "Датчик вытяжки", "Supply Master": "Ведущий приток",
    "Exhaust Master": "Ведущая вытяжка", "Auto": "Авто", "SupplyControl": "Приточному воздуху", "ExtractControl": "Вытяжному воздуху",
    "No Component": "Нет", "Combined Coil": "Комбинированный калорифер", "Fans": "Вентиляторы", "Electric Coil": "Электрокалорифер",
    "Metric": "Метрическая", "Imperial": "Имперская", "dynamic": "Автоматически (DHCP)", "static": "Статический",
    "EN": "English", "LT": "Lietuvių", "Master": "Ведущий", "Slave": "Ведомый", "NONE": "Нет", "ODD": "Нечётная", "EVEN": "Чётная",
    "1 stopbits": "1 стоповый бит", "2 stopbits": "2 стоповых бита", "Temporary": "Временно", "Event Off": "Отключено",
    "Only switch on event": "Только переключение по событию", "Override": "Блокировать ручной режим",
    "heating": "Нагрев", "passive/ERC": "Рекуперация", "cooling": "Охлаждение", "heating/recovery": "Нагрев/рекуперация",
    "cooling/free-cooling": "Охлаждение/свободное охлаждение", "cooling/free-coolin": "Охлаждение/свободное охлаждение",
    "off": "Выключено", "0-10 V": "0–10 В", "slow PWM": "Медленный ШИМ", "none": "Нет", "open": "Открыта", "close": "Закрыта",
    "disabled": "Отключена", "closed": "Закрыта", "opening": "Открывается", "closing": "Закрывается", "OK open": "Открыт, норма",
    "OK closed": "Закрыт, норма", "fire active": "Пожарная тревога", "test running": "Идёт тест", "damper fault": "Неисправность",
    "idle": "Ожидание", "running": "Выполняется", "pass": "Успешно", "fail": "Ошибка", "stop": "Стоп", "CW": "По часовой",
    "CCW": "Против часовой", "no end stop currently recorded": "Концевик не достигнут", "CW endstop reached": "Концевик по часовой",
    "CCW endstop reached": "Концевик против часовой", "inactive": "Не активно", "moving": "Движется", "settling": "Успокоение",
    "holding within tolerance": "Удержание", "correction limit reached": "Предел коррекций", "Not performed": "Не выполнялась",
    "In progress": "Выполняется", "Success": "Успешно", "Failed": "Ошибка", "Idle": "Ожидание", "Busy": "Выполняется",
    "Snapshot unavailable": "Нет снимка", "Error": "Ошибка", "system mode": "Режим установки", "fan speed": "Скорость", "kitchen hood": "Кухонная вытяжка",
    "activated": "Активирован", "deactivated": "Деактивирован", "Mon": "Пн", "Tue": "Вт", "Wed": "Ср", "Thu": "Чт", "Fri": "Пт", "Sat": "Сб", "Sun": "Вс",
    "ClosedIsCooling": "Замкнут: охлаждение", "ClosedIsHeating": "Замкнут: нагрев", "DST Applied": "Применено", "DST Off": "Не применено",
    "No pressure sensors connected": "Датчиков давления нет", "Pressure sensors connected": "Датчики давления есть", "Off": "Выключено",
    "On": "Включено", "invalid": "Нет", "valid": "Да",
    "Mo": "Пн", "Tu": "Вт", "We": "Ср", "Th": "Чт", "Fr": "Пт", "Sa": "Сб", "Su": "Вс", "ON": "Вкл", "1200": "1200",
}

FAULT_RU = {
    "Fan1_FeedbackError": "Нет сигнала от приточного вентилятора",
    "Fan2_FeedbackError": "Нет сигнала от вытяжного вентилятора",
    "AI1_OutOfRange": "Аналоговый вход 1 вне диапазона",
    "AI2_OutOfRange": "Аналоговый вход 2 вне диапазона",
    "AI3_OutOfRange": "Аналоговый вход 3 вне диапазона",
    "AirTemp_ERC_Passive_BypassCalibrationNotPerformed": "Калибровка байпаса не выполнена",
    "AirTemp_ERC_Passive_BypassCalibrationFailed": "Ошибка калибровки байпаса",
    "ERC_Rotary_EfficiencyAlarm": "Низкая эффективность ротора",
    "Preheater_Overheat": "Перегрев преднагревателя",
    "ElectricHeater_Overheat": "Перегрев электронагревателя",
    "Coil2_CombinedCoil_Thermoprot_Active": "Сработала термозащита калорифера",
    "ConfigCheck_MissingIO": "Конфигурация: не хватает входов или выходов",
    "Filter_Clogged_PreWarning": "Скоро менять фильтр",
    "Filter_Clogged_Warning": "Пора менять фильтр",
    "FireProtection_Active": "Сработала пожарная защита",
    "FireDamper_TestFailed": "Тест огнезадерживающих клапанов не пройден",
    "FireDamper1_Fault": "Неисправен огнезадерживающий клапан 1",
    "FireDamper2_Fault": "Неисправен огнезадерживающий клапан 2",
    "Pressure1_AboveLimit": "Давление 1 выше предела",
    "Pressure2_AboveLimit": "Давление 2 выше предела",
    "Pressure1_BelowLimit": "Давление 1 ниже предела",
    "Pressure2_BelowLimit": "Давление 2 ниже предела",
    "Temp_Supply_AboveLimit": "Температура притока выше предела",
    "Temp_Outdoor_AboveLimit": "Наружная температура выше предела",
    "Temp_Extract_AboveLimit": "Температура вытяжки выше предела",
    "Temp_Exhaust_AboveLimit": "Температура выброса выше предела",
    "Temp_ReturnWater_AboveLimit": "Температура обратной воды выше предела",
    "Temp_Supply_BelowLimit": "Температура притока ниже предела",
    "Temp_Outdoor_BelowLimit": "Наружная температура ниже предела",
    "Temp_Extract_BelowLimit": "Температура вытяжки ниже предела",
    "Temp_Exhaust_BelowLimit": "Температура выброса ниже предела",
    "Temp_ReturnWater_BelowLimit": "Температура обратной воды ниже предела",
    "Fan1_TachoAboveLimit": "Обороты приточного вентилятора выше предела",
    "Fan2_TachoAboveLimit": "Обороты вытяжного вентилятора выше предела",
    "Fan1_TachoBelowLimit": "Обороты приточного вентилятора ниже предела",
    "Fan2_TachoBelowLimit": "Обороты вытяжного вентилятора ниже предела",
}


def clean_description(text: str | None) -> str:
    text = (text or "").strip()
    # the table names the maker of the controller; the unit is sold under its own brand
    text = re.sub(r"\bS[a]lda[- ]?", "", text).replace("specified configuration", "Configuration")
    return text.replace("otal heating", "Total heating") if text.startswith("otal") else text


def parse_options(*texts: str | None) -> dict[int, str]:
    """"0 = Tacho, 1 = Thermo" as a dict; also understands "0=1200 , 1=2400"."""
    for text in texts:
        if not text or "=" not in text:
            continue
        found = re.findall(r"(\d+)\s*=\s*([^,=()]+?)(?=\s*(?:,|\s\d+\s*=|\)|$))", text)
        if len(found) >= 2:
            return {int(k): re.sub(r"\.\s*Read-only$", "", v.strip()).rstrip(".") for k, v in found}
    return {}


def option_ru(value: str) -> str:
    return OPTION_RU.get(value, value)


def load(path: Path):
    warnings.filterwarnings("ignore")
    wb = openpyxl.load_workbook(path, data_only=True)
    return wb["Setpoints"], wb["Datapoints"]


def rows_of(ws):
    header = [c.value for c in ws[1]]
    first = {h: i for i, h in reversed(list(enumerate(header))) if h}
    for row in ws.iter_rows(min_row=2, values_only=True):
        yield {h: row[i] for h, i in first.items()}, row, header


def main() -> None:
    sp_ws, dp_ws = load(Path(sys.argv[1]))
    missing: list[str] = []

    def label(name: str) -> dict[str, str]:
        ru = russian(name)
        if ru is None:
            missing.append(name)
            ru = english(name)
        return {"en": english(name), "ru": ru}

    setpoints = []
    group = None
    for row, raw, header in rows_of(sp_ws):
        group = row["Group"] or group
        name = row["Setpoint Name"]
        address = row["Modbus Address"]
        if not name or str(name).startswith("Spare") or address is None or group in SKIP_GROUPS:
            continue
        if name in SKIP_NAMES:
            continue
        if group == "Scheduler" and re.match(r"(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day_E", name):
            continue
        if group == "Scheduler" and name.startswith("EventCopy"):
            continue
        if group == "LSC" and name not in KEEP_MAINTENANCE:
            continue
        if group.startswith("Modbus_") and name in {"Address", "BaudRate", "Parity", "Stopbits"}:
            name = f"{group}_{name}"
        section, level = SECTIONS[group]
        mins = [i for i, h in enumerate(header) if h == "Min"]
        maxs = [i for i, h in enumerate(header) if h == "Max"]
        decimals = int(row["Decimals"] or 0)
        scale = 10**decimals
        raw_min, raw_max = raw[mins[1]], raw[maxs[1]]
        unit_key = row["Unit"] or "None"
        options = parse_options(row["Description"], row["Datalog Name"])
        if name in {"ModbusTCP_ONOFF"}:
            options = {}
        kind = "number"
        if name in TRIGGERS:
            kind = "button"
        elif options:
            kind = "select"
        elif raw_min == 0 and raw_max == 1:
            kind = "switch"
        wm = row["EEPROM WriteMode"]
        writable = wm not in ("Write disabled ", "Write disabled", "Write Disabled, Only In RAM")
        entry = {
            "n": name,
            "a": address,
            "s": 1 if row["Type"] == "int16_t" else 0,
            "d": decimals,
            "u": "" if kind in ("switch", "select", "button") else UNITS.get(unit_key, ""),
            "min": raw_min / scale,
            "max": raw_max / scale,
            "def": raw[header.index("Default Value")] / scale if isinstance(raw[header.index("Default Value")], (int, float)) else 0,
            "k": kind,
            "sec": section,
            "lvl": LEVELS.get(name) or ("service" if PID_PATTERN.search(name) else level),
            "mem": "eeprom" if wm == "EEPROM+RAM" else "ram" if wm == "Only In RAM" else "clock" if wm == "Write Ram And Clock" else "ro",
            "l": label(name),
        }
        if not writable:
            entry["ro"] = 1
        if group in DANGER_GROUPS or name in DANGER_NAMES:
            entry["danger"] = 1
        if name in TRIGGERS:
            entry["cmd"] = TRIGGERS[name]
        if options:
            entry["o"] = {"en": {str(k): v for k, v in options.items()}, "ru": {str(k): option_ru(v) for k, v in options.items()}}
        description = clean_description(row["Description"])
        if description and not options:
            entry["t"] = description
        setpoints.append(entry)

    datapoints = []
    faults: dict[str, dict] = {}
    group = None
    for row, raw, header in rows_of(dp_ws):
        group = row["Group"] or group
        name = row["Datapoint Name"]
        if not name or str(name).startswith("Spare"):
            continue
        name = name.strip()
        address = row["Modbus Address"]
        bits = row["Binary Enumerator"]
        status = re.match(r"(Error|Warning|Alarm)Status([1-4])$", name)
        if status:
            # the list runs from the highest bit down to bit 0
            names = str(bits or "").split(",")
            mapping = {}
            for i, bit_name in enumerate(reversed(names)):
                if bit_name:
                    mapping[str(i)] = bit_name
                    faults.setdefault(bit_name, {"en": english(bit_name), "ru": FAULT_RU.get(bit_name, english(bit_name))})
            datapoints.append({"n": name, "a": address, "s": 0, "d": 0, "u": "", "sec": "operation", "hidden": 1, "bits": mapping, "fault": status[1].lower(), "l": label(name)})
            continue
        if re.match(r"(Raw_AD_|LAN_(MAC|IP|Gateway|Netmask|DNS)|BT_MAC|ELT_Status)", name):
            datapoints.append({"n": name, "a": address, "s": 0, "d": 0, "u": "", "sec": "device", "hidden": 1, "l": {"en": name, "ru": name}})
            continue
        if group == "LSC" and name not in KEEP_DP_LSC:
            continue
        decimals = int(row["Decimals"] or 0)
        unit_key = row["Unit"] or "None"
        options = parse_options(row["Description"], row["Datalog Name"])
        description = clean_description(row["Description"])
        if name in ("CurrentOperatingMode", "CurrentBaseOperatingMode", "Scheduler_ActiveScheduledMode"):
            options = {0: "Standby", 1: "Unoccupied", 2: "Economy", 3: "Comfort", 4: "Boost", 5: "Kitchen Hood"}
        if name == "Scheduler_ActiveScheduledMode":
            options = {0: "Event Off", 1: "Standby", 2: "Unoccupied", 3: "Economy", 4: "Comfort", 5: "Boost"}
        entry = {
            "n": name,
            "a": address,
            "s": 1 if row["Type"] == "int16_t" else 0,
            "d": decimals,
            "u": UNITS.get(unit_key, ""),
            "sec": DP_SECTIONS[group],
            "l": label(name),
        }
        is_flag = unit_key in ON_OFF_UNITS or bool(re.search(r"(ActiveOrNot|_Active$|Active_|ExchangerActive$|FansActive$|_Detected|Expired|IsOpen|IsClosed|_Cond_|Feedback|ThermoProtection|Relay_State|Normalized|^DI[12]$|^FireProtection$|^FireDamper[12]_(Open|Close)$)", name)) or name in ("AnyErrorActive", "AnyWarningActive", "AirTemp_Season_CurrentIsWinter")
        if options and len(options) >= 2:
            entry["o"] = {"en": {str(k): v for k, v in options.items()}, "ru": {str(k): option_ru(v) for k, v in options.items()}}
        elif is_flag:
            entry["flag"] = 1
        if description and not options:
            entry["t"] = description
        if name == "Filter_RemainingDays":
            entry["u"] = "d"
        # 0-1000 with one decimal is a percentage, though the table gives no unit
        if decimals == 1 and not entry["u"] and (name.endswith(("HeatingDemand", "PassiveDemand", "CoolingDemand")) or "0-1000" in (description or "")):
            entry["u"] = "%"
        if name.startswith("BypassDamper_Current_mA"):
            entry["u"] = "mA"
        if re.search(r"_s$|TimerVal$", name):
            entry["u"] = "s"
        datapoints.append(entry)

    if missing:
        print("no Russian name:", *missing, sep="\n  ")
    data = {
        "version": 1,
        "dp": sorted(datapoints, key=lambda r: r["a"]),
        "sp": sorted(setpoints, key=lambda r: r["a"]),
        "faults": faults,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=False) + "\n", encoding="utf-8")
    print(f"{len(datapoints)} data points, {len(setpoints)} setpoints, {len(faults)} faults, {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
