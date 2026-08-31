# SAIRNsenior — persisted legal sources

**Added 2026-08-31, round 29, because the first 26 rounds' sources were lost.**

Rounds 1–26 fetched 60+ state codes, chapters and PDFs into per-session scratch
directories. Those directories are gone. When round 29 asked *"which worker
classes did we actually read for each state?"*, the source text no longer
existed, so the analysis had to run over the **write-ups** instead — a text
heuristic whose two attribution passes disagreed on roughly a third of states.
**The analysis was weaker than it needed to be for one reason: nobody kept the
sources.**

## What is stored

`<STATE>/<slug>.txt` — **extracted text only**, one file per source document.

`MANIFEST.json` — for each file: the URL, fetch date, HTTP status, content type,
**original byte size and sha256 of the original bytes**, PDF page count, and a
note on what it is.

## What is NOT stored, and why

**The original PDFs and HTML.** They run 7–20 MB each; committing them would
bloat the repo for no analytical gain. Every question this corpus has been asked
so far is a text question — *does this chapter name a second worker class? does
this state use the word "companion"?* — and text is greppable, diffable, and
roughly 3 % of the size.

**Reproducibility is preserved by the manifest, not by the bytes.** The sha256
is of the original download, so any quotation can be re-fetched and checked
against the exact document it came from. If a fetch of the same URL later
produces a different hash, the source changed — which is itself worth knowing.

## Publisher requests are honoured, not routed around

Maryland's COMAR publisher (Open Law Library) prints on every page:

> "Please do not scrape. Instead, bulk download."

**That request is respected.** Individual pages read in the course of research
are what any human reader does and are fine; a sweep of that host is not. Where
a publisher states a constraint it is recorded in the manifest's
`publisher_note` field so the next session inherits the constraint instead of
rediscovering it.

## Adding a source

```
python tools/sairn_source_fetch.py --state NC --slug 10A-NCAC-13J \
    --url "http://reports.oah.state.nc.us/..." --note "home care agency licensure"
python tools/sairn_source_fetch.py --list
```

## Honest limits

- **This begins at round 29.** Rounds 1–26 are not reconstructed, and their
  claims still rest only on the write-ups. Do not read a state's absence here as
  evidence it was never read — read it as *the source was not kept*.
- **Extraction is lossy.** PDF text extraction drops tables and column order;
  HTML extraction drops structure. For anything load-bearing — a quoted duration,
  a numeric threshold — **go back to the URL in the manifest.**
- **A stored file is a snapshot, not the current law.** The fetch date is in the
  manifest. Codes are amended.
