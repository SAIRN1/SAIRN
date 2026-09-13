"""Can this write path be retried, and does it check a key against DURABLE storage?

    python tools/idempotency_check.py
    python tools/idempotency_check.py --fixtures    # the blind lock alone
    python tools/idempotency_check.py --json

── THE DEFECT SHAPE, FROM THIS PLATFORM'S OWN RECORD ─────────────────────
A write that can be retried and does not check a key processes the same
business event twice. The dangerous variant is not the missing key -- it is a
key checked against an IN-MEMORY map: it looks like idempotence, passes review,
and fails the moment there are two processes, or one process restarted. That is
the shape of this session's suite-lock race, where a second run snapshotted a
first run's in-flight mutation as its baseline because the guard lived in
memory rather than on disk.

── THE BLIND LOCK ────────────────────────────────────────────────────────
Pass/fail is decided against SYNTHETIC fixtures below and this tool REFUSES TO
JUDGE A SINGLE REAL FILE until they all classify as written. Criteria tuned
against the real corpus would pass by construction.

THE POSITIVE FIXTURE IS REAL, NOT SYNTHETIC, on Michael's instruction:
`api/ledger.js` is idempotent on the business event (source_kind + source_id),
checked against durable storage BEFORE writing anything, and it REFUSES rather
than posting unchecked when the check itself fails. Using the real thing means
the criteria are calibrated against an implementation somebody defended, not
against a sample written to be recognised.

THE NEGATIVE FIXTURE STAYS SYNTHETIC, and that is disclosed rather than
implied: there is no in-memory-keyed write path on this platform to point at.
The fixture is a constructed example, so this checker has never been shown to
catch a REAL instance of the shape it most wants to catch.

── WHAT IT CANNOT SEE, said here rather than discovered later ───────────
  * whether a retry actually happens. It reads the code, not the traffic;
  * a key checked in a database CONSTRAINT rather than in the handler -- a
    unique index is durable idempotence and this would report the handler as
    unguarded. Counted separately as UNIQUE-CONSTRAINT-MAYBE, never as a
    finding;
  * writes outside api/. The client push helpers retry and are not read here.

Exit 0 when every retryable write is guarded or declared, 1 when one is not,
2 when the fixtures fail -- which means nothing real was judged.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRITERIA_VERSION = '2026-09-13.1'

# A caller-supplied key the handler reads. Names seen in real handlers here.
KEY_NAMES = r'(source_id|source_kind|idempotency[_-]?key|request_id|client_token|order_id|external_id)'
# Evidence the key is checked against something that OUTLIVES the process.
DURABLE = r'(fetch\(\s*rest\(|await\s+\w*[Ff]etch|select=|\.from\(|SELECT\s)'
# Evidence it is checked against something that does NOT outlive the process.
# NARROWED after the lock caught the first version: it matched any `new Set(`,
# and api/ledger.js -- the REAL positive fixture -- has one at line 312 to
# dedupe ids in a RESPONSE. That read a defended, correct implementation as the
# dangerous shape. A criteria correction against a real implementation, declared
# here rather than made quietly.
#
# The shape that actually bites is a key store at MODULE SCOPE (it outlives the
# request, which is exactly why it looks like it works) that is then CONSULTED
# with a key. Both halves are required.
IN_MEMORY_STORE = re.compile(
    r'^(?:const|let|var)\s+(\w+)\s*=\s*(?:new\s+(?:Map|Set)\(|\{\s*\})', re.M)


def analyse(rel, src):
    code = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))
    writes = len(re.findall(r"method:\s*'(?:POST|PATCH|PUT)'", code))
    if not writes:
        return None
    reads_key = bool(re.search(KEY_NAMES, code))
    durable = bool(re.search(DURABLE, code))
    in_mem = False
    for m in IN_MEMORY_STORE.finditer(code):
        name = m.group(1)
        # ... and consulted with a caller key. A module-level Map that nothing
        # looks a key up in is a cache, not a false idempotence guard.
        # THE KEY MUST BE IN THE LOOKUP ITSELF, not merely somewhere in the
        # file. Narrowed a THIRD time after the lock and a hand check caught
        # two false positives in a row: api/ledger.js's response-dedupe Set,
        # then api/sd-data.js's BOUNDARY_LOGGED, a LOG-dedupe store consulted
        # with `seenKey`. In a 10,000-line file some key name always appears
        # somewhere, so 'key present in file' is not evidence of anything.
        consulted = re.search(chr(92) + 'b' + re.escape(name) +
                              r'\s*\.\s*(?:has|get|includes)\s*\(\s*([^)]{0,80})\)', code)
        if consulted and re.search(KEY_NAMES, consulted.group(1)):
            in_mem = True
            break
    unique_idx = bool(re.search(r'on_conflict=|ON CONFLICT|unique\s*\(', code, re.I))

    if reads_key and durable and not in_mem:
        verdict = 'GUARDED-DURABLE'
    elif reads_key and in_mem:
        verdict = 'GUARDED-IN-MEMORY'          # the dangerous one
    elif unique_idx:
        verdict = 'UNIQUE-CONSTRAINT-MAYBE'    # not a finding; not proof either
    else:
        verdict = 'UNGUARDED'
    return {'file': rel, 'writes': writes, 'verdict': verdict,
            'reads_key': reads_key, 'durable_check': durable,
            'in_memory_check': in_mem, 'upsert_or_unique': unique_idx}


# ── FIXTURES: hand-decided. The POSITIVE one is the real api/ledger.js.
SYNTHETIC = [
    ('in-memory key store is the DANGEROUS shape and must be named as such',
     "const seen = new Map();\nif (seen.has(payload.idempotency_key)) return;\n"
     "await fetch(rest('t'), { method: 'POST' });",
     'GUARDED-IN-MEMORY'),
    ('a retryable write with no key at all is UNGUARDED',
     "await fetch('https://x/y', { method: 'POST', body: b });",
     'UNGUARDED'),
    ('CONTROL: a file with no write at all is not judged',
     "const x = await fetch(rest('t?select=id'));", None),
]


def run_fixtures():
    bad = []
    for name, src, want in SYNTHETIC:
        got = analyse('fixture.js', src)
        got_v = got['verdict'] if got else None
        if got_v != want:
            bad.append((name, want, got_v))
    # The real positive: api/ledger.js must read as durably guarded.
    p = os.path.join(REPO, 'api', 'ledger.js')
    if not os.path.exists(p):
        bad.append(('api/ledger.js is missing -- the real positive fixture is gone',
                    'GUARDED-DURABLE', None))
    else:
        got = analyse('api/ledger.js', io.open(p, encoding='utf-8', errors='replace').read())
        if not got or got['verdict'] != 'GUARDED-DURABLE':
            bad.append(('the REAL positive fixture api/ledger.js must read as durably '
                        'guarded -- it checks source_kind+source_id before writing',
                        'GUARDED-DURABLE', got['verdict'] if got else None))
    return bad


def main(argv):
    bad = run_fixtures()
    print('IDEMPOTENCY CHECK -- criteria %s, report only' % CRITERIA_VERSION)
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING REAL WAS JUDGED.')
        for n, w, g in bad:
            print('     expected %-22s got %-22s %s' % (w, g, n))
        return 2
    print('  blind lock: %d/%d fixtures correct -- %d synthetic plus the REAL '
          'api/ledger.js' % (len(SYNTHETIC) + 1, len(SYNTHETIC) + 1, len(SYNTHETIC)))
    if '--fixtures' in argv:
        return 0

    rows = []
    for root, _dirs, files in os.walk(os.path.join(REPO, 'api')):
        for f in sorted(files):
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO).replace(os.sep, '/')
            a = analyse(rel, io.open(p, encoding='utf-8', errors='replace').read())
            if a:
                rows.append(a)

    by = {}
    for r in rows:
        by.setdefault(r['verdict'], []).append(r)

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'files': rows}, indent=1))
        return 1 if by.get('UNGUARDED') or by.get('GUARDED-IN-MEMORY') else 0

    tot = sum(r['writes'] for r in rows)
    print('  files with a mutating fetch: %d   mutating calls: %d' % (len(rows), tot))
    for v in ('GUARDED-IN-MEMORY', 'UNGUARDED', 'UNIQUE-CONSTRAINT-MAYBE',
              'GUARDED-DURABLE'):
        n = len(by.get(v, []))
        w = sum(r['writes'] for r in by.get(v, []))
        note = {'GUARDED-IN-MEMORY': '  <- looks idempotent, is not across processes',
                'UNGUARDED': '  <- a retry processes the event twice',
                'UNIQUE-CONSTRAINT-MAYBE': '  <- upsert/unique may carry it; NOT proof',
                'GUARDED-DURABLE': ''}[v]
        print('    %-24s %3d file(s), %4d write(s)%s' % (v, n, w, note))
    print('')
    print('  THE NEGATIVE FIXTURE IS SYNTHETIC AND THAT IS A REAL LIMIT: no')
    print('  in-memory-keyed write path exists on this platform to point at, so')
    print('  this checker has never caught a real instance of the shape it most')
    print('  wants to catch. A zero in that row is not yet evidence.')
    for r in by.get('GUARDED-IN-MEMORY', []) + by.get('UNGUARDED', [])[:15]:
        print('    %-46s %s (%d write(s))' % (r['file'], r['verdict'], r['writes']))
    if len(by.get('UNGUARDED', [])) > 15:
        print('    ... and %d more UNGUARDED (--json for all)'
              % (len(by['UNGUARDED']) - 15))
    return 1 if (by.get('UNGUARDED') or by.get('GUARDED-IN-MEMORY')) else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
