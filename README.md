# Moonraker MCP Server

An MCP (Model Context Protocol) server that bridges Claude to the [Moonraker](https://moonraker.readthedocs.io) 3D printer API. Allows Claude to monitor printer status, control temperatures, manage print jobs, move axes, run macros, manage files, control timelapse, track filament via Spoolman, and more.

Docker image is automatically built and pushed to GHCR on every push to `main`. Watchtower picks up new images automatically — no manual redeploy needed.

---

## Available Tools

### Status

| Tool | Description |
|------|-------------|
| `get_server_info` | Moonraker version and loaded components |
| `get_printer_info` | Klipper state, hostname, software versions |
| `get_printer_status` | Full snapshot: temps, print stats, toolhead position, display message |
| `get_temperatures` | Current and target temperatures for all heaters and sensors |
| `get_job_status` | Current print job progress, state, and time remaining |

### Print Control

| Tool | Description |
|------|-------------|
| `print_file` | Start printing a gcode file by name |
| `pause_print` | Pause the current print |
| `resume_print` | Resume a paused print |
| `cancel_print` | Cancel the current print |

### Motion

| Tool | Description |
|------|-------------|
| `home_axes` | Home one or more axes (default: all) |
| `move_axis` | Move X/Y/Z axes to a position (absolute or relative) |
| `extrude` | Extrude or retract filament (positive = extrude, negative = retract) |

### Heaters and Fans

| Tool | Description |
|------|-------------|
| `set_temperature` | Set extruder or bed temperature (0 = off) |
| `set_fan_speed` | Set part cooling fan speed 0-100% |

### Macros

| Tool | Description |
|------|-------------|
| `list_macros` | List all `[gcode_macro]` entries defined in the Klipper config |
| `run_macro` | Run a Klipper gcode macro by name with optional parameters |
| `send_gcode` | Send raw gcode commands directly to the printer |

### File Management

| Tool | Description |
|------|-------------|
| `list_files` | List files in a Moonraker file root (default: gcodes) |
| `get_file_metadata` | Slicer metadata for a gcode file (print time, filament, layers) |
| `upload_file` | Upload a local gcode file to the printer |
| `read_file` | Read the contents of a file from a Moonraker file root (default: config) |
| `write_file` | Write or overwrite a file in a Moonraker file root (default: config) |
| `delete_file` | Delete a gcode file from the printer |

### History and Logs

| Tool | Description |
|------|-------------|
| `get_print_history` | List past print jobs with status, duration, and filament used |
| `read_log` | Read the tail of a Klipper or Moonraker log file |

### Timelapse

| Tool | Description |
|------|-------------|
| `list_timelapse` | List timelapse video files stored on the printer |
| `render_timelapse` | Trigger rendering of current timelapse frames into a video |
| `get_timelapse_settings` | Get current timelapse plugin settings |

### Spoolman

| Tool | Description |
|------|-------------|
| `get_spoolman_status` | Get Spoolman connection status |
| `get_active_spool` | Get the currently active spool ID |
| `set_active_spool` | Set the active spool ID in Moonraker/Spoolman |

### Power Devices

| Tool | Description |
|------|-------------|
| `list_power_devices` | List all power devices configured in Moonraker with their state |
| `set_power_device` | Turn a power device on, off, or toggle it |

### Service Management

| Tool | Description |
|------|-------------|
| `restart_klipper` | Restart the Klipper host software |
| `firmware_restart` | Send a firmware restart to the MCU (clears MCU error states) |
| `restart_moonraker` | Restart the Moonraker service |
| `reboot_host` | Reboot the host machine |
| `shutdown_host` | Shut down the host machine |
| `emergency_stop` | Immediately halt all motion and disable heaters (requires firmware restart to recover) |
| `get_api_key` | Retrieve the Moonraker API key |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOONRAKER_HOST` | `localhost` | IP or hostname of your Moonraker instance |
| `MOONRAKER_PORT` | `7125` | Moonraker port |
| `MOONRAKER_API_KEY` | *(empty)* | Moonraker API key (if required) |
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `http` |
| `MCP_PORT` | `8765` | Port to listen on in HTTP mode |
| `MCP_SERVER_URL` | `http://localhost:8765` | Public base URL in HTTP mode, used as the OAuth 2.1 issuer URL |

---

## Setup Options

### 1. stdio (Claude Code CLI)

For use with Claude Code or local MCP clients communicating over stdio.

**Requirements:** Python 3.11+

```bash
git clone https://github.com/TyanColte/moonrakermcp.git
cd moonrakermcp
python -m venv .venv
source .venv/bin/activate
pip install .
```

Add to your Claude Code MCP config (`~/.claude/claude.json` or project `.claude/claude.json`):

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

### 2. HTTP mode (Claude.ai web app)

The server uses StreamableHTTP with OAuth 2.1. Place it behind a reverse proxy that terminates TLS.

```bash
MCP_TRANSPORT=http \
MCP_PORT=8765 \
MCP_SERVER_URL=https://your-domain \
MOONRAKER_HOST=192.168.1.100 \
python server.py
```

Add to Claude.ai via **Settings → Integrations**:
- **URL:** `https://your-domain/mcp`

Claude.ai completes the OAuth flow automatically — no Bearer token needed.

---

### 3. Docker Compose (recommended for self-hosted)

Pull the pre-built image from GHCR:

```yaml
services:
  moonraker-mcp:
    image: ghcr.io/tyancolte/moonrakermcp:latest
    restart: unless-stopped
    ports:
      - "8765:8765"
    environment:
      - MCP_TRANSPORT=http
      - MCP_PORT=8765
      - MCP_SERVER_URL=https://moonraker-mcp.your-domain.com
      - MOONRAKER_HOST=192.168.1.100
      - MOONRAKER_PORT=7125
      - MOONRAKER_API_KEY=your-api-key
```

Caddy reverse proxy config:

```
moonraker-mcp.your-domain.com {
    reverse_proxy http://your-server-ip:8765
}
```

Then add to Claude.ai via **Settings → Integrations**:
- **URL:** `https://moonraker-mcp.your-domain.com/mcp`

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

print(log.sessions)
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

Each `TapTest` contains `avg_z`, `stddev`, `true_z_zero`, `sensor_offset`, and a list of `TapSample` objects with `z`, `toolhead_z`, `overshoot`, and `wall_time` values.

---

## Security Notes

- Always place the server behind a reverse proxy that terminates TLS. Never expose port 8765 directly to the internet.
- Set `MCP_SERVER_URL` to your public HTTPS URL — it is used as the OAuth 2.1 issuer URL and must match what clients see.
- `MOONRAKER_API_KEY` is only needed if your Moonraker instance has API key authentication enabled.
