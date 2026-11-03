from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from cosmotech_mcp.core.audit import JsonAuditLog
from cosmotech_mcp.core.commands import CommandResult, run_read_only_command
from cosmotech_mcp.core.policy import Policy
from cosmotech_mcp.core.redaction import json_safe, redact_text
from cosmotech_mcp.core.settings import Settings, ensure_allowed_path
from cosmotech_mcp.providers import aws

LOGGER = logging.getLogger("cosmotech_mcp")
NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,253}$")
SAFE_OUTPUTS = frozenset({"json", "yaml", "wide", "name"})
READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def _safe_name(value: str, label: str = "name") -> str:
    if not NAME_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid Kubernetes {label}")
    return value


def _command_result(result: CommandResult) -> dict[str, Any]:
    return {
        "command": result.command,
        "returnCode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "timedOut": result.timed_out,
        "truncated": result.truncated,
    }


def _fit_result(value: Any, limit: int) -> Any:
    safe_value = json_safe(value)
    encoded = json.dumps(safe_value, separators=(",", ":"), ensure_ascii=True)
    encoded_bytes = encoded.encode("utf-8")
    if len(encoded_bytes) <= limit:
        return safe_value
    preview = encoded_bytes[: max(0, limit - 100)].decode("utf-8", errors="ignore")
    return {"truncated": True, "preview": preview, "maxOutputBytes": limit}


def _guarded(
    name: str,
    arguments: dict[str, Any],
    operation: Callable[[], Any],
    *,
    audit: JsonAuditLog,
    settings: Settings,
) -> Any:
    try:
        audit.record(tool=name, arguments=arguments, outcome="started")
    except OSError:
        LOGGER.exception("Audit log unavailable; refusing tool execution")
        return {"ok": False, "error": "audit_unavailable"}
    try:
        result = _fit_result(operation(), settings.max_output_bytes)
        audit.record(tool=name, arguments=arguments, outcome="success")
        return {"ok": True, "result": result}
    except Exception as exc:
        try:
            audit.record(
                tool=name,
                arguments=arguments,
                outcome="error",
                error_type=type(exc).__name__,
            )
        except OSError:
            LOGGER.exception("Could not append tool failure to audit log")
        LOGGER.warning("Tool %s failed (%s)", name, type(exc).__name__)
        message = redact_text(str(exc))[:500]
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": message,
        }


def create_server(*, settings: Settings | None = None, auth_token: str | None = None) -> FastMCP:
    active_settings = settings or Settings.from_env()
    policy = Policy()
    audit = JsonAuditLog(active_settings.audit_log)
    auth = None
    if auth_token:
        auth = StaticTokenVerifier(
            tokens={
                auth_token: {
                    "client_id": "cosmotech-infrastructure-client",
                    "scopes": ["infrastructure:read"],
                }
            },
            required_scopes=["infrastructure:read"],
        )
    mcp = FastMCP(name="CosmoTech Infrastructure MCP", auth=auth)

    def register(tool_name: str, arguments: dict[str, Any], operation: Callable[[], Any]) -> Any:
        return _guarded(
            tool_name,
            arguments,
            operation,
            audit=audit,
            settings=active_settings,
        )

    def cli(command: str, args: list[str], cwd: str | Path) -> dict[str, Any]:
        return _command_result(
            run_read_only_command(
                command,
                args,
                cwd=cwd,
                settings=active_settings,
                policy=policy,
            )
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def aws_get_identity() -> dict[str, Any]:
        """Read the active AWS caller identity. Never reads access-key material."""
        return register("aws_get_identity", {}, aws.get_identity)

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def aws_inventory(region: str | None = None) -> dict[str, Any]:
        """Read an AWS inventory summary for EKS, ECR, EC2, SQS, DynamoDB, and IAM."""
        return register("aws_inventory", {"region": region}, lambda: aws.inventory(region))

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def aws_eks_inventory(region: str | None = None) -> dict[str, Any]:
        """Read EKS cluster versions, endpoint access, status, and node group names."""
        return register("aws_eks_inventory", {"region": region}, lambda: aws.eks_inventory(region))

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def aws_ecr_inventory(region: str | None = None) -> dict[str, Any]:
        """Read ECR repository names, scanning, mutability, and encryption settings."""
        return register("aws_ecr_inventory", {"region": region}, lambda: aws.ecr_inventory(region))

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def aws_ec2_inventory(region: str | None = None) -> dict[str, Any]:
        """Read EC2 instance state, type, placement, addresses, and tags."""
        return register("aws_ec2_inventory", {"region": region}, lambda: aws.ec2_inventory(region))

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def aws_sqs_inventory(region: str | None = None) -> dict[str, Any]:
        """Read SQS queue attributes, redrive configuration, encryption, and approximate backlog."""
        return register("aws_sqs_inventory", {"region": region}, lambda: aws.sqs_inventory(region))

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def aws_dynamodb_inventory(region: str | None = None) -> dict[str, Any]:
        """Read DynamoDB table metadata, backup status, TTL, and stream state; never reads items."""
        return register(
            "aws_dynamodb_inventory", {"region": region}, lambda: aws.dynamodb_inventory(region)
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def aws_iam_inventory() -> dict[str, Any]:
        """Read IAM role and policy names only; never queries passwords or access keys."""
        return register("aws_iam_inventory", {}, aws.iam_inventory)

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def eks_health() -> dict[str, Any]:
        """Read Kubernetes API reachability, node readiness, and pod phase summaries."""

        def operation() -> dict[str, Any]:
            node_template = (
                "jsonpath={range .items[*]}{.metadata.name}"
                '{"\\t"}{.status.conditions[?(@.type=="Ready")].status}'
                '{"\\n"}{end}'
            )
            pod_template = 'jsonpath={range .items[*]}{.status.phase}{"\\n"}{end}'
            context = cli("kubectl", ["config", "current-context"], active_settings.project_root)
            nodes = cli(
                "kubectl",
                ["get", "nodes", "-o", node_template],
                active_settings.project_root,
            )
            pods = cli(
                "kubectl",
                ["get", "pods", "-A", "-o", pod_template],
                active_settings.project_root,
            )
            if context["returnCode"] != 0 or nodes["returnCode"] != 0 or pods["returnCode"] != 0:
                return {"context": context, "nodes": nodes, "pods": pods, "healthy": False}
            node_lines = [line.split("\t", 1) for line in nodes["stdout"].splitlines() if line]
            pod_phases = [line.strip() for line in pods["stdout"].splitlines() if line.strip()]
            ready_nodes = sum(1 for line in node_lines if len(line) > 1 and line[1] == "True")
            phases: dict[str, int] = {}
            for phase in pod_phases:
                phases[phase] = phases.get(phase, 0) + 1
            return {
                "context": context["stdout"].strip(),
                "nodes": {"ready": ready_nodes, "total": len(node_lines)},
                "podsByPhase": phases,
                "healthy": bool(node_lines) and ready_nodes == len(node_lines),
            }

        return register("eks_health", {}, operation)

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def kubectl_get(
        resource: str,
        name: str = "",
        namespace: str = "",
        output: str = "wide",
        all_namespaces: bool = False,
    ) -> dict[str, Any]:
        """Run allowlisted kubectl get for safe resource kinds; secrets are forbidden."""

        def operation() -> dict[str, Any]:
            resource_name = policy.require_kubectl_resource(resource)
            if output not in SAFE_OUTPUTS:
                raise ValueError("Output format is not allowlisted")
            args = ["get", resource_name]
            if name:
                args.append(_safe_name(name))
            if all_namespaces:
                args.append("-A")
            elif namespace:
                args.extend(["-n", _safe_name(namespace, "namespace")])
            args.extend(["-o", output])
            return cli("kubectl", args, active_settings.project_root)

        return register(
            "kubectl_get",
            {
                "resource": resource,
                "name": name,
                "namespace": namespace,
                "output": output,
                "all_namespaces": all_namespaces,
            },
            operation,
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def kubectl_logs(
        pod: str,
        namespace: str,
        container: str = "",
        tail_lines: int = 200,
        previous: bool = False,
    ) -> dict[str, Any]:
        """Read recent logs from a pod; output is redacted and size-limited."""

        def operation() -> dict[str, Any]:
            if not 1 <= tail_lines <= 1000:
                raise ValueError("tail_lines must be between 1 and 1000")
            args = ["logs", _safe_name(pod, "pod"), "-n", _safe_name(namespace, "namespace")]
            if container:
                args.extend(["-c", _safe_name(container, "container")])
            args.extend(["--tail", str(tail_lines), "--timestamps"])
            if previous:
                args.append("--previous")
            return cli("kubectl", args, active_settings.project_root)

        return register(
            "kubectl_logs",
            {
                "pod": pod,
                "namespace": namespace,
                "container": container,
                "tail_lines": tail_lines,
                "previous": previous,
            },
            operation,
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def kubectl_describe(resource: str, name: str, namespace: str = "") -> dict[str, Any]:
        """Read kubectl describe for an allowlisted resource; secret resources are forbidden."""

        def operation() -> dict[str, Any]:
            resource_name = policy.require_kubectl_resource(resource)
            args = ["describe", f"{resource_name}/{_safe_name(name)}"]
            if namespace:
                args.extend(["-n", _safe_name(namespace, "namespace")])
            return cli("kubectl", args, active_settings.project_root)

        return register(
            "kubectl_describe",
            {"resource": resource, "name": name, "namespace": namespace},
            operation,
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def helm_inventory(namespace: str = "") -> dict[str, Any]:
        """Read Helm release names, namespaces, charts, and statuses."""
        args = ["list", "-o", "json"]
        if namespace:
            args.extend(["-n", _safe_name(namespace, "namespace")])
        else:
            args.append("-A")
        return register(
            "helm_inventory",
            {"namespace": namespace},
            lambda: cli("helm", args, active_settings.project_root),
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def terraform_validate(directory: str) -> dict[str, Any]:
        """Run read-only terraform validate -json without init, apply, or destroy."""

        def operation() -> dict[str, Any]:
            root = ensure_allowed_path(directory, active_settings)
            policy.require_read_only_terraform_action("validate")
            return cli("terraform", [f"-chdir={root}", "validate", "-json"], root)

        return register("terraform_validate", {"directory": directory}, operation)

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def terraform_plan(directory: str) -> dict[str, Any]:
        """Run a no-refresh Terraform plan; does not save a plan or apply changes."""

        def operation() -> dict[str, Any]:
            root = ensure_allowed_path(directory, active_settings)
            policy.require_read_only_terraform_action("plan")
            for config_path in root.rglob("*.tf"):
                if ".terraform" in config_path.parts:
                    continue
                content = config_path.read_text(encoding="utf-8")
                if re.search(r'data\s+"external"', content):
                    raise ValueError(
                        "Terraform external data sources are blocked by read-only policy"
                    )
            return cli(
                "terraform",
                [
                    f"-chdir={root}",
                    "plan",
                    "-refresh=false",
                    "-lock=false",
                    "-input=false",
                    "-no-color",
                    "-detailed-exitcode",
                ],
                root,
            )

        return register("terraform_plan", {"directory": directory}, operation)

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def linux_system_info() -> dict[str, Any]:
        """Read basic Linux host, CPU, memory, and disk information without shelling out."""

        def operation() -> dict[str, Any]:
            memory_total = None
            memory_available = None
            meminfo = Path("/proc/meminfo")
            if meminfo.is_file():
                values = {}
                for line in meminfo.read_text(encoding="utf-8").splitlines():
                    key, _, value = line.partition(":")
                    if key in {"MemTotal", "MemAvailable"}:
                        values[key] = value.strip()
                memory_total = values.get("MemTotal")
                memory_available = values.get("MemAvailable")
            disk = shutil.disk_usage("/")
            return {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "cpuCount": os.cpu_count(),
                "memoryTotal": memory_total,
                "memoryAvailable": memory_available,
                "rootDiskBytes": {"total": disk.total, "used": disk.used, "free": disk.free},
            }

        return register("linux_system_info", {}, operation)

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def docker_inspect(target: str) -> dict[str, Any]:
        """Read safe Docker object metadata; environment variables and secrets are omitted."""

        def invalid_name() -> Any:
            raise ValueError("Invalid Docker object name")

        if not NAME_PATTERN.fullmatch(target):
            return register("docker_inspect", {"target": target}, invalid_name)
        args = [
            "inspect",
            "--format",
            "{{.Name}} {{.State.Status}} {{.Config.User}} {{.HostConfig.Privileged}}",
            target,
        ]
        return register(
            "docker_inspect",
            {"target": target},
            lambda: cli("docker", args, active_settings.project_root),
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def git_status(directory: str) -> dict[str, Any]:
        """Read git branch and worktree status without changing the repository."""

        def operation() -> dict[str, Any]:
            root = ensure_allowed_path(directory, active_settings)
            return cli("git", ["status", "--short", "--branch", "--untracked-files=normal"], root)

        return register("git_status", {"directory": directory}, operation)

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    def observability_health() -> dict[str, Any]:
        """Check Kubernetes pod readiness for Prometheus, Grafana, Loki, Tempo, and OTel."""

        def operation() -> dict[str, Any]:
            pod_template = (
                'jsonpath={range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}'
                '{"\\t"}{.status.phase}{"\\t"}'
                '{range .status.containerStatuses[*]}{.ready}{","}{end}{"\\n"}{end}'
            )
            response = cli(
                "kubectl",
                ["get", "pods", "-A", "-o", pod_template],
                active_settings.project_root,
            )
            if response["returnCode"] != 0:
                return {"healthy": False, "query": response}
            items = []
            for line in response["stdout"].splitlines():
                fields = line.split("\t")
                if len(fields) >= 4:
                    items.append(
                        {
                            "metadata": {"namespace": fields[0], "name": fields[1]},
                            "status": {
                                "phase": fields[2],
                                "containerStatuses": [
                                    {"ready": value.lower() == "true"}
                                    for value in fields[3].split(",")
                                    if value
                                ],
                            },
                        }
                    )
            matchers = {
                "prometheus": ("prometheus", "prometheus"),
                "grafana": ("grafana", "grafana"),
                "loki": ("loki", "loki"),
                "tempo": ("tempo", "tempo"),
                "opentelemetry_collector": ("opentelemetry-collector", "opentelemetry-collector"),
            }
            checks = {}
            for component, (namespace_hint, name_hint) in matchers.items():
                matches = [
                    item
                    for item in items
                    if namespace_hint in item.get("metadata", {}).get("namespace", "").lower()
                    or name_hint in item.get("metadata", {}).get("name", "").lower()
                ]
                pods = []
                for item in matches:
                    status = item.get("status", {})
                    container_statuses = status.get("containerStatuses", [])
                    ready_count = sum(
                        1 for container in container_statuses if container.get("ready")
                    )
                    pods.append(
                        {
                            "namespace": item.get("metadata", {}).get("namespace"),
                            "name": item.get("metadata", {}).get("name"),
                            "phase": status.get("phase", "Unknown"),
                            "readyContainers": ready_count,
                            "totalContainers": len(container_statuses),
                        }
                    )
                checks[component] = {
                    "found": bool(matches),
                    "healthy": bool(matches)
                    and all(
                        pod["phase"] == "Running"
                        and pod["readyContainers"] == pod["totalContainers"]
                        for pod in pods
                    ),
                    "pods": pods,
                }
            return {
                "components": checks,
                "healthy": all(item["healthy"] for item in checks.values()),
            }

        return register("observability_health", {}, operation)

    return mcp
