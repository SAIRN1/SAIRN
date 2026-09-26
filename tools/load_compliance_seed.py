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
rather than a warning printed beside it. `--verify` drives the ENGINE through
the live endpoint on identical inputs BEFORE and AFTER the load and requires
the answer to have CHANGED:

    before   evaluate staffing, state=WV  ->  NO_RULE_FOR_STATE
    after    evaluate staffing, state=WV  ->  a real requirement

A load that returns 200 for every row and leaves that answer unchanged has not
loaded anything this app can use, and this tool reports that as a FAILURE
rather than as a successful run. Nothing else it prints means the rules work.

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


def verification_probe(state, seed):
    """The identical input driven before and after. Staffing, because it is the
    one requirement type every seeded state carries."""
    return {'action': 'evaluate', 'resource': 'alf_compliance_rules',
            'payload': {'check': 'staffing', 'state': state,
                        'on_date': _probe_date(state, seed)}}


def _probe_date(state, seed):
    """A date every rule for this state is in force on. Derived from the seed's
    own effective_from values -- a hardcoded date would go stale silently, and
    this tool would then report NO_RULE_FOR_STATE as a load failure."""
    dates = [r.get('effective_from') for r in (seed.get('rules') or [])
             if str(r.get('state') or '').upper() == str(state).upper()
             and r.get('effective_from')]
    return max(dates) if dates else '2026-01-01'


def answer_changed(before, after):
    """Did the engine's answer on identical input actually move?

    A load is proven by the ANSWER changing, not by 200s. `before` refusing
    with NO_RULE_FOR_STATE and `after` returning a requirement is the shape
    that proves it; anything else is reported rather than interpreted.
    """
    b = json.dumps(before, sort_keys=True)
    a = json.dumps(after, sort_keys=True)
    return b != a


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

    # ── BEFORE. Read-only, every time, for every state being loaded. ────────
    before = {}
    for s in states:
        _, before[s] = post(DATA_API, verification_probe(s, seed), args.key, token)

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
    print('\nVERIFYING BY A CHANGED RESULT ON IDENTICAL INPUTS -- not by the '
          'exit code above:')
    unchanged = []
    for s in states:
        _, after = post(DATA_API, verification_probe(s, seed), args.key, token)
        moved = answer_changed(before[s], after)
        print('  %-4s %s' % (s, 'ANSWER CHANGED' if moved else
                             '*** UNCHANGED -- nothing this app can use was loaded ***'))
        if not moved:
            unchanged.append(s)

    print('\nloaded %d of %d, %d failed, %d state(s) whose answer did not move'
          % (ok, len(to_load), len(failed), len(unchanged)))
    print('NOT A MIGRATION: the endpoint upserts on (license_hash, rule_id), so '
          're-running is safe and a rule REMOVED from the seed is NOT removed '
          'from this licence.')
    if failed or unchanged:
        return EXIT_REFUSED
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
