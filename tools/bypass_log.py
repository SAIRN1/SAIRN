"""bypass_log.py -- item 86, the battleshort pattern. Every override, recorded,
and a REPEATEDLY bypassed check reported as a defect in the CHECK.

    python tools/bypass_log.py                 # the log, and the patterns in it
    python tools/bypass_log.py --json
    python tools/bypass_log.py --selftest

── THE PATTERN, AND WHY IT IS NOT "DO NOT OVERRIDE" ─────────────────────────
A battleshort is the switch on a warship that disables safety interlocks so a
weapon can fire while the ship is on fire. The design is not naive: the point of
formalising it is that the override EXISTS, is expected to be used, and is
therefore engineered rather than improvised. Three requirements come with it, and
this platform's override had none of them:

  (a) IT BYPASSES A NAMED THING, never "all safety off". `SAIRN_SEED_GATE=off`
      currently returns from the hook before a single check runs -- the seed gate,
      the Tier A review gate, the generated-document check, all of them -- which
      is a switch labelled for one purpose that disables ten.
  (b) IT IS TIME-BOUNDED AND SELF-REVERTING, never a switch somebody must
      remember to flip back.
  (c) EVERY USE IS LOGGED, in its OWN log, so a REPEATED bypass of the same
      check becomes visible AS A PATTERN.

(c) is the one that changes behaviour rather than paperwork. **A check that is
bypassed repeatedly is a defect in the CHECK, not a discipline problem in whoever
keeps bypassing it.** A gate that fires on work people legitimately need to ship
is mis-specified, and the only way anybody finds that out is if the bypasses are
counted somewhere they cannot be counted by remembering.

── WHAT IS ALREADY RIGHT, AND IS NOT BEING "FIXED" ──────────────────────────
The existing override is ALREADY self-reverting in the strongest possible sense:
`SAIRN_SEED_GATE=off git push ...` is a shell assignment scoped to ONE COMMAND. It
cannot outlive that command, so there is no switch left flipped. Replacing that
with a timer would be strictly weaker, and requirement (b) is therefore satisfied
for the per-command form and is enforced here only for a STANDING bypass -- the
shape that genuinely can be left on.

── AND THE BLANKET FORM IS NOT DELETED, DELIBERATELY ────────────────────────
A battleshort exists because sometimes you must ship anyway. Removing the only
escape hatch from a blocking gate -- on a platform where no clone can verify that
nobody needs it tonight -- would be the opposite of this pattern: it would push the
next emergency into `--no-verify`, which nothing logs at all. So the blanket form
survives, is logged LOUDLY, and is reported as a distinct and worse category than
a named bypass.

── WHAT THIS CANNOT DO ──────────────────────────────────────────────────────
  * It cannot log a bypass that never reaches it. `git push --no-verify` and a
    direct API push bypass the hook itself, so the log's denominator is "overrides
    that went through the hook", never "overrides". Stated because a clean log
    would otherwise read as no overrides.
  * It cannot tell a legitimate emergency from laziness. It counts; a human reads.
  * It is APPEND-ONLY BY CONVENTION, not by enforcement -- the file is in the
    repo, so anyone who can push can rewrite it. Real tamper-evidence would need
    the audit chain, which is a separate piece of work and is named here rather
    than implied.
"""
import io
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ── THE PATH IS ENV-OVERRIDABLE, AND THAT IS NOT A CONVENIENCE ──────────────
# tests/push_gate/refspec_and_override_probe.py drives the real hook with a real
# `SAIRN_SEED_GATE=off` payload, which is exactly what it should do. Wiring the
# logger into the override site therefore made EVERY SUITE RUN append a row here,
# and within a few runs PATTERN_AT would fire on `ALL` from the probe alone -- a
# pattern detector reporting its own test harness as the pattern.
#
# A REDIRECT, NOT A SUPPRESSION. Skipping the write under test would leave the
# wiring never actually exercised, which is the fail-open shape this platform
# keeps finding. The probe sets SAIRN_BYPASS_LOG to a throwaway file, so the
# write really happens and lands somewhere that is not the audit record.
LOG = os.environ.get('SAIRN_BYPASS_LOG') or os.path.join(
    REPO, 'docs', 'BYPASS-LOG.jsonl')
STANDING = os.path.join(REPO, '.claude', 'standing-bypass.json')

# A check bypassed this many times is reported as a DEFECT IN THE CHECK. Low on
# purpose: three is already a pattern, and a threshold high enough to feel safe is
# a threshold nothing ever reaches.
PATTERN_AT = 3
# The longest a STANDING bypass may be granted for. A standing bypass is the shape
# that can be left on, so it is the one that needs a clock.
MAX_STANDING_HOURS = 24

KNOWN_CHECKS = (
    'seed-gate', 'tier-a-review', 'generated-docs', 'sql-preflight',
    'reachability', 'redaction', 'load-state', 'seam', 'employee-auth-guard',
    'preauth-oracle', 'conflict-marker', 'ALL',
)


class BypassError(Exception):
    pass


def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def session_name():
    base = os.path.basename(REPO)
    m = re.match(r'^SAIRN-(.+)$', base, re.I)
    return (m.group(1) if m else base).lower()


def record(check, reason, command=None, tip=None, when=None, path=None):
    """Append one bypass. Returns the row written.

    FAIL-SAFE BY DESIGN, and the caller is told so: this is invoked from a
    BLOCKING push hook, and a gate that refuses a push because its LOGGING failed
    would convert a bookkeeping problem into an outage. So the hook catches
    everything from here. The cost is that a failed write is a missing row, which
    is why the reporter prints the log's own line count rather than implying
    completeness.
    """
    if not check or not isinstance(check, str):
        raise BypassError('a bypass must name a check')
    if check not in KNOWN_CHECKS:
        # NOT a refusal. An unknown name is recorded as given, because refusing
        # would mean a bypass of a check added yesterday goes unlogged -- and an
        # unlogged bypass is the thing this file exists to prevent. It is
        # reported as UNKNOWN-CHECK so the list can be corrected.
        check = check.strip()
    if not reason or not str(reason).strip():
        raise BypassError('a bypass must carry a reason. "An override nobody '
                          'mentions is how this gets hollowed out."')
    row = {'at': when or _now(), 'session': session_name(), 'check': check,
           'reason': str(reason).strip()[:600],
           'blanket': check == 'ALL',
           'command': (command or '')[:300] or None,
           'tip': tip or None}
    p = path or LOG
    with io.open(p, 'a', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


def read(path=None):
    p = path or LOG
    if not os.path.isfile(p):
        return []
    rows, bad = [], 0
    for line in io.open(p, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            bad += 1
    if bad:
        # A malformed line is reported, never skipped silently: a bypass that
        # cannot be parsed is still a bypass that happened.
        rows.append({'at': '?', 'session': '?', 'check': '(UNPARSEABLE)',
                     'reason': '%d line(s) in the log could not be parsed' % bad,
                     'blanket': False, 'unparseable': bad})
    return rows


def patterns(rows, at=PATTERN_AT):
    """Which checks have been bypassed enough times to be the problem."""
    counts, by_check = {}, {}
    for r in rows:
        c = r.get('check') or '(none)'
        counts[c] = counts.get(c, 0) + 1
        by_check.setdefault(c, []).append(r)
    return {
        'counts': counts,
        'repeatedly_bypassed': sorted([c for c, n in counts.items() if n >= at]),
        'blanket_uses': sum(1 for r in rows if r.get('blanket')),
        'unknown_checks': sorted(set(c for c in counts
                                     if c not in KNOWN_CHECKS and c != '(none)')),
        'by_check': by_check,
    }


def check_standing(path=None, now=None):
    """A STANDING bypass must carry an expiry, and an expired one is INACTIVE.

    Returns {'active': [...], 'expired': [...], 'invalid': [...]}. Requirement (b)
    lives here, because this is the only shape that can be left switched on.
    """
    p = path or STANDING
    out = {'active': [], 'expired': [], 'invalid': []}
    if not os.path.isfile(p):
        return out
    try:
        data = json.load(io.open(p, encoding='utf-8'))
    except (OSError, ValueError) as e:
        out['invalid'].append({'why': 'unreadable standing-bypass file: %s' % e})
        return out
    entries = data.get('bypasses') if isinstance(data, dict) else data
    if not isinstance(entries, list):
        out['invalid'].append({'why': 'no bypasses list'})
        return out
    nowts = now or _now()
    for e in entries:
        if not isinstance(e, dict) or not e.get('check'):
            out['invalid'].append({'why': 'entry names no check', 'entry': e})
            continue
        exp = e.get('expires_at')
        if not exp:
            # NO EXPIRY IS NOT A LONG EXPIRY. A standing bypass with no clock is
            # the switch nobody flips back, which is the entire failure mode
            # requirement (b) exists for -- so it is INVALID, not permanent.
            out['invalid'].append({'why': 'no expires_at -- a standing bypass '
                                          'without a clock is the switch nobody '
                                          'flips back', 'entry': e})
            continue
        if exp <= nowts:
            out['expired'].append(e)
        else:
            out['active'].append(e)
    return out


def _selftest():
    ok = True

    def check_(name, cond, detail=''):
        nonlocal ok
        print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + str(detail)))
        if not cond:
            ok = False

    import tempfile
    d = tempfile.mkdtemp(prefix='bypass-selftest-')
    lg = os.path.join(d, 'log.jsonl')

    print('1. a bypass must NAME a check and carry a REASON')
    try:
        record('', 'why', path=lg); check_('an unnamed check is refused', False)
    except BypassError:
        check_('an unnamed check is refused', True)
    try:
        record('seed-gate', '   ', path=lg)
        check_('a blank reason is refused', False)
    except BypassError as e:
        check_('a blank reason is refused', 'hollowed out' in str(e))

    print('\n2. it appends, and an UNKNOWN check name is logged not dropped')
    record('seed-gate', 'migration had to ship', path=lg)
    record('a-check-added-yesterday', 'new gate, real emergency', path=lg)
    rows = read(lg)
    check_('both rows are present', len(rows) == 2, len(rows))
    p = patterns(rows)
    check_('the unknown name is REPORTED rather than refused',
           p['unknown_checks'] == ['a-check-added-yesterday'], p['unknown_checks'])

    print('\n3. a REPEATED bypass of one check is a pattern')
    for i in range(2):
        record('seed-gate', 'again %d' % i, path=lg)
    p = patterns(read(lg))
    check_('three uses of one check crosses PATTERN_AT',
           'seed-gate' in p['repeatedly_bypassed'], p['repeatedly_bypassed'])
    check_('...and a check used ONCE does not',
           'a-check-added-yesterday' not in p['repeatedly_bypassed'])

    print('\n4. the BLANKET form is counted as its own, worse category')
    record('ALL', 'everything off, emergency', path=lg)
    p = patterns(read(lg))
    check_('blanket uses are counted separately', p['blanket_uses'] == 1,
           p['blanket_uses'])

    print('\n5. an UNPARSEABLE line is reported, never skipped')
    with io.open(lg, 'a', encoding='utf-8') as fh:
        fh.write('{not json\n')
    rows = read(lg)
    check_('the log reports the bad line as a row',
           any(r.get('check') == '(UNPARSEABLE)' for r in rows),
           [r.get('check') for r in rows])

    print('\n6. a STANDING bypass with NO EXPIRY is INVALID, not permanent')
    sp = os.path.join(d, 'standing.json')
    io.open(sp, 'w', encoding='utf-8').write(json.dumps(
        {'bypasses': [{'check': 'seed-gate', 'reason': 'x'}]}))
    st = check_standing(sp, now='2026-09-16T00:00:00Z')
    check_('no expires_at -> invalid', len(st['invalid']) == 1 and not st['active'],
           st)
    check_('...and the reason names the switch nobody flips back',
           'flips back' in st['invalid'][0]['why'])

    print('\n7. an EXPIRED standing bypass is not active')
    io.open(sp, 'w', encoding='utf-8').write(json.dumps({'bypasses': [
        {'check': 'seed-gate', 'reason': 'x', 'expires_at': '2026-09-15T00:00:00Z'},
        {'check': 'tier-a-review', 'reason': 'y', 'expires_at': '2026-09-17T00:00:00Z'}]}))
    st = check_standing(sp, now='2026-09-16T00:00:00Z')
    check_('the past one is EXPIRED', [e['check'] for e in st['expired']] == ['seed-gate'], st)
    check_('the future one is ACTIVE', [e['check'] for e in st['active']] == ['tier-a-review'], st)

    print('\n8. an unreadable standing file is INVALID, never "no bypasses"')
    io.open(sp, 'w', encoding='utf-8').write('{ not json')
    st = check_standing(sp, now='2026-09-16T00:00:00Z')
    check_('it reports invalid rather than an empty active list',
           len(st['invalid']) == 1 and not st['active'], st)

    try:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
        os.rmdir(d)
    except OSError:
        pass
    print('')
    print('  all arms pass' if ok else '  ARMS FAILED')
    return 0 if ok else 2


def main(argv):
    if '--selftest' in argv:
        return _selftest()
    rows = read()
    p = patterns(rows)
    st = check_standing()
    if '--json' in argv:
        print(json.dumps({'rows': len(rows), 'patterns': p, 'standing': st}, indent=1))
        return 0

    print('BYPASS LOG -- item 86, the battleshort pattern. Report only.')
    print('  overrides recorded : %d' % len([r for r in rows if not r.get('unparseable')]))
    print('  blanket (ALL)      : %d   <- a switch labelled for one purpose that '
          'disables ten' % p['blanket_uses'])
    print('')
    if not rows:
        print('  THE LOG IS EMPTY, and that is NOT the same as no overrides.')
        print('  `git push --no-verify` and a direct API push never reach the')
        print('  hook, so this log counts overrides THAT WENT THROUGH IT. A clean')
        print('  log here is evidence about the hook, not about the platform.')
    else:
        for c in sorted(p['counts'], key=lambda k: -p['counts'][k]):
            print('    %-28s %d' % (c, p['counts'][c]))
    if p['repeatedly_bypassed']:
        print('')
        print('  REPEATEDLY BYPASSED -- READ THIS AS A DEFECT IN THE CHECK:')
        for c in p['repeatedly_bypassed']:
            print('    %s (%d times)' % (c, p['counts'][c]))
            for r in p['by_check'][c][:3]:
                print('        %s  %s  %s' % (r.get('at'), r.get('session'),
                                              (r.get('reason') or '')[:70]))
        print('')
        print('  A check that people legitimately need to bypass is MIS-SPECIFIED.')
        print('  The action is to fix the check or narrow it, not to ask whoever')
        print('  keeps bypassing it to try harder.')
    if p['unknown_checks']:
        print('')
        print('  NAMES NOT IN KNOWN_CHECKS (logged anyway, on purpose -- refusing')
        print('  would leave a bypass of a new gate unlogged):')
        for c in p['unknown_checks']:
            print('    %s' % c)
    print('')
    print('  standing bypasses: %d active, %d expired, %d INVALID'
          % (len(st['active']), len(st['expired']), len(st['invalid'])))
    for e in st['invalid']:
        print('    INVALID: %s' % e.get('why'))
    for e in st['active']:
        print('    active until %s: %s' % (e.get('expires_at'), e.get('check')))
    print('')
    print('WHAT THIS CANNOT SEE: an override that never reaches the hook, and the')
    print('difference between a real emergency and laziness. It counts; a human')
    print('reads. And the log is append-only BY CONVENTION -- it is a file in the')
    print('repo, so anybody who can push can rewrite it. Real tamper-evidence')
    print('needs the audit chain, which is separate work.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
