"""The example sensor integration."""
from __future__ import annotations
# from . import sensors

import time
import logging
import asyncio
import struct
import threading

from typing import Final

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
# from homeassistant.const import ()
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

# logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
#                     datefmt='%Y-%m-%d:%H:%M:%S',
#                     level=logging.WARNING, force=True)

_LOGGER = logging.getLogger(__name__)


try:
    from bleak import BleakScanner, BleakClient
except:
    _LOGGER.error("Error while loading bleak")

devices = {}


class Device:
    def __init__(self, name: str, mac: str):
        self.name = name
        self.mac = mac
        self._ads = {}
        self._reads = {}


class DataSource:
    def __init__(self, device: Device, name: str, conf: dict, should_poll: bool = True):
        self.device = device
        self.name = name
        self.prefix = conf.get("prefix")
        self.unpack_format = conf.get("unpack_format")
        self.should_poll = should_poll
        self.lock = threading.Lock()
        self.unpackedData = []
        self.entites = []
        if "entities" in conf:
            entConfs = conf.get("entities")
            _LOGGER.debug("Adding entities: %d", len(entConfs))
            for entConf in entConfs:
                entity = Entity(self, entConf)
                self.entites.append(entity)
        else:
            _LOGGER.debug("Adding entities: 0")

    async def fetchUpdate(self):
        with self.lock:
            return

    async def dataValue(self, index: int):
        with self.lock:
            return self.unpackedData[index]


class AdDataSource(DataSource):
    def __init__(self, device: Device, name: str, adConf: dict):
        self._company_id = adConf.get("company_id")
        super().__init__(device, name, adConf, False)

    async def update(self, data: bytearray):
        unpacked = struct.unpack(self.unpack_format, data)
        with self.lock:
            if self._prefix == None:
                self.unpackedData = unpacked
            elif unpacked[0] == self._prefix:
                self.unpackedData = unpacked
        for entity in self._entites:
            entity.async_schedule_update_ha_state()


class ReadDataSource(DataSource):
    def __init__(self, device: Device, name: str, readConf: dict):
        # char_uuid: str, unpack_format: str, interval: int, prefix=None
        self._char_uuid = readConf.get("uuid")
        self._interval = readConf.get("interval")
        self._last_update = -1
        super().__init__(device, name, readConf, True)

    async def fetchUpdate(self):
        if time.monotonic() - self._last_update < self._interval:
            return

        _LOGGER.debug("Fetching update for source: %s", self.name)
        self._last_update = time.monotonic()
        try:
            client = BleakClient(self.device.mac, timeout=5)
            await client.connect()
            gattChar = await client.read_gatt_char(self._char_uuid)
            unpacked = struct.unpack(self.unpack_format, gattChar)
            with self.lock:
                _LOGGER.debug("Data retrieved from source: %s", self.name)
                if self.prefix == None:
                    self.unpackedData = unpacked
                elif unpacked[0] == self.prefix:
                    self.unpackedData = unpacked

        except Exception as e:
            _LOGGER.warning(e)


class Entity(SensorEntity):

    def __init__(self, datasource: DataSource, config: dict):
        """creates entity from config."""
        self._datasource = datasource
        self._index = config.get("index")
        self._name = config.get("name")
        self._unit = config.get("unit_of_measurement")
        self._device_class = config.get("device_class")
        self._icon = config.get("icon")
        self._factor = config.get("factor")
        if self._factor == None:
            self._factor = 1.0
        self._round = config.get("round")
        if self._round == None:
            self._round = 0

    async def updated(self):
        _LOGGER.debug("updated() called")
        self.async_schedule_update_ha_state()

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.
        False if entity pushes its state to HA.
        """
        return self._datasource.should_poll

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._datasource.device.name + "-" + self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._index < len(self._datasource.unpackedData):
            try:
                value = self._datasource.unpackedData[self._index]
                return round(value * self._factor, self._round)
            except Exception as e:
                _LOGGER.warning(e)

        return None

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def device_class(self):
        """Return the icon of the sensor."""
        return self._device_class

    async def async_update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        await self._datasource.fetchUpdate()


async def async_setup_platform(hass, conf, async_add_entities, discovery_info=None):
    _LOGGER.debug("async_setup_platform()")
    readsConf = conf.get("reads")
    adsConf = conf.get("ads")
    entitiesToRegister = []
    for deviceConf in conf.get("devices"):
        name = deviceConf.get("name")
        mac = deviceConf.get("mac")
        device = Device(name, mac)
        _LOGGER.debug("Creating device: %s", mac)
        if "ads" in deviceConf:
            for adKey in deviceConf.get("ads"):
                _LOGGER.debug("Adding advertirsement: %s", adKey)
                try:
                    adConf = adsConf.get(adKey)
                    if adConf != None:
                        ad = AdDataSource(device, adKey, adConf)
                        entitiesToRegister.extend(ad.entites)
                    else:
                        _LOGGER.warning("Advertisement (\"ads\") config missing: %s", adKey)
                except Exception as e:
                    _LOGGER.error(e)

        if "reads" in deviceConf:
            for readKey in deviceConf.get("reads"):
                _LOGGER.debug("Adding read characteristic: %s", readKey)
                try:
                    readConf = readsConf.get(readKey)
                    if readConf != None:
                        read = ReadDataSource(device, readKey, readConf)
                        entitiesToRegister.extend(read.entites)
                    else:
                        _LOGGER.warning("Characteristic read (\"reads\") config missing: %s", readKey)
                except:
                    _LOGGER.error(e)

        devices[mac] = device

    print(entitiesToRegister)
    _LOGGER.debug("entities: %d", len(entitiesToRegister))
    async_add_entities(entitiesToRegister, True)

    return True