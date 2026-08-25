import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

LICENSE_KEY_PATTERN = re.compile(r"^YTP(?:-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{5}){4}$")
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{24,256}$")
REFRESH_SECONDS = 5 * 60
REGISTER_REFRESH_SECONDS = 20 * 60
DEFAULT_OFFLINE_GRACE_SECONDS = 72 * 60 * 60
MAX_OFFLINE_GRACE_SECONDS = 7 * 24 * 60 * 60


class LicenseManager:
    def __init__(
        self,
        data_dir,
        app_version,
        options_loader,
        private_writer,
        logger,
        http_session=None,
        clock=None,
    ):
        self.data_dir = data_dir
        self.app_version = app_version
        self.options_loader = options_loader
        self.private_writer = private_writer
        self.logger = logger
        self.http = http_session or requests.Session()
        self.clock = clock or time.time
        self.installation_file = os.path.join(data_dir, "youtube_pro_license_installation_id_v400")
        self.installation_secret_file = os.path.join(data_dir, "youtube_pro_license_installation_secret_v400")
        self.activation_file = os.path.join(data_dir, "youtube_pro_license_activation_token_v400")
        self.state_file = os.path.join(data_dir, "youtube_pro_license_state_v400.json")
        self.lock = threading.RLock()
        self.state = self._load_state()

    def _load_state(self):
        try:
            with open(self.state_file, "r", encoding="utf-8") as handle:
                value = json.load(handle)
                return value if isinstance(value, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save_state(self):
        os.makedirs(self.data_dir, exist_ok=True)
        temp_path = f"{self.state_file}.{secrets.token_hex(8)}.tmp"
        descriptor = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(self.state, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.state_file)
            os.chmod(self.state_file, 0o600)
        except (TypeError, ValueError):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def _read_private_token(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                value = handle.read(512).strip()
        except OSError:
            return ""
        if not TOKEN_PATTERN.fullmatch(value):
            return ""
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return value

    def installation_id(self):
        with self.lock:
            value = self._read_private_token(self.installation_file)
            if value:
                return value
            value = secrets.token_urlsafe(32)
            self.private_writer(self.installation_file, value + "\n")
            return value

    def installation_secret(self):
        with self.lock:
            value = self._read_private_token(self.installation_secret_file)
            if value:
                return value
            value = secrets.token_urlsafe(32)
            self.private_writer(self.installation_secret_file, value + "\n")
            return value

    def activation_token(self):
        return self._read_private_token(self.activation_file)

    def options(self):
        value = self.options_loader()
        return value if isinstance(value, dict) else {}

    def server_url(self):
        value = str(self.options().get("license_server_url") or "").strip().rstrip("/")
        try:
            parsed = urlparse(value)
        except (TypeError, ValueError):
            return None
        allow_http = os.getenv("YOUTUBE_PRO_LICENSE_ALLOW_HTTP") == "1"
        if (
            parsed.scheme not in ({"https", "http"} if allow_http else {"https"})
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            return None
        return value

    def enforcement_enabled(self):
        return True

    def configured(self):
        return bool(self.server_url())

    @staticmethod
    def normalize_key(value):
        compact = re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()
        if not compact.startswith("YTP") or len(compact) != 23:
            return None
        normalized = "YTP-" + "-".join(compact[index:index + 5] for index in range(3, 23, 5))
        return normalized if LICENSE_KEY_PATTERN.fullmatch(normalized) else None

    @staticmethod
    def _parse_time(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            return None

    def _safe_remote_url(self, value):
        server = self.server_url()
        if not server:
            return None
        try:
            expected = urlparse(server)
            parsed = urlparse(str(value or ""))
            if parsed.scheme != expected.scheme or parsed.hostname != expected.hostname:
                return None
            if parsed.port != expected.port or parsed.username or parsed.password:
                return None
            return parsed.geturl()
        except (TypeError, ValueError):
            return None

    def _public_status_locked(self):
        now = self.clock()
        expires_at = self.state.get("expires_at")
        expiry = self._parse_time(expires_at)
        valid = bool(self.state.get("valid")) and (expiry is None or expiry > now)
        current_state = str(self.state.get("state") or "unlicensed")
        if expiry is not None and expiry <= now:
            valid = False
            current_state = "expired"
        configured = self.configured()
        if not configured:
            current_state = "not_configured"
            valid = False
        return {
            "configured": configured,
            "enforcement": self.enforcement_enabled(),
            "valid": valid,
            "state": current_state,
            "code": self.state.get("code"),
            "plan_code": self.state.get("plan_code"),
            "plan_name": self.state.get("plan_name"),
            "key_prefix": self.state.get("key_prefix"),
            "expires_at": expires_at,
            "last_checked_at": self.state.get("last_checked_at"),
            "last_success_at": self.state.get("last_success_at"),
            "offline_grace_until": self.state.get("offline_grace_until"),
            "portal_url": self._safe_remote_url(self.state.get("portal_url")) or self.server_url(),
            "claim_url": self._safe_remote_url(self.state.get("claim_url")),
            "claim_expires_at": self.state.get("claim_expires_at"),
            "installation_suffix": self.installation_id()[-8:],
            "error": self.state.get("error"),
        }

    def current_status(self):
        with self.lock:
            return self._public_status_locked()

    def integration_status(self):
        status = self.current_status()
        return {
            "valid": status["valid"],
            "state": status["state"],
            "code": status["code"],
            "plan_code": status["plan_code"],
            "expires_at": status["expires_at"],
        }

    def _update_from_valid_response(self, data, activation_token=None):
        now = self.clock()
        grace_seconds = max(
            0,
            min(int(data.get("offline_grace_seconds") or DEFAULT_OFFLINE_GRACE_SECONDS), MAX_OFFLINE_GRACE_SECONDS),
        )
        self.state.update(
            {
                "valid": True,
                "state": "active",
                "code": str(data.get("code") or "active"),
                "plan_code": data.get("plan_code"),
                "plan_name": data.get("plan_name"),
                "key_prefix": data.get("key_prefix"),
                "expires_at": data.get("expires_at"),
                "last_checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "last_success_at": now,
                "offline_grace_until": now + grace_seconds,
                "next_check_at": now + max(300, min(int(data.get("refresh_after_seconds") or REFRESH_SECONDS), REFRESH_SECONDS)),
                "error": None,
            }
        )
        if activation_token:
            self.private_writer(self.activation_file, activation_token + "\n")
        self._save_state()
        return self._public_status_locked()

    def _update_invalid_response(self, data):
        self.state.update(
            {
                "valid": False,
                "state": "invalid",
                "code": str(data.get("code") or "license_invalid"),
                "last_checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "next_check_at": self.clock() + 15 * 60,
                "error": None,
            }
        )
        self._save_state()
        return self._public_status_locked()

    def _offline_status(self, error):
        now = self.clock()
        expiry = self._parse_time(self.state.get("expires_at"))
        grace_until = float(self.state.get("offline_grace_until") or 0)
        can_use_grace = bool(self.state.get("last_success_at")) and now <= grace_until and (expiry is None or now < expiry)
        self.state.update(
            {
                "valid": can_use_grace,
                "state": "offline_grace" if can_use_grace else "server_unreachable",
                "last_checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "next_check_at": now + 10 * 60,
                "error": str(error)[:240],
            }
        )
        self._save_state()
        return self._public_status_locked()

    def register_installation(self, force=False):
        with self.lock:
            server = self.server_url()
            if not server:
                return self._public_status_locked()
            now = self.clock()
            if not force and self.state.get("claim_url") and now < float(self.state.get("claim_refresh_at") or 0):
                return self._public_status_locked()
        try:
            response = self.http.post(
                f"{server}/api/v1/installations/register",
                json={
                    "installation_id": self.installation_id(),
                    "installation_secret": self.installation_secret(),
                    "addon_version": self.app_version,
                },
                timeout=12,
            )
            data = response.json() if response.content else {}
            if response.status_code >= 400 or not data.get("ok"):
                raise RuntimeError(str(data.get("code") or f"HTTP {response.status_code}"))
            with self.lock:
                now = self.clock()
                expires_in = max(60, min(int(data.get("claim_expires_in") or 1800), 3600))
                self.state.update(
                    {
                        "valid": False,
                        "state": "unlicensed",
                        "code": "license_required",
                        "portal_url": self._safe_remote_url(data.get("portal_url")) or server,
                        "claim_url": self._safe_remote_url(data.get("claim_url")),
                        "claim_expires_at": now + expires_in,
                        "claim_refresh_at": now + min(expires_in - 30, REGISTER_REFRESH_SECONDS),
                        "last_checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "next_check_at": now + REGISTER_REFRESH_SECONDS,
                        "error": None,
                    }
                )
                self._save_state()
                return self._public_status_locked()
        except (OSError, RuntimeError, TypeError, ValueError, requests.RequestException) as error:
            with self.lock:
                return self._offline_status(error)

    def activate(self, raw_key):
        key = self.normalize_key(raw_key)
        if not key:
            raise ValueError("License Key không đúng định dạng")
        server = self.server_url()
        if not server:
            raise ValueError("Chưa cấu hình license_server_url")
        response = self.http.post(
            f"{server}/api/v1/licenses/activate",
            json={
                "license_key": key,
                "installation_id": self.installation_id(),
                "installation_secret": self.installation_secret(),
                "addon_version": self.app_version,
            },
            timeout=15,
        )
        data = response.json() if response.content else {}
        if response.status_code == 429 or response.status_code >= 500:
            raise RuntimeError("License server tạm thời không sẵn sàng")
        if not data.get("valid"):
            with self.lock:
                return self._update_invalid_response(data)
        activation_token = str(data.get("activation_token") or "")
        if not TOKEN_PATTERN.fullmatch(activation_token):
            raise RuntimeError("License server không trả activation token hợp lệ")
        with self.lock:
            return self._update_from_valid_response(data, activation_token=activation_token)

    def validate(self, force=False):
        token = self.activation_token()
        if not token:
            return self.register_installation(force=force)
        server = self.server_url()
        if not server:
            with self.lock:
                return self._public_status_locked()
        with self.lock:
            if not force and self.clock() < float(self.state.get("next_check_at") or 0):
                return self._public_status_locked()
        try:
            response = self.http.post(
                f"{server}/api/v1/licenses/validate",
                json={
                    "activation_token": token,
                    "installation_id": self.installation_id(),
                    "installation_secret": self.installation_secret(),
                    "addon_version": self.app_version,
                },
                timeout=12,
            )
            data = response.json() if response.content else {}
            if response.status_code == 429 or response.status_code >= 500:
                raise RuntimeError(f"HTTP {response.status_code}")
            with self.lock:
                if data.get("valid"):
                    return self._update_from_valid_response(data)
                return self._update_invalid_response(data)
        except (OSError, RuntimeError, TypeError, ValueError, requests.RequestException) as error:
            with self.lock:
                return self._offline_status(error)

    def status(self, force=False):
        if not self.configured():
            return self.current_status()
        return self.validate(force=force)

    def deactivate(self):
        token = self.activation_token()
        server = self.server_url()
        if token and server:
            try:
                self.http.post(
                    f"{server}/api/v1/licenses/deactivate",
                    json={
                        "activation_token": token,
                        "installation_id": self.installation_id(),
                        "installation_secret": self.installation_secret(),
                    },
                    timeout=8,
                )
            except (OSError, RuntimeError, TypeError, ValueError, requests.RequestException) as error:
                self.logger.warning("License deactivate remote call failed: %s", error)
        with self.lock:
            try:
                os.unlink(self.activation_file)
            except FileNotFoundError:
                pass
            self.state = {
                "valid": False,
                "state": "unlicensed",
                "code": "license_required",
                "portal_url": server,
                "next_check_at": 0,
            }
            self._save_state()
        return self.register_installation(force=True) if server else self.current_status()

    def permits_use(self):
        return self.current_status()["valid"]

    def worker(self):
        while True:
            try:
                if self.configured():
                    self.validate(force=False)
            except (OSError, RuntimeError, TypeError, ValueError, requests.RequestException) as error:
                self.logger.warning("License worker failed: %s", error)
            time.sleep(60)
