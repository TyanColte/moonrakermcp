"""
Utility for parsing Klipper log content returned by the read_log MCP tool.

Usage:
    import json
    with open('mcp-read_log-output.txt') as f:
        outer = json.load(f)
    log = KlipperLog(outer)
    print(log.sessions)
    print(log.wall_time_for_klipper_time(7875.6))
"""

import json
import re
import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class KlipperSession:
    start_wall: datetime.datetime
    start_unix: float
    start_line: int

    def klipper_to_wall(self, klipper_seconds: float) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.start_unix + klipper_seconds)


class KlipperLog:
    # Matches: Start printer at Wed Apr 29 16:04:09 2026 (1777496649.6 10.4)
    _RE_START = re.compile(r"Start printer at .+? \((\d+\.\d+)")

    def __init__(self, mcp_result):
        """Accept the raw JSON list returned by the read_log MCP tool."""
        if isinstance(mcp_result, list):
            raw = mcp_result[0]["text"]
        else:
            raw = mcp_result
        inner = json.loads(raw) if isinstance(raw, str) else raw
        self.content = inner["content"]
        self.total_lines = inner.get("total_lines")
        self.lines_returned = inner.get("lines_returned")
        self._lines = self.content.split("\n")
        self.sessions = self._parse_sessions()

    def _parse_sessions(self) -> list:
        sessions = []
        for i, line in enumerate(self._lines):
            m = self._RE_START.search(line)
            if m:
                unix_ts = float(m.group(1))
                sessions.append(KlipperSession(
                    start_wall=datetime.datetime.fromtimestamp(unix_ts),
                    start_unix=unix_ts,
                    start_line=i,
                ))
        return sessions

    def session_for_line(self, line_idx: int) -> Optional[KlipperSession]:
        """Return the session that was active at a given line index."""
        active = None
        for s in self.sessions:
            if s.start_line <= line_idx:
                active = s
            else:
                break
        return active

    def wall_time_for_klipper_time(self, klipper_seconds: float,
                                   session_index: int = -1) -> Optional[datetime.datetime]:
        """Convert a Klipper internal timestamp to wall clock time."""
        if not self.sessions:
            return None
        return self.sessions[session_index].klipper_to_wall(klipper_seconds)
