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
from homeassistant.const import (CONF_NAME, CONF_MAC, CONF_UNIT_OF_MEASUREMENT, DATA_BYTES, TEMP_CELSIUS)
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
        self._unpackFormat = ""
        self._entities = []
        confEntities = conf.get("entities")
        for ce in confEntities:
            entityName = ce.get(CONF_NAME)
            entityUnit = ce.get(CONF_UNIT_OF_MEASUREMENT)
            self._entities.append(Entity(self, entityName, entityUnit))
            self._unpackFormat += ce.get("unpack_format")

    def name(self) -> str:
        return self._name

    def entities(self):
        return self._entities

    async def newData(self, bytes):
        _LOGGER.debug("newData() called - %s %s %d", self._unpackFormat, bytes.hex(), struct.calcsize(self._unpackFormat))
        if len(bytes) == struct.calcsize(self._unpackFormat):
            values = struct.unpack(self._unpackFormat, bytes)
            _LOGGER.info("newData() called: entities: %d | unpack_format: %s | len(values): %d", len(self._entities), self._unpackFormat, len(values))
            if len(values) == len(self._entities):
                i = 0
                while i < len(self._entities):
                    entity = self._entities[i]
                    await entity.set_value(values[i])
                    i = i + 1


class Entity(SensorEntity):

    def __init__(self, sensor, name, unit):
        """Initialize the entity."""
        self._sensor = sensor
        self._name = name
        self._unit = unit
        self._value = None

    async def set_value(self, value):
        _LOGGER.debug("set_value() called")
        self._value = value
        self.async_schedule_update_ha_state()

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
        return self._unit

    async def async_update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug("async_update() called")
