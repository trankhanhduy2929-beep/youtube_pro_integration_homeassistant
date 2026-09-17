from types import SimpleNamespace

import pytest

from custom_components.youtube_pro.diagnostics import (
    async_get_config_entry_diagnostics,
)


@pytest.mark.asyncio
async def test_config_entry_diagnostics_redacts_token():
    entry = SimpleNamespace(
        title="YouTube Pro",
        state="loaded",
        data={"url": "auto", "token": "super-secret-token"},
        options={"default_entity_id": "media_player.living_room"},
        runtime_data=SimpleNamespace(
            last_update_success=True,
            data={"health": "ok"},
        ),
    )

    result = await async_get_config_entry_diagnostics(None, entry)

    assert result["entry"]["data"]["token"] == "**REDACTED**"
    assert result["entry"]["data"]["url"] == "auto"
    assert result["coordinator"]["data"] == {"health": "ok"}
    assert result["coordinator"]["last_update_success"] is True


@pytest.mark.asyncio
async def test_config_entry_diagnostics_handles_missing_runtime_data():
    entry = SimpleNamespace(
        title="YouTube Pro",
        state="setup_error",
        data={"token": "secret"},
        options={},
    )

    result = await async_get_config_entry_diagnostics(None, entry)

    assert result["entry"]["data"]["token"] == "**REDACTED**"
    assert result["coordinator"]["data"] is None
    assert result["coordinator"]["last_update_success"] is None
