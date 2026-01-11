"""Platform for text integration."""

from __future__ import annotations

import logging
from pprint import pformat
from datetime import timedelta

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .zonetouch3 import Zonetouch3

_LOGGER = logging.getLogger("ZoneTouch3")

SCAN_INTERVAL = timedelta(seconds=7)

TEXT_TYPES = [
    ("0", "System ID", "return_system_id"),
    ("1", "System Name", "return_system_name"),
    ("2", "System Installer", "return_system_installer"),
    ("3", "Installer Number", "return_installer_number"),
    ("4", "Firmware Version", "return_firmware_version"),
    ("5", "Console Version", "return_console_version"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZoneTouch3 text entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    zt3: Zonetouch3 = data["zt3"]
    global_state = data["global_state"]

    entities = []
    for zone_id, name, method in TEXT_TYPES:
        entities.append(ZoneTouch3Stats(zt3, zone_id, name, method, global_state, entry.entry_id))

    # Add the global state updater entity
    entities.append(ZoneTouch3GlobalUpdater(zt3, global_state, entry.entry_id))

    async_add_entities(entities)


class ZoneTouch3Stats(TextEntity):
    """Representation of a ZoneTouch3 stats text entity."""

    def __init__(
        self,
        zt3: Zonetouch3,
        zone_id: str,
        name: str,
        method: str,
        global_state: str,
        entry_id: str,
    ) -> None:
        """Initialize the text entity."""
        self._zt3 = zt3
        self._zone_id = zone_id
        self._method = method
        self._entry_id = entry_id
        self._name = name
        self._attr_unique_id = f"{entry_id}_{name.lower().replace(' ', '_')}"
        self._attr_native_value = self._get_value(global_state)

    def _get_value(self, global_state: str) -> str:
        """Get the value from the ZoneTouch3 device."""
        method_func = getattr(self._zt3, self._method)
        return method_func(global_state)

    @property
    def name(self) -> str:
        """Return the display name of this entity."""
        return self._name

    def set_value(self, value: str) -> None:
        """Set value (read-only, just refreshes)."""
        global_state = self.hass.data[DOMAIN][self._entry_id]["global_state"]
        if global_state:
            self._attr_native_value = self._get_value(global_state)

    def update(self) -> None:
        """Update the entity value."""
        global_state = self.hass.data[DOMAIN][self._entry_id]["global_state"]
        if global_state:
            self._attr_native_value = self._get_value(global_state)


class ZoneTouch3GlobalUpdater(TextEntity):
    """Entity that handles global state updates."""

    def __init__(self, zt3: Zonetouch3, global_state: str, entry_id: str) -> None:
        """Initialize the updater entity."""
        self._zt3 = zt3
        self._entry_id = entry_id
        self._name = "Global State Updater"
        self._attr_unique_id = f"{entry_id}_global_updater"
        self._attr_native_value = "Updater - Hide Me - I handle state updates"

    @property
    def name(self) -> str:
        """Return the display name of this entity."""
        return self._name

    def set_value(self, value: str) -> None:
        """Refresh global state."""
        self._attr_native_value = "Updater - Hide Me - I handle state updates"
        self.hass.data[DOMAIN][self._entry_id]["global_state"] = self._zt3.request_all_information()

    def update(self) -> None:
        """Update global state."""
        self._attr_native_value = "Updater - Hide Me - I handle state updates"
        self.hass.data[DOMAIN][self._entry_id]["global_state"] = self._zt3.request_all_information()
