# moonraker-mcp

MCP server bridging Claude to the Moonraker 3D printer API. Runs as a Docker container, exposed via Caddy at `moonraker-mcp.tyan.omegaos.us`.

## Repo Layout

- `server.py` — all MCP tool definitions and dispatch logic
- `klipper_log_parser.py` — utility for parsing Klipper log timestamps and sessions
- `tap_parser.py` — parses BTT Eddy tap test results from Klipper logs
- `Dockerfile` — builds the image pushed to `ghcr.io/tyancolte/moonrakermcp:latest`

## Deploy

Push to GitHub → GitHub Actions builds and pushes the image to GHCR → Watchtower picks it up automatically (no manual redeploy needed).

Stack config: `~/git/docker-stacks/moonraker-mcp/docker-compose.yml`

Transport: HTTP with OAuth 2.1 (`MCP_TRANSPORT=http`), port 8765.

## Moonraker Connection

Connects to Moonraker at `192.168.30.117:7125` (server LAN address, not localhost — the MCP container is not on the host network).

API key via `MOONRAKER_API_KEY` env var (in `~/git/docker-stacks/environment/moonraker-mcp.env`).

## Available Tools

**Status:**
- `get_server_info`, `get_printer_info`, `get_printer_status`, `get_temperatures`, `get_job_status`

**Print control:**
- `print_file`, `pause_print`, `resume_print`, `cancel_print`

**Motion:**
- `home_axes`, `move_axis` (X/Y/Z), `extrude` (E-axis, relative, positive=extrude/negative=retract)

**Heaters and fans:**
- `set_temperature` (extruder or heater_bed), `set_fan_speed` (part cooling fan, 0-100%)

**Macros:**
- `list_macros` — lists all `[gcode_macro]` entries from Klipper config
- `run_macro` — runs a macro by name with optional parameters
- `send_gcode` — raw gcode for anything not covered above

**Files:**
- `list_files`, `get_file_metadata`, `delete_file`
- `read_file` (default root: config), `write_file` (uploads new content to config or other root)
- `upload_file` — uploads a local gcode file to the printer

**History and logs:**
- `get_print_history`, `read_log` (klippy.log or moonraker.log)

**Timelapse:**
- `list_timelapse`, `render_timelapse`, `get_timelapse_settings`

**Spoolman:**
- `get_spoolman_status`, `get_active_spool`, `set_active_spool`

**Power devices:**
- `list_power_devices`, `set_power_device` (on/off/toggle)

**Service management:**
- `restart_klipper`, `firmware_restart`, `restart_moonraker`, `reboot_host`, `shutdown_host`, `emergency_stop`

**Other:**
- `get_api_key`

## Adding New Tools

1. Add a `types.Tool(...)` entry in `list_tools()`
2. Add a `case "tool_name":` block in `_dispatch()`
3. Push — Watchtower handles the rest

Helper functions: `_get`, `_post`, `_delete`, `_get_text`, `_get_raw`, `_gcode`, `_upload` (multipart file upload), `_objects_query` (Moonraker printer object queries).
