"""Switch entities for Enervent eAir overrides."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EnerventConfigEntry
from .api_client import EnerventApiError
from .const import DOMAIN, WEEKDAY_BITS


@dataclass(frozen=True, kw_only=True)
class EnerventSwitchDescription(SwitchEntityDescription):
    """Describe a writable Enervent override."""

    register: int
    mask: int | None = None


_SNC_WEEKDAYS_REGISTER = 97
_WEEKDAY_NAMES = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}


def _setting(key: str, name: str, register: int, icon: str) -> EnerventSwitchDescription:
    return EnerventSwitchDescription(
        key=key,
        name=name,
        icon=icon,
        register=register,
        entity_category=EntityCategory.CONFIG,
    )


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
    EnerventSwitchDescription(
        key="away",
        name="Away mode",
        icon="mdi:home-export-outline",
        register=10001,
    ),
    EnerventSwitchDescription(
        key="away_long",
        name="Away long mode",
        icon="mdi:airplane",
        register=10002,
    ),
    EnerventSwitchDescription(
        key="silent_mode",
        name="Silent mode",
        icon="mdi:volume-off",
        register=10047,
    ),
    _setting("hrc_defrost", "Heat recovery defrosting", 10055, "mdi:snowflake-melt"),
    _setting(
        "summer_night_cooling",
        "Summer night cooling",
        10012,
        "mdi:weather-night",
    ),
    _setting(
        "summer_night_cooling_block_active_cooling",
        "Summer night cooling: active cooling blocked",
        10015,
        "mdi:snowflake-off",
    ),
    _setting("humidity_boost", "Humidity boost", 10009, "mdi:water-percent"),
    _setting("co2_boost", "CO2 boost", 10008, "mdi:molecule-co2"),
    _setting("temperature_boost", "Temperature boost", 10011, "mdi:thermometer-chevron-up"),
    *(
        EnerventSwitchDescription(
            key=f"summer_night_cooling_{day}",
            name=f"Summer night cooling on {name}",
            icon="mdi:calendar-week",
            register=_SNC_WEEKDAYS_REGISTER,
            mask=WEEKDAY_BITS[day],
            entity_category=EntityCategory.CONFIG,
        )
        for day, name in _WEEKDAY_NAMES.items()
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
        if value is None:
            return None
        if self.entity_description.mask is not None:
            return bool(int(value) & self.entity_description.mask)
        return bool(value)

    async def _async_set(self, enabled: bool) -> None:
        description = self.entity_description
        client = self.coordinator.client
        try:
            if description.mask is not None:
                await client.async_set_bit(description.register, description.mask, enabled)
            else:
                await client.async_set_switch(description.register, enabled)
        except EnerventApiError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.async_set_updated_data(dict(client.registers))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the setting or override."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the setting or override."""
        await self._async_set(False)
