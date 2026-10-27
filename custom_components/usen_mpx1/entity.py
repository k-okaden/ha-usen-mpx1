"""Base entity for the USEN MPX-1."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import Mpx1Coordinator


class Mpx1Entity(CoordinatorEntity[Mpx1Coordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: Mpx1Coordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        status = coordinator.data.status
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            connections={(CONNECTION_NETWORK_MAC, status.mac)} if status.mac else set(),
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"{MANUFACTURER} {MODEL}",
            serial_number=status.serial,
            sw_version=status.firmware,
            configuration_url=coordinator.client.base_url,
        )
