"""The USEN MPX-1 integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Mpx1Client
from .coordinator import Mpx1ConfigEntry, Mpx1Coordinator

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: Mpx1ConfigEntry) -> bool:
    client = Mpx1Client(async_get_clientsession(hass), entry.data[CONF_HOST])
    coordinator = Mpx1Coordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Mpx1ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
