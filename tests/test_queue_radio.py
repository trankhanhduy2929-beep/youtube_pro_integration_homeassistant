from collections import deque
from typing import Any

import pytest

from custom_components.youtube_pro import (
    ENQUEUE_SCHEMA,
    LISTENER_FEEDBACK_SCHEMA,
    PLAY_PERSONAL_MIX_SCHEMA,
    START_RADIO_SCHEMA,
)
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
            "profile_id": "default",
        }
    )
    personal_mix = PLAY_PERSONAL_MIX_SCHEMA(
        {
            "entity_id": "media_player.living_room",
            "limit": 12,
            "refresh": True,
        }
    )
    feedback = LISTENER_FEEDBACK_SCHEMA(
        {
            "action": "undo",
        }
    )

    assert enqueue["position"] == "next"
    assert enqueue["media_kind"] == "video"
    assert radio["limit"] == 12
    assert radio["mode"] == "append"
    assert radio["profile_id"] == "default"
    assert personal_mix["limit"] == 12
    assert personal_mix["refresh"] is True
    assert feedback["action"] == "undo"


@pytest.mark.asyncio
async def test_api_sends_targeted_queue_and_radio_payloads():
    session = FakeSession(
        FakeResponse({"success": True}),
        FakeResponse({"success": True}),
        FakeResponse({"success": True, "tracks": []}),
        FakeResponse({"success": True, "tracks": []}),
        FakeResponse({"success": True, "preferences": {}}),
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
        profile_id="default",
    )
    await api.async_queue(entity_id="media_player.living_room", limit=50)
    await api.async_personal_mix(
        profile_id="default",
        limit=12,
        refresh=True,
        entity_id="media_player.living_room",
        start=True,
        shuffle=False,
    )
    await api.async_listener_feedback("undo", profile_id="default")

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
    assert radio["json"]["profile_id"] == "default"

    queue = session.calls[2]
    assert queue["method"] == "GET"
    assert queue["url"].endswith(
        "/api/integration/queue?offset=0&limit=50&entity_id=media_player.living_room"
    )

    personal_mix = session.calls[3]
    assert personal_mix["url"].endswith("/api/integration/personal-mix")
    assert personal_mix["json"] == {
        "media_kind": "audio",
        "limit": 12,
        "refresh": True,
        "start": True,
        "shuffle": False,
        "profile_id": "default",
        "entity_id": "media_player.living_room",
    }

    feedback = session.calls[4]
    assert feedback["url"].endswith("/api/integration/preferences/feedback")
    assert feedback["json"] == {"action": "undo", "profile_id": "default"}
