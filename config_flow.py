"""Config flow for the Polyaire ZoneTouch 3 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DOMAIN, MODEL
from .zonetouch3 import (
    DEFAULT_PORT,
    ZoneTouch3Client,
    ZoneTouch3ConnectionError,
    ZoneTouch3Error,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class ZoneTouch3ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZoneTouch 3."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the console address and verify we can talk to it."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = ZoneTouch3Client(user_input[CONF_HOST], user_input[CONF_PORT])
            try:
                state = await client.async_get_state()
            except ZoneTouch3ConnectionError as err:
                _LOGGER.error(
                    "Cannot connect to ZoneTouch 3 at %s:%s: %s",
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    err,
                )
                errors["base"] = "cannot_connect"
            except ZoneTouch3Error as err:
                _LOGGER.error(
                    "Unexpected response from ZoneTouch 3 at %s:%s: %s",
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    err,
                )
                errors["base"] = "invalid_response"
            except Exception:
                _LOGGER.exception("Unexpected error connecting to ZoneTouch 3")
                errors["base"] = "unknown"
            else:
                if state.system.system_id:
                    await self.async_set_unique_id(state.system.system_id)
                    self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=state.system.name or MODEL, data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
