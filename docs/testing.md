# Validation record

Run date: 2026-11-03. Commands below were run from this project directory. Dependencies are installed in the project-local `.venv`; no AWS credentials or tokens were written to the repository.

## Local checks

| Check | Result |
| --- | --- |
| `pytest -q` | 14 passed |
| `ruff check .` | Passed |
| `ruff format --check .` | 24 files already formatted |
| `python -m compileall -q src tests` | Passed |
| `python -m pip check` | No broken requirements found |
| Markdown local links and JSON/TOML/shell examples | Passed |
| `docker build -t cosmotech-infrastructure-mcp:local .` | Passed |
| STDIO MCP handshake, tool discovery, and `linux_system_info` call | Passed; 19 tools discovered |
| Authenticated Streamable HTTP MCP handshake, discovery, and tool call | Passed; 19 tools discovered |
| HTTP startup without token | Refused with exit code 2 |
| HTTP request without bearer token | Rejected with 401 |
| Docker container HTTP MCP smoke test | Passed; 19 tools discovered and a tool call succeeded |
| `docker_inspect` against disposable local smoke-test container | Passed; exit code 0 |

## Read-only environment checks

- AWS `aws_get_identity` succeeded. `aws_inventory` returned successful status for EKS, ECR, EC2, SQS, DynamoDB, and IAM. Only summaries were inspected; no credential material was requested or printed.
- Kubernetes namespace listing, `eks_health`, and `observability_health` succeeded against the active local context. `helm_inventory` found 7 releases. This confirms the current EKS context only; AKS, GKE, and OpenShift were not separately tested.
- `terraform_validate` against the existing development root returned exit code 0. `terraform_plan` was exercised only on a temporary local output-only fixture without providers or managed resources; detailed exit code 2 was expected because that fixture had an output change. No plan was run against AWS infrastructure.
- All cloud calls were read-only. No apply/destroy, resource creation, or infrastructure configuration change was made.

## Not validated / pending

Azure and GCP native inventory, OpenShift-specific APIs, hosted-client OAuth, and live Prometheus/Grafana/Loki/Tempo/OTel service endpoints were not tested. The observability tool reports Kubernetes pod readiness for those workloads when present; it does not query each product's HTTP API. Kubernetes, Helm, Terraform, Docker, and Git tools require their respective CLI binaries and a usable local context. The Docker image does not bundle those CLIs.

## Version 0.2 local validation

Company routing, source containment/redaction, duplicate claims/replay, budget and step limits, remote opt-in, command failures, missing evidence, private journal and MCP resources/prompts are covered by offline tests. Existing AWS tests use stubs; no live AWS, Kubernetes, model invocation or deployment validation was performed for this update. The 19-tool records above describe the historical 0.1 tests.

Validation on 2026-11-06: **43 tests passed**, Ruff passed and `git diff --check` passed. A local MCP client discovered 25 tools, read the packaged architecture resource and completed a Worker/observability mission against existing local checkouts (two document evidence records, remote access disabled). A targeted scan of six knowledge/documentation files found no AWS access-key patterns, GitHub tokens, account IDs, private-IP patterns or private-key blocks. This is heuristic scanning, not a comprehensive secret-audit certification. No tools were installed; wheel build was not run because hatchling is not installed in the existing runtime environment.
