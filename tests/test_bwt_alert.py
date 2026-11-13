import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bwt_alert as a
import bwt_baseline as bl


def port(crossing, area, wait, status="Open"):
    return {
        "border": "Mexican Border", "port_name": area, "crossing_name": crossing,
        "port_status": status, "hours": "24 hrs/day",
        "passenger_vehicle_lanes": {"standard_lanes": {
            "operational_status": "delay", "delay_minutes": str(wait)}},
        "pedestrian_lanes": {},
    }


def feed(dec=20, mar=10, b1=10, b2=10, far=200, dec_status="Open"):
    return [
        port("Deconcini", "Nogales", dec, dec_status),
        port("Mariposa", "Nogales", mar),
        port("Bridge I", "Laredo", b1),
        port("Bridge II", "Laredo", b2),
        port("", "San Ysidro", far),  # not configured: must never alert
    ]


CFG = {"thresholds": {"deconcini": 60, "mariposa": 45, "laredo/bridgei": 50},
       "clear_fraction": 0.8, "cooldown_s": 7200}


class AlertTests(unittest.TestCase):
    def test_quiet_below_thresholds(self):
        self.assertEqual(a.evaluate(feed(), CFG, {}, 0)[0], [])

    def test_alert_once_then_hold(self):
        lines, st = a.evaluate(feed(dec=75), CFG, {}, 0)
        self.assertEqual(len(lines), 1)
        self.assertIn("DeConcini backed up: 🚗75m (alert ≥60m)", lines[0])
        self.assertEqual(a.evaluate(feed(dec=90), CFG, st, 900)[0], [])

    def test_hysteresis_and_clear(self):
        _, st = a.evaluate(feed(mar=50), CFG, {}, 0)
        lines, st = a.evaluate(feed(mar=40), CFG, st, 900)  # 40 > 36: hold
        self.assertEqual(lines, [])
        lines, _ = a.evaluate(feed(mar=30), CFG, st, 1800)
        self.assertEqual(len(lines), 1)
        self.assertIn("Mariposa cleared", lines[0])

    def test_cooldown(self):
        _, st = a.evaluate(feed(dec=70), CFG, {}, 0)
        _, st = a.evaluate(feed(dec=10), CFG, st, 900)
        self.assertEqual(a.evaluate(feed(dec=70), CFG, st, 1800)[0], [])
        self.assertEqual(len(a.evaluate(feed(dec=70), CFG, st, 7300)[0]), 1)

    def test_closed_changes_nothing(self):
        _, st = a.evaluate(feed(dec=70), CFG, {}, 0)
        lines, st2 = a.evaluate(feed(dec_status="Closed"), CFG, st, 900)
        self.assertEqual(lines, [])
        self.assertTrue(st2["Nogales|Deconcini"]["packed"])

    def test_area_slash_crossing_key(self):
        lines, _ = a.evaluate(feed(b1=55, b2=99), CFG, {}, 0)
        self.assertEqual(len(lines), 1)  # Bridge II is not configured
        self.assertIn("Bridge I", lines[0])

    def test_area_key_covers_every_crossing(self):
        cfg = dict(CFG, thresholds={"nogales": 40})
        lines, _ = a.evaluate(feed(dec=45, mar=41), cfg, {}, 0)
        self.assertEqual(len(lines), 2)

    def test_load_config_validates(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "c.json")
            path.write_text(json.dumps({"thresholds": {"Laredo/Bridge I": 50}, "cooldown_minutes": 30}))
            cfg = a.load_config(path)
            self.assertEqual(cfg["thresholds"], {"laredo/bridgei": 50})
            self.assertEqual(cfg["cooldown_s"], 1800)
            path.write_text(json.dumps({"thresholds": {"x": 0}}))
            with self.assertRaises(ValueError):
                a.load_config(path)

    def test_main_posts_nothing_on_fetch_error(self):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as d, \
                patch.object(a, "CONFIG_PATH", Path(d, "missing.json")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            a.main()
        self.assertEqual(json.loads(out.getvalue()), {"response": ""})

    def test_main_end_to_end_with_state(self):
        with tempfile.TemporaryDirectory() as d:
            cfg_path = Path(d, "c.json")
            cfg_path.write_text(json.dumps({"thresholds": {"deconcini": 60}}))
            with patch.object(a, "CONFIG_PATH", cfg_path), \
                    patch.object(a, "STATE_DIR", Path(d)), \
                    patch.object(a, "STATE_FILE", Path(d, "s.json")), \
                    patch.object(a.bw, "fetch_ports", return_value=feed(dec=80)):
                for expected in ("backed up", ""):
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        a.main()
                    reply = json.loads(out.getvalue())["response"]
                    self.assertIn(expected, reply) if expected else self.assertEqual(reply, "")


class BaselineTests(unittest.TestCase):
    def test_summarize_picks_percentile_and_busiest(self):
        rows = [{"bwt_day": str(d), "time_slot": str(h), "pv_time_avg": str(10 + d * 10 if h == 17 else 10)}
                for d in range(7) for h in range(24)]
        stats = bl.summarize(rows, 90)
        self.assertEqual(stats["median"], 10)
        self.assertEqual(stats["max"], 70)
        self.assertTrue(stats["busiest"][0].startswith("Sun 17:00 70m"))

    def test_summarize_needs_open_hours(self):
        rows = [{"bwt_day": "0", "time_slot": str(h), "pv_time_avg": "0"} for h in range(24)]
        self.assertIsNone(bl.summarize(rows))


if __name__ == "__main__":
    unittest.main()
