FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml server.py ./

RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=http
ENV MCP_PORT=8765
ENV MOONRAKER_HOST=192.168.30.117
ENV MOONRAKER_PORT=7125

EXPOSE 8765

CMD ["python", "server.py"]
