#!/usr/bin/env python3
"""Suggest bwt_alert.py thresholds from CBP's historical wait averages.

Usage:  python3 bwt_baseline.py <name> [month] [percentile]
        python3 bwt_baseline.py nogales 11
        python3 bwt_baseline.py mariposa 7 80

<name> is the same name as the /<name>bwt command (area or crossing). The
month defaults to the current month; the percentile defaults to 90, meaning
the alert fires in roughly the busiest 10% of open hours.

Data comes from the endpoint behind the "Historical" page on bwt.cbp.gov:

  https://bwt.cbp.gov/api/historicalwaittimes/<bwtId>/POV/GEN/<month>/7

It returns one average standard passenger-vehicle wait (pv_time_avg) per
weekday (bwt_day 0 = Monday ... 6 = Sunday) and hour (time_slot, local time
at the port) for that month. CBP does not say which years are averaged.
The bwtId comes from /api/bwtmodern/crossingslist; its last six digits are
the port_number in the live /api/waittimes feed.

This only reads CBP data and prints a report. It sends nothing.
"""

import datetime
import json
import statistics
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import border_wait as bw  # noqa: E402

BASE = "https://bwt.cbp.gov/api"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def get_json(url):
    req = urllib.request.Request(url, headers=bw.HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def bwt_ids():
    """Map live-feed port_number -> historical bwtId."""
    rows = get_json(f"{BASE}/bwtmodern/crossingslist").get("portCrossings", [])
    return {str(r["bwtId"])[-6:]: str(r["bwtId"]) for r in rows if r.get("bwtId")}


def history(bwt_id, month):
    data = get_json(f"{BASE}/historicalwaittimes/{bwt_id}/POV/GEN/{month}/7")
    return data.get("wait_times", []) if isinstance(data, dict) else []


def summarize(rows, percentile=90):
    """Return stats for open hours (car wait > 0), or None if there are none."""
    slots = {(int(r["bwt_day"]), int(r["time_slot"])): int(r["pv_time_avg"])
             for r in rows if str(r.get("pv_time_avg", "")).isdigit()}
    open_waits = sorted(v for v in slots.values() if v > 0)
    if len(open_waits) < 10:
        return None
    cut = statistics.quantiles(open_waits, n=100, method="inclusive")[percentile - 1]
    threshold = int(5 * round(cut / 5)) or 5
    busiest = sorted(((v, d, h) for (d, h), v in slots.items() if v >= threshold), reverse=True)
    return {
        "median": statistics.median(open_waits),
        "threshold": threshold,
        "max": open_waits[-1],
        "busiest": [f"{DAYS[d]} {h:02d}:00 {v}m" for v, d, h in busiest[:5]],
        "alert_hours_per_week": len(busiest),
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    name = bw.normalize(argv[1])
    month = int(argv[2]) if len(argv) > 2 else datetime.date.today().month
    percentile = int(argv[3]) if len(argv) > 3 else 90
    ports = bw.resolve_ports(bw.fetch_ports(), name)
    if not ports:
        print(f"No CBP crossing matches {name!r}.", file=sys.stderr)
        return 1
    ids = bwt_ids()
    suggested = {}
    for port in ports:
        label = bw.display_name(port)
        bwt_id = ids.get(str(port.get("port_number", "")))
        stats = summarize(history(bwt_id, month), percentile) if bwt_id else None
        if not stats:
            print(f"{label}: no passenger-vehicle history for month {month}.")
            continue
        print(f"{label} (month {month}): typical {stats['median']:g}m, "
              f"p{percentile} {stats['threshold']}m, max {stats['max']}m, "
              f"~{stats['alert_hours_per_week']} hours/week at or above threshold")
        print("  busiest: " + ", ".join(stats["busiest"]))
        crossing = bw.normalize(port.get("crossing_name") or "")
        key = f"{bw.normalize(port.get('port_name'))}/{crossing}" if len(ports) > 1 and crossing else name
        suggested[key] = stats["threshold"]
    if suggested:
        print("\nSuggested bwt_alert.json:")
        print(json.dumps({"thresholds": suggested, "clear_fraction": 0.8,
                          "cooldown_minutes": 120}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
