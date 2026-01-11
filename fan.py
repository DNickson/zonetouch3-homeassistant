"""Platform for fan integration."""

from __future__ import annotations

import logging
from pprint import pformat
from datetime import timedelta
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .zonetouch3 import Zonetouch3

_LOGGER = logging.getLogger("ZoneTouch3")

SCAN_INTERVAL = timedelta(seconds=5)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZoneTouch3 fan entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    zt3: Zonetouch3 = data["zt3"]
    global_state = data["global_state"]

    entities = []
    for zone_no in range(0, 8):
        entities.append(
            ZoneTouch3Fan(zt3, zone_no, global_state, entry.entry_id)
        )

    async_add_entities(entities)


class ZoneTouch3Fan(FanEntity):
    """Representation of a ZoneTouch3 zone fan."""

    _attr_icon = "mdi:air-conditioner"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    def __init__(
        self, zt3: Zonetouch3, zone: int, global_state: str, entry_id: str
    ) -> None:
        """Initialize the fan."""
        self._zt3 = zt3
        self._zone = zone
        self._entry_id = entry_id
        self._name = zt3.return_zone_name(global_state, str(zone))
        self._state = zt3.return_zone_state(global_state, str(zone))
        self._attr_percentage = zt3.return_zone_percentage(global_state, str(zone))
        self._attr_unique_id = f"{entry_id}_zone_{zone}"

    @property
    def name(self) -> str:
        """Return the display name of this fan."""
        return self._name

    @property
    def is_on(self) -> bool | None:
        """Return true if the entity is on."""
        return self._state

    def turn_on(self, **kwargs: Any) -> None:
        """Turn on the fan."""
        self._zt3.update_zone_state('03', 150)
        self._state = True

    def turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        self._zt3.update_zone_state('02', 150)
        self._state = False

    @property
    def percentage(self) -> int | None:
        """Return the current percentage."""
        return self._attr_percentage

    def set_percentage(self, percentage: int) -> None:
        """Set the fan percentage."""
        self._zt3.update_zone_state('80', percentage)
        self._attr_percentage = percentage

    def update(self) -> None:
        """Get live state of individual fan."""
        global_state = self.hass.data[DOMAIN][self._entry_id]["global_state"]
        if global_state:
            self._state = self._zt3.return_zone_state(global_state, str(self._zone))
            self._attr_percentage = self._zt3.return_zone_percentage(global_state, str(self._zone))
