#!/usr/bin/env python
# OWNER: cc
# written 2026-10-19, batch b20 items 1-4
"""REAL context% per build agent, read from its own transcript -- independent
of anything any agent says about itself.

    python tools/context_verify.py                 # all four build agents
    python tools/context_verify.py --agent hank
    python tools/context_verify.py --json
    python tools/context_verify.py --fixtures      # the criteria lock

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── WHAT IT MEASURES ────────────────────────────────────────────────────────
The LAST ASSISTANT TURN's whole prompt, over the smallest published window for
that turn's own model that the measured prompt actually fits in.

    prompt = input_tokens + cache_read_input_tokens + cache_creation_input_tokens

ALL THREE, and this is measured rather than argued. On 2026-10-19T14:29Z the
four build agents' last turns carried:

    hank    input_tokens 2   cache_creation 112    cache_read 670,816
    cc      input_tokens 2   cache_creation 1,501  cache_read 654,276
    cody    input_tokens 2   cache_creation 596    cache_read 616,217
    fourth  input_tokens 2   cache_creation 523    cache_read 584,884

`input_tokens` ALONE IS TWO. A figure built on it reports every agent at 0.0%
while each carries over half a million tokens of prompt.

── THE WINDOW IS NOT IN THE TRANSCRIPT, AND THAT IS MEASURED ───────────────
cc's own 4.7MB transcript was searched for `context_window`, `1m`, `200000`
and `1000000`: every hit is prose or an echoed command. There is NO structured
window field. And the model string does not settle it either -- all four agents
record `claude-opus-5` while this session's own model id is
`claude-opus-5[1m]`, so the 1M variant records what a 200k session records.

SO THE WINDOW IS THE SMALLEST TABLED WINDOW FOR THAT MODEL THAT THE MEASURED
MAXIMUM PROMPT FITS IN. That is evidence, not an assumption: a session
observed at 657,248 tokens is demonstrably not on a 200k window. A prompt that
fits NO tabled window is COULD NOT TELL -- never a percentage over 100 with a
denominator already known to be wrong.

── SCOPE: THE FOUR BUILD AGENTS ONLY ───────────────────────────────────────
`hover` and `hover2` are EXCLUDED BY THE SEPARATION BOUNDARY, not by
oversight. Their project folders exist on this machine; reading an auditor's
own transcript from a build clone is the same boundary violation as writing
into its clone, running the other way. They are not listed and they are not
read.

── IT NEVER READS A SELF-REPORT ────────────────────────────────────────────
Not the status registry, not a digest. Transcripts only. The board publishes
both figures side by side so a disagreement is visible rather than averaged --
and the two measure slightly different moments, so the AGE of each is printed
rather than inviting a reader to treat every gap as a lie.
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

CRITERIA_VERSION = '2026-10-19.1'

# THE FOUR BUILD AGENTS. See the module docstring for why hover/hover2 are not
# here -- it is a boundary, and a later reader must not "fix" the omission.
BUILD_AGENTS = ('hank', 'cc', 'cody', 'fourth')
PROJECT_FMT = 'C--Users-marsh-Documents-SAIRN-%s'

# Published windows, smallest first. The tool picks the smallest one the
# measured prompt fits in, so an entry being present is not a claim that any
# session uses it.
WINDOWS = {
    'claude-opus-5': (200000, 1000000),
    'claude-opus-4': (200000, 1000000),
    'claude-sonnet-5': (200000, 1000000),
    'claude-haiku-4-5': (200000,),
}
DEFAULT_WINDOWS = (200000, 1000000)

PROMPT_KEYS = ('input_tokens', 'cache_read_input_tokens',
               'cache_creation_input_tokens')


def projects_dir():
    return os.path.join(os.path.expanduser('~'), '.claude', 'projects')


def model_family(model):
    """'claude-opus-5[1m]' or 'claude-opus-5-20260101' -> a WINDOWS key."""
    m = (model or '').strip()
    m = re.sub(r'\[[^\]]*\]$', '', m)             # the [1m] variant marker
    m = re.sub(r'-\d{8}$', '', m)                 # a dated build
    return m


def window_for(model, observed_max):
    """-> (window, why_or_''). The SMALLEST tabled window the prompt fits.

    Pure. `observed_max` is the largest prompt actually seen in the session,
    which is the only evidence available that distinguishes two variants of
    one model string.
    """
    fam = model_family(model)
    sizes = WINDOWS.get(fam, DEFAULT_WINDOWS)
    for size in sizes:
        if observed_max <= size:
            return size, ''
    return None, ('a prompt of %s token(s) fits no published window for %r '
                  '(largest tabled: %s), so no percentage is reported rather '
                  'than one over 100 with a denominator known to be wrong'
                  % ('{:,}'.format(observed_max), fam,
                     '{:,}'.format(sizes[-1])))


def prompt_of(usage):
    """The whole prompt from a usage dict. Missing keys count as zero, and
    a usage with NO prompt key at all returns None -- which is a could-not-
    tell about that record rather than a prompt of zero."""
    if not isinstance(usage, dict):
        return None
    if not any(k in usage for k in PROMPT_KEYS):
        return None
    return sum(int(usage.get(k) or 0) for k in PROMPT_KEYS)


def scan_transcript(path):
    """-> dict with the last assistant turn's prompt, the model, the session's
    observed maximum and the record count. Never raises."""
    out = {'prompt': None, 'model': '', 'observed_max': 0, 'turns': 0,
            'last_ts': ''}
    try:
        fh = io.open(path, 'rb')
    except OSError as exc:
        out['why'] = 'transcript unreadable (%s)' % exc.__class__.__name__
        return out
    with fh:
        for line in fh:
            if b'"usage"' not in line:
                continue
            try:
                rec = json.loads(line.decode('utf-8', 'replace'))
            except ValueError:
                continue
            msg = rec.get('message') or {}
            # THE ASSISTANT TURN, not any turn. A tool result carrying the
            # word `usage` in its text is not a turn, and a user record never
            # carries a prompt size.
            if (rec.get('type') or msg.get('role')) not in ('assistant',):
                continue
            p = prompt_of(msg.get('usage') or rec.get('usage'))
            if p is None:
                continue
            out['turns'] += 1
            out['prompt'] = p                      # the LAST one wins
            out['observed_max'] = max(out['observed_max'], p)
            if msg.get('model'):
                out['model'] = msg['model']
            if rec.get('timestamp'):
                out['last_ts'] = rec['timestamp']
    return out


def newest_transcript(agent, base=None):
    """-> (path, n_transcripts, why_or_''). mtime is a PROXY for current and
    the caller prints the age so a reader can see what was chosen."""
    base = base or projects_dir()
    d = os.path.join(base, PROJECT_FMT % agent)
    if not os.path.isdir(d):
        return '', 0, ('no project folder at %s, so this agent\'s context '
                       'CANNOT BE VERIFIED -- not 0%%' % d)
    try:
        files = [os.path.join(d, f) for f in os.listdir(d)
                 if f.endswith('.jsonl')]
    except OSError as exc:
        return '', 0, 'project folder unreadable (%s)' % exc
    if not files:
        return '', 0, ('the project folder exists and holds no transcript, so '
                       'there is nothing to measure -- not 0%')
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0], len(files), ''


def verify(agent, base=None, now=None):
    """-> one row dict. The whole measurement for one agent, no self-report."""
    now = float(now if now is not None else time.time())
    row = {'agent': agent, 'pct': None, 'prompt': None, 'window': None,
           'model': '', 'session': '', 'transcripts': 0, 'age_h': None,
           'why': ''}
    path, n, why = newest_transcript(agent, base)
    row['transcripts'] = n
    if not path:
        row['why'] = why
        return row
    row['session'] = os.path.basename(path)[:-6]
    try:
        row['age_h'] = round((now - os.path.getmtime(path)) / 3600.0, 2)
    except OSError:
        row['age_h'] = None
    got = scan_transcript(path)
    row['model'] = got['model']
    if got.get('why'):
        row['why'] = got['why']
        return row
    if got['prompt'] is None:
        row['why'] = ('the newest transcript carries no assistant turn with a '
                      'prompt size yet, so there is nothing to measure')
        return row
    row['prompt'] = got['prompt']
    row['turns'] = got['turns']
    row['last_ts'] = got['last_ts']
    win, w_why = window_for(got['model'], got['observed_max'])
    if win is None:
        row['why'] = w_why
        return row
    row['window'] = win
    row['pct'] = round(100.0 * got['prompt'] / float(win), 1)
    return row


# ── THE CRITERIA LOCK, IN BOTH DIRECTIONS ──────────────────────────────────
def run_fixtures():
    print('CONTEXT VERIFY -- criteria lock %s' % CRITERIA_VERSION)
    bad = total = 0

    def check(name, got, want):
        nonlocal bad, total
        total += 1
        ok = (got == want)
        if not ok:
            bad += 1
        print('  %s %-64s got %r' % ('ok  ' if ok else 'FAIL', name, got))

    # THE PROMPT SUM. The arm that matters most: a figure built on
    # input_tokens alone reports 0.0% over a 650k prompt.
    real = {'input_tokens': 2, 'cache_creation_input_tokens': 1501,
            'cache_read_input_tokens': 654276, 'output_tokens': 899}
    check('the prompt is all THREE input fields summed', prompt_of(real),
          655779)
    check('ABLATION: input_tokens alone would be 2, which is 0.0% of any '
          'window -- the whole reason cache_read is counted',
          real['input_tokens'], 2)
    check('output_tokens is NOT part of the prompt',
          prompt_of(dict(real, output_tokens=999999)), 655779)
    check('a missing field counts as zero rather than crashing',
          prompt_of({'input_tokens': 5}), 5)
    check('a usage with NO prompt key is None, not a prompt of zero',
          prompt_of({'output_tokens': 10}), None)
    check('a non-dict usage is None', prompt_of('nope'), None)

    # THE WINDOW. Smallest that fits, and COULD NOT TELL past the largest.
    check('a 150k prompt on opus-5 resolves to the 200k window',
          window_for('claude-opus-5', 150000)[0], 200000)
    check('a 657k prompt on the SAME model string resolves to 1M -- the '
          'variant records the same string, so the evidence decides',
          window_for('claude-opus-5', 657248)[0], 1000000)
    check('...and the [1m] marker on the model string is handled too',
          window_for('claude-opus-5[1m]', 657248)[0], 1000000)
    check('...and a dated build name resolves to the same family',
          window_for('claude-opus-5-20260101', 150000)[0], 200000)
    check('a prompt over every tabled window is COULD NOT TELL, not >100%',
          window_for('claude-opus-5', 1500000)[0], None)
    check('...and the reason names the figure and the largest window',
          'fits no published window' in window_for('claude-opus-5',
                                                   1500000)[1], True)
    check('an unknown model falls back to the default table rather than '
          'crashing', window_for('claude-wat-9', 150000)[0], 200000)
    check('a haiku-sized model has no 1M entry, so an over-large prompt is '
          'COULD NOT TELL', window_for('claude-haiku-4-5', 657248)[0], None)

    # RESOLUTION FAILURES ARE NEVER 0%.
    import tempfile
    sandbox = tempfile.mkdtemp(prefix='ctxverify-')
    r = verify('nosuchagent', base=sandbox)
    check('a missing project folder is a could-not-tell with a reason',
          (r['pct'], 'CANNOT BE VERIFIED' in r['why']), (None, True))
    empty = os.path.join(sandbox, PROJECT_FMT % 'emptyagent')
    os.makedirs(empty)
    r = verify('emptyagent', base=sandbox)
    check('an EMPTY project folder is a could-not-tell, not 0%',
          (r['pct'], 'nothing to measure' in r['why']), (None, True))

    # A REAL TRANSCRIPT, SYNTHESISED: two assistant turns and a decoy.
    agent_dir = os.path.join(sandbox, PROJECT_FMT % 'fakeagent')
    os.makedirs(agent_dir)
    recs = [
        {'type': 'user', 'message': {'role': 'user', 'content': 'hi'}},
        {'type': 'assistant', 'message': {
            'role': 'assistant', 'model': 'claude-opus-5',
            'usage': {'input_tokens': 1, 'cache_read_input_tokens': 300000,
                      'cache_creation_input_tokens': 0, 'output_tokens': 5}}},
        # A TOOL RESULT whose TEXT contains the word usage. Not a turn.
        {'type': 'user', 'message': {'role': 'user', 'content':
                                     'the word "usage" appears here'}},
        {'type': 'assistant', 'message': {
            'role': 'assistant', 'model': 'claude-opus-5',
            'usage': {'input_tokens': 2, 'cache_read_input_tokens': 400000,
                      'cache_creation_input_tokens': 500,
                      'output_tokens': 7}}},
    ]
    p = os.path.join(agent_dir, 'aaaa-bbbb.jsonl')
    io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(
        chr(10).join(json.dumps(r) for r in recs) + chr(10))
    r = verify('fakeagent', base=sandbox)
    check('the LAST assistant turn wins, not the first or the largest',
          r['prompt'], 400502)
    check('...and the window is the smallest that fits the session MAXIMUM',
          r['window'], 1000000)
    check('...so the percentage is the last turn over that window',
          r['pct'], 40.1)
    check('the session id is reported, because mtime is a proxy for current',
          r['session'], 'aaaa-bbbb')
    check('two assistant turns were counted and the decoy was not',
          r.get('turns'), 2)

    # SCOPE, asserted rather than left to a comment.
    check('hover and hover2 are NOT in the agent list -- the separation '
          'boundary, stated as an arm so a later edit has to argue with it',
          [a for a in BUILD_AGENTS if a.startswith('hover')], [])
    check('...and the four build agents are',
          sorted(BUILD_AGENTS), ['cc', 'cody', 'fourth', 'hank'])

    for f in os.listdir(agent_dir):
        os.remove(os.path.join(agent_dir, f))
    os.rmdir(agent_dir)
    os.rmdir(empty)
    os.rmdir(sandbox)
    print('  %d/%d fixtures classify correctly' % (total - bad, total))
    return EXIT_FINDING if bad else EXIT_CLEAN


def rows(base=None, agents=None):
    return [verify(a, base) for a in (agents or BUILD_AGENTS)]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv or '--selftest' in argv:
        return run_fixtures()
    # THE LOCK FIRST, as everywhere else here: a measurement tool whose own
    # criteria are broken reports a confident figure it never checked.
    if run_fixtures() != EXIT_CLEAN:
        print('')
        print('COULD NOT RUN: the criteria lock failed, so no figure about a '
              'real session is trustworthy.')
        return EXIT_COULD_NOT_RUN
    print('')

    one = argv[argv.index('--agent') + 1] if '--agent' in argv else None
    data = rows(agents=[one] if one else None)
    if '--json' in argv:
        print(json.dumps(data, indent=1))
        return EXIT_FINDING if any(r['pct'] is None for r in data) \
            else EXIT_CLEAN

    print('CONTEXT VERIFY -- criteria %s, read from transcripts only' %
          CRITERIA_VERSION)
    print('  projects: %s' % projects_dir())
    print('  scope   : the four BUILD agents. hover/hover2 are excluded by '
          'the separation boundary, not missing.')
    print('')
    print('  %-7s %8s %12s %11s %7s  %s'
          % ('agent', 'REAL %', 'prompt', 'window', 'age h', 'session'))
    unknown = 0
    for r in data:
        if r['pct'] is None:
            unknown += 1
            print('  %-7s %8s %12s %11s %7s  %s'
                  % (r['agent'], 'UNKNOWN', '-', '-',
                     '-' if r['age_h'] is None else r['age_h'],
                     r['session'] or '-'))
            print('           ? %s' % r['why'])
            continue
        print('  %-7s %7.1f%% %12s %11s %7s  %s'
              % (r['agent'], r['pct'], '{:,}'.format(r['prompt']),
                 '{:,}'.format(r['window']), r['age_h'], r['session']))
    print('')
    print('  THE AGE MATTERS AS MUCH AS THE FIGURE: this is the last '
          'assistant turn of the')
    print('  NEWEST transcript. An agent that stopped hours ago still has '
          'one, and its')
    print('  figure is true of that turn rather than of now.')
    if unknown:
        print('')
        print('%d agent(s) COULD NOT BE VERIFIED -- named above with a '
              'reason, and not counted as 0%%.' % unknown)
        return EXIT_FINDING
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
