from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cosmotech_mcp.core.redaction import redact


class JsonAuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def record(
        self,
        *,
        tool: str,
        arguments: dict[str, Any],
        outcome: str,
        error_type: str | None = None,
    ) -> None:
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tool": tool,
            "arguments": redact(arguments),
            "outcome": outcome,
            "error_type": error_type,
        }
        encoded = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
        with self._lock:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            descriptor = os.open(
                self.path,
                os.O_APPEND | os.O_CREAT | os.O_WRONLY,
                0o600,
            )
            try:
                with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
                    stream.write(encoded + "\n")
            except Exception:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise
