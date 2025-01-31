"""Platform for light integration."""

from __future__ import annotations

import logging
from pprint import pformat
import time
from typing import Any

import voluptuous as vol

from homeassistant.components.text import PLATFORM_SCHEMA, TextEntity
from homeassistant.const import CONF_ENTITIES, CONF_IP_ADDRESS, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .zonetouch3 import Zonetouch3

_LOGGER = logging.getLogger("ZoneTouch3")

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

    # loop though zone amount, create/entities objects per zone
    for zone_no in range(0, config[CONF_ENTITIES]):
        add_entities(
            [
                zonetouch_3_stats(
                    {
                        "name": config[CONF_NAME] + "System Value" + str(zone_no),
                        "address": config[CONF_IP_ADDRESS],
                        "port": config[CONF_PORT],
                        "zone": zone_no,
                    }
                )
            ]
        )

class zonetouch_3_stats(TextEntity):

    def __init__(self, text) -> None:
        _LOGGER.info(pformat(text))
        self.text = Zonetouch3(text["address"], text["port"], text["zone"])
        self._zone = text["zone"]
        self._confname = text["name"]
        time.sleep(2)
        self._name = text["name"]
        self._attr_unique_id = self._name
        time.sleep(0.5)
        self._attr_native_value = self.determine_type()
    
    def determine_type(self):
        match str(self._zone):
            case '0':
                self._attr_native_value = self.text.get_zonetouch_system_id()
            case '1':
                self._attr_native_value = self.text.get_zonetouch_system_name()
            case '2':
                self._attr_native_value = self.text.get_zonetouch_system_installer()
            case '3':
                self._attr_native_value = self.text.get_zonetouch_system_installer_number()
            case '4':
                self._attr_native_value = self.text.get_zonetouch_system_firmware()
            case '5':
                self._attr_native_value = self.text.get_zonetouch_console_version()

        return self._attr_native_value

    def set_value(self, value: str) -> None:
        self.determine_type()
        time.sleep(0.5)