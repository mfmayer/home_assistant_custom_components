"""The example sensor integration."""
from __future__ import annotations
from threading import Thread
import time
import logging
import asyncio
import struct
import threading
from typing import Final

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (CONF_NAME, CONF_MAC, DATA_BYTES, TEMP_CELSIUS)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

sensors = {}


async def async_setup(hass: HomeAssistant, config):
    _LOGGER.debug("async_setup()")
    x = threading.Thread(target=thread_func, args=(hass,), daemon=True)
    x.start()
    return True


def thread_func(hass):
    _LOGGER.debug("thread_func()")
    while True:
        time.sleep(5)
        _LOGGER.debug("thread_func() - running")
