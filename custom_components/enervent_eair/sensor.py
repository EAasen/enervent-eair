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
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EnerventConfigEntry
from .const import (
    DOMAIN,
    WEEK_PROGRAM_ACTIONS,
    WEEK_PROGRAM_SLOTS,
    WEEKDAY_BITS,
)
from .entity import EnerventEntity


@dataclass(frozen=True, kw_only=True)
class EnerventSensorDescription(SensorEntityDescription):
    """Describe a register-backed sensor."""

    register: int
    scale: float = 1
    options_map: dict[int, str] | None = None


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
    EnerventSensorDescription(
        key="software_version",
        name="Software version",
        register=599,
        scale=100,
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EnerventSensorDescription(
        key="hardware_version",
        name="Hardware version",
        register=598,
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EnerventSensorDescription(
        key="unit_family",
        name="Unit family",
        register=597,
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        options_map={
            0: "Pingvin", 1: "Pandion", 2: "Pelican", 3: "Pegasos",
            4: "Pegasos XL", 5: "LTR-3", 6: "LTR-6", 7: "LTR-7",
            8: "LTR-7 XL", 9: "LTR-2", 10: "Liggolo", 11: "Plaza",
            12: "Pingvin XL", 13: "Pallas", 14: "Perfect", 15: "LTR-4",
            16: "Alta", 17: "Salla", 18: "Neo", 19: "Pinion",
        },
    ),
    EnerventSensorDescription(
        key="heat_recovery_type",
        name="Heat recovery type",
        register=653,
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        options_map={0: "Heat recovery wheel", 1: "VG heat recovery"},
    ),
    EnerventSensorDescription(
        key="heater_type",
        name="Heater type",
        register=171,
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        options_map={
            0: "None",
            1: "Electrical SLP02",
            2: "CHG coil",
            3: "GWC earth tube",
        },
    ),
    EnerventSensorDescription(
        key="cooling_unit_type",
        name="Cooling unit type",
        register=154,
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        options_map={
            0: "No cooling unit", 1: "CW", 2: "HP", 3: "CG", 4: "CX",
            5: "CXINV", 8: "COOLER", 9: "CHG",
        },
    ),
)


async def async_setup_entry(
    hass: Any,
    entry: EnerventConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Enervent sensors."""
    async_add_entities(
        [
            *(EnerventSensor(entry, description) for description in SENSORS),
            EnerventWeekProgramSensor(entry),
        ]
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
    def native_value(self) -> int | float | str | None:
        """Return the scaled or named register value."""
        description = self.entity_description
        value = self.coordinator.data.get(description.register)
        if value is None:
            return None
        if description.options_map is not None:
            return description.options_map.get(int(value), f"Unknown ({value})")
        if description.scale == 1:
            return value
        return value / description.scale


def describe_week_program(program: dict[str, int]) -> dict[str, Any]:
    """Convert raw slot registers to readable values."""
    return {
        "slot": program["slot"],
        "weekdays": [
            day for day, bit in WEEKDAY_BITS.items() if program["weekdays"] & bit
        ],
        "start": f"{program['start_hour']:02d}:{program['start_minute']:02d}",
        "stop": f"{program['stop_hour']:02d}:{program['stop_minute']:02d}",
        "action": WEEK_PROGRAM_ACTIONS.get(
            program["action"], f"Unknown ({program['action']})"
        ),
    }


class EnerventWeekProgramSensor(EnerventEntity, SensorEntity):
    """Count configured weekly time programs and list them as attributes."""

    _attr_name = "Weekly time programs"
    _attr_icon = "mdi:calendar-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: EnerventConfigEntry) -> None:
        super().__init__(entry, "weekly_time_programs")

    def _programs(self) -> list[dict[str, Any]]:
        client = self.coordinator.client
        programs = []
        for slot in range(1, WEEK_PROGRAM_SLOTS + 1):
            program = client.get_week_program(slot)
            if program is not None and program["action"]:
                programs.append(describe_week_program(program))
        return programs

    @property
    def native_value(self) -> int:
        """Return how many slots have an action."""
        return len(self._programs())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the configured slots."""
        return {"programs": self._programs()}
