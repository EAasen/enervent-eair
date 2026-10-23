"""Enervent eAir integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api_client import EnerventApiClient, EnerventApiError
from .const import (
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_NUMBER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import EnerventDataUpdateCoordinator


@dataclass
class EnerventRuntimeData:
    """Runtime objects for one configured unit."""

    client: EnerventApiClient
    coordinator: EnerventDataUpdateCoordinator


type EnerventConfigEntry = ConfigEntry[EnerventRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant, entry: EnerventConfigEntry
) -> bool:
    """Set up an Enervent eAir config entry."""
    client = EnerventApiClient(
        hass,
        entry.data[CONF_SERIAL_NUMBER],
        entry.data[CONF_PIN],
    )
    coordinator = EnerventDataUpdateCoordinator(
        hass,
        client,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except (ConfigEntryNotReady, EnerventApiError) as err:
        await client.async_close()
        if isinstance(err, ConfigEntryNotReady):
            raise
        raise ConfigEntryNotReady from err

    entry.runtime_data = EnerventRuntimeData(client, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EnerventConfigEntry
) -> bool:
    """Unload an Enervent eAir config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    await entry.runtime_data.client.async_close()
    return True
