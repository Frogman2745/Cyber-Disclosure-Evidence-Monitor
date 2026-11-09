"""Verify bounded SEC disclosure anchors and export a traceable review queue."""

import csv
import hashlib
from html.parser import HTMLParser
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "tr", "td", "br"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1
        if tag in {"p", "div", "tr", "td"}:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def normalize(value):
    return re.sub(r"\s+", " ", value).strip().casefold()


def main():
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "evidence.json").read_text(encoding="utf-8"))
    source_map = {item["company"]: item for item in sources}
    if len(source_map) != len(sources):
        raise ValueError("Duplicate company source")
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    files = {}
    for company, source in source_map.items():
        raw = (ROOT / "sources" / source["file"]).read_bytes()
        parser = VisibleText()
        parser.feed(raw.decode("utf-8", errors="replace"))
        files[company] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "text": normalize("".join(parser.parts)),
            "size_bytes": len(raw),
        }
    rows = []
    seen = set()
    for item in evidence:
        if item["id"] in seen:
            raise ValueError(f"Duplicate evidence id: {item['id']}")
        seen.add(item["id"])
        company = item["company"]
        source = source_map[company]
        match_count = files[company]["text"].count(normalize(item["anchor"]))
        rows.append({
            **item,
            "form": source["form"],
            "fiscal_year_end": source["fiscal_year_end"],
            "accession": source["accession"],
            "filing_url": source["url"],
            "source_sha256": files[company]["sha256"],
            "anchor_match_count": match_count,
            "verification": "matched_once" if match_count == 1 else "needs_review",
        })
    with (output / "evidence_register.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "source_files": [{**source, "sha256": files[source["company"]]["sha256"], "size_bytes": files[source["company"]]["size_bytes"]} for source in sources],
        "candidate_count": len(rows),
        "matched_once": sum(row["verification"] == "matched_once" for row in rows),
        "needs_review": [row["id"] for row in rows if row["verification"] != "matched_once"],
        "interpretation": "Anchor matching establishes traceability, not control effectiveness or verified implementation.",
    }
    (output / "verification_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    cards = []
    for company in source_map:
        source = source_map[company]
        company_rows = [row for row in rows if row["company"] == company]
        items = "".join(
            "<li><span class='tag'>" + escape(row["csf_function"]) + "</span>"
            + "<h3>" + escape(row["theme"]) + "</h3>"
            + "<p>" + escape(row["observation"]) + "</p>"
            + "<small>Source anchor: “" + escape(row["anchor"]) + "” · "
            + escape(row["verification"]) + " · Review: " + escape(row["review_state"]) + "</small></li>"
            for row in company_rows
        )
        cards.append(
            "<section class='card'><header><h2>" + escape(company) + "</h2>"
            + "<p>FY end " + escape(source["fiscal_year_end"]) + " · Form 10-K · "
            + escape(source["accession"]) + "</p></header><ul>" + items + "</ul>"
            + "<a href='" + escape(source["url"], quote=True) + "'>Open SEC filing ↗</a></section>"
        )
    page = """<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Cyber Disclosure Evidence Monitor</title><style>
:root{font-family:system-ui,sans-serif;color:#172335;background:#f4f7fb}*{box-sizing:border-box}
body{margin:0}main{max-width:1160px;margin:auto;padding:36px 20px 64px}
.eyebrow{text-transform:uppercase;letter-spacing:.16em;color:#2463a6;font-size:12px;font-weight:700}
h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.1;margin:12px 0}h2{margin:0;font-size:1.5rem}
.intro{max-width:760px;line-height:1.6;color:#40536a}.notice{padding:18px 22px;border-left:4px solid #e1a243;background:#fff8ea;line-height:1.55;margin:28px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}.card{background:white;border:1px solid #dce4ec;border-radius:15px;padding:24px;box-shadow:0 6px 24px #182c4410}
.card header p{color:#607086;font-size:13px}.card ul{list-style:none;padding:0}.card li{padding:18px 0;border-top:1px solid #e4eaf1}.card li p{line-height:1.5}.card small{color:#607086;line-height:1.5;display:block}
.tag{font-size:11px;font-weight:700;color:#12605a;background:#e0f5f0;padding:5px 9px;border-radius:50px}h3{font-size:16px;margin:12px 0 6px}a{color:#1462a4;font-weight:700}
footer{margin-top:30px;color:#627389;font-size:13px;line-height:1.5}</style><main>
<div class='eyebrow'>Portfolio prototype · SEC filing evidence</div><h1>Cyber Disclosure Evidence Monitor</h1>
<p class='intro'>Six traceable disclosure observations across three large public cloud companies. Each item is linked to a specific 2025 Form 10-K and checked against a downloaded SEC source file.</p>
<div class='notice'><strong>Interpretation limit:</strong> These are company disclosures, not independent tests. A matched anchor establishes traceability only. All observations remain review candidates; no company security ranking or control-effectiveness claim is made.</div>
<div class='grid'>""" + "".join(cards) + """</div><footer>Microsoft fiscal year ends June 30; Alphabet and Amazon end December 31. Function tags are navigation aids based on NIST CSF 2.0, not assessment results. Source hashes and match counts are in verification_report.json.</footer></main></html>"""
    (output / "comparison.html").write_text(page, encoding="utf-8")
    print(json.dumps({"candidate_count": report["candidate_count"], "matched_once": report["matched_once"], "needs_review": report["needs_review"]}))
    if report["needs_review"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
