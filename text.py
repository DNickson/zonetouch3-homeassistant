"""Platform for light integration."""

from __future__ import annotations

import logging
from pprint import pformat
import time
from datetime import timedelta
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

DOMAIN = "zonetouch3"
SCAN_INTERVAL = timedelta(seconds=7)

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
                    }, hass
                )
            ]
        )

    add_entities(
            [
                global_zonetouch_data(
                    {
                        "name": config[CONF_NAME] + "Global State" + "01",
                        "address": config[CONF_IP_ADDRESS],
                        "port": config[CONF_PORT],
                        "zone": zone_no,
                    }, hass
                )
            ]
        )

class zonetouch_3_stats(TextEntity):

    def __init__(self, text, hass) -> None:
        _LOGGER.info(pformat(text))
        self.text = Zonetouch3(text["address"], text["port"], text["zone"])
        self._zone = text["zone"]
        #self._name = text["name"]
        self._hass = hass
        self._attr_native_value = self.determine_type()

        match str(self._zone):
            case '0':
                self._name = "System ID"
                self._attr_unique_id = self._name
            case '1':
                self._name = "System Name"
                self._attr_unique_id = self._name
            case '2':
                self._name = "System Installer"
                self._attr_unique_id = self._name
            case '3':
                self._name = "Installer Number"
                self._attr_unique_id = self._name
            case '4':
                self._name = "Firmware Version"
                self._attr_unique_id = self._name
            case '5':
                self._name = self._name = "Console Version"
                self._attr_unique_id = self._name
    
    def determine_type(self):
        match str(self._zone):
            case '0':
                self._attr_native_value = self.text.return_system_id(self._hass.data[DOMAIN]['global_state'])
            case '1':
                self._attr_native_value = self.text.return_system_name(self._hass.data[DOMAIN]['global_state'])
            case '2':
                self._attr_native_value = self.text.return_system_installer(self._hass.data[DOMAIN]['global_state'])
            case '3':
                self._attr_native_value = self.text.return_installer_number(self._hass.data[DOMAIN]['global_state'])
            case '4':
                self._attr_native_value = self.text.return_firmware_version(self._hass.data[DOMAIN]['global_state'])
            case '5':
                self._attr_native_value = self.text.return_console_version(self._hass.data[DOMAIN]['global_state'])
            case '6':
                self._attr_native_value = self.text.return_console_temp(self._hass.data[DOMAIN]['global_state'])

        return self._attr_native_value

    def set_value(self, value: str) -> None:
        self.determine_type()
    
    def update(self) -> None:
        self.determine_type()

class global_zonetouch_data(TextEntity):

    def __init__(self, text, hass: HomeAssistant) -> None:
        _LOGGER.info(pformat(text))
        self._text = Zonetouch3(text["address"], text["port"], text["zone"])
        self._name = text["name"]
        self._attr_unique_id = self._name
        self._hass = hass
        self._attr_native_value = "Updater - Hide Me - I handle state updates"

    def set_value(self, value: str) -> None:
        if self._hass.data[DOMAIN]['global_state']:
            self._attr_native_value = "Updater - Hide Me - I handle state updates"
            self._hass.data[DOMAIN]['global_state'] = self._text.request_all_information()

    def update(self) -> None:
        if self._hass.data[DOMAIN]['global_state']:
            self._attr_native_value = "Updater - Hide Me - I handle state updates"
            self._hass.data[DOMAIN]['global_state'] = self._text.request_all_information()