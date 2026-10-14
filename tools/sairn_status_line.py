#!/usr/bin/env python
# OWNER: cc
# written 2026-10-14, batch b8, queue item 3
"""The status line: which agent, which model, and HOW MUCH CONTEXT IS GONE.

    python tools/sairn_status_line.py --fixtures     # the criteria lock
    echo '<status json>' | python tools/sairn_status_line.py

Wired in `~/.claude/settings.json` as `statusLine`, which is USER-LEVEL and
therefore applies in ALL SIX agent folders from one entry. **NOT A HOOK.** A
status line is a display command: it cannot block a tool call, cannot edit a
file and cannot refuse anything. The 23 hooks Michael cleared on 2026-10-11
stay cleared and nothing here re-adds one.

── WHY A CONTEXT PERCENTAGE AND NOT A TOKEN COUNT ──────────────────────────
Every long batch on this platform has ended the same way: a session that did
not know how close it was, then a compaction mid-edit. The number that matters
is the FRACTION of the window that is gone, because the ceiling differs by
model -- this session is Opus 5 with a 1M window and the ordinary one is 200K,
and `840,000 tokens` reads as a catastrophe in one and as 84% in the other.

Red at 70%, on Michael's instruction. One threshold, not a gradient: a status
line with four colours is a thing you stop reading.

── THE NUMBER IS MEASURED, AND WHEN IT CANNOT BE IT SAYS SO ────────────────
There is no "context used" field in the status-line payload. What exists is
`transcript_path`, so the figure is read from the LAST `message.usage` in the
transcript -- `input_tokens + cache_read_input_tokens +
cache_creation_input_tokens`, which is what the model was actually handed on
that turn. Output tokens are NOT added: they are already inside the next turn's
input, and adding both double-counts.

**A `0%` THAT MEANS "I COULD NOT TELL" WOULD BE THE WORST POSSIBLE OUTPUT** --
it is the one value that reads as reassuring. So every failure prints
`ctx ??%` with a short reason instead of a number (PR 1.11 in the one place a
reader glances at rather than reads). The failures are real: a fresh session
has no usage line yet, a transcript can be absent, and a line can be truncated
mid-write while the file is being appended to.

── IT ALWAYS EXITS 0 ───────────────────────────────────────────────────────
Same decision `compaction_brief.py` made for its own hook mode, for a weaker
reason: a status line that exits non-zero prints a harness error over the
place the number should be, which costs the figure it exists to show. Nothing
here can fail closed, so nothing here is allowed to gate anything either --
said out loud, because an always-exit-0 program must never be cited as a check.
"""
import io
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

CRITERIA_VERSION = '2026-10-14.1'

RED_AT = 70                 # Michael's threshold, batch b8
BIG_WINDOW = 1000000        # the [1m] models
SMALL_WINDOW = 200000       # everything else
TAIL_BYTES = 262144         # first look: the last 256KB of the transcript
TAIL_BYTES_WIDE = 4194304   # second look, once: 4MB

RESET = '\033[0m'
RED = '\033[1;31m'
DIM = '\033[2m'


def agent_name(start):
    """This clone's session name from its PER-CLONE MARKER, or ''.

    Never the folder name. A clone renamed SAIRN-cody would otherwise label
    itself cody in six folders at once -- hover finding #258 is that exact
    defect, and `sairn_session_identity` is the one implementation of the
    answer rather than a copy of it.
    """
    try:
        import sairn_session_identity as sid
        return sid.session_name(start or None)
    except Exception:                                            # noqa: BLE001
        return ''


def window_for(payload):
    """-> (tokens, why). The context ceiling for the model in play."""
    model = payload.get('model') or {}
    ident = '%s %s' % (model.get('id') or '', model.get('display_name') or '')
    if '1m' in ident.lower():
        return BIG_WINDOW, '1m in the model id'
    if payload.get('exceeds_200k_tokens'):
        # A session that has already passed 200K cannot be a 200K session, so
        # this is a measurement and not an assumption.
        return BIG_WINDOW, 'exceeds_200k_tokens is true'
    return SMALL_WINDOW, 'default'


def _tail_lines(path, nbytes):
    with io.open(path, 'rb') as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        start = max(0, size - nbytes)
        fh.seek(start)
        data = fh.read()
    if start:
        data = data.split(b'\n', 1)[-1]      # drop the partial first line
    return data.split(b'\n')


def used_tokens(path):
    """-> (tokens, '') or (None, why). The LAST usage in the transcript.

    SCANNED FROM THE END, in a bounded window, because a transcript is append-
    only and megabytes long -- reading it whole to find its last line is how a
    status line becomes the slowest thing in the session.
    """
    if not path:
        return None, 'no transcript_path'
    if not os.path.isfile(path):
        return None, 'no transcript yet'
    for nbytes in (TAIL_BYTES, TAIL_BYTES_WIDE):
        try:
            lines = _tail_lines(path, nbytes)
        except OSError as exc:
            return None, 'transcript unreadable (%s)' % exc.__class__.__name__
        for raw in reversed(lines):
            raw = raw.strip()
            if not raw or b'usage' not in raw:
                continue
            try:
                rec = json.loads(raw.decode('utf-8', 'replace'))
            except ValueError:
                # A line being appended right now is truncated. Not an error,
                # and NOT a reason to report a smaller number: skip it.
                continue
            usage = ((rec.get('message') or {}).get('usage')
                     if isinstance(rec.get('message'), dict) else None)
            if not isinstance(usage, dict):
                usage = rec.get('usage') if isinstance(rec.get('usage'),
                                                       dict) else None
            if not isinstance(usage, dict):
                continue
            total = 0
            for key in ('input_tokens', 'cache_read_input_tokens',
                        'cache_creation_input_tokens'):
                val = usage.get(key)
                if isinstance(val, (int, float)):
                    total += int(val)
            if total > 0:
                return total, ''
    return None, 'no usage line yet'


def render(payload, colour=True):
    """-> the one status line. Never raises; never fabricates a percentage."""
    bits = []
    agent = agent_name((payload.get('workspace') or {}).get('current_dir')
                       or payload.get('cwd') or '')
    if agent:
        bits.append(agent)
    model = (payload.get('model') or {}).get('display_name') or ''
    if model:
        bits.append(model)

    window, _why = window_for(payload)
    used, why = used_tokens(payload.get('transcript_path'))
    if used is None:
        bits.append('ctx ??%% (%s)' % why)
    else:
        pct = int(round(100.0 * used / window))
        txt = 'ctx %d%% of %dk' % (pct, window // 1000)
        if colour and pct >= RED_AT:
            txt = '%s%s%s' % (RED, txt, RESET)
        bits.append(txt)
    out = ' | '.join(bits)
    return '%s%s%s' % (DIM, out, RESET) if colour and used is None else out


# ── THE CRITERIA LOCK ───────────────────────────────────────────────────────
def run_fixtures():
    import shutil
    import tempfile
    print('SAIRN STATUS LINE -- criteria lock %s' % CRITERIA_VERSION)
    bad = total = 0

    def check(label, got, want):
        nonlocal bad, total
        total += 1
        if got != want:
            bad += 1
            print('  LOCK FAILED  %s' % label)
            print('               wanted %r' % (want,))
            print('               got    %r' % (got,))

    tmp = tempfile.mkdtemp(prefix='statusline-fix-')
    try:
        def transcript(name, lines):
            p = os.path.join(tmp, name)
            with io.open(p, 'w', encoding='utf-8', newline='\n') as fh:
                for obj in lines:
                    fh.write(obj if isinstance(obj, str)
                             else json.dumps(obj))
                    fh.write('\n')
            return p

        def usage(n):
            return {'type': 'assistant',
                    'message': {'usage': {'input_tokens': n,
                                          'cache_read_input_tokens': 0,
                                          'cache_creation_input_tokens': 0}}}

        def pay(path, model='claude-opus-5', **kw):
            d = {'transcript_path': path, 'model': {'id': model,
                                                    'display_name': model},
                 'workspace': {'current_dir': tmp}, 'cwd': tmp}
            d.update(kw)
            return d

        # THE SUM IS THE THREE INPUT FIELDS, NOT output_tokens.
        p = transcript('t1.jsonl', [
            {'type': 'assistant', 'message': {'usage': {
                'input_tokens': 10000, 'cache_read_input_tokens': 30000,
                'cache_creation_input_tokens': 10000,
                'output_tokens': 900000}}}])
        check('the three input fields are summed and output_tokens is NOT',
              used_tokens(p)[0], 50000)

        # THE LAST usage WINS, and a trailing line without one does not hide it.
        p = transcript('t2.jsonl', [usage(10000), usage(140000),
                                    {'type': 'user', 'message':
                                     {'content': 'no usage here'}}])
        check('the LAST usage line is the one reported, past a trailing '
              'user turn', used_tokens(p)[0], 140000)

        # A TRUNCATED LINE IS SKIPPED, NOT COUNTED AS SMALLER.
        p = transcript('t3.jsonl', [usage(140000),
                                    '{"message": {"usage": {"input_to'])
        check('a half-written final line is skipped rather than lowering the '
              'number', used_tokens(p)[0], 140000)

        # EVERY COULD-NOT-TELL IS A REASON, NEVER A ZERO.
        check('an absent transcript is a reason, not 0',
              used_tokens(os.path.join(tmp, 'nope.jsonl')),
              (None, 'no transcript yet'))
        check('an empty transcript_path is a reason, not 0',
              used_tokens('')[0], None)
        p = transcript('t4.jsonl', [{'type': 'user', 'message': {'content': 'x'}}])
        check('a fresh transcript with no usage line is a reason, not 0',
              used_tokens(p), (None, 'no usage line yet'))
        p = transcript('t5.jsonl', [{'type': 'assistant', 'message': {'usage': {
            'input_tokens': 0, 'cache_read_input_tokens': 0,
            'cache_creation_input_tokens': 0}}}])
        check('a usage line of all zeros is NOT a 0% answer', used_tokens(p)[0],
              None)

        # THE WINDOW.
        check('[1m] in the model id means a 1M window',
              window_for({'model': {'id': 'claude-opus-5[1m]'}})[0], BIG_WINDOW)
        check('a plain id means 200K',
              window_for({'model': {'id': 'claude-opus-5'}})[0], SMALL_WINDOW)
        check('exceeds_200k_tokens alone is enough -- a session past 200K '
              'cannot be a 200K session',
              window_for({'model': {'id': 'claude-sonnet-5'},
                          'exceeds_200k_tokens': True})[0], BIG_WINDOW)
        check('no model block at all does not raise',
              window_for({})[0], SMALL_WINDOW)

        # THE THRESHOLD, IN BOTH DIRECTIONS, ON THE RENDERED STRING.
        p = transcript('t6.jsonl', [usage(138000)])         # 69.0% of 200K
        line = render(pay(p))
        check('69% carries no red', RED in line, False)
        check('...and still shows the exact percentage',
              'ctx 69% of 200k' in line, True)
        p = transcript('t7.jsonl', [usage(140000)])         # exactly 70%
        check('EXACTLY 70%% is red -- the boundary is >=, not >',
              RED in render(pay(p)), True)
        # THE DISPLAYED NUMBER AND THE COLOUR AGREE, which a floor-vs-round
        # mismatch would break: 139,000 is 69.5%, prints as 70%, and must
        # therefore be red. A line reading `70%` in plain text would be worse
        # than either answer alone.
        p = transcript('t7b.jsonl', [usage(139000)])
        line = render(pay(p))
        check('69.5% prints as 70% AND is red -- display and threshold cannot '
              'disagree', ('ctx 70%' in line, RED in line), (True, True))
        p = transcript('t8.jsonl', [usage(190000)])
        check('95% is red', RED in render(pay(p)), True)
        check('...and colour can be turned off for a non-tty reader',
              RED in render(pay(p), colour=False), False)

        # THE SAME TOKEN COUNT IS A DIFFERENT ANSWER PER WINDOW, which is the
        # whole reason this prints a percentage.
        p = transcript('t9.jsonl', [usage(700000)])
        check('700K of a 1M window is 70% and red',
              'ctx 70% of 1000k' in render(pay(p, model='claude-opus-5[1m]')),
              True)
        check('...and the same count in a 200K session is not reported as 70%',
              'ctx 70% of 200k' in render(pay(p)), False)

        # THE COULD-NOT-TELL PATH RENDERS A LINE RATHER THAN NOTHING.
        line = render(pay(os.path.join(tmp, 'gone.jsonl')), colour=False)
        check('a missing transcript still renders a line, and it says ??',
              'ctx ??%' in line, True)
        check('...and that line carries NO digit percentage anywhere',
              '%' in line.replace('??%', ''), False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('  %d/%d fixtures classify correctly' % (total - bad, total))
    if bad:
        print('  THE CRITERIA ARE BROKEN. The percentage this prints is not '
              'trustworthy until these pass.')
        return 1
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv:
        return run_fixtures()
    try:
        raw = sys.stdin.read()
    except Exception:                                            # noqa: BLE001
        raw = ''
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        payload = {}
    try:
        print(render(payload))
    except Exception as exc:                                     # noqa: BLE001
        # A status line must not print a traceback over the figure, and must
        # not print a number it did not compute either.
        print('ctx ??%% (status line failed: %s)' % exc.__class__.__name__)
    return 0


if __name__ == '__main__':
    sys.exit(main())
