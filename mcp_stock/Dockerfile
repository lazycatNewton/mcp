FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

WORKDIR /app

RUN groupadd --system mcp && useradd --system --gid mcp --home-dir /app mcp

COPY . /app/mcp_stock

RUN pip install --no-cache-dir "mcp>=1.0.0" "tushare>=1.4.29" && \
    chown -R mcp:mcp /app

USER mcp

EXPOSE 8000

CMD ["python", "-m", "mcp_stock", "--transport", "streamable-http"]
