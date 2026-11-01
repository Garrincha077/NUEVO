"""Offline regression tests: DST, grace, run proof and strict output status."""
from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from owner_cron_audit import (
    Cron, classify_due, expected_occurrences, extract_crons, previous_morning, summary,
)


def ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def run(when, status="completed", conclusion="success", id=1):
    return {"id": id, "html_url": f"https://github.com/owner/repo/actions/runs/{id}",
            "event": "schedule", "created_at": when, "status": status,
            "conclusion": conclusion}


class ScheduleAuditTests(unittest.TestCase):
    def test_sunday_seven_alias_and_posix_dom_dow_or(self):
        self.assertTrue(Cron("0 9 * * 7").matches(ts("2026-11-01T09:00:00Z")))
        self.assertTrue(Cron("0 9 1 * 3").matches(ts("2026-11-01T09:00:00Z")))
        self.assertFalse(Cron("0 9 1 * 3").matches(ts("2026-11-02T09:00:00Z")))
        self.assertTrue(Cron("15-45/15 6 * JAN-MAR MON-FRI").matches(ts("2026-03-02T06:30:00Z")))
        self.assertFalse(Cron("15-45/15 6 * JAN-MAR MON-FRI").matches(ts("2026-04-02T06:30:00Z")))

    def test_dst_start_and_end_shift_previous_check(self):
        summer = previous_morning(ts("2026-03-29T09:00:00Z"))
        winter = previous_morning(ts("2026-11-01T10:00:00Z"))
        self.assertEqual(summer, ts("2026-03-28T09:00:00Z"))
        self.assertEqual(winter, ts("2026-10-31T09:00:00Z"))
        self.assertEqual(previous_morning(ts("2026-03-30T09:00Z")),
                         ts("2026-03-29T08:00Z"))
        self.assertEqual(previous_morning(ts("2026-10-26T09:00Z")),
                         ts("2026-10-25T09:00Z"))
        self.assertEqual(summer.astimezone(ZoneInfo("Europe/Zagreb")).hour, 10)
        self.assertEqual(winter.astimezone(ZoneInfo("Europe/Zagreb")).hour, 10)

    def test_multiple_crons_deduplicated(self):
        due = expected_occurrences(["0 8 * * *", "0 8 * * 0"], ts("2026-11-01T07:59Z"),
                                   ts("2026-11-01T08:10Z"))
        self.assertEqual(due, [ts("2026-11-01T08:00Z")])

    def test_on_key_with_pyyaml_bool_and_no_schedule(self):
        text = 'name: X\non:\n  schedule:\n    - cron: "0 7 * * 2-6"\n'
        self.assertEqual(extract_crons(text), ["0 7 * * 2-6"])
        self.assertEqual(extract_crons('on:\n  workflow_dispatch:\n'), [])

    def test_timing_grace_no_future_miss(self):
        due = [ts("2026-11-01T08:00Z")]
        self.assertEqual(classify_due(due, [], ts("2026-11-01T08:29Z"))[0]["status"],
                         "PENDING_GRACE")
        self.assertEqual(classify_due(due, [], ts("2026-11-01T08:30Z"))[0]["status"],
                         "MISSED_UNVERIFIED")

    def test_late_success_output_is_unverified(self):
        rows = classify_due([ts("2026-11-01T08:00Z")],
                            [run("2026-11-01T09:10:00Z")], ts("2026-11-01T10:00Z"))
        self.assertEqual(rows[0]["status"], "DELAYED_OUTPUT_UNVERIFIED")
        self.assertEqual(rows[0]["outputFresh"], "NOT_CHECKED")
        self.assertTrue(rows[0]["runUrl"].endswith("/1"))

    def test_failed_cancelled_and_running_are_distinct(self):
        due = [ts("2026-11-01T08:00Z")]
        for status, conclusion, expected in [("completed", "failure", "FAILURE"),
                                              ("completed", "cancelled", "CANCELLED"),
                                              ("in_progress", None, "IN_PROGRESS")]:
            result = classify_due(due, [run("2026-11-01T08:11:00Z", status, conclusion)],
                                  ts("2026-11-01T09:00Z"))
            self.assertEqual(result[0]["status"], expected)

    def test_next_slot_cannot_claim_late_previous_run(self):
        due = [ts("2026-11-01T08:00Z"), ts("2026-11-01T09:00Z")]
        rows = classify_due(due, [run("2026-11-01T09:10Z")], ts("2026-11-01T10:00Z"))
        self.assertEqual(rows[0]["status"], "MISSED_UNVERIFIED")
        self.assertEqual(rows[1]["status"], "RUN_SUCCESS_OUTPUT_UNVERIFIED")
        self.assertEqual(rows[1]["timingMapping"], "INFERRED_FROM_CREATED_AT_ONLY")

    def test_non_schedule_run_cannot_fill_missing_cron(self):
        manual = {**run("2026-11-01T08:02Z"), "event": "workflow_dispatch"}
        rows = classify_due([ts("2026-11-01T08:00Z")], [manual], ts("2026-11-01T09:00Z"))
        self.assertEqual(rows[0]["status"], "MISSED_UNVERIFIED")

    def test_summary_explicit_unverified_outputs(self):
        report = {"coverage": "PUBLIC_ONLY_INCOMPLETE_PRIVATE_COVERAGE", "status": "INCOMPLETE",
                  "repositoriesDiscovered": 1, "scheduledWorkflowsSeen": 1,
                  "windowStartUTC": "2026-10-31T08:00:00Z", "generatedAtUTC": "2026-11-01T10:00:00Z",
                  "counts": {"MISSED_UNVERIFIED": 1}, "occurrences": [], "errors": []}
        self.assertIn("NOT verified here", summary(report))


if __name__ == "__main__":
    unittest.main()
