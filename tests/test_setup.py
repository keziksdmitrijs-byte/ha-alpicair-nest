"""The integration against the simulated unit."""

from __future__ import annotations

from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er

from custom_components.alpicair_nest.const import PANEL_URL


async def test_setup_and_unload(hass, loaded) -> None:
    assert loaded.state is ConfigEntryState.LOADED
    assert PANEL_URL in hass.data["frontend_panels"]
    await hass.config_entries.async_unload(loaded.entry_id)
    await hass.async_block_till_done()
    assert loaded.state is ConfigEntryState.NOT_LOADED
    assert PANEL_URL not in hass.data["frontend_panels"]
    assert await hass.config_entries.async_setup(loaded.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL in hass.data["frontend_panels"]


async def test_main_readings(hass, loaded) -> None:
    assert hass.states.get("sensor.alpicair_nest_t_outdoor").state == "2.8"
    assert hass.states.get("sensor.alpicair_nest_t_supply").state == "19.3"
    assert hass.states.get("sensor.alpicair_nest_airflow_supply").state == "245"
    assert hass.states.get("sensor.alpicair_nest_filter_remainingdays").state == "121"
    assert hass.states.get("sensor.alpicair_nest_running_hours").state == "13120"
    assert hass.states.get("sensor.alpicair_nest_active_faults").state == "0"
    # (21.4 - 6.2) / (21.4 - 2.8)
    assert hass.states.get("sensor.alpicair_nest_recovery_efficiency").state == "81.7"


async def test_analog_sensors_follow_the_inputs(hass, loaded) -> None:
    registry = er.async_get(hass)
    assert hass.states.get("sensor.alpicair_nest_ai_extractairhumidity").state == "42"
    assert hass.states.get("sensor.alpicair_nest_ai_extractairco2").state == "640"
    voc = registry.async_get("sensor.alpicair_nest_ai_voc")
    assert voc is not None and voc.disabled


async def test_service_settings_are_not_entities(hass, loaded) -> None:
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, loaded.entry_id)
    ids = {e.entity_id for e in entities}
    assert "number.alpicair_nest_airtemp_supplytarget_comfort" in ids
    assert not any("fan1_pulsesperrotation" in i for i in ids)
    assert not any("restartunit" in i for i in ids)
    assert not {"number.alpicair_nest_min", "number.alpicair_nest_hour", "number.alpicair_nest_date"} & ids
    assert len(ids) > 250


async def test_climate(hass, loaded, unit) -> None:
    state = hass.states.get("climate.alpicair_nest")
    assert state.state == HVACMode.FAN_ONLY
    assert state.attributes["preset_mode"] == "comfort"
    assert state.attributes["temperature"] == 20.0
    assert state.attributes["current_temperature"] == 19.3
    assert state.attributes["min_temp"] == 12.0

    await hass.services.async_call(
        "climate", "set_preset_mode", {"entity_id": "climate.alpicair_nest", "preset_mode": "economy"}, blocking=True
    )
    await hass.async_block_till_done()
    assert unit.holding[unit.addresses["OperatingMode"]] == 2
    assert unit.holding[unit.addresses["ControlMode"]] == 1

    await hass.services.async_call(
        "climate", "set_temperature", {"entity_id": "climate.alpicair_nest", "temperature": 18.5}, blocking=True
    )
    await hass.async_block_till_done()
    assert unit.holding[unit.addresses["AirTemp_SupplyTarget_Economy"]] == 185

    await hass.services.async_call("climate", "turn_off", {"entity_id": "climate.alpicair_nest"}, blocking=True)
    await hass.async_block_till_done()
    assert unit.holding[unit.addresses["OperatingMode"]] == 0
    await hass.services.async_call("climate", "turn_on", {"entity_id": "climate.alpicair_nest"}, blocking=True)
    await hass.async_block_till_done()
    assert unit.holding[unit.addresses["OperatingMode"]] == 2

    await hass.services.async_call(
        "climate", "set_preset_mode", {"entity_id": "climate.alpicair_nest", "preset_mode": "schedule"}, blocking=True
    )
    await hass.async_block_till_done()
    assert unit.holding[unit.addresses["ControlMode"]] == 0
    assert hass.states.get("climate.alpicair_nest").attributes["preset_mode"] == "schedule"


async def test_number_and_select(hass, loaded, unit) -> None:
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.alpicair_nest_airtemp_supplytarget_comfort", "value": 21.5},
        blocking=True,
    )
    assert unit.holding[unit.addresses["AirTemp_SupplyTarget_Comfort"]] == 215
    state = hass.states.get("select.alpicair_nest_operatingmode")
    assert state.state == "Comfort"
    await hass.services.async_call(
        "select", "select_option", {"entity_id": state.entity_id, "option": "Boost"}, blocking=True
    )
    await hass.async_block_till_done()
    assert unit.holding[unit.addresses["OperatingMode"]] == 4


async def test_unchanged_value_is_not_written(hass, loaded, unit) -> None:
    unit.writes.clear()
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.alpicair_nest_airtemp_supplytarget_comfort", "value": 20.0},
        blocking=True,
    )
    assert unit.writes == []


async def test_filter_reset_button(hass, loaded, unit) -> None:
    await hass.services.async_call("button", "press", {"entity_id": "button.alpicair_nest_filter_reset"}, blocking=True)
    await hass.async_block_till_done()
    assert (unit.addresses["Filter_Reset"], 1) in unit.writes


async def test_clock_written_in_one_go(hass, loaded, unit) -> None:
    await hass.services.async_call("button", "press", {"entity_id": "button.alpicair_nest_sync_clock"}, blocking=True)
    assert [a for a, _ in unit.writes] == list(range(602, 608))
