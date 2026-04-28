#!/usr/bin/env python3
import asyncio
import json
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

MOONRAKER_HOST = os.getenv("MOONRAKER_HOST", "localhost")
MOONRAKER_PORT = int(os.getenv("MOONRAKER_PORT", "7125"))
MOONRAKER_API_KEY = os.getenv("MOONRAKER_API_KEY", "")
BASE_URL = f"http://{MOONRAKER_HOST}:{MOONRAKER_PORT}"

MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
MCP_PORT = int(os.getenv("MCP_PORT", "8765"))
MCP_AUTH_KEY = os.getenv("MCP_AUTH_KEY", "")

server = Server("moonraker-mcp")


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if MOONRAKER_API_KEY:
        h["X-Api-Key"] = MOONRAKER_API_KEY
    return h


async def _get(path: str, params: dict | None = None) -> Any:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{BASE_URL}{path}", headers=_headers(), params=params)
        r.raise_for_status()
        return r.json()


async def _get_raw(path: str, query: str) -> Any:
    """GET with a pre-built query string (needed for Moonraker's bare ?key style)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{BASE_URL}{path}?{query}", headers=_headers())
        r.raise_for_status()
        return r.json()


async def _post(path: str, data: dict | None = None) -> Any:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{BASE_URL}{path}", headers=_headers(), json=data or {})
        r.raise_for_status()
        return r.json()


async def _get_text(path: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{BASE_URL}{path}", headers=_headers())
        r.raise_for_status()
        return r.text


async def _delete(path: str) -> Any:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.delete(f"{BASE_URL}{path}", headers=_headers())
        r.raise_for_status()
        return r.json()


async def _objects_query(*objects: str) -> Any:
    from urllib.parse import quote
    return await _get_raw("/printer/objects/query", "&".join(quote(o) for o in objects))


async def _gcode(script: str) -> Any:
    return await _post("/printer/gcode/script", {"script": script})


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_server_info",
            description="Get Moonraker server info: version, components loaded, and websocket connection state.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_printer_info",
            description="Get Klipper printer info: state, hostname, software versions.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_printer_status",
            description=(
                "Get a full snapshot of printer state: temperatures, print stats, "
                "toolhead position, display message, and virtual SD card."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_temperatures",
            description="Get current and target temperatures for all heaters (extruder, bed, any extra sensors).",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_job_status",
            description="Get current print job status: filename, state, progress %, print time, estimated time remaining.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="list_files",
            description="List gcode files stored on the printer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root": {
                        "type": "string",
                        "description": "File root to list (default: gcodes)",
                        "default": "gcodes",
                    }
                },
            },
        ),
        types.Tool(
            name="get_file_metadata",
            description="Get slicer metadata for a gcode file: estimated print time, filament used, layer count, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Gcode filename"}
                },
                "required": ["filename"],
            },
        ),
        types.Tool(
            name="print_file",
            description="Start printing a gcode file by name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Gcode filename to print"}
                },
                "required": ["filename"],
            },
        ),
        types.Tool(
            name="pause_print",
            description="Pause the currently running print job.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="resume_print",
            description="Resume a paused print job.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="cancel_print",
            description="Cancel the current print job.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="send_gcode",
            description="Send one or more raw gcode commands directly to the printer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Gcode command(s) to send (newline-separated for multiple)",
                    }
                },
                "required": ["script"],
            },
        ),
        types.Tool(
            name="set_temperature",
            description="Set the target temperature for a heater. Use 0 to turn it off.",
            inputSchema={
                "type": "object",
                "properties": {
                    "heater": {
                        "type": "string",
                        "enum": ["extruder", "heater_bed"],
                        "description": "Which heater to set",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Target temperature in Celsius (0 = off)",
                    },
                },
                "required": ["heater", "temperature"],
            },
        ),
        types.Tool(
            name="home_axes",
            description="Home printer axes. Homes all axes when none specified.",
            inputSchema={
                "type": "object",
                "properties": {
                    "axes": {
                        "type": "string",
                        "description": "Axes to home, e.g. 'X', 'XY', 'XYZ'. Omit to home all.",
                        "default": "",
                    }
                },
            },
        ),
        types.Tool(
            name="move_axis",
            description="Move printer axes. At least one of x/y/z must be provided.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X target (mm)"},
                    "y": {"type": "number", "description": "Y target (mm)"},
                    "z": {"type": "number", "description": "Z target (mm)"},
                    "speed": {
                        "type": "number",
                        "description": "Feed rate in mm/min (default 3000)",
                        "default": 3000,
                    },
                    "relative": {
                        "type": "boolean",
                        "description": "True for relative positioning, false for absolute (default false)",
                        "default": False,
                    },
                },
            },
        ),
        types.Tool(
            name="emergency_stop",
            description=(
                "EMERGENCY STOP: immediately halts all motion and disables heaters. "
                "Requires a firmware restart to recover."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="restart_klipper",
            description="Restart the Klipper host software (does not reset the MCU).",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="firmware_restart",
            description="Send a firmware restart to the MCU — clears MCU error states.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="restart_moonraker",
            description="Restart the Moonraker service.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="reboot_host",
            description="Reboot the host machine running Klipper and Moonraker.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="shutdown_host",
            description="Shut down the host machine running Klipper and Moonraker.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_print_history",
            description="Get a list of past print jobs with status, duration, and filament used.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max number of history entries to return (default 50)",
                        "default": 50,
                    }
                },
            },
        ),
        types.Tool(
            name="delete_file",
            description="Delete a gcode file from the printer's storage.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Gcode filename to delete"}
                },
                "required": ["filename"],
            },
        ),
        types.Tool(
            name="read_file",
            description="Read the contents of a file from a Moonraker file root (default: config).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the root, e.g. 'printer.cfg' or 'config_backups/printer-20260426.cfg'",
                    },
                    "root": {
                        "type": "string",
                        "description": "File root (default: config)",
                        "default": "config",
                    },
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="get_api_key",
            description=(
                "Retrieve the Moonraker API key. Only works when the request comes from "
                "a trusted client (e.g. localhost with trusted_clients configured)."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        result = await _dispatch(name, arguments)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    except httpx.HTTPStatusError as e:
        msg = f"HTTP {e.response.status_code} from Moonraker: {e.response.text}"
        return [types.TextContent(type="text", text=msg)]
    except httpx.RequestError as e:
        return [types.TextContent(type="text", text=f"Connection error (is Moonraker running?): {e}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {e}")]


async def _dispatch(name: str, args: dict[str, Any]) -> Any:
    match name:
        case "get_server_info":
            return await _get("/server/info")

        case "get_printer_info":
            return await _get("/printer/info")

        case "get_printer_status":
            return await _objects_query(
                "heater_bed", "extruder", "print_stats",
                "toolhead", "display_status", "virtual_sdcard",
            )

        case "get_temperatures":
            objects = await _get("/printer/objects/list")
            temp_prefixes = (
                "extruder", "heater_bed", "heater_generic",
                "temperature_sensor", "temperature_probe",
            )
            temp_objects = [
                o for o in objects.get("result", {}).get("objects", [])
                if any(o.startswith(p) for p in temp_prefixes)
            ]
            return await _objects_query(*temp_objects)

        case "get_job_status":
            return await _objects_query("print_stats", "virtual_sdcard", "display_status")

        case "list_files":
            return await _get("/server/files/list", params={"root": args.get("root", "gcodes")})

        case "get_file_metadata":
            return await _get("/server/files/metadata", params={"filename": args["filename"]})

        case "print_file":
            return await _post("/printer/print/start", {"filename": args["filename"]})

        case "pause_print":
            return await _post("/printer/print/pause")

        case "resume_print":
            return await _post("/printer/print/resume")

        case "cancel_print":
            return await _post("/printer/print/cancel")

        case "send_gcode":
            return await _gcode(args["script"])

        case "set_temperature":
            heater, temp = args["heater"], args["temperature"]
            gcode = f"M104 S{temp}" if heater == "extruder" else f"M140 S{temp}"
            return await _gcode(gcode)

        case "home_axes":
            axes = args.get("axes", "").upper().strip()
            return await _gcode(f"G28 {axes}".strip())

        case "move_axis":
            parts = []
            for axis in ("x", "y", "z"):
                if axis in args:
                    parts.append(f"{axis.upper()}{args[axis]}")
            if not parts:
                return {"error": "No axes provided — specify at least one of x, y, z"}
            speed = args.get("speed", 3000)
            if args.get("relative", False):
                script = f"G91\nG0 {' '.join(parts)} F{speed}\nG90"
            else:
                script = f"G90\nG0 {' '.join(parts)} F{speed}"
            return await _gcode(script)

        case "emergency_stop":
            return await _post("/printer/emergency_stop")

        case "restart_klipper":
            return await _post("/printer/restart")

        case "firmware_restart":
            return await _post("/printer/firmware_restart")

        case "restart_moonraker":
            return await _post("/machine/services/restart", {"service": "moonraker"})

        case "reboot_host":
            return await _post("/machine/reboot")

        case "shutdown_host":
            return await _post("/machine/shutdown")

        case "get_print_history":
            return await _get("/server/history/list", params={"limit": args.get("limit", 50)})

        case "delete_file":
            filename = args["filename"]
            return await _delete(f"/server/files/gcodes/{filename}")

        case "read_file":
            from urllib.parse import quote
            root = args.get("root", "config")
            path = args["path"]
            encoded = "/".join(quote(p, safe="") for p in path.split("/"))
            content = await _get_text(f"/server/files/{root}/{encoded}")
            return {"root": root, "path": path, "content": content}

        case "get_api_key":
            return await _get("/access/api_key")

        case _:
            return {"error": f"Unknown tool: {name}"}


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run_http():
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route
    import uvicorn

    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if MCP_AUTH_KEY:
                auth = request.headers.get("authorization", "")
                if auth != f"Bearer {MCP_AUTH_KEY}":
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
            return await call_next(request)

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )
    if MCP_AUTH_KEY:
        app.add_middleware(AuthMiddleware)

    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT)


if __name__ == "__main__":
    if MCP_TRANSPORT == "http":
        run_http()
    else:
        asyncio.run(main())
