"""Platform for light integration."""

from __future__ import annotations

import logging
from pprint import pformat
import time
from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_ENTITIES, CONF_IP_ADDRESS, CONF_NAME, CONF_PORT, UnitOfTemperature
from homeassistant.core import HomeAssistant

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .zonetouch3 import Zonetouch3

_LOGGER = logging.getLogger("ZoneTouch3")

DOMAIN = "zonetouch3"
SCAN_INTERVAL = timedelta(seconds=300)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default ="zonetouch3"): cv.string,
    vol.Optional(CONF_ENTITIES, default ="8"): cv.positive_int,
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional(CONF_PORT, default = 7030): cv.port,
})

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    "Setup the platform"
    _LOGGER.info(pformat(config))

    add_entities(
            [
                zonetouch_3_temp(
                    {
                        "name": config[CONF_NAME] + "Global State" + "01",
                        "address": config[CONF_IP_ADDRESS],
                        "port": config[CONF_PORT],
                        "zone": "0",
                    }, hass
                )
            ]
        )

class zonetouch_3_temp(SensorEntity):

    def __init__(self, sensor, hass) -> None:
        _LOGGER.info(pformat(sensor))
        self.sensor = Zonetouch3(sensor["address"], sensor["port"], sensor["zone"])
        self._hass = hass
        self._name = "Temperature"
        self._attr_unique_id = self._name
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_value = self.sensor.return_console_temp(self._hass.data[DOMAIN]['global_state'])
        

    def update(self) -> None:
        self._attr_native_value = self.sensor.return_console_temp(self._hass.data[DOMAIN]['global_state'])