from types import SimpleNamespace

import pytest
from homeassistant.components.media_player import MediaClass, SearchMediaQuery
from homeassistant.components.media_player.const import MediaType
from homeassistant.components.media_source import MediaSourceItem
from homeassistant.core import HomeAssistant

from custom_components.youtube_pro.const import DOMAIN
from custom_components.youtube_pro.media_player import YouTubeProPlayer
from custom_components.youtube_pro.media_source import (
    YouTubeProMediaSource,
    _encode_identifier,
)

TRACKS = [
    {
        "id": "one",
        "title": "Bài Một",
        "url": "https://www.youtube.com/watch?v=one",
        "thumbnail": "https://i.ytimg.com/vi/one/mqdefault.jpg",
        "duration": 180,
        "channel": "Kênh Một",
    },
    {
        "id": "two",
        "title": "Bài Hai",
        "url": "https://www.youtube.com/watch?v=two",
        "thumbnail": "https://i.ytimg.com/vi/two/mqdefault.jpg",
        "duration": 200,
        "channel": "Kênh Hai",
    },
]

VIDEO_TRACKS = [
    {
        "id": "video-one",
        "title": "Video Một",
        "url": "https://www.youtube.com/watch?v=video-one",
        "thumbnail": "https://i.ytimg.com/vi/video-one/mqdefault.jpg",
        "duration": 240,
        "channel": "Kênh Video",
        "media_kind": "video",
    }
]


class FakeApi:
    base_url = "http://homeassistant.local:2032"

    def __init__(self):
        self.calls = []
        self.queue_requests = []
        self.resolve_targets = []

    async def async_library(self):
        return {
            "playlists": [
                {
                    "name": "Yêu thích",
                    "track_count": 2,
                    "thumbnail": TRACKS[0]["thumbnail"],
                }
            ],
            "queue_count": 2,
            "history_count": 1,
            "search_history": ["nhạc chill"],
            "discovery": [{"title": "Mix dành cho bạn", "query": "nhạc hay"}],
            "video_discovery": [{"title": "Thịnh hành", "query": "video hot"}],
        }

    async def async_playlist(self, name, **kwargs):
        assert name == "Yêu thích"
        return {"tracks": TRACKS, "total": 2, "has_more": False}

    async def async_queue(self, **kwargs):
        self.queue_requests.append(kwargs)
        return {"tracks": TRACKS, "total": 2, "has_more": False}

    async def async_history(self, **kwargs):
        return {"tracks": TRACKS[:1], "total": 1, "has_more": False}

    async def async_personal_mix(self, **kwargs):
        self.calls.append(("personal_mix", kwargs))
        return {
            "tracks": TRACKS,
            "total": 2,
            "has_more": False,
            "profile": {"id": "default", "name": "Phòng khách"},
        }

    async def async_search(self, query, **kwargs):
        media_kind = kwargs.get("media_kind", "audio")
        self.calls.append(("search", query, media_kind))
        return {
            "results": VIDEO_TRACKS if media_kind == "video" else TRACKS,
            "has_more": False,
        }

    async def async_resolve(self, url, **kwargs):
        media_kind = kwargs.get("media_kind", "audio")
        self.calls.append(("resolve", url, media_kind))
        self.resolve_targets.append(kwargs.get("entity_id"))
        return {
            "media_url": (
                "http://192.168.1.2:2032/api/media/token/video.mp4"
                if media_kind == "video"
                else "http://192.168.1.2:2032/api/media/token/audio.m4a"
            ),
            "content_type": "video/mp4" if media_kind == "video" else "audio/mp4",
        }

    async def async_play(
        self, entity_id, url, title, repeat, shuffle, **kwargs
    ):
        self.calls.append(
            (
                "play",
                entity_id,
                url,
                repeat,
                shuffle,
                kwargs.get("media_kind", "audio"),
            )
        )

    async def async_play_playlist(self, entity_id, name, index, repeat, shuffle):
        self.calls.append(("playlist", entity_id, name, index, repeat, shuffle))

    async def async_control(self, entity_id, action, **kwargs):
        self.calls.append(("control", entity_id, action, kwargs))


class FakeCoordinator:
    def __init__(self, hass, api):
        self.hass = hass
        self.api = api
        self.last_update_success = True
        self.data = {
            "version": "5.2.0",
            "sessions": {
                "media_player.living_room": {
                    "state": "playing",
                    "current_track": TRACKS[0],
                    "last_position": 12,
                    "last_duration": 180,
                    "repeat": "all",
                    "shuffle": True,
                    "track_count": 2,
                    "index": 0,
                }
            },
        }

    async def async_request_refresh(self):
        return None

    def async_add_listener(self, *args, **kwargs):
        return lambda: None


def make_player(hass, api):
    coordinator = FakeCoordinator(hass, api)
    entry = SimpleNamespace(
        entry_id="entry-1",
        options={"default_entity_id": "media_player.living_room"},
        data={},
    )
    return YouTubeProPlayer(coordinator, entry)


@pytest.mark.asyncio
async def test_media_source_browse_and_resolve(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    api = FakeApi()
    source = YouTubeProMediaSource(hass, FakeCoordinator(hass, api))

    root = await source.async_browse_media(MediaSourceItem(hass, DOMAIN, "", None))
    assert len(root.children) == 7

    identifier = f"playlist/{_encode_identifier('Yêu thích')}"
    playlist = await source.async_browse_media(
        MediaSourceItem(hass, DOMAIN, identifier, None)
    )
    assert len(playlist.children) == 2
    assert playlist.children[1].identifier.startswith("playlist-track/")

    resolved = await source.async_resolve_media(
        MediaSourceItem(hass, DOMAIN, playlist.children[1].identifier, None)
    )
    assert resolved.mime_type == "audio/mp4"
    assert api.calls[-1] == ("resolve", TRACKS[1]["url"], "audio")


@pytest.mark.asyncio
async def test_media_source_personal_mix(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    api = FakeApi()
    source = YouTubeProMediaSource(hass, FakeCoordinator(hass, api))

    mix = await source.async_browse_media(
        MediaSourceItem(hass, DOMAIN, "personal-mix", None)
    )

    assert mix.title == "Mix cá nhân · Phòng khách"
    assert len(mix.children) == 2
    assert api.calls[-1][0] == "personal_mix"


@pytest.mark.asyncio
async def test_media_source_queue_uses_target_player(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    api = FakeApi()
    source = YouTubeProMediaSource(hass, FakeCoordinator(hass, api))

    queue = await source.async_browse_media(
        MediaSourceItem(
            hass,
            DOMAIN,
            "queue",
            "media_player.living_room",
        )
    )

    assert len(queue.children) == 2
    assert api.queue_requests[-1] == {
        "limit": 200,
        "entity_id": "media_player.living_room",
    }


@pytest.mark.asyncio
async def test_video_media_browser_search_and_resolve(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    api = FakeApi()
    source = YouTubeProMediaSource(hass, FakeCoordinator(hass, api))

    video_root = await source.async_browse_media(
        MediaSourceItem(hass, DOMAIN, "videos", None)
    )
    assert video_root.media_content_type == MediaType.VIDEO
    assert video_root.children

    identifier = f"video-search/{_encode_identifier('video hot')}"
    results = await source.async_browse_media(
        MediaSourceItem(hass, DOMAIN, identifier, None)
    )
    assert results.children[0].media_class == MediaClass.VIDEO
    assert results.children[0].identifier.startswith("video-track/")

    resolved = await source.async_resolve_media(
        MediaSourceItem(
            hass,
            DOMAIN,
            results.children[0].identifier,
            "media_player.living_room",
        )
    )
    assert resolved.mime_type == "video/mp4"
    assert api.calls[-1] == ("resolve", VIDEO_TRACKS[0]["url"], "video")
    assert api.resolve_targets[-1] == "media_player.living_room"


@pytest.mark.asyncio
async def test_virtual_player_search_and_play(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    api = FakeApi()
    player = make_player(hass, api)

    results = await player.async_search_media(
        SearchMediaQuery(search_query="nhạc chill")
    )
    assert len(results.result) == 2
    await player.async_play_media(
        MediaType.MUSIC, results.result[0].media_content_id
    )
    await player.async_media_next_track()

    assert player.media_title == "Bài Một"
    assert (
        "play",
        "media_player.living_room",
        TRACKS[0]["url"],
        "all",
        True,
        "audio",
    ) in api.calls
    assert any(
        call[:3] == ("control", "media_player.living_room", "next")
        for call in api.calls
    )


@pytest.mark.asyncio
async def test_virtual_player_video_search_and_play(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    api = FakeApi()
    player = make_player(hass, api)

    results = await player.async_search_media(
        SearchMediaQuery(
            search_query="video hot",
            media_content_type=MediaType.VIDEO,
        )
    )
    assert len(results.result) == 1
    assert results.result[0].media_class == MediaClass.VIDEO
    await player.async_play_media(
        MediaType.VIDEO, results.result[0].media_content_id
    )

    assert (
        "play",
        "media_player.living_room",
        VIDEO_TRACKS[0]["url"],
        "all",
        True,
        "video",
    ) in api.calls
