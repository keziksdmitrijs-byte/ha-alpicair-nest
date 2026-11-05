"""What the panel talks to, and who may do what."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_capture_events, async_fire_time_changed

from custom_components.alpicair_nest.const import DOMAIN, EVENT_FAULT
from custom_components.alpicair_nest.diagnostics import async_get_config_entry_diagnostics

from .simulator import TEST_PIN


async def _ask(client, command: str, **fields):
    await client.send_json_auto_id({"type": f"{DOMAIN}/{command}", **fields})
    return await client.receive_json()


async def _poll(hass, entry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


@pytest.fixture
async def admin(hass, hass_ws_client, loaded):
    return await hass_ws_client(hass)


@pytest.fixture
async def viewer(hass, hass_ws_client, loaded, hass_admin_user):
    hass_admin_user.groups = []
    return await hass_ws_client(hass)


async def test_info(admin) -> None:
    answer = await _ask(admin, "info")
    assert answer["success"]
    unit = answer["result"]["units"][0]
    assert unit["firmware"] == 48012
    assert unit["mac"] == "02:ac:10:20:30:40"
    assert answer["result"]["is_admin"]


async def test_schema_in_russian(admin) -> None:
    answer = await _ask(admin, "schema", language="ru")
    result = answer["result"]
    names = {item["name"]: item for item in result["setpoints"]}
    assert names["AirTemp_SupplyTarget_Comfort"]["label"] == "Уставка притока, режим «Комфорт»"
    assert names["OperatingMode"]["options"]["3"] == "Комфорт"
    assert "Min" not in names
    assert "ServiceLock" not in names
    assert result["faults"]["Fan1_FeedbackError"] == "Нет сигнала от приточного вентилятора"


async def test_subscription(hass, admin, unit, loaded) -> None:
    await admin.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    assert (await admin.receive_json())["success"]
    first = await admin.receive_json()
    event = first["event"]
    assert event["dp"]["T_Outdoor"] == 2.8
    assert event["sp"]["AirTemp_SupplyTarget_Comfort"] == 20.0
    assert event["virtual"]["running_hours"] == 13120
    assert event["available"] is True

    unit.input[unit.addresses_dp["T_Outdoor"]] = 35
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
    await hass.async_block_till_done()
    second = (await admin.receive_json())["event"]
    assert second["dp"] == {"T_Outdoor": 3.5}
    assert second["sp"] == {}


async def test_everyday_write(admin, unit) -> None:
    answer = await _ask(admin, "write", name="AirTemp_SupplyTarget_Comfort", value=21.5)
    assert answer["result"] == {"value": 21.5}
    assert unit.holding[unit.addresses["AirTemp_SupplyTarget_Comfort"]] == 215


async def test_out_of_range(admin) -> None:
    answer = await _ask(admin, "write", name="AirTemp_SupplyTarget_Comfort", value=99)
    assert answer["error"]["code"] == "invalid_value"


async def test_unknown_or_hidden_names(admin) -> None:
    for name in ("ServiceLock", "Min", "NoSuchThing"):
        assert (await _ask(admin, "write", name=name, value=1))["error"]["code"] == "not_found"


async def test_viewer_cannot_touch_adjuster_or_service(viewer, unit) -> None:
    assert (await _ask(viewer, "write", name="Linear_Fan1_Fanspeed_Comfort", value=40))["error"]["code"] == "forbidden"
    assert (await _ask(viewer, "write", name="Fan1_PulsesPerRotation", value=2))["error"]["code"] == "forbidden"
    assert (await _ask(viewer, "unlock", pin=str(TEST_PIN)))["error"]["code"] == "unauthorized"
    assert (await _ask(viewer, "write", name="AirTemp_SupplyTarget_Comfort", value=21))["success"]
    assert (await _ask(viewer, "log_clear"))["error"]["code"] == "unauthorized"


async def test_service_needs_the_pin(admin, unit) -> None:
    address = unit.addresses["Fan1_PulsesPerRotation"]
    assert (await _ask(admin, "write", name="Fan1_PulsesPerRotation", value=4))["error"]["code"] == "service_locked"
    assert unit.holding[address] != 4

    assert (await _ask(admin, "unlock", pin="0"))["error"]["code"] == "wrong_pin"
    assert (await _ask(admin, "unlock", pin="abcd"))["error"]["code"] == "wrong_pin"
    answer = await _ask(admin, "unlock", pin=str(TEST_PIN))
    token = answer["result"]["token"]
    assert str(TEST_PIN) not in json.dumps(answer["result"])

    assert (await _ask(admin, "write", name="Fan1_PulsesPerRotation", value=4, token="wrong"))["error"][
        "code"
    ] == "service_locked"
    assert (await _ask(admin, "write", name="Fan1_PulsesPerRotation", value=4, token=token))["success"]
    assert unit.holding[address] == 4


async def test_too_many_wrong_pins(admin) -> None:
    for _ in range(5):
        assert (await _ask(admin, "unlock", pin="1"))["error"]["code"] == "wrong_pin"
    assert (await _ask(admin, "unlock", pin=str(TEST_PIN)))["error"]["code"] == "too_many_tries"


async def test_dangerous_command_needs_confirmation(admin, unit) -> None:
    token = (await _ask(admin, "unlock", pin=str(TEST_PIN)))["result"]["token"]
    answer = await _ask(admin, "write", name="RestartUnit", token=token)
    assert answer["error"]["code"] == "confirm_required"
    assert (await _ask(admin, "write", name="RestartUnit", token=token, confirm=True))["success"]
    assert (unit.addresses["RestartUnit"], 11223) in unit.writes


async def test_control(admin, unit, hass) -> None:
    assert (await _ask(admin, "control", action="set_mode", mode=4))["success"]
    await hass.async_block_till_done()
    assert unit.holding[unit.addresses["OperatingMode"]] == 4
    assert (await _ask(admin, "control", action="set_auto"))["success"]
    await hass.async_block_till_done()
    assert unit.holding[unit.addresses["ControlMode"]] == 0


async def test_operating_mode_setting_takes_manual_control(hass, admin, unit) -> None:
    await _ask(admin, "control", action="set_auto")
    await hass.async_block_till_done()
    assert (await _ask(admin, "write", name="OperatingMode", value=2))["success"]
    await hass.async_block_till_done()
    assert unit.holding[unit.addresses["ControlMode"]] == 1
    assert unit.holding[unit.addresses["OperatingMode"]] == 2


async def test_schedule(admin, unit) -> None:
    days = (await _ask(admin, "schedule"))["result"]["days"]
    assert len(days) == 7
    assert len(days[0]) == 10
    assert days[0][0] == [6, 30, 4, 20]
    assert days[5][0] == [0, 0, 0, 0]

    events = days[0]
    events[1] = [23, 15, 2, 17]
    answer = await _ask(admin, "schedule_write", day=2, events=events)
    assert answer["success"]
    assert unit.holding[700 + 2 * 40 + 4] == 23

    answer = await _ask(admin, "schedule_copy", source=2, targets=[5, 6])
    assert answer["result"]["days"][6][1] == [23, 15, 2, 17]
    assert unit.holding[700 + 6 * 40 + 7] == 17


async def test_schedule_limits(admin) -> None:
    events = [[0, 0, 0, 0] for _ in range(10)]
    events[0] = [25, 0, 0, 0]
    assert (await _ask(admin, "schedule_write", day=0, events=events))["error"]["code"] == "invalid_value"
    assert (await _ask(admin, "schedule_write", day=0, events=events[:3]))["error"]["code"] == "invalid_value"


async def test_faults(hass, admin, unit, loaded) -> None:
    events = async_capture_events(hass, EVENT_FAULT)
    word = unit.addresses_dp["ErrorStatus1"]
    unit.input[word] = 1 | (1 << 5)
    await _poll(hass, loaded)
    state = hass.states.get("sensor.alpicair_nest_active_faults")
    assert state.state == "2"
    names = {fault["name"] for fault in state.attributes["faults"]}
    # bit 5 of the word has no name in the table: it is still shown, not swallowed
    assert names == {"Fan 1 (supply) Feedback Error", "ErrorStatus1 bit 5"}
    assert len(events) == 2

    unit.input[word] = 0
    await _poll(hass, loaded)
    assert hass.states.get("sensor.alpicair_nest_active_faults").state == "0"
    log = (await _ask(admin, "log"))["result"]["log"]
    assert [item["on"] for item in log] == [False, False, True, True]
    assert (await _ask(admin, "log_clear"))["success"]
    assert (await _ask(admin, "log"))["result"]["log"] == []


async def test_alarm_word_repeats_a_warning_once(hass, unit, loaded) -> None:
    """A real unit sets the same bit in the warning word and the alarm word."""
    unit.input[unit.addresses_dp["WarningStatus1"]] = 1 << 11
    unit.input[unit.addresses_dp["AlarmStatus1"]] = 1 << 11
    await _poll(hass, loaded)
    faults = loaded.runtime_data.data.faults
    assert [(fault["kind"], fault["name"]) for fault in faults] == [("warning", "ERC_Rotary_EfficiencyAlarm")]


async def test_refused_address_is_skipped(hass, unit, loaded) -> None:
    coordinator = loaded.runtime_data
    unit.refused_input = {unit.addresses_dp["AI_VOC"]}
    await _poll(hass, loaded)
    assert coordinator.last_update_success
    assert coordinator.unreadable["dp"] == [unit.addresses_dp["AI_VOC"]]
    assert hass.states.get("sensor.alpicair_nest_t_outdoor").state == "2.8"


async def test_connection_loss_and_return(hass, unit, loaded) -> None:
    port = unit.port
    await unit.stop()
    await _poll(hass, loaded)
    assert hass.states.get("sensor.alpicair_nest_t_outdoor").state == "unavailable"
    await unit.start(port)
    await _poll(hass, loaded)
    assert hass.states.get("sensor.alpicair_nest_t_outdoor").state == "2.8"


async def test_fallback_when_single_write_is_missing(hass, admin, unit) -> None:
    unit.no_single_write = True
    assert (await _ask(admin, "write", name="AirTemp_SupplyTarget_Comfort", value=22))["success"]
    assert unit.holding[unit.addresses["AirTemp_SupplyTarget_Comfort"]] == 220


async def test_pin_never_leaves(hass, admin, unit, loaded) -> None:
    """Not in the data, the diagnostics, or what the panel receives."""
    unit.holding[475] = 7391
    loaded.runtime_data._setpoints_due = True
    await loaded.runtime_data.async_refresh()
    assert 475 not in loaded.runtime_data.data.sp

    diagnostics = await async_get_config_entry_diagnostics(hass, loaded)
    assert 475 not in diagnostics["setpoints"]
    text = json.dumps(diagnostics, default=str)
    assert "127.0.0.1" not in text
    assert "02:ac:10" not in text

    schema = (await _ask(admin, "schema"))["result"]
    assert not [item for item in schema["setpoints"] if item["address"] == 475]
