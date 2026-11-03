# CosmoTech Infrastructure MCP

CosmoTech Infrastructure MCP is a Python Model Context Protocol (MCP) server for read-only inspection of AWS, Kubernetes, Terraform, Git, Linux host, Docker, and Kubernetes observability state. It exposes 19 tools over local STDIO or authenticated Streamable HTTP.

This is an early MVP. AWS and local CLI integrations are implemented; the Kubernetes features use the active local `kubectl` context. Azure and GCP native integrations, OpenShift-specific APIs, OAuth for hosted clients, and write or automation operations are not implemented.

## Features

- Read AWS caller identity and summaries for EKS, ECR, EC2, SQS, DynamoDB, and IAM.
- Inspect Kubernetes health, allowlisted resources, recent pod logs, resource descriptions, and Helm releases.
- Run Terraform validate and a no-refresh plan; no initialize, apply, destroy, or saved plan.
- Read Linux host facts, safe Docker metadata, Git status, and readiness of common observability pods.
- Apply an allowlist to subprocess commands, restrict filesystem working directories, redact likely secrets, and write JSONL audit events.

## Quick install

Requirements: Python 3.12 or newer and Git. The AWS CLI and provider CLIs are optional; install only the tools for the integrations you plan to use. See [installation](docs/installation.md) and [configuration](docs/configuration.md).

```bash
git clone https://github.com/rlcosmo/cosmotech-infrastructure-mcp.git
cd cosmotech-infrastructure-mcp

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

Start locally over STDIO:

```bash
.venv/bin/python -m cosmotech_mcp serve --transport stdio
```

Configure a client using the [client guide](docs/clients.md), then explore the [tool examples](docs/examples.md). For authenticated local HTTP, see [HTTP setup](docs/clients.md#openai-codex-cli-local-streamable-http).

## Documentation

- [Installation and prerequisites](docs/installation.md)
- [Configuration and provider credentials](docs/configuration.md)
- [Client setup: Codex, ChatGPT, Claude Code, Cursor](docs/clients.md)
- [Tool examples](docs/examples.md)
- [Security model](docs/security.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture and boundaries](docs/architecture.md)
- [Validation record](docs/testing.md)

## License

MIT. See [LICENSE](LICENSE).
