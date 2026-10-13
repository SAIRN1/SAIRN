#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b6, queue item 1 -- the approved per-gate skip
"""A SCOPED, LOGGED, EXPIRING exemption for ONE named gate.

    SAIRN_SKIP=seed-gate SAIRN_SKIP_WHY="the seed files are mid-migration and
    Michael is running sql/x.sql now; the drift IS the migration" git push ...

    python tools/gate_skip.py --gates          # the valid ids, derived
    python tools/gate_skip.py --check          # is a skip active for this push?
    python tools/gate_skip.py --fixtures       # the criteria lock

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── WHY, AND THE MEASUREMENT IS THE ARGUMENT ────────────────────────────────
docs/BYPASS-LOG.jsonl, read 2026-10-13: 94 rows, and EIGHTY of them
`blanket: true` -- `SAIRN_SEED_GATE=off`, which returns from the push hook
before a single check runs. Only 13 carry a reason beyond the mechanism.

Nobody chose to switch off everything. The blanket form was the only thing
available, so the blanket form is what the log records -- and every one of
those 80 pushes also skipped the credential scanner, the seed check, the
register feed, the Tier A gate and the derived-document check, none of which
the session had any complaint about.

AND IT CANNOT BE STOPPED FROM OUTSIDE. Measured in b5 against the real
permission matcher: a deny rule cannot match `SAIRN_SEED_GATE=off` because
deny rules match PAST a leading env assignment, and the documented
fall-out-of-allow behaviour did not hold either -- the push ran with no
prompt. So this file is not a second layer. It is the only available control,
which is why it is built to be the CHEAPER path rather than the stricter one.

── THE FOUR FIELDS, AND WHY EACH IS REQUIRED ───────────────────────────────
  GATE     one id from a closed list the gates PUBLISH. An unknown id is a
           REFUSAL, never a silent no-op: an override that matched nothing
           while the push proceeded would log a skip that did not happen.
  AGENT    derived from the session identity, never passed in. A skip whose
           author is self-declared is a skip with no author.
  REASON   required, >= 40 characters, and REFUSED if it merely restates the
           mechanism. 81 of 94 existing rows are populated with the mechanism;
           that field exists and means nothing, which is the shape the defect
           register already refused for `not-citable`.
  EXPIRY   every skip dies. Default 30 minutes, ceiling 4 hours -- the same
           window a claim gets, because a skip is a claim about one push.

── WHAT IS NOT SKIPPABLE AT ALL ────────────────────────────────────────────
Named here rather than discovered later. A skip is for a gate whose INPUT is
temporarily wrong, not for a gate whose FINDING is inconvenient:

  credentials  a leaked key is not a false positive somebody is in a hurry
               about
  syntax       `node --check` failing means the push breaks the app
  hook-integrity  skipping the thing that notices disarmament hides every
               other skip

── NO `all`, NO COMMA LIST ─────────────────────────────────────────────────
Two gates to skip is two decisions. A comma list is the blanket form wearing
a different spelling, and it is the first thing that will be asked for.
"""
import io
import json
import os
import re
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-13.1'

ENV_GATE = 'SAIRN_SKIP'
ENV_WHY = 'SAIRN_SKIP_WHY'
ENV_MINUTES = 'SAIRN_SKIP_MINUTES'

DEFAULT_MINUTES = 30
MAX_MINUTES = 240
MIN_REASON = 40

# ── THE GATE IDS. A CLOSED LIST, AND IT IS DECLARED HERE ON PURPOSE ────────
# The design said "derive it by importing the gates". That was the right
# instinct and the wrong mechanism: tools/sairn_push_gate_hook.py is a single
# 3,500-line module whose checks are numbered sections rather than objects, so
# "import the gates" would mean importing the gate that imports this file.
# A circular import at the top of a BLOCKING push hook is a worse failure than
# a list that needs one edit when a check is added.
#
# SO THE LIST IS EXPLICIT AND THE DRIFT IS CHECKED INSTEAD: --gates prints it,
# the gate's own numbered-check count is compared against it, and a mismatch is
# a FINDING rather than a silent divergence. That is the same trade the hook
# already makes for its own `## The N Checks` count.
GATES = {
    'seed-gate': 'the seed files must match the live licence',
    'tier-a': 'a Tier A change needs a recorded review obligation',
    'register-feed': 'a commit that closes a defect must feed the register',
    'external-files': 'a tool or script outside git must be indexed',
    'derived-docs': 'a generated document must match its sources',
    'scrutiny-ledger': 'self-checking files changed in a push get a row',
    'credential-sql': 'SQL writing credential rows needs the recoverability guard',
    'control-bytes': 'no control characters in tracked text',
}

UNSKIPPABLE = {
    'credentials': 'a leaked key is not a false positive somebody is in a '
                   'hurry about',
    'syntax': 'a syntax failure means the push breaks the app',
    'hook-integrity': 'skipping the check that notices disarmament would hide '
                      'every other skip',
}

# A reason that only restates the mechanism. 81 of the 94 existing log rows
# are exactly this, which is why it is refused rather than merely counted.
BOILERPLATE_RE = re.compile(
    r'(?i)^[\s\W]*(the\s+)?(sairn[_ ]?seed[_ ]?gate|sairn[_ ]?skip|skip|'
    r'override|bypass|off|blanket|gate|push)[\s\W]*$')


def session_name():
    """The agent, DERIVED. A self-declared author is no author."""
    try:
        import sairn_session_identity as sid
        return sid.session_name()
    except Exception:                                            # noqa: BLE001
        return ''


def _skip_dir():
    return os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS',
                        'gate-skips')


def skip_path(agent, gate):
    return os.path.join(_skip_dir(), '%s-%s.json' % (agent or 'unknown', gate))


def validate(gate, why, minutes, agent):
    """-> (ok, list_of_refusals). Every refusal names what to do instead."""
    bad = []
    g = (gate or '').strip()
    if not g:
        bad.append('no gate named. %s must carry exactly one gate id -- run '
                   '`python tools/gate_skip.py --gates` for the list.' % ENV_GATE)
    elif g in UNSKIPPABLE:
        bad.append('%r is NOT SKIPPABLE: %s' % (g, UNSKIPPABLE[g]))
    elif ',' in g or g.lower() == 'all':
        bad.append('%r names more than one gate. There is no `all` and no comma '
                   'list -- two gates to skip is two decisions, and a comma '
                   'list is the blanket form with a different spelling.' % g)
    elif g not in GATES:
        bad.append('%r is not a gate id. An unknown id is REFUSED rather than '
                   'ignored: a skip that matched nothing, while the push '
                   'proceeded, would record a skip that never happened. Known: '
                   '%s' % (g, ', '.join(sorted(GATES))))

    w = (why or '').strip()
    if not w:
        bad.append('%s is REQUIRED. A skip with no reason is the field that '
                   'already means nothing in 81 of the 94 existing bypass '
                   'rows.' % ENV_WHY)
    elif len(w) < MIN_REASON:
        bad.append('%s is %d characters and the minimum is %d. Say what the '
                   'gate would have refused and why that is acceptable on this '
                   'push.' % (ENV_WHY, len(w), MIN_REASON))
    elif BOILERPLATE_RE.match(w):
        bad.append('%s only restates the mechanism (%r). The required shape is '
                   'WHAT the gate would have refused and WHY that is '
                   'acceptable here.' % (ENV_WHY, w[:40]))

    try:
        m = int(minutes)
    except Exception:                                            # noqa: BLE001
        bad.append('%s must be a whole number of minutes.' % ENV_MINUTES)
        m = 0
    if m <= 0 or m > MAX_MINUTES:
        bad.append('expiry must be between 1 and %d minutes (got %r). Every '
                   'skip dies; a skip that does not is an exemption.'
                   % (MAX_MINUTES, minutes))

    if not (agent or '').strip():
        bad.append('the agent could not be derived from the session identity, '
                   'so this skip would have no author. Refused rather than '
                   'recorded as "unknown".')
    return (not bad), bad


def requested():
    """-> (gate, why, minutes) from the environment. Nothing is defaulted
    except the expiry, and that default is stated in the record."""
    return (os.environ.get(ENV_GATE, ''),
            os.environ.get(ENV_WHY, ''),
            os.environ.get(ENV_MINUTES, str(DEFAULT_MINUTES)))


def grant(gate, why, minutes, agent, now=None, tip=None):
    """Write the skip record. Returns the record written."""
    now = float(now if now is not None else time.time())
    rec = {
        'gate': gate,
        'agent': agent,
        'reason': why.strip(),
        'granted_at': now,
        'expires_at': now + int(minutes) * 60,
        'minutes': int(minutes),
        'tip': tip,
        'criteria': CRITERIA_VERSION,
        # Filled in by the gate when it knows what it WOULD have said. A skip
        # that does not record what it let through is a count, not evidence.
        'skipped_findings': None,
    }
    os.makedirs(_skip_dir(), exist_ok=True)
    io.open(skip_path(agent, gate), 'w', encoding='utf-8',
            newline=chr(10)).write(json.dumps(rec, indent=2) + chr(10))
    return rec


def active(gate, agent=None, now=None):
    """-> (record, '') if a live skip covers this gate, else (None, why_not)."""
    agent = agent if agent is not None else session_name()
    if not agent:
        return None, 'the agent could not be derived, so no skip can apply'
    p = skip_path(agent, gate)
    if not os.path.isfile(p):
        return None, 'no skip recorded for %s/%s' % (agent, gate)
    try:
        rec = json.loads(io.open(p, encoding='utf-8').read())
    except Exception as exc:                                     # noqa: BLE001
        # UNREADABLE IS NOT GRANTED. An exemption file that cannot be parsed is
        # the one case where failing open would be indistinguishable from a
        # real grant.
        return None, 'the skip record at %s could not be read (%s), so it is '\
                     'NOT honoured' % (p, exc)
    now = float(now if now is not None else time.time())
    if float(rec.get('expires_at') or 0) <= now:
        age = (now - float(rec.get('expires_at') or 0)) / 60.0
        return None, 'the skip for %s expired %.0f minute(s) ago' % (gate, age)
    if rec.get('gate') != gate or rec.get('agent') != agent:
        return None, 'the skip record names %r/%r, not %r/%r' % (
            rec.get('agent'), rec.get('gate'), agent, gate)
    return rec, ''


def record_findings(gate, findings, agent=None):
    """Write back WHAT the gate would have refused. Best-effort by design:
    this runs inside a blocking hook and must never deny a push over its own
    bookkeeping -- but a missing field is visible, unlike a missing row."""
    agent = agent if agent is not None else session_name()
    p = skip_path(agent, gate)
    try:
        rec = json.loads(io.open(p, encoding='utf-8').read())
        rec['skipped_findings'] = findings
        io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(
            json.dumps(rec, indent=2) + chr(10))
        return True
    except Exception:                                            # noqa: BLE001
        return False


def log(gate, rec, findings=None):
    """One row in BYPASS-LOG, SCOPED rather than blanket."""
    try:
        import bypass_log
        detail = rec.get('reason', '')
        if findings:
            detail += ' || WOULD HAVE REFUSED: ' + '; '.join(
                str(f)[:160] for f in findings[:6])
        bypass_log.record(gate, 'SCOPED skip of %s only, expiring %s -- %s'
                          % (gate, time.strftime(
                              '%H:%M:%SZ', time.gmtime(rec['expires_at'])),
                             detail),
                          tip=rec.get('tip'))
        return True
    except Exception:                                            # noqa: BLE001
        return False


BLANKET_REFUSAL = [
    '',
    'REFUSED: SAIRN_SEED_GATE=off is the BLANKET form and it no longer works.',
    '',
    'It returned from this hook before a single check ran -- the seed gate, the',
    'Tier A gate, the register feed, the credential scanner, the derived-document',
    'check, all of them -- and docs/BYPASS-LOG.jsonl records 80 of 94 overrides',
    'taking that shape. Nobody chose to switch off everything; it was the only',
    'thing available.',
    '',
    'USE THE SCOPED FORM. One gate, a real reason, an expiry:',
    '',
    '    SAIRN_SKIP=<gate> SAIRN_SKIP_WHY="<what this gate would have refused',
    '    and why that is acceptable on this push>" git push origin main',
    '',
    '    python tools/gate_skip.py --gates     # the ids',
    '',
    'The reason is REQUIRED, must be at least %d characters, and is refused if it'
    % MIN_REASON,
    'only restates the mechanism. The skip expires in %d minutes by default and'
    % DEFAULT_MINUTES,
    'never lives longer than %d. Every grant is logged as SCOPED, with the' % MAX_MINUTES,
    'findings the gate WOULD have raised written into the record.',
    '',
    'Three gates refuse to be skipped at all: %s.' % ', '.join(sorted(UNSKIPPABLE)),
    '',
]


# ── THE CRITERIA LOCK ───────────────────────────────────────────────────────
# Locked against fixtures before the tool is wired into anything, and in BOTH
# directions: what must be refused, and what must be granted. A validator with
# only refusing fixtures passes trivially by refusing everything.
GOOD_WHY = ('the seed files are mid-migration because Michael is running '
            'sql/sairnbuild_data_schema.sql right now, so the drift this gate '
            'sees IS the migration rather than a defect')

FIXTURES = (
    ('a real gate, a real reason, a sane expiry', 'seed-gate', GOOD_WHY, 30, True),
    ('an unknown gate id', 'seed-gte', GOOD_WHY, 30, False),
    ('an unskippable gate', 'credentials', GOOD_WHY, 30, False),
    ('all', 'all', GOOD_WHY, 30, False),
    ('a comma list', 'seed-gate,tier-a', GOOD_WHY, 30, False),
    ('no gate', '', GOOD_WHY, 30, False),
    ('no reason', 'seed-gate', '', 30, False),
    ('a reason under the minimum', 'seed-gate', 'mid-migration', 30, False),
    ('a reason that only restates the mechanism', 'seed-gate',
     'SAIRN_SEED_GATE=off' + ' ' * 30, 30, False),
    ('expiry of zero', 'seed-gate', GOOD_WHY, 0, False),
    ('expiry over the ceiling', 'seed-gate', GOOD_WHY, MAX_MINUTES + 1, False),
    ('expiry exactly at the ceiling is ALLOWED -- the bound is <=',
     'seed-gate', GOOD_WHY, MAX_MINUTES, True),
    ('a non-numeric expiry', 'seed-gate', GOOD_WHY, 'soon', False),
)


def run_fixtures():
    print('GATE SKIP -- criteria lock %s' % CRITERIA_VERSION)
    bad = 0
    for name, gate, why, minutes, want_ok in FIXTURES:
        ok, refusals = validate(gate, why, minutes, 'cc')
        mark = 'ok  ' if ok == want_ok else 'FAIL'
        if ok != want_ok:
            bad += 1
        print('  %s %-56s granted=%-5s wanted=%s' % (mark, name, ok, want_ok))
        if ok != want_ok:
            for r in refusals:
                print('         %s' % r[:130])
    # AND THE AGENT HALF, which no fixture above can reach because they all
    # pass a real one.
    ok, refusals = validate('seed-gate', GOOD_WHY, 30, '')
    mark = 'ok  ' if not ok else 'FAIL'
    if ok:
        bad += 1
    print('  %s %-56s granted=%-5s wanted=False'
          % (mark, 'an undetectable agent', ok))
    print('  %d/%d fixtures classify correctly' % (len(FIXTURES) + 1 - bad,
                                                   len(FIXTURES) + 1))
    return EXIT_FINDING if bad else EXIT_CLEAN


HOOK = os.path.join(TOOLS, 'sairn_push_gate_hook.py')


def wired_gates():
    """Which ids the push hook actually PASSES to deny(), read from the file.

    ── A DECLARED-BUT-UNWIRED ID IS THE FAILURE THIS ANSWERS ────────────────
    GATES is a list in this file; the wiring is `deny(..., gate='x')` in the
    hook. Those two can disagree, and the disagreement is invisible from
    either side: a session would request a valid id, be granted a skip, see
    the gate deny anyway, and have nothing to read. So the wiring is MEASURED
    rather than assumed, and the mismatch is printed as a finding.

    Read as TEXT, not by import: importing a 3,500-line blocking push hook to
    ask it a question is a cost and a risk this does not need.
    """
    try:
        src = io.open(HOOK, encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    return set(re.findall(r"gate=['\"]([a-z0-9-]+)['\"]", src))


def cmd_gates():
    print('SKIPPABLE GATES (%d) -- one id per skip, never a list:' % len(GATES))
    wired = wired_gates()
    for g in sorted(GATES):
        if wired is None:
            mark = '  ?'
        else:
            mark = 'WIRED' if g in wired else '  --'
        print('  %-5s %-18s %s' % (mark, g, GATES[g]))
    print('')
    print('NOT SKIPPABLE (%d), and this is not configurable:' % len(UNSKIPPABLE))
    for g in sorted(UNSKIPPABLE):
        print('        %-18s %s' % (g, UNSKIPPABLE[g]))
    print('')
    if wired is None:
        print('COULD NOT READ the push hook, so WIRED is unknown for every id '
              'above.')
        print('That is not a pass: an unwired id grants a skip the gate then '
              'ignores.')
        return EXIT_COULD_NOT_RUN
    unwired = sorted(set(GATES) - wired)
    stray = sorted(wired - set(GATES) - set(UNSKIPPABLE))
    if unwired:
        print('%d DECLARED BUT NOT WIRED: %s' % (len(unwired),
                                                 ', '.join(unwired)))
        print('  A skip for one of these is GRANTED and then IGNORED by the '
              'gate, because')
        print('  no deny() in the hook passes that id yet. Requesting one is '
              'not an error')
        print('  and not an exemption either -- it does nothing, and this line '
              'is the only')
        print('  place that says so. Wiring each is one `gate=` kwarg at that '
              'check\'s deny().')
    if stray:
        print('%d WIRED BUT NOT DECLARED: %s -- the hook passes an id this '
              'file does not know, so the skip can never be granted.'
              % (len(stray), ', '.join(stray)))
    if unwired or stray:
        return EXIT_FINDING
    print('Every declared id is wired.')
    return EXIT_CLEAN


def cmd_check():
    gate, why, minutes = requested()
    agent = session_name()
    print('GATE SKIP -- criteria %s' % CRITERIA_VERSION)
    print('  agent    : %s' % (agent or '(not derivable)'))
    print('  requested: %s' % (gate or '(nothing)'))
    if not gate:
        print('')
        print('No skip requested. Every gate runs.')
        return EXIT_CLEAN
    ok, refusals = validate(gate, why, minutes, agent)
    if not ok:
        print('')
        print('REFUSED (%d):' % len(refusals))
        for r in refusals:
            print('  ! %s' % r)
        return EXIT_FINDING
    rec = grant(gate, why, minutes, agent)
    print('')
    print('GRANTED for %s only, expiring in %d minute(s).' % (gate, rec['minutes']))
    print('  record : %s' % skip_path(agent, gate))
    print('  reason : %s' % rec['reason'][:140])
    print('')
    print('Every other gate still runs. The grant is logged as SCOPED.')
    return EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv:
        return run_fixtures()
    if '--gates' in argv:
        return cmd_gates()
    # THE LOCK RUNS BEFORE ANY REAL VERDICT. A validator whose own criteria are
    # broken grants a skip it never checked.
    if run_fixtures() != EXIT_CLEAN:
        print('')
        print('COULD NOT RUN: the criteria lock failed, so no verdict about a '
              'real skip is trustworthy. Nothing was granted.')
        return EXIT_COULD_NOT_RUN
    print('')
    return cmd_check()


if __name__ == '__main__':
    sys.exit(main())
