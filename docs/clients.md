# MCP clients

The server supports local MCP STDIO and authenticated Streamable HTTP. The repository tests exercise an actual STDIO MCP handshake, tool discovery, and a local tool call. They do not launch Codex CLI, ChatGPT, Claude Code, or Cursor. The configurations below are examples based on each client's documented MCP configuration; validate them in your installed client version.

For initial setup, use STDIO on the same machine. It avoids a network listener and lets the MCP client manage the server process. Use absolute paths in client configuration.

## OpenAI Codex CLI: STDIO

Add this to `~/.codex/config.toml`, replacing the path with the cloned project location:

```toml
[mcp_servers.cosmotech_infrastructure]
command = "/home/alex/src/cosmotech-infrastructure-mcp/.venv/bin/python"
args = ["-m", "cosmotech_mcp", "serve", "--transport", "stdio"]
env_vars = ["AWS_PROFILE", "AWS_REGION", "KUBECONFIG", "COSMOTECH_ALLOWED_ROOTS"]
startup_timeout_sec = 20
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"
```

The project `.env` is loaded by the server. `env_vars` allows Codex to pass selected variables from the shell that launched it; use the `.env` or the launching shell for the AWS profile, kubeconfig path, and allowed roots. Then restart Codex and check:

```bash
codex mcp list
```

You can also register STDIO using the CLI:

```bash
codex mcp add cosmotech_infrastructure -- \
  /home/alex/src/cosmotech-infrastructure-mcp/.venv/bin/python \
  -m cosmotech_mcp serve --transport stdio
```

## OpenAI Codex CLI: local Streamable HTTP

Create a high-entropy token in a permission-restricted file outside the repository, then export it to the shell that will run both the server and Codex. This example does not print the generated token:

```bash
install -d -m 700 "$HOME/.config/cosmotech-mcp"
umask 077
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' \
  > "$HOME/.config/cosmotech-mcp/http-token"
export MCP_HTTP_BEARER_TOKEN="$(cat "$HOME/.config/cosmotech-mcp/http-token")"
```

In one terminal, start the server:

```bash
cd /home/alex/src/cosmotech-infrastructure-mcp
.venv/bin/python -m cosmotech_mcp serve --transport http
```

The server listens at `http://127.0.0.1:8765/mcp` by default. In `~/.codex/config.toml`, configure:

```toml
[mcp_servers.cosmotech_infrastructure_http]
url = "http://127.0.0.1:8765/mcp"
bearer_token_env_var = "MCP_HTTP_BEARER_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"
```

Launch Codex from a shell where `MCP_HTTP_BEARER_TOKEN` is set. The URL is local to that machine. Do not use plain HTTP over an untrusted network.

## Claude Code: STDIO

For project-specific configuration, create `.mcp.json` in the project where Claude Code runs. Replace the command path and profile name. Do not put credential values in this file:

```json
{
  "mcpServers": {
    "cosmotech-infrastructure": {
      "type": "stdio",
      "command": "/home/alex/src/cosmotech-infrastructure-mcp/.venv/bin/python",
      "args": ["-m", "cosmotech_mcp", "serve", "--transport", "stdio"],
      "env": {
        "AWS_PROFILE": "infra-readonly",
        "AWS_REGION": "us-east-1",
        "KUBECONFIG": "/home/alex/.kube/config",
        "COSMOTECH_ALLOWED_ROOTS": "/home/alex/src/cosmotech-infrastructure-mcp:/home/alex/work/terraform"
      }
    }
  }
}
```

Restart Claude Code and use `/mcp` to inspect the connection. The settings file example follows Claude Code's documented MCP configuration; it has not been tested with Claude Code in this project.

## Cursor: STDIO

For project-specific configuration, create `.cursor/mcp.json` in the Cursor workspace (or use `~/.cursor/mcp.json` for global configuration):

```json
{
  "mcpServers": {
    "cosmotech-infrastructure": {
      "type": "stdio",
      "command": "/home/alex/src/cosmotech-infrastructure-mcp/.venv/bin/python",
      "args": ["-m", "cosmotech_mcp", "serve", "--transport", "stdio"],
      "env": {
        "AWS_PROFILE": "infra-readonly",
        "AWS_REGION": "us-east-1",
        "KUBECONFIG": "/home/alex/.kube/config",
        "COSMOTECH_ALLOWED_ROOTS": "/home/alex/src/cosmotech-infrastructure-mcp:/home/alex/work/terraform"
      }
    }
  }
}
```

Restart Cursor and enable the server in its MCP settings. Cursor's documented config format supports local command servers; this project configuration has not been tested inside Cursor.

## ChatGPT custom MCP app

ChatGPT cannot connect directly to a server running only on your laptop or loopback. It needs a reachable remote MCP endpoint or a supported secure tunnel. A remote setup must provide HTTPS, `/mcp`, and an authentication method accepted by the selected ChatGPT plan and workspace configuration. This server implements a static bearer token, not OAuth.

Current OpenAI documentation describes full MCP support for Business and Enterprise/Edu workspaces, with availability and controls managed by workspace administrators; Pro users may have read/fetch-only MCP app access in developer mode. Check the linked documentation and your account's current settings before deploying because this is a changing rollout. For a supported workspace/plan, the general setup is:

1. Ask the workspace administrator whether developer mode/custom MCP apps are available and enabled for your account.
2. Deploy the server behind a TLS-terminating proxy on a network reachable by ChatGPT. Keep the application token in a secret manager; do not expose the server directly to the public internet.
3. Create a custom MCP app in the workspace settings, enter the HTTPS endpoint ending in `/mcp`, and select an authentication option compatible with the server's bearer token.
4. Scan/discover the tools, review the exposed read-only actions, then test the draft app from a new chat.

Plan availability, admin controls, authentication choices, and UI can change. Check the [current ChatGPT developer mode and MCP app documentation](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt). The remote ChatGPT integration is not deployed or validated by this repository. A static bearer token is not a substitute for per-user OAuth on a public multi-user service.

## Other MCP-compatible clients

Any client supporting MCP STDIO can launch the Python command shown above. Clients supporting Streamable HTTP can connect to `/mcp` if they can send `Authorization: Bearer <token>` securely and can reach the server. Client configuration keys and secret interpolation differ; consult the client's current documentation rather than copying an unverified HTTP config snippet. Avoid storing bearer tokens in tracked project configuration.

For Cursor, its current `mcp.json` format supports HTTP headers and environment interpolation. With `MCP_HTTP_BEARER_TOKEN` present in the environment used to launch Cursor, a local HTTP entry can look like this:

```json
{
  "mcpServers": {
    "cosmotech-infrastructure-http": {
      "url": "http://127.0.0.1:8765/mcp",
      "headers": {
        "Authorization": "Bearer ${env:MCP_HTTP_BEARER_TOKEN}"
      }
    }
  }
}
```

This is a client configuration example, not an end-to-end test with Cursor. Use HTTPS for a remote server.

## Client references

- [Codex MCP configuration](https://developers.openai.com/codex/mcp)
- [ChatGPT developer mode and MCP apps](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt)
- [Claude Code MCP](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Cursor MCP configuration](https://cursor.com/docs/mcp)
- [MCP specification](https://modelcontextprotocol.io/)
