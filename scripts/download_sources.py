"""Download the public source documents into data/raw/ and check their SHA-256 hashes.

Run: .venv/Scripts/python scripts/download_sources.py

fda.gov rejects requests without browser-like headers, so a normal browser header set is sent.
The warning letter is an HTML page; its letter body is extracted to a .txt file.
A hash mismatch means the publisher changed the file: re-check the parser, rebuild the index,
re-run the evaluation, and record the change (corpus change control).
"""
from __future__ import annotations

import hashlib
import html
import re
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402
from app.ingest.sources import SOURCES  # noqa: E402

EXPECTED_SHA256 = {
    "A22": "284729b4601b748b6b4238c8aef161ad2d3361ee08c9254cb6e9d8a7ef2e6814",
    "A11": "8ec11211ba33bf88ad4e71acc6bf60fd0e7823cfa495b116872e2c287e4aebbb",
    "A11D": "ff831798eb35ee71cd2a860967774750af1f827953acd7613e859cda31e9dcf0",
    "CH4D": "6dbe9d93dc5ebc672d647851970c89300aa43c9966873b8a169b68c3d42fddba",
    "Q9": "3bbc860385b2630372c81eebb82ba74ae643ef383ce94b5e01d26bbd0b9883fb",
    "AIA": "bba630444b3278e881066774002a1d7824308934f49ccfa203e65be43692f55e",
    "FDA-CRED": "62352ed0fc17c07a670ed1381a8cdb1173f1c8988fb6e066da270e7cc72d4aaa",
    "FDA-DP": "f9029092294000e3c677e29753f4bd260907e0d4765cf1cbe795acd7811e4a7d",
    "FDA-WL": "65a0cee9be49bd7959d43fac4873707fd2b5b0c6dde3f1ec998ea8dc017fa9bd",  # of the extracted .txt
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none", "Sec-Fetch-Dest": "document", "Upgrade-Insecure-Requests": "1",
}


def html_letter_to_text(raw: str) -> str:
    body = re.search(r"<article.*?</article>", raw, re.S)
    s = body.group(0) if body else raw
    s = re.sub(r"<(script|style).*?</\1>", "", s, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    return "\n".join(line.strip() for line in s.splitlines() if line.strip())


def main() -> int:
    raw_dir = get_settings().raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    bad = 0
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=120) as client:
        for src in SOURCES:
            target = raw_dir / src.filename
            if not target.exists():
                r = client.get(src.url)
                r.raise_for_status()
                if src.filename.endswith(".txt"):
                    (raw_dir / src.filename.replace(".txt", ".html")).write_bytes(r.content)
                    target.write_text(html_letter_to_text(r.text), encoding="utf-8")
                else:
                    if not r.content.startswith(b"%PDF"):
                        print(f"[x] {src.doc_id}: not a PDF (blocked?)")
                        bad += 1
                        continue
                    target.write_bytes(r.content)
                time.sleep(1)
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            ok = digest == EXPECTED_SHA256.get(src.doc_id)
            bad += not ok
            print(f"[{'ok' if ok else 'CHANGED'}] {src.doc_id:9s} {target.name}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
