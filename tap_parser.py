"""
Parser for BTT Eddy tap test results from Klipper logs.

Usage:
    import json
    from klipper_log_parser import KlipperLog
    from tap_parser import find_tap_tests

    with open('mcp-read_log-output.txt') as f:
        data = json.load(f)
    log = KlipperLog(data)
    for test in find_tap_tests(log):
        print(test)
"""

import re
import datetime
from dataclasses import dataclass
from typing import Optional

from klipper_log_parser import KlipperLog, KlipperSession

# btt_eddy: tap[2]: 0.080 toolhead at: -0.055 overshoot: 0.135 at 7873.1961s
_RE_TAP_SAMPLE = re.compile(
    r"btt_eddy: tap\[(\d+)\]: ([\d.]+) toolhead at: ([-\d.]+) overshoot: ([\d.]+) at ([\d.]+)s"
)

# btt_eddy: Probe computed tap at 0.138 (tap at z=0.088, stddev 0.005) with 3 samples,
#           homed z with true_z_zero=-0.138, ..., sensor offset -0.063 at z=2.000
_RE_COMPUTED = re.compile(
    r"Probe computed tap at ([\d.]+) \(tap at z=([\d.]+), stddev ([\d.]+)\) with (\d+) samples,"
    r".+?true_z_zero=([-\d.]+).+?sensor offset ([-\d.]+)"
)


@dataclass
class TapSample:
    session: KlipperSession
    tap_number: int
    z: float
    toolhead_z: float
    overshoot: float
    klipper_time: float

    @property
    def wall_time(self) -> datetime.datetime:
        return self.session.klipper_to_wall(self.klipper_time)


@dataclass
class TapTest:
    session: KlipperSession
    samples: list
    avg_z: float
    stddev: float
    true_z_zero: float
    sensor_offset: float

    @property
    def wall_time(self) -> Optional[datetime.datetime]:
        return self.samples[-1].wall_time if self.samples else None

    def __str__(self):
        time_str = self.wall_time.strftime('%Y-%m-%d %H:%M:%S') if self.wall_time else 'unknown'
        lines = [
            f"Tap test @ {time_str}",
            f"  Samples: {len(self.samples)}, avg z={self.avg_z:.3f} mm, stddev={self.stddev:.3f}",
            f"  true_z_zero={self.true_z_zero:.3f}, sensor_offset={self.sensor_offset:.3f}",
        ]
        for s in self.samples:
            lines.append(
                f"  Tap {s.tap_number}: z={s.z:.3f}  toolhead={s.toolhead_z:.3f}"
                f"  overshoot={s.overshoot:.3f}  @ {s.wall_time.strftime('%H:%M:%S')}"
            )
        return "\n".join(lines)


def find_tap_tests(log: KlipperLog) -> list:
    """Return all TapTest objects from the log, newest first."""
    current_samples = []
    tests = []

    for i, line in enumerate(log._lines):
        m = _RE_TAP_SAMPLE.search(line)
        if m:
            sample = TapSample(
                session=log.session_for_line(i),
                tap_number=int(m.group(1)),
                z=float(m.group(2)),
                toolhead_z=float(m.group(3)),
                overshoot=float(m.group(4)),
                klipper_time=float(m.group(5)),
            )
            # Deduplicate — BTT Eddy emits the same line multiple times
            if not current_samples or current_samples[-1].tap_number != sample.tap_number:
                current_samples.append(sample)
            continue

        m = _RE_COMPUTED.search(line)
        if m:
            tests.append(TapTest(
                session=log.session_for_line(i),
                samples=list(current_samples),
                avg_z=float(m.group(2)),
                stddev=float(m.group(3)),
                true_z_zero=float(m.group(5)),
                sensor_offset=float(m.group(6)),
            ))
            current_samples = []

    tests.reverse()
    return tests
