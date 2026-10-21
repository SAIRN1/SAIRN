#!/usr/bin/env python
"""hover_context_measure.py -- the real, measured context-window figure for
THIS role's own session, read from this session's own transcript jsonl,
replacing the digest's long-standing "CONTEXT%: UNKNOWN -- no tool in this
environment exposes the real per-turn token-usage figure" line.

Own tool, own clone. Built H1 b66, per direct instruction: NOT shared with
H2 -- H2 builds its own independent version later, not a copy of this one,
the same "independent, not copied" standard this role already holds
everyone else's second-opinion tooling to (see SKILL.md, Spec 3).

WHAT IS ACTUALLY MEASURED, NAMED PRECISELY RATHER THAN IMPLIED. Each
written assistant-turn entry in a session's own .jsonl transcript carries
a real `message.usage` object from the API response: `input_tokens` (new,
uncached tokens sent this turn) and `cache_read_input_tokens` (tokens
served from prompt cache -- still real context occupying the window, just
billed differently). Their SUM is the real total context size the model
was holding for that turn -- not an estimate, the API's own reported
figure, read back from disk rather than guessed. This is the exact fix
the b66 dispatch asked for: "report that real figure in your digest's
CONTEXT line going forward instead of self-estimate/UNKNOWN."

WHY THE *LAST* ASSISTANT TURN, AND THE HONEST STALENESS THIS IMPLIES. The
transcript is written turn-by-turn as the session progresses; the entry
for the turn CURRENTLY in progress does not exist yet (it is written only
once that turn completes). So the figure this tool reports is always the
real, measured context as of the last FULLY WRITTEN turn -- not a live,
real-time reading of the turn calling this tool. Said plainly in the
output, not left to be assumed: this is the measured figure as of the
last completed turn, not necessarily this exact instant.

SESSION FILE SELECTION, FAIL-CLOSED. This role's own session transcripts
live as top-level *.jsonl files directly in this tool's own project
directory (the parent of hover-audit-log/, i.e.
~/.claude/projects/<this-project-hash>/) -- never inside a subagent's own
nested subdirectory, which is a structurally different, separate
transcript this tool is not measuring. `--session <uuid>` names one
explicitly; with no flag, the tool auto-picks the most-recently-MODIFIED
top-level *.jsonl in that directory, which is correct for "the session
calling this tool right now" because every turn appends to its own file
immediately -- the current session's file is the one that was just
written to. Disclosed, not hidden: this is a heuristic (mtime-based), not
a guarantee, and the tool prints which file and which session id it
actually used so a caller can verify it picked the right one. Zero
top-level *.jsonl files, an unreadable/unparseable file, or zero assistant
turns carrying a `usage` object are all COULD_NOT_RUN (exit 2), never a
silent 0 or a guessed figure (PR SS1.11).

SIDECHAIN EXCLUSION. A transcript line can carry `isSidechain: true` for
a branched/background exchange that is not the main turn sequence; those
are excluded from "last assistant turn" so a sidechain's own usage figure
is never mistaken for the main conversation's real context size.

Run:
  python hover_context_measure.py                  # auto-pick this session
  python hover_context_measure.py --session <uuid>  # a specific session
  python hover_context_measure.py --selftest        # fixtures, no real read
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(HERE)

EXIT_OK = 0
EXIT_RED_FLAG = 1
EXIT_COULD_NOT_RUN = 2

# ── THE RED-FLAG CONTEXT THRESHOLD: 70% -> 80%, AND MADE MECHANICAL ───────
# MOVED ON DIRECT INSTRUCTION, H1 b68. The honest before-state, stated
# first: this threshold was PROSE ONLY. The rule ">70%, stop starting items"
# existed as a sentence in a dispatch and in this role's own b24 handoff
# ("the '>70%, stop starting items' condition had nothing left to gate") and
# appeared in NO tool anywhere -- grepped for before changing anything:
# zero hits for a 70 threshold constant across all 60 of this role's tools.
# So "moving it to 80%" could not be a one-character edit; there was no
# mechanism to edit. It is BOTH moved to 80% and given a real trigger here
# for the first time, which is the same lesson this role's own SKILL.md
# already records against itself: a sentence an LLM is supposed to remember
# is not a mechanical trigger, and prose is exactly what that section says
# is not enough.
#
# WHY A HIGHER NUMBER IS THE SAFER ONE HERE, rather than a looser one: the
# rule gates STARTING new work, and firing it too early strands dispatched
# items unfinished for no reason. b66/b67 both ran to completion past 50%
# of a 1M window with no degradation, so 70% was costing real work. 80%
# still leaves ~200k tokens on a 1M window -- more than a whole b67's worth
# of measured usage -- to finish and hand off cleanly.
# ── b74: 80% -> 85%, TO MATCH THE WRAP-UP WATCHER, AND LOCKED TO IT ────────
# Michael's b74 standing rule: 85% REAL context is an automatic hard wrap-up,
# and this role's own red-flag threshold must match it. The honest
# before-state: hover_context_watch.py moved to 85 in b72 (WRAP_PCT) and this
# file stayed at 80, so the two instruments this role runs disagreed for a
# whole batch about the same question -- one said STOP at 80, the other said
# wrap at 85 -- and nothing noticed, because each was internally consistent.
# Fixed by moving the number AND by a fixture (T14) that reads WRAP_PCT from
# the watcher and fails if the two ever differ again: a threshold that has to
# be remembered in two files will be remembered in one.
RED_FLAG_PCT = 85.0

# The same window table and the same inference convention the platform's own
# tools/context_verify.py uses -- deliberately the SAME numbers rather than
# a second, competing answer. That tool is scoped to the four build clones
# and says so ("the hover clones are not reachable from here"), so this is
# the hover-side implementation of one shared convention, not a rival one.
WINDOWS = {
    'claude-opus-5': (200000, 1000000),
    'claude-opus-4': (200000, 1000000),
    'claude-sonnet-5': (200000, 1000000),
    'claude-haiku-4-5': (200000,),
}
DEFAULT_WINDOWS = (200000, 1000000)

# Declared per-session window marker, read if present. Same filename and
# same reasoning as the platform convention: untracked, so it cannot travel
# in a commit; keyed by session, because an observed prompt can witness a
# declaration that is too SMALL and can never witness one that is too LARGE.
WINDOW_MARKER = 'sairn-context-window'


def last_assistant_usage(lines):
    """(usage_dict, turn_index, reason) over an iterable of raw jsonl text
    lines -- turn_index is the 1-based ordinal among assistant turns
    counted (not the raw line number), so a caller can say "turn 47 of
    this session" without exposing the file's internal line numbering.
    reason is None on success. Pure function, directly fixture-tested."""
    last_usage = None
    count = 0
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except ValueError:
            continue  # a single malformed line does not abort the whole read
        if obj.get('type') != 'assistant':
            continue
        if obj.get('isSidechain'):
            continue
        msg = obj.get('message')
        if not isinstance(msg, dict):
            continue
        usage = msg.get('usage')
        if not isinstance(usage, dict):
            continue
        count += 1
        last_usage = usage
    if last_usage is None:
        return None, 0, 'no assistant turn in this transcript carries a usage object'
    return last_usage, count, None


def model_of(lines):
    """The model string the session's own assistant turns record, or None.
    Read from the transcript rather than assumed -- and note it does NOT
    settle the window: a 1M-variant session records the same model string a
    200k one does, which is why the inference below needs the observed
    maximum prompt as well."""
    model = None
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except ValueError:
            continue
        if obj.get('type') != 'assistant' or obj.get('isSidechain'):
            continue
        msg = obj.get('message')
        if isinstance(msg, dict) and msg.get('model'):
            model = str(msg['model'])
    return model


def model_family(model):
    """Strip a variant suffix like '[1m]' so 'claude-opus-5[1m]' and
    'claude-opus-5' land on the same window table row."""
    if not model:
        return ''
    return model.split('[')[0].strip()


def observed_max_prompt(lines):
    """The largest real prompt seen across the session's own assistant
    turns. This is the only evidence in the transcript that distinguishes a
    1M session from a 200k one, so the window inference needs it -- the
    last turn alone is not enough (a fresh window's first turn is small on
    either)."""
    best = 0
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except ValueError:
            continue
        if obj.get('type') != 'assistant' or obj.get('isSidechain'):
            continue
        msg = obj.get('message')
        if not isinstance(msg, dict):
            continue
        usage = msg.get('usage')
        if isinstance(usage, dict):
            best = max(best, context_figure(usage))
    return best


def declared_window(session_id, project_dir=PROJECT_DIR):
    """(tokens_or_None, why). Reads the untracked per-session marker if one
    exists. The marker lives in THIS clone's .git directory, keyed by
    session id -- same convention as the platform tool."""
    repo = os.path.join(os.path.expanduser('~'), 'Documents', 'SAIRN-hover')
    path = os.path.join(repo, '.git', WINDOW_MARKER)
    if not os.path.isfile(path):
        return None, 'no declared window marker at %s' % path
    try:
        with open(path, encoding='utf-8') as f:
            raw = f.read()
    except OSError as e:
        return None, 'declared-window marker unreadable: %s' % e
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] == session_id:
            try:
                return int(parts[1]), ''
            except ValueError:
                return None, 'marker line for this session is not an integer: %r' % line
        if len(parts) == 1 and session_id is None:
            try:
                return int(parts[0]), ''
            except ValueError:
                pass
    return None, 'marker exists but names no window for session %s' % session_id


def window_for(model, observed_max, declared=None):
    """(window_or_None, why). DECLARED if there is one, else the SMALLEST
    tabled window the observed prompt actually fits in.

    THAT INFERENCE IS A FLOOR ON THE WINDOW, THEREFORE A CEILING ON THE
    PERCENTAGE, and this matters in exactly one direction: early in a 1M
    session a 141k prompt fits 200k, so the inference reports ~71% when the
    truth is ~14%. Over-reporting is the safe direction for a threshold
    whose job is to say "stop starting things" -- but it is still wrong, so
    it is labelled an inference every time and a declared marker always
    wins. A declaration SMALLER than a prompt actually observed is refused,
    because then the declaration is the thing that is wrong."""
    fam = model_family(model)
    sizes = WINDOWS.get(fam, DEFAULT_WINDOWS)
    if declared:
        if observed_max > declared:
            return None, ('a window of %s is declared for this session but a '
                          'prompt of %s was actually observed -- the '
                          'DECLARATION is wrong, so no percentage is reported '
                          'off a denominator already contradicted'
                          % ('{:,}'.format(declared), '{:,}'.format(observed_max)))
        return declared, 'declared'
    for size in sizes:
        if observed_max <= size:
            return size, ('inferred as the smallest tabled window for %r that '
                          'the observed maximum prompt (%s) fits -- a FLOOR on '
                          'the window and so a CEILING on the percentage'
                          % (fam or 'unknown model', '{:,}'.format(observed_max)))
    return None, ('an observed prompt of %s fits no published window for %r '
                  '(largest tabled %s) -- no percentage rather than one over '
                  '100 off a denominator known to be wrong'
                  % ('{:,}'.format(observed_max), fam or 'unknown model',
                     '{:,}'.format(sizes[-1])))


def context_figure(usage):
    """The real total: new tokens this turn + tokens served from cache.
    Both are real context the model held; splitting them is a billing
    distinction, not a context-size one."""
    return int(usage.get('input_tokens') or 0) + int(usage.get('cache_read_input_tokens') or 0)


def pick_session_file(project_dir, session_id=None):
    """(path, reason) -- reason is None on success. Only top-level
    *.jsonl, never a subagent's nested transcript (those live under
    <uuid>/subagents/, a different directory shape entirely)."""
    candidates = [p for p in glob.glob(os.path.join(project_dir, '*.jsonl'))
                  if os.path.isfile(p)]
    if not candidates:
        return None, 'no top-level *.jsonl transcripts found in %s' % project_dir
    if session_id:
        matches = [p for p in candidates
                   if os.path.splitext(os.path.basename(p))[0] == session_id]
        if not matches:
            return None, 'no transcript named %s.jsonl in %s' % (session_id, project_dir)
        return matches[0], None
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0], None


def cmd_measure(argv):
    session_id = None
    if '--session' in argv:
        i = argv.index('--session')
        if i + 1 >= len(argv):
            print('--session requires a value')
            return EXIT_COULD_NOT_RUN
        session_id = argv[i + 1]

    path, reason = pick_session_file(PROJECT_DIR, session_id)
    if path is None:
        print('COULD NOT RUN: %s' % reason)
        return EXIT_COULD_NOT_RUN

    try:
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
    except OSError as e:
        print('COULD NOT RUN: could not read %s: %s' % (path, e))
        return EXIT_COULD_NOT_RUN

    usage, turn_count, err = last_assistant_usage(lines)
    if err:
        print('COULD NOT RUN: %s (%s)' % (err, path))
        return EXIT_COULD_NOT_RUN

    sid = os.path.splitext(os.path.basename(path))[0]
    figure = context_figure(usage)
    print('CONTEXT: %d tokens (input_tokens=%d + cache_read_input_tokens=%d), '
          'measured from the last completed assistant turn (#%d of this '
          'transcript, not necessarily this instant) in session %s (%s)'
          % (figure, int(usage.get('input_tokens') or 0),
             int(usage.get('cache_read_input_tokens') or 0),
             turn_count, sid, path))

    # ── THE RED-FLAG GATE, mechanical since b68 (was prose at 70%) ────────
    model = model_of(lines)
    obs_max = observed_max_prompt(lines)
    decl, decl_why = declared_window(sid)
    win, win_why = window_for(model, obs_max, declared=decl)
    if win is None:
        print('CONTEXT%%: COULD NOT TELL -- %s' % win_why)
        print('  The red-flag threshold (%.0f%%) therefore did not evaluate. '
              'That is a third state, never folded into "under the '
              'threshold". Declare the real window to resolve it:'
              % RED_FLAG_PCT)
        print('  echo "%s <tokens>" >> %s' % (
            sid, os.path.join(os.path.expanduser('~'), 'Documents',
                               'SAIRN-hover', '.git', WINDOW_MARKER)))
        return EXIT_COULD_NOT_RUN

    pct = 100.0 * figure / win
    # win_why, never decl_why: when nothing is declared, decl_why is the
    # marker-ABSENCE reason ("no declared window marker at ..."), which is
    # not the reason the window is what it is. Caught by reading this tool's
    # own first real output -- it printed the marker path where the
    # inference explanation belonged.
    print('CONTEXT%%: %.1f%% of %s (model %r; window %s)'
          % (pct, '{:,}'.format(win), model or 'unknown', win_why))
    if not decl:
        print('  NOTE: the window is INFERRED, not declared -- it is a floor, '
              'so this percentage is a CEILING and may overstate usage early '
              'in a large-window session.')
    if pct >= RED_FLAG_PCT:
        print('RED FLAG: %.1f%% is at or past the %.0f%% threshold -- STOP '
              'STARTING NEW ITEMS. Finish, hand off and close out what is '
              'already open. (70%% -> 80%% at b68, which made it mechanical, '
              'then 80%% -> 85%% at b74 to match hover_context_watch.WRAP_PCT; '
              'it was prose before b68 and gated nothing.)' % (pct, RED_FLAG_PCT))
        return EXIT_RED_FLAG
    print('Under the %.0f%% red-flag threshold -- a measured all-clear, not '
          'an unrun check.' % RED_FLAG_PCT)
    return EXIT_OK


def _selftest():
    ok = 0
    total = 0

    def ck(label, cond):
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
            print('  ok   %s' % label)
        else:
            print('  FAIL %s' % label)

    good_line = json.dumps({'type': 'assistant', 'isSidechain': False,
                             'message': {'role': 'assistant',
                                         'usage': {'input_tokens': 5,
                                                   'cache_read_input_tokens': 1000}}})
    second_line = json.dumps({'type': 'assistant',
                               'message': {'role': 'assistant',
                                           'usage': {'input_tokens': 7,
                                                     'cache_read_input_tokens': 2000}}})
    side_line = json.dumps({'type': 'assistant', 'isSidechain': True,
                             'message': {'role': 'assistant',
                                         'usage': {'input_tokens': 999999,
                                                   'cache_read_input_tokens': 999999}}})
    non_assistant_line = json.dumps({'type': 'mode', 'mode': 'default'})
    malformed_line = '{not valid json'

    total += 1
    usage, count, err = last_assistant_usage([good_line, second_line])
    if err is None and context_figure(usage) == 2007 and count == 2:
        ok += 1
        print('  ok   F1 the LAST assistant turn wins, not the first '
              '(second_line: 7+2000=2007, not first_line\'s 5+1000=1005); '
              'count reflects both turns seen')
    else:
        print('  FAIL F1 wrong usage/figure/count selected: %r %r %r' % (usage, count, err))

    ck('F2 sidechain turns are excluded -- a sidechain figure never wins',
       context_figure(last_assistant_usage([good_line, side_line])[0]) == 1005)

    ck('F3 a malformed line does not abort the whole read -- the real '
       'entries around it still parse',
       last_assistant_usage([malformed_line, good_line])[0] is not None)

    ck('F4 a non-assistant line (mode/permission-mode/etc) is ignored, '
       'not mistaken for a turn',
       last_assistant_usage([non_assistant_line, good_line])[2] is None)

    ck('C1 KNOWN-BAD CONTROL: zero assistant-with-usage lines at all is '
       'COULD_NOT_RUN, never a silent 0',
       last_assistant_usage([non_assistant_line, malformed_line])[0] is None)

    ck('C2 context_figure sums BOTH fields, not just one',
       context_figure({'input_tokens': 3, 'cache_read_input_tokens': 4}) == 7)

    ck('C3 missing fields default to 0 rather than raising',
       context_figure({}) == 0)

    import tempfile
    tmp = tempfile.mkdtemp(prefix='hover_context_measure_fx_')
    try:
        empty_dir_path, empty_reason = pick_session_file(tmp)
        ck('C4 FAIL-CLOSED: an empty project dir (no *.jsonl at all) '
           'refuses rather than guessing', empty_dir_path is None and empty_reason)

        p1 = os.path.join(tmp, 'aaaa.jsonl')
        p2 = os.path.join(tmp, 'bbbb.jsonl')
        open(p1, 'w', encoding='utf-8').write(good_line + '\n')
        import time
        time.sleep(0.01)
        open(p2, 'w', encoding='utf-8').write(good_line + '\n')
        os.utime(p2, None)
        picked, _ = pick_session_file(tmp)
        ck('F5 auto-pick chooses the most-recently-MODIFIED file, not '
           'alphabetical/first-found', os.path.basename(picked) == 'bbbb.jsonl')

        named, named_reason = pick_session_file(tmp, session_id='aaaa')
        ck('F6 an explicit --session overrides mtime auto-pick',
           named is not None and os.path.basename(named) == 'aaaa.jsonl')

        missing, missing_reason = pick_session_file(tmp, session_id='nope')
        ck('C5 FAIL-CLOSED: a --session naming a transcript that does not '
           'exist refuses, never silently falls back to auto-pick',
           missing is None and missing_reason)

        # ── THE RED-FLAG THRESHOLD, b68. Locked in BOTH directions, and
        # the number itself asserted so a silent edit back to 70 fails here.
        ck('T0 the threshold constant is 85% (b74), not the 80% of b68 or the '
           'old prose 70%',
           RED_FLAG_PCT == 85.0)

        big = json.dumps({'type': 'assistant',
                           'message': {'role': 'assistant',
                                       'model': 'claude-opus-5',
                                       'usage': {'input_tokens': 2,
                                                 'cache_read_input_tokens': 850000}}})
        small = json.dumps({'type': 'assistant',
                             'message': {'role': 'assistant',
                                         'model': 'claude-opus-5',
                                         'usage': {'input_tokens': 2,
                                                   'cache_read_input_tokens': 100000}}})
        ck('T1 model_of reads the real model string off an assistant turn',
           model_of([big]) == 'claude-opus-5')
        ck('T2 model_family strips a [1m] variant suffix so both variants '
           'hit one window row',
           model_family('claude-opus-5[1m]') == 'claude-opus-5')
        ck('T3 observed_max_prompt takes the LARGEST prompt, not the last',
           observed_max_prompt([big, small]) == 850002)

        w1, why1 = window_for('claude-opus-5', 850002)
        ck('T4 an 850k observed prompt infers the 1M window (200k cannot '
           'hold it)', w1 == 1000000)
        w2, why2 = window_for('claude-opus-5', 100002)
        ck('T5 FLOOR BEHAVIOUR, disclosed not hidden: a 100k prompt infers '
           '200k -- the smallest window it fits -- and the reason text says '
           'it is a floor/ceiling', w2 == 200000 and 'FLOOR' in why2)
        w3, why3 = window_for('claude-opus-5', 850002, declared=1000000)
        ck('T6 a DECLARED window wins over the inference', w3 == 1000000)
        w4, why4 = window_for('claude-opus-5', 850002, declared=200000)
        ck('T7 KNOWN-BAD CONTROL: a declaration SMALLER than an observed '
           'prompt is refused (window None), never used to report a >100% '
           'figure', w4 is None and 'DECLARATION is wrong' in why4)
        w5, why5 = window_for('claude-haiku-4-5', 500000)
        ck('T8 FAIL-CLOSED: a prompt fitting no tabled window returns None '
           'with a named reason, not a percentage over 100',
           w5 is None and 'no published window' in why5)

        # The threshold arithmetic itself, both sides of the line.
        ck('T9 850002 of 1,000,000 is 85.0% -- at/over 85%, a RED FLAG',
           (100.0 * 850002 / 1000000) >= RED_FLAG_PCT)
        ck('T10 KNOWN-BAD CONTROL: 700,000 of 1,000,000 is 70.0% -- this is '
           'exactly the figure the OLD 70% rule would have red-flagged and '
           'the current 85% rule must NOT, which is the whole point of the move',
           (100.0 * 700000 / 1000000) < RED_FLAG_PCT)
        ck('T11 the 85% boundary is inclusive (>=), so exactly 850,000 of '
           '1,000,000 still red-flags',
           (100.0 * 850000 / 1000000) >= RED_FLAG_PCT)
        ck('T13 KNOWN-BAD CONTROL for the b74 move: 800,000 of 1,000,000 is '
           '80.0% -- the figure that red-flagged under b68 and must NOT now',
           (100.0 * 800000 / 1000000) < RED_FLAG_PCT)
        # T14 reads the WATCHER'S number. Import failure is a FAILURE of this
        # arm, not a skip: an unverifiable match is not a match.
        watch_wrap = None
        for d in (HERE, os.path.join(os.path.expanduser('~'), 'Documents',
                                      'SAIRN-hover', '.claude', 'skills',
                                      'sairn-hover-auditor', 'tools')):
            try:
                sys.path.insert(0, d)
                import hover_context_watch as _w
                watch_wrap = _w.WRAP_PCT
                break
            except Exception:
                continue
        ck('T14 this red-flag threshold EQUALS hover_context_watch.WRAP_PCT '
           '(%r vs %r) -- the two instruments can no longer disagree about '
           'when to stop' % (RED_FLAG_PCT, watch_wrap),
           watch_wrap is not None and RED_FLAG_PCT == watch_wrap)

        declared_missing, dwhy = declared_window('no-such-session-id')
        ck('T12 a session with no declared-window marker line returns None '
           'with a reason, so the caller falls back to the inference rather '
           'than to a guess', declared_missing is None and dwhy)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print('%d/%d fixture checks correct' % (ok, total))
    return ok == total


def main(argv):
    if '--selftest' in argv:
        return EXIT_OK if _selftest() else 1
    return cmd_measure(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
