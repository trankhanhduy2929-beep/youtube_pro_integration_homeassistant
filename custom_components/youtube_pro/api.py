"""Async client for the YouTube Pro add-on API."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout


class YouTubeProApiError(Exception):
    """Base API error."""


class YouTubeProCannotConnect(YouTubeProApiError):
    """The add-on could not be reached."""


class YouTubeProInvalidAuth(YouTubeProApiError):
    """The integration token was rejected."""


class YouTubeProApi:
    """Client for the add-on's isolated integration API."""

    def __init__(self, session: ClientSession, base_url: str, token: str) -> None:
        """Initialize the client."""
        self._session = session
        self.base_url = base_url.rstrip("/")
        self._token = token.strip()

    async def _json_response(self, response: ClientResponse) -> dict[str, Any]:
        try:
            payload = await response.json(content_type=None)
        except (ClientError, ValueError, TypeError) as error:
            raise YouTubeProApiError(
                f"Add-on trả dữ liệu không hợp lệ (HTTP {response.status})"
            ) from error
        if not isinstance(payload, dict):
            raise YouTubeProApiError("Add-on trả dữ liệu không hợp lệ")
        return payload

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                json=payload,
                timeout=ClientTimeout(total=timeout),
            ) as response:
                data = await self._json_response(response)
                if response.status in (401, 403):
                    raise YouTubeProInvalidAuth(
                        data.get("error") or "Integration token không hợp lệ"
                    )
                if response.status >= 400 or data.get("success") is False:
                    raise YouTubeProApiError(
                        str(data.get("error") or f"HTTP {response.status}")
                    )
                return data
        except YouTubeProApiError:
            raise
        except (ClientError, TimeoutError) as error:
            raise YouTubeProCannotConnect(
                "Không thể kết nối YouTube Pro add-on"
            ) from error

    async def async_health(self) -> dict[str, Any]:
        """Validate the endpoint and token."""
        return await self._request("GET", "/api/integration/health", timeout=10)

    async def async_status(self) -> dict[str, Any]:
        """Fetch coordinator data."""
        return await self._request("GET", "/api/integration/status", timeout=10)

    async def async_play(
        self,
        entity_id: str,
        url: str,
        title: str,
        repeat: str,
        shuffle: bool,
    ) -> dict[str, Any]:
        """Play one YouTube URL."""
        return await self._request(
            "POST",
            "/api/integration/play",
            payload={
                "entity_id": entity_id,
                "url": url,
                "title": title,
                "repeat": repeat,
                "shuffle": shuffle,
                "source_name": "Home Assistant service",
            },
            timeout=90,
        )

    async def async_play_playlist(
        self,
        entity_id: str,
        playlist_name: str,
        index: int,
        repeat: str,
        shuffle: bool,
    ) -> dict[str, Any]:
        """Play a stored add-on playlist."""
        return await self._request(
            "POST",
            "/api/integration/play-playlist",
            payload={
                "entity_id": entity_id,
                "playlist_name": playlist_name,
                "index": index,
                "repeat": repeat,
                "shuffle": shuffle,
            },
            timeout=90,
        )

    async def async_enqueue(self, url: str, title: str) -> dict[str, Any]:
        """Append a URL to the add-on queue."""
        return await self._request(
            "POST",
            "/api/integration/enqueue",
            payload={"url": url, "title": title},
        )

    async def async_set_timer(self, timer: dict[str, Any]) -> dict[str, Any]:
        """Create or update an add-on timer."""
        return await self._request(
            "POST",
            "/api/integration/timers",
            payload=timer,
        )

    async def async_library(self) -> dict[str, Any]:
        """Fetch the Media Browser library summary."""
        return await self._request("GET", "/api/integration/library", timeout=15)

    async def async_playlist(
        self, name: str, *, offset: int = 0, limit: int = 200
    ) -> dict[str, Any]:
        """Fetch tracks from one stored playlist."""
        query = urlencode({"offset": offset, "limit": limit})
        return await self._request(
            "GET",
            f"/api/integration/playlists/{quote(name, safe='')}?{query}",
            timeout=20,
        )

    async def async_queue(
        self, *, offset: int = 0, limit: int = 200
    ) -> dict[str, Any]:
        """Fetch the shared add-on queue."""
        query = urlencode({"offset": offset, "limit": limit})
        return await self._request(
            "GET", f"/api/integration/queue?{query}", timeout=15
        )

    async def async_history(
        self, *, offset: int = 0, limit: int = 200
    ) -> dict[str, Any]:
        """Fetch recently played tracks."""
        query = urlencode({"offset": offset, "limit": limit})
        return await self._request(
            "GET", f"/api/integration/history?{query}", timeout=15
        )

    async def async_search(
        self, query: str, *, offset: int = 0, limit: int = 20
    ) -> dict[str, Any]:
        """Search YouTube through the add-on extractor."""
        return await self._request(
            "POST",
            "/api/integration/search",
            payload={"query": query, "offset": offset, "limit": limit},
            timeout=45,
        )

    async def async_resolve(self, url: str) -> dict[str, Any]:
        """Resolve a YouTube URL to the add-on relay."""
        return await self._request(
            "POST",
            "/api/integration/resolve",
            payload={"url": url},
            timeout=90,
        )

    async def async_control(
        self,
        entity_id: str,
        action: str,
        *,
        repeat: str | None = None,
        shuffle: bool | None = None,
    ) -> dict[str, Any]:
        """Control an add-on playback session."""
        payload: dict[str, Any] = {"entity_id": entity_id, "action": action}
        if repeat is not None:
            payload["repeat"] = repeat
        if shuffle is not None:
            payload["shuffle"] = shuffle
        return await self._request(
            "POST", "/api/integration/control", payload=payload, timeout=45
        )
