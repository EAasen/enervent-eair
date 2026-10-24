"""Binary sensors for Enervent eAir."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EnerventConfigEntry
from .const import DOMAIN, REGISTER_MODE

_HRC_DEFROSTING_BIT = 32768


@dataclass(frozen=True, kw_only=True)
class EnerventBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a register-backed binary sensor."""

    register: int | None = None
    mode_bit: int | None = None


SENSORS = (
    EnerventBinarySensorDescription(
        key="alarm_a",
        name="Alarm A",
        register=10041,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    EnerventBinarySensorDescription(
        key="alarm_b",
        name="Alarm B",
        register=10042,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    EnerventBinarySensorDescription(
        key="hrc_defrosting",
        name="Heat recovery defrosting",
        register=REGISTER_MODE,
        mode_bit=_HRC_DEFROSTING_BIT,
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    EnerventBinarySensorDescription(
        key="clock_program_active",
        name="Time program active",
        register=10043,
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
)


async def async_setup_entry(
    hass: Any,
    entry: EnerventConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up Enervent binary sensors."""
    async_add_entities(
        EnerventBinarySensor(entry, description) for description in SENSORS
    )


class EnerventBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Represent an Enervent alarm or operating state."""

    entity_description: EnerventBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: EnerventConfigEntry,
        description: EnerventBinarySensorDescription,
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
        """Return whether the alert or operating state is active."""
        value = self.coordinator.data.get(self.entity_description.register)
        if value is None:
            return None
        if self.entity_description.mode_bit is not None:
            return bool(int(value) & self.entity_description.mode_bit)
        return bool(value)
