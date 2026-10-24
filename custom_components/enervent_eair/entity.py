"""Shared entity helpers for Enervent eAir."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EnerventConfigEntry
from .api_client import EnerventApiError
from .const import DOMAIN


class EnerventEntity(CoordinatorEntity):
    """Base entity attached to the Enervent eAir device."""

    _attr_has_entity_name = True

    def __init__(self, entry: EnerventConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Enervent eAir",
            "manufacturer": "Enervent",
        }

    async def _async_write(self, write: Callable[[], Awaitable[None]]) -> None:
        """Run a confirmed write and publish the updated register cache."""
        try:
            await write()
        except EnerventApiError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(self.coordinator.client.registers)
