"""Platform for sensor integration."""

from __future__ import annotations

import logging
from pprint import pformat
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .zonetouch3 import Zonetouch3

_LOGGER = logging.getLogger("ZoneTouch3")

SCAN_INTERVAL = timedelta(seconds=300)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZoneTouch3 sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    zt3: Zonetouch3 = data["zt3"]
    global_state = data["global_state"]

    async_add_entities([ZoneTouch3Temperature(zt3, global_state, entry.entry_id)])


class ZoneTouch3Temperature(SensorEntity):
    """Representation of a ZoneTouch3 temperature sensor."""

    def __init__(self, zt3: Zonetouch3, global_state: str, entry_id: str) -> None:
        """Initialize the sensor."""
        self._zt3 = zt3
        self._entry_id = entry_id
        self._name = "Temperature"
        self._attr_unique_id = f"{entry_id}_temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_value = zt3.return_console_temp(global_state)

    @property
    def name(self) -> str:
        """Return the display name of this sensor."""
        return self._name

    def update(self) -> None:
        """Update the sensor value."""
        global_state = self.hass.data[DOMAIN][self._entry_id]["global_state"]
        if global_state:
            self._attr_native_value = self._zt3.return_console_temp(global_state)
