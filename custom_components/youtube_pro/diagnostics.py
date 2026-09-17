"""Diagnostics support for the YouTube Pro integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN, DOMAIN

TO_REDACT = (CONF_TOKEN,)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    data = dict(entry.data)
    for key in TO_REDACT:
        if key in data:
            data[key] = "**REDACTED**"
    coordinator = getattr(entry, "runtime_data", None)
    return {
        "domain": DOMAIN,
        "entry": {
            "title": entry.title,
            "state": str(entry.state),
            "data": data,
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": getattr(coordinator, "last_update_success", None),
            "data": getattr(coordinator, "data", None),
        },
    }
