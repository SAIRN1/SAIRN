#!/usr/bin/env python
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
  3. sc_anesthesia_base_units HAS NO SEED FILE. No gate can be built for it, and
     that absence is itself the finding.

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


def main():
    total = 0
    for cfg in CONFIGS:
        rules, dupes = collect(cfg)
        sql = build_sql(cfg, rules, dupes)
        dest = 'sql/%s_load_gate_generated.sql' % cfg['table']
        with io.open(dest, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(sql)
        total += len(rules)
        print('%-14s %-24s rules=%-3d dupes=%d -> %s (%d bytes)' % (
            cfg['app'], cfg['table'], len(rules), len(dupes), dest, os.path.getsize(dest)))
    print('total rules gated: %d across %d tables' % (total, len(CONFIGS)))
    print('NOT GATED: sc_anesthesia_base_units (sairncode) -- no seed file exists in the repo,')
    print('           so there is no declared state to compare a live licence against.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
