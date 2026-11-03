from __future__ import annotations

import os
import selectors
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from cosmotech_mcp.core.policy import Policy
from cosmotech_mcp.core.redaction import redact_text
from cosmotech_mcp.core.settings import Settings, ensure_allowed_path


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: str
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    truncated: bool


def _kill_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        pass


def run_read_only_command(
    command: str,
    args: list[str],
    *,
    cwd: str | Path,
    settings: Settings,
    policy: Policy,
) -> CommandResult:
    policy.require_command(command)
    if len(args) > 64 or sum(len(item) for item in args) > 32768:
        raise ValueError("Command arguments exceed policy limits")
    if any(not isinstance(item, str) or "\x00" in item for item in args):
        raise ValueError("Command arguments must be strings without NUL bytes")
    working_directory = ensure_allowed_path(cwd, settings)
    executable = shutil.which(command)
    if executable is None:
        raise FileNotFoundError(f"Required executable is unavailable: {command}")

    process = subprocess.Popen(
        [executable, *args],
        cwd=working_directory,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        start_new_session=(os.name == "posix"),
        bufsize=0,
    )
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    total_captured = 0
    truncated = False
    timed_out = False
    deadline = time.monotonic() + settings.command_timeout_seconds

    while selector.get_map():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            _kill_process(process)
            deadline = time.monotonic() + 1
        for key, _ in selector.select(timeout=min(max(remaining, 0), 0.2)):
            try:
                chunk = os.read(key.fileobj.fileno(), 8192)
            except OSError:
                chunk = b""
            if not chunk:
                selector.unregister(key.fileobj)
                key.fileobj.close()
                continue
            remaining_bytes = settings.max_output_bytes - total_captured
            if remaining_bytes > 0:
                kept = chunk[:remaining_bytes]
                captured[key.data].extend(kept)
                total_captured += len(kept)
            if len(chunk) > max(remaining_bytes, 0):
                truncated = True
        if timed_out and process.poll() is None:
            _kill_process(process)

    returncode = process.wait(timeout=1)
    stdout = redact_text(captured["stdout"].decode("utf-8", errors="replace"))
    stderr = redact_text(captured["stderr"].decode("utf-8", errors="replace"))
    max_bytes = settings.max_output_bytes
    stdout_bytes = stdout.encode("utf-8")
    stderr_bytes = stderr.encode("utf-8")
    if len(stdout_bytes) + len(stderr_bytes) > max_bytes:
        truncated = True
        stdout_bytes = stdout_bytes[:max_bytes]
        remaining = max_bytes - len(stdout_bytes)
        stderr_bytes = stderr_bytes[:remaining]
        stdout = stdout_bytes.decode("utf-8", errors="ignore")
        stderr = stderr_bytes.decode("utf-8", errors="ignore")
    return CommandResult(
        command=command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        truncated=truncated,
    )
