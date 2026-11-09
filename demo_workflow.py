"""Run a disposable end-to-end example without changing real review decisions."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
CODE = ["verify_evidence.py", "review_log.py", "sources.json", "evidence.json"]


def run(folder, *args):
    process = subprocess.run(
        [sys.executable, *args], cwd=folder, text=True, capture_output=True, check=False
    )
    return process.returncode, (process.stdout + process.stderr).strip()


def main():
    transcript = ["DISPOSABLE DEMO — no real review decisions were recorded"]
    with tempfile.TemporaryDirectory(prefix="grc-evidence-demo-") as temporary:
        folder = Path(temporary)
        for filename in CODE:
            shutil.copy2(ROOT / filename, folder / filename)
        shutil.copytree(ROOT / "sources", folder / "sources")

        code, message = run(folder, "verify_evidence.py")
        if code:
            raise RuntimeError(message)
        transcript.append("1. Verify Item 1C anchors: " + message)

        code, message = run(folder, "review_log.py", "record", "MSFT-2025-01", "needs_more_evidence", "--reviewer", "DEMO ONLY", "--note", "Example review note; inspect the full filing context before any real decision.")
        if code:
            raise RuntimeError(message)
        transcript.append("2. Record example decision: needs_more_evidence (DEMO ONLY)")

        code, message = run(folder, "verify_evidence.py")
        if code:
            raise RuntimeError(message)
        report = json.loads((folder / "output" / "verification_report.json").read_text(encoding="utf-8"))
        state = report["review_status"]["MSFT-2025-01"]["state"]
        assert state == "needs_more_evidence"
        transcript.append("3. Regenerate comparison: MSFT-2025-01 = " + state)

        evidence_path = folder / "evidence.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence[0]["observation"] += " DEMO wording change."
        evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        code, message = run(folder, "verify_evidence.py")
        if code:
            raise RuntimeError(message)
        report = json.loads((folder / "output" / "verification_report.json").read_text(encoding="utf-8"))
        state = report["review_status"]["MSFT-2025-01"]["state"]
        assert state == "stale_evidence_re_review_required"
        transcript.append("4. Change observation wording: MSFT-2025-01 = " + state)

        log_path = folder / "output" / "reviews.jsonl"
        log_path.write_text(log_path.read_text(encoding="utf-8").replace("needs_more_evidence", "approve", 1), encoding="utf-8")
        code, message = run(folder, "review_log.py", "status")
        assert code != 0 and "integrity failure" in message
        transcript.append("5. Tamper with saved decision: blocked by review log integrity failure")

    output = ROOT / "output" / "demo_transcript.txt"
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(transcript) + "\n", encoding="utf-8")
    print(output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
