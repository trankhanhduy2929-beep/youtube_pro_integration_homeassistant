"""Discover the YouTube Pro add-on endpoint inside Home Assistant."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import ADDON_PORT, ADDON_SLUG, AUTO_URL

SUPERVISOR_ADDONS_URL = "http://supervisor/addons"
DISCOVERY_TIMEOUT = ClientTimeout(total=3)


def is_auto_url(value: str | None) -> bool:
    """Return whether the endpoint should be discovered automatically."""
    return not str(value or "").strip() or str(value).strip().casefold() in {
        AUTO_URL,
        "automatic",
        "default",
    }


def normalize_addon_url(value: str) -> str:
    """Normalize a manually entered add-on URL."""
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return ""
    if parsed.path not in {"", "/"}:
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _url_for_host(hostname: str) -> str:
    host = str(hostname or "").strip()
    if not host:
        return ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"http://{host}:{ADDON_PORT}"


def _configured_host_urls(hass: Any) -> list[str]:
    urls: list[str] = []
    config = getattr(hass, "config", None)
    for attribute in ("internal_url", "external_url"):
        raw_url = str(getattr(config, attribute, "") or "")
        parsed = urlsplit(raw_url)
        if parsed.hostname:
            candidate = _url_for_host(parsed.hostname)
            if candidate and candidate not in urls:
                urls.append(candidate)
    return urls


async def async_discover_addon_urls(
    session: ClientSession,
    *,
    hass: Any | None = None,
    supervisor_token: str | None = None,
) -> tuple[str, ...]:
    """Return likely internal URLs for an installed YouTube Pro add-on."""
    urls: list[str] = []
    token = (
        os.environ.get("SUPERVISOR_TOKEN", "")
        if supervisor_token is None
        else supervisor_token
    )
    if token:
        overview = await _get_json(session, SUPERVISOR_ADDONS_URL, token)
        data = _unwrap_data(overview)
        addons = data.get("addons") if isinstance(data, Mapping) else None
        if isinstance(addons, list):
            matches = [addon for addon in addons if _is_youtube_pro_addon(addon)]
            matches.sort(key=lambda addon: str(addon.get("state", "")) != "started")
            for addon in matches:
                slug = str(addon.get("slug", "")).strip()
                info = await _get_json(
                    session,
                    f"{SUPERVISOR_ADDONS_URL}/{quote(slug, safe='')}/info",
                    token,
                )
                info_data = _unwrap_data(info)
                hostnames = []
                if isinstance(info_data, Mapping):
                    hostnames.append(str(info_data.get("hostname", "")).strip())
                hostnames.extend((slug.replace("_", "-"), slug))
                for hostname in hostnames:
                    candidate = _url_for_host(hostname)
                    if candidate and candidate not in urls:
                        urls.append(candidate)

    for hostname in (
        ADDON_SLUG,
        ADDON_SLUG.replace("_", "-"),
        f"local_{ADDON_SLUG}",
        f"local-{ADDON_SLUG.replace('_', '-')}",
    ):
        candidate = _url_for_host(hostname)
        if candidate not in urls:
            urls.append(candidate)

    for candidate in _configured_host_urls(hass):
        if candidate not in urls:
            urls.append(candidate)

    fallback = _url_for_host("homeassistant.local")
    if fallback not in urls:
        urls.append(fallback)
    return tuple(urls)


async def _get_json(session: ClientSession, url: str, token: str) -> Any:
    try:
        async with session.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=DISCOVERY_TIMEOUT,
        ) as response:
            if response.status != 200:
                return None
            return await response.json(content_type=None)
    except (ClientError, TimeoutError, TypeError, ValueError):
        return None


def _unwrap_data(payload: Any) -> Any:
    if isinstance(payload, Mapping) and isinstance(payload.get("data"), Mapping):
        return payload["data"]
    return payload


def _is_youtube_pro_addon(addon: Any) -> bool:
    if not isinstance(addon, Mapping):
        return False
    slug = str(addon.get("slug", "")).strip()
    return slug == ADDON_SLUG or slug.endswith(f"_{ADDON_SLUG}")
