"""The YouTube Pro integration."""

from __future__ import annotations

from collections.abc import Awaitable
from datetime import time
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_URL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import YouTubeProApi, YouTubeProApiError
from .const import (
    CONF_CONFIG_ENTRY_ID,
    CONF_TOKEN,
    DOMAIN,
    REPEAT_MODES,
    SERVICE_ENQUEUE,
    SERVICE_PLAY,
    SERVICE_PLAY_PLAYLIST,
    SERVICE_SET_TIMER,
    TIMER_TYPES,
)
from .coordinator import YouTubeProConfigEntry, YouTubeProCoordinator

PLATFORMS = [Platform.SENSOR, Platform.MEDIA_PLAYER]


def media_player_entity(value: Any) -> str:
    """Validate one media_player entity ID."""
    entity_id = cv.entity_id(value)
    if not entity_id.startswith("media_player."):
        raise vol.Invalid("Expected a media_player entity")
    return entity_id


PLAY_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_ENTITY_ID): media_player_entity,
        vol.Required("url"): cv.url,
        vol.Optional("title", default="YouTube"): cv.string,
        vol.Optional("repeat", default="off"): vol.In(REPEAT_MODES),
        vol.Optional("shuffle", default=False): cv.boolean,
    }
)

PLAY_PLAYLIST_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_ENTITY_ID): media_player_entity,
        vol.Required("playlist_name"): cv.string,
        vol.Optional("index", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("repeat", default="all"): vol.In(REPEAT_MODES),
        vol.Optional("shuffle", default=False): cv.boolean,
    }
)

ENQUEUE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required("url"): cv.url,
        vol.Optional("title", default="YouTube"): cv.string,
    }
)

SET_TIMER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("id"): cv.string,
        vol.Required(ATTR_ENTITY_ID): media_player_entity,
        vol.Required("time"): cv.time,
        vol.Optional("action", default="play"): vol.In(TIMER_TYPES),
        vol.Optional("playlist_name", default=""): cv.string,
        vol.Optional("days", default=[]): [
            vol.All(vol.Coerce(int), vol.Range(min=0, max=6))
        ],
        vol.Optional("shuffle", default=True): cv.boolean,
        vol.Optional("enabled", default=True): cv.boolean,
        vol.Optional("duration", default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=720)
        ),
    }
)


def coordinator_for_call(
    hass: HomeAssistant, call: ServiceCall
) -> YouTubeProCoordinator:
    """Resolve a loaded coordinator for a service call."""
    requested = call.data.get(CONF_CONFIG_ENTRY_ID)
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if requested:
        entries = [entry for entry in entries if entry.entry_id == requested]
    if not entries:
        raise HomeAssistantError("YouTube Pro integration chưa được tải")
    return entries[0].runtime_data


async def refresh_after_service(
    coordinator: YouTubeProCoordinator, operation: Awaitable[Any]
) -> None:
    """Execute an API operation and refresh coordinator data."""
    try:
        await operation
    except YouTubeProApiError as error:
        raise HomeAssistantError(str(error)) from error
    await coordinator.async_request_refresh()


async def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_PLAY):
        return

    async def async_play(call: ServiceCall) -> None:
        coordinator = coordinator_for_call(hass, call)
        await refresh_after_service(
            coordinator,
            coordinator.api.async_play(
                call.data[ATTR_ENTITY_ID],
                call.data["url"],
                call.data["title"],
                call.data["repeat"],
                call.data["shuffle"],
            ),
        )

    async def async_play_playlist(call: ServiceCall) -> None:
        coordinator = coordinator_for_call(hass, call)
        await refresh_after_service(
            coordinator,
            coordinator.api.async_play_playlist(
                call.data[ATTR_ENTITY_ID],
                call.data["playlist_name"],
                call.data["index"],
                call.data["repeat"],
                call.data["shuffle"],
            ),
        )

    async def async_enqueue(call: ServiceCall) -> None:
        coordinator = coordinator_for_call(hass, call)
        await refresh_after_service(
            coordinator,
            coordinator.api.async_enqueue(call.data["url"], call.data["title"]),
        )

    async def async_set_timer(call: ServiceCall) -> None:
        coordinator = coordinator_for_call(hass, call)
        run_time = call.data["time"]
        if isinstance(run_time, time):
            run_time = run_time.strftime("%H:%M")
        payload = {
            "entity_id": call.data[ATTR_ENTITY_ID],
            "time": str(run_time),
            "type": call.data["action"],
            "playlist_name": call.data["playlist_name"],
            "days": call.data["days"],
            "is_random": call.data["shuffle"],
            "enabled": call.data["enabled"],
            "duration": call.data["duration"],
        }
        if call.data.get("id"):
            payload["id"] = call.data["id"]
        await refresh_after_service(
            coordinator,
            coordinator.api.async_set_timer(payload),
        )

    hass.services.async_register(
        DOMAIN, SERVICE_PLAY, async_play, schema=PLAY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_PLAYLIST,
        async_play_playlist,
        schema=PLAY_PLAYLIST_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ENQUEUE, async_enqueue, schema=ENQUEUE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_TIMER, async_set_timer, schema=SET_TIMER_SCHEMA
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: YouTubeProConfigEntry
) -> bool:
    """Set up YouTube Pro from a config entry."""
    api = YouTubeProApi(
        async_get_clientsession(hass),
        entry.data[CONF_URL],
        entry.data[CONF_TOKEN],
    )
    coordinator = YouTubeProCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_services(hass)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        for service in (
            SERVICE_PLAY,
            SERVICE_PLAY_PLAYLIST,
            SERVICE_ENQUEUE,
            SERVICE_SET_TIMER,
        ):
            hass.services.async_remove(DOMAIN, service)
    return unloaded
