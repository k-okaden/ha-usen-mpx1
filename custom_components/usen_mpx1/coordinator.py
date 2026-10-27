"""Polling coordinator for the USEN MPX-1."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Mpx1Client, Mpx1Error, Mpx1Preset, Mpx1Status
from .const import DOMAIN, PRESET_REFRESH_POLLS, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type Mpx1ConfigEntry = ConfigEntry[Mpx1Coordinator]


@dataclass
class Mpx1Data:
    status: Mpx1Status
    presets: list[Mpx1Preset] = field(default_factory=list)


class Mpx1Coordinator(DataUpdateCoordinator[Mpx1Data]):
    """Polls /data/home.csv and (occasionally) the preset list."""

    config_entry: Mpx1ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: Mpx1ConfigEntry, client: Mpx1Client) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self._presets: list[Mpx1Preset] = []
        self._polls_since_presets = PRESET_REFRESH_POLLS

    async def _async_update_data(self) -> Mpx1Data:
        try:
            status = await self.client.get_status()
        except Mpx1Error as err:
            raise UpdateFailed(str(err)) from err

        self._polls_since_presets += 1
        if status.power and (not self._presets or self._polls_since_presets >= PRESET_REFRESH_POLLS):
            try:
                if presets := await self.client.get_presets():
                    self._presets = presets
                    self._polls_since_presets = 0
            except Mpx1Error as err:
                _LOGGER.debug("Could not read presets: %s", err)

        return Mpx1Data(status=status, presets=self._presets)
