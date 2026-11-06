from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _positive_int(name: str, default: int, *, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 1 or value > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path
    allowed_roots: tuple[Path, ...]
    command_timeout_seconds: int
    max_output_bytes: int
    audit_log: Path
    http_host: str
    http_port: int
    http_bearer_token: str | None
    allow_non_loopback_http: bool
    company_remote_diagnostics: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        env_path = Path(os.getenv("COSMOTECH_ENV_FILE", PROJECT_ROOT / ".env"))
        load_dotenv(env_path, override=False)

        roots_value = os.getenv("COSMOTECH_ALLOWED_ROOTS", "").strip()
        roots = [PROJECT_ROOT]
        if roots_value:
            roots.extend(
                (PROJECT_ROOT / value).resolve()
                for value in roots_value.split(os.pathsep)
                if value.strip()
            )

        audit_value = os.getenv("COSMOTECH_AUDIT_LOG", "").strip()
        if audit_value:
            audit_path = Path(audit_value).expanduser().resolve()
        else:
            audit_path = (
                Path.home() / ".local" / "state" / "cosmotech-infrastructure-mcp" / "audit.jsonl"
            )

        host = os.getenv("MCP_HTTP_HOST", "127.0.0.1").strip()
        token = os.getenv("MCP_HTTP_BEARER_TOKEN", "").strip() or None
        allow_non_loopback = os.getenv("MCP_HTTP_ALLOW_NON_LOOPBACK", "false").lower() in {
            "1",
            "true",
            "yes",
        }
        if host not in {"127.0.0.1", "::1", "localhost"}:
            if not allow_non_loopback:
                raise ValueError(
                    "Non-loopback HTTP binding requires MCP_HTTP_ALLOW_NON_LOOPBACK=true"
                )
            if token is None:
                raise ValueError("HTTP transport requires MCP_HTTP_BEARER_TOKEN")

        return cls(
            project_root=PROJECT_ROOT,
            allowed_roots=tuple(dict.fromkeys(path.resolve() for path in roots)),
            command_timeout_seconds=_positive_int(
                "COSMOTECH_COMMAND_TIMEOUT_SECONDS", 15, maximum=300
            ),
            max_output_bytes=_positive_int("COSMOTECH_MAX_OUTPUT_BYTES", 65536, maximum=1048576),
            audit_log=audit_path,
            http_host=host,
            http_port=_positive_int("MCP_HTTP_PORT", 8765, maximum=65535),
            http_bearer_token=token,
            allow_non_loopback_http=allow_non_loopback,
            company_remote_diagnostics=os.getenv(
                "COSMOTECH_COMPANY_REMOTE_DIAGNOSTICS", "false"
            ).lower()
            == "true",
        )


def ensure_allowed_path(path: str | Path, settings: Settings) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = settings.project_root / candidate
    resolved = candidate.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("Path must refer to an existing directory")
    if not any(resolved == root or root in resolved.parents for root in settings.allowed_roots):
        raise ValueError("Path is outside configured allowed roots")
    return resolved
