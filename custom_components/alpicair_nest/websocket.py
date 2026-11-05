"""What the panel talks to.

Three levels guard the writes, whatever the panel shows: anyone logged in for everyday settings,
an administrator for adjuster settings, and an administrator who has given the unit's service PIN for
service settings. The PIN is compared with the one in the unit; it is neither kept nor sent back.
"""

from __future__ import annotations

import hmac
import secrets
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant, callback

from .client import ModbusError
from .const import (
    CLOCK_REGISTERS,
    DOMAIN,
    PIN_LOCK_SECONDS,
    PIN_MAX_TRIES,
    SCHEDULE_BASE,
    SCHEDULE_DAYS,
    SCHEDULE_EVENTS,
    SCHEDULE_FIELDS,
    SERVICE_UNLOCK_SECONDS,
    SP_SERVICE_PIN,
)
from .coordinator import NestCoordinator
from .registers import Register

ERR_NOT_FOUND = "not_found"
ERR_FORBIDDEN = "forbidden"
ERR_LOCKED = "service_locked"
ERR_WRONG_PIN = "wrong_pin"
ERR_TOO_MANY = "too_many_tries"
ERR_CONFIRM = "confirm_required"
ERR_INVALID = "invalid_value"
ERR_UNIT = "unit_error"

ENTRY_ID = vol.Optional("entry_id")
EVENT_LIMITS = ((0, 23), (0, 59), (0, 5), (0, 30))


@dataclass
class _Access:
    """Service access, per unit."""

    tokens: dict[str, float] = field(default_factory=dict)
    tries: int = 0
    locked_until: float = 0


def _access(hass: HomeAssistant, entry_id: str) -> _Access:
    return hass.data.setdefault(DOMAIN, {}).setdefault("access", {}).setdefault(entry_id, _Access())


def _coordinator(hass: HomeAssistant, msg: dict[str, Any]) -> NestCoordinator | None:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    wanted = msg.get("entry_id")
    for entry in entries:
        if wanted is None or entry.entry_id == wanted:
            return entry.runtime_data
    return None


def _with_coordinator(handler):
    """Answers not_found when there is no such unit, and unit_error when the unit fails."""

    @wraps(handler)
    async def wrapper(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
        coordinator = _coordinator(hass, msg)
        if coordinator is None:
            connection.send_error(msg["id"], ERR_NOT_FOUND, "No such unit")
            return
        try:
            await handler(hass, connection, msg, coordinator)
        except ModbusError as err:
            connection.send_error(msg["id"], ERR_UNIT, str(err))
        except ValueError as err:
            connection.send_error(msg["id"], ERR_INVALID, str(err))

    return wrapper


def _serving(language: str) -> str:
    return "ru" if language.split("-")[0] == "ru" else "en"


def _describe(register: Register, language: str) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": register.name,
        "address": register.address,
        "label": register.label(language),
        "section": register.section,
        "unit": register.unit,
        "decimals": register.decimals,
    }
    options = register.option_labels(language)
    if options:
        item["options"] = options
    if register.hint:
        item["hint"] = register.hint
    return item


def _schema(coordinator: NestCoordinator, language: str) -> dict[str, Any]:
    registers = coordinator.registers
    setpoints = []
    for register in registers.setpoints.values():
        if register.name in CLOCK_REGISTERS:
            continue
        item = _describe(register, language)
        item.update(
            kind=register.entity,
            level=register.level,
            min=register.minimum,
            max=register.maximum,
            default=register.default,
            memory=register.memory,
        )
        if register.read_only:
            item["read_only"] = True
        if register.danger:
            item["danger"] = True
        setpoints.append(item)
    datapoints = []
    for register in registers.datapoints.values():
        if register.hidden:
            continue
        item = _describe(register, language)
        if register.flag:
            item["flag"] = True
        datapoints.append(item)
    faults = {name: labels.get(language) or labels["en"] for name, labels in registers.faults.items()}
    return {"datapoints": datapoints, "setpoints": setpoints, "faults": faults}


def _values(coordinator: NestCoordinator) -> dict[str, Any]:
    registers = coordinator.registers
    return {
        "dp": {
            r.name: r.decode(coordinator.data.dp.get(r.address)) for r in registers.datapoints.values() if not r.hidden
        },
        "sp": {r.name: r.decode(coordinator.data.sp.get(r.address)) for r in registers.setpoints.values()},
    }


def _status(coordinator: NestCoordinator) -> dict[str, Any]:
    words = {r.name: coordinator.data.dp.get(r.address) for r in coordinator.registers.datapoints.values() if r.fault}
    return {
        "available": coordinator.last_update_success,
        "virtual": coordinator.data.virtual,
        "faults": coordinator.data.faults,
        "words": words,
    }


def _allowed(
    hass: HomeAssistant,
    connection: ActiveConnection,
    coordinator: NestCoordinator,
    register: Register,
    token: str | None,
) -> str | None:
    """Why this write is refused, None when it is not."""
    if register.level == "user":
        return None
    if not connection.user.is_admin:
        return ERR_FORBIDDEN
    if register.level == "service" and not _token_valid(hass, coordinator, token):
        return ERR_LOCKED
    return None


def _token_valid(hass: HomeAssistant, coordinator: NestCoordinator, token: str | None) -> bool:
    access = _access(hass, coordinator.config_entry.entry_id)
    now = time.monotonic()
    access.tokens = {key: until for key, until in access.tokens.items() if until > now}
    return token is not None and token in access.tokens


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    for command in (
        ws_info,
        ws_schema,
        ws_subscribe,
        ws_write,
        ws_unlock,
        ws_control,
        ws_schedule,
        ws_schedule_write,
        ws_schedule_copy,
        ws_log,
        ws_log_clear,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/info"})
@callback
def ws_info(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
    """The units there are."""
    units = []
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator: NestCoordinator = entry.runtime_data
        units.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "host": coordinator.client.host,
                "port": coordinator.client.port,
                "unit": coordinator.client.unit,
                "framing": coordinator.client.framing,
                "mac": coordinator.data.virtual.get("mac"),
                "ip": coordinator.data.virtual.get("ip"),
                "firmware": coordinator.value("FirmwareVerMain"),
                "bootloader": coordinator.value("FirmwareVerBootloader"),
                "available": coordinator.last_update_success,
            }
        )
    connection.send_result(msg["id"], {"units": units, "is_admin": connection.user.is_admin})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/schema", ENTRY_ID: str, vol.Optional("language"): str}
)
@websocket_api.async_response
@_with_coordinator
async def ws_schema(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """Every register the panel can show, in the viewer's language."""
    connection.send_result(msg["id"], _schema(coordinator, _serving(msg.get("language") or hass.config.language)))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe", ENTRY_ID: str})
@websocket_api.async_response
@_with_coordinator
async def ws_subscribe(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """All values at first, then what changed after each poll or write."""
    sent = _values(coordinator)

    @callback
    def changed() -> None:
        nonlocal sent
        current = _values(coordinator)
        event = {
            table: {name: value for name, value in values.items() if sent[table].get(name) != value}
            for table, values in current.items()
        }
        sent = current
        connection.send_message(websocket_api.event_message(msg["id"], {**event, **_status(coordinator)}))

    connection.subscriptions[msg["id"]] = coordinator.async_add_listener(changed)
    connection.send_result(msg["id"])
    connection.send_message(websocket_api.event_message(msg["id"], {**sent, **_status(coordinator)}))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/write",
        ENTRY_ID: str,
        vol.Required("name"): str,
        vol.Optional("value"): vol.Coerce(float),
        vol.Optional("token"): str,
        vol.Optional("confirm", default=False): bool,
    }
)
@websocket_api.async_response
@_with_coordinator
async def ws_write(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """Changes a setting or runs a command."""
    register = coordinator.registers.setpoints.get(msg["name"])
    if register is None or register.name in CLOCK_REGISTERS:
        connection.send_error(msg["id"], ERR_NOT_FOUND, "No such setting")
        return
    refused = _allowed(hass, connection, coordinator, register, msg.get("token"))
    if refused:
        connection.send_error(msg["id"], refused, register.name)
        return
    if register.danger and not msg["confirm"]:
        connection.send_error(msg["id"], ERR_CONFIRM, register.name)
        return
    if register.entity == "button":
        await coordinator.async_press(register.name)
        connection.send_result(msg["id"], {})
        return
    if "value" not in msg:
        raise ValueError("A value is required")
    if register.name == "OperatingMode":
        await coordinator.async_set_operating_mode(register.encode(msg["value"]))
        connection.send_result(msg["id"], {"value": coordinator.value(register.name)})
        return
    connection.send_result(msg["id"], {"value": await coordinator.async_write(register.name, msg["value"])})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/unlock", ENTRY_ID: str, vol.Required("pin"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_with_coordinator
async def ws_unlock(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """Opens service settings for a while against the PIN stored in the unit."""
    access = _access(hass, coordinator.config_entry.entry_id)
    now = time.monotonic()
    if access.locked_until > now:
        connection.send_error(msg["id"], ERR_TOO_MANY, str(int(access.locked_until - now) + 1))
        return
    stored = await coordinator.async_read_register(SP_SERVICE_PIN)
    entered = msg["pin"].strip()
    if not (entered.isdecimal() and hmac.compare_digest(str(int(entered)).encode(), str(stored).encode())):
        access.tries += 1
        if access.tries >= PIN_MAX_TRIES:
            access.tries = 0
            access.locked_until = now + PIN_LOCK_SECONDS
        connection.send_error(msg["id"], ERR_WRONG_PIN, "Wrong PIN")
        return
    access.tries = 0
    token = secrets.token_urlsafe(24)
    access.tokens[token] = now + SERVICE_UNLOCK_SECONDS
    connection.send_result(msg["id"], {"token": token, "seconds": SERVICE_UNLOCK_SECONDS})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/control",
        ENTRY_ID: str,
        vol.Required("action"): vol.In(["set_mode", "set_auto", "sync_clock"]),
        vol.Optional("mode"): vol.All(int, vol.Range(min=0, max=5)),
    }
)
@websocket_api.async_response
@_with_coordinator
async def ws_control(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """The everyday commands."""
    action = msg["action"]
    if action == "set_auto":
        await coordinator.async_set_auto()
    elif action == "sync_clock":
        await coordinator.async_sync_clock()
    else:
        if "mode" not in msg:
            raise ValueError("A mode is required")
        await coordinator.async_set_operating_mode(msg["mode"])
    connection.send_result(msg["id"], {})


def _table(schedule: dict[int, int]) -> list[list[list[int]]]:
    """days -> events -> hour, minute, mode, temperature"""
    return [
        [
            [
                schedule.get(SCHEDULE_BASE + (day * SCHEDULE_EVENTS + event) * SCHEDULE_FIELDS + item, 0)
                for item in range(SCHEDULE_FIELDS)
            ]
            for event in range(SCHEDULE_EVENTS)
        ]
        for day in range(SCHEDULE_DAYS)
    ]


def _day_registers(day: int, events: list[list[int]]) -> dict[int, int]:
    if len(events) != SCHEDULE_EVENTS:
        raise ValueError(f"A day holds {SCHEDULE_EVENTS} events")
    changes: dict[int, int] = {}
    for index, event in enumerate(events):
        if len(event) != SCHEDULE_FIELDS:
            raise ValueError(f"An event holds {SCHEDULE_FIELDS} values")
        for item, (value, (low, high)) in enumerate(zip(event, EVENT_LIMITS, strict=True)):
            if not low <= value <= high:
                raise ValueError(f"{value} is outside {low}..{high}")
            changes[SCHEDULE_BASE + (day * SCHEDULE_EVENTS + index) * SCHEDULE_FIELDS + item] = value
    return changes


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/schedule", ENTRY_ID: str})
@websocket_api.async_response
@_with_coordinator
async def ws_schedule(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """The week, read from the unit now."""
    connection.send_result(msg["id"], {"days": _table(await coordinator.async_read_schedule_now())})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/schedule_write",
        ENTRY_ID: str,
        vol.Required("day"): vol.All(int, vol.Range(min=0, max=SCHEDULE_DAYS - 1)),
        vol.Required("events"): [[int]],
    }
)
@websocket_api.async_response
@_with_coordinator
async def ws_schedule_write(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """Replaces one day."""
    await coordinator.async_write_schedule(_day_registers(msg["day"], msg["events"]))
    connection.send_result(msg["id"], {"days": _table(coordinator.data.schedule)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/schedule_copy",
        ENTRY_ID: str,
        vol.Required("source"): vol.All(int, vol.Range(min=0, max=SCHEDULE_DAYS - 1)),
        vol.Required("targets"): [vol.All(int, vol.Range(min=0, max=SCHEDULE_DAYS - 1))],
    }
)
@websocket_api.async_response
@_with_coordinator
async def ws_schedule_copy(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """Copies a day onto others, by writing the registers: the outcome can be read back."""
    table = _table(await coordinator.async_read_schedule_now())
    changes: dict[int, int] = {}
    for target in msg["targets"]:
        changes.update(_day_registers(target, table[msg["source"]]))
    await coordinator.async_write_schedule(changes)
    connection.send_result(msg["id"], {"days": _table(coordinator.data.schedule)})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/log", ENTRY_ID: str})
@websocket_api.async_response
@_with_coordinator
async def ws_log(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """Fault history, newest first."""
    connection.send_result(msg["id"], {"log": coordinator.fault_log[::-1]})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/log_clear", ENTRY_ID: str})
@websocket_api.require_admin
@websocket_api.async_response
@_with_coordinator
async def ws_log_clear(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any], coordinator: NestCoordinator
) -> None:
    """Clears the history kept in Home Assistant."""
    await coordinator.async_clear_log()
    connection.send_result(msg["id"], {})
