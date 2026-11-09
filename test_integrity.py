"""Regression checks for the evidence and review integrity boundaries."""

import json
from pathlib import Path
import tempfile
import unittest

from review_log import digest, load_events, review_status
from verify_evidence import item_1c_section


class IntegrityTests(unittest.TestCase):
    def test_item_1c_ignores_toc_and_other_sections(self):
        text = (
            "item 1c. cybersecurity item 2. properties "
            "item 1c. cybersecurity " + "source statement " * 100
            + "item 2. properties unrelated source statement"
        )
        section = item_1c_section(text)
        self.assertIn("source statement", section)
        self.assertNotIn("unrelated", section)

    def test_ambiguous_section_fails_closed(self):
        with self.assertRaises(ValueError):
            item_1c_section("item 1c. cybersecurity short item 2. properties")

    def test_review_log_detects_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reviews.jsonl"
            event = {"evidence_id": "A", "decision": "approve", "previous_hash": "0" * 64}
            event["event_hash"] = digest(event)
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            self.assertEqual(len(load_events(path)), 1)
            event["decision"] = "reject"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_events(path)

    def test_changed_source_invalidates_review(self):
        rows = {"A": {"source_sha256": "new", "section_sha256": "section", "evidence_sha256": "same"}}
        events = [{"evidence_id": "A", "decision": "approve", "source_sha256": "old", "section_sha256": "section", "reviewer": "R", "timestamp_utc": "T"}]
        self.assertEqual(review_status(rows, events)["A"]["state"], "stale_source_re_review_required")

    def test_changed_observation_invalidates_review(self):
        rows = {"A": {"source_sha256": "same", "section_sha256": "same", "evidence_sha256": "new"}}
        events = [{"evidence_id": "A", "decision": "approve", "source_sha256": "same", "section_sha256": "same", "evidence_sha256": "old", "reviewer": "R", "timestamp_utc": "T"}]
        self.assertEqual(review_status(rows, events)["A"]["state"], "stale_evidence_re_review_required")


if __name__ == "__main__":
    unittest.main()
