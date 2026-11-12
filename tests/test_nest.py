"""The NEST (MCB controller): its own table, coils and discrete inputs, and the same entities and panel API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.alpicair_nest.client import ModbusClient
from custom_components.alpicair_nest.const import DOMAIN, EVENT_FAULT
from custom_components.alpicair_nest.diagnostics import async_get_config_entry_diagnostics
from custom_components.alpicair_nest.discovery import async_probe, format_serial

from .conftest import NEST_SERIAL
from .simulator import TEST_PIN, Simulator

TABLE = Path(__file__).parent.parent / "custom_components" / "alpicair_nest" / "registers_nest.json"
LS_TABLE = TABLE.with_name("registers.json")


async def _ask(client, command: str, **fields):
    await client.send_json_auto_id({"type": f"{DOMAIN}/{command}", **fields})
    return await client.receive_json()


async def _poll(hass, entry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


@pytest.fixture
async def admin(hass, hass_ws_client, nest_loaded):
    return await hass_ws_client(hass)


# the table


def test_table_has_no_secrets() -> None:
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    holding = {r["a"] for r in table["sp"] if r["tb"] == "h"}
    # passwords, forced outputs, values a building management system writes, factory functions, the I/O map
    assert not holding & {198, 199}
    assert not holding & set(range(400, 436))
    assert not holding & set(range(800, 998))
    assert "password" not in TABLE.read_text(encoding="utf-8").lower()


def test_table_is_consistent() -> None:
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    names = [r["n"] for r in table["sp"]] + [r["n"] for r in table["dp"]]
    assert len(names) == len(set(names))
    for kind in ("sp", "dp"):
        places = [(r["tb"], r["a"]) for r in table[kind]]
        assert len(places) == len(set(places))
    for register in table["sp"]:
        assert register["tb"] in ("h", "c")
        assert register["min"] <= register["max"], register["n"]
        assert register["min"] <= register["def"] <= register["max"] or register["sec"] in ("holidays", "week_schedule")
        assert register["k"] in ("number", "select", "switch", "button")
        if register["k"] == "select":
            assert len(register["o"]["ru"]) >= 2, register["n"]
        if register["tb"] == "c":
            assert register["k"] != "number", register["n"]
    for register in table["sp"] + table["dp"]:
        for language in ("en", "ru", "lv"):
            assert register["l"][language], register["n"]
    for register in table["dp"]:
        assert register["tb"] in ("i", "d")
        if register.get("fault"):
            assert register["n"] in table["faults"]


def test_everything_is_named_in_three_languages() -> None:
    """A name the translation missed comes out in English: only codes and numbers may look the same."""
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    same = [r["n"] for r in table["sp"] + table["dp"] if r["l"]["ru"] == r["l"]["en"] or r["l"]["lv"] == r["l"]["en"]]
    assert same == ["BoostMode_Active"]


def test_shared_registers_have_the_names_of_the_nest_ls() -> None:
    """What the panels and the entities ask for by name is in both tables."""
    nest = json.loads(TABLE.read_text(encoding="utf-8"))
    ls = json.loads(LS_TABLE.read_text(encoding="utf-8"))
    shared_dp = {
        "T_Supply", "T_Extract", "T_Exhaust", "T_Outdoor", "Fan1_RPM", "Fan2_RPM", "Fan1_Output", "Fan2_Output",
        "Airflow_Supply", "Airflow_Exhaust", "Filter_RemainingDays", "CurrentOperatingMode", "AnyErrorActive",
        "AnyWarningActive", "AI_ExtractAirHumidity", "AI_ExtractAirCO2", "AI_SupplyAirHumidity", "FirmwareVerMain",
        "AirTemp_SupplyControl_PresentSetpoint", "AirTemp_ERC_Passive_BypassPosition", "AirTemp_ERC_Rotary_Speed",
    }  # fmt: skip
    shared_sp = {
        "OperatingMode", "AirTemp_SupplyTarget_Comfort", "AirTemp_SupplyTarget_Economy", "ResetErrors", "Filter_Reset",
        "AirTemp_SupplyTarget_Unoccupied", "Filter_TimerPeriod_Days", "AirTemp_ControlStrategy", "FreeCooling_Enable",
        "Linear_Fan1_Fanspeed_Comfort", "Linear_Fan2_Fanspeed_Boost", "RestartUnit",
    }  # fmt: skip
    for table in (nest, ls):
        assert shared_dp <= {r["n"] for r in table["dp"]}
        assert shared_sp <= {r["n"] for r in table["sp"]}
    by_name = {r["n"]: r for r in nest["dp"]}
    for name in ("T_Supply", "Fan1_Output", "AirTemp_ERC_Passive_BypassPosition"):
        theirs = next(r for r in ls["dp"] if r["n"] == name)
        assert (by_name[name]["d"], by_name[name]["u"]) == (theirs["d"], theirs["u"])


def test_serial() -> None:
    assert format_serial([12, 3456, 0, 0, 7]) == NEST_SERIAL
    assert format_serial([0, 0, 0, 0, 0]) is None
    assert format_serial([1, 2]) is None


# the client


@pytest.mark.parametrize("framing", ["tcp", "rtu"])
async def test_coils_and_discrete_inputs(socket_enabled, framing: str) -> None:
    unit = Simulator(framing=framing, model="nest")
    unit.discrete.update({1: 1, 9: 1, 14: 1})
    await unit.start()
    client = ModbusClient("127.0.0.1", unit.port, 1, framing)
    assert await client.read_discrete(1, 16) == [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0]
    assert await client.read_coils(3, 3) == [0, 0, 0]
    await client.write_coil(4, True)
    assert await client.read_coils(3, 3) == [0, 1, 0]
    await client.write_coil(4, False)
    assert unit.coil_writes == [(4, 1), (4, 0)]
    await client.close()
    await unit.stop()


async def test_probe_tells_the_models_apart(socket_enabled) -> None:
    nest, ls = Simulator(model="nest"), Simulator()
    await nest.start()
    await ls.start()
    found = await async_probe("127.0.0.1", nest.port, model="nest")
    assert found is not None and found.matched
    assert (found.model, found.serial, found.firmware, found.mac) == ("nest", NEST_SERIAL, 127, None)
    assert found.unique_id == NEST_SERIAL
    wrong = await async_probe("127.0.0.1", nest.port, model="nest_ls")
    assert wrong is None or not wrong.matched
    wrong = await async_probe("127.0.0.1", ls.port, model="nest")
    assert wrong is None or not wrong.matched
    await nest.stop()
    await ls.stop()


# adding one


async def test_flow_adds_a_nest(hass, nest_unit) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["menu_options"] == ["nest", "nest_ls"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "nest"})
    assert result["step_id"] == "method"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "manual"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": nest_unit.port}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "AlpicAir NEST (127.0.0.1)"
    assert result["data"]["model"] == "nest"
    assert result["result"].unique_id == NEST_SERIAL
    await hass.async_block_till_done()
    assert hass.states.get("climate.alpicair_nest") is not None
    await hass.config_entries.async_unload(result["result"].entry_id)
    await hass.async_block_till_done()


async def test_flow_asks_when_the_other_model_was_chosen(hass, nest_unit) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "nest_ls"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "manual"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": nest_unit.port, "unit": 1}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["description_placeholders"]["model"] == "NEST LS"


async def test_entry_without_a_model_is_a_nest_ls(hass, loaded) -> None:
    assert "model" not in loaded.data
    assert loaded.runtime_data.model == "nest_ls"
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, loaded.unique_id)})
    assert device.model == "NEST LS"


# entities


async def test_readings(hass, nest_loaded) -> None:
    assert hass.states.get("sensor.alpicair_nest_t_outdoor").state == "2.8"
    assert hass.states.get("sensor.alpicair_nest_t_supply").state == "19.3"
    assert hass.states.get("sensor.alpicair_nest_fan1_output").state == "70.0"
    assert hass.states.get("sensor.alpicair_nest_airflow_supply").state == "245"
    assert hass.states.get("sensor.alpicair_nest_filter_remainingdays").state == "61"
    assert hass.states.get("sensor.alpicair_nest_systemstate").state == "Comfort"
    # 130 days and 5 hours
    assert hass.states.get("sensor.alpicair_nest_running_hours").state == "3125"
    assert hass.states.get("sensor.alpicair_nest_recovery_efficiency").state == "81.7"
    assert hass.states.get("sensor.alpicair_nest_active_faults").state == "0"
    assert hass.states.get("binary_sensor.alpicair_nest_anyerroractive").state == "off"
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, NEST_SERIAL)})
    assert (device.model, device.sw_version, device.serial_number) == ("NEST", "127", NEST_SERIAL)


async def test_humidity_and_co2_follow_the_inputs(hass, nest_loaded) -> None:
    registry = er.async_get(hass)
    assert hass.states.get("sensor.alpicair_nest_ai_extractairhumidity").state == "42.0"
    # no input is set up for CO2, but a value arrives: it is shown
    assert hass.states.get("sensor.alpicair_nest_ai_extractairco2").state == "640"
    supply = registry.async_get("sensor.alpicair_nest_ai_supplyairhumidity")
    assert supply is not None and supply.disabled


async def test_schedules_and_service_settings_are_not_entities(hass, nest_loaded) -> None:
    registry = er.async_get(hass)
    ids = {e.entity_id for e in er.async_entries_for_config_entry(registry, nest_loaded.entry_id)}
    assert "number.alpicair_nest_airtemp_supplytarget_comfort" in ids
    assert "switch.alpicair_nest_freecooling_enable" in ids
    assert not any("weekly_scheduler" in i or "holidays_scheduler" in i for i in ids)
    assert not any("heater_type" in i or "restartunit" in i or "restor_factory" in i for i in ids)
    assert len(ids) > 250


async def test_climate(hass, nest_loaded, nest_unit) -> None:
    unit = nest_unit
    state = hass.states.get("climate.alpicair_nest")
    assert state.state == HVACMode.FAN_ONLY
    assert state.attributes["preset_modes"] == ["building_protection", "economy", "comfort", "boost"]
    assert state.attributes["preset_mode"] == "comfort"
    assert state.attributes["temperature"] == 21.0
    assert state.attributes["current_temperature"] == 19.3
    assert (state.attributes["min_temp"], state.attributes["max_temp"]) == (16.0, 30.0)

    async def call(service: str, **data) -> None:
        fields = {"entity_id": "climate.alpicair_nest", **data}
        await hass.services.async_call("climate", service, fields, blocking=True)
        await hass.async_block_till_done()

    await call("set_preset_mode", preset_mode="economy")
    assert unit.holding[unit.addresses["OperatingMode"]] == 2
    assert hass.states.get("climate.alpicair_nest").attributes["preset_mode"] == "economy"

    await call("set_temperature", temperature=18.5)
    assert unit.holding[unit.addresses["AirTemp_SupplyTarget_Economy"]] == 185

    # boost is a coil, and the mode behind it stays
    await call("set_preset_mode", preset_mode="boost")
    assert unit.coil_writes[-1] == (unit.addresses["BoostMode_Active"], 1)
    assert unit.holding[unit.addresses["OperatingMode"]] == 2
    assert hass.states.get("climate.alpicair_nest").attributes["preset_mode"] == "boost"

    # leaving boost ends it first
    await call("set_preset_mode", preset_mode="comfort")
    assert unit.coil_writes[-1] == (unit.addresses["BoostMode_Active"], 0)
    assert unit.holding[unit.addresses["OperatingMode"]] == 3

    await call("turn_off")
    assert unit.holding[unit.addresses["OperatingMode"]] == 0
    assert hass.states.get("climate.alpicair_nest").state == HVACMode.OFF
    await call("turn_on")
    assert unit.holding[unit.addresses["OperatingMode"]] == 3


async def test_switch_is_a_coil(hass, nest_loaded, nest_unit) -> None:
    address = nest_unit.addresses["FreeCooling_Enable"]
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.alpicair_nest_freecooling_enable"}, blocking=True
    )
    assert nest_unit.coils[address] == 1
    assert nest_unit.writes == []
    assert hass.states.get("switch.alpicair_nest_freecooling_enable").state == "on"
    nest_unit.coil_writes.clear()
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.alpicair_nest_freecooling_enable"}, blocking=True
    )
    assert nest_unit.coil_writes == []


async def test_buttons(hass, nest_loaded, nest_unit) -> None:
    unit = nest_unit
    await hass.services.async_call("button", "press", {"entity_id": "button.alpicair_nest_filter_reset"}, blocking=True)
    await hass.async_block_till_done()
    assert (unit.addresses["Filter_Reset"], 1) in unit.coil_writes
    assert hass.states.get("sensor.alpicair_nest_filter_remainingdays").state == "90"
    await hass.services.async_call("button", "press", {"entity_id": "button.alpicair_nest_reseterrors"}, blocking=True)
    assert (unit.addresses["ResetErrors"], 1) in unit.writes


@pytest.mark.parametrize("one_by_one", [False, True])
async def test_clock(hass, nest_loaded, nest_unit, one_by_one: bool) -> None:
    nest_unit.no_multiple_write = one_by_one
    await hass.services.async_call("button", "press", {"entity_id": "button.alpicair_nest_sync_clock"}, blocking=True)
    await hass.async_block_till_done()
    # the date and the time, then the command; the register between them is not touched
    assert [a for a, _ in nest_unit.writes] == [100, 101, 102, 104, 105, 106]
    assert nest_unit.coil_writes == [(2, 1)]
    assert 1 <= nest_unit.input[5] <= 12


# the panel's API


async def test_schema(admin) -> None:
    result = (await _ask(admin, "schema", language="ru"))["result"]
    assert result["profile"] == {
        "model": "nest",
        "model_name": "NEST",
        "modes": ["Ожидание", "Защита здания", "Эконом", "Комфорт", "Буст"],
        "selectable": [0, 1, 2, 3, 4],
        "auto": False,
        "schedule": False,
        "target_limits": [16.0, 30.0],
    }
    names = {item["name"]: item for item in result["setpoints"]}
    assert names["AirTemp_SupplyTarget_Comfort"]["label"] == "Температура в режиме «Комфорт»"
    assert names["OperatingMode"]["options"] == {"0": "Ожидание", "1": "Защита здания", "2": "Эконом", "3": "Комфорт"}
    assert names["Heater_Type"]["level"] == "service"
    assert names["RestartUnit"]["danger"]
    assert result["faults"]["A38_Supply_Fan_Protection"] == "A.38 Отказ приточного вентилятора"
    readings = {item["name"] for item in result["datapoints"]}
    assert "T_Supply" in readings and "Ahu_Id_1" not in readings
    latvian = (await _ask(admin, "schema", language="lv"))["result"]
    assert latvian["profile"]["modes"][1] == "Ēkas aizsardzība"


async def test_ls_profile(hass, hass_ws_client, loaded) -> None:
    client = await hass_ws_client(hass)
    profile = (await _ask(client, "schema", language="en"))["result"]["profile"]
    assert profile["model"] == "nest_ls"
    assert profile["modes"] == ["Standby", "Unoccupied", "Economy", "Comfort", "Boost", "Kitchen Hood"]
    assert (profile["auto"], profile["schedule"], profile["target_limits"]) == (True, True, None)


async def test_info_and_values(hass, admin, nest_loaded) -> None:
    unit = (await _ask(admin, "info"))["result"]["units"][0]
    assert (unit["model"], unit["model_name"], unit["firmware"], unit["serial"]) == ("nest", "NEST", 127, NEST_SERIAL)
    await admin.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    assert (await admin.receive_json())["success"]
    first = (await admin.receive_json())["event"]
    assert first["dp"]["T_Supply"] == 19.3
    assert first["dp"]["AnyErrorActive"] == 0
    assert first["sp"]["FreeCooling_Enable"] == 0
    # the clock is a reading here; the panel finds it where the NEST LS keeps its own
    assert (first["sp"]["Date"], first["sp"]["Month"], first["sp"]["Year"]) == (12, 11, 26)
    assert (first["sp"]["Hour"], first["sp"]["Min"]) == (8, 38)
    assert first["virtual"]["sensors"] == ["extract_co2", "extract_humidity"]
    assert first["virtual"]["exchanger"] == "plate"
    assert first["words"] == {}


async def test_writes(admin, nest_unit) -> None:
    unit = nest_unit
    assert (await _ask(admin, "write", name="AirTemp_SupplyTarget_Comfort", value=22.5))["result"]["value"] == 22.5
    assert unit.holding[unit.addresses["AirTemp_SupplyTarget_Comfort"]] == 225
    too_warm = await _ask(admin, "write", name="AirTemp_SupplyTarget_Comfort", value=31)
    assert too_warm["error"]["code"] == "invalid_value"
    assert (await _ask(admin, "write", name="Dryness_Protection", value=1))["result"]["value"] == 1
    assert unit.coils[unit.addresses["Dryness_Protection"]] == 1
    # a negative value goes out as two's complement
    assert (await _ask(admin, "write", name="Winter_Summer_Tset_Correction", value=-1.5))["result"]["value"] == -1.5
    assert unit.holding[unit.addresses["Winter_Summer_Tset_Correction"]] == 0x10000 - 15
    assert (await _ask(admin, "write", name="Service_Password", value=1))["error"]["code"] == "not_found"


async def test_control(admin, nest_unit) -> None:
    unit = nest_unit
    assert (await _ask(admin, "control", action="set_mode", mode=1))["success"]
    assert unit.holding[unit.addresses["OperatingMode"]] == 1
    assert (await _ask(admin, "control", action="set_mode", mode=4))["success"]
    assert unit.coils[unit.addresses["BoostMode_Active"]] == 1
    assert (await _ask(admin, "control", action="set_mode", mode=5))["error"]["code"] == "invalid_value"
    assert (await _ask(admin, "control", action="set_auto"))["error"]["code"] == "invalid_value"
    assert (await _ask(admin, "schedule"))["error"]["code"] == "invalid_value"
    assert (await _ask(admin, "write", name="OperatingMode", value=2))["success"]
    assert unit.holding[unit.addresses["OperatingMode"]] == 2
    assert unit.coils[unit.addresses["BoostMode_Active"]] == 0


async def test_service_needs_the_pin(admin, nest_unit, nest_loaded) -> None:
    unit = nest_unit
    address = unit.addresses["Heater_Type"]
    assert (await _ask(admin, "write", name="Heater_Type", value=3))["error"]["code"] == "service_locked"
    assert (await _ask(admin, "unlock", pin="4321"))["error"]["code"] == "wrong_pin"
    assert (await _ask(admin, "unlock", pin="abcd"))["error"]["code"] == "wrong_pin"
    # the unit's own PIN opens nothing: the service PIN is Home Assistant's, 4444 until changed
    assert (await _ask(admin, "unlock", pin=str(TEST_PIN)))["error"]["code"] == "wrong_pin"
    answer = await _ask(admin, "unlock", pin="4444")
    token = answer["result"]["token"]
    assert "4444" not in json.dumps(answer["result"])
    assert (await _ask(admin, "write", name="Heater_Type", value=3, token=token))["success"]
    assert unit.holding[address] == 3
    # nothing is entered in the unit's password register, and it is never read or kept
    assert 199 not in [written for written, _ in unit.writes]
    assert 199 not in nest_loaded.runtime_data.data.sp
    diagnostics = json.dumps(await async_get_config_entry_diagnostics(None, nest_loaded))
    assert NEST_SERIAL not in diagnostics
    assert "3456" not in json.dumps(json.loads(diagnostics)["datapoints"])


async def test_faults(hass, admin, nest_unit, nest_loaded) -> None:
    from pytest_homeassistant_custom_component.common import async_capture_events

    events = async_capture_events(hass, EVENT_FAULT)
    nest_unit.discrete.update({14: 1, 38: 1, 188: 1, 189: 1})
    await _poll(hass, nest_loaded)
    faults = nest_loaded.runtime_data.data.faults
    assert [(f["kind"], f["name"]) for f in faults] == [
        ("warning", "W14_Change_Supply_And_Extract_Filters"),
        ("alarm", "A38_Supply_Fan_Protection"),
    ]
    assert len(events) == 2
    assert hass.states.get("sensor.alpicair_nest_active_faults").state == "2"
    assert hass.states.get("binary_sensor.alpicair_nest_anyerroractive").state == "on"
    names = [f["name"] for f in hass.states.get("sensor.alpicair_nest_active_faults").attributes["faults"]]
    assert names == ["W.14 Change the supply and extract filters (timer)", "A.38 Supply fan failure"]

    nest_unit.discrete.update({14: 0, 38: 0, 188: 0, 189: 0})
    await _poll(hass, nest_loaded)
    log = (await _ask(admin, "log"))["result"]["log"]
    assert [(entry["name"], entry["on"]) for entry in log if not entry["on"]]
    assert len(log) == 4
