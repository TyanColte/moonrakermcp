# Moonraker MCP Server

An MCP (Model Context Protocol) server that bridges Claude to the [Moonraker](https://moonraker.readthedocs.io) 3D printer API. Allows Claude to check printer status, control temperatures, manage print jobs, move axes, and more.

## Available Tools

| Tool | Description |
|------|-------------|
| `get_server_info` | Moonraker version and loaded components |
| `get_printer_info` | Klipper state, hostname, software versions |
| `get_printer_status` | Full snapshot: temps, print stats, toolhead position |
| `get_temperatures` | Current and target temperatures for all heaters |
| `get_job_status` | Current print job progress, state, and time remaining |
| `list_files` | List gcode files stored on the printer |
| `get_file_metadata` | Slicer metadata for a gcode file |
| `print_file` | Start printing a gcode file |
| `pause_print` | Pause the current print |
| `resume_print` | Resume a paused print |
| `cancel_print` | Cancel the current print |
| `send_gcode` | Send raw gcode commands |
| `set_temperature` | Set extruder or bed temperature |
| `home_axes` | Home one or more axes |
| `move_axis` | Move axes to a position |
| `emergency_stop` | Immediately halt all motion and disable heaters |
| `restart_klipper` | Restart the Klipper host software |
| `firmware_restart` | Send a firmware restart to the MCU |
| `restart_moonraker` | Restart the Moonraker service |
| `reboot_host` | Reboot the host machine |
| `shutdown_host` | Shut down the host machine |
| `get_print_history` | List past print jobs |
| `delete_file` | Delete a gcode file |
| `get_api_key` | Retrieve the Moonraker API key |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOONRAKER_HOST` | `localhost` | IP or hostname of your Moonraker instance |
| `MOONRAKER_PORT` | `7125` | Moonraker port |
| `MOONRAKER_API_KEY` | *(empty)* | Moonraker API key (if required) |
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `http` |
| `MCP_PORT` | `8765` | Port to listen on in HTTP mode |
| `MCP_AUTH_KEY` | *(empty)* | Bearer token to protect the HTTP endpoint |

---

## Setup Options

### 1. Manual (stdio)

For use with Claude Code CLI or local MCP clients that communicate over stdio.

**Requirements:** Python 3.11+

```bash
git clone https://github.com/TyanColte/moonrakermcp.git
cd moonrakermcp
python -m venv .venv
source .venv/bin/activate
pip install .
```

Run the server:

```bash
MOONRAKER_HOST=192.168.1.100 python server.py
```

Add to your Claude Code config (`~/.claude/claude.json` or project `.claude/claude.json`):

```json
{
  "mcpServers": {
    "moonraker": {
      "command": "/path/to/moonrakermcp/.venv/bin/python",
      "args": ["/path/to/moonrakermcp/server.py"],
      "env": {
        "MOONRAKER_HOST": "192.168.1.100"
      }
    }
  }
}
```

---

### 2. HTTP mode (manual)

For use with Claude.ai web app. The server exposes an SSE endpoint over HTTP, which should sit behind a reverse proxy that handles TLS.

```bash
MCP_TRANSPORT=http \
MCP_PORT=8765 \
MCP_AUTH_KEY=your-secret-key \
MOONRAKER_HOST=192.168.1.100 \
python server.py
```

The SSE endpoint will be available at `http://localhost:8765/sse`.

Add to Claude.ai via **Settings → Integrations**:
- **URL:** `https://your-domain/sse`
- **Bearer token:** the value of `MCP_AUTH_KEY`

---

### 3. Docker (build from source)

```bash
git clone https://github.com/TyanColte/moonrakermcp.git
cd moonrakermcp
docker build -t moonraker-mcp:latest .

docker run -d \
  --name moonraker-mcp \
  --restart unless-stopped \
  -p 8765:8765 \
  -e MCP_TRANSPORT=http \
  -e MCP_PORT=8765 \
  -e MOONRAKER_HOST=192.168.1.100 \
  -e MCP_AUTH_KEY=your-secret-key \
  moonraker-mcp:latest
```

---

### 4. Docker Compose / Portainer Stack

Build the image first (on the host machine):

```bash
git clone https://github.com/TyanColte/moonrakermcp.git
cd moonrakermcp
docker build -t moonraker-mcp:latest .
```

Then deploy with the following compose file (paste into Portainer as a new stack):

```yaml
services:
  moonraker-mcp:
    image: moonraker-mcp:latest
    restart: unless-stopped
    ports:
      - "8765:8765"
    environment:
      - MCP_TRANSPORT=http
      - MCP_PORT=8765
      - MOONRAKER_HOST=192.168.1.100
      - MOONRAKER_PORT=7125
      - MOONRAKER_API_KEY=
      - MCP_AUTH_KEY=your-secret-key
```

#### Reverse proxy (Caddy example)

```
moonraker-mcp.your-domain.com {
    reverse_proxy http://your-server-ip:8765
}
```

Then add to Claude.ai via **Settings → Integrations**:
- **URL:** `https://moonraker-mcp.your-domain.com/sse`
- **Bearer token:** the value of `MCP_AUTH_KEY`

---

## Security Notes

- Always set `MCP_AUTH_KEY` when running in HTTP mode — without it the endpoint is open to anyone who knows the URL.
- Always place the server behind a reverse proxy that terminates TLS. Never expose the HTTP port directly to the internet.
- `MOONRAKER_API_KEY` is only needed if your Moonraker instance has API key authentication enabled.
