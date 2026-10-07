#!/usr/bin/env python
# OWNER-INTENDED BARE-RUN WRITER. A bare run of this tool WRITES, and that is
# its interface rather than a defect: see tools/bare_run_writers.py for the
# path it writes and why. tools/bare_run_write_check.py reads that list and
# does not flag the tools on it. If this tool stops being a generator, take it
# off the list in the same change -- an allowlist nobody re-derives is how a
# real defect hides inside a convention.
"""SUPERSEDED 2026-08-29 -- DO NOT BUILD ON THIS. Use tools/sairn_load_state_check.py.

>>> CC / anyone extending load-state checking: read this before adding an app. <<<

Two load-state gates were built the same night by two sessions working in
parallel -- this generated-SQL one, and a live-endpoint one. Michael's call on
2026-08-29 was to standardise on ONE, and the deciding factor was staleness:

    A GENERATED FILE MUST BE REGENERATED AFTER EVERY SEED EDIT. If someone
    forgets, the gate quietly checks yesterday's expectations and reports
    clean. That is the same silent-failure shape this whole gate exists to
    catch, reintroduced inside the catcher.

tools/sairn_load_state_check.py reads the seed files at RUN TIME, so it cannot
go stale, needs only a licence key (no Supabase editor, so it can gate a
pre-push step from any clone), covers holiday CALENDARS as well as rules, and
reports MISSING and EXTRA rather than only STALE. It now covers SAIRNlaw plus
the four tables this file reached -- alf_compliance_rules, alf_payer_rules,
dnt_cred_rules, rf_cert_rules, rf_contingency_rules -- via the new read-only
api/reference-fingerprint.js:

    python tools/sairn_load_state_check.py --app sairncare
    python tools/sairn_load_state_check.py --app sairndental
    python tools/sairn_load_state_check.py --app sairnroofing

THIS FILE IS KEPT, NOT DELETED, because three of its findings are load-bearing
and were carried into the replacement rather than rediscovered later:

  1. PROMOTED COLUMNS. Only SAIRNlaw keeps everything in `data`. rf_contingency_
     rules keeps `count` and `unit` as real columns; a fingerprint over `data`
     alone would miss a wrong count entirely. The replacement hashes the whole
     row for exactly this reason.
  2. THE TWO SERVER NORMALISATIONS, read out of api/sd-data.js's write branches
     rather than assumed: `state` is uppercased, `status` defaults to 'active'.
     Miss them and the gate cries wolf on its first run and gets switched off.
  3. sc_anesthesia_base_units HAS NO SEED FILE. No gate can be built for it --
     but CORRECTED 2026-08-29, the absence is NOT the finding, and both this
     file and the replacement said it was before anyone checked. SAIRNcode's own
     build record (SAIRN-ACTIVE-WORK-cc.md, 2026-08-20) says that table is
     "empty-by-default, Source-required": the coder enters base units with their
     own citation and the app says "not in your reference table yet" rather than
     inventing one. It is CUSTOMER-OWNED data, correctly seedless, and its
     migration is queued and unrun so there is no live table either. Writing a
     platform seed for it would push unverified values into a table built to
     hold only what the practice verified -- the fabricated-data class, committed
     by the tool meant to prevent it.

ONE DEFECT, recorded so it is not reintroduced anywhere: INERT_COLUMNS below is
correct, but the SAIRNlaw-specific predecessor's INERT_KEYS listed `computation`
among the keys that cannot change a computed result. It selects the counting
standard -- frcp_6a vs fl_rgpja_2514 vs ok_12_2006 -- and a rule whose standard
drifted would have passed that gate clean. The subtractive principle stated
below is right; the hand-picked exception list is where it went wrong.

The generated .sql gates this produced have been removed. Regenerating them
would put two gates back.

── ORIGINAL HEADER FOLLOWS ─────────────────────────────────────────────────

Generate load-state gates for every app whose reference content is seeded per licence.

WHY THIS EXISTS
---------------
A rule is corrected in a seed, the commit lands, and a live licence keeps
serving the old value indefinitely. That happened on LAW-PINNACLE-2026 -- federal
answer deadlines computed three days late for a day after the fix -- and it was
found by accident. `version` cannot detect it: every seed rule is version 1,
including the two a correction changed.

tools/sairnlaw_build_load_gate.py solved it for SAIRNlaw. This generalises the
same mechanism to the other apps with the identical seed-to-per-licence-table
shape, and it is deliberately NOT a glob swap, because those tables are not
shaped like law_deadline_rules.

WHAT IS DIFFERENT ABOUT THE OTHER APPS
--------------------------------------
law_deadline_rules is (license_hash, entry_id, data jsonb) -- all compute content
lives in one blob. The others carry PROMOTED COLUMNS that hold compute-relevant
content directly: rf_contingency_rules keeps `count` and `unit` as real columns,
dnt_cred_rules keeps `state` / `requirement_type` / `role`, and so on. A gate
that compared only `data` would miss a wrong `count` or `unit` entirely -- the
exact defect class this exists to catch.

So both sides are built SUBTRACTIVELY from the whole row:

    live     = to_jsonb(row) - bookkeeping columns
    expected = seed rule     - its id field

`to_jsonb(row)` names no columns, so a compute column added later is compared by
default rather than silently skipped. Same reasoning as the SAIRNlaw gate, one
level up: there is no column list here that can go stale.

TWO SERVER NORMALISATIONS THE GATE MUST MIRROR
----------------------------------------------
Read from every write branch in api/sd-data.js, not assumed:
  * `state` is uppercased server-side  -> String(payload.state).trim().toUpperCase()
  * `status` defaults to 'active'      -> payload.status || 'active'
Without mirroring these the gate reports false STALE on every row whose seed
omits status (alf_payer_rules does exactly that) -- a gate that cries wolf on
its first run gets switched off, which is worse than not having one.

NOT COVERED, AND WHY
--------------------
sc_anesthesia_base_units (SAIRNcode) has the right table shape but NO SEED FILE
anywhere in the repo. There is nothing to compare a live licence against, so no
gate can be built for it. That absence is itself the finding: it is per-licence
reference content with no source of truth in version control.
"""
import glob
import io
import json
import os
import sys

def _check_or_write(path, text):
    """Write `text`, or under `--check` compare and write NOTHING.

    READ-ONLY MODE, 2026-10-07 (cc). One of 17 tools measured as writing to the
    tree on a bare run. Writing is this tool's job; what was missing was any
    way to ASK what it would write without letting it write -- and for a tool
    that emits a STATUS DOCUMENT that matters more than for a generator,
    because a status page is read as current by whoever opens it next.

    0 identical, 1 drifted, 2 could not tell. An unreadable or absent target is
    the third state and is never reported as drift.
    """
    import io as _io
    import os as _os
    import sys as _sys
    if '--check' not in _sys.argv:
        _io.open(path, 'w', encoding='utf-8', newline='').write(text)
        return 0
    if not _os.path.isfile(path):
        print('COULD NOT COMPARE: %s does not exist -- a missing target, not '
              'drift. NOTHING WRITTEN.' % path)
        return 2
    try:
        cur = _io.open(path, encoding='utf-8').read()
    except Exception as _e:
        print('COULD NOT COMPARE: %s unreadable (%s). NOTHING WRITTEN.'
              % (path, _e))
        return 2
    if cur == text:
        print('IDENTICAL: %s already says what this run would say. NOTHING '
              'WRITTEN.' % path)
        return 0
    print('DRIFTED: %s differs from what this run would say. NOTHING WRITTEN.'
          % path)
    print('  on disk  : %d bytes' % len(cur))
    print('  would be : %d bytes' % len(text))
    return 1


# Columns that exist for bookkeeping and cannot change a computed result.
INERT_COLUMNS = ['id', 'license_hash', 'app_id', 'created_at', 'updated_at', 'verified_by']

CONFIGS = [
    dict(app='sairncare', table='alf_compliance_rules', id_col='rule_id',
         seeds=['sql/sairncare_compliance_seed.json'], seed_id='rule_id'),
    dict(app='sairncare', table='alf_payer_rules', id_col='rule_id',
         seeds=['sql/sairncare_payer_rules_seed.json'], seed_id='rule_id'),
    dict(app='sairndental', table='dnt_cred_rules', id_col='rule_id',
         seeds=['sql/sairndental_credentials_seed_ohio.json'], seed_id='rule_id'),
    dict(app='sairnroofing', table='rf_cert_rules', id_col='rule_id',
         seeds=['sql/sairnroofing_certifications_seed_ohio.json'], seed_id='rule_id'),
    dict(app='sairnroofing', table='rf_contingency_rules', id_col='rule_id',
         seeds=['sql/sairnroofing_contingency_seed_ohio.json'], seed_id='rule_id'),
]


def normalise(rule, seed_id):
    """Mirror the server's write-path normalisation, then drop the id field."""
    out = {k: v for k, v in rule.items() if k != seed_id}
    if 'state' in out and isinstance(out['state'], str):
        out['state'] = out['state'].strip().upper()
    out['status'] = out.get('status') or 'active'
    return out


def collect(cfg):
    rules, dupes = {}, []
    for path in cfg['seeds']:
        if not os.path.exists(path):
            raise SystemExit('missing seed: %s' % path)
        with io.open(path, encoding='utf-8') as fh:
            doc = json.load(fh)
        for rule in doc.get('rules', []):
            rid = rule.get(cfg['seed_id'])
            if not rid:
                raise SystemExit('rule with no %s in %s' % (cfg['seed_id'], path))
            if rid in rules:
                dupes.append(rid)
                continue
            rules[rid] = dict(file=os.path.basename(path),
                              compute=normalise(rule, cfg['seed_id']))
    return rules, dupes


def lit(text):
    return "'" + str(text).replace("'", "''") + "'"


def build_sql(cfg, rules, dupes):
    subtract = ' - '.join(lit(c) for c in INERT_COLUMNS + [cfg['id_col']])
    o = []
    w = o.append
    w('-- sql/%s_load_gate_generated.sql' % cfg['table'])
    w('-- GENERATED by tools/sairn_build_load_gates.py -- DO NOT HAND-EDIT.')
    w('-- Re-run that script after any seed change; this file is derived, not authored.')
    w('-- READ-ONLY: no insert, update, delete, grant, revoke, alter, drop, truncate.')
    w('--')
    w('-- Compares every live %s row against the seed it should have come' % cfg['table'])
    w('-- from. A row in the output is a licence serving something the seeds do not say.')
    w('--')
    w('-- BOTH SIDES ARE SUBTRACTIVE. This table keeps compute content in PROMOTED')
    w('-- COLUMNS, not only in `data`, so comparing the blob alone would miss a wrong')
    w('-- value in one of them. to_jsonb(row) names no columns, so a column added')
    w('-- later is compared by default instead of being skipped by a stale list.')
    w('-- Bookkeeping columns subtracted: %s, %s.' % (', '.join(INERT_COLUMNS), cfg['id_col']))
    w('--')
    w("-- The expected side mirrors the server's write-path normalisation, read from")
    w('-- api/sd-data.js rather than assumed: `state` uppercased, `status` defaulted to')
    w("-- 'active'. Without that the gate reports false STALE on every row whose seed")
    w('-- omits status, and a gate that cries wolf on its first run gets switched off.')
    w('')
    w('with expected(rule_id, seed_file, compute) as (values')
    rows = []
    for rid in sorted(rules):
        r = rules[rid]
        rows.append('  (%s, %s, %s::jsonb)' % (
            lit(rid), lit(r['file']),
            lit(json.dumps(r['compute'], sort_keys=True, ensure_ascii=False))))
    w(',\n'.join(rows))
    w('),')
    w('licences as (')
    w("  select k.key, encode(digest(k.key,'sha256'),'hex') as h")
    w('  from public.license_keys k where k.app_id = %s' % lit(cfg['app']))
    w('),')
    w('live as (')
    w('  select l.key as licence, r.%s as rule_id,' % cfg['id_col'])
    w('         (to_jsonb(r) - %s) as compute' % subtract)
    w('  from licences l')
    w('  join public.%s r on r.license_hash = l.h' % cfg['table'])
    w('),')
    w('-- every (licence, seed rule) PAIR. Joining expected straight to live on')
    w('-- rule_id alone cannot see "missing from licence A while present on licence B".')
    w('wanted as (')
    w('  select l.key as licence, x.rule_id, x.seed_file, x.compute')
    w('  from licences l cross join expected x')
    w(')')
    w('select')
    w('  coalesce(w.licence, v.licence)   as licence,')
    w('  coalesce(w.rule_id, v.rule_id)   as rule_id,')
    w('  w.seed_file,')
    w('  case')
    w("    when v.rule_id is null then 'MISSING -- seed rule never loaded onto this licence'")
    w("    when w.rule_id is null then 'ORPHAN -- live row with no seed; origin unknown'")
    w("    else 'STALE -- live content differs from the seed'")
    w('  end                              as verdict,')
    w('  jsonb_pretty(w.compute)          as seed_compute,')
    w('  jsonb_pretty(v.compute)          as live_compute')
    w('from wanted w')
    w('full outer join live v on v.licence = w.licence and v.rule_id = w.rule_id')
    w('where v.rule_id is null or w.rule_id is null')
    w('   or v.compute is distinct from w.compute')
    w('order by 4, 1, 2;')
    if dupes:
        w('')
        w('-- ⚠ duplicate ids in the seeds, first kept: %s' % ', '.join(sorted(dupes)))
    return '\n'.join(o) + '\n'


KNOWN_FLAGS = ('--check', '--selftest', '--determinism',
               '--write-superseded-gates', '--help', '-h')

USAGE = """Build the SUPERSEDED generated load-state gates. Read the docstring first.

    python tools/sairn_build_load_gates.py --check         compare, write nothing
    python tools/sairn_build_load_gates.py --determinism   build twice in temp
                                                           dirs and compare
    python tools/sairn_build_load_gates.py --selftest      the arms below
    python tools/sairn_build_load_gates.py --write-superseded-gates
                                                           ACTUALLY WRITE the
                                                           five .sql files

A BARE RUN NO LONGER WRITES, and that is not a bug in the usage. This tool was
SUPERSEDED on 2026-08-29 by Michael's decision to standardise on
tools/sairn_load_state_check.py, and its five generated .sql gates were DELETED
as part of that decision. The deciding factor was staleness: a generated gate
must be regenerated after every seed edit, and a forgotten regeneration makes
the gate check yesterday's expectations and report clean -- the silent-failure
shape the gate exists to catch, reintroduced inside the catcher.

So a bare run of this file silently reinstates five gates a human decided to
remove. The write now needs --write-superseded-gates, spelled that way because
the flag has to say what it does rather than how.

Exit 0 fine, 1 drift or an arm failed, 2 COULD NOT RUN (including an argument
this tool does not recognise, and including a bare run)."""


def _build_all():
    """-> {dest: sql}. Pure: reads seeds, writes nothing."""
    out = {}
    for cfg in CONFIGS:
        rules, dupes = collect(cfg)
        out['sql/%s_load_gate_generated.sql' % cfg['table']] = build_sql(
            cfg, rules, dupes)
    return out


def determinism(rounds=2):
    """Build the whole set `rounds` times and compare sha256 per file.

    THE ARM THIS TOOL ACTUALLY NEEDED. Its output is ordered from dicts and
    sets built out of seed files; a set iteration order leaking into a .sql
    file would make every later --check report drift that is not drift, and
    the reader's conclusion would be "the seeds moved".

    In process rather than in two subprocesses, deliberately and with the
    limit stated: PYTHONHASHSEED differs BETWEEN processes, not within one, so
    this cannot see a str-hash-ordering dependency. `--determinism` runs the
    cross-process half and says so.
    """
    import hashlib
    runs = [_build_all() for _ in range(rounds)]
    keys = sorted(runs[0])
    rows = []
    for k in keys:
        digests = [hashlib.sha256(r[k].encode('utf-8')).hexdigest() for r in runs]
        rows.append((k, digests[0], all(d == digests[0] for d in digests)))
    return rows


def selftest():
    arms = []
    rows = determinism(3)
    arms.append(('three in-process builds agree byte-for-byte, per file',
                 [ok for _, _, ok in rows], [True] * len(rows)))
    arms.append(('every configured table produced a file',
                 len(rows), len(CONFIGS)))

    # A bare argv must NOT reach the write path. The real defect this guards is
    # not a typo -- it is somebody running the tool to see what it does and
    # silently reinstating five gates a human deleted.
    arms.append(('a bare run is refused, not treated as "write"',
                 classify([]), ('bare',)))
    arms.append(('an unknown flag is refused',
                 classify(['--bogus']), ('unknown', '--bogus')))
    arms.append(('--check is still --check',
                 classify(['--check']), ('check',)))
    arms.append(('the write needs its own explicit flag',
                 classify(['--write-superseded-gates']), ('write',)))

    lines, passed = [], 0
    for name, got, want in arms:
        ok = got == want
        passed += ok
        lines.append('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
        if not ok:
            lines.append('       wanted %r, got %r' % (want, got))
    return passed, len(arms) - passed, lines


def classify(argv):
    """-> ('check'|'write'|'selftest'|'determinism'|'help'|'bare',)
       or ('unknown', the argument). Pure."""
    unknown = [a for a in argv if a not in KNOWN_FLAGS]
    if unknown:
        return ('unknown', unknown[0])
    if '--help' in argv or '-h' in argv:
        return ('help',)
    if '--selftest' in argv:
        return ('selftest',)
    if '--determinism' in argv:
        return ('determinism',)
    if '--check' in argv:
        return ('check',)
    if '--write-superseded-gates' in argv:
        return ('write',)
    return ('bare',)


def main():
    mode = classify(sys.argv[1:])
    if mode[0] == 'unknown':
        print('COULD NOT RUN -- argument not recognised: %s' % mode[1])
        print('Nothing was written. Recognised: %s' % ', '.join(KNOWN_FLAGS))
        return 2
    if mode[0] == 'help':
        print(USAGE)
        return 0
    if mode[0] == 'bare':
        print('COULD NOT RUN -- a bare run of this tool is refused since '
              '2026-10-07, and nothing was written.')
        print('')
        print('It is SUPERSEDED (Michael, 2026-08-29) and its five generated '
              '.sql gates were DELETED by that decision. A bare run put them '
              'back, which is why it now refuses.')
        print('  what to use instead : python tools/sairn_load_state_check.py '
              '--app <app>')
        print('  to inspect, not write: --check, --determinism, --selftest')
        print('  to really write them : --write-superseded-gates, and say why')
        return 2
    if mode[0] == 'selftest':
        p, f, lines = selftest()
        print('selftest: %d/%d arm(s) pass' % (p, p + f))
        for ln in lines:
            print(ln)
        return 1 if f else 0
    if mode[0] == 'determinism':
        rows = determinism(3)
        print('determinism: 3 in-process builds of %d file(s)' % len(rows))
        for k, dig, ok in rows:
            print('  %-4s %s  %s' % ('SAME' if ok else 'DIFF', dig[:24], k))
        bad = [k for k, _, ok in rows if not ok]
        print('STATED LIMIT: three builds in ONE process cannot see a '
              'PYTHONHASHSEED-dependent ordering, because that seed is fixed '
              'per process. Run this twice from the shell with different seeds '
              'for that half.')
        return 1 if bad else 0

    total = 0
    _worst = 0
    for cfg in CONFIGS:
        rules, dupes = collect(cfg)
        sql = build_sql(cfg, rules, dupes)
        dest = 'sql/%s_load_gate_generated.sql' % cfg['table']
        # ── THE WORST VERDICT WINS, NOT THE LAST ONE ───────────────────────
        # This writes SEVERAL files in a loop. A loop that keeps only the
        # final status is how one drifted file hides behind four clean ones,
        # so `_worst` is a max and never an assignment.
        _rc = _check_or_write(dest, sql)
        _worst = max(_worst, _rc)
        total += len(rules)
        if '--check' not in sys.argv:
            print('%-14s %-24s rules=%-3d dupes=%d -> %s (%d bytes)' % (
                cfg['app'], cfg['table'], len(rules), len(dupes), dest,
                os.path.getsize(dest)))
    if '--check' in sys.argv:
        return _worst
    print('total rules gated: %d across %d tables' % (total, len(CONFIGS)))
    print('NOT GATED: sc_anesthesia_base_units (sairncode) -- no seed file exists in the repo,')
    print('           so there is no declared state to compare a live licence against.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
