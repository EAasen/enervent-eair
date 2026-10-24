"""Select entities for Enervent eAir."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory

from . import EnerventConfigEntry
from .const import MODE_PRESETS, REGISTER_MODE
from .entity import EnerventEntity

_TEMPERATURE_BOOST_SENSOR_REGISTER = 82
# Model enumeration "tboostsensor".
_TEMPERATURE_BOOST_SENSORS = {
    9: "Extract air temperature",
    1: "Room temperature average",
}
_MODE_NAMES = {value: name for name, value in MODE_PRESETS.items()}


async def async_setup_entry(
    hass: Any,
    entry: EnerventConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Enervent selects."""
    async_add_entities(
        [EnerventOperatingModeSelect(entry), EnerventTemperatureBoostSensor(entry)]
    )


class EnerventOperatingModeSelect(EnerventEntity, SelectEntity):
    """Select Home, Away, Away long, Boost or Overpressure."""

    _attr_name = "Operating mode"
    _attr_icon = "mdi:home-switch-outline"
    _attr_options = list(MODE_PRESETS)

    def __init__(self, entry: EnerventConfigEntry) -> None:
        super().__init__(entry, "operating_mode")

    @property
    def current_option(self) -> str | None:
        """Return the active operating mode."""
        mode = self.coordinator.data.get(REGISTER_MODE)
        if mode is None:
            return None
        return _MODE_NAMES.get(int(mode) & 0x7FFF)

    async def async_select_option(self, option: str) -> None:
        """Apply an operating mode."""
        await self._async_write(lambda: self.coordinator.client.async_set_mode(option))


class EnerventTemperatureBoostSensor(EnerventEntity, SelectEntity):
    """Choose the measurement used by temperature boost."""

    _attr_name = "Temperature boost measurement"
    _attr_icon = "mdi:thermometer"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(_TEMPERATURE_BOOST_SENSORS.values())

    def __init__(self, entry: EnerventConfigEntry) -> None:
        super().__init__(entry, "temperature_boost_measurement")

    @property
    def current_option(self) -> str | None:
        """Return the selected measurement."""
        value = self.coordinator.data.get(_TEMPERATURE_BOOST_SENSOR_REGISTER)
        return None if value is None else _TEMPERATURE_BOOST_SENSORS.get(int(value))

    async def async_select_option(self, option: str) -> None:
        """Select the measurement."""
        value = next(
            raw for raw, name in _TEMPERATURE_BOOST_SENSORS.items() if name == option
        )
        await self._async_write(
            lambda: self.coordinator.client.async_write_register(
                _TEMPERATURE_BOOST_SENSOR_REGISTER, value
            )
        )
