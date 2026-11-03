from __future__ import annotations

from dataclasses import dataclass

READ_ONLY_COMMANDS = frozenset({"kubectl", "helm", "terraform", "docker", "git"})
FORBIDDEN_COMMANDS = frozenset(
    {"sh", "bash", "zsh", "fish", "cmd", "powershell", "apply", "destroy", "exec"}
)
READ_ONLY_KUBECTL_RESOURCES = frozenset(
    {
        "cluster-info",
        "deployments",
        "endpoints",
        "events",
        "gateways",
        "ingresses",
        "namespaces",
        "nodes",
        "persistentvolumeclaims",
        "persistentvolumes",
        "pods",
        "services",
        "statefulsets",
        "storageclasses",
        "virtualservices",
        "destinationrules",
        "peerauthentications",
        "authorizationpolicies",
    }
)


class PolicyDenied(ValueError):
    """Raised when an operation is outside the read-only policy."""


@dataclass(frozen=True, slots=True)
class Policy:
    def require_command(self, command: str) -> None:
        if command in FORBIDDEN_COMMANDS or command not in READ_ONLY_COMMANDS:
            raise PolicyDenied(f"Command is not allowlisted: {command}")

    def require_kubectl_resource(self, resource: str) -> str:
        normalized = resource.lower()
        if normalized not in READ_ONLY_KUBECTL_RESOURCES:
            raise PolicyDenied("Kubernetes resource is not allowlisted")
        return normalized

    def require_read_only_terraform_action(self, action: str) -> None:
        if action not in {"validate", "plan"}:
            raise PolicyDenied("Only terraform validate and plan are available")
