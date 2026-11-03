# Security model

CosmoTech Infrastructure MCP is intended for read-only infrastructure inspection. Review the code and the exact client configuration before granting it access to sensitive environments. MCP tool output is visible to the connected AI client and may be processed under that client's data handling rules.

## Tool and command permissions

- AWS tools call boto3 read APIs only. IAM inventory reads role/policy names and metadata; DynamoDB inventory never reads table items.
- Subprocess execution permits only `kubectl`, `helm`, `terraform`, `docker`, and `git`. It uses an argument array with `shell=False`; shell programs and arbitrary commands are denied.
- Kubernetes resource operations use an allowlist: `cluster-info`, `deployments`, `endpoints`, `events`, `gateways`, `ingresses`, `namespaces`, `nodes`, `persistentvolumeclaims`, `persistentvolumes`, `pods`, `services`, `statefulsets`, `storageclasses`, `virtualservices`, `destinationrules`, `peerauthentications`, and `authorizationpolicies`. Kubernetes Secret resources cannot be fetched. Logs and descriptions can still include sensitive application data; use narrow RBAC and avoid querying sensitive namespaces.
- Terraform exposes only `validate` and `plan`. Validate does not initialize. Plan disables refresh and state locking, does not save a plan, and blocks Terraform `external` data sources. It can still evaluate provider/data-source code. Use a suitable local backend/state and test workspace, and inspect the configuration before planning.
- Docker only inspects selected metadata; environment variables are omitted. Git runs `status` only.

There are no write, apply, destroy, Kubernetes mutation, shell, or arbitrary file-reading tools.

## Filesystem boundary

The project directory is always allowed. `COSMOTECH_ALLOWED_ROOTS` adds explicit directories. Terraform and Git tools require an existing directory within those roots. Keep this list as narrow as practical. The setting limits command working directories and selected target directories; the operating-system user and provider credentials still determine what the process can access.

## Credential handling and redaction

- Use AWS IAM Identity Center, profiles, or short-lived role credentials. Keep credentials outside the repository and avoid secrets in `.env` where the process environment or a secret manager can provide them.
- `.env` is ignored by Git. Keep `.env.example` limited to blank or non-secret defaults.
- `KUBECONFIG` points to an external file; do not copy kubeconfig credentials into client config.
- Returned structured data and subprocess text pass through heuristic redaction for common key names, AWS access-key formats, bearer values, and private-key blocks. Redaction is best effort; it cannot identify every secret format or prevent the AI client from seeing unredacted data that does not match its patterns.
- The audit log stores tool names, redacted arguments, timestamps, outcomes, and error types, but not tool results. It is created with restrictive permissions. Protect it as operational metadata and configure its retention according to local policy.

## Runtime limits and HTTP exposure

CLI calls default to a 15-second timeout and a combined 64 KiB output cap. Configuration permits at most 300 seconds and 1 MiB. AWS SDK calls use bounded connect/read timeouts and standard retries. Each AWS inventory section is capped at 200 resources.

STDIO is local to the client process and inherits that process's credentials and permissions. HTTP uses Streamable HTTP at `/mcp`, requires `MCP_HTTP_BEARER_TOKEN`, and defaults to loopback. The server does not terminate TLS. To accept non-loopback connections, set `MCP_HTTP_ALLOW_NON_LOOPBACK=true` and configure a token; put the service behind a TLS terminator and network access controls.

The bearer token is static shared-secret authentication. It does not provide per-user identity, OAuth authorization, or user-specific scopes. It is not a replacement for OAuth on a public multi-user service. Do not expose this HTTP server directly to the public internet. Store the token in a secret manager or a permission-restricted local file, rotate it by changing the secret and restarting the server, and never commit it or include it in logs.

For container use, the image binds on its container interface and enables non-loopback HTTP because container networking requires it. The example publishes only to host loopback. Access to a Docker daemon/socket is highly privileged and can effectively grant host control; do not mount the socket or provider credentials unless required and separately reviewed.
