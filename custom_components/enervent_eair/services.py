"""Services for Enervent eAir weekly time programs."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .api_client import EnerventApiError
from .const import (
    DOMAIN,
    WEEK_PROGRAM_ACTIONS,
    WEEK_PROGRAM_SLOTS,
    WEEKDAY_BITS,
)

SERVICE_SET_WEEK_PROGRAM = "set_week_program"
SERVICE_CLEAR_WEEK_PROGRAM = "clear_week_program"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
_ACTION_BY_NAME = {name: value for value, name in WEEK_PROGRAM_ACTIONS.items()}

_BASE_SCHEMA = {
    vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Required("slot"): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=WEEK_PROGRAM_SLOTS)
    ),
}
SET_SCHEMA = vol.Schema(
    {
        **_BASE_SCHEMA,
        vol.Required("weekdays"): vol.All(
            cv.ensure_list, [vol.In(list(WEEKDAY_BITS))], vol.Length(min=1)
        ),
        vol.Required("start"): cv.time,
        vol.Required("stop"): cv.time,
        vol.Required("action"): vol.In(
            [name for name in _ACTION_BY_NAME if name != "No action"]
        ),
    }
)
CLEAR_SCHEMA = vol.Schema(_BASE_SCHEMA)


def _client(hass: HomeAssistant, call: ServiceCall):
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
        entries = [entry for entry in entries if entry.entry_id == entry_id]
    if len(entries) != 1:
        raise ServiceValidationError(
            "Specify config_entry_id for exactly one loaded Enervent unit"
        )
    return entries[0].runtime_data


async def _async_write(hass: HomeAssistant, call: ServiceCall, **program) -> None:
    runtime = _client(hass, call)
    try:
        await runtime.client.async_set_week_program(call.data["slot"], **program)
    except EnerventApiError as err:
        raise HomeAssistantError(str(err)) from err
    runtime.coordinator.async_set_updated_data(runtime.client.registers)


def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_WEEK_PROGRAM):
        return

    async def set_week_program(call: ServiceCall) -> None:
        start = call.data["start"]
        stop = call.data["stop"]
        await _async_write(
            hass,
            call,
            weekdays=sum(WEEKDAY_BITS[day] for day in set(call.data["weekdays"])),
            start_hour=start.hour,
            start_minute=start.minute,
            stop_hour=stop.hour,
            stop_minute=stop.minute,
            action=_ACTION_BY_NAME[call.data["action"]],
        )

    async def clear_week_program(call: ServiceCall) -> None:
        await _async_write(
            hass,
            call,
            weekdays=0,
            start_hour=0,
            start_minute=0,
            stop_hour=0,
            stop_minute=0,
            action=0,
        )

    hass.services.async_register(
        DOMAIN, SERVICE_SET_WEEK_PROGRAM, set_week_program, schema=SET_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_WEEK_PROGRAM, clear_week_program, schema=CLEAR_SCHEMA
    )
