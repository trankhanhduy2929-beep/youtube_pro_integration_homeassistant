"""Config flow for YouTube Pro."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_URL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .addon_discovery import (
    async_discover_addon_urls,
    is_auto_url,
    normalize_addon_url,
)
from .api import (
    YouTubeProApi,
    YouTubeProApiError,
    YouTubeProCannotConnect,
    YouTubeProInvalidAuth,
)
from .const import CONF_DEFAULT_ENTITY_ID, CONF_TOKEN, DEFAULT_URL, DOMAIN


def normalize_base_url(value: str) -> str:
    """Validate and normalize an add-on base URL."""
    if is_auto_url(value):
        return DEFAULT_URL
    validated = cv.url(value.strip())
    parsed = urlsplit(validated)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise vol.Invalid("invalid_url")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def user_schema(default_url: str = DEFAULT_URL) -> vol.Schema:
    """Return the config form schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_URL, default=default_url): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(CONF_TOKEN): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_DEFAULT_ENTITY_ID): EntitySelector(
                EntitySelectorConfig(domain="media_player")
            ),
        }
    )


class YouTubeProConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle YouTube Pro configuration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return YouTubeProOptionsFlow()

    async def _validate(
        self, url: str, token: str, *, timeout: int = 10
    ) -> dict[str, Any]:
        api = YouTubeProApi(async_get_clientsession(self.hass), url, token)
        return await api.async_health(timeout=timeout)

    async def _validate_auto(self, token: str) -> tuple[str, dict[str, Any]]:
        """Discover and validate the first reachable add-on endpoint."""
        session = async_get_clientsession(self.hass)
        candidates = await async_discover_addon_urls(session, hass=self.hass)
        if not candidates:
            raise YouTubeProCannotConnect("Không tìm thấy YouTube Pro add-on")

        async def probe(url: str) -> tuple[str, dict[str, Any] | None, Exception | None]:
            try:
                return url, await self._validate(url, token, timeout=5), None
            except Exception as error:  # noqa: BLE001 - probe all local candidates
                return url, None, error

        results = await asyncio.gather(*(probe(url) for url in candidates))
        auth_error: YouTubeProInvalidAuth | None = None
        for url, health, error in results:
            if health is not None:
                return url, health
            if isinstance(error, YouTubeProInvalidAuth) and auth_error is None:
                auth_error = error
        if auth_error:
            raise auth_error
        raise YouTubeProCannotConnect("Không thể tự tìm thấy YouTube Pro add-on")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure an add-on instance."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                requested_url = normalize_base_url(str(user_input.get(CONF_URL) or ""))
                token = str(user_input[CONF_TOKEN]).strip()
                if is_auto_url(requested_url):
                    url, health = await self._validate_auto(token)
                else:
                    url = normalize_addon_url(requested_url)
                    if not url:
                        raise vol.Invalid("invalid_url")
                    health = await self._validate(url, token)
            except vol.Invalid:
                errors["base"] = "invalid_url"
            except YouTubeProInvalidAuth:
                errors["base"] = "invalid_auth"
            except YouTubeProCannotConnect:
                errors["base"] = "cannot_connect"
            except YouTubeProApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(url.casefold())
                self._abort_if_unique_id_configured()
                host = urlsplit(url).hostname or "YouTube Pro"
                return self.async_create_entry(
                    title=f"YouTube Pro ({host})",
                    data={
                        CONF_URL: url,
                        CONF_TOKEN: token,
                        CONF_DEFAULT_ENTITY_ID: str(
                            user_input.get(CONF_DEFAULT_ENTITY_ID) or ""
                        ),
                        "api_version": health.get("api_version", 1),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                user_schema(), user_input or {}
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start token reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update a rotated integration token."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token = str(user_input[CONF_TOKEN]).strip()
            try:
                health = await self._validate(entry.data[CONF_URL], token)
            except YouTubeProInvalidAuth:
                errors["base"] = "invalid_auth"
            except YouTubeProCannotConnect:
                errors["base"] = "cannot_connect"
            except YouTubeProApiError:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={
                        **entry.data,
                        CONF_TOKEN: token,
                        "api_version": health.get("api_version", 1),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                )
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
        )


class YouTubeProOptionsFlow(OptionsFlow):
    """Configure the Media Browser playback target."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage YouTube Pro options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = str(
            self.config_entry.options.get(CONF_DEFAULT_ENTITY_ID)
            or self.config_entry.data.get(CONF_DEFAULT_ENTITY_ID)
            or ""
        )
        key = (
            vol.Optional(CONF_DEFAULT_ENTITY_ID, default=current)
            if current
            else vol.Optional(CONF_DEFAULT_ENTITY_ID)
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    key: EntitySelector(
                        EntitySelectorConfig(domain="media_player")
                    )
                }
            ),
        )
