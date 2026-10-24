"""Number entities for Enervent eAir settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)

from . import EnerventConfigEntry
from .entity import EnerventEntity


@dataclass(frozen=True, kw_only=True)
class EnerventNumberDescription(NumberEntityDescription):
    """Describe a writable register; min/max/step are in display units."""

    register: int
    scale: int = 1


def _temperature(
    key: str, name: str, register: int, minimum: float, maximum: float
) -> EnerventNumberDescription:
    return EnerventNumberDescription(
        key=key,
        name=name,
        register=register,
        scale=10,
        native_min_value=minimum,
        native_max_value=maximum,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    )


def _percent(
    key: str, name: str, register: int, minimum: float = 20
) -> EnerventNumberDescription:
    return EnerventNumberDescription(
        key=key,
        name=name,
        register=register,
        native_min_value=minimum,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    )


def _plain(
    key: str,
    name: str,
    register: int,
    minimum: float,
    maximum: float,
    unit: str | None,
    icon: str,
) -> EnerventNumberDescription:
    return EnerventNumberDescription(
        key=key,
        name=name,
        register=register,
        native_min_value=minimum,
        native_max_value=maximum,
        native_step=1,
        native_unit_of_measurement=unit,
        icon=icon,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    )


# Registers, scales and bounds come from the unit's model metadata.
NUMBERS: tuple[EnerventNumberDescription, ...] = (
    _temperature(
        "winter_boost_limit_temperature",
        "Winter boost limit temperature",
        157,
        -10,
        20,
    ),
    _temperature(
        "summer_winter_limit_temperature",
        "Summer/winter limit temperature",
        137,
        -10,
        15,
    ),
    _temperature(
        "summer_night_cooling_start_temperature",
        "Summer night cooling start temperature",
        94,
        8,
        30,
    ),
    _temperature(
        "summer_night_cooling_stop_temperature",
        "Summer night cooling stop temperature",
        95,
        8,
        30,
    ),
    _temperature(
        "summer_night_cooling_min_outdoor_temperature",
        "Summer night cooling lowest outdoor temperature",
        93,
        8,
        30,
    ),
    _temperature(
        "summer_night_cooling_min_temperature_difference",
        "Summer night cooling min temperature difference",
        96,
        0,
        5,
    ),
    _percent(
        "summer_night_cooling_supply_air", "Summer night cooling supply air", 89
    ),
    _percent(
        "summer_night_cooling_extract_air", "Summer night cooling extract air", 90
    ),
    _plain(
        "summer_night_cooling_start_hour",
        "Summer night cooling start hour",
        98,
        0,
        23,
        UnitOfTime.HOURS,
        "mdi:clock-start",
    ),
    _plain(
        "summer_night_cooling_stop_hour",
        "Summer night cooling stop hour",
        99,
        0,
        23,
        UnitOfTime.HOURS,
        "mdi:clock-end",
    ),
    _percent("humidity_boost_limit", "Humidity boost limit", 69, minimum=10),
    _percent(
        "humidity_boost_threshold_48h",
        "Humidity boost 48 h threshold",
        70,
        minimum=0,
    ),
    EnerventNumberDescription(
        key="co2_boost_limit",
        name="CO2 boost limit",
        register=76,
        native_min_value=400,
        native_max_value=3000,
        native_step=50,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        icon="mdi:molecule-co2",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    _percent("away_supply_fan_speed", "Away supply fan speed", 100),
    _percent("away_extract_fan_speed", "Away extract fan speed", 102),
    _temperature(
        "away_temperature_drop", "Away temperature drop", 101, 0, 15
    ),
    _temperature(
        "away_long_temperature_drop", "Away long temperature drop", 103, 0, 15
    ),
    _percent("boost_supply_fan_speed", "Boost supply fan speed", 67),
    _percent("boost_extract_fan_speed", "Boost extract fan speed", 68),
    _percent("overpressure_supply_fan_speed", "Overpressure supply fan speed", 54),
    _percent(
        "overpressure_extract_fan_speed", "Overpressure extract fan speed", 55
    ),
    _plain(
        "overpressure_duration",
        "Overpressure duration",
        57,
        1,
        60,
        UnitOfTime.MINUTES,
        "mdi:timer-outline",
    ),
    _plain(
        "silent_mode_duration",
        "Silent mode duration",
        735,
        10,
        120,
        UnitOfTime.MINUTES,
        "mdi:timer-outline",
    ),
)


async def async_setup_entry(
    hass: Any,
    entry: EnerventConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Enervent setting numbers."""
    async_add_entities(EnerventNumber(entry, description) for description in NUMBERS)


class EnerventNumber(EnerventEntity, NumberEntity):
    """A numeric unit setting backed by one register."""

    entity_description: EnerventNumberDescription

    def __init__(
        self, entry: EnerventConfigEntry, description: EnerventNumberDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Only offer settings the unit actually reports."""
        return (
            super().available
            and self.entity_description.register in self.coordinator.data
        )

    @property
    def native_value(self) -> float | None:
        """Return the setting in display units."""
        value = self.coordinator.data.get(self.entity_description.register)
        if value is None:
            return None
        return value / self.entity_description.scale

    async def async_set_native_value(self, value: float) -> None:
        """Write the setting to the unit."""
        description = self.entity_description
        raw = round(value * description.scale)
        await self._async_write(
            lambda: self.coordinator.client.async_write_register(
                description.register, raw
            )
        )
