from collections import deque
from typing import Any

import pytest

from custom_components.youtube_pro import ENQUEUE_SCHEMA, START_RADIO_SCHEMA
from custom_components.youtube_pro.api import YouTubeProApi


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self.payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def json(self, *, content_type=None):
        return self.payload


class FakeSession:
    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = deque(responses)
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any):
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.popleft()


def test_queue_and_radio_service_schemas():
    enqueue = ENQUEUE_SCHEMA(
        {
            "entity_id": "media_player.living_room",
            "url": "https://www.youtube.com/watch?v=one",
            "position": "next",
            "media_kind": "video",
        }
    )
    radio = START_RADIO_SCHEMA(
        {
            "entity_id": "media_player.living_room",
            "url": "https://www.youtube.com/watch?v=one",
            "limit": 12,
            "mode": "append",
        }
    )

    assert enqueue["position"] == "next"
    assert enqueue["media_kind"] == "video"
    assert radio["limit"] == 12
    assert radio["mode"] == "append"


@pytest.mark.asyncio
async def test_api_sends_targeted_queue_and_radio_payloads():
    session = FakeSession(
        FakeResponse({"success": True}),
        FakeResponse({"success": True}),
        FakeResponse({"success": True, "tracks": []}),
    )
    api = YouTubeProApi(session, "http://youtube-pro-addon:2032", "token")

    await api.async_enqueue(
        "https://www.youtube.com/watch?v=one",
        "Video One",
        media_kind="video",
        entity_id="media_player.living_room",
        position="next",
    )
    await api.async_start_radio(
        "media_player.living_room",
        "https://www.youtube.com/watch?v=one",
        "Video One",
        media_kind="video",
        limit=12,
        mode="append",
    )
    await api.async_queue(entity_id="media_player.living_room", limit=50)

    enqueue = session.calls[0]
    assert enqueue["url"].endswith("/api/integration/enqueue")
    assert enqueue["json"] == {
        "url": "https://www.youtube.com/watch?v=one",
        "title": "Video One",
        "media_kind": "video",
        "entity_id": "media_player.living_room",
        "position": "next",
    }

    radio = session.calls[1]
    assert radio["url"].endswith("/api/integration/radio")
    assert radio["json"]["entity_id"] == "media_player.living_room"
    assert radio["json"]["seed"]["media_kind"] == "video"
    assert radio["json"]["limit"] == 12
    assert radio["json"]["mode"] == "append"
    assert radio["json"]["start_if_missing"] is True

    queue = session.calls[2]
    assert queue["method"] == "GET"
    assert queue["url"].endswith(
        "/api/integration/queue?offset=0&limit=50&entity_id=media_player.living_room"
    )
