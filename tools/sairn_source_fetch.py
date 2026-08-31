#!/usr/bin/env python
"""sairn_source_fetch.py -- fetch a legal source document and persist its TEXT durably.

WHY THIS EXISTS. Rounds 1-26 of the SAIRNsenior state survey fetched 60+ state
codes, chapters and PDFs into per-session scratch directories. Those directories
are gone. When round 29 needed to ask "which worker classes did we actually read
for each state?", the source text no longer existed, so the analysis had to run
over the WRITE-UPS instead -- a text heuristic whose two attribution passes
disagreed on roughly a third of states. The analysis was weaker than it needed
to be for one reason: nobody kept the sources.

── WHY TEXT AND NOT THE ORIGINAL FILE ──────────────────────────────────────
The originals are 7-20 MB PDFs. Committing them would bloat the repo for no
analytical gain: every question asked of this corpus so far has been a text
question (does this chapter mention a second worker class? does this state use
the word "companion"?). Extracted text is greppable, diffable, and about 3% of
the size.

Reproducibility is preserved in the manifest instead: URL, fetch date, HTTP
status, content-type, original byte size and sha256 of the ORIGINAL bytes. Any
claim made from the text can be re-verified against the source it came from.

── PUBLISHER REQUESTS ARE HONOURED, NOT ROUTED AROUND ──────────────────────
Maryland's COMAR publisher (Open Law Library) prints on every page:
"Please do not scrape. Instead, bulk download." That is a request from the
publisher and this tool does not bulk-fetch that host. Individual pages read
in the course of research are fine and are what a human reader would do; a
sweep is not. `--respect-note` records such a note in the manifest so the next
session sees the constraint instead of rediscovering it.

Usage:
    python tools/sairn_source_fetch.py --state NC --slug 10A-NCAC-13J \\
        --url "http://reports.oah.state.nc.us/..." [--note "..."]
    python tools/sairn_source_fetch.py --list
"""
import argparse, hashlib, io, json, os, re, sys, urllib.request, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "docs", "sources", "sairnsenior")
MANIFEST = os.path.join(BASE, "MANIFEST.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def fetch(url):
    """urllib first; fall back to curl.

    Not belt-and-braces. Arizona's and Mississippi's hosts return 403 to urllib
    and 200 to curl for the identical URL and User-Agent -- the difference is
    below the header layer, so no amount of header-setting in urllib fixes it.
    curl is already the proven client against every host in this survey.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "text/html,application/pdf,*/*"})
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except Exception:
        pass
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        body = os.path.join(td, "body")
        p = subprocess.run(["curl", "-sSL", "-A", UA, "-H", "Accept: text/html,application/pdf,*/*",
                            "-o", body, "-w", "%{http_code}\t%{content_type}", url],
                           capture_output=True, text=True, timeout=180)
        if p.returncode != 0:
            raise RuntimeError(f"curl failed: {p.stderr.strip()[:200]}")
        code, _, ctype = p.stdout.partition("\t")
        with open(body, "rb") as f:
            return int(code), ctype, f.read()


def to_text(raw, ctype):
    """PDF -> pypdf text; anything else treated as HTML/plain."""
    if "pdf" in ctype.lower() or raw[:5] == b"%PDF-":
        import pypdf
        rd = pypdf.PdfReader(io.BytesIO(raw))
        pages = [(p.extract_text() or "") for p in rd.pages]
        return "\n".join(f"<<<PAGE {i+1}>>>\n{t}" for i, t in enumerate(pages)), len(rd.pages)
    h = raw.decode("utf-8", "replace")
    h = re.sub(r"<(script|style).*?</\1>", " ", h, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "\n", h)
    import html as _html
    t = _html.unescape(t)
    return re.sub(r"\n\s*\n+", "\n", t), None


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    return {"note": "Extracted text of legal sources for the SAIRNsenior state "
                    "survey. Originals are not stored; sha256 is of the original "
                    "bytes so any quote can be re-verified.", "entries": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", help="two-letter state code, e.g. NC")
    ap.add_argument("--slug", help="short file name, e.g. 10A-NCAC-13J")
    ap.add_argument("--url")
    ap.add_argument("--note", default="", help="what this is / why it was fetched")
    ap.add_argument("--respect-note", default="", help="publisher constraint to record")
    ap.add_argument("--from-file", default="", help=(
        "store from an already-downloaded local copy instead of refetching. "
        "Needed because a source can stop being available AFTER you read it: "
        "Mississippi's host served the 7 MB Title 15 Pt 16 PDF once on "
        "2026-08-31 and returned 403 to the same URL an hour later. --url is "
        "still recorded, so the entry stays traceable."))
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    man = load_manifest()
    if a.list:
        for e in man["entries"]:
            print(f"{e['state']:3} {e['slug']:34} {e['fetched']}  {e['bytes']:>9}  {e['url'][:70]}")
        print(f"\n{len(man['entries'])} source(s) in {os.path.relpath(BASE, ROOT)}")
        return 0

    if not (a.state and a.slug and a.url):
        ap.error("--state, --slug and --url are required unless --list")

    if a.from_file:
        with open(a.from_file, "rb") as f:
            raw = f.read()
        status, ctype = 200, ("application/pdf" if raw[:5] == b"%PDF-" else "text/html")
    else:
        status, ctype, raw = fetch(a.url)
        if status != 200:
            print(f"HTTP {status} -- not stored", file=sys.stderr)
            return 1
    text, pages = to_text(raw, ctype)

    d = os.path.join(BASE, a.state.upper())
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, a.slug + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    man["entries"] = [e for e in man["entries"]
                      if not (e["state"] == a.state.upper() and e["slug"] == a.slug)]
    man["entries"].append({
        "state": a.state.upper(), "slug": a.slug, "url": a.url,
        "fetched": datetime.date.today().isoformat(),
        "http": status, "content_type": ctype, "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "pdf_pages": pages, "text_chars": len(text),
        "note": a.note, "publisher_note": a.respect_note,
    })
    man["entries"].sort(key=lambda e: (e["state"], e["slug"]))
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
        f.write("\n")

    print(f"stored {os.path.relpath(path, ROOT)}  "
          f"({len(raw):,} bytes source -> {len(text):,} chars text"
          + (f", {pages} pages" if pages else "") + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
