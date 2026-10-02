#!/usr/bin/env python3
# mm_meta:
# name: US Border Wait Times
# emoji: 🛂
# language: Python
"""MeshMonitor Automation Engine script for CBP U.S. land-border wait times."""

import json
import os
import re
import sys
import urllib.error
import urllib.request

API_URL = "https://bwt.cbp.gov/api/waittimes"
HEADERS = {"User-Agent": "MeshMonitor-US-BorderWait-Automation/1.1"}
TIMEOUT = 8
MAX_REPLY_CHARS = 195
MAX_REPLY_BYTES = 195

ALIASES = {
    # Mexico
    "douglas": "douglasraulhectorcastro",
    "sandiego": "sanysidro",
    "roma": "roma",
    # Canada
    "buffalo": "buffaloniagarafalls",
    "niagara": "buffaloniagarafalls",
    "niagarafalls": "buffaloniagarafalls",
    "sault": "saultstemarie",
    "saultstemarie": "saultstemarie",
}

# Friendly aliases for individual CBP crossing names. Commands not listed here
# can still resolve dynamically when the command uniquely matches a crossing_name.
CROSSING_ALIASES = {
    "anzalduas": "anzalduasinternationalbridge",
    "bota": "bridgeoftheamericas",
    "deconcini": "deconcini",
    "mariposa": "mariposa",
    "morley": "morleygate",
    "morleygate": "morleygate",
    "pdn": "pasodelnorte",
    "stanton": "stantondcl",
    "stantondcl": "stantondcl",
    "ysleta": "ysleta",
}

def normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())

def fetch_ports():
    req = urllib.request.Request(API_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)

def requested_command():
    text = " ".join(
        [os.environ.get("MESSAGE", ""), os.environ.get("TRIGGER", "")]
        + [v for k, v in os.environ.items() if k.startswith("PARAM_")]
    ).lower()
    match = re.search(r"(?<![a-z0-9_])/?([a-z0-9]+?)(?:bwt|border)\b", text)
    return match.group(1) if match else None

def resolve_ports(data, command):
    validate_ports(data)
    border_ports = [
        p for p in data
        if p.get("border") in ("Mexican Border", "Canadian Border")
    ]

    # Resolve an individual POE/crossing first. This lets commands such as
    # /mariposabwt or /anzalduasbwt return one crossing while preserving
    # grouped commands such as /nogalesbwt and /hidalgopharrbwt.
    crossing_wanted = CROSSING_ALIASES.get(command, command)

    crossing_exact = [
        p for p in border_ports
        if normalize(p.get("crossing_name", "")) == crossing_wanted
    ]
    if len(crossing_exact) == 1:
        return crossing_exact

    crossing_prefix = [
        p for p in border_ports
        if normalize(p.get("crossing_name", "")).startswith(crossing_wanted)
    ]
    crossing_names = {
        normalize(p.get("crossing_name", "")) for p in crossing_prefix
    }
    if len(crossing_names) == 1:
        return crossing_prefix

    # Fall back to the existing grouped CBP port_name resolver.
    wanted = ALIASES.get(command, command)

    exact = [
        p for p in border_ports
        if normalize(p.get("port_name", "")) == wanted
    ]
    if exact:
        return exact

    prefix = [
        p for p in border_ports
        if normalize(p.get("port_name", "")).startswith(wanted)
    ]
    port_names = {normalize(p.get("port_name", "")) for p in prefix}
    return prefix if len(port_names) == 1 else []

def lane_wait(lane):
    if not lane:
        return None
    status = str(lane.get("operational_status", "")).lower()
    if "closed" in status:
        return None
    delay = str(lane.get("delay_minutes", "")).strip()
    if delay.isdigit():
        return f"{int(delay)}m"
    if "no delay" in status:
        return "0m"
    return None

def clean_hours(value):
    hours = (value or "hours n/a").strip()
    hours = hours.replace("24 hrs/day", "24 hrs")
    hours = re.sub(r"\s+(am|pm)", r"\1", hours, flags=re.I)
    return hours

def display_name(port):
    name = (port.get("crossing_name") or port.get("port_name") or "POE").strip()
    if name.lower() == "deconcini":
        return "DeConcini"
    return name

def crossing_line(port):
    name = display_name(port)
    hours = clean_hours(port.get("hours"))
    is_open = str(port.get("port_status", "")).lower() == "open"

    if not is_open:
        return f"🔴 {name} · CLOSED · {hours}"

    passenger = port.get("passenger_vehicle_lanes") or {}
    pedestrian = port.get("pedestrian_lanes") or {}

    standard = lane_wait(passenger.get("standard_lanes"))
    ready = lane_wait(passenger.get("ready_lanes"))
    trusted = lane_wait(passenger.get("NEXUS_SENTRI_lanes"))
    ped = lane_wait(pedestrian.get("standard_lanes"))

    parts = []
    if standard:
        parts.append(f"🚗{standard}")
    if ready:
        parts.append(f"READY {ready}")
    if trusted:
        label = "NEXUS" if port.get("border") == "Canadian Border" else "SENTRI"
        parts.append(f"{label} {trusted}")
    if ped:
        parts.append(f"🚶{ped}")

    if not parts:
        return f"🟢 {name} · {hours} · waits pending"

    return f"🟢 {name} · {hours} · {' '.join(parts)}"

def validate_ports(data):
    """Reject malformed feeds before formatting or resolving their records."""
    if not isinstance(data, list) or not data:
        raise ValueError("CBP feed must be a nonempty array")
    for port in data:
        if not isinstance(port, dict):
            raise ValueError("CBP port must be an object")
        for field in ("border", "port_name"):
            if not isinstance(port.get(field), str) or not port[field].strip():
                raise ValueError(f"Missing or invalid {field}")
        for field in ("crossing_name", "hours", "port_status"):
            if port.get(field) is not None and not isinstance(port[field], str):
                raise ValueError(f"Invalid {field}")
        for field in ("passenger_vehicle_lanes", "pedestrian_lanes"):
            group = port.get(field) or {}
            if not isinstance(group, dict):
                raise ValueError(f"Invalid {field}")
            for key in ("standard_lanes", "ready_lanes", "NEXUS_SENTRI_lanes"):
                lane = group.get(key)
                if lane is not None and not isinstance(lane, dict):
                    raise ValueError(f"Invalid {field}.{key}")

def split_reply(text):
    """Preserve all text while bounding both characters and UTF-8 bytes."""
    chunks, chunk = [], ""
    for char in text:
        candidate = chunk + char
        if len(candidate) > MAX_REPLY_CHARS or len(candidate.encode("utf-8")) > MAX_REPLY_BYTES:
            chunks.append(chunk)
            chunk = char
        else:
            chunk = candidate
    if chunk:
        chunks.append(chunk)
    return chunks

def build_report(data, command):
    matches = resolve_ports(data, command)
    if not matches:
        return f"🛂 /{command}bwt: CBP port not found."

    lines = [line for p in matches if (line := crossing_line(p))]
    if not lines:
        return f"🛂 /{command}bwt: waits unavailable."

    message = "\n".join(lines)
    if len(message) <= MAX_REPLY_CHARS and len(message.encode("utf-8")) <= MAX_REPLY_BYTES:
        return message
    return [chunk for line in lines for chunk in split_reply(line)]

def main():
    command = requested_command()
    if not command:
        print(json.dumps({
            "response": "🛂 Use /<port>bwt, e.g. /nogalesbwt or /detroitbwt"
        }, ensure_ascii=False))
        return

    try:
        data = fetch_ports()
        report = build_report(data, command)
        key = "responses" if isinstance(report, list) else "response"
        print(json.dumps({key: report}, ensure_ascii=False))
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"CBP lookup failed: {e}", file=sys.stderr)
        print(json.dumps({
            "response": "🛂 Border wait times unavailable right now."
        }, ensure_ascii=False))

if __name__ == "__main__":
    main()

