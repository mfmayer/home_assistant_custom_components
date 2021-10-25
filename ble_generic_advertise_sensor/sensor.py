"""The example sensor integration."""
from __future__ import annotations
from . import sensors

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


async def async_setup_platform(hass, conf, async_add_entities, discovery_info=None):
    _LOGGER.warning("async_setup_platform()")
    sensor = Sensor(hass, conf)
    mac = conf.get(CONF_MAC)
    sensors[mac] = sensor
    async_add_entities(sensor.entities())
    return True


class Sensor:
    """Representation of a Sensor."""

    def __init__(self, hass, conf):
        """Initialize the sensor."""
        self._name = conf.get(CONF_NAME)
        _LOGGER.debug("__init__() called: %s", self._name)
        self._conf = conf
        self._hass = hass

        self._entities = []
        confEntities = conf.get("entities")
        for ce in confEntities:
            self._entities.append(Entity(self, ce))

        # self._state = None
        # self._test = 5
        # add_entities

    def name(self) -> str:
        return self._name

    def entities(self):
        return self._entities

    async def newData(self, hass, bytes):
        _LOGGER.debug("newData() called")


class Entity(SensorEntity):

    def __init__(self, sensor, entityConf):
        """Initialize the entity."""
        self._sensor = sensor
        self._entityConf = entityConf
        self._name = entityConf.get(CONF_NAME)
        self._value = None

    async def set_value(self, value):
        _LOGGER.debug("set_value() called")
        self._value = value
        self.async_schedule_update_ha_state()

    async def async_added_to_hass(self):
        _LOGGER.debug("async_added_to_hass() called")

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        _LOGGER.debug("name() called")
        return self._sensor.name() + "_" + self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        _LOGGER.debug("state() called")
        return self._value

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        _LOGGER.debug("unit_of_measurement() called")
        return TEMP_CELSIUS

    async def async_update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug("async_update() called")
