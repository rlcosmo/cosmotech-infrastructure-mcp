# Configuration

The server reads environment variables from the process and from `.env` at the project root. Process environment values take precedence because dotenv loading does not override existing values. Copy `.env.example` to `.env`; the example file contains no credentials. `.env` is ignored by Git.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `AWS_PROFILE` | boto3 default credential chain | Optional AWS named profile. Use an IAM Identity Center or role-based profile where possible. |
| `AWS_REGION` | boto3/profile region | Default AWS region. Individual regional inventory tools also accept a `region` argument. |
| `KUBECONFIG` | kubectl default (`~/.kube/config`) | Optional path to the kubeconfig used by `kubectl`. Set in the environment inherited by the server or the client configuration. |
| `COSMOTECH_ALLOWED_ROOTS` | Empty; only the project directory | Additional directories allowed as subprocess working directories and as targets to `terraform_validate`, `terraform_plan`, and `git_status`. Separate entries with the platform path separator (`:` on Linux/macOS, `;` on Windows). |
| `MCP_HTTP_BEARER_TOKEN` | Unset | Required for HTTP transport. Static bearer token used by the server's token verifier. |
| `MCP_HTTP_HOST` | `127.0.0.1` | HTTP bind address. Non-loopback addresses require the opt-in below and a token. |
| `MCP_HTTP_PORT` | `8765` | HTTP listening port. |
| `MCP_HTTP_ALLOW_NON_LOOPBACK` | `false` | Must be `true` to bind HTTP outside loopback. This only enables binding; it does not provide TLS. |
| `COSMOTECH_COMMAND_TIMEOUT_SECONDS` | `15` | Timeout for allowlisted CLI calls; accepted range is 1–300 seconds. |
| `COSMOTECH_MAX_OUTPUT_BYTES` | `65536` | Combined subprocess and returned tool output cap; accepted range is 1–1,048,576 bytes. |
| `COSMOTECH_AUDIT_LOG` | `~/.local/state/cosmotech-infrastructure-mcp/audit.jsonl` | Optional audit file path. The file is created with mode `0600`, and parent directories with restrictive permissions. |
| `FASTMCP_CHECK_FOR_UPDATES` | FastMCP default | Set to `off` in the example environment to disable FastMCP update checks. |

`COSMOTECH_ENV_FILE` is also supported by the code as an optional path to the dotenv file. It defaults to the project-root `.env`; it is not required for normal use.

## Restrict paths

The server always allows the directory containing the installed project. Add only the infrastructure directories that the MCP tools need to inspect. Use absolute paths for clarity:

```dotenv
COSMOTECH_ALLOWED_ROOTS=/home/alex/work/terraform:/home/alex/work/service-repo
```

Relative entries resolve from the project directory. The target passed to `terraform_validate`, `terraform_plan`, or `git_status` must exist, be a directory, and be inside one of the configured roots. This setting constrains process working directories and those tool targets; it does not change cloud IAM or Kubernetes RBAC permissions.

## AWS credentials and permissions

The AWS provider uses boto3's normal credential chain. The AWS CLI is convenient but not required by the server. A safe local setup is to configure IAM Identity Center with the AWS CLI, sign in, then set a profile name in `.env`:

```bash
aws configure sso --profile infra-readonly
aws sso login --profile infra-readonly
```

```dotenv
AWS_PROFILE=infra-readonly
AWS_REGION=us-east-1
```

Use short-lived role credentials and a read-only IAM policy. Do not put access keys, session tokens, or AWS config files in the repository or container image. The server requires these read actions for the corresponding tools:

| Tool/service | AWS API actions |
| --- | --- |
| Identity | `sts:GetCallerIdentity` |
| EKS inventory | `eks:ListClusters`, `eks:DescribeCluster`, `eks:ListNodegroups` |
| ECR inventory | `ecr:DescribeRepositories` |
| EC2 inventory | `ec2:DescribeInstances` |
| SQS inventory | `sqs:ListQueues`, `sqs:GetQueueAttributes` |
| DynamoDB inventory | `dynamodb:ListTables`, `dynamodb:DescribeTable`, `dynamodb:DescribeContinuousBackups`, `dynamodb:DescribeTimeToLive` |
| IAM inventory | `iam:ListRoles`, `iam:ListAttachedRolePolicies`, `iam:ListRolePolicies` |

Scope resources where the AWS service supports resource-level permissions; list/describe APIs often require `Resource: "*"`. IAM inventory returns role and policy names/metadata only. The combined `aws_inventory` tool attempts each service summary and reports per-service errors independently; give the role only the actions for services you want it to inventory.

## Kubernetes credentials

Install `kubectl` separately, configure a context using your organization-approved process, and verify it before connecting the MCP client:

```bash
kubectl config current-context
kubectl get nodes
```

If the kubeconfig is not at `~/.kube/config`, point `KUBECONFIG` to its path. Grant only Kubernetes RBAC `get` and `list` for the resource kinds you query; `kubectl_logs` additionally needs `get` on `pods/log`. `eks_health` and `observability_health` list nodes and pods across namespaces, so they need cluster-wide read access. An all-namespaces `helm_inventory` needs read access to Helm's stored release records across namespaces (often Secrets or ConfigMaps, depending on Helm configuration). Ordinary resource and pod-log queries can be scoped to a namespace. Never commit kubeconfig files or embed credentials in client JSON/TOML.

## Other provider CLIs

Install and configure `helm`, `terraform`, or `docker` only if you will use their tools. Their commands use the local process environment and configured CLI context. The server does not install CLIs, initialize Terraform, select Kubernetes contexts, or authenticate cloud providers for you.
