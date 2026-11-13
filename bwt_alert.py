#!/usr/bin/env python3
# mm_meta:
# name: BWT Backup Alerts
# emoji: 🛂
# language: Python
"""Post to a channel when a land-border crossing backs up, and when it clears.

Run on a schedule (for example every 15 minutes). Each run reads the CBP feed
once and compares each configured crossing's standard passenger-vehicle wait
with its threshold:

  - ALERT once when the wait reaches the threshold.
  - CLEAR once when it falls to clear_fraction x threshold (hysteresis, so a
    wait hovering around the line does not flap).
  - At most one alert per crossing per cooldown_minutes.
  - A closed crossing, a missing wait, or a failed fetch posts nothing.

Configuration is a JSON file (BWT_ALERT_CONFIG, default bwt_alert.json next to
this script). Threshold keys use the same names as the /<name>bwt commands,
an area key applies its threshold to every crossing in that area, and
"area/crossing" picks one crossing whose name is not unique (e.g. "laredo/bridgei"):

  {"thresholds": {"deconcini": 60, "mariposa": 45, "laredo/bridgei": 50},
   "clear_fraction": 0.8, "cooldown_minutes": 120}

bwt_baseline.py suggests thresholds from CBP's historical averages.

Prints {"response": ""} when there is nothing to say, otherwise
{"response": "..."} or {"responses": [...]}.
State: BWT_STATE_DIR (default /data/scripts/state)/bwt_alert_state.json
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import border_wait as bw  # noqa: E402

CONFIG_PATH = Path(os.environ.get("BWT_ALERT_CONFIG", Path(__file__).with_name("bwt_alert.json")))
STATE_DIR = Path(os.environ.get("BWT_STATE_DIR", "/data/scripts/state"))
STATE_FILE = STATE_DIR / "bwt_alert_state.json"
MAX_BYTES = 195


def load_config(path=None):
    cfg = json.loads(Path(path or CONFIG_PATH).read_text())
    thresholds = cfg.get("thresholds")
    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError("config needs a nonempty 'thresholds' object")
    for key, value in thresholds.items():
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"threshold for {key!r} must be a positive number")
    return {
        "thresholds": {"/".join(bw.normalize(part) for part in k.split("/", 1)): v
                       for k, v in thresholds.items()},
        "clear_fraction": float(cfg.get("clear_fraction", 0.8)),
        "cooldown_s": int(float(cfg.get("cooldown_minutes", 120)) * 60),
    }


def car_wait(port):
    """Standard passenger-vehicle wait in minutes, or None if closed/unknown."""
    if str(port.get("port_status", "")).lower() != "open":
        return None
    lane = (port.get("passenger_vehicle_lanes") or {}).get("standard_lanes")
    wait = bw.lane_wait(lane)
    return int(wait[:-1]) if wait else None


def crossing_id(port):
    return f"{port.get('port_name', '').strip()}|{(port.get('crossing_name') or '').strip()}"


def resolve_key(data, key):
    """A /<name>bwt name, or "area/crossing" for one crossing in an area."""
    if "/" in key:
        area, crossing = (bw.normalize(part) for part in key.split("/", 1))
        return [p for p in bw.resolve_ports(data, area)
                if bw.normalize(p.get("crossing_name") or "") == crossing]
    return bw.resolve_ports(data, key)


def watched(data, cfg):
    """[(port, threshold)] for every crossing a configured key resolves to."""
    out, seen = [], set()
    for key, limit in cfg["thresholds"].items():
        for port in resolve_key(data, key):
            cid = crossing_id(port)
            if cid not in seen:
                seen.add(cid)
                out.append((port, limit))
    return out


def evaluate(data, cfg, state, now):
    """Return (lines_to_send, new_state). Pure apart from `now`."""
    lines, new = [], dict(state)
    for port, limit in watched(data, cfg):
        cid = crossing_id(port)
        st = dict(new.get(cid, {}))
        wait = car_wait(port)
        if wait is None:
            continue
        st["last_wait"] = wait
        name = bw.display_name(port)
        if not st.get("packed"):
            last = st.get("alert_at")
            if wait >= limit and (last is None or now - last >= cfg["cooldown_s"]):
                lines.append(f"⚠️ {name} backed up: 🚗{wait}m (alert ≥{limit:g}m)")
                st.update(packed=True, alert_at=now)
        elif wait <= limit * cfg["clear_fraction"]:
            lines.append(f"✅ {name} cleared: 🚗{wait}m")
            st["packed"] = False
        new[cid] = st
    return lines, new


def pack(lines):
    """Join lines into as few messages of at most MAX_BYTES as possible."""
    msgs, cur = [], ""
    for line in lines:
        candidate = f"{cur}\n{line}" if cur else line
        if len(candidate.encode("utf-8")) <= MAX_BYTES:
            cur = candidate
            continue
        if cur:
            msgs.append(cur)
        cur = line
    if cur:
        msgs.append(cur)
    return [chunk for msg in msgs for chunk in bw.split_reply(msg)]


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True))
    os.replace(tmp, STATE_FILE)


def main():
    try:
        cfg = load_config()
        data = bw.fetch_ports()
        bw.validate_ports(data)
    except Exception as e:  # never post because of a config or fetch problem
        print(f"BWT alert skipped: {e}", file=sys.stderr)
        print(json.dumps({"response": ""}))
        return
    lines, new = evaluate(data, cfg, load_state(), int(time.time()))
    save_state(new)
    if not lines:
        print(json.dumps({"response": ""}))
        return
    msgs = pack(["🛂 " + lines[0]] + lines[1:])
    key, value = ("response", msgs[0]) if len(msgs) == 1 else ("responses", msgs)
    print(json.dumps({key: value}, ensure_ascii=False))


if __name__ == "__main__":
    main()
