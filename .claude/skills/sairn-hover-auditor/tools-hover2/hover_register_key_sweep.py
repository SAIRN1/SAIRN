#!/usr/bin/env python
"""hover_register_key_sweep.py (hover2's own build) -- the storage-key-vs-
register cross-check from seq 370, promoted from a scratchpad script to a
standing tool with the naming-variant false-positive class FIXED and locked
by fixtures (per the 2026-09-29 eight-item paste, item 4).

WHAT IT DOES: for every app HTML file in the platform repo, extract every
quoted string literal shaped like a register-known prefix's resource-name
pattern, and report which of them have NO row in docs/CRITICALITY-TIERS.md.

THREE FILTER CLASSES, each named and each with fixtures in BOTH directions:
  * INFRA -- session/license/role/settings/sync-bookkeeping keys, the same
    shape confirmed by direct read for sb_/bld_ on 2026-09-29. Filtered,
    counted, reported as a number, never silently dropped.
  * NAMING VARIANT (regular) -- a key ending _list/_records/_obj/_arr whose
    stripped stem IS a registered name (dnt_patients_list -> dnt_patients,
    the confirmed real case at sairndental.html:2185). Resolved, not
    reported as a gap.
  * NAMING VARIANT (irregular) -- a key whose stem differs from its
    registered row by more than a suffix strip. These CANNOT be derived
    mechanically without guessing, so they live in an explicit, versioned
    IRREGULAR_VARIANTS map -- each entry added only after a human read
    confirmed the code's key and the register's row name the same real
    resource. Seq 370 already named the first three as PROBABLE; confirmed
    and locked here.

FAIL CLOSED: an unreadable register or repo is COULD NOT RUN (exit 2).
Exit 0 when no unregistered keys remain, 1 when any are reported.

Run:
  python hover_register_key_sweep.py            # full sweep, one list
  python hover_register_key_sweep.py --selftest # fixtures only
"""
import io
import os
import re
import sys
from collections import defaultdict

REPO = os.environ.get('HOVER_PLATFORM_REPO',
                      r'C:\Users\marsh\Documents\SAIRN-hover2')
TIERS_REL = os.path.join('docs', 'CRITICALITY-TIERS.md')

INFRA_SUFFIXES = (
    '_lic', '_lic_fp', '_license_key', '_license', '_role', '_session',
    '_session_token', '_session_role', '_session_employee',
    '_session_employee_id', '_sub_session_id', '_sub_session_name',
    '_sub_session_token', '_seeded', '_settings', '_settings_obj', '_sync',
    '_sync_stale', '_sync_pending', '_synced_bootstrap', '_synced_ids',
    '_trial_start', '_cache_owner', '_jobs', '_pending_writes',
    '_unconfirmed_writes', '_po_seq', '_seq', '_pending_trusted',
    '_demo_cleared', '_last_backup', '_last_panel', '_cfg',
)

REGULAR_VARIANT_SUFFIXES = ('_list', '_records', '_obj', '_arr')

# Irregular naming variants: key-in-code -> registered row. Every entry here
# was confirmed by a human read (the code's storage key and the register row
# describe the same real resource), never derived by string similarity.
#   dnt_coverage_list      -> dnt_coverage_rules   (2026-09-29, seq 370 probable, confirmed)
#   dnt_procedures_list    -> dnt_procedure_types  (2026-09-29, same)
#   dnt_vendor_order_history -> dnt_vendor_orders  (2026-09-29, same)
IRREGULAR_VARIANTS = {
    'dnt_coverage_list': 'dnt_coverage_rules',
    'dnt_procedures_list': 'dnt_procedure_types',
    'dnt_vendor_order_history': 'dnt_vendor_orders',
}


def load_registered(tiers_text):
    return set(re.findall(r"^\|\s*`([a-z0-9_]+)`", tiers_text, re.M))


def is_infra(name):
    return any(name.endswith(suf) for suf in INFRA_SUFFIXES)


def resolve_variant(name, registered):
    """Registered row this key is a naming variant of, or None. Checks the
    irregular map FIRST (an explicit human-confirmed mapping beats a
    mechanical suffix strip), then the regular suffix strips."""
    if name in IRREGULAR_VARIANTS:
        target = IRREGULAR_VARIANTS[name]
        # the mapping is only honoured if its target genuinely IS registered
        # -- a stale map entry must surface as a gap again, not silently
        # vouch for a row that no longer exists.
        return target if target in registered else None
    for suf in REGULAR_VARIANT_SUFFIXES:
        if name.endswith(suf):
            base = name[: -len(suf)]
            if base in registered:
                return base
    return None


def classify(found_names, registered):
    """{'checked': [...], 'variant': [(key, row)...], 'infra': [...],
        'unregistered': [...]} for one prefix's found set."""
    out = {'checked': [], 'variant': [], 'infra': [], 'unregistered': []}
    for name in sorted(found_names):
        if name in registered:
            out['checked'].append(name)
            continue
        row = resolve_variant(name, registered)
        if row:
            out['variant'].append((name, row))
            continue
        if is_infra(name):
            out['infra'].append(name)
            continue
        out['unregistered'].append(name)
    return out


def sweep(repo=None):
    repo = repo or REPO
    tiers = os.path.join(repo, TIERS_REL)
    if not os.path.isfile(tiers):
        print('COULD NOT RUN: register not found: %s' % tiers)
        return 2
    with io.open(tiers, encoding='utf-8') as f:
        registered = load_registered(f.read())
    if not registered:
        print('COULD NOT RUN: register parsed to zero resource rows')
        return 2
    reg_by_prefix = defaultdict(set)
    for name in registered:
        m = re.match(r'^([a-z]+)_', name)
        if m:
            reg_by_prefix[m.group(1) + '_'].add(name)

    import glob
    any_gap = False
    for path in sorted(glob.glob(os.path.join(repo, '*.html'))):
        fname = os.path.basename(path)
        with io.open(path, encoding='utf-8', errors='replace') as f:
            text = f.read()
        cands = set(re.findall(r"['\"]([a-z]{2,8}_[a-z][a-z0-9_]*)['\"]", text))
        by_prefix = defaultdict(set)
        for c in cands:
            m = re.match(r'^([a-z]+)_', c)
            if m and (m.group(1) + '_') in reg_by_prefix:
                by_prefix[m.group(1) + '_'].add(c)
        for p, found in sorted(by_prefix.items()):
            reg = reg_by_prefix[p]
            cls = classify(found, reg)
            if len(cls['checked']) < 2:
                continue  # not genuinely this app's own prefix
            universe = len(cls['checked']) + len(cls['unregistered'])
            print('%-22s %-8s checked %d/%d  (variants resolved %d, infra %d)'
                  % (fname, p, len(cls['checked']), universe,
                     len(cls['variant']), len(cls['infra'])))
            for name in cls['unregistered']:
                any_gap = True
                print('    UNREGISTERED  %s' % name)
    return 1 if any_gap else 0


def selftest():
    bad = []
    total = [0]

    def ck(name, cond):
        total[0] += 1
        if not cond:
            bad.append(name)
        print('  %s   %s' % ('ok' if cond else 'FAIL', name))

    reg = {'dnt_patients', 'dnt_coverage_rules', 'dnt_procedure_types',
           'dnt_vendor_orders', 'sb_ap'}

    ck('a registered key classifies checked',
       classify({'sb_ap'}, reg)['checked'] == ['sb_ap'])
    ck('REGULAR VARIANT _list: dnt_patients_list resolves to dnt_patients, '
       'not reported as a gap',
       classify({'dnt_patients_list'}, reg)['variant'] ==
       [('dnt_patients_list', 'dnt_patients')])
    ck('KNOWN-BAD CONTROL (_list): a _list key whose stem is NOT registered '
       'stays UNREGISTERED -- the strip must not vouch for a nonexistent row',
       classify({'dnt_ghosts_list'}, reg)['unregistered'] == ['dnt_ghosts_list'])

    ck('IRREGULAR VARIANT: dnt_coverage_list resolves to dnt_coverage_rules '
       'via the explicit human-confirmed map',
       classify({'dnt_coverage_list'}, reg)['variant'] ==
       [('dnt_coverage_list', 'dnt_coverage_rules')])
    ck('IRREGULAR VARIANT: dnt_procedures_list resolves to dnt_procedure_types',
       classify({'dnt_procedures_list'}, reg)['variant'] ==
       [('dnt_procedures_list', 'dnt_procedure_types')])
    ck('IRREGULAR VARIANT: dnt_vendor_order_history resolves to '
       'dnt_vendor_orders',
       classify({'dnt_vendor_order_history'}, reg)['variant'] ==
       [('dnt_vendor_order_history', 'dnt_vendor_orders')])
    ck('KNOWN-BAD CONTROL (irregular): a map entry whose TARGET row is not '
       'registered surfaces as a gap again, never silently vouched',
       classify({'dnt_coverage_list'},
                reg - {'dnt_coverage_rules'})['unregistered'] ==
       ['dnt_coverage_list'])

    ck('INFRA: a _session_token key is filtered as infra',
       classify({'sb_session_token'}, reg)['infra'] == ['sb_session_token'])
    ck('KNOWN-BAD CONTROL (infra): a real data key must never classify infra',
       classify({'sb_emps'}, reg)['infra'] == [] and
       classify({'sb_emps'}, reg)['unregistered'] == ['sb_emps'])

    ck('a genuinely unregistered key is reported',
       classify({'sb_co'}, reg)['unregistered'] == ['sb_co'])

    print('')
    if bad:
        print('%d ok, %d FAILED: %s' % (total[0] - len(bad), len(bad), bad))
        return 1
    print('%d ok, 0 failed' % total[0])
    return 0


if __name__ == '__main__':
    if '--selftest' in sys.argv[1:]:
        sys.exit(selftest())
    sys.exit(sweep())
