from __future__ import annotations

import argparse
import logging
import sys

from cosmotech_mcp.core.settings import Settings
from cosmotech_mcp.server import create_server


def main() -> int:
    parser = argparse.ArgumentParser(prog="cosmotech-mcp")
    subparsers = parser.add_subparsers(dest="command", required=True)
    serve_parser = subparsers.add_parser("serve", help="Start the MCP server")
    serve_parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(message)s")

    try:
        settings = Settings.from_env()
        if args.transport == "http":
            if not settings.http_bearer_token:
                raise ValueError("HTTP transport requires MCP_HTTP_BEARER_TOKEN")
            server = create_server(settings=settings, auth_token=settings.http_bearer_token)
            server.run(
                transport="http",
                host=settings.http_host,
                port=settings.http_port,
                show_banner=False,
            )
        else:
            server = create_server(settings=settings)
            server.run(transport="stdio", show_banner=False)
    except (ValueError, OSError) as exc:
        print(f"cosmotech-mcp: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
