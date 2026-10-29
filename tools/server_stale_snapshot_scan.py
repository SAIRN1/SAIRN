#!/usr/bin/env python
"""server_stale_snapshot_scan.py -- S2: the SERVER-SIDE read-await-write shape.

hank b66. tools/sairn_stale_snapshot_scan.py finds the CLIENT shape (a
browser-store read, an await, a write of the stale array). Its arm is blind to
server code: a planted server-side case went undetected in b63, so its zero on
api/ was not evidence of anything. This is the server arm.

THE SHAPE, inside one function body:
    1. a READ from the database  -- fetch(...) with no write method, or a
       PostgREST GET, whose result is parsed (`await r.json()`);
    2. at least one further `await` after it;
    3. a WRITE -- fetch(..., { method: 'PATCH' | 'PUT' | 'POST' }) -- to a URL
       or body built from what was read;
    4. and NO concurrency guard on that write: no `If-Match`, no
       `version=eq.` / `updated_at=eq.` / `etag` condition, no `rpc/` call
       (an atomic server function), no `Prefer: ...resolution=` upsert.

That is a lost-update candidate: two requests read the same row, both write,
and the second silently overwrites the first.

THESE ARE QUESTIONS, NOT DEFECTS, the same rule as the client scanner. A hit is
a bug only if two requests can interleave on the same row. A per-user row, a
single-writer job, or an append-only insert may be fine. Do not drive the count
to zero.

CLI:
    python tools/server_stale_snapshot_scan.py [paths...]   # default api/**/*.js
    python tools/server_stale_snapshot_scan.py --selftest   # fixtures, both directions
Exit: 0 scanned (hits are questions); 2 COULD NOT RUN (nothing scanned);
1 selftest failure.
"""
import glob
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNC = re.compile(r"(?:async\s+function\s*[A-Za-z0-9_$]*\s*\([^)]*\)|async\s*\([^)]*\)\s*=>|async\s+[A-Za-z0-9_$]+\s*=>)\s*\{")
READ = re.compile(r"=\s*await\s+[A-Za-z0-9_$.]*fetch\s*\((?:(?!method\s*:\s*['\"](?:PATCH|PUT|POST|DELETE)).){0,400}?\)", re.S)
JSON = re.compile(r"await\s+[A-Za-z0-9_$]+\.json\s*\(\s*\)")
WRITE = re.compile(r"fetch\s*\((?:(?!\bfetch\s*\().){0,600}?method\s*:\s*['\"](PATCH|PUT|POST)['\"]", re.S)
GUARD = re.compile(r"If-Match|version=eq\.|updated_at=eq\.|etag|rpc/|resolution=|on_conflict=|row_version|\.lock\b|advisory", re.I)


def strip_comments(js):
    js = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), js, flags=re.S)
    return re.sub(r"(^|[^:'\"\\])//[^\n]*", r"\1", js)


def bodies(js):
    """(start_offset, body_text) for every async function, by brace matching."""
    out = []
    for m in FUNC.finditer(js):
        i, depth = m.end() - 1, 0
        for j in range(i, len(js)):
            c = js[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out.append((i, js[i:j + 1]))
                    break
    return out


def scan_text(js):
    """Line numbers of candidate sites. Pure."""
    js = strip_comments(js)
    hits = set()
    for start, body in bodies(js):
        for r in READ.finditer(body):
            after = body[r.end():]
            jm = JSON.search(after)
            if not jm:
                continue
            w = WRITE.search(after, jm.end())
            if not w:
                continue
            # The await that matters comes AFTER the parse: `await r.json()`
            # itself is not a window in which another request can write.
            between = after[jm.end():w.start()]
            if "await" not in between:
                continue
            window = after[w.start():w.end() + 400]
            if GUARD.search(window):
                continue
            hits.add(js.count("\n", 0, start + r.end() + w.start()) + 1)
            break
    return sorted(hits)


FIX_POS = """async function bump(id) {
  const r = await fetch(rest('t?id=eq.' + id), { headers: h });
  const rows = await r.json();
  const n = rows[0].count + 1;
  await audit(id);
  await fetch(rest('t?id=eq.' + id), { method: 'PATCH', headers: h, body: JSON.stringify({ count: n }) });
}"""
FIX_GUARDED = FIX_POS.replace("rest('t?id=eq.' + id), { method", "rest('t?id=eq.' + id + '&version=eq.' + rows[0].version), { method")
FIX_RPC = """async function bump(id) {
  const r = await fetch(rest('t?id=eq.' + id), { headers: h });
  const rows = await r.json();
  await audit(id);
  await fetch(rest('rpc/bump_count'), { method: 'POST', headers: h, body: JSON.stringify({ id: id }) });
}"""
FIX_NOWRITE = """async function show(id) {
  const r = await fetch(rest('t?id=eq.' + id), { headers: h });
  const rows = await r.json();
  await audit(id);
  return rows;
}"""
FIX_NOAWAIT = """async function bump(id) {
  const r = await fetch(rest('t?id=eq.' + id), { headers: h });
  const rows = await r.json();
  fetch(rest('t?id=eq.' + id), { method: 'PATCH', headers: h, body: JSON.stringify({ count: rows[0].count + 1 }) });
}"""
FIX_ARROW = FIX_POS.replace("async function bump(id) {", "const bump = async (id) => {")
FIX_COMMENTED = FIX_POS.replace("  await fetch(rest('t?id=eq.' + id), { method: 'PATCH'", "  // await fetch(rest('t?id=eq.' + id), { method: 'PATCH'")


def selftest():
    arms = [
        ("POSITIVE: read, json, await, unguarded PATCH is reported", scan_text(FIX_POS) != []),
        ("...and the reported line is the write's", scan_text(FIX_POS) == [6]),
        ("ARROW FUNCTIONS are scanned too", scan_text(FIX_ARROW) != []),
        ("NEGATIVE: a version=eq. condition on the write is a guard", scan_text(FIX_GUARDED) == []),
        ("NEGATIVE: an rpc/ call is an atomic server function", scan_text(FIX_RPC) == []),
        ("NEGATIVE: a read with no write is not the shape", scan_text(FIX_NOWRITE) == []),
        ("NEGATIVE: no await between read and write is not the shape", scan_text(FIX_NOAWAIT) == []),
        ("NEGATIVE: a commented-out write is not code", scan_text(FIX_COMMENTED) == []),
    ]
    bad = 0
    for name, ok in arms:
        print("  %s %s" % ("ok  " if ok else "FAIL", name))
        bad += 0 if ok else 1
    print("  %d/%d arms" % (len(arms) - bad, len(arms)))
    return bad


def main(argv):
    if "--selftest" in argv:
        print("SERVER STALE-SNAPSHOT SCAN -- selftest")
        return 1 if selftest() else 0
    paths = [a for a in argv if not a.startswith("--")] or sorted(
        p for p in glob.glob(os.path.join(REPO, "api", "**", "*.js"), recursive=True) if not p.endswith(".test.js"))
    scanned, total = 0, 0
    for p in paths:
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            js = fh.read()
        scanned += 1
        hits = scan_text(js)
        if hits:
            total += len(hits)
            print("== %s\n   read-await-write sites to judge: %s" % (os.path.relpath(p, REPO), ", ".join(map(str, hits))))
    print("-" * 72)
    print("%d file(s) scanned | %d read-await-write site(s) to judge" % (scanned, total))
    if not scanned:
        print("ZERO files were scanned -- COULD NOT RUN, not a pass.")
        return 2
    print("QUESTIONS, NOT DEFECTS: a site is a lost update only if two requests can write the same row concurrently.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
