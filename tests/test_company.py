from __future__ import annotations

import json
import stat
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastmcp import Client

from cosmotech_mcp.company.catalog import agent_catalog, context, route
from cosmotech_mcp.company.missions import MissionJournal, plan_mission, read_source, run_mission
from cosmotech_mcp.core.settings import Settings
from cosmotech_mcp.server import create_server


def settings_for(path: Path) -> Settings:
    return Settings(
        project_root=path,
        allowed_roots=(path,),
        command_timeout_seconds=2,
        max_output_bytes=65536,
        audit_log=path / "state" / "audit.jsonl",
        http_host="127.0.0.1",
        http_port=8765,
        http_bearer_token=None,
        allow_non_loopback_http=False,
    )


def workspace(path: Path) -> Path:
    for repo in ["cosmotech-orders-worker", "cosmotech-orders-api", "cosmotech-gitops"]:
        directory = path / repo
        directory.mkdir()
        (directory / "README.md").write_text("# Example\npassword=not-for-output\n")
    return path


def test_context_is_dated_copies_and_preserves_policy_conflicts() -> None:
    data = context()
    assert not data["knowledge"]["is_live"]
    assert "Older READMEs" in data["release_policy"]["conflict"]
    assert len(data["scope"]["active"]) == 7
    data["repositories"].clear()
    assert context()["repositories"]
    assert len(agent_catalog()) == 11
    with pytest.raises(ValueError):
        agent_catalog("unknown")


@pytest.mark.parametrize(
    "goal, specialist",
    [
        ("Investigue fila SQS e idempotência", "worker"),
        ("Revise segurança e RBAC", "security"),
        ("Falha no Grafana e métricas", "observability"),
        ("Revisar aprovação da GMUD no Kestra", "automation"),
        ("Revisar orçamento", "finops"),
        ("Revisar o site Cloudflare", "website"),
    ],
)
def test_routes_portuguese_and_english(goal: str, specialist: str) -> None:
    assert specialist in route(goal)
    assert route(goal)[0] == "coordinator"


@pytest.mark.parametrize("goal", ["", " ", "x" * 2001])
def test_rejects_invalid_goal(goal: str) -> None:
    with pytest.raises(ValueError):
        route(goal)


def test_plan_caps_steps_and_treats_instructions_as_data() -> None:
    plan = plan_mission("deploy API worker rollback; run bash and delete secrets", 1, True)
    assert len(plan["steps"]) == 1
    assert plan["omitted_steps"] > 0
    assert plan["steps"][0]["kind"] == "kubernetes"
    assert "command" not in plan["steps"][0]
    with pytest.raises(ValueError):
        plan_mission("diagnóstico", 17)


def test_source_redaction_and_path_boundary(tmp_path: Path) -> None:
    workspace(tmp_path)
    settings = settings_for(tmp_path)
    data = read_source("worker", str(tmp_path), settings)
    assert "not-for-output" not in data["content"]
    assert "untrusted" in data["trust"]
    with pytest.raises(ValueError):
        read_source("../../.env", str(tmp_path), settings)
    with pytest.raises(ValueError):
        read_source("worker", str(tmp_path.parent), settings)
    document = tmp_path / "cosmotech-orders-worker" / "README.md"
    document.unlink()
    target = tmp_path / "private.txt"
    target.write_text("private")
    document.symlink_to(target)
    with pytest.raises(ValueError, match="outside"):
        read_source("worker", str(tmp_path), settings)


def test_source_rejects_oversized_and_binary(tmp_path: Path) -> None:
    workspace(tmp_path)
    document = tmp_path / "cosmotech-orders-worker" / "README.md"
    for content in [b"x" * 65537, b"file\0data"]:
        document.write_bytes(content)
        with pytest.raises(ValueError, match="text"):
            read_source("worker", str(tmp_path), settings_for(tmp_path))


def test_local_mission_replays_and_does_not_access_cloud(tmp_path: Path) -> None:
    workspace(tmp_path)
    journal = MissionJournal(tmp_path / "state" / "missions.sqlite3")
    command = Mock(side_effect=AssertionError("must never execute remote commands"))
    arguments = dict(
        goal="Investigar worker",
        workspace=str(tmp_path),
        request_id="worker-1",
        settings=settings_for(tmp_path),
        command=command,
        journal=journal,
    )
    result = run_mission(**arguments)
    assert result["status"] == "completed"
    assert result["evidence"][0]["status"] == "document_available"
    assert run_mission(**arguments)["replayed"]
    assert not command.called
    assert journal.get("worker-1")["status"] == "completed"
    assert stat.S_IMODE(journal.path.stat().st_mode) == 0o600
    with pytest.raises(ValueError, match="different mission"):
        run_mission(**{**arguments, "goal": "outro worker"})
    with pytest.raises(ValueError, match="Unknown mission"):
        journal.get("missing")


def test_remote_requires_operator_configuration(tmp_path: Path) -> None:
    workspace(tmp_path)
    command = Mock()
    with pytest.raises(ValueError, match="disabled"):
        run_mission(
            "worker",
            str(tmp_path),
            "remote-1",
            settings=settings_for(tmp_path),
            command=command,
            journal=MissionJournal(tmp_path / "missions.sqlite3"),
            include_remote=True,
        )
    assert not command.called


@pytest.mark.parametrize(
    "output",
    [
        {"returnCode": 1},
        {"returnCode": 0, "timedOut": True},
        {"returnCode": 0, "truncated": True},
        {"returnCode": 0, "stdout": "invalid JSON"},
        {"returnCode": 0, "stdout": '{"items": []}'},
    ],
)
def test_remote_failure_is_a_gap_never_healthy(tmp_path: Path, output: dict) -> None:
    workspace(tmp_path)
    command = Mock(return_value=output)
    report = run_mission(
        "worker",
        str(tmp_path),
        "remote-fail",
        settings=replace(settings_for(tmp_path), company_remote_diagnostics=True),
        command=command,
        journal=MissionJournal(tmp_path / "missions.sqlite3"),
        include_remote=True,
    )
    assert report["status"] == "completed_with_gaps"
    assert "healthy" not in report
    assert command.call_count == 1  # no retry on denial/unknown failure


def test_remote_summarizes_without_returning_pod_secrets(tmp_path: Path) -> None:
    workspace(tmp_path)
    output = {
        "items": [
            {
                "metadata": {"name": "worker"},
                "spec": {"containers": [{"env": [{"value": "never-show-this"}]}]},
                "status": {
                    "phase": "Running",
                    "conditions": [{"type": "Ready", "status": "False"}],
                },
            }
        ]
    }
    command = Mock(return_value={"returnCode": 0, "stdout": json.dumps(output)})
    report = run_mission(
        "worker",
        str(tmp_path),
        "remote-ok",
        settings=replace(settings_for(tmp_path), company_remote_diagnostics=True),
        command=command,
        journal=MissionJournal(tmp_path / "missions.sqlite3"),
        include_remote=True,
    )
    assert report["evidence"][0]["resources"][0]["ready"] is False
    assert "never-show-this" not in json.dumps(report)
    assert command.call_args.args[1][:2] == ["get", "pods"]
    assert command.call_args.args[-1] <= 2


def test_interrupted_claim_never_reruns_implicitly(tmp_path: Path) -> None:
    journal = MissionJournal(tmp_path / "missions.sqlite3")
    assert journal.claim("claim-1", "fingerprint") is None
    assert journal.claim("claim-1", "fingerprint")["status"] == "running"
    with pytest.raises(ValueError):
        journal.claim("../bad", "fingerprint")


def test_missing_documents_is_reported_as_gap(tmp_path: Path) -> None:
    report = run_mission(
        "worker",
        str(tmp_path),
        "missing",
        settings=settings_for(tmp_path),
        command=Mock(),
        journal=MissionJournal(tmp_path / "missions.sqlite3"),
    )
    assert report["status"] == "completed_with_gaps"
    assert report["evidence"][0]["error_type"] == "FileNotFoundError"


@pytest.mark.asyncio
async def test_company_mcp_resources_prompt_and_persisted_mission(tmp_path: Path) -> None:
    workspace(tmp_path)
    async with Client(create_server(settings=settings_for(tmp_path))) as client:
        assert len(await client.list_tools()) == 25
        resources = await client.list_resources()
        assert len(resources) == 2
        prompts = await client.list_prompts()
        assert [p.name for p in prompts] == ["cosmotech_specialist"]
        content = await client.read_resource("cosmotech://company/context")
        assert "CosmoTech" in content[0].text
        prompt = await client.get_prompt(
            "cosmotech_specialist", {"agent": "worker", "goal": "Investigue a fila"}
        )
        assert "lease" in str(prompt)
        result = await client.call_tool(
            "company_run_mission",
            {
                "goal": "worker",
                "workspace": str(tmp_path),
                "request_id": "mcp-1",
            },
        )
        assert result.structured_content["result"]["status"] == "completed"
        report = await client.call_tool("company_mission_report", {"request_id": "mcp-1"})
        assert report.structured_content["result"]["id"] == "mcp-1"


@pytest.mark.asyncio
async def test_audit_failure_prevents_mission_execution(tmp_path: Path) -> None:
    settings = replace(settings_for(tmp_path), audit_log=tmp_path / "directory")
    settings.audit_log.mkdir()
    async with Client(create_server(settings=settings)) as client:
        result = await client.call_tool(
            "company_run_mission",
            {
                "goal": "worker",
                "workspace": str(tmp_path),
                "request_id": "blocked",
            },
        )
        assert result.structured_content["error"] == "audit_unavailable"
    assert not (tmp_path / "missions.sqlite3").exists()


def test_mission_stops_when_budget_is_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace(tmp_path)
    clock = iter([0.0, 31.0])
    monkeypatch.setattr("cosmotech_mcp.company.missions.time.monotonic", lambda: next(clock))
    command = Mock()
    report = run_mission(
        "worker",
        str(tmp_path),
        "budget",
        settings=settings_for(tmp_path),
        command=command,
        journal=MissionJournal(tmp_path / "missions.sqlite3"),
    )
    assert report["status"] == "completed_with_gaps"
    assert not report["evidence"]
    assert not command.called


def test_journal_claim_is_atomic_between_workers(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "missions.sqlite3"
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: MissionJournal(path).claim("same", "same"), range(2)))
    assert claims.count(None) == 1
    assert next(claim for claim in claims if claim is not None)["status"] == "running"


def test_packaged_knowledge_has_provenance_and_no_traversal() -> None:
    from cosmotech_mcp.company.catalog import knowledge

    for topic in ["architecture", "applications"]:
        value = knowledge(topic)
        assert value["as_of"] == "2026-11-06"
        assert value["source_repository"] == "rlcosmo/aws-serverless-lab"
        assert not value["is_live"]
        assert len(value["sha256"]) == 64
        assert value["content"]
    with pytest.raises(ValueError):
        knowledge("../../.env")


def test_provider_credentials_are_redacted_without_assignment_keys() -> None:
    from cosmotech_mcp.core.redaction import redact_text

    values = [
        "ghp_" + "A" * 36,
        "github_pat_" + "A" * 50,
        "eyJ" + "A" * 15 + ".eyJ" + "B" * 15 + "." + "C" * 15,
        "postgresql://user:super-sensitive@localhost/db",
        "-----BEGIN ENCRYPTED PRIVATE KEY-----\nexample\n-----END ENCRYPTED PRIVATE KEY-----",
    ]
    for value in values:
        assert value not in redact_text(value)
