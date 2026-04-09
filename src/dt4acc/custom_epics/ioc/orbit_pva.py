from __future__ import annotations

import getpass
import os
import threading
import time
from typing import Any, Dict, List

from ...core.utils.logger import get_logger
from p4p import Type, Value
from p4p.server import Server
from p4p.server.thread import SharedPV
logger = get_logger()
orbit_type = Type(
    id="epics:nt/NTTable:1.0",
    spec=[
        (
            "value",
            ("S", None, [
                ("A",         "ad"),
                ("B",         "ad"),
                ("BPM",       "as"),
                ("C",         "ad"),
                ("D",         "ad"),
                ("X",         "ad"),
                ("Y",         "ad"),
            ]),
        ),
        (
            "alarm",
            ("S", "alarm_t", [
                ("severity", "i"),
                ("status", "i"),
                ("message", "s"),
            ]),
        ),
        (
            "timeStamp",
            ("S", "time_t", [
                ("secondsPastEpoch", "l"),
                ("nanoseconds",      "i"),
                ("userTag",          "i"),
            ]),
        ),
    ],
)

initial_data = {
    "value": {
        "A":         [],
        "B":         [],
        "BPM":       [],
        "C":         [],
        "D":         [],
        "X":         [],
        "Y":         [],
    },
}


class OrbitTwinServer:
    def __init__(self, pv_name: str = "ORBITCC:rdBpm"):
        self.pv_name = pv_name
        self.pv = SharedPV(initial=Value(orbit_type, initial_data))

        @self.pv.put
        def _handle_put(pv, op):
            new_value = op.value()
            pv.post(new_value)
            op.done()

        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the PVA server in the background."""
        if self._thread and self._thread.is_alive():
            return

        def run_server():
            Server.forever(providers=[{self.pv_name: self.pv}])

        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()

    def push(self, *, x: List[float], y: List[float], names: List[str]) -> None:
        bpm_mask = [n.startswith("BPM") for n in names]
        x = [v for v, keep in zip(x, bpm_mask) if keep]
        y = [v for v, keep in zip(y, bpm_mask) if keep]
        names = [n for n, keep in zip(names, bpm_mask) if keep]

        now = time.time()
        data = {
            "value": {
                "A": [v * 0.95 for v in x],
                "B": [v * 0.90 for v in x],
                "BPM": names,
                "C": [v * 0.85 for v in x],
                "D": [v * 0.80 for v in x],
                "X": x,
                "Y": y,
            },
            "timeStamp": {
                "secondsPastEpoch": int(now),
                "nanoseconds": int((now % 1) * 1e9),
                "userTag": 0,
            },
            "alarm": {
                "severity": 0,
                "status": 0,
                "message": "",
            },
        }
        self.pv.post(Value(orbit_type, data))

    def push_raw(self, data: Dict[str, Any]) -> None:
        """Publish a prebuilt dictionary from the server side."""
        self.pv.post(Value(orbit_type, data))


def main():
    prefix = os.environ.get("DT4ACC_PREFIX", getpass.getuser())
    logger.warning(f"PREFIX in orbit pva IS: {prefix}")
    server = OrbitTwinServer(prefix + "ORBITCC:rdBpm")
    server.start()

    print(f"Orbit PV server is running on '{prefix}:ORBITCC:rdBpm'")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            threading.Event().wait(1.0)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()