"""Config flow for ZoneTouch3 integration."""
from __future__ import annotations

import logging
import socket
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DOMAIN, DEFAULT_PORT
from .zonetouch3 import Zonetouch3

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class ZoneTouch3ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZoneTouch3."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)

            # Check if already configured
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Test connection
            try:
                zt3 = Zonetouch3(host, port, "0")
                result = await self.hass.async_add_executor_job(
                    zt3.request_all_information
                )
                if result:
                    system_name = await self.hass.async_add_executor_job(
                        zt3.return_system_name, result
                    )
                    title = system_name if system_name else f"ZoneTouch3 ({host})"
                    return self.async_create_entry(title=title, data=user_input)
            except socket.error:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
