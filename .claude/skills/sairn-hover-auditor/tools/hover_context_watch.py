#!/usr/bin/env python
"""hover_context_watch.py -- the 85% WRAP-UP WATCHER, mechanical, no hooks.
Built H1 b72, item 5b.

WHAT IT IS FOR. The standing wrap rule is now "at 85% REAL context, stop at
the next safe point and wrap up automatically". b68 moved that threshold
from 70% to 80% and b72 moved it to 85%; what has been missing at every
step is a thing that WATCHES it rather than a number somebody remembers.
hover_context_measure.py already answers "what is the real figure"; this
answers "and what must happen now", in one line a caller cannot misread.

THE HONEST LIMIT, FIRST, BECAUSE IT IS THE WHOLE SHAPE OF THIS TOOL.
**NO HOOKS, by instruction -- so this tool CANNOT FIRE BY ITSELF.** It is
mechanical in the sense that its verdict is deterministic, derived from a
real measured number, and carries an exit code a caller can gate on. It is
NOT autonomous. Something has to call it. A watcher that must be called can
be forgotten, and pretending otherwise would be the exact defect this role
files against other people's checks -- a control that only exists when
somebody remembers it.

Three things make that limit as small as it can honestly be made:
  1. It is CHEAP -- one file read, no network, no model call -- so there is
     no reason not to call it between items.
  2. Its output is an INSTRUCTION, not a number. At or past the threshold it
     prints the alert block and the ordered wrap-up checklist, so the caller
     does not have to remember what wrapping up means either.
  3. `--assert-under` makes it a GATE: non-zero exit at or past the
     threshold, so it can sit in front of any command a session runs before
     starting new work and refuse rather than advise.
Stated plainly in the output of every run, so nobody reads a passing run as
proof that something is standing guard.

WHY THE MEASUREMENT IS BORROWED AND FAILS CLOSED. Everything about reading
the real figure -- the usage fields, the sidechain exclusion, the declared-
vs-inferred window, the floor/ceiling honesty -- lives in
hover_context_measure.py and was paid for over three batches. A second
implementation here would be a second thing to keep in step, and the b71
closure-state work is the live example of what that costs. So this imports
it, and if the import fails it REFUSES (exit 2) rather than falling back to
an estimate: a watcher that guesses the number it is watching is worse than
no watcher, because its silence looks the same either way (PR SS1.11).

WHY THE PROJECT DIRECTORY IS DERIVED, NOT TAKEN FROM `HERE`.
hover_context_measure sets PROJECT_DIR from its own location, which is
correct when it runs from the operational directory and wrong when it runs
from the tracked archival copy. b71 lost real time to exactly that shape in
hover_backup_mirror.py -- a tool answering from a store 49 pushes stale
because it was run from the other copy. This tool therefore derives the
real transcript directory from the repo path and CHECKS it holds
transcripts, refusing if it does not.

Run:
  python hover_context_watch.py                     # verdict + exit code
  python hover_context_watch.py --assert-under      # gate form, refuses
  python hover_context_watch.py --simulate 850000   # drive it at 85%
  python hover_context_watch.py --simulate-pct 85   # same, as a percentage
  python hover_context_watch.py --selftest
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

EXIT_UNDER = 0
EXIT_WRAP_NOW = 1
EXIT_COULD_NOT_RUN = 2

# ── THE THRESHOLDS, AND THE ONE PLACE THEY LIVE ─────────────────────────────
# WRAP_PCT is the b72 standing rule. ALERT_PCT is deliberately LOWER: the
# fourth cross-domain discipline is "set the alarm tighter than the failure
# point", because an alarm that fires AT the limit leaves no room to act on
# it. 85% of 1M is 150,000 tokens of headroom; a wrap-up measured on this
# session costs roughly 25,000-30,000 (b69 crossed 78.5% -> 81.0% writing
# three documents). So the advisory fires at 78% -- far enough out that a
# session can finish the item it is on, and close enough that it is not
# crying wolf.
WRAP_PCT = 85.0
ALERT_PCT = 78.0

# The ordered checklist, kept HERE rather than in prose anywhere else, so the
# tool that detects the condition is the thing that says what to do about it.
WRAP_STEPS = (
    'Finish ONLY the item you are mid-way through. Start nothing new.',
    'Write SAIRN-handoff-H1-<batch>.md: committed/pushed state, every open '
    'item with its EXACT next step, claims held, transcript path.',
    'Commit and push without force; confirm HEAD == origin/main.',
    'Mirror-push the chain log and run the restore drill if it is due.',
    'Upload the handoff to Drive.',
    'Write the report, then the digest (30 lines MAX -- run the line count).',
    'Release the claim and set the status row to idle.',
    'Final chat message is the done-line and nothing else.',
)


def project_dir():
    """(path, why). The REAL transcript directory, derived from the repo
    rather than from this file's own location, and verified to hold
    transcripts. See the docstring for why `HERE` is not trusted here."""
    home = os.path.expanduser('~')
    cand = os.path.join(home, '.claude', 'projects',
                         'C--Users-marsh-Documents-SAIRN-hover')
    if not os.path.isdir(cand):
        return None, 'no transcript directory at %s' % cand
    import glob
    if not glob.glob(os.path.join(cand, '*.jsonl')):
        return None, ('%s holds no top-level *.jsonl transcript -- this is '
                       'not the session directory' % cand)
    return cand, ''


def _measure():
    """(tokens, window, model, why). Borrowed, and FAILS CLOSED."""
    pdir, why = project_dir()
    if pdir is None:
        return None, None, None, why
    try:
        sys.path.insert(0, HERE)
        import hover_context_measure as M
    except Exception as e:
        return None, None, None, (
            'hover_context_measure is unavailable (%s). This watcher will '
            'NOT fall back to an estimate -- a watcher that guesses the '
            'number it is watching is worse than no watcher.' % e)
    try:
        # (path, reason) -- NOT a bare path. The first version of this
        # function passed the whole tuple to open() and the real read died
        # with "expected str, bytes or os.PathLike object, not tuple". The
        # fixtures did not catch it because W13 and W14 exercise the
        # fail-closed and directory-derivation arms only; nothing drove the
        # real transcript read until the tool was pointed at the live
        # session. That is the three-for-three base rate SKILL.md records
        # for a freshly written scanner, hit again, and the fail-closed
        # design is what made it a visible COULD NOT RUN instead of a
        # fabricated all-clear. W15 below now drives this path.
        path, pick_why = M.pick_session_file(pdir)
        if path is None:
            return None, None, None, 'no session transcript: %s' % pick_why
        with open(path, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        # ALSO A TUPLE: (usage_dict, turn_index, reason). The second tuple
        # bug in the same function, found by W15 the moment it existed --
        # which is the argument for W15 rather than a point against it. Both
        # came from reading these functions' NAMES instead of their return
        # contracts; both docstrings say the shape plainly.
        usage, turn_idx, usage_why = M.last_assistant_usage(lines)
        if not usage:
            return None, None, None, ('no assistant turn carrying a usage '
                                       'object in %s: %s' % (path, usage_why))
        tokens = M.context_figure(usage)
        model = M.model_of(lines)
        sid = os.path.basename(path).rsplit('.', 1)[0]
        decl, _ = M.declared_window(sid)
        win, win_why = M.window_for(model, M.observed_max_prompt(lines),
                                     declared=decl)
        if win is None:
            return None, None, None, 'window could not be settled: %s' % win_why
        return tokens, win, model, ''
    except Exception as e:
        return None, None, None, 'measurement failed: %s: %s' % (
            type(e).__name__, e)


def verdict(pct):
    """'WRAP-NOW' | 'ALERT' | 'UNDER'. Pure, so the fixtures can drive every
    arm without a transcript."""
    if pct >= WRAP_PCT:
        return 'WRAP-NOW'
    if pct >= ALERT_PCT:
        return 'ALERT'
    return 'UNDER'


def render(tokens, window, model, simulated=False):
    """The block a caller reads. Returns (text, verdict)."""
    pct = 100.0 * tokens / window
    v = verdict(pct)
    out = []
    bar = '=' * 72
    if simulated:
        out.append('*** SIMULATED READING -- NOT THIS SESSION\'S REAL FIGURE '
                   '***')
    out.append('CONTEXT WATCH: %s tokens of %s = %.1f%%  (model %r)'
               % ('{:,}'.format(tokens), '{:,}'.format(window), pct, model))
    out.append('thresholds: ALERT at %.0f%%, WRAP at %.0f%%  -- verdict %s'
               % (ALERT_PCT, WRAP_PCT, v))
    if v == 'WRAP-NOW':
        out += [bar,
                'MICHAEL -- H1 IS WRAPPING UP. This is the alert, not a '
                'warning: real measured context is at or past the %.0f%% '
                'standing threshold, so this session is stopping at the next '
                'safe point and closing out rather than starting anything '
                'new.' % WRAP_PCT,
                bar,
                'WRAP-UP CHECKLIST, in order:']
        for i, s in enumerate(WRAP_STEPS, 1):
            out.append('  %d. %s' % (i, s))
        out.append(bar)
    elif v == 'ALERT':
        out += [bar,
                'ADVISORY, fired EARLY ON PURPOSE (%.0f%% not %.0f%%): a '
                'wrap-up on this session costs roughly 25,000-30,000 tokens, '
                'so an alarm at the limit leaves no room to act on it. '
                'Finish the current item; do not start a large new one.'
                % (ALERT_PCT, WRAP_PCT),
                bar]
    else:
        out.append('Under both thresholds -- a measured all-clear, not an '
                   'unrun check.')
    out.append('NO HOOKS: this tool cannot fire by itself and nothing is '
               'standing guard between calls. Call it between items, or put '
               '--assert-under in front of work that should not start.')
    return '\n'.join(out), v


def selftest():
    ok = [0]
    bad = [0]

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   %s' % name)
        else:
            bad[0] += 1
            print('  FAIL %s' % name)

    ck('W1 the pure verdict is UNDER below the advisory threshold',
       verdict(42.2) == 'UNDER')
    ck('W2 ALERT fires at the advisory threshold, which is DELIBERATELY '
       'lower than the wrap threshold (discipline 4: set the alarm tighter '
       'than the failure point)', verdict(ALERT_PCT) == 'ALERT')
    ck('W3 one tenth under the advisory threshold is still UNDER -- the '
       'boundary is >=, not >', verdict(ALERT_PCT - 0.1) == 'UNDER')
    ck('W4 WRAP-NOW fires AT the threshold, not just past it -- an "at or '
       'past" rule that only fires past it silently skips the exact '
       'boundary case', verdict(WRAP_PCT) == 'WRAP-NOW')
    ck('W5 WRAP-NOW holds above it', verdict(99.9) == 'WRAP-NOW')
    ck('W6 ALERT does not swallow WRAP-NOW: the band between the two is '
       'ALERT and the top is WRAP',
       verdict(WRAP_PCT - 0.1) == 'ALERT' and verdict(WRAP_PCT) == 'WRAP-NOW')

    txt, v = render(850000, 1000000, 'claude-opus-5[1m]')
    ck('W7 at exactly 85%% the rendered block is the WRAP alert, names '
       'Michael, and carries all %d checklist steps' % len(WRAP_STEPS),
       v == 'WRAP-NOW' and 'MICHAEL' in txt
       and all(s[:28] in txt for s in WRAP_STEPS))
    ck('W8 the WRAP block states the no-hooks limit rather than implying the '
       'tool is standing guard', 'NO HOOKS' in txt)

    txt2, v2 = render(422000, 1000000, 'claude-opus-5[1m]')
    ck('W9 at 42.2% of a 1M window the block is an all-clear and carries NO checklist, so '
       'an under-threshold run cannot be mistaken for a wrap instruction',
       v2 == 'UNDER' and 'WRAP-UP CHECKLIST' not in txt2)
    ck('W10 the all-clear still states the no-hooks limit -- the honest '
       'limit is not only printed when it is bad news',
       'NO HOOKS' in txt2)

    txt3, v3 = render(800000, 1000000, 'claude-opus-5[1m]')
    ck('W11 at 80% of a 1M window -- the OLD b68 threshold -- the verdict is ALERT and '
       'NOT wrap, which is the measurable difference the b72 change makes',
       v3 == 'ALERT' and 'WRAP-UP CHECKLIST' not in txt3)

    txt4, _ = render(850000, 1000000, 'claude-opus-5[1m]', simulated=True)
    ck('W12 a simulated reading is LABELLED as simulated in its own output, '
       'so a pasted proof-run can never be mistaken for a real measurement',
       'SIMULATED' in txt4)

    # FAIL-CLOSED ARM. Block the borrowed dependency the way an absent file
    # would and confirm it refuses rather than estimating.
    import importlib
    saved = sys.modules.get('hover_context_measure')
    sys.modules['hover_context_measure'] = None
    try:
        t, w, m, why = _measure()
        ck('W13 FAIL-CLOSED: with hover_context_measure unavailable the '
           'watcher REFUSES and names the tool, rather than falling back to '
           'an estimate',
           t is None and 'hover_context_measure' in (why or ''))
    finally:
        if saved is not None:
            sys.modules['hover_context_measure'] = saved
        else:
            del sys.modules['hover_context_measure']
        importlib.invalidate_caches()

    pdir, why = project_dir()
    ck('W14 the transcript directory is DERIVED and VERIFIED to hold '
       'transcripts rather than taken from this file\'s own location (%s)'
       % (pdir or why), pdir is not None)

    # ── W15: DRIVE THE REAL READ. Added after the real read crashed on a
    # tuple while all 14 arms above passed -- every one of them exercised a
    # pure function or a refusal, and none of them opened a transcript. An
    # arm that only tests the parts that cannot fail is the shape this role
    # files against other people's suites.
    t, w, m, why = _measure()
    ck('W15 the REAL measurement path returns a usable (tokens, window, '
       'model) against this session\'s own transcript -- %s'
       % ('%s of %s, model %r' % ('{:,}'.format(t), '{:,}'.format(w), m)
          if t is not None else 'REFUSED: %s' % why),
       t is not None and w is not None and t > 0 and w > 0)
    if t is not None:
        ck('W16 and the real figure renders to one of the three verdicts '
           'rather than raising', verdict(100.0 * t / w) in
           ('UNDER', 'ALERT', 'WRAP-NOW'))

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return EXIT_UNDER if not bad[0] else EXIT_WRAP_NOW


def main(argv):
    if '--selftest' in argv:
        return selftest()

    simulated = False
    window = None
    model = 'simulated'
    if '--simulate-pct' in argv:
        pct = float(argv[argv.index('--simulate-pct') + 1])
        window = 1000000
        tokens = int(round(window * pct / 100.0))
        simulated = True
    elif '--simulate' in argv:
        tokens = int(argv[argv.index('--simulate') + 1])
        window = 1000000
        simulated = True
    else:
        tokens, window, model, why = _measure()
        if tokens is None:
            print('COULD NOT RUN: %s' % why)
            print('This is a THIRD STATE and is never folded into an '
                  'all-clear: the watcher did not run, which is not the same '
                  'as being under the threshold.')
            return EXIT_COULD_NOT_RUN

    txt, v = render(tokens, window, model, simulated=simulated)
    print(txt)
    if '--assert-under' in argv and v == 'WRAP-NOW':
        print('REFUSED by --assert-under: do not start new work.')
        return EXIT_WRAP_NOW
    return EXIT_WRAP_NOW if v == 'WRAP-NOW' else EXIT_UNDER


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
