"""Media player for the USEN MPX-1."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import CHANNEL_AUX, VOLUME_MAX, Mpx1Error
from .const import DOMAIN, SERVICE_PLAY_CUE, SERVICE_STOP_CUE, SOURCE_AUX
from .coordinator import Mpx1ConfigEntry, Mpx1Coordinator
from .entity import Mpx1Entity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Mpx1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([Mpx1MediaPlayer(entry.runtime_data)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_PLAY_CUE,
        {
            vol.Required("cue"): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
            vol.Optional("volume", default=0): vol.All(vol.Coerce(int), vol.Range(min=-6, max=6)),
            vol.Optional("repeat", default=False): cv.boolean,
            vol.Optional("mute_bgm", default=False): cv.boolean,
        },
        "async_play_cue",
    )
    platform.async_register_entity_service(SERVICE_STOP_CUE, None, "async_stop_cue")


class Mpx1MediaPlayer(Mpx1Entity, MediaPlayerEntity):
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_media_content_type = MediaType.MUSIC
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, coordinator: Mpx1Coordinator) -> None:
        super().__init__(coordinator, "media_player")

    @property
    def _status(self):
        return self.coordinator.data.status

    @property
    def state(self) -> MediaPlayerState:
        return MediaPlayerState.PLAYING if self._status.power else MediaPlayerState.OFF

    @property
    def volume_level(self) -> float:
        return self._status.volume / VOLUME_MAX

    @property
    def source_list(self) -> list[str]:
        return [p.name for p in self.coordinator.data.presets] + [SOURCE_AUX]

    @property
    def source(self) -> str | None:
        return self._status.channel_name or None

    @property
    def media_title(self) -> str | None:
        return self._status.title or None

    @property
    def media_artist(self) -> str | None:
        return self._status.artist

    @property
    def media_channel(self) -> str | None:
        return self._status.channel_name or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "volume_raw": self._status.volume,
            "preset": self._status.preset,
            "next_tracks": self._status.next_tracks,
        }

    async def _run(self, call: Awaitable[Any]) -> None:
        try:
            await call
        except Mpx1Error as err:
            raise HomeAssistantError(f"USEN MPX-1: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self._run(self.coordinator.client.power_on())

    async def async_turn_off(self) -> None:
        await self._run(self.coordinator.client.power_off())

    async def async_volume_up(self) -> None:
        await self._run(self.coordinator.client.volume_step(True))

    async def async_volume_down(self) -> None:
        await self._run(self.coordinator.client.volume_step(False))

    async def async_set_volume_level(self, volume: float) -> None:
        await self._run(
            self.coordinator.client.set_volume(round(volume * VOLUME_MAX), self._status.volume)
        )

    async def async_select_source(self, source: str) -> None:
        if source == SOURCE_AUX:
            chn = CHANNEL_AUX
        else:
            preset = next((p for p in self.coordinator.data.presets if p.name == source), None)
            if preset is None:
                raise ServiceValidationError(f"Unknown source: {source}")
            chn = preset.number
        await self._run(self.coordinator.client.select_channel(chn))

    async def async_play_cue(
        self, cue: int, volume: int = 0, repeat: bool = False, mute_bgm: bool = False
    ) -> None:
        client = self.coordinator.client
        args = {"volume": volume + 6, "repeat": repeat, "mute_bgm": mute_bgm}

        async def _play() -> None:
            # Same sequence as the web UI: select the cue, then press play.
            await client.cue(cue, 0, **args)
            await client.cue(cue, 2, **args)

        await self._run(_play())

    async def async_stop_cue(self) -> None:
        await self._run(self.coordinator.client.cue(1, 3))
