# MCP client configuration

All examples below use local STDIO, which avoids opening a network listener. The venv must exist at the configured absolute path. STDIO inherits selected environment variables from its parent process; configure AWS identity using the normal boto3 credential chain.

## Codex CLI

Add a local server using `~/.codex/config.toml`:

```toml
[mcp_servers.cosmotech_infrastructure]
command = "/opt/aws-serverless-lab/cosmotech-infrastructure-mcp/.venv/bin/python"
args = ["-m", "cosmotech_mcp", "serve", "--transport", "stdio"]
env_vars = ["AWS_PROFILE", "AWS_REGION", "KUBECONFIG", "COSMOTECH_ALLOWED_ROOTS"]
startup_timeout_sec = 20
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"
```

Check with `codex mcp list` and `/mcp` in the Codex TUI. The CLI can also add the STDIO command:

```bash
codex mcp add cosmotech_infrastructure -- \
  /opt/aws-serverless-lab/cosmotech-infrastructure-mcp/.venv/bin/python \
  -m cosmotech_mcp serve --transport stdio
```

Codex supports a bearer token sourced from an environment variable for HTTP MCP endpoints. The MVP's HTTP endpoint is bound to loopback by default; use the STDIO configuration from the same machine rather than exposing a WSL port. Remote Codex use requires a protected endpoint reachable from the client.

## ChatGPT MCP

ChatGPT clients that accept a custom remote MCP endpoint can use `https://<approved-host>/mcp` after the service is deployed with TLS and an authentication method supported by the selected ChatGPT integration. This repository does not deploy such an endpoint. The MVP's static bearer token is suitable for controlled local/internal testing, not a public ChatGPT connector; OAuth discovery and hosted-client registration remain pending.

For ChatGPT integrations that use OpenAI's Agents/Responses API, connect using its MCP transport configuration and provide the deployed `server_url` and appropriate authentication. The local WSL server is not reachable from OpenAI-hosted clients.

## Claude Code

Create `.mcp.json` in the project where Claude Code runs:

```json
{
  "mcpServers": {
    "cosmotech-infrastructure": {
      "type": "stdio",
      "command": "/opt/aws-serverless-lab/cosmotech-infrastructure-mcp/.venv/bin/python",
      "args": ["-m", "cosmotech_mcp", "serve", "--transport", "stdio"],
      "env": {
        "AWS_PROFILE": "your-read-only-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

Alternatively, use Claude Code's `claude mcp add` command with the same executable and arguments. Keep actual credentials out of `.mcp.json`.

## Other MCP clients

For a client with STDIO support, configure command and args as shown above. For Streamable HTTP clients, set the URL to `/mcp` and send `Authorization: Bearer <token>` from a secret manager or environment-variable reference. The server refuses HTTP startup without `MCP_HTTP_BEARER_TOKEN` and defaults to `127.0.0.1`.

## References

- OpenAI Codex MCP configuration: <https://learn.chatgpt.com/docs/extend/mcp>
- FastMCP transports and HTTP authentication: <https://gofastmcp.com/deployment/running-server> and <https://gofastmcp.com/servers/auth/token-verification>
- Claude Code MCP: <https://docs.anthropic.com/en/docs/claude-code/mcp>
