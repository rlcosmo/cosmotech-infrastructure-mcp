from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from cosmotech_mcp.core.settings import PROJECT_ROOT, Settings
from cosmotech_mcp.server import create_server


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        project_root=PROJECT_ROOT,
        allowed_roots=(PROJECT_ROOT,),
        command_timeout_seconds=2,
        max_output_bytes=4096,
        audit_log=tmp_path / "audit.jsonl",
        http_host="127.0.0.1",
        http_port=8765,
        http_bearer_token=None,
        allow_non_loopback_http=False,
    )


@pytest.mark.asyncio
async def test_server_registers_tools_and_executes_local_tool(tmp_path: Path) -> None:
    server = create_server(settings=make_settings(tmp_path))
    async with Client(server) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        assert {
            "aws_get_identity",
            "aws_inventory",
            "aws_eks_inventory",
            "aws_ecr_inventory",
            "aws_ec2_inventory",
            "aws_sqs_inventory",
            "aws_dynamodb_inventory",
            "aws_iam_inventory",
            "eks_health",
            "kubectl_get",
            "kubectl_logs",
            "kubectl_describe",
            "helm_inventory",
            "terraform_validate",
            "terraform_plan",
            "linux_system_info",
            "docker_inspect",
            "git_status",
            "observability_health",
        } <= names
        linux_tool = next(tool for tool in tools if tool.name == "linux_system_info")
        assert linux_tool.annotations.read_only_hint is True
        assert linux_tool.annotations.destructive_hint is False
        result = await client.call_tool("linux_system_info", {})
        assert not result.is_error
        assert "rootDiskBytes" in json.dumps(result.structured_content)
    audit_lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["outcome"] for line in audit_lines] == ["started", "success"]


def test_http_server_has_auth_verifier_when_token_is_set(tmp_path: Path) -> None:
    server = create_server(settings=make_settings(tmp_path), auth_token="mcp-test-token")
    assert server.auth is not None


@pytest.mark.asyncio
async def test_stdio_process_performs_mcp_handshake_and_tool_call(tmp_path: Path) -> None:
    environment = dict(os.environ)
    environment.update(
        {
            "COSMOTECH_AUDIT_LOG": str(tmp_path / "stdio-audit.jsonl"),
            "COSMOTECH_ALLOWED_ROOTS": str(PROJECT_ROOT),
            "FASTMCP_CHECK_FOR_UPDATES": "off",
            "AWS_EC2_METADATA_DISABLED": "true",
        }
    )
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "cosmotech_mcp", "serve", "--transport", "stdio"],
        env=environment,
        cwd=str(PROJECT_ROOT),
    )
    async with Client(transport, timeout=20) as client:
        tools = await client.list_tools()
        result = await client.call_tool("linux_system_info", {})
    assert len(tools) == 25
    assert not result.is_error
    assert (tmp_path / "stdio-audit.jsonl").is_file()


@pytest.mark.asyncio
async def test_terraform_validate_and_plan_on_local_fixture(tmp_path: Path) -> None:
    terraform = tmp_path / "terraform-fixture"
    terraform.mkdir()
    (terraform / "main.tf").write_text(
        'terraform { required_version = ">= 1.0" }\noutput "example" { value = "read-only" }\n',
        encoding="utf-8",
    )
    settings = Settings(
        project_root=tmp_path,
        allowed_roots=(tmp_path,),
        command_timeout_seconds=15,
        max_output_bytes=8192,
        audit_log=tmp_path / "audit.jsonl",
        http_host="127.0.0.1",
        http_port=8765,
        http_bearer_token=None,
        allow_non_loopback_http=False,
    )
    async with Client(create_server(settings=settings), timeout=30) as client:
        validate = await client.call_tool("terraform_validate", {"directory": str(terraform)})
        plan = await client.call_tool("terraform_plan", {"directory": str(terraform)})
    validate_payload = validate.structured_content
    plan_payload = plan.structured_content
    assert validate_payload["ok"] is True
    assert validate_payload["result"]["returnCode"] == 0
    assert plan_payload["ok"] is True
    assert plan_payload["result"]["returnCode"] in {0, 2}
