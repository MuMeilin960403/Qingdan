"""Application paths, data-directory resolution and identity."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

APP_NAME = "轻单"
APP_NAME_EN = "Qingdan"
APP_VERSION = "1.2.0"
ORG_NAME = "Qingdan"


class DataDirectoryError(RuntimeError):
    """Raised when no writable directory can be found for app data."""


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def assets_dir() -> Path:
    return project_root() / "assets"


def application_dir() -> Path:
    """Directory containing the executable, or the source checkout."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


def _unique(items: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for item in items:
        key = str(item).casefold()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def candidate_data_dirs() -> list[Path]:
    """Ordered writable-data candidates; the first is the portable folder."""

    candidates: list[Path] = []
    override = os.environ.get("QINGDAN_DATA_DIR")
    if override:
        candidates.append(Path(override).expanduser().resolve())

    # Keep the no-install build genuinely portable. This also makes the app
    # work on managed machines where AppData is locked down for unsigned apps.
    candidates.append(application_dir() / "data")

    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        roaming = os.environ.get("APPDATA")
        if local:
            candidates.append(Path(local) / APP_NAME_EN)
        if roaming:
            candidates.append(Path(roaming) / APP_NAME_EN)
        candidates.append(Path.home() / "Documents" / APP_NAME_EN)
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            candidates.append(Path(xdg) / APP_NAME_EN.lower())
        candidates.append(Path.home() / ".local" / "share" / APP_NAME_EN.lower())

    candidates.append(Path(tempfile.gettempdir()) / APP_NAME_EN)
    return _unique(candidates)


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".write-test-{uuid4().hex}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def resolve_data_dir() -> Path:
    """Find a writable data directory, preferring the portable one."""

    candidates = candidate_data_dirs()
    for candidate in candidates:
        if _is_writable(candidate):
            return candidate

    tried = "\n".join(f"· {path}" for path in candidates)
    raise DataDirectoryError(
        "找不到可写的数据目录。请把「轻单」文件夹放到可写的位置，"
        "或设置 QINGDAN_DATA_DIR 指向一个可写文件夹。\n\n"
        f"已尝试：\n{tried}"
    )


_CACHED_DATA_DIR: Path | None = None


def app_data_dir() -> Path:
    global _CACHED_DATA_DIR
    if _CACHED_DATA_DIR is None:
        _CACHED_DATA_DIR = resolve_data_dir()
    return _CACHED_DATA_DIR


def tasks_path() -> Path:
    return app_data_dir() / "tasks.json"
