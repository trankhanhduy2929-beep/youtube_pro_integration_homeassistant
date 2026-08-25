"""Diagnostic sensors for YouTube Pro."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YouTubeProConfigEntry, YouTubeProCoordinator


@dataclass(frozen=True, kw_only=True)
class YouTubeProSensorDescription(SensorEntityDescription):
    """Describe a diagnostic sensor."""

    value_fn: Callable[[Mapping[str, Any]], Any]
    attributes_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None


def transport_value(data: Mapping[str, Any]) -> str:
    """Summarize active cast transports."""
    values = {str(value) for value in (data.get("transports") or {}).values() if value}
    if not values:
        return "idle"
    if len(values) == 1:
        return values.pop()
    return "mixed"


SENSORS: tuple[YouTubeProSensorDescription, ...] = (
    YouTubeProSensorDescription(
        key="health",
        translation_key="health",
        icon="mdi:heart-pulse",
        device_class=SensorDeviceClass.ENUM,
        options=["ok", "degraded"],
        value_fn=lambda data: data.get("health", "degraded"),
        attributes_fn=lambda data: {
            "addon_version": data.get("version"),
            "api_version": data.get("api_version"),
            "home_assistant_connected": data.get("ha_ok"),
            "websocket_connected": data.get("websocket_connected"),
            "websocket_last_error": data.get("websocket_last_error"),
            "last_error": data.get("last_error"),
        },
    ),
    YouTubeProSensorDescription(
        key="extractor",
        translation_key="extractor",
        icon="mdi:youtube",
        value_fn=lambda data: data.get("extractor", "idle"),
        attributes_fn=lambda data: {
            "format_id": data.get("format_id"),
            "last_resolved_at": data.get("last_resolved_at"),
        },
    ),
    YouTubeProSensorDescription(
        key="resolve_time",
        translation_key="resolve_time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("resolve_ms"),
    ),
    YouTubeProSensorDescription(
        key="active_sessions",
        translation_key="active_sessions",
        icon="mdi:speaker-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("active_session_count", 0),
        attributes_fn=lambda data: {
            "sessions": data.get("sessions") or {},
            "queue_count": data.get("queue_count", 0),
            "timer_count": data.get("timer_count", 0),
            "playlists": data.get("playlists") or [],
        },
    ),
    YouTubeProSensorDescription(
        key="transport",
        translation_key="transport",
        icon="mdi:cast-audio",
        device_class=SensorDeviceClass.ENUM,
        options=["idle", "direct", "relay", "mixed"],
        value_fn=transport_value,
        attributes_fn=lambda data: {"entities": data.get("transports") or {}},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YouTubeProConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up diagnostic sensors."""
    async_add_entities(
        YouTubeProSensor(entry.runtime_data, entry, description)
        for description in SENSORS
    )


class YouTubeProSensor(
    CoordinatorEntity[YouTubeProCoordinator], SensorEntity
):
    """Representation of an add-on diagnostic sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YouTubeProCoordinator,
        entry: YouTubeProConfigEntry,
        description: YouTubeProSensorDescription,
    ) -> None:
        """Initialize a sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="YouTube Pro",
            manufacturer="YouTube Pro",
            model="Home Assistant Add-on",
            sw_version=str(coordinator.data.get("version") or "unknown"),
            configuration_url=coordinator.api.base_url,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return diagnostic attributes."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
