from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .zonetouch3 import Zonetouch3

DOMAIN = "zonetouch3"

"""The Zone Touch 3 Integration."""

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    zt3 = Zonetouch3("192.168.15.7", 7030, "0")

    hass.data[DOMAIN] = {'global_state': zt3.request_all_information()}

    return True