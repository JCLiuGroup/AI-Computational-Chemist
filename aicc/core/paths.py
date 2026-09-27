"""Collection and helper-script path discovery for AICC commands."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def find_collection_root(start: Path | None = None) -> Path | None:
    """Find the collection containing both ``procedures/`` and ``tools/``."""

    origin = (start or Path(__file__)).resolve()
    for parent in (origin, *origin.parents):
        if (parent / "procedures").is_dir() and (parent / "tools").is_dir():
            return parent
    return None


def collection_root() -> Path:
    """Return the collection containing the running CLI implementation."""

    discovered = find_collection_root()
    if discovered is not None:
        return discovered
    return (Path.home() / ".codex" / ".auto-computational-chemist").resolve()


def skill_source_root() -> Path:
    """Return the collection whose skills ``aicc skill`` should manage."""

    configured = (
        os.environ.get("AICC_COLLECTION")
        or os.environ.get("AICC_SOURCE")
        or os.environ.get("CDX_SKILL_SOURCE")
    )
    if configured:
        return Path(configured).expanduser().resolve()
    return collection_root()


def orchestrator_scripts_dir() -> Path:
    return collection_root() / "procedures" / "research-orchestrator" / "scripts"


def ensure_orchestrator_imports() -> Path:
    """Expose existing research-orchestrator helpers without duplicating them."""

    scripts_dir = orchestrator_scripts_dir()
    token = str(scripts_dir)
    if token not in sys.path:
        sys.path.insert(0, token)
    return scripts_dir
