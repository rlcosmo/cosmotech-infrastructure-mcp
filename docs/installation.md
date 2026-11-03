# Installation

## Prerequisites

Required for local installation:

- Python 3.12 or newer.
- Git, to clone the repository.
- A supported MCP client if you want to call the server through an AI tool.

Optional tools, needed only for the related integrations:

| Tool | Used by | Notes |
| --- | --- | --- |
| AWS CLI v2 | Convenient AWS IAM Identity Center/profile setup and diagnostics | The server calls AWS through boto3; AWS CLI is not required for AWS MCP tools. |
| `kubectl` | Kubernetes health, get, logs, describe, and observability checks | Requires an active context and working kubeconfig. |
| Helm CLI | `helm_inventory` | Uses the Helm configuration and credentials available to the server process. |
| Terraform CLI | `terraform_validate` and `terraform_plan` | The server does not initialize Terraform or install providers. |
| Docker CLI | `docker_inspect` | The server inspects metadata through the configured Docker CLI/daemon. |
| Docker Engine or compatible builder | Building/running the provided image | Not needed for local Python/STDIO use. The image does not bundle provider CLIs. |

Only Git, Python and the project dependencies are needed for the server itself. AWS credentials, Kubernetes access and the optional CLIs are needed only for the tools that use them.

## Clone and install

```bash
git clone https://github.com/rlcosmo/cosmotech-infrastructure-mcp.git
cd cosmotech-infrastructure-mcp

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

The `dev` extra in `pyproject.toml` installs pytest, pytest-asyncio, and Ruff. The base install includes boto3, FastMCP, and python-dotenv. The editable install makes the `cosmotech-mcp` command and `python -m cosmotech_mcp` available in the environment.

On systems where `python3` is not Python 3.12+, use the versioned executable, such as `python3.12 -m venv .venv`. The project does not declare support for older Python versions.

## Start the server

Start local STDIO for an MCP client:

```bash
.venv/bin/python -m cosmotech_mcp serve --transport stdio
```

STDIO is intended to be launched and managed by the MCP client. For a manual protocol check, run the test suite; its smoke test starts the process and performs initialization, tool discovery, and a local tool call.

HTTP setup is documented in [client configuration](clients.md#openai-codex-cli-local-streamable-http). Do not run the HTTP transport on a network interface without reviewing [security guidance](security.md).

## Build the container

Docker is optional. From the project root:

```bash
docker build -t cosmotech-infrastructure-mcp:local .
```

The image runs the HTTP transport as a non-root user and binds inside the container. It contains the Python server and its Python dependencies, not `aws`, `kubectl`, `helm`, `terraform`, `docker`, or `git` binaries. Consequently, only capabilities supported by the installed contents/configuration are available in the image. AWS access and a kubeconfig also require explicit secure credential configuration; credentials are not copied into the image.

## Development checks

With the `dev` extra installed:

```bash
python -m pytest
ruff check .
ruff format --check .
python -m compileall -q src tests
```

See [testing](testing.md) for the validation record and its scope.
