"""Record and validate human evidence decisions against verified source hashes."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "output" / "reviews.jsonl"
DECISIONS = {"approve", "reject", "needs_more_evidence"}


def digest(data):
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_events(path=LOG):
    if not path.exists():
        return []
    events = []
    previous = "0" * 64
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        event = json.loads(line)
        event_hash = event.pop("event_hash")
        if event.get("previous_hash") != previous or digest(event) != event_hash:
            raise ValueError(f"Review log integrity failure at line {number}")
        event["event_hash"] = event_hash
        previous = event_hash
        events.append(event)
    return events


def load_register():
    path = ROOT / "output" / "evidence_register.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {row["id"]: row for row in rows}


def record(evidence_id, decision, reviewer, note):
    if decision not in DECISIONS:
        raise ValueError(f"Decision must be one of {sorted(DECISIONS)}")
    if not reviewer.strip() or len(note.strip()) < 12:
        raise ValueError("A reviewer name and substantive note of at least 12 characters are required")
    rows = load_register()
    if evidence_id not in rows:
        raise ValueError(f"Unknown evidence ID: {evidence_id}")
    row = rows[evidence_id]
    if row["verification"] != "matched_once":
        raise ValueError("Source anchor must match exactly once before review")
    events = load_events()
    event = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_id": evidence_id,
        "decision": decision,
        "reviewer": reviewer.strip(),
        "note": note.strip(),
        "source_sha256": row["source_sha256"],
        "section_sha256": row["section_sha256"],
        "evidence_sha256": row["evidence_sha256"],
        "previous_hash": events[-1]["event_hash"] if events else "0" * 64,
    }
    event["event_hash"] = digest(event)
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def review_status(rows=None, events=None):
    rows = rows if rows is not None else load_register()
    events = events if events is not None else load_events()
    latest = {event["evidence_id"]: event for event in events}
    result = {}
    for evidence_id, row in rows.items():
        event = latest.get(evidence_id)
        if not event:
            state = "unreviewed"
        elif event["source_sha256"] != row["source_sha256"] or event["section_sha256"] != row["section_sha256"]:
            state = "stale_source_re_review_required"
        elif event.get("evidence_sha256") != row["evidence_sha256"]:
            state = "stale_evidence_re_review_required"
        else:
            state = event["decision"]
        result[evidence_id] = {"state": state, "reviewer": event["reviewer"] if event else "", "timestamp_utc": event["timestamp_utc"] if event else ""}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    action = sub.add_parser("record")
    action.add_argument("evidence_id")
    action.add_argument("decision", choices=sorted(DECISIONS))
    action.add_argument("--reviewer", required=True)
    action.add_argument("--note", required=True)
    sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "record":
        print(json.dumps(record(args.evidence_id, args.decision, args.reviewer, args.note), indent=2))
    else:
        print(json.dumps(review_status(), indent=2))


if __name__ == "__main__":
    main()
