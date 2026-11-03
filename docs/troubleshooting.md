# Troubleshooting

## `Transport closed` or the client cannot discover tools

**Diagnose:** Confirm the server command is executable and run the STDIO command manually from the project directory. Check that the client points to `.venv/bin/python` and passes `-m cosmotech_mcp serve --transport stdio`. The server writes logs to stderr; stdout is reserved for MCP protocol traffic.

**Fix:** Activate the project virtual environment or use the absolute venv interpreter path, then run `pip install -e ".[dev]"`. Restart the client after changing its MCP configuration. For HTTP, verify the endpoint includes `/mcp`, the port is reachable from the client, and the client supports Streamable HTTP.

## Server does not start

**Diagnose:** Run `.venv/bin/python -m cosmotech_mcp serve --transport stdio` in a terminal and read the error. Check Python with `python --version`, verify the virtual environment, and confirm the selected `--transport` is `stdio` or `http`.

**Fix:** Recreate the environment with Python 3.12 or newer and reinstall the project dependencies. HTTP startup requires `MCP_HTTP_BEARER_TOKEN`. Binding a non-loopback address also requires `MCP_HTTP_ALLOW_NON_LOOPBACK=true`.

## AWS credentials not found or `NoCredentialsError`

**Diagnose:** Run `aws sts get-caller-identity --profile infra-readonly` (if AWS CLI is installed), or check that the same environment/profile is visible to the MCP process. For IAM Identity Center, check the profile and session expiration.

**Fix:** Sign in with `aws sso login --profile <profile>` and set `AWS_PROFILE` and `AWS_REGION` in the environment inherited by the client or in the project `.env`. Use role-based short-lived credentials; do not paste keys into client configuration.

## AWS metadata service (IMDS) unavailable

**Diagnose:** boto3 tried its instance metadata credential provider, but the process is not on an appropriately configured instance or cannot reach IMDS. This commonly happens in containers and local development.

**Fix:** Configure a local AWS profile, IAM Identity Center, environment-provided short-lived credentials, or workload identity appropriate to the runtime. The MCP does not configure IMDS or credentials. Do not weaken IMDS security settings just to make local use work.

## Directory rejected by `COSMOTECH_ALLOWED_ROOTS`

**Diagnose:** `terraform_validate`, `terraform_plan`, or `git_status` received a path that does not exist, is not a directory, or is outside the project and configured roots.

**Fix:** Add the narrow parent directory to `COSMOTECH_ALLOWED_ROOTS`, separated by `:` on Linux/macOS or `;` on Windows. Use an absolute path and restart the MCP process. Relative roots resolve from the project directory.

## kubeconfig or Kubernetes context errors

**Diagnose:** Run `kubectl config current-context` and `kubectl get nodes` using the same account and environment as the MCP server. Inspect whether `KUBECONFIG` points to the intended file and whether its credentials have expired.

**Fix:** Select/refresh the approved context using your platform's normal process; pass `KUBECONFIG` to the client process if it is not at `~/.kube/config`. Grant the read permissions needed for the query. The health and observability tools read across namespaces, so namespace-only RBAC can make them fail.

## `terraform` not found or validation fails

**Diagnose:** `terraform` is an optional external executable and must be in the MCP process's `PATH`. The tools do not run `terraform init`.

**Fix:** Install Terraform using your organization's approved method and ensure the MCP client process inherits its path. Initialize the working directory yourself where required, then call validate or plan. For a plan, use a suitable state/backend and remember that it disables refresh and locking.

## Python dependency installation or import failures

**Diagnose:** Confirm Python is 3.12+, the virtual environment is activated, and the client command points to that environment's interpreter. Check the install output for build-backend or network errors.

**Fix:** From the project root, run:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip check
```

If the client starts from another working directory, use an absolute interpreter path. The package is installed in editable mode by the documented setup; the client does not need to rely on its current directory to find the module.

## Audit log unavailable

**Diagnose:** Every tool call writes an audit event before execution. If that log cannot be created or appended, the tool returns `audit_unavailable` and does not execute.

**Fix:** Check the parent directory's ownership and available disk space, or set `COSMOTECH_AUDIT_LOG` to a protected writable path. Keep restrictive permissions because event arguments, although redacted, can include operational identifiers.
