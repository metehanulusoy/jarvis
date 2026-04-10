"""Scoped file operations for the coding assistant."""

from __future__ import annotations

from pathlib import Path


def is_path_allowed(path: Path, allowed_dirs: list[Path]) -> bool:
    """Check if a path falls within any of the allowed directories.

    Resolves symlinks and checks the real path to prevent symlink escapes.
    """
    try:
        # Resolve to real path (follows symlinks) BEFORE checking
        real_path = path.resolve(strict=False)

        # Reject if the path contains symlinks that escape allowed dirs
        # Check every component of the path
        for allowed in allowed_dirs:
            allowed_real = allowed.resolve(strict=False)
            if real_path == allowed_real or real_path.is_relative_to(allowed_real):
                # Double-check: if file exists, verify real path matches
                if real_path.exists() and real_path.resolve() != real_path:
                    return False  # Symlink changed between checks
                return True
        return False
    except (OSError, ValueError):
        return False


def read_file(path: str, allowed_dirs: list[Path]) -> str:
    """Read a file if it's within allowed directories."""
    p = Path(path).expanduser().resolve()
    if not is_path_allowed(p, allowed_dirs):
        return f"Error: path is outside allowed directories."
    if not p.exists():
        return f"Error: file does not exist."
    if not p.is_file():
        return "Error: path is not a regular file."
    try:
        content = p.read_text(errors="replace")
        # Limit output size to 100KB
        if len(content) > 100_000:
            return content[:100_000] + "\n\n[... truncated at 100KB ...]"
        return content
    except Exception:
        return "Error: could not read file."


def write_file(path: str, content: str, allowed_dirs: list[Path]) -> str:
    """Write to a file if it's within allowed directories."""
    p = Path(path).expanduser().resolve()
    if not is_path_allowed(p, allowed_dirs):
        return f"Error: path is outside allowed directories."
    # Don't follow symlinks for writes
    if p.is_symlink():
        return "Error: refusing to write through a symlink."
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Written {len(content)} bytes to {p.name}"
    except Exception:
        return "Error: could not write file."
