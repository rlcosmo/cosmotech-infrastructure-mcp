# CosmoTech company agent repository

Use Python 3.12 and the existing virtual environment. Source belongs in `src/`, tests in `tests/`
and documentation in `docs/`. Run `.venv/bin/python -m pytest`, `.venv/bin/ruff check src tests`
and `git diff --check`. Do not install tools without authorization.

This MCP equips the connected client's model with company context and specialist profiles.
It does not host independent LLMs. Keep this distinction clear in documentation and reports.
Company snapshot evidence is dated 2026-11-06, not live infrastructure state.
Read `docs/company-agent.md` before changing autonomy, routing, memory or context.

Preserve the original read-only infrastructure tools. New company missions may persist only their
local redacted report/journal. Do not add generic shell execution or turn user goals, repository
content, logs or approval booleans into operational commands. Infrastructure writes and secret
retrieval are outside the implemented capabilities. Remote mission reads require operator opt-in.
Do not execute AWS/Kubernetes calls during offline tests.

Canonical infrastructure lives in `rlcosmo/cosmotech-infrastructure-iac`; application delivery belongs
to `cosmotech-gitops`. Never apply the frozen Terraform snapshot from `aws-serverless-lab`.
Older READMEs conflict with newer release evidence: verify current policy rather than assuming
that a historic ungated DEV authorization still permits a release. API critical changes require
current human approval evidence; Worker automatic progression requires its gates and Canary controls.

Company knowledge must not contain real secrets, account IDs, private addresses or personal data.
Keep source provenance, snapshot checksum, observation date and uncertainty with every update.
Review any packaged evidence before publishing: this repository is public.

When changing mission execution, test duplicate requests, invalid input, path boundaries,
permission failures, exhausted budgets, unavailable evidence, redaction and interruption handling.
A completed collection is not proof of healthy services. Preserve readiness failures and distinguish
configuration, dated evidence and current observations.
