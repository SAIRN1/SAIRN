#!/usr/bin/env python
"""Load SAIRNcare compliance rules from the seed file into a live licence.

    set SAIRNCARE_LICENSE_KEY=...      (or --key)
    set SAIRNCARE_EMP=...              (or --employee)
    set SAIRNCARE_PIN=...              (or --pin)

    python tools/load_compliance_seed.py --dry-run
    python tools/load_compliance_seed.py --state WV
    python tools/load_compliance_seed.py                 # every state in the cap

── ITEM 65b's SIBLING: THE OTHER HALF THAT WAS NEVER WRITTEN ───────────────
On 2026-09-25 three West Virginia rules were read out of 64 CSR 14, seeded into
sql/sairncare_compliance_seed.json, tested by 20 arms -- and were INERT. The
push gate refused them and was right to: a seed-file change does nothing until
a loader runs, and `tools/` carried `load_deadline_seed.py` for SAIRNlaw and
NOTHING for SAIRNcare. The seed had to land anyway, because a loader reads it
from the repo, so it went in under an override with the inertness written into
the file, the index row and the commit. This is the tool that closes it.

The gate's own words name the defect it exists for: on 2026-08-27 two committed
SAIRNlaw corrections were never loaded and the canonical licence computed
federal answer deadlines three days late for a day.

── A LOADER'S EXIT CODE IS NOT EVIDENCE, AND THIS ONE DOES NOT OFFER ONE ───
That sentence is in the push gate's refusal text, and it is the design here
rather than a warning printed beside it. The verification is UNCONDITIONAL --
there is no flag to skip it, and no flag to ask for it. It drives the ENGINE
through the live endpoint, once per rule, BEFORE and AFTER the load, and asks
whether the engine now returns THAT rule:

    before   evaluate staffing WV/assisted_living_residence  ->  NO_RULE_FOR_STATE
    after    evaluate staffing WV/assisted_living_residence  ->  WV-STAFFING-ALR-2026

A load that returns 200 for every row and leaves the engine unable to reach
those rules has not loaded anything this app can use, and this tool reports that
as a FAILURE rather than as a successful run. Nothing else it prints means the
rules work.

── AND THE FIRST VERSION OF THAT VERIFICATION NEVER RAN (fixed 2026-09-26) ──
It sent `payload.check` where the endpoint requires `payload.requirement_type`,
so every probe answered **400 "evaluate requires state and requirement_type"** --
before AND after. Two identical 400s compare equal, so the tool reported
`*** UNCHANGED -- nothing this app can use was loaded ***` on every run it has
ever done, including the one where all three West Virginia rules landed
correctly. The header above promised the ONLY evidence that counts, and it was a
string comparison between two copies of the same refusal.

Three things were wrong and all three are fixed:

  1. `check` -> `requirement_type`, the key the endpoint actually reads.
  2. NO `facility_class`, so even a well-formed probe answered
     `NO_RULE_FOR_CLASS` -- "WV regulates classes that carry different figures,
     so another class's rule is not applied in its place". The class now comes
     from the RULE BEING VERIFIED, never a hardcoded list.
  3. "the answer must have CHANGED" conflated *nothing loaded* with *already
     loaded*. The endpoint upserts, so re-running is idempotent BY DESIGN and
     the second run's answer is identical to the first's -- which the old
     criterion called a failure. Three states, never two: LOADED (it moved),
     ALREADY IN FORCE (it did not move and the engine returns the rule), and
     NOT IN FORCE (the engine cannot reach it) -- and only the third fails.

── WHAT IT WILL NOT DO ─────────────────────────────────────────────────────
* NEVER PROBE A DEPLOYMENT WITH A WRITE. load_deadline_seed.py's header records
  what that cost: a dummy add_rule POSTed to test whether a standard had shipped
  STORED the dummy, and that endpoint implements no delete. Every probe here is
  `evaluate`, which writes nothing.
* NEVER LOAD A STATE OUTSIDE THE COVERAGE CAP. The seed carries
  `coverage_cap.states` -- Michael's 2026-09-25 decision, five states -- and a
  rule for a state outside it is REFUSED rather than loaded, because the cap is
  a decision and a loader that quietly widened it would be the decision being
  re-opened by a tool.
* NEVER DELETE. The endpoint upserts on (license_hash, rule_id), so re-running
  is idempotent. A rule REMOVED from the seed file is NOT removed from the
  licence by running this, and that is said rather than assumed.

Exit 0 loaded and verified, 1 something was refused or the verification did not
change, 2 could not run at all. Three states, never two.
"""
import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_http                                                 # noqa: E402

SEED = os.path.join(REPO, 'sql', 'sairncare_compliance_seed.json')
DATA_API = 'https://sairn.vercel.app/api/sd-data'
AUTH_API = 'https://sairn.vercel.app/api/alf-auth'

EXIT_OK, EXIT_REFUSED, EXIT_COULD_NOT_RUN = 0, 1, 2


def post(url, body, key, token=None):
    """-> (status, parsed body). Uses the shared transport rather than a
    hand-rolled urlopen, so a Vercel bot-mitigation challenge RAISES instead of
    being parsed as an answer -- a loader that read a challenge page as a 200
    would report rules loaded that never were."""
    headers = {'X-SD-Auth': token} if token else None
    r = sairn_http.fetch_json(url, timeout=60, method='POST',
                              payload=body, key=key, headers=headers)
    return r.status, r.body


# ── THE PURE HALF ───────────────────────────────────────────────────────────
# What to load, and what to refuse, decided without touching the network.

def load_seed(path=SEED):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


def select_rules(seed, state=None):
    """-> (to_load, refused). Refused rows carry the reason they were refused."""
    cap = (seed.get('coverage_cap') or {}).get('states')
    rules = seed.get('rules') or []
    to_load, refused = [], []
    for r in rules:
        st = str(r.get('state') or '').upper()
        if state and st != str(state).upper():
            continue
        if cap and st not in cap:
            refused.append((r.get('rule_id'), 'state %s is OUTSIDE the coverage '
                                              'cap %s -- that cap is a decision, '
                                              'and a loader does not widen one'
                            % (st, ', '.join(cap))))
            continue
        a = ((r.get('data') or {}).get('authority') or {})
        if not a.get('citation') or not re.match(r'^https?://', str(a.get('url') or '')):
            # The endpoint refuses this too. Catching it here means the run
            # stops before a partial load rather than halfway through one.
            refused.append((r.get('rule_id'), 'no authority citation or no '
                                              'resolvable source URL -- the '
                                              'endpoint would refuse it'))
            continue
        to_load.append(r)
    return to_load, refused


def rule_payload(r):
    return {
        'rule_id': r['rule_id'],
        'state': r['state'],
        'requirement_type': r['requirement_type'],
        'facility_class': r.get('facility_class'),
        'effective_from': r['effective_from'],
        'effective_to': r.get('effective_to'),
        'status': r.get('status') or 'active',
        'data': r.get('data') or {},
    }


def verification_probe(rule):
    """The identical input driven before and after, ONE PROBE PER RULE.

    Per rule rather than per state, because a state-level probe cannot tell
    "this state answers something" from "this rule is reachable" -- PA carries
    six rules across two facility classes, and a probe that only asked for
    `staffing` in PA would report a pass while a `training/pch` rule sat
    unreachable.

    EVERY FIELD COMES FROM THE RULE. `requirement_type` is the key the endpoint
    requires (the first version sent `check` and earned a 400 every time);
    `facility_class` is omitted only when the rule itself carries none, because
    the engine refuses to apply one class's figures to another; and `on_date` is
    the rule's own `effective_from`, so a date nobody has to maintain.
    """
    payload = {'requirement_type': rule['requirement_type'],
               'state': rule['state'],
               'on_date': rule.get('effective_from') or '2026-01-01'}
    if rule.get('facility_class'):
        payload['facility_class'] = rule['facility_class']
    return {'action': 'evaluate', 'resource': 'alf_compliance_rules',
            'payload': payload}


def answer_changed(before, after):
    """Did the engine's answer on identical input move? INFORMATION, not the
    pass criterion -- see probe_verdict. Kept because "it moved" is the thing a
    reader wants to see on a first load, and because the distinction between
    moved and already-in-force is the one the old criterion collapsed."""
    return json.dumps(before, sort_keys=True) != json.dumps(after, sort_keys=True)


def probe_verdict(rule, before, after):
    """-> (verdict, detail). Three states, never two.

      'loaded'    the engine now returns THIS rule, and the answer moved.
      'in_force'  the engine returns THIS rule and the answer did not move --
                  an idempotent re-run, which is what the endpoint's upsert is
                  for. A PASS, and the old "must have CHANGED" test called it a
                  failure.
      'not_in_force'  the engine cannot reach this rule. The only failure, and
                  the detail carries the engine's own refusal code rather than a
                  paraphrase of it.

    The evidence is `ok: true` AND a matching `rule_id`. `ok: true` alone is not
    enough: the engine answers ok for a DIFFERENT rule covering the same query,
    which is a load that silently did nothing. `evaluated: false` is fine and
    expected -- this probe supplies no census, so the engine describes the rule
    and names what it would still need.
    """
    a = after if isinstance(after, dict) else {}
    if a.get('ok') is not True:
        err = (a.get('error') or {})
        return 'not_in_force', (err.get('code') or 'no ok:true in the answer')
    got = a.get('rule_id')
    if got != rule['rule_id']:
        return 'not_in_force', ('the engine answered with %r, not %r -- this '
                                'rule is not the one serving its own query'
                                % (got, rule['rule_id']))
    return ('loaded' if answer_changed(before, after) else 'in_force'), got


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--state', help='load one state only (default: every state in the cap)')
    ap.add_argument('--key', default=os.environ.get('SAIRNCARE_LICENSE_KEY'))
    ap.add_argument('--employee', default=os.environ.get('SAIRNCARE_EMP'))
    ap.add_argument('--pin', default=os.environ.get('SAIRNCARE_PIN'))
    ap.add_argument('--dry-run', action='store_true',
                    help='print what would be loaded and touch nothing')
    args = ap.parse_args(argv)

    try:
        seed = load_seed()
    except Exception as e:                              # noqa: BLE001
        sys.stderr.write('COULD NOT RUN: %s is unreadable (%s). Nothing was '
                         'loaded.\n' % (SEED, e))
        return EXIT_COULD_NOT_RUN

    to_load, refused = select_rules(seed, args.state)
    print('SEED %s' % os.path.relpath(SEED, REPO))
    print('  rules selected   %3d' % len(to_load))
    print('  REFUSED          %3d   <- not loaded, and each says why' % len(refused))
    for rid, why in refused:
        print('    %-28s %s' % (rid, why))
    states = sorted({r['state'] for r in to_load})
    print('  states           %s' % (', '.join(states) or '(none)'))

    if args.dry_run:
        print('\nDRY RUN -- nothing was sent. Re-run without --dry-run to load.')
        return EXIT_OK if to_load else EXIT_REFUSED

    if not to_load:
        sys.stderr.write('\nNothing to load. That is not a successful load.\n')
        return EXIT_REFUSED
    if not args.key or not args.employee or not args.pin:
        sys.stderr.write(
            '\nCOULD NOT RUN: this endpoint needs a LICENCE KEY and a signed-in '
            'MANAGEMENT session -- alf_compliance_rules write is management '
            'only. Set SAIRNCARE_LICENSE_KEY, SAIRNCARE_EMP and SAIRNCARE_PIN, '
            'or pass --key/--employee/--pin.\nNothing was loaded, and an '
            'unloaded seed is INERT rather than absent.\n')
        return EXIT_COULD_NOT_RUN

    st, body = post(AUTH_API, {'action': 'login', 'employee_id': args.employee,
                               'pin': args.pin}, args.key)
    token = (body or {}).get('token')
    if st != 200 or not token:
        sys.stderr.write('COULD NOT RUN: sign-in failed (%s) -- %s\n'
                         % (st, json.dumps(body)[:300]))
        return EXIT_COULD_NOT_RUN
    role = ((body or {}).get('role') or '').lower()
    print('\nsigned in as %s (%s)' % (args.employee, role or 'role unknown'))

    # ── BEFORE. Read-only, every time, ONE PROBE PER RULE. ──────────────────
    before = {}
    for r in to_load:
        _, before[r['rule_id']] = post(DATA_API, verification_probe(r), args.key, token)

    ok, failed = 0, []
    for r in to_load:
        st, resp = post(DATA_API, {'action': 'write',
                                   'resource': 'alf_compliance_rules',
                                   'payload': rule_payload(r)}, args.key, token)
        if st == 200 and (resp or {}).get('ok'):
            ok += 1
            print('  loaded  %s' % r['rule_id'])
        else:
            failed.append((r['rule_id'], st, json.dumps(resp)[:200]))
            print('  FAILED  %-28s %s %s' % (r['rule_id'], st, json.dumps(resp)[:160]))

    # ── AFTER, ON IDENTICAL INPUT. This is the only evidence that counts. ───
    print('\nVERIFYING BY DRIVING THE ENGINE, once per rule, on the inputs that '
          'rule covers -- not by the exit code above:')
    unreachable, moved_n, already_n = [], 0, 0
    for r in to_load:
        _, after = post(DATA_API, verification_probe(r), args.key, token)
        verdict, detail = probe_verdict(r, before[r['rule_id']], after)
        if verdict == 'loaded':
            moved_n += 1
            print('  LOADED         %-28s the engine now answers with it' % r['rule_id'])
        elif verdict == 'in_force':
            already_n += 1
            print('  ALREADY IN FORCE %-26s unchanged, and the engine answers '
                  'with it -- an idempotent re-run, not a failure' % r['rule_id'])
        else:
            unreachable.append((r['rule_id'], detail))
            print('  *** NOT IN FORCE %-24s %s' % (r['rule_id'], detail))

    print('\nloaded %d of %d, %d failed to write, %d newly in force, %d already '
          'in force, %d the engine CANNOT REACH'
          % (ok, len(to_load), len(failed), moved_n, already_n, len(unreachable)))
    print('NOT A MIGRATION: the endpoint upserts on (license_hash, rule_id), so '
          're-running is safe and a rule REMOVED from the seed is NOT removed '
          'from this licence.')
    if failed or unreachable:
        return EXIT_REFUSED
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
