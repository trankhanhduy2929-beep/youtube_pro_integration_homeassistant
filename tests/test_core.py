import importlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import pytest


@pytest.fixture()
def addon(tmp_path, monkeypatch):
    monkeypatch.setenv("YOUTUBE_PRO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("YOUTUBE_PRO_DISABLE_WORKERS", "1")
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root))
    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.save_json(
        module.OPTIONS_FILE,
        {"license_server_url": "https://license.example.test", "license_enforcement": True},
    )
    module.license_manager.state = {
        "valid": True,
        "state": "active",
        "code": "active",
        "plan_code": "test",
        "plan_name": "Test",
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    yield module
    sys.modules.pop("app", None)


def test_cast_profile_prefers_relay_after_direct_failures(addon):
    entity_id = "media_player.test_speaker"
    addon.record_cast_result(entity_id, "direct", "audio/mp4", False, 3200, "did not start")
    addon.record_cast_result(entity_id, "direct", "audio/mp4", False, 3000, "did not start")

    plan = addon.cast_attempt_plan(
        entity_id,
        {"content_type": "audio/mp4", "stream_url": "https://example.googlevideo.com/audio"},
    )

    assert plan[0][0] == "relay"
    assert Path(addon.CAST_PREF_FILE).is_file()


def test_cast_profile_records_success(addon):
    entity_id = "media_player.test_speaker"
    addon.record_cast_result(entity_id, "relay", "music", True, 850)

    profile = addon.cast_preference_status(entity_id)

    assert profile["preferred_transport"] == "relay"
    assert profile["preferred_media_type"] == "music"


def test_search_uses_batched_cache(addon):
    class FakeYDL:
        calls: ClassVar[list[tuple[str, int]]] = []

        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, query, download=False):
            self.calls.append((query, self.options["playlistend"]))
            count = int(query.split(":", 1)[0].replace("ytsearch", ""))
            return {
                "entries": [
                    {"id": f"id{index}", "title": f"Track {index}", "duration": 180}
                    for index in range(count)
                ]
            }

    with patch.object(addon.yt_dlp, "YoutubeDL", FakeYDL):
        assert len(addon.search_youtube("demo", 0, 20)) == 20
        assert len(addon.search_youtube("demo", 20, 20)) == 20
        assert len(addon.search_youtube("demo", 40, 20)) == 20

    assert FakeYDL.calls == [("ytsearch40:demo", 40), ("ytsearch80:demo", 80)]


def test_cast_profile_api_can_reset_entity(addon):
    entity_id = "media_player.test_speaker"
    addon.record_cast_result(entity_id, "relay", "music", True, 850)
    client = addon.app.test_client()

    response = client.delete("/api/cast-preferences", json={"entity_id": entity_id})

    assert response.status_code == 200
    assert entity_id not in response.get_json()["profiles"]


def sample_tracks():
    return [
        {"id": "one", "title": "One", "url": "https://www.youtube.com/watch?v=one", "duration": 100},
        {"id": "two", "title": "Two", "url": "https://www.youtube.com/watch?v=two", "duration": 120},
        {"id": "three", "title": "Three", "url": "https://www.youtube.com/watch?v=three", "duration": 140},
    ]


def fake_resolved(url):
    track = next(track for track in sample_tracks() if track["url"] == url)
    return {
        "source_url": url,
        "stream_url": "https://example.googlevideo.com/audio",
        "content_type": "audio/mp4",
        "extension": "m4a",
        "content_length": 1000,
        "headers": {},
        "track": track,
        "details": {},
    }


def test_backend_playback_session_start_and_next(addon):
    entity_id = "media_player.test_speaker"
    with (
        patch.object(addon, "resolve_track", side_effect=fake_resolved),
        patch.object(addon, "cast_entry", return_value="http://relay/audio"),
    ):
        session = addon.start_playback_session(entity_id, sample_tracks(), 0, "off", False, "test", "Test")
        assert session["state"] == "starting"
        assert session["current_track"]["id"] == "one"

        session = addon.advance_playback_session(entity_id, 1)
        assert session["index"] == 1
        assert session["current_track"]["id"] == "two"

        addon.advance_playback_session(entity_id, 1)
        session = addon.advance_playback_session(entity_id, 1)
        assert session["state"] == "completed"


def test_repeat_one_replays_current_track(addon):
    entity_id = "media_player.test_speaker"
    with (
        patch.object(addon, "resolve_track", side_effect=fake_resolved),
        patch.object(addon, "cast_entry", return_value="http://relay/audio"),
    ):
        addon.start_playback_session(entity_id, sample_tracks(), 1, "one", False)
        session = addon.advance_playback_session(entity_id, 1, automatic=True)

    assert session["index"] == 1
    assert session["current_track"]["id"] == "two"


def test_natural_end_requests_backend_auto_next(addon):
    entity_id = "media_player.test_speaker"
    session = addon.normalize_playback_session(
        {
            "entity_id": entity_id,
            "tracks": sample_tracks(),
            "index": 0,
            "state": "playing",
            "last_state": "playing",
            "last_position": 95,
            "last_duration": 100,
            "track_started_at": 1,
        }
    )
    with addon.state_lock:
        addon.playback_sessions[entity_id] = session

    with patch.object(addon, "request_playback_advance") as request_advance:
        addon.playback_handle_state(
            entity_id,
            {"state": "idle", "attributes": {"media_position": 100, "media_duration": 100}},
        )

    request_advance.assert_called_once_with(entity_id)


def test_playback_sessions_are_persisted(addon):
    entity_id = "media_player.test_speaker"
    session = addon.normalize_playback_session(
        {"entity_id": entity_id, "tracks": sample_tracks(), "index": 2, "state": "paused"}
    )
    with addon.state_lock:
        addon.playback_sessions[entity_id] = session
    addon.persist_playback_sessions()

    saved = addon.load_json(addon.PLAYBACK_FILE, {})

    assert saved[entity_id]["index"] == 2
    assert saved[entity_id]["state"] == "paused"

def test_player_state_accepts_backward_seek(addon):
    entity_id = "media_player.test_speaker"
    session = addon.normalize_playback_session(
        {
            "entity_id": entity_id,
            "tracks": sample_tracks(),
            "index": 0,
            "state": "playing",
            "last_state": "playing",
            "last_position": 80,
            "last_duration": 100,
        }
    )
    with addon.state_lock:
        addon.playback_sessions[entity_id] = session

    addon.playback_handle_state(
        entity_id,
        {"state": "playing", "attributes": {"media_position": 20, "media_duration": 100}},
    )

    assert addon.playback_session_for(entity_id)["last_position"] == 20

def test_stop_marks_session_before_home_assistant_call(addon):
    entity_id = "media_player.test_speaker"
    session = addon.normalize_playback_session(
        {"entity_id": entity_id, "tracks": sample_tracks(), "state": "playing"}
    )
    with addon.state_lock:
        addon.playback_sessions[entity_id] = session

    def assert_stopping(service, payload):
        current = addon.playback_session_for(entity_id)
        assert service == "media_stop"
        assert payload == {"entity_id": entity_id}
        assert current["state"] == "stopped"
        assert current["stop_requested"] is True

    with patch.object(addon, "ha_service", side_effect=assert_stopping):
        addon.stop_playback_session(entity_id)

def test_failed_timer_retries_without_marking_day_complete(addon):
    now = addon.datetime(2026, 8, 24, 9, 30, 0)
    timer = addon.normalize_timer(
        {
            "id": "morning",
            "time": "09:30",
            "type": "play",
            "entity_id": "media_player.test_speaker",
            "playlist_name": "Missing",
        }
    )
    with addon.state_lock:
        addon.timers = [timer]

    first = addon.run_timer_cycle(now)
    throttled = addon.run_timer_cycle(now + addon.timedelta(seconds=10))
    retried = addon.run_timer_cycle(now + addon.timedelta(seconds=31))

    assert first[0]["success"] is False
    assert throttled == []
    assert retried[0]["success"] is False
    assert addon.timers[0]["last_trigger_date"] is None

def test_successful_timer_marks_trigger_date(addon):
    now = addon.datetime(2026, 8, 24, 21, 0, 0)
    timer = addon.normalize_timer(
        {
            "id": "stop-night",
            "time": "21:00",
            "type": "stop",
            "entity_id": "media_player.test_speaker",
        }
    )
    with addon.state_lock:
        addon.timers = [timer]

    with patch.object(addon, "stop_entity") as stop_entity:
        result = addon.run_timer_cycle(now)

    stop_entity.assert_called_once_with("media_player.test_speaker")
    assert result == [{"id": "stop-night", "success": True, "error": ""}]
    assert addon.timers[0]["last_trigger_date"] == "2026-08-24"

def test_integration_token_is_private_and_stable(addon):
    first = addon.integration_api_token()
    second = addon.integration_api_token()
    mode = stat.S_IMODE(os.stat(addon.INTEGRATION_TOKEN_FILE).st_mode)

    assert first == second
    assert len(first) >= 48
    assert mode == 0o600

def test_integration_routes_require_bearer_without_opening_admin_api(addon):
    client = addon.app.test_client()
    remote = {"REMOTE_ADDR": "192.168.1.20"}
    token = addon.integration_api_token()

    missing = client.get("/api/integration/health", environ_base=remote)
    wrong = client.get(
        "/api/integration/health",
        headers={"Authorization": "Bearer wrong-token"},
        environ_base=remote,
    )
    valid = client.get(
        "/api/integration/health",
        headers={"Authorization": f"Bearer {token}"},
        environ_base=remote,
    )
    admin = client.get(
        "/api/status",
        headers={"Authorization": f"Bearer {token}"},
        environ_base=remote,
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert valid.status_code == 200
    assert valid.get_json()["api_version"] == 2
    assert admin.status_code == 403

def test_integration_token_can_only_rotate_via_ingress(addon):
    client = addon.app.test_client()
    remote = {"REMOTE_ADDR": "192.168.1.20"}
    old_token = addon.integration_api_token()

    forbidden = client.get("/api/integration-token", environ_base=remote)
    rejected = client.post("/api/integration-token")
    response = client.post(
        "/api/integration-token",
        headers={"X-YouTube-Pro-Action": "rotate-token"},
    )
    new_token = response.get_json()["token"]
    old_auth = client.get(
        "/api/integration/health",
        headers={"Authorization": f"Bearer {old_token}"},
        environ_base=remote,
    )
    new_auth = client.get(
        "/api/integration/health",
        headers={"Authorization": f"Bearer {new_token}"},
        environ_base=remote,
    )

    assert forbidden.status_code == 403
    assert rejected.status_code == 400
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert new_token != old_token
    assert old_auth.status_code == 401
    assert new_auth.status_code == 200

def test_integration_play_endpoint_uses_backend_session(addon):
    client = addon.app.test_client()
    remote = {"REMOTE_ADDR": "192.168.1.20"}
    headers = {"Authorization": f"Bearer {addon.integration_api_token()}"}
    session = {
        "entity_id": "media_player.test_speaker",
        "state": "starting",
        "current_track": sample_tracks()[0],
    }

    with patch.object(addon, "start_playback_session", return_value=session) as start_session:
        response = client.post(
            "/api/integration/play",
            json={
                "entity_id": "media_player.test_speaker",
                "url": sample_tracks()[0]["url"],
                "title": "One",
            },
            headers=headers,
            environ_base=remote,
        )

    assert response.status_code == 200
    assert response.get_json()["session"] == session
    assert start_session.call_args.args[0] == "media_player.test_speaker"
    assert start_session.call_args.args[1][0]["url"] == sample_tracks()[0]["url"]

def test_integration_token_is_not_exposed_by_status_or_backup(addon):
    client = addon.app.test_client()
    remote = {"REMOTE_ADDR": "192.168.1.20"}
    token = addon.integration_api_token()
    headers = {"Authorization": f"Bearer {token}"}

    integration_status = client.get(
        "/api/integration/status",
        headers=headers,
        environ_base=remote,
    )
    ingress_status = client.get("/api/status")
    backup = client.get("/api/backup")

    assert integration_status.status_code == 200
    assert ingress_status.status_code == 200
    assert backup.status_code == 200
    assert token not in integration_status.get_data(as_text=True)
    assert token not in ingress_status.get_data(as_text=True)
    assert token not in backup.get_data(as_text=True)

def test_stale_auto_next_does_not_advance_replaced_session(addon):
    entity_id = "media_player.test_speaker"
    old_session = addon.normalize_playback_session(
        {
            "session_id": "old-session",
            "play_id": "old-play",
            "entity_id": entity_id,
            "tracks": sample_tracks(),
            "index": 0,
            "state": "playing",
        }
    )
    new_session = addon.normalize_playback_session(
        {
            "session_id": "new-session",
            "play_id": "new-play",
            "entity_id": entity_id,
            "tracks": sample_tracks(),
            "index": 1,
            "state": "playing",
        }
    )
    captured = {}

    class DeferredThread:
        def __init__(self, target, daemon):
            captured["target"] = target

        def start(self):
            return None

    with addon.state_lock:
        addon.playback_sessions[entity_id] = old_session
    with patch.object(addon.threading, "Thread", DeferredThread):
        addon.request_playback_advance(entity_id)
    with addon.state_lock:
        addon.playback_sessions[entity_id] = new_session
    with patch.object(addon, "playback_play_current") as play_current:
        captured["target"]()

    play_current.assert_not_called()
    assert addon.playback_session_for(entity_id)["index"] == 1

def test_media_browser_library_and_playlist_endpoints(addon):
    client = addon.app.test_client()
    remote = {"REMOTE_ADDR": "192.168.1.20"}
    headers = {"Authorization": f"Bearer {addon.integration_api_token()}"}
    with addon.state_lock:
        addon.playlists = {"Yêu thích": sample_tracks()}
        addon.queue = sample_tracks()[:2]
        addon.history = sample_tracks()[1:]
        addon.search_history = ["nhạc chill"]

    library = client.get(
        "/api/integration/library", headers=headers, environ_base=remote
    )
    playlist = client.get(
        "/api/integration/playlists/Y%C3%AAu%20th%C3%ADch?limit=2",
        headers=headers,
        environ_base=remote,
    )
    queue = client.get(
        "/api/integration/queue", headers=headers, environ_base=remote
    )
    history = client.get(
        "/api/integration/history", headers=headers, environ_base=remote
    )

    assert library.status_code == 200
    assert library.get_json()["playlists"][0]["track_count"] == 3
    assert library.get_json()["search_history"] == ["nhạc chill"]
    assert len(library.get_json()["discovery"]) >= 4
    assert playlist.get_json()["total"] == 3
    assert playlist.get_json()["has_more"] is True
    assert len(playlist.get_json()["tracks"]) == 2
    assert len(queue.get_json()["tracks"]) == 2
    assert history.get_json()["tracks"][0]["id"] == "three"

def test_media_browser_search_records_query(addon):
    client = addon.app.test_client()
    remote = {"REMOTE_ADDR": "192.168.1.20"}
    headers = {"Authorization": f"Bearer {addon.integration_api_token()}"}
    with patch.object(addon, "search_youtube", return_value=sample_tracks()[:2]):
        response = client.post(
            "/api/integration/search",
            json={"query": "  Nhạc Chill  ", "limit": 2},
            headers=headers,
            environ_base=remote,
        )

    assert response.status_code == 200
    assert response.get_json()["query"] == "Nhạc Chill"
    assert len(response.get_json()["results"]) == 2
    assert addon.search_history[0] == "Nhạc Chill"
    assert addon.load_json(addon.SEARCH_HISTORY_FILE, [])[0] == "Nhạc Chill"

def test_media_browser_resolve_returns_relay_url(addon):
    client = addon.app.test_client()
    remote = {"REMOTE_ADDR": "192.168.1.20"}
    headers = {"Authorization": f"Bearer {addon.integration_api_token()}"}
    with (
        patch.object(addon, "resolve_track", return_value=fake_resolved(sample_tracks()[0]["url"])),
        patch.object(addon, "media_base_url", return_value="http://192.168.1.2:2032"),
    ):
        response = client.post(
            "/api/integration/resolve",
            json={"url": sample_tracks()[0]["url"]},
            headers=headers,
            environ_base=remote,
        )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["media_url"].startswith("http://192.168.1.2:2032/api/media/")
    assert payload["content_type"] == "audio/mp4"
    assert payload["track"]["id"] == "one"

def test_integration_control_forwards_pause(addon):
    client = addon.app.test_client()
    remote = {"REMOTE_ADDR": "192.168.1.20"}
    headers = {"Authorization": f"Bearer {addon.integration_api_token()}"}
    with patch.object(addon, "ha_service") as service:
        response = client.post(
            "/api/integration/control",
            json={"entity_id": "media_player.test_speaker", "action": "pause"},
            headers=headers,
            environ_base=remote,
        )

    assert response.status_code == 200
    service.assert_called_once_with(
        "media_pause", {"entity_id": "media_player.test_speaker"}
    )


def test_license_identity_and_secret_are_private(addon, tmp_path):
    manager = addon.LicenseManager(
        str(tmp_path),
        "3.3.0",
        dict,
        addon.write_private_text,
        addon.logger,
    )

    installation_id = manager.installation_id()
    installation_secret = manager.installation_secret()

    assert installation_id == manager.installation_id()
    assert installation_secret == manager.installation_secret()
    assert installation_id != installation_secret
    assert stat.S_IMODE(Path(manager.installation_file).stat().st_mode) == 0o600
    assert stat.S_IMODE(Path(manager.installation_secret_file).stat().st_mode) == 0o600
    assert "installation_secret" not in manager.current_status()


def test_integration_license_status_never_exposes_claim_or_secrets(addon):
    addon.save_json(
        addon.OPTIONS_FILE,
        {
            "license_server_url": "https://license.example.test",
            "license_enforcement": True,
        },
    )
    addon.license_manager.state = {
        "valid": False,
        "state": "unlicensed",
        "code": "license_required",
        "plan_code": None,
        "expires_at": None,
        "claim_url": "https://license.example.test/connect?token=claim-secret",
        "activation_token": "activation-secret",
        "installation_secret": "installation-secret",
    }
    client = addon.app.test_client()
    headers = {"Authorization": f"Bearer {addon.integration_api_token()}"}
    remote = {"REMOTE_ADDR": "192.168.1.20"}

    responses = [
        client.get("/api/integration/health", headers=headers, environ_base=remote),
        client.get("/api/integration/status", headers=headers, environ_base=remote),
        client.post(
            "/api/integration/search",
            json={"query": "test"},
            headers=headers,
            environ_base=remote,
        ),
    ]

    assert [response.status_code for response in responses] == [402, 402, 402]
    serialized = json.dumps([response.get_json() for response in responses])
    assert "claim_url" not in serialized
    assert "claim-secret" not in serialized
    assert "activation-secret" not in serialized
    assert "installation-secret" not in serialized


def test_license_activation_and_offline_grace(addon, tmp_path, monkeypatch):
    class FakeResponse:
        content = b"{}"
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class FakeSession:
        def __init__(self):
            self.calls = []
            self.fail = False

        def post(self, url, json, timeout):
            self.calls.append((url, json, timeout))
            if self.fail:
                raise addon.requests.ConnectionError("offline")
            return FakeResponse(
                {
                    "valid": True,
                    "code": "active",
                    "plan_code": "monthly_1m",
                    "plan_name": "1 tháng",
                    "key_prefix": "YTP-AAAAA-•••••-AAAAA",
                    "expires_at": "2099-01-01T00:00:00+00:00",
                    "activation_token": "a" * 48,
                    "refresh_after_seconds": 300,
                    "offline_grace_seconds": 3600,
                }
            )

    now = [1_800_000_000.0]
    session = FakeSession()
    monkeypatch.setenv("YOUTUBE_PRO_LICENSE_ALLOW_HTTP", "1")
    manager = addon.LicenseManager(
        str(tmp_path),
        "3.3.0",
        lambda: {"license_server_url": "http://license.example.test", "license_enforcement": True},
        addon.write_private_text,
        addon.logger,
        http_session=session,
        clock=lambda: now[0],
    )

    status = manager.activate("YTP-AAAAA-AAAAA-AAAAA-AAAAA")
    assert status["valid"] is True
    assert stat.S_IMODE(Path(manager.activation_file).stat().st_mode) == 0o600
    assert session.calls[0][1]["installation_secret"] == manager.installation_secret()
    serialized_state = Path(manager.state_file).read_text(encoding="utf-8")
    assert "YTP-AAAAA-AAAAA-AAAAA-AAAAA" not in serialized_state
    assert "a" * 48 not in serialized_state

    session.fail = True
    now[0] += 301
    status = manager.validate(force=True)
    assert status["valid"] is True
    assert status["state"] == "offline_grace"

    now[0] += 3601
    status = manager.validate(force=True)
    assert status["valid"] is False
    assert status["state"] == "server_unreachable"


def test_license_enforcement_is_mandatory_and_secrets_are_not_exposed(addon):
    addon.save_json(
        addon.OPTIONS_FILE,
        {"license_server_url": "", "license_enforcement": True},
    )
    addon.license_manager.state = {
        "valid": False,
        "state": "invalid",
        "code": "license_blocked",
        "key_prefix": "YTP-AAAAA-•••••-AAAAA",
    }
    client = addon.app.test_client()

    blocked = client.post("/api/search", json={"query": "test"})
    assert blocked.status_code == 402

    status_response = client.get("/api/status")
    backup_response = client.get("/api/backup")
    status_payload = status_response.get_json()
    backup_payload = backup_response.get_json()
    license_payload = client.get("/api/license").get_json()
    assert status_response.status_code == 402
    assert backup_response.status_code == 402
    serialized = json.dumps([status_payload, backup_payload, license_payload])
    assert "installation_secret" not in serialized
    assert "YTP-AAAAA-AAAAA-AAAAA-AAAAA" not in serialized

    addon.save_json(
        addon.OPTIONS_FILE,
        {"license_server_url": "", "license_enforcement": False},
    )
    with patch.object(addon, "search_youtube", return_value=[]):
        still_blocked = client.post("/api/search", json={"query": "test"})
    assert still_blocked.status_code == 402
    assert addon.license_manager.enforcement_enabled() is True


def test_unlicensed_addon_only_exposes_license_gate_and_health(addon):
    addon.save_json(addon.OPTIONS_FILE, {"license_server_url": "", "license_enforcement": False})
    addon.license_manager.state = {"valid": False, "state": "unlicensed", "code": "license_required"}
    client = addon.app.test_client()
    integration_headers = {"Authorization": f"Bearer {addon.integration_api_token()}"}
    remote = {"REMOTE_ADDR": "192.168.1.20"}

    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/api/health", environ_base=remote).status_code == 200
    assert client.get("/api/license").status_code == 200

    blocked = [
        client.get("/api/status"),
        client.get("/api/backup"),
        client.get("/api/queue"),
        client.get("/api/playlists"),
        client.get("/api/integration-token"),
        client.get("/api/media/not-a-token/audio.m4a", environ_base=remote),
        client.get("/api/integration/health", headers=integration_headers, environ_base=remote),
    ]
    assert [response.status_code for response in blocked] == [402] * len(blocked)
    assert all(response.get_json()["code"] == "license_required" for response in blocked)
