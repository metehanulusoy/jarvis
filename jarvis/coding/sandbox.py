"""Safe code execution in a subprocess."""

from __future__ import annotations

import os
import resource
import signal
import subprocess
import tempfile
from dataclasses import dataclass

# Env vars that must NEVER leak into sandboxed code
_SECRET_PATTERNS = (
    "KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "AUTH",
    "GMAIL", "IMAP", "OPENAI", "ANTHROPIC", "AWS_",
)

# Max output size to prevent memory exhaustion (1MB)
_MAX_OUTPUT = 1024 * 1024


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False


def _safe_env() -> dict[str, str]:
    """Build a minimal environment with secrets stripped out."""
    safe = {}
    for k, v in os.environ.items():
        if any(pat in k.upper() for pat in _SECRET_PATTERNS):
            continue
        safe[k] = v
    safe["PYTHONDONTWRITEBYTECODE"] = "1"
    safe["PYTHONUNBUFFERED"] = "1"
    return safe


def _set_resource_limits():
    """Set resource limits for the child process (called via preexec_fn)."""
    limits = [
        # Max 512MB virtual memory
        (resource.RLIMIT_AS, 512 * 1024 * 1024),
        # Max 50MB file writes
        (resource.RLIMIT_FSIZE, 50 * 1024 * 1024),
    ]
    # RLIMIT_NPROC not available on all platforms
    if hasattr(resource, "RLIMIT_NPROC"):
        limits.append((resource.RLIMIT_NPROC, 100))
    # RLIMIT_RSS as fallback for memory on macOS (advisory, not enforced by all kernels)
    if hasattr(resource, "RLIMIT_RSS"):
        limits.append((resource.RLIMIT_RSS, 512 * 1024 * 1024))

    for limit_type, value in limits:
        try:
            resource.setrlimit(limit_type, (value, value))
        except (ValueError, resource.error, OSError):
            pass  # Not supported on this platform — timeout is the hard backstop


def run_code(code: str, timeout: int = 30) -> ExecutionResult:
    """Run Python code in an isolated subprocess with resource limits."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write(code)
        f.flush()
        tmppath = f.name

    try:
        result = subprocess.run(
            ["python3", tmppath],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir(),
            env=_safe_env(),
            preexec_fn=_set_resource_limits,
        )
        return ExecutionResult(
            stdout=result.stdout[:_MAX_OUTPUT],
            stderr=result.stderr[:_MAX_OUTPUT],
            returncode=result.returncode,
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            stdout="",
            stderr=f"Execution timed out after {timeout}s",
            returncode=-1,
            timed_out=True,
        )
    finally:
        try:
            os.unlink(tmppath)
        except OSError:
            pass
