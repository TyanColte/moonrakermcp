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
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"http://localhost:{MCP_PORT}")

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
        types.Tool(
            name="read_log",
            description=(
                "Read the tail of a Klipper or Moonraker log file. "
                "Use list_files with root='logs' to see all available log files."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "log": {
                        "type": "string",
                        "description": "Log filename, e.g. 'klippy.log' or 'moonraker.log' (default: klippy.log)",
                        "default": "klippy.log",
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Number of lines from the end to return (default: 100)",
                        "default": 100,
                    },
                },
            },
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

        case "read_log":
            from urllib.parse import quote
            log = args.get("log", "klippy.log")
            lines = args.get("lines", 100)
            content = await _get_text(f"/server/files/logs/{quote(log, safe='')}")
            all_lines = content.splitlines()
            tail = all_lines[-lines:]
            return {
                "log": log,
                "total_lines": len(all_lines),
                "lines_returned": len(tail),
                "content": "\n".join(tail),
            }

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
    import contextlib
    import secrets
    import time
    from collections.abc import AsyncIterator
    from mcp.server.auth.provider import (
        AccessToken, AuthorizationCode, AuthorizationParams,
        RefreshToken, construct_redirect_uri,
    )
    from mcp.server.auth.routes import create_auth_routes, create_protected_resource_routes
    from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
    from pydantic import AnyHttpUrl
    from starlette.applications import Starlette
    from starlette.routing import Mount
    import uvicorn

    issuer_url = AnyHttpUrl(MCP_SERVER_URL.rstrip("/"))
    resource_url = AnyHttpUrl(MCP_SERVER_URL.rstrip("/") + "/")

    class PermissiveOAuthProvider:
        """In-memory OAuth provider that auto-approves all requests."""

        def __init__(self):
            self._clients: dict[str, OAuthClientInformationFull] = {}
            self._auth_codes: dict[str, AuthorizationCode] = {}
            self._access_tokens: dict[str, AccessToken] = {}
            self._refresh_tokens: dict[str, RefreshToken] = {}

        async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
            return self._clients.get(client_id)

        async def register_client(self, client_info: OAuthClientInformationFull) -> None:
            self._clients[client_info.client_id] = client_info

        async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
            code = secrets.token_urlsafe(32)
            self._auth_codes[code] = AuthorizationCode(
                code=code,
                scopes=params.scopes or [],
                expires_at=time.time() + 300,
                client_id=client.client_id,
                code_challenge=params.code_challenge,
                redirect_uri=params.redirect_uri,
                redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            )
            return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

        async def load_authorization_code(self, client: OAuthClientInformationFull, code: str) -> AuthorizationCode | None:
            return self._auth_codes.get(code)

        async def exchange_authorization_code(self, client: OAuthClientInformationFull, auth_code: AuthorizationCode) -> OAuthToken:
            del self._auth_codes[auth_code.code]
            access = secrets.token_urlsafe(32)
            refresh = secrets.token_urlsafe(32)
            self._access_tokens[access] = AccessToken(
                token=access, client_id=client.client_id, scopes=auth_code.scopes, expires_at=None,
            )
            self._refresh_tokens[refresh] = RefreshToken(
                token=refresh, client_id=client.client_id, scopes=auth_code.scopes, expires_at=None,
            )
            return OAuthToken(
                access_token=access, token_type="bearer",
                refresh_token=refresh, scope=" ".join(auth_code.scopes),
            )

        async def load_refresh_token(self, client: OAuthClientInformationFull, token: str) -> RefreshToken | None:
            return self._refresh_tokens.get(token)

        async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
            del self._refresh_tokens[refresh_token.token]
            access = secrets.token_urlsafe(32)
            new_refresh = secrets.token_urlsafe(32)
            self._access_tokens[access] = AccessToken(
                token=access, client_id=client.client_id, scopes=refresh_token.scopes, expires_at=None,
            )
            self._refresh_tokens[new_refresh] = RefreshToken(
                token=new_refresh, client_id=client.client_id, scopes=refresh_token.scopes,
            )
            return OAuthToken(
                access_token=access, token_type="bearer",
                refresh_token=new_refresh, scope=" ".join(refresh_token.scopes),
            )

        async def load_access_token(self, token: str) -> AccessToken | None:
            return self._access_tokens.get(token)

        async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
            if isinstance(token, AccessToken):
                self._access_tokens.pop(token.token, None)
            else:
                self._refresh_tokens.pop(token.token, None)

    oauth_provider = PermissiveOAuthProvider()

    session_manager = StreamableHTTPSessionManager(
        app=server,
        stateless=False,
        json_response=False,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            yield

    auth_routes = create_auth_routes(
        provider=oauth_provider,
        issuer_url=issuer_url,
        client_registration_options=ClientRegistrationOptions(enabled=True, valid_scopes=["mcp"]),
        revocation_options=RevocationOptions(enabled=True),
    )

    protected_resource_routes = create_protected_resource_routes(
        resource_url=resource_url,
        authorization_servers=[issuer_url],
        scopes_supported=["mcp"],
        resource_name="Moonraker MCP Server",
    )

    app = Starlette(
        lifespan=lifespan,
        routes=[
            *auth_routes,
            *protected_resource_routes,
            Mount("/", app=session_manager.handle_request),
        ]
    )

    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT)


if __name__ == "__main__":
    if MCP_TRANSPORT == "http":
        run_http()
    else:
        asyncio.run(main())
