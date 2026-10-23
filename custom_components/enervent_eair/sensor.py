"""Sensors for Enervent eAir."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EnerventConfigEntry
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class EnerventSensorDescription(SensorEntityDescription):
    """Describe a register-backed sensor."""

    register: int
    scale: float = 1


SENSORS: tuple[EnerventSensorDescription, ...] = (
    EnerventSensorDescription(
        key="room_temperature_te20",
        name="Room temperature TE20",
        register=1,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="room_temperature_te21",
        name="Room temperature TE21",
        register=2,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="supply_fan_speed",
        name="Supply fan speed",
        register=3,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="extract_fan_speed",
        name="Extract fan speed",
        register=4,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="outdoor_temperature",
        name="Outdoor temperature",
        register=6,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="supply_temperature_after_heat_recovery",
        name="Supply temperature after heat recovery",
        register=7,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="supply_temperature",
        name="Supply temperature",
        register=8,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="waste_air_temperature",
        name="Waste air temperature",
        register=9,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="extract_temperature",
        name="Extract temperature",
        register=10,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="extract_temperature_before_heat_recovery",
        name="Extract temperature before heat recovery",
        register=11,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="return_water_temperature",
        name="Return water temperature",
        register=12,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="extract_humidity",
        name="Extract air humidity",
        register=13,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="supply_filter_pressure_difference",
        name="Supply filter pressure difference",
        register=14,
        native_unit_of_measurement=UnitOfPressure.PA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="extract_filter_pressure_difference",
        name="Extract filter pressure difference",
        register=15,
        native_unit_of_measurement=UnitOfPressure.PA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="heat_recovery_efficiency_supply",
        name="Heat recovery efficiency supply",
        register=29,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="heat_recovery_efficiency_extract",
        name="Heat recovery efficiency extract",
        register=30,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="average_humidity_48h",
        name="Average humidity (48 h)",
        register=35,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="average_room_temperature",
        name="Average room temperature",
        register=46,
        scale=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnerventSensorDescription(
        key="service_reminder_days",
        name="Service reminder in days",
        register=538,
        native_unit_of_measurement="d",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: Any,
    entry: EnerventConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Enervent sensors."""
    async_add_entities(
        EnerventSensor(entry, description) for description in SENSORS
    )


class EnerventSensor(CoordinatorEntity, SensorEntity):
    """Represent one Enervent register as a sensor."""

    entity_description: EnerventSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: EnerventConfigEntry,
        description: EnerventSensorDescription,
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
    def native_value(self) -> int | float | None:
        """Return the scaled register value."""
        value = self.coordinator.data.get(self.entity_description.register)
        if value is None:
            return None
        return value / self.entity_description.scale
