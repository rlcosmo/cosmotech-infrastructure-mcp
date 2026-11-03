FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTMCP_CHECK_FOR_UPDATES=off \
    MCP_HTTP_HOST=0.0.0.0 \
    MCP_HTTP_PORT=8765 \
    MCP_HTTP_ALLOW_NON_LOOPBACK=true

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /home/appuser/.local/state/cosmotech-infrastructure-mcp \
    && chown -R appuser:appuser /app /home/appuser/.local

USER 10001:10001
EXPOSE 8765
ENTRYPOINT ["cosmotech-mcp", "serve", "--transport", "http"]
