"""Build deterministic HACS, manual-install and source archives."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "youtube_pro"
INTEGRATION = ROOT / "custom_components" / DOMAIN
FIXED_TIMESTAMP = (2026, 8, 25, 0, 0, 0)
REPO_FOLDER = "youtube-pro-home-assistant"


def manifest_version() -> str:
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    return str(manifest["version"])


def integration_files() -> list[Path]:
    return sorted(
        (
            path
            for path in INTEGRATION.rglob("*")
            if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts
        ),
        key=lambda path: path.as_posix(),
    )


def repository_files() -> list[Path]:
    excluded_dirs = {".git", ".pytest_cache", ".ruff_cache", ".venv", "dist"}
    return sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and not any(part in excluded_dirs or part == "__pycache__" for part in path.parts)
            and path.suffix != ".pyc"
        ),
        key=lambda path: path.as_posix(),
    )


def write_zip(output: Path, files: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for source, name in files:
            info = zipfile.ZipInfo(name, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(), compresslevel=9)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    version = manifest_version()
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)

    hacs = output / "youtube_pro.zip"
    manual = output / "youtube_pro_manual.zip"
    versioned_hacs = output / f"youtube_pro_v{version}_hacs.zip"
    versioned_manual = output / f"youtube_pro_v{version}_manual.zip"
    source = output / f"youtube_pro_homeassistant_v{version}_source.zip"

    files = integration_files()
    write_zip(hacs, [(path, path.relative_to(INTEGRATION).as_posix()) for path in files])
    write_zip(
        manual,
        [
            (
                path,
                f"custom_components/{DOMAIN}/{path.relative_to(INTEGRATION).as_posix()}",
            )
            for path in files
        ],
    )
    write_zip(
        source,
        [
            (path, f"{REPO_FOLDER}/{path.relative_to(ROOT).as_posix()}")
            for path in repository_files()
        ],
    )
    versioned_hacs.write_bytes(hacs.read_bytes())
    versioned_manual.write_bytes(manual.read_bytes())

    archives = (hacs, manual, versioned_hacs, versioned_manual, source)
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in archives),
        encoding="utf-8",
    )
    for path in (*archives, output / "SHA256SUMS.txt"):
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
