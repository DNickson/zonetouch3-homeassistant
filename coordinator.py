"""Data update coordinator for the Polyaire ZoneTouch 3 integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .zonetouch3 import (
    ZoneStatus,
    ZoneTouch3Client,
    ZoneTouch3Error,
    ZoneTouchState,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)

type ZoneTouch3ConfigEntry = ConfigEntry[ZoneTouch3Coordinator]


class ZoneTouch3Coordinator(DataUpdateCoordinator[ZoneTouchState]):
    """Polls the ZoneTouch 3 console and shares the state with all entities."""

    config_entry: ZoneTouch3ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ZoneTouch3ConfigEntry,
        client: ZoneTouch3Client,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> ZoneTouchState:
        try:
            return await self.client.async_get_state()
        except ZoneTouch3Error as err:
            raise UpdateFailed(f"Error communicating with ZoneTouch 3: {err}") from err

    def apply_zone_statuses(self, zones: dict[int, ZoneStatus]) -> None:
        """Merge the group status a control command returned into the data.

        The device answers every control command with a full group status
        message, so entities update immediately instead of waiting for the
        next poll. Names are not part of that message and are carried over.
        """
        for number, status in zones.items():
            existing = self.data.zones.get(number)
            if existing is not None:
                status.name = existing.name
            self.data.zones[number] = status
        self.async_set_updated_data(self.data)
