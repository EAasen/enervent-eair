"""Climate entity for Enervent eAir."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EnerventConfigEntry
from .api_client import EnerventApiError
from .const import (
    DOMAIN,
    MODE_PRESETS,
    REGISTER_MAX_TEMP,
    REGISTER_MIN_TEMP,
    REGISTER_MODE,
    REGISTER_SUPPLY_TEMP,
    REGISTER_TARGET_TEMP,
)

_MODE_PRESET_NAMES = {
    0: "Home",
    16: "Away",
    32: "Away long",
    512: "Boost",
    1024: "Overpressure",
}
_TEMPERATURE_SCALE = 10


async def async_setup_entry(
    hass: Any,
    entry: EnerventConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up the Enervent climate entity."""
    async_add_entities([EnerventClimateEntity(entry)])


class EnerventClimateEntity(CoordinatorEntity, ClimateEntity):
    """Expose the eAir supply temperature and operating presets."""

    _attr_has_entity_name = True
    _attr_name = "Ventilation"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_mode = HVACMode.AUTO
    _attr_hvac_modes = [HVACMode.AUTO]
    _attr_target_temperature_step = 0.5
    _attr_preset_modes = list(MODE_PRESETS)
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(self, entry: EnerventConfigEntry) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Enervent eAir",
            "manufacturer": "Enervent",
        }

    @property
    def current_temperature(self) -> float | None:
        """Return the measured supply-air temperature."""
        raw = self.coordinator.data.get(REGISTER_SUPPLY_TEMP)
        return None if raw is None else float(raw) / _TEMPERATURE_SCALE

    @property
    def target_temperature(self) -> float | None:
        """Return the supply-air temperature setpoint."""
        raw = self.coordinator.data.get(REGISTER_TARGET_TEMP)
        return None if raw is None else float(raw) / _TEMPERATURE_SCALE

    @property
    def min_temp(self) -> float:
        """Return the unit's configured minimum setpoint."""
        return float(self.coordinator.data.get(REGISTER_MIN_TEMP, 10))

    @property
    def max_temp(self) -> float:
        """Return the unit's configured maximum setpoint."""
        return float(self.coordinator.data.get(REGISTER_MAX_TEMP, 35))

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset from the mode bit mask."""
        mode = self.coordinator.data.get(REGISTER_MODE)
        if mode is None:
            return None
        return _MODE_PRESET_NAMES.get(int(mode) & 0x7FFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the supply-air temperature."""
        if (temperature := kwargs.get("temperature")) is None:
            raise HomeAssistantError("A target temperature is required")
        try:
            await self.coordinator.client.async_set_temperature(float(temperature))
        except EnerventApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Accept the only HVAC mode exposed by this ventilation controller."""
        if hvac_mode != HVACMode.AUTO:
            raise HomeAssistantError(f"Unsupported Enervent HVAC mode: {hvac_mode}")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set a supported operating preset."""
        if preset_mode not in self._attr_preset_modes:
            raise HomeAssistantError(f"Unsupported Enervent preset: {preset_mode}")
        try:
            await self.coordinator.client.async_set_mode(preset_mode)
        except EnerventApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
