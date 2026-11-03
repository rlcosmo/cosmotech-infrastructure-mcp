# CosmoTech Infrastructure MCP

Provider-neutral, read-only infrastructure inspection over the Model Context Protocol. The MVP uses FastMCP, Python 3.12+, boto3, and existing command-line clients. It supports local STDIO and authenticated Streamable HTTP.

## Status

Implemented in this MVP: AWS inventory, Kubernetes CLI inspection, Terraform validate/plan, Linux host facts, Docker metadata inspection, Git status, health checks for Kubernetes workloads, JSON audit, redaction, command allowlisting, timeout, and output limits.

Azure, GCP, OpenShift-specific APIs, provider-native policy engines, OAuth for hosted clients, and write/automation operations are planned, not implemented. Kubernetes tools use the active `kubectl` context and therefore can work with EKS, AKS, GKE, or OpenShift when their CLI credentials/context are available. The server does not install or configure those credentials.

## Install locally

```bash
cd /opt/aws-serverless-lab/cosmotech-infrastructure-mcp
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
```

The AWS tools use boto3's standard credential provider chain. Configure AWS IAM Identity Center, a profile, or role credentials outside Git; do not put keys in `.env`. The optional CLIs `kubectl`, `helm`, `terraform`, `docker`, and `git` must be installed separately for their tools to work.

Set `COSMOTECH_ALLOWED_ROOTS` to a path-separated list of directories the CLI tools may inspect. The server always allows its own project directory, then adds the configured paths. Absolute paths are accepted; relative paths resolve from the MCP project directory. On Linux, separate entries with `:`. Paths outside configured roots are rejected.

For the `/opt/aws-serverless-lab` checkout, configure `.env` as follows to allow this MCP project and the Terraform project while keeping access scoped:

```dotenv
COSMOTECH_ALLOWED_ROOTS=/opt/aws-serverless-lab/cosmotech-infrastructure-mcp:/opt/aws-serverless-lab/terraform
```

## Start the server

STDIO is the local-client default:

```bash
.venv/bin/python -m cosmotech_mcp serve --transport stdio
```

Authenticated Streamable HTTP uses `/mcp` and binds to loopback by default:

```bash
export MCP_HTTP_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
.venv/bin/python -m cosmotech_mcp serve --transport http
```

HTTP startup fails without `MCP_HTTP_BEARER_TOKEN`. The default host is `127.0.0.1`; keep it there when running under WSL. Non-loopback binding additionally requires `MCP_HTTP_ALLOW_NON_LOOPBACK=true` and a token. Do not expose the WSL listener to a public network. For an enterprise remote deployment, put it behind TLS and an identity provider or a protected gateway, and review the client authentication flow first.

## Safety model

- No arbitrary shell tool exists. Command execution is restricted to `kubectl`, `helm`, `terraform`, `docker`, and `git` with argument arrays and `shell=False`.
- `kubectl` resource kinds are allowlisted; Secret objects cannot be fetched. Logs and CLI output are redacted and byte-limited.
- Terraform is limited to `validate` and a `plan` with refresh and state locking disabled; it does not save a plan, initialize providers, apply, or destroy. Terraform `external` data sources are rejected by the plan tool.
- AWS uses read-only boto3 APIs. IAM inventory lists role and policy names; it never queries passwords, secret values, access keys, or key material.
- Every tool call writes a JSONL audit event with redacted arguments and outcome. The default file is `~/.local/state/cosmotech-infrastructure-mcp/audit.jsonl`, created with restrictive permissions.
- Command timeout defaults to 15 seconds and output to 64 KiB. Both limits are configurable within hard maximums.

These controls reduce risk but do not replace cloud IAM least privilege, host isolation, TLS, network controls, or review of the configuration passed to the server.

## Client examples

See [docs/clients.md](docs/clients.md) for Codex CLI, ChatGPT, Claude Code, and generic MCP configuration. The local Codex STDIO example is:

```toml
[mcp_servers.cosmotech_infrastructure]
command = "/opt/aws-serverless-lab/cosmotech-infrastructure-mcp/.venv/bin/python"
args = ["-m", "cosmotech_mcp", "serve", "--transport", "stdio"]
env_vars = ["AWS_PROFILE", "AWS_REGION", "KUBECONFIG", "COSMOTECH_ALLOWED_ROOTS"]
startup_timeout_sec = 20
tool_timeout_sec = 60
```

## Development checks

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m compileall -q src tests
```

The integration smoke test starts the actual STDIO server process and performs MCP initialization and tool discovery without calling AWS or changing infrastructure.

## Container

The Docker image includes the Python server only. Mount provider configuration read-only and install only the CLIs needed for your environment. Do not mount the Docker socket unless a separate security review approves that access. Example:

```bash
docker build -t cosmotech-infrastructure-mcp:local .
docker run --rm -p 127.0.0.1:8765:8765 \
  -e MCP_HTTP_BEARER_TOKEN="$MCP_HTTP_BEARER_TOKEN" \
  cosmotech-infrastructure-mcp:local
```

The server listens on the container interfaces; this example publishes the port only on host loopback. The image entrypoint passes `--transport http`. AWS credentials and kubeconfig need explicit read-only mounts or workload identity. Never bake them into the image.

## License

MIT. See [LICENSE](LICENSE).
