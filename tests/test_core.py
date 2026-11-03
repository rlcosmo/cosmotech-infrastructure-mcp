from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from cosmotech_mcp.core.audit import JsonAuditLog
from cosmotech_mcp.core.commands import run_read_only_command
from cosmotech_mcp.core.policy import Policy, PolicyDenied
from cosmotech_mcp.core.redaction import redact, redact_text
from cosmotech_mcp.core.settings import Settings, ensure_allowed_path


def make_settings(root: Path, *, timeout: int = 2, max_output: int = 256) -> Settings:
    return Settings(
        project_root=root,
        allowed_roots=(root,),
        command_timeout_seconds=timeout,
        max_output_bytes=max_output,
        audit_log=root / "audit.jsonl",
        http_host="127.0.0.1",
        http_port=8765,
        http_bearer_token=None,
        allow_non_loopback_http=False,
    )


def test_redacts_secret_keys_and_known_secret_formats() -> None:
    aws_key = "AKIA" + "A" * 16
    value = {
        "password": "never-show-this",
        "env": [{"name": "AWS_SECRET_ACCESS_KEY", "value": "also-hidden"}],
        "database": "DATABASE_URL=postgres://user:db-secret@localhost/orders",
        "text": f"Authorization: Bearer abc.def.ghi {aws_key}",
    }
    output = json.dumps(redact(value))
    assert "never-show-this" not in output
    assert "also-hidden" not in output
    assert "db-secret" not in output
    assert "abc.def.ghi" not in output
    assert aws_key not in output
    assert "[REDACTED_AWS_ACCESS_KEY]" in redact_text(aws_key)


def test_audit_is_jsonl_private_and_redacted(tmp_path: Path) -> None:
    log_path = tmp_path / "private" / "audit.jsonl"
    audit = JsonAuditLog(log_path)
    audit.record(
        tool="unit_test",
        arguments={"token": "sensitive-value", "region": "us-east-1"},
        outcome="success",
    )
    raw = log_path.read_text(encoding="utf-8")
    event = json.loads(raw)
    assert event["arguments"]["token"] == "[REDACTED]"
    assert event["arguments"]["region"] == "us-east-1"
    assert "sensitive-value" not in raw
    assert stat.S_IMODE(log_path.stat().st_mode) == 0o600


def test_policy_blocks_shell_and_secret_resource() -> None:
    policy = Policy()
    with pytest.raises(PolicyDenied):
        policy.require_command("bash")
    with pytest.raises(PolicyDenied):
        policy.require_kubectl_resource("secrets")
    with pytest.raises(PolicyDenied):
        policy.require_read_only_terraform_action("apply")
    assert policy.require_kubectl_resource("pods") == "pods"


def test_allowed_path_rejects_path_outside_configured_roots(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    rejected = tmp_path / "rejected"
    allowed.mkdir()
    rejected.mkdir()
    settings = make_settings(allowed)
    assert ensure_allowed_path(allowed, settings) == allowed
    with pytest.raises(ValueError, match="outside configured"):
        ensure_allowed_path(rejected, settings)


def test_command_runner_caps_redacts_and_uses_no_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "fake-git"
    executable.write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.stdout.write('password=hidden ' + 'x' * 1000)\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    monkeypatch.setattr("cosmotech_mcp.core.commands.shutil.which", lambda _: str(executable))
    result = run_read_only_command(
        "git",
        [],
        cwd=tmp_path,
        settings=make_settings(tmp_path, max_output=64),
        policy=Policy(),
    )
    assert result.returncode == 0
    assert result.truncated
    assert len(result.stdout.encode("utf-8")) <= 64
    assert "hidden" not in result.stdout


def test_command_runner_times_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = tmp_path / "fake-git"
    executable.write_text(
        "#!/usr/bin/env python3\nimport time\ntime.sleep(5)\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    monkeypatch.setattr("cosmotech_mcp.core.commands.shutil.which", lambda _: str(executable))
    result = run_read_only_command(
        "git",
        [],
        cwd=tmp_path,
        settings=make_settings(tmp_path, timeout=1),
        policy=Policy(),
    )
    assert result.timed_out
    assert result.returncode is not None


def test_settings_requires_explicit_non_loopback_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COSMOTECH_ALLOWED_ROOTS", "")
    monkeypatch.setenv("MCP_HTTP_HOST", "0.0.0.0")
    monkeypatch.delenv("MCP_HTTP_ALLOW_NON_LOOPBACK", raising=False)
    monkeypatch.setenv("MCP_HTTP_BEARER_TOKEN", "test-token")
    with pytest.raises(ValueError, match="Non-loopback"):
        Settings.from_env()
