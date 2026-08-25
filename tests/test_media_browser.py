from types import SimpleNamespace

import pytest
from homeassistant.components.media_player import SearchMediaQuery
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


class FakeApi:
    base_url = "http://homeassistant.local:2032"

    def __init__(self):
        self.calls = []

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
        }

    async def async_playlist(self, name, **kwargs):
        assert name == "Yêu thích"
        return {"tracks": TRACKS, "total": 2, "has_more": False}

    async def async_queue(self, **kwargs):
        return {"tracks": TRACKS, "total": 2, "has_more": False}

    async def async_history(self, **kwargs):
        return {"tracks": TRACKS[:1], "total": 1, "has_more": False}

    async def async_search(self, query, **kwargs):
        self.calls.append(("search", query))
        return {"results": TRACKS, "has_more": False}

    async def async_resolve(self, url):
        self.calls.append(("resolve", url))
        return {
            "media_url": "http://192.168.1.2:2032/api/media/token/audio.m4a",
            "content_type": "audio/mp4",
        }

    async def async_play(self, entity_id, url, title, repeat, shuffle):
        self.calls.append(("play", entity_id, url, repeat, shuffle))

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
            "version": "4.0.0",
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


@pytest.mark.asyncio
async def test_media_source_browse_and_resolve(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    api = FakeApi()
    source = YouTubeProMediaSource(hass, FakeCoordinator(hass, api))

    root = await source.async_browse_media(MediaSourceItem(hass, DOMAIN, "", None))
    assert len(root.children) == 5

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
    assert api.calls[-1] == ("resolve", TRACKS[1]["url"])


@pytest.mark.asyncio
async def test_virtual_player_search_and_play(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    api = FakeApi()
    coordinator = FakeCoordinator(hass, api)
    entry = SimpleNamespace(
        entry_id="entry-1",
        options={"default_entity_id": "media_player.living_room"},
        data={},
    )
    player = YouTubeProPlayer(coordinator, entry)

    results = await player.async_search_media(
        SearchMediaQuery(search_query="nhạc chill")
    )
    assert len(results.result) == 2
    await player.async_play_media(
        MediaType.MUSIC, results.result[0].media_content_id
    )
    await player.async_media_next_track()

    assert player.media_title == "Bài Một"
    assert ("play", "media_player.living_room", TRACKS[0]["url"], "all", True) in api.calls
    assert any(call[:3] == ("control", "media_player.living_room", "next") for call in api.calls)
