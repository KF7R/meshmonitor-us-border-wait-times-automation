import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch

import border_wait as b


def port(crossing="DeConcini", area="Nogales", border="Mexican Border"):
    return {
        "border": border, "port_name": area, "crossing_name": crossing,
        "port_status": "Open", "hours": "24 hrs/day",
        "passenger_vehicle_lanes": {
            key: {"delay_minutes": "15", "operational_status": "open"}
            for key in ("standard_lanes", "ready_lanes", "NEXUS_SENTRI_lanes")
        },
        "pedestrian_lanes": {"standard_lanes": {"delay_minutes": "5"}},
    }


class BorderWaitTests(unittest.TestCase):
    def test_documented_and_legacy_commands(self):
        for command in ("nogales", "mariposa", "detroit", "bota", "morley", "saultstemarie"):
            for suffix in ("bwt", "border"):
                with self.subTest(command=command, suffix=suffix):
                    with patch.dict(os.environ, {"MESSAGE": "/" + command.upper() + suffix}, clear=True):
                        self.assertEqual(b.requested_command(), command)

    def test_invalid_commands(self):
        for message in ("/bwt", "/nogalesbwt_extra", "/nogalesbwt123", "hello"):
            with patch.dict(os.environ, {"MESSAGE": message}, clear=True):
                self.assertIsNone(b.requested_command())

    def test_trigger_fallback(self):
        with patch.dict(os.environ, {"TRIGGER": "/detroitbwt"}, clear=True):
            self.assertEqual(b.requested_command(), "detroit")

    def test_individual_and_group_resolution(self):
        rows = [port(), port("Mariposa"), port("Morley Gate")]
        self.assertEqual(len(b.resolve_ports(rows, "nogales")), 3)
        self.assertEqual(b.resolve_ports(rows, "mariposa"), [rows[1]])
        self.assertEqual(b.resolve_ports(rows, "morley"), [rows[2]])

    def test_four_crossings_preserved(self):
        names = ["Lewiston Bridge", "Peace Bridge", "Rainbow Bridge", "Whirlpool Bridge"]
        rows = [port(name, "Buffalo/Niagara Falls", "Canadian Border") for name in names]
        result = b.build_report(rows, "buffalo")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        for name, reply in zip(names, result):
            self.assertIn(name, reply)

    def test_long_unicode_line_preserved_and_bounded(self):
        record = port("長" * 200)
        result = b.build_report([record], "nogales")
        self.assertIsInstance(result, list)
        self.assertEqual("".join(result), b.crossing_line(record))
        for reply in result:
            self.assertLessEqual(len(reply), 195)
            self.assertLessEqual(len(reply.encode("utf-8")), 195)

    def test_closed_port_hides_waits(self):
        record = port()
        record["port_status"] = "Closed"
        self.assertIn("CLOSED", b.crossing_line(record))
        self.assertNotIn("15m", b.crossing_line(record))

    def test_closed_lane_and_zero_delay(self):
        self.assertIsNone(b.lane_wait({"operational_status": "Lanes Closed", "delay_minutes": "15"}))
        self.assertEqual(b.lane_wait({"operational_status": "no delay", "delay_minutes": "0"}), "0m")

    def test_malformed_feeds_return_json_error(self):
        bad_feeds = [{"error": "unavailable"}, [], [None], [{}],
                     [dict(port(), passenger_vehicle_lanes="invalid")],
                     [dict(port(), hours=123)]]
        for data in bad_feeds:
            with self.subTest(data=data):
                stdout = io.StringIO()
                with patch.dict(os.environ, {"MESSAGE": "/nogalesbwt"}, clear=True), \
                     patch.object(b, "fetch_ports", return_value=data), \
                     contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
                    b.main()
                self.assertIn("unavailable", json.loads(stdout.getvalue())["response"])

    def test_main_emits_successful_json(self):
        stdout = io.StringIO()
        with patch.dict(os.environ, {"MESSAGE": "/mariposabwt"}, clear=True), \
             patch.object(b, "fetch_ports", return_value=[port("Mariposa")]), \
             contextlib.redirect_stdout(stdout):
            b.main()
        self.assertIn("Mariposa", json.loads(stdout.getvalue())["response"])


if __name__ == "__main__":
    unittest.main()
