"""Validate the YouTube Pro custom integration repository."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "youtube_pro"
INTEGRATION = ROOT / "custom_components" / DOMAIN
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f"cannot parse {path}: {error}")
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def main() -> int:
    required = (
        "__init__.py",
        "api.py",
        "config_flow.py",
        "const.py",
        "coordinator.py",
        "manifest.json",
        "media_player.py",
        "media_source.py",
        "sensor.py",
        "services.yaml",
        "strings.json",
        "translations/en.json",
        "translations/vi.json",
    )
    for relative in required:
        if not (INTEGRATION / relative).is_file():
            fail(f"missing required file: custom_components/{DOMAIN}/{relative}")

    manifest = load_json(INTEGRATION / "manifest.json")
    if manifest.get("domain") != DOMAIN:
        fail("manifest domain is not youtube_pro")
    version = str(manifest.get("version", ""))
    if not VERSION_PATTERN.fullmatch(version):
        fail(f"invalid integration version: {version}")
    if not manifest.get("config_flow"):
        fail("config_flow must be enabled")
    hacs = load_json(ROOT / "hacs.json")
    if hacs.get("filename") != "youtube_pro.zip":
        fail("hacs.json filename must be youtube_pro.zip")

    for path in ROOT.rglob("*"):
        if path.is_dir() and path.name in {"__pycache__", ".pytest_cache", ".ruff_cache"}:
            fail(f"cache directory must not be committed: {path.relative_to(ROOT)}")
        if path.is_file() and path.suffix == ".pyc":
            fail(f"compiled Python file must not be committed: {path.relative_to(ROOT)}")

    source = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in INTEGRATION.rglob("*.py")
    )
    forbidden = (
        "PAYOS_API_KEY",
        "PAYOS_CHECKSUM_KEY",
        "LICENSE_API_SERVICE_TOKEN",
        "DATABASE_URL",
        "ADMIN_PASSWORD",
    )
    leaked = [marker for marker in forbidden if marker in source]
    if leaked:
        fail(f"backend secret marker found in integration: {', '.join(leaked)}")

    print(f"Validated {DOMAIN} integration {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
