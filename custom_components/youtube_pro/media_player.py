"""Virtual media player for YouTube Pro Media Browser search."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaPlayerEntity,
    SearchMedia,
    SearchMediaQuery,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import YouTubeProApiError
from .const import CONF_DEFAULT_ENTITY_ID, DOMAIN
from .coordinator import YouTubeProConfigEntry, YouTubeProCoordinator
from .media_source import (
    MEDIA_KIND_AUDIO,
    MEDIA_KIND_VIDEO,
    YouTubeProMediaSource,
    _decode_identifier,
    _track_item,
)

MEDIA_SOURCE_PREFIX = f"media-source://{DOMAIN}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YouTubeProConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the YouTube Pro virtual player."""
    async_add_entities([YouTubeProPlayer(entry.runtime_data, entry)])


class YouTubeProPlayer(
    CoordinatorEntity[YouTubeProCoordinator], MediaPlayerEntity
):
    """Bridge Home Assistant Media Browser to a selected physical speaker."""

    _attr_has_entity_name = True
    _attr_name = "Media Browser"
    _attr_icon = "mdi:youtube-music"
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.BROWSE_MEDIA
        | MediaPlayerEntityFeature.SEARCH_MEDIA
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.SHUFFLE_SET
        | MediaPlayerEntityFeature.REPEAT_SET
    )

    def __init__(
        self,
        coordinator: YouTubeProCoordinator,
        entry: YouTubeProConfigEntry,
    ) -> None:
        """Initialize the virtual player."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_media_browser"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="YouTube Pro",
            manufacturer="YouTube Pro",
            model="Home Assistant Add-on",
            sw_version=str(coordinator.data.get("version") or "unknown"),
            configuration_url=coordinator.api.base_url,
            entry_type=DeviceEntryType.SERVICE,
        )
        self._media_source = YouTubeProMediaSource(
            coordinator.hass, coordinator
        )

    @property
    def target_entity_id(self) -> str:
        """Return the configured physical media player."""
        return str(
            self.entry.options.get(CONF_DEFAULT_ENTITY_ID)
            or self.entry.data.get(CONF_DEFAULT_ENTITY_ID)
            or ""
        )

    @property
    def session(self) -> dict[str, Any]:
        """Return the add-on session for the configured target."""
        sessions = self.coordinator.data.get("sessions") or {}
        session = sessions.get(self.target_entity_id)
        return session if isinstance(session, dict) else {}

    @property
    def available(self) -> bool:
        """Return whether browsing and search are available."""
        return self.coordinator.last_update_success

    @property
    def state(self) -> MediaPlayerState:
        """Mirror the selected speaker's add-on playback session."""
        state = str(self.session.get("state") or "idle")
        return {
            "resolving": MediaPlayerState.BUFFERING,
            "starting": MediaPlayerState.BUFFERING,
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
        }.get(state, MediaPlayerState.IDLE)

    @property
    def current_track(self) -> dict[str, Any]:
        """Return current track metadata."""
        track = self.session.get("current_track")
        return track if isinstance(track, dict) else {}

    @property
    def media_title(self) -> str | None:
        """Return current title."""
        return str(self.current_track.get("title") or "") or None

    @property
    def media_artist(self) -> str | None:
        """Return current channel."""
        return str(self.current_track.get("channel") or "") or None

    @property
    def media_image_url(self) -> str | None:
        """Return current artwork."""
        return str(self.current_track.get("thumbnail") or "") or None

    @property
    def media_image_remotely_accessible(self) -> bool:
        """Return whether artwork is remotely accessible."""
        return True

    @property
    def media_duration(self) -> int | None:
        """Return current duration."""
        duration = int(
            self.session.get("last_duration")
            or self.current_track.get("duration")
            or 0
        )
        return duration or None

    @property
    def media_position(self) -> int | None:
        """Return current position."""
        position = int(float(self.session.get("last_position") or 0))
        return position if self.media_duration else None

    @property
    def media_content_id(self) -> str | None:
        """Return current YouTube URL."""
        return str(self.current_track.get("url") or "") or None

    @property
    def media_content_type(self) -> MediaType:
        """Return current media type."""
        return (
            MediaType.VIDEO
            if self.current_track.get("media_kind") == MEDIA_KIND_VIDEO
            else MediaType.MUSIC
        )

    @property
    def shuffle(self) -> bool:
        """Return shuffle mode."""
        return bool(self.session.get("shuffle"))

    @property
    def repeat(self) -> RepeatMode:
        """Return repeat mode."""
        try:
            return RepeatMode(str(self.session.get("repeat") or "off"))
        except ValueError:
            return RepeatMode.OFF

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the physical playback target and source context."""
        return {
            "target_entity_id": self.target_entity_id or None,
            "source_name": self.session.get("source_name"),
            "track_index": self.session.get("index"),
            "track_count": self.session.get("track_count"),
        }

    def _target_or_raise(self) -> str:
        target = self.target_entity_id
        if not target:
            raise HomeAssistantError(
                "Hãy mở Configure của YouTube Pro và chọn loa mặc định"
            )
        if target == self.entity_id:
            raise HomeAssistantError("Loa mặc định không thể là Media Browser ảo")
        return target

    async def _async_api_operation(self, operation) -> None:
        try:
            await operation
        except YouTubeProApiError as error:
            raise HomeAssistantError(str(error)) from error
        await self.coordinator.async_request_refresh()

    @staticmethod
    def _media_identifier(media_id: str) -> str:
        if media_id == MEDIA_SOURCE_PREFIX:
            return ""
        if media_id.startswith(f"{MEDIA_SOURCE_PREFIX}/"):
            return media_id[len(MEDIA_SOURCE_PREFIX) + 1 :]
        return media_id

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Browse the add-on library."""
        identifier = self._media_identifier(media_content_id or "")
        item = self._media_source_item(identifier)
        result = await self._media_source.async_browse_media(item)
        result.can_search = True
        return result

    async def async_search_media(self, query: SearchMediaQuery) -> SearchMedia:
        """Search YouTube directly from Home Assistant Media Browser."""
        search_query = query.search_query.strip()
        if not search_query:
            return SearchMedia(result=[])
        media_kind = self._search_media_kind(query)
        try:
            if media_kind == MEDIA_KIND_VIDEO:
                payload = await self.coordinator.api.async_search(
                    search_query, limit=20, media_kind=media_kind
                )
            else:
                payload = await self.coordinator.api.async_search(
                    search_query, limit=20
                )
        except YouTubeProApiError as error:
            raise HomeAssistantError(str(error)) from error
        return SearchMedia(
            result=[
                item
                for track in payload.get("results") or []
                if (item := _track_item(track, media_kind=media_kind)) is not None
            ]
        )

    def _search_media_kind(self, query: SearchMediaQuery) -> str:
        """Infer whether native Media Browser search targets audio or video."""
        media_type = str(query.media_content_type or "").casefold()
        if media_type in {MediaType.VIDEO.value, MediaType.MOVIE.value}:
            return MEDIA_KIND_VIDEO
        if query.media_filter_classes and MediaClass.VIDEO in query.media_filter_classes:
            return MEDIA_KIND_VIDEO
        identifier = self._media_identifier(query.media_content_id or "")
        if identifier == "videos" or identifier.startswith("video-"):
            return MEDIA_KIND_VIDEO
        return MEDIA_KIND_AUDIO

    def _media_source_item(self, identifier: str):
        from homeassistant.components.media_source import MediaSourceItem

        return MediaSourceItem(
            self.hass,
            DOMAIN,
            identifier,
            self.entity_id,
        )

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Play a Media Browser selection on the configured physical speaker."""
        target = self._target_or_raise()
        identifier = self._media_identifier(str(media_id))
        kind, separator, encoded = identifier.partition("/")

        if kind in {"playlist-track", "video-playlist-track"} and separator:
            encoded_name, index_separator, raw_index = encoded.partition("/")
            if not index_separator:
                raise HomeAssistantError("Playlist identifier không hợp lệ")
            name = _decode_identifier(encoded_name)
            await self._async_api_operation(
                self.coordinator.api.async_play_playlist(
                    target,
                    name,
                    int(raw_index),
                    self.repeat.value,
                    self.shuffle,
                )
            )
            return

        if kind == "track" and separator:
            url = _decode_identifier(encoded)
            await self._async_api_operation(
                self.coordinator.api.async_play(
                    target,
                    url,
                    "YouTube Music",
                    self.repeat.value,
                    self.shuffle,
                )
            )
            return

        if kind == "video-track" and separator:
            url = _decode_identifier(encoded)
            await self._async_api_operation(
                self.coordinator.api.async_play(
                    target,
                    url,
                    "YouTube Video",
                    self.repeat.value,
                    self.shuffle,
                    media_kind=MEDIA_KIND_VIDEO,
                    track={"url": url, "title": "YouTube Video"},
                )
            )
            return

        if identifier.startswith(
            (
                "https://youtube.com/",
                "https://www.youtube.com/",
                "https://youtu.be/",
                "https://music.youtube.com/",
            )
        ):
            media_kind = (
                MEDIA_KIND_VIDEO
                if str(media_type).casefold()
                in {MediaType.VIDEO.value, MediaType.MOVIE.value}
                else MEDIA_KIND_AUDIO
            )
            await self._async_api_operation(
                self.coordinator.api.async_play(
                    target,
                    identifier,
                    "YouTube Music",
                    self.repeat.value,
                    self.shuffle,
                    media_kind=media_kind,
                )
            )
            return

        if identifier.startswith(("http://", "https://")):
            await self.hass.services.async_call(
                "media_player",
                "play_media",
                {
                    ATTR_ENTITY_ID: target,
                    "media_content_id": identifier,
                    "media_content_type": str(media_type),
                },
                blocking=True,
            )
            return

        raise HomeAssistantError("Mục Media Browser này không thể phát")

    async def async_media_play(self) -> None:
        """Resume playback."""
        await self._async_control("play")

    async def async_media_pause(self) -> None:
        """Pause playback."""
        await self._async_control("pause")

    async def async_media_stop(self) -> None:
        """Stop playback."""
        await self._async_control("stop")

    async def async_media_next_track(self) -> None:
        """Skip to the next track."""
        await self._async_control("next")

    async def async_media_previous_track(self) -> None:
        """Return to the previous track."""
        await self._async_control("previous")

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Set shuffle mode."""
        await self._async_control("mode", repeat=self.repeat.value, shuffle=shuffle)

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Set repeat mode."""
        value = repeat.value if isinstance(repeat, RepeatMode) else str(repeat)
        await self._async_control("mode", repeat=value, shuffle=self.shuffle)

    async def _async_control(
        self,
        action: str,
        *,
        repeat: str | None = None,
        shuffle: bool | None = None,
    ) -> None:
        target = self._target_or_raise()
        await self._async_api_operation(
            self.coordinator.api.async_control(
                target,
                action,
                repeat=repeat,
                shuffle=shuffle,
            )
        )
