"""Fan entities representing ZoneTouch 3 zone dampers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ZoneTouch3ConfigEntry, ZoneTouch3Coordinator
from .entity import ZoneTouch3Entity
from .zonetouch3 import PowerCommand, PowerState, ZoneStatus, ZoneTouch3Error

PRESET_TURBO = "turbo"
PERCENTAGE_STEP = 5  # the console adjusts the open percentage in 5% steps


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneTouch3ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one fan per zone reported by the device."""
    coordinator = entry.runtime_data
    async_add_entities(
        ZoneTouch3Fan(coordinator, number) for number in sorted(coordinator.data.zones)
    )


class ZoneTouch3Fan(ZoneTouch3Entity, FanEntity):
    """A single ZoneTouch 3 zone damper."""

    _attr_icon = "mdi:air-conditioner"
    _attr_speed_count = 100 // PERCENTAGE_STEP

    def __init__(self, coordinator: ZoneTouch3Coordinator, zone_number: int) -> None:
        super().__init__(coordinator)
        self._zone_number = zone_number
        self._attr_unique_id = f"{self._device_id}_zone_{zone_number}"

        features = (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
        )
        if coordinator.data.zones[zone_number].turbo_supported:
            features |= FanEntityFeature.PRESET_MODE
            self._attr_preset_modes = [PRESET_TURBO]
        self._attr_supported_features = features

    @property
    def _zone(self) -> ZoneStatus | None:
        return self.coordinator.data.zones.get(self._zone_number)

    @property
    def available(self) -> bool:
        return super().available and self._zone is not None

    @property
    def name(self) -> str:
        zone = self._zone
        if zone is not None and zone.name:
            return zone.name
        return f"Zone {self._zone_number + 1}"

    @property
    def is_on(self) -> bool | None:
        zone = self._zone
        return zone.is_on if zone is not None else None

    @property
    def percentage(self) -> int | None:
        zone = self._zone
        return zone.percentage if zone is not None else None

    @property
    def preset_mode(self) -> str | None:
        zone = self._zone
        if zone is not None and zone.power is PowerState.TURBO:
            return PRESET_TURBO
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        zone = self._zone
        if zone is None:
            return None
        return {"zone_number": self._zone_number, "spill_active": zone.spill_active}

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Open the zone, optionally at a given percentage or in turbo."""
        if preset_mode == PRESET_TURBO:
            await self._async_control(power=PowerCommand.TURBO)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self._async_control(power=PowerCommand.ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Close the zone."""
        await self._async_control(power=PowerCommand.OFF)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the zone open percentage, turning it on if needed."""
        if percentage == 0:
            await self._async_control(power=PowerCommand.OFF)
        else:
            await self._async_control(power=PowerCommand.ON, percentage=percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the zone to turbo."""
        if preset_mode == PRESET_TURBO:
            await self._async_control(power=PowerCommand.TURBO)

    async def _async_control(
        self, power: PowerCommand = PowerCommand.KEEP, percentage: int | None = None
    ) -> None:
        try:
            zones = await self.coordinator.client.async_set_zone(
                self._zone_number, power=power, percentage=percentage
            )
        except ZoneTouch3Error as err:
            raise HomeAssistantError(
                f"Failed to control zone {self.name}: {err}"
            ) from err
        self.coordinator.apply_zone_statuses(zones)
