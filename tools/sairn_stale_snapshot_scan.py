#!/usr/bin/env python
"""sairn_stale_snapshot_scan.py -- two defect shapes, scanned by shape.

Added 2026-09-02. Every real defect found in a long sweep across the platform
that night came from one of these two shapes, and NO existing tool looks for
either of them.

  1. UTC CALENDAR DERIVATION
     new Date().toISOString().slice(0,10)  reads the UTC calendar date, which
     is one day ahead of a US facility's own date from roughly 8pm Eastern
     onward. Not cosmetic where it lands on a record: sairncare had 17, and
     they dated eMAR medication administrations, controlled-substance counts
     and incident reports a day late every evening, and rolled the billing
     month over on the last evening of every month.
     A BARE new Date().toISOString() storing an INSTANT is CORRECT and is not
     reported -- a timestamp is a moment, not a calendar day.

  2. STALE SNAPSHOT ACROSS AN AWAIT (read -> await -> write)
     Read a collection, await a network call, then write that pre-await
     snapshot back. Anything else that wrote the same store during the round
     trip is silently discarded. Found three real instances that night --
     sairnlegacy confirmReserve (a rejected reservation reverted every other
     change to the merchandise list), sairncode scSaveSettings (a refused
     settings save ate a concurrent one), sairncare reviewPharmacyOrder
     (accepting a pharmacy order dropped a medication administration recorded
     during the round trip).

────────────────────────────────────────────────────────────────────────────
READ THIS BEFORE TRUSTING A COUNT FROM THIS SCRIPT
────────────────────────────────────────────────────────────────────────────
THE RAW HIT COUNT IS NOT A SCORE, AND DRIVING IT TO ZERO IS NOT THE GOAL.

Roughly half the shape-2 hits found by hand that night were CORRECT code. The
script separates what it can (see LIKELY-OK below) and still cannot separate
the rest, because the difference is semantic.

AND A FIXED SITE USUALLY STILL TRIGGERS. The correct fix for shape 2 is to
RE-READ after the await, which leaves the original pre-await read in place --
so the shape is still there and this scanner still sees it. sairncode's
scSaveSettings still appears in this scan after being fixed, for exactly that
reason. This is the same trap tools/key_collision_check.py has: its count went
UP when a stale-snapshot bug was fixed, because the correct pattern needs a
second variable name for the same key. In both tools, a rising number can mean
the code got better.

So: read every hit, decide it individually, and record the verdict. A hit is a
question, not a defect.
"""

import argparse
import glob
import os
import re
import sys

UTC_CAL = re.compile(r"new Date\(\)\.toISOString\(\)\.slice\(\s*0\s*,\s*(?:10|7)\s*\)")
UTC_INSTANT = re.compile(r"new Date\(\)\.toISOString\(\)(?!\s*\.slice)")
LOCAL_HELPER = re.compile(r"function\s+\w*[Ll]ocal(?:Today|Date)\w*\s*\(")
FUNC = re.compile(r"(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(")
# a write to browser storage through any of the wrappers this platform uses
WRITE = re.compile(r"(?:localStorage\.setItem|\bst|\bsvStore|\bscSave)\(\s*['\"]([A-Za-z0-9_]+)['\"]")
# `var x = accessor();` -- a whole-collection read. Also matches a chained
# form, `list = residents().map(...)`, because that is how sairncare's
# saveResident correctly re-reads after its await; requiring a bare `;` here
# put a KNOWN-GOOD function in the wrong bucket on this script's first run.
READ = re.compile(r"(?:var|let|const)?\s*([A-Za-z0-9_$]+)\s*=\s*([A-Za-z0-9_$]+)\(\s*\)\s*(?:[;,)\]]|\.[A-Za-z_])")


def script_blocks(html):
    return re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)


def scan_utc(js):
    """Calendar-date derivations only. Instants are correct and excluded."""
    hits = []
    for m in UTC_CAL.finditer(js):
        hits.append(js[:m.start()].count("\n") + 1)
    return hits, len(UTC_INSTANT.findall(js))


def functions(js):
    marks = [(m.start(), m.group(1)) for m in FUNC.finditer(js)]
    marks.append((len(js), None))
    for i in range(len(marks) - 1):
        yield marks[i][1], marks[i][0], js[marks[i][0]:marks[i + 1][0]]


def scan_stale(js):
    """read -> await -> write, with the mitigated form separated out."""
    hits = []
    for name, offset, body in functions(js):
        if "await" not in body:
            continue
        for w in WRITE.finditer(body):
            before = body[:w.start()]
            if "await" not in before:
                continue                      # write completes before any await -- safe
            last_await = before.rindex("await")
            pre_await = before[:last_await]
            if not READ.search(pre_await):
                continue                      # nothing was snapshotted beforehand
            between = before[last_await:]
            # MITIGATED: something is re-read from a call AFTER the await and
            # before the write. That is the correct fix, and it is separated
            # rather than silently dropped -- a reader may still want to look.
            mitigated = bool(READ.search(between))
            hits.append({
                "function": name,
                "key": w.group(1),
                "line": js[:offset + w.start()].count("\n") + 1,
                "mitigated": mitigated,
            })
    return hits


def scan_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        html = fh.read()
    blocks = script_blocks(html)
    if not blocks:
        return None
    js = "\n".join(blocks)
    utc_lines, instants = scan_utc(js)
    return {
        "path": path,
        "utc": utc_lines,
        "instants": instants,
        "helper": bool(LOCAL_HELPER.search(js)),
        "stale": scan_stale(js),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="files to scan (default: *.html in cwd)")
    ap.add_argument("--show-mitigated", action="store_true",
                    help="also list read-await-write sites that appear to re-read correctly")
    ap.add_argument("--quiet-clean", action="store_true", help="omit files with nothing to report")
    args = ap.parse_args()

    paths = args.paths or sorted(glob.glob("*.html"))
    results = [r for r in (scan_file(p) for p in paths if os.path.isfile(p)) if r]

    total_utc = 0
    total_open = 0
    total_mitigated = 0

    for r in results:
        open_hits = [h for h in r["stale"] if not h["mitigated"]]
        mit_hits = [h for h in r["stale"] if h["mitigated"]]
        total_utc += len(r["utc"])
        total_open += len(open_hits)
        total_mitigated += len(mit_hits)
        if args.quiet_clean and not r["utc"] and not open_hits and not (args.show_mitigated and mit_hits):
            continue

        print("\n== %s" % r["path"])
        if r["utc"]:
            print("   UTC calendar derivations: %d  (local-date helper present: %s)"
                  % (len(r["utc"]), "yes" if r["helper"] else "NO"))
            print("     lines: %s" % ", ".join(str(x) for x in r["utc"][:20]))
            if not r["helper"]:
                print("     no localToday()-style helper in this file -- one must be added, not inlined per site")
        elif not args.quiet_clean:
            print("   UTC calendar derivations: none  (%d bare instant timestamps, which are correct)"
                  % r["instants"])

        if open_hits:
            print("   read -> await -> write, NOT obviously re-read:")
            for h in open_hits:
                print("     line %-6d %-28s writes %s" % (h["line"], h["function"] or "(anonymous)", h["key"]))
        if mit_hits and args.show_mitigated:
            print("   read -> await -> write, appears to re-read after the await (LIKELY OK):")
            for h in mit_hits:
                print("     line %-6d %-28s writes %s" % (h["line"], h["function"] or "(anonymous)", h["key"]))

    print("\n" + "-" * 72)
    print("%d UTC calendar derivations | %d stale-snapshot sites to judge | %d appear already re-read"
          % (total_utc, total_open, total_mitigated))
    print("""
THESE ARE QUESTIONS, NOT DEFECTS. Read each one before acting:

  * A stale-snapshot hit is only a bug if something ELSE writes that same key
    while the await is in flight. Where nothing else can, it is harmless.
  * A FIXED site usually still appears here. The correct fix re-reads after the
    await and leaves the original read in place, so the shape survives it --
    the LIKELY-OK bucket catches most of those, not all. Same trap as
    tools/key_collision_check.py, whose count went UP when a real
    stale-snapshot bug was fixed.
  * A rising number can therefore mean the code got better. Do not treat this
    total as a score, and do not drive it to zero.
  * A bare new Date().toISOString() storing an instant is correct and is never
    reported. Only .slice(0,10) and .slice(0,7) calendar derivations are.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
