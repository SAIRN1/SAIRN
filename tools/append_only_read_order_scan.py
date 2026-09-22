"""Which append-only trail reads in api/sd-data.js come back in an UNDEFINED order.

Run: python tools/append_only_read_order_scan.py
     python tools/append_only_read_order_scan.py --json

REPORT-ONLY. Exits 0 with findings, 2 when it could not run. It is a scan, not
a gate: an unordered read is only a DEFECT when something downstream depends on
the order, and that question needs a person (see THE THIRD COLUMN below).

── WHY THIS EXISTS ─────────────────────────────────────────────────────────
Postgres promises nothing about the order of a SELECT that does not ask for
one, and PostgREST forwards that straight through. On a small table a seq scan
usually returns heap order, so an unordered read LOOKS like insertion order for
the whole of development and stops looking like it the first time the planner
picks an index or a reused page moves a row. Correct in dev, wrong in
production, silent in both.

Six SAIRNcare trail reads carried that defect and were fixed on 2026-09-22
(f9e9628f). The handoff that commissioned that work named THREE; the other
three were found only by enumerating the class. This file is the enumeration,
widened to every app, so the next one is found by running something rather than
by somebody remembering.

── THE POPULATION IS DERIVED TWICE, BECAUSE ONE DERIVATION IS WRONG ────────
"Append-only" is not one fact on this platform and a single test gets it wrong
in both directions:

  BY THE DATABASE'S OWN GUARANTEE -- a `grant select, insert` with no update,
  delete or truncate. Strong, checkable, and MISSES tables that are append-only
  by contract but carry UPDATE because the write uses on_conflict
  merge-duplicates. alf_incidents and alf_op_audits are exactly that.

  BY APPLICATION CONTRACT -- the dispatcher enforces it with
  appendOnlyExisting(res, existingR, '<table>'), which answers 409 rather than
  overwrite. MISSES every table whose append-only-ness lives only in the grant.

Measured: 21 by grant, 5 by contract, 3 in both. Neither is a superset. The
population is the UNION, and the overlap is printed so a reader can see the two
answers rather than a merged number that hides the disagreement.

── THE THIRD COLUMN: AN UNORDERED READ IS NOT AUTOMATICALLY A DEFECT ───────
This is the distinction that makes the output worth reading. Three shapes came
out of the first real run and only one was a finding:

  ORDER-INDEPENDENT BY CONSTRUCTION. rf_certifications and dnt_credentials feed
  latestBy(), which picks a winner per key by comparing recorded_at AND
  breaking ties on entry_id. It never takes "the last row in the list", so the
  order it arrives in cannot change the answer. Those reads are CORRECT
  unordered -- and carry a tiebreaker the SAIRNcare fix does not.

  ORDER-IRRELEVANT. rf_claim_photos selects photo_id alone to build a
  membership set.

  A REAL ORDERING DEFECT. rf_claim_agreements' read branch returns an
  append-only chain of executed/rescinded events to a renderer that maps them
  straight into a table with no sort, and prints created_at sliced to ten
  characters. Server order IS display order and there is none.

So this tool reports WHERE to look. It deliberately does not guess which of the
three a read is, because that needs the consumer read, and a scan that guessed
would be a fabricated verdict in the shape of a measurement.

── WHAT IT CANNOT SEE, PRINTED EVERY RUN RATHER THAN IMPLIED ───────────────
It reads ONE file. A table read by a dedicated endpoint, written and never
read, or reached through a query built in a shape this scanner does not
recognise, comes out as COULD NOT LOCATE A READ -- which is a third state and
is never folded into "ordered". PR 1.11.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip() or '.'
DISPATCHER = os.path.join('api', 'sd-data.js')
SQL_DIR = 'sql'

GRANT_RE = re.compile(
    r'grant\s+([a-z,\s]+?)\s+on\s+(?:table\s+)?public\.(\w+)\s+to\s+service_role', re.I)
CONTRACT_RE = re.compile(r"appendOnlyExisting\(res, existingR, '(\w+)'\)")

# A SINGLE-ROW LOOKUP IS KEYED ON THE ROW'S OWN UNIQUE ID, and ordering one is
# meaningless. A read keyed on a PARENT id (claim_id, job_id, provider_id) is
# still a LIST and ordering it still matters.
#
# THIS LIST WAS WRONG IN ITS FIRST DRAFT AND THE ERROR RAN BOTH WAYS, which is
# why it is spelled out rather than approximated by a `_id=eq.` wildcard. The
# wildcard excluded rf_claim_photos and rf_proposals -- real list reads, keyed
# on a parent -- and hid four reads from the count. Naming the own-key columns
# explicitly means a NEW one is a visible omission rather than a silent
# exclusion, and `agreement_id` was added after exactly that: a single-row
# existence check surfaced as a false finding on the first run.
OWN_KEY_RE = re.compile(
    r'&(entry_id|photo_id|proposal_id|document_id|agreement_id|rule_id|id)=eq\.')


class CouldNotRun(Exception):
    pass


def read_text(path, why):
    """FAIL CLOSED. A file this scan depends on that cannot be read means the
    check DID NOT RUN, named, with a non-zero exit -- never a clean sweep over
    a population it never enumerated. PR 1.11."""
    try:
        return io.open(os.path.join(REPO, path), encoding='utf-8',
                       errors='replace').read()
    except OSError as e:
        raise CouldNotRun('%s could not be read (%s). This scan %s and cannot '
                          'do so without it.' % (path, e.strerror, why))


def code_lines(src):
    """Dispatcher lines with whole-line comments blanked, LINE NUMBERS KEPT.

    Blanked rather than dropped so a reported line number still points at the
    real file. The fix's own headers quote the queries they changed, and a
    raw scan counts that prose as code -- the trap
    api/alf-append-only-fail-closed.test.js already records.
    """
    return ['' if re.match(r'^\s*(//|\*|/\*)', l) else l
            for l in src.split('\n')]


def append_only_tables():
    """(by_grant, by_contract). Two derivations, deliberately not merged here."""
    if not os.path.isdir(os.path.join(REPO, SQL_DIR)):
        raise CouldNotRun('%s/ is not a directory, so the grant half of the '
                          'population cannot be derived.' % SQL_DIR)
    grants = {}
    names = sorted(n for n in os.listdir(os.path.join(REPO, SQL_DIR))
                   if n.endswith('.sql'))
    if not names:
        raise CouldNotRun('%s/ holds no .sql files. An empty population would '
                          'report every app clean.' % SQL_DIR)
    for n in names:
        for m in GRANT_RE.finditer(read_text(os.path.join(SQL_DIR, n),
                                             'derives append-only tables from grants')):
            verbs = {v.strip().lower() for v in m.group(1).split(',') if v.strip()}
            grants.setdefault(m.group(2), set()).update(verbs)
    by_grant = {t for t, v in grants.items()
                if 'select' in v and 'insert' in v
                and not (v & {'update', 'delete', 'truncate'})}
    body = '\n'.join(code_lines(read_text(DISPATCHER, 'derives the contract half')))
    by_contract = set(CONTRACT_RE.findall(body))
    return by_grant, by_contract, len(grants)


def scan():
    by_grant, by_contract, n_granted = append_only_tables()
    population = sorted(by_grant | by_contract)
    if not population:
        raise CouldNotRun('no append-only table matched EITHER derivation. '
                          'That is a broken scanner, not a clean platform.')
    lines = code_lines(read_text(DISPATCHER, 'locates the reads'))

    ordered, unordered, no_read = [], [], []
    for t in population:
        pat = re.compile(r"['\"]" + re.escape(t) + r"\?")
        rows = [(i + 1, '&order=' in l) for i, l in enumerate(lines)
                if pat.search(l) and 'select=' in l and not OWN_KEY_RE.search(l)]
        if not rows:
            no_read.append(t)
            continue
        for n, has in rows:
            (ordered if has else unordered).append({'table': t, 'line': n})
    return {
        'granted_tables_seen': n_granted,
        'by_grant': sorted(by_grant), 'by_contract': sorted(by_contract),
        'both': sorted(by_grant & by_contract),
        'population': population,
        'ordered': ordered, 'unordered': unordered, 'no_read_located': no_read,
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        r = scan()
    except CouldNotRun as e:
        sys.stderr.write('COULD NOT RUN: %s\nNothing was checked. This is NOT '
                         'a pass.\n' % e)
        return 2
    if '--json' in argv:
        print(json.dumps(r, indent=2))
        return 0

    print('APPEND-ONLY TRAIL READS WITHOUT AN ORDER -- a scan, not a gate\n')
    print('  POPULATION, derived twice because one derivation is wrong both ways:')
    print('    service_role grant lines read from sql/ : %d' % r['granted_tables_seen'])
    print('    append-only by DB GRANT                 : %d' % len(r['by_grant']))
    print('    append-only by APPLICATION CONTRACT     : %d' % len(r['by_contract']))
    print('    in BOTH                                 : %d' % len(r['both']))
    print('    UNION -- the population scanned          : %d' % len(r['population']))
    print('    contract-only (a grant test would MISS these): %s'
          % (', '.join(sorted(set(r['by_contract']) - set(r['by_grant']))) or 'none'))
    print('\n  LIST READS IN %s:' % DISPATCHER)
    print('    carry an explicit order= : %d' % len(r['ordered']))
    print('    DO NOT                   : %d' % len(r['unordered']))
    for u in r['unordered']:
        print('      %s:%d  %s' % (DISPATCHER, u['line'], u['table']))
    print('\n  COULD NOT LOCATE A READ IN THIS FILE: %d' % len(r['no_read_located']))
    print('    A THIRD STATE, never folded into "ordered". Written-and-never-read,')
    print('    read by a dedicated endpoint, or built in a shape this scanner does')
    print('    not recognise -- this scan cannot tell those apart.')
    for t in r['no_read_located']:
        print('      %s' % t)
    print('\n  AN UNORDERED READ IS NOT AUTOMATICALLY A DEFECT, and deciding')
    print('  which it is needs the CONSUMER read, not this list. The three')
    print('  shapes the first real run produced:')
    print('    - ORDER-INDEPENDENT: feeds latestBy(), which picks a winner by')
    print('      comparing a timestamp and breaking ties on an id. Correct.')
    print('    - ORDER-IRRELEVANT: selects one column to build a membership set.')
    print('    - A REAL DEFECT: returned to a renderer that maps rows straight')
    print('      into a table with no sort. Server order IS display order.')
    print('  This tool does not guess which. A guessed verdict in the shape of a')
    print('  measurement is worse than no measurement.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
