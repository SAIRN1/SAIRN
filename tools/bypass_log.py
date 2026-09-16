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
# The reserved check name a retraction carries. Not in KNOWN_CHECKS on purpose:
# it is not a check anybody can bypass, it is a statement about another row.
RETRACTION = '(RETRACTION)'
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


def retract(target_at, why, path=None, when=None):
    """Mark an earlier row as not a real bypass. APPEND-ONLY -- nothing is deleted.

    ── WHY A RETRACTION AND NOT A DELETE (2026-09-16) ──────────────────────
    `tests/push_gate/check9_probe.py` drove the real hook with a real override
    payload and never set SAIRN_BYPASS_LOG, so the hook correctly recorded a
    bypass -- into the live audit log, attributed to a real session, for a
    command no human ran.

    The row cannot be deleted. This log is the record of what happened to the
    gates, and a log that quietly loses rows it finds embarrassing is worth less
    than one with a known-bad row in it -- the same rule the platform already
    applies to sb_po and sb_recv, where a correction is a new row and never an
    erasure. So the bad row stays and this one says what it really was.

    ── AND IT HAS TO CHANGE THE READING, NOT JUST THE CONTENTS ─────────────
    A retraction that only added a line would be a comment. `patterns()` counts
    rows to decide whether a check is being bypassed so often that the CHECK is
    the defect -- at PATTERN_AT, which is 3. Three probe artefacts would report
    a phantom defect in a gate nobody actually bypassed. So a retracted row is
    excluded from that count, and the exclusion is reported rather than silent.
    """
    if not target_at or not isinstance(target_at, str):
        raise BypassError('a retraction must name the `at` of the row it retracts')
    if not why or not str(why).strip():
        raise BypassError('a retraction must carry a reason. A row struck from '
                          'the record without one is indistinguishable from a '
                          'row somebody wanted gone.')
    row = {'at': when or _now(), 'session': session_name(),
           'check': RETRACTION, 'reason': str(why).strip()[:600],
           'blanket': False, 'command': None, 'tip': None,
           'retracts': target_at}
    p = path or LOG
    with io.open(p, 'a', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


def retracted_ats(rows):
    """The `at` values some later row retracts."""
    return set(r['retracts'] for r in rows
               if r.get('check') == RETRACTION and r.get('retracts'))


def patterns(rows, at=PATTERN_AT):
    """Which checks have been bypassed enough times to be the problem.

    A RETRACTED ROW IS NOT COUNTED, and neither is the retraction itself. Both
    would otherwise inflate the figure that decides whether a check is
    mis-specified -- see retract() for the row that made this necessary.
    """
    struck = retracted_ats(rows)
    counts, by_check = {}, {}
    for r in rows:
        if r.get('check') == RETRACTION or r.get('at') in struck:
            continue
        c = r.get('check') or '(none)'
        counts[c] = counts.get(c, 0) + 1
        by_check.setdefault(c, []).append(r)
    return {
        'counts': counts,
        'repeatedly_bypassed': sorted([c for c, n in counts.items() if n >= at]),
        # ALSO retraction-aware. This read `sum(... for r in rows)` over every
        # row and was the half that survived the first fix: patterns() excluded
        # struck rows from `counts` while the blanket figure beside it still
        # counted them, so one report said two different things about the same
        # row. A correction the reporter does not honour is a comment.
        'blanket_uses': sum(1 for r in rows if r.get('blanket')
                            and r.get('at') not in struck),
        'retracted': sorted(struck),
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

    print('\n4b. a RETRACTED row stops counting, and nothing is deleted')
    rl = os.path.join(d, 'retract.jsonl')
    a = record('seed-gate', 'first', path=rl, when='2026-09-16T01:00:00Z')
    record('seed-gate', 'second', path=rl, when='2026-09-16T02:00:00Z')
    record('seed-gate', 'third', path=rl, when='2026-09-16T03:00:00Z')
    check_('three real uses cross PATTERN_AT before any retraction',
           'seed-gate' in patterns(read(rl))['repeatedly_bypassed'])
    retract(a['at'], 'confirmed test artefact -- a probe drove the hook',
            path=rl, when='2026-09-16T04:00:00Z')
    p = patterns(read(rl))
    check_('...and after retracting ONE, the pattern no longer fires',
           'seed-gate' not in p['repeatedly_bypassed'], p['repeatedly_bypassed'])
    check_('...counted as 2, not 3, and not as 4 either -- the retraction is '
           'not itself a bypass', p['counts'].get('seed-gate') == 2,
           p['counts'])
    # THE ROW IS STILL THERE. That is the whole point: a log that deletes what
    # embarrasses it is worth less than one with a known-bad row and a note.
    raw = io.open(rl, encoding='utf-8').read()
    check_('...and the retracted row is STILL IN THE FILE, not deleted',
           raw.count('"reason": "first"') == 1, raw[:200])
    check_('...and the retraction names which row it strikes',
           any(r.get('retracts') == a['at'] for r in read(rl)))
    # BOTH DIRECTIONS: an un-retracted row must still count, or the arm above
    # would pass against a patterns() that counted nothing at all.
    check_('a row nobody retracted still counts',
           patterns(read(rl))['counts'].get('seed-gate') == 2)
    for bad, why in ((None, 'no target'), ('', 'empty target')):
        try:
            retract(bad, 'x', path=rl)
            check_('a retraction with %s is refused' % why, False)
        except BypassError:
            check_('a retraction with %s is refused' % why, True)
    try:
        retract('2026-09-16T01:00:00Z', '   ', path=rl)
        check_('a retraction with no reason is refused', False)
    except BypassError:
        check_('a retraction with no reason is refused', True)

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
    real = [r for r in rows if not r.get('unparseable')
            and r.get('check') != RETRACTION]
    struck = retracted_ats(rows)
    print('  overrides recorded : %d   (%d still stand, %d retracted)'
          % (len(real), len([r for r in real if r.get('at') not in struck]),
             len(struck)))
    print('  blanket (ALL)      : %d   <- a switch labelled for one purpose that '
          'disables ten' % p['blanket_uses'])
    if struck:
        # NAMED, not netted off. A count that silently shrank would be
        # indistinguishable from rows having been deleted, which is the thing
        # retraction exists to avoid.
        print('')
        print('  RETRACTED (%d) -- still in the file, not counted above:' % len(struck))
        for r in rows:
            if r.get('check') == RETRACTION:
                orig = next((o for o in rows if o.get('at') == r.get('retracts')), None)
                print('    %s  %s' % (r.get('retracts'),
                                      (orig or {}).get('command') or '(no command)'))
                print('      why: %s' % r.get('reason', '')[:200])
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
