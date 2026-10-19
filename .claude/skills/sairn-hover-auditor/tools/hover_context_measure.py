#!/usr/bin/env python
"""hover_context_measure.py -- the real, measured context-window figure for
THIS role's own session, read from this session's own transcript jsonl,
replacing the digest's long-standing "CONTEXT%: UNKNOWN -- no tool in this
environment exposes the real per-turn token-usage figure" line.

Own tool, own clone. Built H1 b66, per direct instruction: NOT shared with
H2 -- H2 builds its own independent version later, not a copy of this one,
the same "independent, not copied" standard this role already holds
everyone else's second-opinion tooling to (see SKILL.md, Spec 3).

ARCHIVAL COPY, same disclosure as every other tool in this directory: the
OPERATIONAL copy lives per-clone in hover-audit-log/, where PROJECT_DIR
below actually resolves to the real project directory full of session
*.jsonl transcripts. Run from HERE, PROJECT_DIR resolves to this skill's
own directory instead, which has no top-level *.jsonl transcripts --
that is fine, not a bug: --selftest still passes (it never touches real
transcripts), and the real-data path fails CLOSED with a named reason
rather than silently measuring the wrong thing.

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
EXIT_COULD_NOT_RUN = 2


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
