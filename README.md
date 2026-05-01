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
| `read_file` | Read the contents of a file from a Moonraker file root (default: config) |
| `read_log` | Read the tail of a Klipper or Moonraker log file |
| `get_api_key` | Retrieve the Moonraker API key |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOONRAKER_HOST` | `localhost` | IP or hostname of your Moonraker instance |
| `MOONRAKER_PORT` | `7125` | Moonraker port |
| `MOONRAKER_API_KEY` | *(empty)* | Moonraker API key (if required) |
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `http` |
| `MCP_PORT` | `8765` | Port to listen on in HTTP mode |
| `MCP_SERVER_URL` | `http://localhost:8765` | Public base URL of the server, used as the OAuth 2.1 issuer URL in HTTP mode |

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

For use with Claude.ai web app. The server uses StreamableHTTP with OAuth 2.1 and should sit behind a reverse proxy that handles TLS.

```bash
MCP_TRANSPORT=http \
MCP_PORT=8765 \
MCP_SERVER_URL=https://your-domain \
MOONRAKER_HOST=192.168.1.100 \
python server.py
```

The MCP endpoint will be available at `http://localhost:8765/mcp`.

Add to Claude.ai via **Settings → Integrations**:
- **URL:** `https://your-domain/mcp`

Claude.ai will complete the OAuth flow automatically — no Bearer token is needed.

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
  -e MCP_SERVER_URL=https://your-domain \
  -e MOONRAKER_HOST=192.168.1.100 \
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
      - MCP_SERVER_URL=https://your-domain
      - MOONRAKER_HOST=192.168.1.100
      - MOONRAKER_PORT=7125
      - MOONRAKER_API_KEY=
```

#### Reverse proxy (Caddy example)

```
moonraker-mcp.your-domain.com {
    reverse_proxy http://your-server-ip:8765
}
```

Then add to Claude.ai via **Settings → Integrations**:
- **URL:** `https://moonraker-mcp.your-domain.com/mcp`

Claude.ai will complete the OAuth flow automatically — no Bearer token is needed.

---

## Log Parsing Utilities

Two Python modules are included for working with data returned by the `read_log` tool.

### `klipper_log_parser.py`

Parses Klipper log content and converts internal Klipper timestamps to wall-clock times.

```python
import json
from klipper_log_parser import KlipperLog

result = mcp_client.call_tool("read_log", {"log": "klippy.log", "lines": 500})
log = KlipperLog(result)

# List detected Klipper sessions with their start times
print(log.sessions)

# Convert a Klipper internal timestamp to wall time
print(log.wall_time_for_klipper_time(7875.6))
```

### `tap_parser.py`

Parses BTT Eddy tap test results from a `KlipperLog`. Returns `TapTest` objects with per-sample wall-clock times.

```python
from klipper_log_parser import KlipperLog
from tap_parser import find_tap_tests

log = KlipperLog(result)
for test in find_tap_tests(log):
    print(test)
```

Each `TapTest` contains `avg_z`, `stddev`, `true_z_zero`, `sensor_offset`, and a list of `TapSample` objects with individual `z`, `toolhead_z`, `overshoot`, and `wall_time` values.

---

## Security Notes

- Always place the server behind a reverse proxy that terminates TLS. Never expose the HTTP port directly to the internet.
- Set `MCP_SERVER_URL` to your public HTTPS URL in HTTP mode — it is used as the OAuth 2.1 issuer URL and must match what clients see.
- `MOONRAKER_API_KEY` is only needed if your Moonraker instance has API key authentication enabled.
