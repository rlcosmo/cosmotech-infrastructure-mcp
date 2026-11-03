# Tool examples

These examples use the registered MCP tool names and arguments. Ask the connected client to call the named tool with the JSON arguments shown. Replace paths and resource identifiers with values from your environment. All tools are read-only.

## 1. AWS caller identity

Tool: `aws_get_identity`; no arguments.

```json
{}
```

Returns the active AWS account, ARN, and user ID using STS. It does not return credentials.

## 2. AWS inventory

Tool: `aws_inventory`; optional `region`.

```json
{"region":"us-east-1"}
```

Summarizes EKS, ECR, EC2, SQS, DynamoDB, and IAM. Individual services can fail independently and return an error type in that section. To inspect one service directly, use `aws_eks_inventory`, `aws_ecr_inventory`, `aws_ec2_inventory`, `aws_sqs_inventory`, `aws_dynamodb_inventory` (each accepts optional `region`) or `aws_iam_inventory` (no arguments).

## 3. Kubernetes cluster health

Tool: `eks_health`; no arguments.

```json
{}
```

Uses the current `kubectl` context and reads node readiness and pod phase counts across namespaces. Despite the tool name, it can inspect any Kubernetes cluster selected by the active context; it does not call the EKS API.

## 4. Recent pod logs

Tool: `kubectl_logs`; required `pod` and `namespace`, optional `container`, `tail_lines` (1–1000, default 200), and `previous` (default `false`).

```json
{"pod":"orders-api-7c8b6d9f6c-abcde","namespace":"production","container":"api","tail_lines":100,"previous":false}
```

Output is redacted on a best-effort basis and limited in size. Logs can contain application/customer data; request only the minimum needed.

## 5. Terraform validation

Tool: `terraform_validate`; required existing directory `directory` within the allowed roots.

```json
{"directory":"/home/alex/work/terraform/environments/dev"}
```

Runs `terraform validate -json`. It does not run `terraform init`; prepare and initialize the working directory separately if Terraform requires it.

## 6. Terraform plan

Tool: `terraform_plan`; required existing directory `directory` within the allowed roots.

```json
{"directory":"/home/alex/work/terraform/environments/dev"}
```

Runs a plan with refresh and state locking disabled, input disabled, no saved plan, and detailed exit codes. It does not apply or destroy resources. Exit code 2 means Terraform found planned changes; inspect the returned output. The server blocks `external` data sources but a plan can still evaluate providers and other data sources.

## 7. Git worktree status

Tool: `git_status`; required existing directory `directory` within the allowed roots.

```json
{"directory":"/home/alex/work/service-repo"}
```

Returns branch and short worktree status. It does not change Git state.

## 8. Observability workload readiness

Tool: `observability_health`; no arguments.

```json
{}
```

Looks for pods matching Prometheus, Grafana, Loki, Tempo, and OpenTelemetry Collector names/namespaces, and reports pod phase and container readiness. It does not query Prometheus metrics, Grafana dashboards, or Loki/Tempo/OTel APIs. A missing component reports `found: false` and makes the aggregate health result false.

## Other available tools

| Tool | Arguments | What it reads |
| --- | --- | --- |
| `aws_get_identity` | None | Active AWS caller identity. |
| `aws_inventory` | `region` optional | Summary across supported AWS services. |
| `aws_eks_inventory` | `region` optional | EKS clusters, endpoint access, versions, and node groups. |
| `aws_ecr_inventory` | `region` optional | ECR repository settings. |
| `aws_ec2_inventory` | `region` optional | EC2 instance state, placement, addresses, and tags. |
| `aws_sqs_inventory` | `region` optional | Queue attributes, redrive/encryption settings, and approximate backlog. |
| `aws_dynamodb_inventory` | `region` optional | Table metadata, backups, TTL, and stream state; no items. |
| `aws_iam_inventory` | None | IAM role and policy names/metadata. |
| `eks_health` | None | Current Kubernetes context, node readiness, pod phases. |
| `kubectl_get` | `resource`, `name` optional, `namespace` optional, `output` optional (`json`, `yaml`, `wide`, `name`), `all_namespaces` optional | Allowlisted Kubernetes resource get. |
| `kubectl_logs` | `pod`, `namespace`, `container` optional, `tail_lines` optional, `previous` optional | Recent pod logs. |
| `kubectl_describe` | `resource`, `name`, `namespace` optional | Description of an allowlisted resource. |
| `helm_inventory` | `namespace` optional | Helm release names, namespaces, charts, statuses. |
| `terraform_validate` | `directory` | Terraform validation. |
| `terraform_plan` | `directory` | No-refresh Terraform plan. |
| `linux_system_info` | None | Basic Linux, CPU, memory, and root disk facts. |
| `docker_inspect` | `target` | Docker name, state, user, and privileged flag. |
| `git_status` | `directory` | Branch and worktree status. |
| `observability_health` | None | Readiness of selected observability pods. |

See [security](security.md) for permissions and [configuration](configuration.md) for required CLIs and credentials.
