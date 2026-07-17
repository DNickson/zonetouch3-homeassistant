"""Base entity for the Polyaire ZoneTouch 3 integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ZoneTouch3Coordinator


class ZoneTouch3Entity(CoordinatorEntity[ZoneTouch3Coordinator]):
    """Common device registration for all ZoneTouch 3 entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ZoneTouch3Coordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        system = coordinator.data.system
        self._device_id = entry.unique_id or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=system.name or MODEL,
            sw_version=system.firmware_version or None,
        )
