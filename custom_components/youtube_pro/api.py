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

    @staticmethod
    def _normalize_media_kind(value: Any) -> str:
        """Normalize the media kind accepted by the add-on API."""
        return (
            "video"
            if str(value or "").casefold() in {"video", "movie", "watch"}
            else "audio"
        )

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

    async def async_health(self, *, timeout: int = 10) -> dict[str, Any]:
        """Validate the endpoint and token."""
        return await self._request(
            "GET", "/api/integration/health", timeout=timeout
        )

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
        *,
        media_kind: str = "audio",
        track: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Play one YouTube URL."""
        normalized_kind = self._normalize_media_kind(media_kind)
        request_track = dict(track or {})
        request_track.setdefault("url", url)
        request_track.setdefault("title", title)
        request_track.setdefault("media_kind", normalized_kind)
        payload: dict[str, Any] = {
            "entity_id": entity_id,
            "url": url,
            "title": title,
            "repeat": repeat,
            "shuffle": shuffle,
            "source_name": "Home Assistant service",
        }
        if normalized_kind == "video" or track is not None:
            payload.update(
                {
                    "media_kind": normalized_kind,
                    "track": request_track,
                }
            )
        return await self._request(
            "POST",
            "/api/integration/play",
            payload=payload,
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

    async def async_enqueue(
        self,
        url: str,
        title: str,
        *,
        media_kind: str = "audio",
        entity_id: str | None = None,
        position: str = "end",
    ) -> dict[str, Any]:
        """Add a URL to the active session or shared add-on queue."""
        normalized_kind = self._normalize_media_kind(media_kind)
        payload: dict[str, Any] = {"url": url, "title": title}
        if normalized_kind == "video":
            payload["media_kind"] = normalized_kind
        if entity_id:
            payload["entity_id"] = entity_id
        if position == "next":
            payload["position"] = position
        return await self._request(
            "POST",
            "/api/integration/enqueue",
            payload=payload,
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
        self,
        *,
        offset: int = 0,
        limit: int = 200,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch the shared queue or active device session queue."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if entity_id:
            params["entity_id"] = entity_id
        query = urlencode(params)
        return await self._request(
            "GET", f"/api/integration/queue?{query}", timeout=15
        )

    async def async_queue_view(self, entity_id: str | None = None) -> dict[str, Any]:
        """Fetch the queue view, including the current item when available."""
        query = urlencode({"entity_id": entity_id}) if entity_id else ""
        suffix = f"?{query}" if query else ""
        return await self._request(
            "GET", f"/api/integration/queue{suffix}", timeout=15
        )

    async def async_start_radio(
        self,
        entity_id: str,
        url: str,
        title: str,
        *,
        media_kind: str = "audio",
        limit: int = 24,
        mode: str = "replace",
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a YouTube recommendation radio from a seed track."""
        normalized_kind = self._normalize_media_kind(media_kind)
        payload: dict[str, Any] = {
            "entity_id": entity_id,
            "seed": {
                "url": url,
                "title": title,
                "media_kind": normalized_kind,
            },
            "media_kind": normalized_kind,
            "limit": limit,
            "mode": mode,
            "start_if_missing": True,
        }
        if profile_id:
            payload["profile_id"] = profile_id
        return await self._request(
            "POST",
            "/api/integration/radio",
            payload=payload,
            timeout=90,
        )

    async def async_preferences(self) -> dict[str, Any]:
        """Fetch local listener profiles and feedback summaries."""
        return await self._request(
            "GET", "/api/integration/preferences", timeout=15
        )

    async def async_update_preferences(
        self,
        action: str,
        *,
        profile_id: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create, rename, delete or select a listener profile."""
        payload: dict[str, Any] = {"action": action}
        if profile_id:
            payload["profile_id"] = profile_id
        if name:
            payload["name"] = name
        return await self._request(
            "POST", "/api/integration/preferences", payload=payload, timeout=15
        )

    async def async_listener_feedback(
        self,
        action: str,
        track: dict[str, Any] | None = None,
        *,
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        """Record like, dislike or block feedback for a track."""
        payload: dict[str, Any] = {"action": action}
        if track:
            payload["track"] = dict(track)
        if profile_id:
            payload["profile_id"] = profile_id
        return await self._request(
            "POST",
            "/api/integration/preferences/feedback",
            payload=payload,
            timeout=15,
        )

    async def async_personal_mix(
        self,
        *,
        profile_id: str | None = None,
        media_kind: str = "audio",
        limit: int = 24,
        refresh: bool = False,
        entity_id: str | None = None,
        start: bool = False,
        shuffle: bool = True,
    ) -> dict[str, Any]:
        """Build a local-profile-aware YouTube mix."""
        normalized_kind = self._normalize_media_kind(media_kind)
        payload: dict[str, Any] = {
            "media_kind": normalized_kind,
            "limit": limit,
            "refresh": refresh,
            "start": start,
            "shuffle": shuffle,
        }
        if profile_id:
            payload["profile_id"] = profile_id
        if entity_id:
            payload["entity_id"] = entity_id
        return await self._request(
            "POST", "/api/integration/personal-mix", payload=payload, timeout=90
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
        self,
        query: str,
        *,
        offset: int = 0,
        limit: int = 20,
        media_kind: str = "audio",
    ) -> dict[str, Any]:
        """Search YouTube through the add-on extractor."""
        normalized_kind = self._normalize_media_kind(media_kind)
        return await self._request(
            "POST",
            "/api/integration/search",
            payload={
                "query": query,
                "offset": offset,
                "limit": limit,
                **(
                    {"media_kind": normalized_kind}
                    if normalized_kind == "video"
                    else {}
                ),
            },
            timeout=45,
        )

    async def async_resolve(
        self,
        url: str,
        *,
        media_kind: str = "audio",
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        """Resolve a YouTube URL to the add-on relay."""
        normalized_kind = self._normalize_media_kind(media_kind)
        payload: dict[str, Any] = {"url": url}
        if normalized_kind == "video":
            payload["media_kind"] = normalized_kind
        if entity_id:
            payload["entity_id"] = entity_id
        return await self._request(
            "POST",
            "/api/integration/resolve",
            payload=payload,
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
