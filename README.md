# Cyber Disclosure Evidence Monitor

An evidence-first GRC portfolio project comparing what Microsoft, Alphabet, and Amazon disclose about cybersecurity governance in their 2025 Form 10-Ks. The tool checks short text anchors against locally stored SEC filings and exports a reviewable register. It does **not** certify controls, infer security maturity, or rank the companies.

## Run

```powershell
$env:SEC_USER_AGENT = "YourResearchApp/1.0 your-real-email@example.com"
python fetch_sources.py
python verify_evidence.py
```

The verification script produces `output/evidence_register.csv`, `output/verification_report.json`, and `output/comparison.html`. The scripts use only the Python standard library. Replace the example contact address with your own before fetching. Source HTML files are downloaded from the SEC and are kept with SHA-256 hashes in the report; they are not intended for redistribution through a public repository. `sources/` is ignored by Git.

## Scope and interpretation

- Sample: one 2025 annual Form 10-K per company. Microsoft has a June 30 fiscal year end; Alphabet and Amazon have December 31 fiscal year ends. This is a comparison of disclosed statements, not identical time windows.
- The register uses short anchors to verify that each paraphrased observation is traceable to a filing. A reviewer must still examine context before marking an observation approved.
- NIST CSF 2.0 function tags are a navigation aid, not a control assessment or compliance result.
- An item not observed in these filings means only that this bounded sample did not establish it.
- SEC Item 106 describes annual cybersecurity risk management, strategy, and governance disclosure. A future phase will add bounded Form 8-K Item 1.05 event tracking with materiality-determination dates kept distinct from discovery dates.

## Source policy

Primary filings: SEC EDGAR. Framework: NIST CSF 2.0. See `sources.json` and `evidence.json` for accession-specific URLs. The SEC's disclosure guidance is at https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/cybersecurity-risk-management-strategy-governance-incident-disclosure and NIST CSF 2.0 at https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20.

## Next build phases

1. Expand the register to all Item 1C themes with reviewer decisions and counterevidence notes.
2. Ingest quarterly and annual filings through the SEC submissions API, preserving revisions and accessions.
3. Add a local review UI with source snippets, uncertainty flags, and export history.
4. Add an optional AI extraction candidate lane evaluated against hand-reviewed examples. AI output never becomes a finding without review.
