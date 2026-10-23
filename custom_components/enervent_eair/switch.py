"""Switch entities for Enervent eAir overrides."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EnerventConfigEntry
from .api_client import EnerventApiError
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class EnerventSwitchDescription(SwitchEntityDescription):
    """Describe a writable Enervent override."""

    register: int


SWITCHES = (
    EnerventSwitchDescription(
        key="manual_boost",
        name="Manual boost",
        icon="mdi:fan-plus",
        register=10010,
    ),
    EnerventSwitchDescription(
        key="overpressure",
        name="Overpressure mode",
        icon="mdi:fan-chevron-up",
        register=10003,
    ),
)


async def async_setup_entry(
    hass: Any,
    entry: EnerventConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Enervent override switches."""
    async_add_entities(EnerventSwitch(entry, description) for description in SWITCHES)


class EnerventSwitch(CoordinatorEntity, SwitchEntity):
    """Control one supported unit override."""

    entity_description: EnerventSwitchDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: EnerventConfigEntry,
        description: EnerventSwitchDescription,
    ) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Enervent eAir",
            "manufacturer": "Enervent",
        }

    @property
    def is_on(self) -> bool | None:
        """Return the current switch state."""
        value = self.coordinator.data.get(self.entity_description.register)
        return None if value is None else bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the override."""
        try:
            await self.coordinator.client.async_set_switch(
                self.entity_description.register, True
            )
        except EnerventApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the override."""
        try:
            await self.coordinator.client.async_set_switch(
                self.entity_description.register, False
            )
        except EnerventApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
