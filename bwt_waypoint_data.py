#!/usr/bin/env python3
# mm_meta:
# name: BWT Waypoint Data
# emoji: 🛂
# language: Python

import json
import sys

from border_wait import fetch_ports, resolve_ports, lane_wait, display_name


def waypoint_description(port):
    is_open = str(port.get("port_status", "")).lower() == "open"

    if not is_open:
        return "CLOSED"

    passenger = port.get("passenger_vehicle_lanes") or {}
    pedestrian = port.get("pedestrian_lanes") or {}

    standard = lane_wait(passenger.get("standard_lanes"))
    ready = lane_wait(passenger.get("ready_lanes"))
    trusted = lane_wait(passenger.get("NEXUS_SENTRI_lanes"))
    ped = lane_wait(pedestrian.get("standard_lanes"))

    parts = []

    if standard:
        parts.append(f"Cars {standard}")
    if ready:
        parts.append(f"Ready {ready}")
    if trusted:
        label = "NEXUS" if port.get("border") == "Canadian Border" else "SENTRI"
        parts.append(f"{label} {trusted}")
    if ped:
        parts.append(f"Pedestrians {ped}")

    return ", ".join(parts) if parts else "Waits unavailable"


def main():
    if len(sys.argv) != 2:
        print("Usage: bwt_waypoint_data.py <poe>", file=sys.stderr)
        sys.exit(2)

    command = sys.argv[1].strip().lower()

    try:
        data = fetch_ports()
        matches = resolve_ports(data, command)

        if len(matches) != 1:
            raise ValueError(
                f"{command}: expected exactly one crossing, got {len(matches)}"
            )

        port = matches[0]

        result = {
            "poe": command,
            "name": display_name(port),
            "description": waypoint_description(port)
        }

        print(json.dumps(result, ensure_ascii=False))

    except (OSError, ValueError) as e:
        print(f"BWT waypoint lookup failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
