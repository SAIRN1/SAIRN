#!/usr/bin/env python
"""Runs the CRITERIA_VERSION 3 editor pass (bare `:NNNN` implied-file
citations) over this log's last 30 entries, per direct instruction.

WHY A DRIVER, NOT A BARE CLI CALL: hover_editor_review.py's --default-file
is ONE file for the WHOLE report, matching its designed shape (one register
CELL = one resource = one file). This log's own entries are messier -- a
single entry can cite bare `:NNNN` line numbers against SEVERAL files in one
paragraph (seq 676: `:39431` is stonedesk.html, `:1627-1631` is
api/sd-data.js, `:218` is api/_lib/job-risk.js, all in one summary). Running
the whole entry once against a single default-file would silently mis-check
every implied citation that belongs to a DIFFERENT file as ANCHOR-ABSENT --
a false finding manufactured by this driver's own guess, not a real one.

METHOD: for each entry containing >=1 bare implied-file citation, take its
own declared `source_shas` keys (the files IT SAYS it read that round) as the
candidate-file set -- never guessed, always the entry's own structured
field. Run the editor pass once per candidate file. A citation is CHECKED
CLEAN if it resolves OK or DRIFT against AT LEAST ONE candidate (the file it
actually belongs to); it is FLAGGED only if every candidate run reports it
FINDING or CANNOT-CHECK, i.e. no file the entry itself named can account for
it. An entry with an empty source_shas is reported COULD NOT RESOLVE
CANDIDATES, a named third state, never silently skipped or silently passed.

universe = entries in the last 30 with >=1 bare implied-file citation.
checked = of those, entries where every citation resolved against >=1
candidate (clean or drift, never a bare guess).
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "hover-audit-log.jsonl"
REPO = Path(r"C:\Users\marsh\Documents\SAIRN-hover")

IMPLIED = re.compile(r"(?<![\w./])\:(\d{1,6})(?:-(\d{1,6}))?\b")


def last_n_entries(n):
    with open(LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    return [json.loads(l) for l in lines[-n:]]


def run_review(text, default_file):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                      encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        args = [sys.executable, str(HERE / "hover_editor_review.py"),
                "--report", path, "--repo", str(REPO), "-v"]
        if default_file:
            args += ["--default-file", default_file]
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout
    finally:
        Path(path).unlink(missing_ok=True)


ROW = re.compile(r"^\[(OK|DRIFT|SHALLOW|CANNOT|FINDING)\s+([A-Za-z-]+)\]\s+(.*)$")
# check_fileline() (hover_editor_review.py:161-233) ALWAYS labels an implied
# row "IMPLIED-FILE <path>:<l1>" -- only the START line, even when the
# original citation was a range (`:1627-1631`) -- l2 only widens the
# file-length bound check, it never appears in any printed label. Keying on
# the START LINE, not the full range string, is therefore what the tool's
# own output actually supports; matching on the full "1627-1631" string
# against a label that only ever says "1627" silently failed to match
# ANYTHING and made every implied citation look unresolved on the first cut
# of this driver -- caught by hand-verifying one entry's raw output against
# what the summary counters claimed, not trusted from the summary alone.
IMPLIED_ROW = re.compile(r"IMPLIED-FILE\s+(\S+):(\d+)")


def classify_implied(stdout, only_path=None):
    """{start_line(int) -> best row kind seen}, parsed from the tool's own
    'IMPLIED-FILE <path>:<line>' label (run with -v so OK rows are not
    suppressed -- without it a clean citation prints nothing and would be
    silently missed here). only_path restricts to rows about that exact
    default-file, so a citation the tool resolved against a DIFFERENT
    sentence's path (still possible even under one --default-file, since
    every implied match in the report is checked against the SAME
    default-file) is not confused with one about this candidate."""
    rank = {"OK": 0, "DRIFT": 1, "SHALLOW": 2, "CANNOT": 3, "FINDING": 4}
    kinds = {}
    for line in stdout.splitlines():
        m = ROW.match(line.strip())
        if not m:
            continue
        kind, _cls, detail = m.group(1), m.group(2), m.group(3)
        im = IMPLIED_ROW.search(detail)
        if not im:
            continue
        path, l1 = im.group(1), int(im.group(2))
        if only_path and path != only_path:
            continue
        if l1 not in kinds or rank[kind] < rank[kinds[l1]]:
            kinds[l1] = kind
    return kinds


def main():
    entries = last_n_entries(30)
    universe = []
    for e in entries:
        starts = sorted({int(m.group(1)) for m in IMPLIED.finditer(e.get("summary", ""))})
        if starts:
            universe.append((e, starts))

    print("UNIVERSE: %d of last %d entries carry >=1 bare implied-file citation "
          "(seq %d-%d)" % (len(universe), len(entries), entries[0]["seq"], entries[-1]["seq"]))

    rank = {"OK": 0, "DRIFT": 1, "SHALLOW": 2, "CANNOT": 3, "FINDING": 4}
    checked = 0
    flagged = []
    unresolved_candidates = []
    for e, starts in universe:
        candidates = sorted((e.get("source_shas") or {}).keys())
        if not candidates:
            unresolved_candidates.append((e["seq"], starts))
            continue
        best = {}
        for cand in candidates:
            rc, out = run_review(e["summary"], cand)
            for l1, kind in classify_implied(out, only_path=cand).items():
                if l1 not in best or rank[kind] < rank[best[l1]]:
                    best[l1] = kind
        still_bad = [s for s in starts if best.get(s, "FINDING") in ("FINDING", "CANNOT")]
        if still_bad:
            flagged.append((e["seq"], still_bad, candidates, best))
        else:
            checked += 1

    print("CHECKED CLEAN (every implied citation resolved OK/DRIFT/SHALLOW "
          "against >=1 of the entry's own declared files): %d of %d" %
          (checked, len(universe)))

    if unresolved_candidates:
        print("\nCOULD NOT RESOLVE CANDIDATES (entry has implied citations but "
              "an empty source_shas -- a third state, not silently passed):")
        for seq, starts in unresolved_candidates:
            print("  seq %d: %s" % (seq, [":%d" % s for s in starts]))

    if flagged:
        print("\nFLAGGED (no declared file accounts for these citations):")
        for seq, starts, candidates, best in flagged:
            print("  seq %d: %s against candidates %s -> %s" %
                  (seq, [":%d" % s for s in starts], candidates,
                   {(":%d" % s): best.get(s) for s in starts}))
    else:
        print("\nNo citation flagged.")


if __name__ == "__main__":
    main()
