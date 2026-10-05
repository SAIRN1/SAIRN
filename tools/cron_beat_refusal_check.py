#!/usr/bin/env python
"""A CRON REFUSAL THAT WRITES NO HEARTBEAT -- the FALSE GREEN, swept.

    python tools/cron_beat_refusal_check.py
    python tools/cron_beat_refusal_check.py --fixtures   # the criteria lock, alone
    python tools/cron_beat_refusal_check.py --all        # every refusal, cleared ones too
    python tools/cron_beat_refusal_check.py --quiet

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY.

── THE OUTAGE THIS COMES FROM, AND WHY IT WAS INVISIBLE ────────────────────
Recorded on 133b0989473d (2026-09-16) and register-only for twelve days:

    "recurrence is named: nothing sweeps for cron endpoints whose refusal paths
     return without beating."

`api/sairndental/send-reminder.js` returned 502 on a failed `dnt_appointments`
read and wrote NO heartbeat. Vercel's runtime-error table recorded that failure
**23 times between 2026-09-12 and 2026-09-14.**

**AND THE CONSEQUENCE WAS WORSE THAN SILENCE.** The job succeeds most hours and
failed about one in three, so the last successful beat stayed fresh and
`cron-watchdog` went on reporting `send-reminder=ok` through the entire outage.
**A FALSE GREEN, not a gap.** The failures were found in the provider's error
table -- which is precisely the work the heartbeat exists so nobody has to do.

The same defect in `api/audit-checkpoint.js` was easier: it refused on EVERY run,
so it produced a visible NEVER_BEAT. The dangerous shape is the intermittent one.

── THE CRITERION, AND THE ONE DISTINCTION THAT MAKES IT DECIDABLE ──────────
**Not every refusal should beat, and beating on the wrong one is a security
defect rather than a monitoring one.**

  A PRE-AUTH REFUSAL MUST NOT BEAT. A 401 from an unauthenticated caller is not
  the job failing -- and a beat written before the secret is checked would let
  anyone with the URL forge liveness for a job that never ran. That is strictly
  worse than no beat.

  A POST-AUTH REFUSAL MUST BEAT. Past the secret check, the caller IS the
  scheduler and a refusal IS the job failing. Returning without a beat leaves
  the watchdog reading a stale success.

So the sweep splits each handler at its authorisation check and reports only the
refusals BELOW it that reach a `return` with no `beat(` between.

── WHAT IT CANNOT SEE, stated rather than discovered later ─────────────────
  * A beat written inside a helper the refusal calls. The call is followed one
    level for locally-defined functions and no further, so a deeper indirection
    reads as missing and is a FALSE POSITIVE. `--all` prints the cleared rows so
    the ratio is visible.
  * Whether the beat's `outcome` is the RIGHT one. `failed` versus `partial` is a
    judgement about what the job did, and the record for this defect argues one
    specific case at length. Not decidable here.
  * A refusal expressed as a thrown exception caught by an outer handler that
    beats. The outer beat is real and this reads the inner path as bare.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                 # noqa: E402

CONTROLLED_BY = ['tests/run_cron_beat_refusal_probe.py']
CRITERIA_VERSION = '2026-09-28.1'

# The authorisation boundary. Everything BELOW the last of these in a handler is
# past the secret check and its refusals are the job failing.
AUTH_MARKERS = (
    'CRON_SECRET', 'authorization', 'Authorization', 'authHeader',
    'x-vercel-cron', 'unauthorized', 'Unauthorized',
)
REFUSAL = re.compile(r'res\.status\(\s*(4\d\d|5\d\d)\s*\)')
BEAT = re.compile(r'\bbeat\s*\(')
RETURN = re.compile(r'^\s*return\b')
# A LITERAL BACKSPACE CHARACTER LANDED IN THIS PATTERN'S FIRST DRAFT, so it could
# never match anything and _enclosing_if() returned None for every line -- which
# made two fixtures fail and would have made the pre-auth exemption dead code.
# This repo already records a regex that shipped with a literal backspace and
# could never match; that is why it is compiled at module level here, where it is
# visible, and why the control drives it on a real `if (` line rather than
# trusting it.
IF_LINE = re.compile(r'\bif\s*\(')

FINDING = 'FINDING'
CLEAN_PRE_AUTH = 'pre-auth refusal -- must NOT beat'
CLEAN_BEATS = 'beats before returning'
CLEAN_NO_RETURN = 'not a terminating refusal'
CLEAN_CANNOT_BEAT = "CANNOT beat -- the beat's own dependency is what is missing"


def beat_dependencies():
    """Environment names api/_lib/heartbeat.js needs in order to write at all.

    READ FROM THE HEARTBEAT MODULE, not retyped here. A refusal caused by one of
    these being missing is a refusal that CANNOT beat -- the table the beat goes
    into is unreachable -- and reporting it as a missing beat would demand an
    impossible fix. Retyping the list would let the two drift and turn a correct
    advisory into a false finding the day heartbeat.js gains a dependency.

    Returns None on a read failure, never an empty set: an empty set would silently
    turn every cannot-beat row back into a finding.
    """
    try:
        src = io.open(os.path.join(REPO, 'api', '_lib', 'heartbeat.js'),
                      encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    return set(re.findall(r'process\.env\.([A-Z][A-Z0-9_]+)', src))


def auth_line(lines):
    """The last line index carrying an authorisation marker IN CODE, or None.

    LAST rather than first: a handler may mention the secret in a comment far
    above the check. Using the first would put post-auth refusals above the
    boundary and silently exempt them, which is the failing direction.

    ── AND COMMENTS ARE NOW EXCLUDED, WHICH IS THE WHOLE POINT (2026-10-05) ──
    Taking the LAST marker ANYWHERE meant a single TRAILING COMMENT naming the
    secret pushed the boundary to the bottom of the file, and every post-auth
    refusal above it was then reported `pre-auth refusal -- must NOT beat`.
    DRIVEN, not reasoned: a handler whose 502 is a genuine FINDING reports
    FINDING, and the same handler with

        // NOTE: callers must send CRON_SECRET in the Authorization header.

    appended reports it CLEAN. One comment line, a real monitoring gap erased,
    and the tool said CLEAN -- the exact shape PR 1.11 exists for, in a checker
    rather than a gate.

    I REPORTED THIS FIXED ONCE AND IT WAS NOT. It was written up on 2026-09-29
    as an index row describing the "comment-armed disjunct", the structural
    `own_auth` test was added beside it, and the LINE-NUMBER disjunct was left
    in place -- so the finding stayed live while its record said otherwise.
    Re-raised as H2 seq 486 and fixed here.

    THE STRUCTURAL HALF IS UNTOUCHED. `own_auth` -- a refusal whose own nearest
    enclosing `if` names a marker -- carries the real work and is comment-proof
    by construction. This function is only the "sits above every marker"
    fallback, and the fallback is what needed the code/comment distinction.

    STRIPPED WITH tools/jscomments, NOT A REGEX OF MY OWN. That module already
    handles `//`, `/* */` and the case a hand-rolled stripper gets wrong -- a
    `//` inside a string literal -- and it is used by the inventory generator
    for the same reason.
    """
    try:
        import jscomments
        code = jscomments.strip_comments(chr(10).join(lines)).split(chr(10))
    except Exception:
        # FAIL TOWARD THE STRICTER ANSWER, never toward clean. If the stripper
        # cannot run, fall back to NO fallback boundary at all: `own_auth`
        # still classifies real pre-auth refusals, and anything that would only
        # have been exempted by the line-number test is reported instead of
        # waved through. A comment-stripper outage must not be able to hide a
        # finding -- that is the same failure, one layer up.
        return None
    if len(code) != len(lines):
        # Line-for-line correspondence is what makes the index usable. If the
        # stripper ever changes the line count, the index is meaningless and
        # refusing the fallback is the only safe answer.
        return None
    hits = [i for i, l in enumerate(code)
            if any(m in l for m in AUTH_MARKERS)]
    return hits[-1] if hits else None


def _enclosing_if(lines, i, back=6):
    """Index of the nearest `if (` line at or above `i`, or None.

    `back` bounds the lookback so a refusal deep inside a function body does not
    get attributed to an `if` forty lines up. It is a named parameter for the
    same reason the window below is: a fixed distance on source text is a shape
    this repo sweeps for, so it is visible rather than buried.
    """
    for k in range(i, max(-1, i - back) - 1, -1):
        if IF_LINE.search(lines[k]):
            return k
    return None


def refusals(src, window=14):
    """(line, status, verdict) for every refusal in one handler's source.

    `window` is the number of lines after the refusal in which a `return` and a
    `beat(` are looked for. A fixed window is a known weak spot -- this repo has
    a standing sweep for exactly that shape -- so it is a NAMED parameter, it is
    printed, and the control drives a beat placed at the window edge.
    """
    lines = src.split('\n')
    auth = auth_line(lines)
    deps = beat_dependencies()
    out = []
    for i, line in enumerate(lines):
        m = REFUSAL.search(line)
        if not m:
            continue
        status = m.group(1)
        tail = lines[i:i + window]
        # BEAT IS LOOKED FOR BEFORE THE REFUSAL TOO. The corrected shape in
        # send-reminder.js awaits beat() and THEN calls res.status(), so a
        # forward-only window would report the fix as the defect.
        head = lines[max(0, i - window):i]
        terminates = any(RETURN.match(t) for t in tail)
        beats = any(BEAT.search(t) for t in tail + head)
        # ── PRE-AUTH IS THE REFUSAL'S OWN CONDITION, NOT A LINE NUMBER ──────
        # The first version tested `i <= auth` against the LAST auth marker, and
        # two fixtures caught it immediately: the 401's `res.status` sits one
        # line BELOW the `if` that carries the marker, so the auth refusal itself
        # was judged and reported. Pushing the boundary down by a few lines would
        # have fixed the fixture and reintroduced the fixed-window shape this
        # repo has a standing sweep for.
        #
        # So the test is structural: a refusal is pre-auth when ITS OWN nearest
        # enclosing `if` names an auth marker, or when it sits above every marker
        # in the file.
        guard = _enclosing_if(lines, i)
        own_auth = guard is not None and any(m in lines[guard] for m in AUTH_MARKERS)
        # ── A REFUSAL THAT CANNOT BEAT, FOUND BY THE FIRST REAL RUN ──────────
        # All three of the first three findings were one shape: a POST-AUTH 500
        # for a missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY. Reporting those
        # as missing beats demands an IMPOSSIBLE fix -- beat() writes to Supabase
        # with exactly those variables, so on that path the table the beat would
        # go into is unreachable. cron-watchdog is the sharpest case: it is the
        # only reader of the heartbeat table.
        #
        # They are a REAL monitoring blind spot and are reported as such, in their
        # own state, with the out-of-band answer named: tools/cron_liveness_check.py
        # runs on GitHub Actions, a genuinely different scheduler, which is the
        # only thing that can cover a path that cannot self-report.
        cfg_block = '\n'.join(lines[max(0, i - window):i + 2])
        cannot = deps is not None and any(d in cfg_block for d in deps)
        if own_auth or (auth is not None and i <= auth):
            out.append((i + 1, status, CLEAN_PRE_AUTH))
        elif cannot and not beats:
            out.append((i + 1, status, CLEAN_CANNOT_BEAT))
        elif not terminates:
            out.append((i + 1, status, CLEAN_NO_RETURN))
        elif beats:
            out.append((i + 1, status, CLEAN_BEATS))
        else:
            out.append((i + 1, status, FINDING))
    return out


# ── THE FIXTURE LOCK (discipline 1) ──────────────────────────────────────────
FIXTURES = (
    # ── THE TRAILING-COMMENT FIXTURE, added 2026-10-05 (H2 seq 486) ──────────
    # FIRST, because it is the one this lock did not have and the reason the
    # defect survived a report of its own fix. A single comment naming the
    # secret BELOW a genuine post-auth finding used to push the line-number
    # boundary to the bottom of the file and report the finding as pre-auth.
    # If this fixture ever classifies as pre-auth again, the comment/code
    # distinction in auth_line() has been lost.
    ("""
module.exports = async (req, res) => {
  if (req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }
  const r = await fetch('https://example.invalid/x');
  if (!r.ok) {
    res.status(502).json({ error: 'upstream' });
    return;
  }
  res.status(200).json({ ok: true });
};
// NOTE: callers must send CRON_SECRET in the Authorization header.
""",
     [CLEAN_PRE_AUTH, FINDING],
     'a TRAILING COMMENT naming the secret must not exempt a post-auth '
     'refusal -- one comment line used to erase a real monitoring gap and '
     'report CLEAN'),

    ("""
  if (req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }
  var r = await fetch(url);
  if (!r.ok) {
    res.status(502).json({ error: 'Could not list appointments' });
    return;
  }
""", [CLEAN_PRE_AUTH, FINDING],
     'THE REAL OUTAGE: a 401 above the auth check is correct and must not beat; '
     'the 502 below it returned with no beat 23 times'),
    ("""
  if (req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }
  var r = await fetch(url);
  if (!r.ok) {
    await beat({ job: 'x', outcome: 'failed' });
    res.status(502).json({ error: 'Could not list appointments' });
    return;
  }
""", [CLEAN_PRE_AUTH, CLEAN_BEATS],
     'THE FIX for that outage -- beat() BEFORE res.status(), which a '
     'forward-only window would have reported as the defect'),
    ("""
  if (bad) {
    res.status(500).json({ error: 'Server configuration error' });
    return;
  }
  if (req.headers.authorization !== process.env.CRON_SECRET) {
    res.status(401).json({});
    return;
  }
""", [CLEAN_PRE_AUTH, CLEAN_PRE_AUTH],
     'a config refusal ABOVE the auth check is pre-auth too -- and beating there '
     'would let an unauthenticated caller forge liveness, which is worse than '
     'no beat'),
    ("""
  if (req.headers.authorization !== process.env.CRON_SECRET) {
    res.status(401).json({});
    return;
  }
  if (!rows) {
    res.status(502).json({ error: 'x' });
  }
  rows.forEach(function (r) { send(r); });
""", [CLEAN_PRE_AUTH, CLEAN_NO_RETURN],
     'a refusal that does NOT terminate is not this defect -- execution '
     'continues and a beat may come later'),
    ("""
  var r = await fetch(url);
  if (!r.ok) {
    res.status(502).json({ error: 'x' });
    return;
  }
""", [FINDING],
     'NO auth marker anywhere means no boundary, so every refusal is judged -- '
     'erring toward reporting, because an unauthenticated cron endpoint is its '
     'own finding and must not also buy an exemption here'),
)


def run_fixtures(verbose=False):
    bad = []
    for src, want, why in FIXTURES:
        got = [v for _l, _s, v in refusals(src)]
        if got != want:
            bad.append('EXPECTED %s, got %s -- %s' % (want, got, why))
        elif verbose:
            print('  ok   %-44s %s' % (','.join(want)[:42], why))
    return bad


# ── THE REAL RUN ─────────────────────────────────────────────────────────────
def cron_paths():
    """Handler files for every path in vercel.json's `crons`, plus the reason
    any declared cron could not be resolved -- never a silent short list."""
    import json
    could_not = []
    try:
        cfg = json.load(io.open(os.path.join(REPO, 'vercel.json'),
                                encoding='utf-8'))
    except Exception as e:                                       # noqa: BLE001
        return None, ['vercel.json unreadable: %s' % e]
    out = []
    for c in cfg.get('crons') or []:
        p = str(c.get('path') or '').lstrip('/')
        if not p:
            continue
        cand = os.path.join(REPO, p + '.js')
        if os.path.isfile(cand):
            out.append(p + '.js')
        else:
            could_not.append('%s -- declared in vercel.json, no handler at %s.js'
                             % (c.get('path'), p))
    return out, could_not


def main(argv):
    ap = argparse.ArgumentParser(add_help=True,
                                 description=__doc__.split('\n')[0])
    ap.add_argument('--fixtures', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    # PostToolUse/Write|Edit. Runs the CRITERIA LOCK only when the edit could
    # have moved what it locks -- this checker itself, or a cron handler -- and
    # is silent otherwise. Wired 2026-10-05 because the trailing-comment defect
    # survived a report of its own fix for six days with nothing running the
    # lock on a cadence.
    ap.add_argument('--hook', action='store_true')
    a = ap.parse_args(argv)

    if a.hook:
        # NEVER blocks and says nothing unless the lock actually FAILS. Fails
        # OPEN on an unreadable payload: a criteria lock must not be the thing
        # that stops an edit.
        try:
            payload = json.load(sys.stdin)
            fp = (payload.get('tool_input', {}) or {}).get('file_path', '') or ''
        except Exception:                                     # noqa: BLE001
        # DELIBERATE, and in the SAFE direction: a report-only hook must not
        # be the thing that stops a legitimate command. An unreadable payload
        # means this notice says nothing, never that the command is blocked.
        #
        # THE WORD IS IN THE FIRST LINE ON PURPOSE -- fail_open_scan.py reads a
        # window of ln-6 .. ln+3 around the `except`, so a reason written five
        # lines down is invisible to it. Learned on gh_token.py:296 earlier in
        # the same batch, where exactly that mistake left the site classified
        # DEPENDENCY-shaped through a first attempt at this comment.
            return 0
        fp = fp.replace('\\', '/')
        relevant = ('cron_beat_refusal_check.py' in fp
                    or '/api/cron-' in fp or 'heartbeat.js' in fp
                    or 'send-reminder' in fp)
        if not relevant:
            return 0
        bad = run_fixtures(verbose=False)
        if bad:
            print(json.dumps({'hookSpecificOutput': {
                'hookEventName': 'PostToolUse',
                'additionalContext':
                    'cron_beat_refusal_check CRITERIA LOCK FAILED after this '
                    'edit -- %d of %d fixtures misclassify. The checker no '
                    'longer classifies its own known cases, so any CLEAN it '
                    'reports is unearned. First failure: %s'
                    % (len(bad), len(FIXTURES), bad[0][:300])}}))
        return 0

    if not a.quiet:
        print('CRON REFUSAL WITHOUT A HEARTBEAT -- criteria %s' % CRITERIA_VERSION)

    bad = run_fixtures(verbose=(a.fixtures and not a.quiet))
    if bad:
        if not a.quiet:
            print('\nCRITERIA LOCK FAILED -- %d of %d fixtures misclassified.'
                  % (len(bad), len(FIXTURES)))
            for b in bad:
                print('  ! %s' % b)
            print('\nNOTHING REAL WAS JUDGED.')
        return EXIT_COULD_NOT_RUN
    if not a.quiet:
        print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
              'sources only' % (len(FIXTURES), len(FIXTURES)))
    if a.fixtures:
        return 0

    paths, could_not = cron_paths()
    if paths is None:
        if not a.quiet:
            for c in could_not:
                print('  ? %s' % c)
        return EXIT_COULD_NOT_RUN
    if not paths:
        if not a.quiet:
            print('\nNO CRON HANDLERS RESOLVED. That is not a clean sweep -- '
                  'vercel.json declared\nnone, or none resolved to a file.')
        return EXIT_COULD_NOT_RUN

    findings, cleared = [], []
    for rel in paths:
        try:
            src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                          errors='replace').read()
        except OSError as e:
            could_not.append('%s -- could not read: %s' % (rel, e))
            continue
        for line, status, verdict in refusals(src):
            row = (rel, line, status, verdict)
            (findings if verdict == FINDING else cleared).append(row)

    if not a.quiet:
        print('read %d cron handler(s) declared in vercel.json; %d refusal path(s) '
              'judged' % (len(paths), len(findings) + len(cleared)))
        print('CHECKED / UNIVERSE: %d of %d declared crons resolved to a handler.'
              % (len(paths), len(paths) + len([c for c in could_not
                                               if 'no handler at' in c])))
        print('  A REFUSAL IS JUDGED ONLY BELOW THE AUTH BOUNDARY. A pre-auth '
              '401 must NOT beat --\n  a beat before the secret is checked lets '
              'anyone with the URL forge liveness for a\n  job that never ran, '
              'which is worse than no beat at all.')
        # ── CANNOT-BEAT IS PRINTED ALWAYS, NEVER FOLDED INTO CLEAN ──────────
        # These are not findings -- the fix is impossible locally -- and they are
        # not nothing either. A path that cannot self-report is a monitoring blind
        # spot, and a clean line that swallowed it would be this tool committing
        # the false-green defect it exists to find.
        _cb = [r for r in cleared if r[3] == CLEAN_CANNOT_BEAT]
        if _cb:
            _deps = ' / '.join(sorted(beat_dependencies() or ())) or 'beat dependency'
            print('\nCANNOT BEAT (%d) -- NOT findings, and NOT nothing:' % len(_cb))
            for rel, line, status, _v in _cb:
                print('  ~ %s:%d  a %s refusal for a missing %s'
                      % (rel, line, status, _deps))
            print('  beat() writes to Supabase with those same variables, so on '
                  'these paths the')
            print('  table the beat would go into is unreachable. '
                  'api/cron-watchdog.js is the')
            print('  sharpest case: it is the ONLY reader of the heartbeat table.')
            print('  THE ANSWER IS ALREADY BUILT AND IS OUT OF BAND -- '
                  'tools/cron_liveness_check.py')
            print('  runs on GitHub Actions, a genuinely different scheduler from '
                  "Vercel's. A path")
            print('  that cannot self-report can only be covered by something not '
                  'on the same bus.')
        if a.all:
            print('\nCLEARED (%d), with the reason each cleared:' % len(cleared))
            for rel, line, status, verdict in cleared:
                print('  - %-42s :%-5s %s  %s' % (rel, line, status, verdict))

    return finish(
        ['%s:%d  a %s refusal BELOW the auth check returns with no beat() -- '
         'the watchdog keeps reading the last success' % (rel, line, status)
         for rel, line, status, _v in findings],
        could_not_run=could_not, quiet=a.quiet,
        clean_line='\nCLEAN -- every post-auth refusal in every declared cron '
                   'handler writes a heartbeat before returning.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
