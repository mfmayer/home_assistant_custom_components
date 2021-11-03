"""The example sensor integration."""
from __future__ import annotations

from threading import Thread
import time
import logging
import asyncio
import struct
import threading
from typing import Final

from .sensor import devices

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (CONF_NAME, CONF_MAC, DATA_BYTES, TEMP_CELSIUS)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

try:
    from bleak import BleakScanner
except Exception as e:
    _LOGGER.error("error while loading bleak: %s", e)

hass = None


async def async_setup(hass: HomeAssistant, config):
    _LOGGER.debug("async_setup()")
    x = threading.Thread(target=thread_func, args=(hass,), daemon=True)
    x.start()
    return True


def thread_func(_hass):
    _LOGGER.debug("thread_func()")
    global hass
    hass = _hass
    asyncio.run(thread_handler())


async def thread_handler():
    _LOGGER = logging.getLogger(__name__)
    _LOGGER.debug("thread_handler()")
    global hass
    global devices

    def detection_callback(device, advertisement_data):
        # print(device.address, "RSSI:", device.rssi, advertisement_data)
        mac = device.address.lower()
        if mac in devices:
            bleDevice = devices.get(mac)
            for manu_id in advertisement_data.manufacturer_data:
                if manu_id in bleDevice.ads:
                    ad = bleDevice.ads.get(manu_id)
                    manufacturer_data = advertisement_data.manufacturer_data.get(manu_id)
                    asyncio.run_coroutine_threadsafe(
                        ad.update(manufacturer_data), hass.loop)

    while True:
        try:
            scanner = BleakScanner()
            scanner.register_detection_callback(detection_callback)
            await scanner.start()
            await asyncio.sleep(360.0)
            await scanner.stop()
        except Exception as e:
            _LOGGER.error(e)
            await asyncio.sleep(360.0)
