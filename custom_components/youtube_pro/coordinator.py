"""Data coordinator for YouTube Pro."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
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
            data = await self.api.async_status()
        except YouTubeProInvalidAuth as error:
            self._async_clear_issue()
            raise ConfigEntryAuthFailed(str(error)) from error
        except YouTubeProApiError as error:
            self._async_set_issue(str(error))
            raise UpdateFailed(str(error)) from error
        self._async_clear_issue()
        return data

    def _async_set_issue(self, message: str) -> None:
        try:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                "cannot_connect",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="cannot_connect",
                translation_placeholders={"error": message[:200]},
            )
        except Exception:  # noqa: BLE001
            LOGGER.debug("Unable to create YouTube Pro repair issue", exc_info=True)

    def _async_clear_issue(self) -> None:
        try:
            ir.async_delete_issue(self.hass, DOMAIN, "cannot_connect")
        except Exception:  # noqa: BLE001
            LOGGER.debug("Unable to clear YouTube Pro repair issue", exc_info=True)
