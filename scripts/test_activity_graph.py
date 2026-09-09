import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from scripts.activity_graph import render_activity


NS = {"svg": "http://www.w3.org/2000/svg"}


def root_for(days, theme="dark"):
    return ET.fromstring(render_activity(days, theme))


def points(root):
    return root.findall(".//svg:circle[@class='day-point']", NS)


class RenderActivityTests(unittest.TestCase):
    def test_uses_exact_31_calendar_day_window_ending_at_last_date(self):
        start = date(2025, 12, 1)
        days = [(start + timedelta(days=i), i) for i in range(45)]

        plotted = points(root_for(days))

        self.assertEqual(len(plotted), 31)
        self.assertEqual(plotted[0].attrib["data-date"], "2025-12-15")
        self.assertEqual(plotted[-1].attrib["data-date"], "2026-01-14")
        self.assertEqual(plotted[0].attrib["data-count"], "14")

    def test_fills_missing_calendar_dates_with_zero(self):
        days = [(date(2026, 2, 1), 3), (date(2026, 2, 3), 7)]

        by_date = {p.attrib["data-date"]: p.attrib["data-count"] for p in points(root_for(days))}

        self.assertEqual(by_date["2026-02-01"], "3")
        self.assertEqual(by_date["2026-02-02"], "0")
        self.assertEqual(by_date["2026-02-03"], "7")

    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):
            render_activity([], "dark")

    def test_zero_and_single_day_data_produce_finite_valid_svg(self):
        svg = render_activity([(date(2026, 3, 9), 0)], "light")
        root = ET.fromstring(svg)

        self.assertEqual(root.attrib["viewBox"], "0 0 880 300")
        self.assertEqual(len(points(root)), 31)
        self.assertNotIn("nan", svg.lower())
        self.assertNotIn("inf", svg.lower())
        labels = [n.text for n in root.findall(".//svg:text[@class='y-label']", NS)]
        self.assertEqual(labels, ["0", "1"])

    def test_svg_maps_dates_and_counts_to_accessible_points(self):
        days = [
            (date(2026, 4, 1), 0),
            (date(2026, 4, 2), 2),
            (date(2026, 4, 3), 4),
        ]
        root = root_for(days)
        plotted = points(root)
        tail = plotted[-3:]

        self.assertEqual(root.find("svg:title", NS).text, "Contribution Graph")
        self.assertIn("2026-03-04 to 2026-04-03", root.find("svg:desc", NS).text)
        self.assertEqual(
            [(p.attrib["data-date"], p.attrib["data-count"]) for p in tail],
            [("2026-04-01", "0"), ("2026-04-02", "2"), ("2026-04-03", "4")],
        )
        self.assertGreater(float(tail[0].attrib["cy"]), float(tail[1].attrib["cy"]))
        self.assertGreater(float(tail[1].attrib["cy"]), float(tail[2].attrib["cy"]))
        self.assertEqual([p.find("svg:title", NS).text for p in tail], [
            "2026-04-01: 0 contributions",
            "2026-04-02: 2 contributions",
            "2026-04-03: 4 contributions",
        ])

    def test_edge_date_labels_anchor_inward_without_moving_points(self):
        root = root_for([(date(2026, 5, 1), 2)])
        labels = root.findall(".//svg:text[@class='x-label']", NS)
        plotted = points(root)

        self.assertEqual(labels[0].attrib["text-anchor"], "start")
        self.assertEqual(labels[-1].attrib["text-anchor"], "end")
        self.assertEqual(labels[0].attrib["x"], plotted[0].attrib["cx"])
        self.assertEqual(labels[-1].attrib["x"], plotted[-1].attrib["cx"])

    def test_as_of_excludes_future_row_from_window_counts_and_scale(self):
        days = [
            (date(2026, 9, 8), 2),
            (date(2026, 9, 9), 4),
            (date(2026, 9, 10), 999),
        ]
        root = ET.fromstring(render_activity(days, "dark", as_of=date(2026, 9, 9)))
        plotted = points(root)
        y_labels = [int(n.text) for n in root.findall(".//svg:text[@class='y-label']", NS)]

        self.assertEqual(plotted[-1].attrib["data-date"], "2026-09-09")
        self.assertEqual(plotted[-1].attrib["data-count"], "4")
        self.assertNotIn("2026-09-10", {p.attrib["data-date"] for p in plotted})
        self.assertEqual(max(y_labels), 4)


if __name__ == "__main__":
    unittest.main()
