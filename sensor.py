"""Sensors for the Polyaire ZoneTouch 3: console temperature and system info."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ZoneTouch3ConfigEntry, ZoneTouch3Coordinator
from .entity import ZoneTouch3Entity
from .zonetouch3 import ZoneTouchState


@dataclass(frozen=True, kw_only=True)
class ZoneTouch3SensorDescription(SensorEntityDescription):
    """Describes a ZoneTouch 3 sensor."""

    value_fn: Callable[[ZoneTouchState], float | str | None]


SENSORS: tuple[ZoneTouch3SensorDescription, ...] = (
    ZoneTouch3SensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda state: state.system.temperature,
    ),
    ZoneTouch3SensorDescription(
        key="system_id",
        translation_key="system_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.system.system_id or None,
    ),
    ZoneTouch3SensorDescription(
        key="installer",
        translation_key="installer",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.system.installer or None,
    ),
    ZoneTouch3SensorDescription(
        key="installer_phone",
        translation_key="installer_phone",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.system.installer_phone or None,
    ),
    ZoneTouch3SensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.system.firmware_version or None,
    ),
    ZoneTouch3SensorDescription(
        key="console_version",
        translation_key="console_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.system.console_version or None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneTouch3ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ZoneTouch 3 sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        ZoneTouch3Sensor(coordinator, description) for description in SENSORS
    )


class ZoneTouch3Sensor(ZoneTouch3Entity, SensorEntity):
    """A sensor backed by a field of the coordinator data."""

    entity_description: ZoneTouch3SensorDescription

    def __init__(
        self,
        coordinator: ZoneTouch3Coordinator,
        description: ZoneTouch3SensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._device_id}_{description.key}"

    @property
    def native_value(self) -> float | str | None:
        return self.entity_description.value_fn(self.coordinator.data)
