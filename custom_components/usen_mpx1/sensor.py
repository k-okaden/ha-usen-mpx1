"""Sensors for the USEN MPX-1."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import Mpx1Status
from .coordinator import Mpx1ConfigEntry, Mpx1Coordinator
from .entity import Mpx1Entity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class Mpx1SensorDescription(SensorEntityDescription):
    value_fn: Callable[[Mpx1Status], str | int | None]


SENSORS: tuple[Mpx1SensorDescription, ...] = (
    Mpx1SensorDescription(
        key="channel",
        translation_key="channel",
        value_fn=lambda s: s.channel_name or None,
    ),
    Mpx1SensorDescription(
        key="now_playing",
        translation_key="now_playing",
        value_fn=lambda s: s.now_playing or None,
    ),
    Mpx1SensorDescription(
        key="next_track",
        translation_key="next_track",
        value_fn=lambda s: s.next_tracks[0] if s.next_tracks and s.next_tracks[0] else None,
    ),
    Mpx1SensorDescription(
        key="volume",
        translation_key="volume",
        value_fn=lambda s: s.volume,
    ),
    Mpx1SensorDescription(
        key="line_status",
        translation_key="line_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.line_status,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Mpx1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(Mpx1Sensor(coordinator, description) for description in SENSORS)


class Mpx1Sensor(Mpx1Entity, SensorEntity):
    entity_description: Mpx1SensorDescription

    def __init__(self, coordinator: Mpx1Coordinator, description: Mpx1SensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | int | None:
        return self.entity_description.value_fn(self.coordinator.data.status)
