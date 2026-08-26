from collections import deque
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.youtube_pro.addon_discovery import (
    async_discover_addon_urls,
    is_auto_url,
)


class FakeResponse:
    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self.payload = payload

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

    def get(self, url: str, **kwargs: Any):
        self.calls.append({"url": url, **kwargs})
        return self.responses.popleft()


@pytest.mark.asyncio
async def test_discovery_prefers_supervisor_hostname():
    session = FakeSession(
        FakeResponse(
            200,
            {
                "data": {
                    "addons": [
                        {
                            "slug": "local_youtube_pro_addon",
                            "state": "started",
                        }
                    ]
                }
            },
        ),
        FakeResponse(
            200,
            {"data": {"hostname": "local-youtube-pro-addon"}},
        ),
    )

    urls = await async_discover_addon_urls(
        session,
        supervisor_token="supervisor-token",
    )

    assert urls[0] == "http://local-youtube-pro-addon:2032"
    assert session.calls[0]["url"] == "http://supervisor/addons"
    assert session.calls[0]["headers"] == {
        "Authorization": "Bearer supervisor-token"
    }


@pytest.mark.asyncio
async def test_discovery_has_safe_fallbacks_without_supervisor():
    hass = SimpleNamespace(
        config=SimpleNamespace(internal_url="http://192.168.1.20:8123")
    )
    urls = await async_discover_addon_urls(FakeSession(), hass=hass, supervisor_token="")

    assert "http://youtube-pro-addon:2032" in urls
    assert "http://youtube_pro_addon:2032" in urls
    assert "http://192.168.1.20:2032" in urls
    assert urls[-1] == "http://homeassistant.local:2032"


@pytest.mark.parametrize("value", ("", "auto", "AUTO", "automatic"))
def test_auto_url_values_are_detected(value: str):
    assert is_auto_url(value)
