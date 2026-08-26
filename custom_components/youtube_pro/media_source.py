"""Expose YouTube Pro in the Home Assistant Media Browser."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Iterable
from typing import Any

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .api import YouTubeProApiError
from .const import DOMAIN
from .coordinator import YouTubeProCoordinator

MAX_BROWSE_TRACKS = 200
MEDIA_KIND_AUDIO = "audio"
MEDIA_KIND_VIDEO = "video"

DEFAULT_VIDEO_DISCOVERY = (
    {"title": "Thịnh hành", "query": "video thịnh hành Việt Nam"},
    {"title": "Âm nhạc", "query": "music video Việt Nam mới nhất"},
    {"title": "Giải trí", "query": "video giải trí Việt Nam"},
    {"title": "Tin tức", "query": "tin tức mới nhất Việt Nam"},
    {"title": "Công nghệ", "query": "video công nghệ mới nhất"},
    {"title": "Gaming", "query": "gaming Việt Nam thịnh hành"},
)


def _encode_identifier(value: str) -> str:
    return urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _decode_identifier(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    try:
        return urlsafe_b64decode(f"{value}{padding}").decode()
    except (UnicodeDecodeError, ValueError) as error:
        raise BrowseError("Media Browser identifier không hợp lệ") from error


def _normalize_media_kind(value: Any) -> str:
    return (
        MEDIA_KIND_VIDEO
        if str(value or "").strip().casefold() in {"video", "movie", "watch"}
        else MEDIA_KIND_AUDIO
    )


def _media_type(media_kind: str) -> MediaType:
    return MediaType.VIDEO if media_kind == MEDIA_KIND_VIDEO else MediaType.MUSIC


def _media_class(media_kind: str) -> MediaClass:
    return MediaClass.VIDEO if media_kind == MEDIA_KIND_VIDEO else MediaClass.MUSIC


def _source_item(
    identifier: str,
    title: str,
    *,
    media_class: MediaClass,
    media_type: MediaType,
    can_play: bool = False,
    can_expand: bool = True,
    thumbnail: str | None = None,
) -> BrowseMediaSource:
    return BrowseMediaSource(
        domain=DOMAIN,
        identifier=identifier,
        media_class=media_class,
        media_content_type=media_type,
        title=title,
        can_play=can_play,
        can_expand=can_expand,
        thumbnail=thumbnail or None,
    )


def _track_item(
    track: dict[str, Any],
    identifier: str | None = None,
    *,
    media_kind: str | None = None,
) -> BrowseMediaSource | None:
    url = str(track.get("url") or "").strip()
    if not url:
        return None
    normalized_kind = _normalize_media_kind(
        media_kind if media_kind is not None else track.get("media_kind")
    )
    title = str(track.get("title") or "YouTube")
    channel = str(track.get("channel") or "").strip()
    if channel:
        title = f"{title} · {channel}"
    prefix = "video-track" if normalized_kind == MEDIA_KIND_VIDEO else "track"
    return _source_item(
        identifier or f"{prefix}/{_encode_identifier(url)}",
        title,
        media_class=_media_class(normalized_kind),
        media_type=_media_type(normalized_kind),
        can_play=True,
        can_expand=False,
        thumbnail=str(track.get("thumbnail") or ""),
    )


def _track_children(
    tracks: Iterable[dict[str, Any]], playlist_name: str | None = None
) -> list[BrowseMediaSource]:
    children = []
    for index, track in enumerate(tracks):
        if not isinstance(track, dict):
            continue
        identifier = None
        if playlist_name:
            media_kind = _normalize_media_kind(track.get("media_kind"))
            prefix = (
                "video-playlist-track"
                if media_kind == MEDIA_KIND_VIDEO
                else "playlist-track"
            )
            identifier = f"{prefix}/{_encode_identifier(playlist_name)}/{index}"
        if item := _track_item(track, identifier):
            children.append(item)
    return children


def _children_media_class(
    tracks: Iterable[dict[str, Any]],
) -> MediaClass | None:
    kinds = {
        _normalize_media_kind(track.get("media_kind"))
        for track in tracks
        if isinstance(track, dict) and track.get("url")
    }
    if kinds == {MEDIA_KIND_VIDEO}:
        return MediaClass.VIDEO
    if kinds == {MEDIA_KIND_AUDIO}:
        return MediaClass.MUSIC
    return None


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Set up the YouTube Pro media source."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries or not getattr(entries[0], "runtime_data", None):
        raise BrowseError("YouTube Pro chưa được tải")
    return YouTubeProMediaSource(hass, entries[0].runtime_data)


class YouTubeProMediaSource(MediaSource):
    """Provide add-on playlists and YouTube search results as media."""

    name = "YouTube Pro"

    def __init__(
        self, hass: HomeAssistant, coordinator: YouTubeProCoordinator
    ) -> None:
        super().__init__(DOMAIN)
        self.hass = hass
        self.coordinator = coordinator

    @property
    def api(self):
        """Return the add-on API client."""
        return self.coordinator.api

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a selected YouTube track to the add-on relay."""
        try:
            identifier = str(item.identifier or "")
            kind, separator, encoded = identifier.partition("/")
            if not separator or not encoded:
                raise Unresolvable("Mục Media Browser này không thể phát trực tiếp")

            media_kind = MEDIA_KIND_AUDIO
            if kind == "track":
                url = _decode_identifier(encoded)
            elif kind == "video-track":
                media_kind = MEDIA_KIND_VIDEO
                url = _decode_identifier(encoded)
            elif kind in {"playlist-track", "video-playlist-track"}:
                encoded_name, index_separator, raw_index = encoded.partition("/")
                if not index_separator:
                    raise Unresolvable("Playlist identifier không hợp lệ")
                playlist = await self.api.async_playlist(
                    _decode_identifier(encoded_name), limit=MAX_BROWSE_TRACKS
                )
                tracks = playlist.get("tracks") or []
                try:
                    selected_track = tracks[int(raw_index)]
                    url = str(selected_track["url"])
                    media_kind = (
                        MEDIA_KIND_VIDEO
                        if kind == "video-playlist-track"
                        else _normalize_media_kind(selected_track.get("media_kind"))
                    )
                except (IndexError, KeyError, TypeError, ValueError) as error:
                    raise Unresolvable(
                        "Không tìm thấy mục trong playlist"
                    ) from error
            else:
                raise Unresolvable("Mục Media Browser này không thể phát trực tiếp")

            if media_kind == MEDIA_KIND_VIDEO:
                resolve_options: dict[str, Any] = {"media_kind": media_kind}
                if item.target_media_player:
                    resolve_options["entity_id"] = item.target_media_player
                payload = await self.api.async_resolve(url, **resolve_options)
            else:
                payload = await self.api.async_resolve(url)
        except BrowseError as error:
            raise Unresolvable(str(error)) from error
        except YouTubeProApiError as error:
            raise Unresolvable(str(error)) from error
        media_url = str(payload.get("media_url") or "")
        content_type = str(payload.get("content_type") or "audio/mp4")
        if not media_url:
            raise Unresolvable("Add-on không trả về URL phát")
        return PlayMedia(media_url, content_type)

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse playlists, queue, history and YouTube searches."""
        try:
            identifier = str(item.identifier or "")
            if not identifier:
                return await self._async_root()
            kind, _, encoded = identifier.partition("/")
            if kind == "playlists" and not encoded:
                return await self._async_playlists()
            if kind == "playlist" and encoded:
                return await self._async_playlist(_decode_identifier(encoded))
            if kind == "queue" and not encoded:
                return await self._async_track_collection("queue", "Hàng chờ")
            if kind == "history" and not encoded:
                return await self._async_track_collection("history", "Nghe gần đây")
            if kind == "discover" and not encoded:
                return await self._async_search_directory(
                    "discover", "Khám phá", MEDIA_KIND_AUDIO
                )
            if kind == "searches" and not encoded:
                return await self._async_search_directory(
                    "searches", "Tìm kiếm gần đây", MEDIA_KIND_AUDIO
                )
            if kind == "videos" and not encoded:
                return await self._async_video_directory()
            if kind == "search" and encoded:
                return await self._async_search(
                    _decode_identifier(encoded), MEDIA_KIND_AUDIO
                )
            if kind == "video-search" and encoded:
                return await self._async_search(
                    _decode_identifier(encoded), MEDIA_KIND_VIDEO
                )
        except YouTubeProApiError as error:
            raise BrowseError(str(error)) from error
        raise BrowseError("Không hỗ trợ mục Media Browser này")

    async def _async_root(self) -> BrowseMediaSource:
        library = await self.api.async_library()
        playlist_count = len(library.get("playlists") or [])
        queue_count = int(library.get("queue_count") or 0)
        history_count = int(library.get("history_count") or 0)
        children = [
            _source_item(
                "discover",
                "Khám phá trên YouTube",
                media_class=MediaClass.DIRECTORY,
                media_type=MediaType.MUSIC,
            ),
            _source_item(
                "searches",
                "Tìm kiếm gần đây",
                media_class=MediaClass.DIRECTORY,
                media_type=MediaType.MUSIC,
            ),
            _source_item(
                "videos",
                "Video YouTube",
                media_class=MediaClass.DIRECTORY,
                media_type=MediaType.VIDEO,
            ),
            _source_item(
                "playlists",
                f"Playlist của bạn ({playlist_count})",
                media_class=MediaClass.PLAYLIST,
                media_type=MediaType.PLAYLIST,
            ),
            _source_item(
                "queue",
                f"Hàng chờ ({queue_count})",
                media_class=MediaClass.PLAYLIST,
                media_type=MediaType.PLAYLIST,
            ),
            _source_item(
                "history",
                f"Nghe gần đây ({history_count})",
                media_class=MediaClass.PLAYLIST,
                media_type=MediaType.PLAYLIST,
            ),
        ]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.APP,
            media_content_type=MediaType.APP,
            title=self.name,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
            children=children,
        )

    async def _async_playlists(self) -> BrowseMediaSource:
        library = await self.api.async_library()
        children = [
            _source_item(
                f"playlist/{_encode_identifier(str(playlist.get('name') or ''))}",
                f"{playlist.get('name') or 'Playlist'} ({int(playlist.get('track_count') or 0)})",
                media_class=MediaClass.PLAYLIST,
                media_type=MediaType.PLAYLIST,
                thumbnail=str(playlist.get("thumbnail") or ""),
            )
            for playlist in library.get("playlists") or []
            if playlist.get("name")
        ]
        return self._collection("playlists", "Playlist của bạn", children)

    async def _async_playlist(self, name: str) -> BrowseMediaSource:
        payload = await self.api.async_playlist(name, limit=MAX_BROWSE_TRACKS)
        return self._track_collection(
            f"playlist/{_encode_identifier(name)}", name, payload, playlist_name=name
        )

    async def _async_track_collection(
        self, identifier: str, title: str
    ) -> BrowseMediaSource:
        payload = (
            await self.api.async_queue(limit=MAX_BROWSE_TRACKS)
            if identifier == "queue"
            else await self.api.async_history(limit=MAX_BROWSE_TRACKS)
        )
        return self._track_collection(identifier, title, payload)

    async def _async_search_directory(
        self, identifier: str, title: str, media_kind: str
    ) -> BrowseMediaSource:
        library = await self.api.async_library()
        entries: list[tuple[str, str]] = []
        if identifier == "discover":
            entries.extend(
                (
                    str(item.get("title") or item.get("query")),
                    str(item.get("query") or ""),
                )
                for item in library.get("discovery") or []
                if item.get("query")
            )
        else:
            entries.extend(
                (f"Tìm: {query}", str(query))
                for query in library.get("search_history") or []
                if query
            )
            entries.extend(
                (
                    str(item.get("title") or item.get("query")),
                    str(item.get("query") or ""),
                )
                for item in library.get("discovery") or []
                if item.get("query")
            )
        return self._search_collection(identifier, title, entries, media_kind)

    async def _async_video_directory(self) -> BrowseMediaSource:
        library = await self.api.async_library()
        entries: list[tuple[str, str]] = []
        entries.extend(
            (
                str(item.get("title") or item.get("query")),
                str(item.get("query") or ""),
            )
            for item in library.get("video_discovery") or DEFAULT_VIDEO_DISCOVERY
            if item.get("query")
        )
        entries.extend(
            (f"Video đã tìm: {query}", str(query))
            for query in library.get("search_history") or []
            if query
        )
        return self._search_collection(
            "videos", "Video YouTube", entries, MEDIA_KIND_VIDEO
        )

    async def _async_search(
        self, query: str, media_kind: str
    ) -> BrowseMediaSource:
        if media_kind == MEDIA_KIND_VIDEO:
            payload = await self.api.async_search(
                query, limit=20, media_kind=media_kind
            )
        else:
            payload = await self.api.async_search(query, limit=20)
        tracks = []
        for raw_track in payload.get("results") or []:
            if not isinstance(raw_track, dict):
                continue
            track = dict(raw_track)
            track["media_kind"] = media_kind
            tracks.append(track)
        result = {
            "tracks": tracks,
            "total": len(tracks),
            "has_more": bool(payload.get("has_more")),
        }
        prefix = "video-search" if media_kind == MEDIA_KIND_VIDEO else "search"
        title_prefix = "Video" if media_kind == MEDIA_KIND_VIDEO else "Kết quả"
        return self._track_collection(
            f"{prefix}/{_encode_identifier(query)}",
            f"{title_prefix}: {query}",
            result,
            media_kind=media_kind,
        )

    def _search_collection(
        self,
        identifier: str,
        title: str,
        entries: Iterable[tuple[str, str]],
        media_kind: str,
    ) -> BrowseMediaSource:
        seen: set[str] = set()
        children = []
        prefix = "video-search" if media_kind == MEDIA_KIND_VIDEO else "search"
        for label, query in entries:
            normalized = query.casefold()
            if not query or normalized in seen:
                continue
            seen.add(normalized)
            children.append(
                _source_item(
                    f"{prefix}/{_encode_identifier(query)}",
                    label,
                    media_class=MediaClass.DIRECTORY,
                    media_type=_media_type(media_kind),
                )
            )
        return self._collection(
            identifier, title, children, media_type=_media_type(media_kind)
        )

    def _track_collection(
        self,
        identifier: str,
        title: str,
        payload: dict[str, Any],
        playlist_name: str | None = None,
        media_kind: str | None = None,
    ) -> BrowseMediaSource:
        tracks = []
        for raw_track in payload.get("tracks") or []:
            if not isinstance(raw_track, dict):
                continue
            track = dict(raw_track)
            if media_kind is not None:
                track["media_kind"] = media_kind
            tracks.append(track)
        children = _track_children(tracks, playlist_name)
        total = int(payload.get("total") or len(children))
        not_shown = max(0, total - len(children))
        if payload.get("has_more") and not_shown == 0:
            not_shown = 1
        child_class = _children_media_class(tracks)
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=identifier,
            media_class=MediaClass.PLAYLIST,
            media_content_type=MediaType.PLAYLIST,
            title=title,
            can_play=False,
            can_expand=True,
            children_media_class=child_class,
            children=children,
            not_shown=not_shown,
        )

    @staticmethod
    def _collection(
        identifier: str,
        title: str,
        children: list[BrowseMediaSource],
        *,
        media_type: MediaType = MediaType.MUSIC,
    ) -> BrowseMediaSource:
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=identifier,
            media_class=MediaClass.DIRECTORY,
            media_content_type=media_type,
            title=title,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
            children=children,
        )
