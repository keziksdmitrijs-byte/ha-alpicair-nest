"""Diagnostics download: the raw registers, without addresses of any kind."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import NestConfigEntry
from .const import CONF_MAC

TO_REDACT = {CONF_HOST, CONF_MAC, "mac", "ip", "unique_id", "title"}
# the LAN and Bluetooth addresses among the data points
PRIVATE_DP = range(316, 344)


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: NestConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    private_sp = {r.address for r in coordinator.registers.setpoints.values() if r.section == "network"}
    return {
        "entry": async_redact_data({**entry.as_dict()}, TO_REDACT),
        "framing": coordinator.client.framing,
        "unit": coordinator.client.unit,
        "virtual": async_redact_data(data.virtual, TO_REDACT),
        "faults": data.faults,
        "fault_log": coordinator.fault_log,
        "datapoints": {a: v for a, v in sorted(data.dp.items()) if a not in PRIVATE_DP},
        "setpoints": {a: v for a, v in sorted(data.sp.items()) if a not in private_sp},
        "unreadable": coordinator.unreadable,
    }
