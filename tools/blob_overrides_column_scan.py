#!/usr/bin/env python3
"""tools/blob_overrides_column_scan.py -- a read mapper that spreads its stored
blob AFTER the authoritative columns, where the blob can actually carry one of
those column names.

    python tools/blob_overrides_column_scan.py
    python tools/blob_overrides_column_scan.py --list
    python tools/blob_overrides_column_scan.py --baseline

Exit 0 no worse than pinned, 1 a regression, 2 COULD NOT TELL.

── THE DEFECT, MEASURED LIVE ──────────────────────────────────────────────
api/sd-data.js's alf_incidents read built its response as

    Object.assign({ id, resident_id, created_at, recorded_by: <column> }, r.data)

`Object.assign` applies sources LEFT TO RIGHT, so the stored blob -- which is a
copy of the caller's own payload -- overwrote the authoritative column of the
same name. `recorded_by` was also missing from that write's strip list, so a
caller could put it in the payload, have it stored inside `data`, and have it
replace the server-set column on every read.

Driven against the deployed endpoint on ALF-TEST-2026: a write carrying
`recorded_by: 'FORGED-SOMEONE-ELSE'` read back `recorded_by =
'FORGED-SOMEONE-ELSE'` while the session's employee_id was 'sairn-demo-owner'.
The column in the database was CORRECT the whole time; every response was wrong.

NINE GREEN, ABLATION-VERIFIED ARMS MISSED IT, because they asserted the OUTBOUND
request body -- which was always right -- and nothing asserted what came back.

── WHAT MAKES A MAPPER EXPLOITABLE, AND IT IS A PAIR ─────────────────────
The spread order alone is not the defect. `{id: r.entry_id}, r.data` is safe
wherever `id` is in that write path's storedBlob strip list, because the blob
then cannot contain `id` at all. The defect needs BOTH:

  1. the mapper spreads the blob AFTER the columns, AND
  2. at least one of those column names is NOT stripped on write, so the blob
     can carry it.

So this tool pairs each resource's mapper keys against that resource's strip
list. A column in both is SAFE-BY-STRIP; a column in neither is EXPLOITABLE.

── IDENTITY KEYS ARE CALLED OUT SEPARATELY ───────────────────────────────
An exploitable `notes` is a data-integrity bug. An exploitable `recorded_by`,
`administered_by`, `approved_by`, `signed_by`, `verified_by`, `reviewed_by`,
`witnessed_by` or `created_by` is an ATTRIBUTION SPOOF -- the row asserts who did
something and the caller chose it. Those are reported as their own count because
they are not the same finding.

── WHAT IT CANNOT DO ─────────────────────────────────────────────────────
It reads source text. A mapper built through a helper, a spread operator
(`{...cols, ...r.data}`), or a shape assembled across statements is invisible to
it, so the universe is a FLOOR and is reported as one. It also cannot tell
whether an exploitable key MATTERS -- that is per resource and is why the
identity split exists rather than a severity guess.

A RATCHET on docs/blob-override-coverage.json: `exploitable` must never rise.
"""
import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN = os.path.join(REPO, 'docs', 'blob-override-coverage.json')

SCAN = ['api/sd-data.js', 'api/sd-sub-data.js', 'api/sc-ai.js', 'api/law-auth.js']

# Object.assign({ <cols> }, <var>.data)  -- the blob LAST.
BLOB_LAST = re.compile(
    r"""Object\.assign\(\s*\{(?P<cols>[^{}]{0,400})\}\s*,\s*(?P<var>[A-Za-z_$][\w$]*)\.data\s*\)""")
# Object.assign({}, <var>.data, {...}) -- the blob FIRST, the safe shape.
BLOB_FIRST = re.compile(
    r"""Object\.assign\(\s*\{\s*\}\s*,\s*[A-Za-z_$][\w$]*\.data""")
# storedBlob(payload, ['a', 'b', ...])
STRIP = re.compile(
    r"""storedBlob\(\s*[A-Za-z_$][\w$]*\s*,\s*\[(?P<keys>[^\]]*)\]""")
KEY = re.compile(r"""['"]([A-Za-z_$][\w$]*)['"]""")
# The key names on the left-hand side of the mapper literal.
COLKEY = re.compile(r"""(?:^|,)\s*([A-Za-z_$][\w$]*)\s*:""")

IDENTITY = {'recorded_by', 'administered_by', 'approved_by', 'signed_by',
            'verified_by', 'reviewed_by', 'witnessed_by', 'created_by',
            'author', 'filed_by', 'reported_by', 'acknowledged_by',
            'countersigned_by', 'dispensed_by', 'performed_by'}


class CouldNotTell(Exception):
    pass


def stripped_keys(src):
    """Every key any storedBlob() call in this file strips, unioned.

    THE UNION IS DELIBERATELY GENEROUS AND THAT MAKES THIS FAIL-SAFE IN THE
    REPORTING DIRECTION: a key stripped by ANY write in the file is treated as
    stripped everywhere, so the tool UNDER-reports rather than inventing
    findings. Attributing each strip list to its own resource branch needs a
    branch boundary this scanner does not have, and guessing one would be the
    magic-window defect. Stated rather than left for a reader to discover.
    """
    out = set()
    for m in STRIP.finditer(src):
        out |= set(KEY.findall(m.group('keys')))
    return out


def scan():
    results = {}
    for rel in SCAN:
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            continue
        try:
            src = io.open(path, encoding='utf-8', errors='replace').read()
        except OSError as exc:
            raise CouldNotTell('%s could not be read (%s) -- NOT a pass'
                               % (rel, exc))
        stripped = stripped_keys(src)
        last, first = [], len(BLOB_FIRST.findall(src))
        for m in BLOB_LAST.finditer(src):
            line = src.count('\n', 0, m.start()) + 1
            cols = [c for c in COLKEY.findall(m.group('cols'))]
            risky = sorted(set(cols) - stripped)
            last.append({'line': line, 'cols': cols, 'exploitable': risky,
                         'identity': sorted(set(risky) & IDENTITY)})
        results[rel] = {'blob_last': last, 'blob_first': first,
                        'stripped': sorted(stripped)}
    if not results:
        raise CouldNotTell(
            'none of the scanned files exist -- NOTHING was measured. This is '
            'not "no mappers".')
    if not any(r['blob_last'] or r['blob_first'] for r in results.values()):
        raise CouldNotTell(
            'no Object.assign mapper matched anywhere -- the shape moved and '
            'NOTHING was measured. This is NOT "every mapper is safe".')
    return results


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--baseline', action='store_true')
    args = ap.parse_args(argv)

    try:
        res = scan()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2

    total_last = sum(len(r['blob_last']) for r in res.values())
    total_first = sum(r['blob_first'] for r in res.values())
    exploitable = [(rel, m) for rel, r in res.items()
                   for m in r['blob_last'] if m['exploitable']]
    identity = [(rel, m) for rel, m in exploitable if m['identity']]

    print('BLOB-OVERRIDES-COLUMN SCAN')
    print('Object.assign applies sources LEFT TO RIGHT, so a stored blob spread')
    print('AFTER the columns overwrites the authoritative value with the')
    print('caller\'s own payload copy.')
    print('')
    print('  mappers spreading the blob LAST  : %d' % total_last)
    print('  mappers spreading the blob FIRST : %d   (the safe shape)' % total_first)
    print('  of the LAST group, EXPLOITABLE   : %d   (a column key that is NOT'
          % len(exploitable))
    print('                                         stripped on write)')
    print('  *** of those, IDENTITY keys      : %d   (an attribution spoof, not'
          % len(identity))
    print('                                         a data-integrity bug)')
    print('')

    if identity:
        print('  ATTRIBUTION SPOOFS -- the row asserts WHO did something and the')
        print('  caller chooses it:')
        for rel, m in identity:
            print('   %s:%d  %s' % (rel, m['line'], ', '.join(m['identity'])))
        print('')
    if exploitable and args.list:
        print('  EXPLOITABLE (all):')
        for rel, m in exploitable:
            print('   %s:%d  %s' % (rel, m['line'], ', '.join(m['exploitable'])))
        print('')

    print('CHECKED / UNIVERSE: %d mapper(s) examined across %d file(s).'
          % (total_last + total_first, len(res)))
    print('THE UNIVERSE IS A FLOOR: a mapper built through a helper, a spread')
    print('operator, or assembled across statements is invisible to a source')
    print('scan. And the strip list is UNIONED PER FILE, not per resource, so')
    print('this UNDER-reports rather than inventing findings.')
    print('')

    if args.baseline:
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            '_what': 'Pinned blob-overrides-column coverage. Written by '
                     'tools/blob_overrides_column_scan.py --baseline. A ratchet: '
                     '`exploitable` and `identity` must never rise.',
            '_why': 'A read mapper that spreads the stored blob after the '
                    'authoritative columns lets the caller overwrite them. '
                    'Measured live on alf_incidents: recorded_by read back as '
                    'the forged payload value while the column was correct.',
            'blob_last': total_last,
            'blob_first': total_first,
            'exploitable': len(exploitable),
            'identity': len(identity),
            'identity_sites': ['%s:%d' % (rel, m['line']) for rel, m in identity],
        }, indent=2, sort_keys=True) + '\n')
        print('wrote %s' % os.path.relpath(PIN, REPO))
        return 0

    if not os.path.isfile(PIN):
        sys.stderr.write('COULD NOT TELL -- %s does not exist, so NOTHING was '
                         'compared. Run --baseline once.\n'
                         % os.path.relpath(PIN, REPO))
        return 2
    try:
        pin = json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        sys.stderr.write('COULD NOT TELL -- %s will not parse (%s). NOTHING WAS '
                         'COMPARED.\n' % (os.path.relpath(PIN, REPO), e))
        return 2
    was = pin.get('exploitable')
    if not isinstance(was, int):
        sys.stderr.write('COULD NOT TELL -- the pin carries no integer '
                         '`exploitable`.\n')
        return 2
    now = len(exploitable)
    if now > was:
        print('REGRESSION -- exploitable mappers rose from %d to %d.' % (was, now))
        print('Spread the blob FIRST and let the columns overwrite it, or strip')
        print('the key on write. Identity keys need BOTH.')
        return 1
    if now < was:
        print('IMPROVED -- fell from %d to %d. Re-pin:' % (was, now))
        print('   python tools/blob_overrides_column_scan.py --baseline')
        return 0
    print('OK -- no worse than pinned (%d exploitable, %d of them identity).'
          % (was, len(identity)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
