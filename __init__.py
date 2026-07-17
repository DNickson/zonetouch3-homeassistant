"""The Polyaire ZoneTouch 3 integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .coordinator import ZoneTouch3ConfigEntry, ZoneTouch3Coordinator
from .zonetouch3 import ZoneTouch3Client

PLATFORMS = [Platform.FAN, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ZoneTouch3ConfigEntry) -> bool:
    """Set up ZoneTouch 3 from a config entry."""
    client = ZoneTouch3Client(entry.data[CONF_HOST], entry.data[CONF_PORT])
    coordinator = ZoneTouch3Coordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZoneTouch3ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
