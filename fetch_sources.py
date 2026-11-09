"""Download the bounded SEC source set with an identifying User-Agent."""

import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def main():
    agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not agent or "@" not in agent:
        raise SystemExit("Set SEC_USER_AGENT to a descriptive app name and your contact email.")
    folder = ROOT / "sources"
    folder.mkdir(exist_ok=True)
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    for index, source in enumerate(sources):
        target = folder / source["file"]
        if target.exists():
            print(f"Already present: {target.name}")
            continue
        request = Request(source["url"], headers={"User-Agent": agent})
        with urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}: {source['url']}")
            payload = response.read()
        if len(payload) < 100_000 or b"Item" not in payload:
            raise RuntimeError(f"Unexpected SEC response for {source['company']}")
        target.write_bytes(payload)
        print(f"Downloaded: {target.name} ({len(payload)} bytes)")
        if index < len(sources) - 1:
            time.sleep(1)


if __name__ == "__main__":
    main()
