"""Data coordinator for YouTube Pro."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    YouTubeProApi,
    YouTubeProApiError,
    YouTubeProInvalidAuth,
)
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN, LOGGER

YouTubeProConfigEntry = ConfigEntry["YouTubeProCoordinator"]


class YouTubeProCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll diagnostic and playback state from the add-on."""

    config_entry: YouTubeProConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: YouTubeProConfigEntry,
        api: YouTubeProApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_status()
        except YouTubeProInvalidAuth as error:
            raise ConfigEntryAuthFailed(str(error)) from error
        except YouTubeProApiError as error:
            raise UpdateFailed(str(error)) from error
