#!/usr/bin/env python
# OWNER: cc
# written 2026-10-19, batch b20 items 1-4
"""REAL context% per build agent, read from its own transcript -- independent
of anything any agent says about itself.

    python tools/context_verify.py                 # all four build agents
    python tools/context_verify.py --agent hank
    python tools/context_verify.py --agent self    # whoever this clone is
    python tools/context_verify.py --json
    python tools/context_verify.py --digest-line    # the line to PASTE in a digest
    python tools/context_verify.py --check-digest SAIRN-digest-cc-b21.txt
    python tools/context_verify.py --fixtures      # the criteria lock

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── WHY --digest-line AND --check-digest EXIST (added 2026-10-19, b21) ──────
b20 measured the gap this tool was built to find and then left it open: every
build agent's SELF-REPORTED context under-read the real figure by 7 to 12
points -- cc 61.9 vs 68.8, cody 59.2 vs 66.3, fourth 48.0 vs 60.0. Printing a
board column beside the self-report makes the gap VISIBLE; it does not stop
the next digest carrying an estimate. The source of the defect is the digest's
`CONTEXT` line being TYPED.

So it is no longer typed. `--digest-line` emits the exact line, and
`--check-digest` re-derives it, which is what the push gate runs:

    CONTEXT 69.6% of 1,000,000 -- 696,085 tokens, measured.

THE ARM WITH TEETH IS NOT THE SHAPE, IT IS THE TOKEN COUNT. An estimate can
be written in the measured shape; what it cannot do is match, to the token, a
prompt size that a real assistant turn in this session's own transcript
actually carried. So the check is: the stated token count must EQUAL some real
turn's prompt. A typed figure does not, and the tool's own output always does.

The percentage is then checked against the stated count and window
arithmetically, which catches a real count with a hand-edited percentage over
it.

THE WINDOW IS CHECKED LOOSELY, ON PURPOSE. It must be a published window for
the measured model and must be at least the stated count -- not equal to the
window measured at PUSH time, because a session that crossed 200k between
writing the digest and pushing it would have two honest answers and the gate
would refuse the earlier one.

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

── AND THAT INFERENCE IS A FLOOR, WHICH b20 DID NOT SAY OUT LOUD (b21) ─────
MEASURED THE FIRST TIME THIS TOOL WAS POINTED AT A FRESH SESSION, 2026-10-19.
cc's new window carried 141,853 tokens on `claude-opus-5`, so the smallest
tabled window it fits in is 200,000 and the tool printed **70.9%** -- while
the session was in fact a 1M one at **14.2%**. The inference is sound in ONE
direction only: it is a FLOOR on the window, therefore a CEILING on the
percentage, and it is only tight once the session has passed the smaller
window. b20's figures were safe because all four agents were already between
584k and 670k; a batch's FIRST digest is exactly where it is not.

A 5x-wrong denominator wired into every digest is worse than no figure, so the
denominator now has a DECLARED source and the inference is the fallback:

    python tools/context_verify.py --provision-window 1000000

writes `.git/sairn-context-window` in this clone -- not tracked, per-clone,
surviving a rename, the same convention as the session-identity marker it
sits beside. A declared window that is SMALLER than a prompt actually observed
is refused rather than used: the declaration is then the thing that is wrong.

IT IS KEYED BY SESSION ID, NOT BY CLONE, and that is not tidiness. The
observed prompt witnesses a declaration that is too SMALL and can never
witness one that is too LARGE -- 1,000,000 left standing in a clone whose next
session runs on a 200k model would report 15% while that session sat at 75%,
which is the understatement b20 existed to stop. So a declaration speaks only
for the session that made it, and a new session declares again. The cost is
one command per batch and it is the correct trade.

With nothing declared and more than one published window still fitting, the
row is AMBIGUOUS -- the token count is reported, both candidate percentages
are named, and `--digest-line` REFUSES to emit a confident line. The remedy is
one command and it is printed.

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

CRITERIA_VERSION = '2026-10-19.2'

# How far back a digest's token count may be matched against a real turn.
# MEASURED rather than picked: the four build agents hold 44-47 transcripts
# and 246-275 MB each, and scanning all of them in a push gate is not free --
# but only 1 or 2 per agent (4.8-5.9 MB) have been touched in the last day,
# which is the only span in which a digest written this batch can live. The
# cost of the bound is honest and stated: a digest whose figure came from a
# session older than this reads as UNMATCHED rather than as wrong.
RECENT_WINDOW_H = 24.0

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

# The DECLARED window, per clone, beside the session-identity marker and for
# the same three reasons: untracked so it cannot travel in a commit,
# per-clone so five working copies have five answers, and surviving a rename.
WINDOW_MARKER = 'sairn-context-window'


def clone_dir(agent):
    """The sibling build clone for `agent`. Build clones only -- the hover
    clones are not reachable from here and must not be added."""
    return os.path.join(os.path.dirname(REPO), 'SAIRN-%s' % agent)


def _git_dir_of(clone):
    """-> the .git directory of `clone`, handling the worktree `.git` FILE."""
    g = os.path.join(clone, '.git')
    if os.path.isdir(g):
        return g
    if os.path.isfile(g):
        try:
            raw = io.open(g, encoding='utf-8').read().strip()
        except OSError:
            return None
        if raw.startswith('gitdir:'):
            p = raw.split(':', 1)[1].strip()
            return p if os.path.isabs(p) else os.path.abspath(
                os.path.join(clone, p))
    return None


def declared_window(agent, clone=None, session=None):
    """-> (tokens_or_None, why). The window declared FOR THAT SESSION.

    KEYED BY SESSION, NOT BY CLONE, and that is the whole safety of it. A
    clone-wide marker would be wrong in the DANGEROUS direction the first time
    a cc session ran on a 200k model: 1,000,000 declared over a 150k prompt
    reports 15% while the session is at 75%, and understating context is the
    exact defect b20 was about. The too-SMALL direction is caught by the
    observed prompt; the too-LARGE direction has no such witness, so it is
    closed by scope instead -- a declaration only ever speaks for the session
    that made it.

    None with an empty `why` means simply 'nothing declared for this session',
    which is not an error -- the caller falls back to the inference and says
    that it did.
    """
    c = clone or clone_dir(agent)
    g = _git_dir_of(c)
    if not g or not session:
        return None, ''
    p = os.path.join(g, WINDOW_MARKER)
    if not os.path.isfile(p):
        return None, ''
    try:
        lines = io.open(p, encoding='utf-8').read().splitlines()
    except OSError as exc:
        return None, '%s exists but could not be read (%s)' % (p, exc)
    for raw in lines:
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        parts = raw.split()
        if len(parts) != 2 or parts[0] != session:
            continue
        digits = parts[1].replace(',', '').replace('_', '')
        if not digits.isdigit() or int(digits) <= 0:
            return None, ('%s declares %r for session %s, which is not a '
                          'token count. A marker that is present but '
                          'unreadable is a third state and is not a window.'
                          % (p, parts[1][:40], session[:8]))
        return int(digits), ''
    return None, ''


def provision_window(tokens, clone=None, session=None, agent=None, base=None):
    """Declare the window for ONE session. -> (path, session, tokens).

    With no `session`, the session is the newest transcript in this clone's own
    project folder -- the same mtime proxy the rest of this tool uses and
    prints.
    """
    c = clone or REPO
    g = _git_dir_of(c)
    if not g:
        raise OSError('no .git directory found for %s, so there is nowhere to '
                      'write the window marker' % c)
    n = int(str(tokens).replace(',', '').replace('_', ''))
    if n <= 0:
        raise ValueError('%r is not a token count' % tokens)
    if not session:
        who = agent
        if who is None:
            who, why = resolve_agent('self', c)
            if who is None:
                raise OSError(why)
        path, _, why = newest_transcript(who, base)
        if not path:
            raise OSError(why)
        session = os.path.basename(path)[:-6]
    p = os.path.join(g, WINDOW_MARKER)
    keep = []
    if os.path.isfile(p):
        for raw in io.open(p, encoding='utf-8').read().splitlines():
            parts = raw.strip().split()
            if len(parts) == 2 and parts[0] == session:
                continue                      # replaced, not duplicated
            if raw.strip():
                keep.append(raw.rstrip())
    keep.append('%s %d' % (session, n))
    io.open(p, 'w', encoding='utf-8', newline=chr(10)).write(
        chr(10).join(keep) + chr(10))
    return p, session, n


def projects_dir():
    return os.path.join(os.path.expanduser('~'), '.claude', 'projects')


def model_family(model):
    """'claude-opus-5[1m]' or 'claude-opus-5-20260101' -> a WINDOWS key."""
    m = (model or '').strip()
    m = re.sub(r'\[[^\]]*\]$', '', m)             # the [1m] variant marker
    m = re.sub(r'-\d{8}$', '', m)                 # a dated build
    return m


def window_for(model, observed_max, declared=None):
    """-> (window, why_or_''). DECLARED if there is one, else the SMALLEST
    tabled window the prompt fits -- which is a FLOOR, see the docstring.

    Pure. `observed_max` is the largest prompt actually seen in the session,
    which is the only evidence available that distinguishes two variants of
    one model string.
    """
    fam = model_family(model)
    sizes = WINDOWS.get(fam, DEFAULT_WINDOWS)
    if declared:
        if observed_max > declared:
            return None, ('this clone DECLARES a window of %s and a prompt of '
                          '%s was actually observed, so the DECLARATION is '
                          'the thing that is wrong -- no percentage is '
                          'reported off a denominator already contradicted. '
                          'Re-provision it: python tools/context_verify.py '
                          '--provision-window <tokens>'
                          % ('{:,}'.format(declared),
                             '{:,}'.format(observed_max)))
        return declared, ''
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
            'last_ts': '', 'prompts': set()}
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
            out['prompts'].add(p)
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


def verify(agent, base=None, now=None, clone=None):
    """-> one row dict. The whole measurement for one agent, no self-report.

    `clone` overrides where the DECLARED window is read from, so a fixture can
    exercise this against a sandbox instead of a real sibling clone -- a
    criteria lock that reads live state is not a lock.
    """
    now = float(now if now is not None else time.time())
    row = {'agent': agent, 'pct': None, 'prompt': None, 'window': None,
           'model': '', 'session': '', 'transcripts': 0, 'age_h': None,
           'why': '', 'window_source': '', 'ambiguous': False,
           'candidates': []}
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
    decl, d_why = declared_window(agent, clone, row['session'])
    if d_why:
        row['why'] = d_why
        return row
    win, w_why = window_for(got['model'], got['observed_max'], decl)
    if win is None:
        row['why'] = w_why
        return row
    row['window'] = win
    row['window_source'] = 'declared' if decl else 'inferred'
    row['pct'] = round(100.0 * got['prompt'] / float(win), 1)
    if not decl:
        # THE FLOOR IS ONLY TIGHT ONCE THE SESSION HAS PASSED THE SMALLER
        # WINDOW. Say so with the numbers rather than printing one of them.
        fam = model_family(got['model'])
        fits = [s for s in WINDOWS.get(fam, DEFAULT_WINDOWS)
                if got['observed_max'] <= s]
        if len(fits) > 1:
            row['ambiguous'] = True
            row['candidates'] = [
                {'window': s,
                 'pct': round(100.0 * got['prompt'] / float(s), 1)}
                for s in fits]
            row['why'] = ('the window is INFERRED and %d published sizes still '
                          'fit (%s), so the percentage could be any of %s. '
                          'The token count is the measured part. Declare it '
                          'once: python tools/context_verify.py '
                          '--provision-window <tokens>'
                          % (len(fits),
                             ', '.join('{:,}'.format(s) for s in fits),
                             ', '.join('%.1f%%' % c['pct']
                                       for c in row['candidates'])))
    return row


# ── WHO IS THIS CLONE ───────────────────────────────────────────────────────
def resolve_agent(name, start=None):
    """'self' -> this clone's session name. -> (agent_or_None, why).

    The identity comes from tools/sairn_session_identity.py, which reads a
    marker inside .git/ rather than the directory name. It is NOT guessed:
    a clone with no marker (a git WORKTREE is the common case) gets None and
    a reason, and the caller decides what that means -- see check_digest.
    """
    if name != 'self':
        return name, ''
    try:
        sys.path.insert(0, TOOLS)
        import sairn_session_identity as ident
        return ident.session_name(start), ''
    except Exception as exc:                                     # noqa: BLE001
        return None, ('this clone\'s session identity could not be '
                      'established, so "self" resolves to nobody: %s'
                      % str(exc).splitlines()[0])


# ── THE DIGEST LINE ─────────────────────────────────────────────────────────
# One format, one regex, one producer. The shape is b20's, kept rather than
# redesigned -- four digests already carry it and a new shape would make every
# one of them a finding for no gain.
DIGEST_RE = re.compile(
    r'^CONTEXT\s+(\d+(?:\.\d+)?)%\s+of\s+([\d,]+)\s*--\s*([\d,]+)\s+tokens,'
    r'\s*measured\.?\s*$', re.M)


def digest_line(row):
    """The line a digest must carry, built from a measurement. -> str or None."""
    if row.get('pct') is None:
        return None
    return ('CONTEXT %.1f%% of %s -- %s tokens, measured.'
            % (row['pct'], '{:,}'.format(row['window']),
               '{:,}'.format(row['prompt'])))


def parse_digest_line(text):
    """-> (pct, window, prompt) from a digest's CONTEXT line, or None.

    `text` may be the whole file. The LAST match wins, for the same reason the
    last assistant turn does: an appended correction is the current answer.
    """
    found = None
    for m in DIGEST_RE.finditer(text or ''):
        found = m
    if not found:
        return None
    return (float(found.group(1)),
            int(found.group(2).replace(',', '')),
            int(found.group(3).replace(',', '')))


def recent_transcripts(agent, base=None, now=None):
    """Transcripts touched within RECENT_WINDOW_H, newest first. -> (paths, why)."""
    now = float(now if now is not None else time.time())
    d = os.path.join(base or projects_dir(), PROJECT_FMT % agent)
    if not os.path.isdir(d):
        return [], 'no project folder at %s' % d
    try:
        names = [f for f in os.listdir(d) if f.endswith('.jsonl')]
    except OSError as exc:
        return [], 'project folder unreadable (%s)' % exc
    rows = []
    for f in names:
        p = os.path.join(d, f)
        try:
            mt = os.path.getmtime(p)
        except OSError:
            continue
        if (now - mt) <= RECENT_WINDOW_H * 3600.0:
            rows.append((mt, p))
    if not rows:
        return [], ('no transcript in %s was touched in the last %gh, so there '
                    'is no recent turn to match against -- not a mismatch'
                    % (d, RECENT_WINDOW_H))
    rows.sort(reverse=True)
    return [p for _, p in rows], ''


def prompt_was_real(agent, value, base=None, now=None):
    """Did some real assistant turn carry exactly `value` tokens of prompt?

    -> (True/False/None, evidence). None is COULD NOT TELL -- no transcript to
    read -- and is never folded into False, because "I could not look" and
    "I looked and it is not there" are different answers and only one of them
    is an accusation.
    """
    paths, why = recent_transcripts(agent, base, now)
    if not paths:
        return None, why
    scanned = 0
    for p in paths:
        got = scan_transcript(p)
        scanned += 1
        if got.get('why'):
            continue
        if value in got['prompts']:
            return True, ('matched a real assistant turn in %s (%d turn(s) '
                           'read)' % (os.path.basename(p)[:8], got['turns']))
    return False, ('%s token(s) matches no assistant turn in any of this '
                   'agent\'s %d transcript(s) touched in the last %gh'
                   % ('{:,}'.format(value), scanned, RECENT_WINDOW_H))


# What a digest's CONTEXT line can be. Four states, and COULD-NOT-TELL is one
# of them rather than being folded into either verdict.
OK = 'OK'
MISSING = 'MISSING'
INCONSISTENT = 'INCONSISTENT'
NOT_MEASURED = 'NOT_MEASURED'
UNTOLD = 'COULD_NOT_TELL'


def check_digest(text, agent, base=None, now=None, clone=None):
    """Is this digest's CONTEXT line a MEASUREMENT? -> dict.

    Keys: verdict (one of the five above), why, line, pct, window, prompt.
    """
    out = {'agent': agent, 'verdict': UNTOLD, 'why': '', 'line': '',
           'pct': None, 'window': None, 'prompt': None}
    if agent not in BUILD_AGENTS:
        out['why'] = ('%r is not one of the four build agents, so this check '
                      'does not apply -- hover and hover2 are outside it by '
                      'the separation boundary, not by oversight' % agent)
        return out
    parsed = parse_digest_line(text)
    if parsed is None:
        out['verdict'] = MISSING
        out['why'] = ('no CONTEXT line in the measured shape. The line is not '
                      'written by hand: run `python tools/context_verify.py '
                      '--digest-line` and paste what it prints.')
        return out
    pct, window, prompt = parsed
    out.update({'pct': pct, 'window': window, 'prompt': prompt})
    out['line'] = ('CONTEXT %s%% of %s -- %s tokens, measured.'
                   % (pct, '{:,}'.format(window), '{:,}'.format(prompt)))

    # ARITHMETIC FIRST, because it needs nothing and catches a hand-edited
    # percentage sitting over a real token count.
    want = round(100.0 * prompt / float(window), 1) if window else None
    if want is None or abs(want - pct) > 0.051:
        out['verdict'] = INCONSISTENT
        out['why'] = ('%s tokens of %s is %.1f%%, and the line says %.1f%% -- '
                      'the percentage does not come from the count beside it'
                      % ('{:,}'.format(prompt), '{:,}'.format(window),
                         want if want is not None else -1.0, pct))
        return out
    if prompt > window:
        out['verdict'] = INCONSISTENT
        out['why'] = ('a prompt of %s cannot sit in a window of %s'
                      % ('{:,}'.format(prompt), '{:,}'.format(window)))
        return out

    # THE WINDOW, loosely: a published size for this agent's measured model.
    # See the module docstring for why this is not an equality check.
    measured = verify(agent, base, now, clone)
    fam = model_family(measured.get('model'))
    sizes = WINDOWS.get(fam, DEFAULT_WINDOWS)
    decl, _ = declared_window(agent, clone, measured.get('session'))
    if decl and window != decl:
        out['verdict'] = INCONSISTENT
        out['why'] = ('this clone DECLARES a window of %s and the line says '
                      '%s' % ('{:,}'.format(decl), '{:,}'.format(window)))
        return out
    if window not in sizes and not decl:
        out['verdict'] = INCONSISTENT
        out['why'] = ('%s is not a published window for %r (published: %s)'
                      % ('{:,}'.format(window), fam or 'unknown',
                         ', '.join('{:,}'.format(s) for s in sizes)))
        return out

    # AND THE ARM WITH TEETH.
    real, evidence = prompt_was_real(agent, prompt, base, now)
    if real is None:
        out['verdict'] = UNTOLD
        out['why'] = evidence
        return out
    if not real:
        out['verdict'] = NOT_MEASURED
        out['why'] = evidence
        return out
    out['verdict'] = OK
    out['why'] = evidence
    return out


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

    # THE DECLARED WINDOW (b21). The inference is a FLOOR and the fresh-session
    # case is where that bites: 141,853 tokens read as 70.9% of 200k while the
    # session was a 1M one at 14.2%.
    check('A DECLARATION BEATS THE INFERENCE -- the fresh-1M-session case, '
          'which the inference alone gets 5x wrong',
          window_for('claude-opus-5', 150000, declared=1000000)[0], 1000000)
    check('a declaration SMALLER than a prompt actually observed is refused, '
          'and the DECLARATION is named as the wrong thing',
          (window_for('claude-opus-5', 657248, declared=200000)[0],
           'DECLARATION is the thing that is wrong' in
           window_for('claude-opus-5', 657248, declared=200000)[1]),
          (None, True))
    check('a declaration outside the published table is still honoured -- it '
          'is a measurement of this clone, not a vote on the table',
          window_for('claude-opus-5', 150000, declared=500000)[0], 500000)

    # RESOLUTION FAILURES ARE NEVER 0%.
    import tempfile
    sandbox = tempfile.mkdtemp(prefix='ctxverify-')
    r = verify('nosuchagent', base=sandbox, clone=sandbox)
    check('a missing project folder is a could-not-tell with a reason',
          (r['pct'], 'CANNOT BE VERIFIED' in r['why']), (None, True))
    empty = os.path.join(sandbox, PROJECT_FMT % 'emptyagent')
    os.makedirs(empty)
    r = verify('emptyagent', base=sandbox, clone=sandbox)
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
    r = verify('fakeagent', base=sandbox, clone=sandbox)
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

    # AMBIGUITY, AND THE MARKER THAT RESOLVES IT.
    fresh_dir = os.path.join(sandbox, PROJECT_FMT % 'freshagent')
    os.makedirs(fresh_dir)
    io.open(os.path.join(fresh_dir, 'fresh.jsonl'), 'w', encoding='utf-8',
            newline=chr(10)).write(json.dumps(
                {'type': 'assistant', 'message': {
                    'role': 'assistant', 'model': 'claude-opus-5',
                    'usage': {'input_tokens': 2,
                              'cache_read_input_tokens': 141851,
                              'cache_creation_input_tokens': 0}}}) + chr(10))
    r = verify('freshagent', base=sandbox, clone=sandbox)
    check('THE REAL 2026-10-19 CASE: 141,853 tokens on an undeclared clone is '
          'AMBIGUOUS, not a confident 70.9%',
          (r['ambiguous'], r['prompt']), (True, 141853))
    check('...and BOTH candidate percentages are named rather than one picked '
          'silently',
          [(c['window'], c['pct']) for c in r['candidates']],
          [(200000, 70.9), (1000000, 14.2)])
    check('...and the reported pct stays the CEILING, so nothing reads as '
          'safer than it might be', r['pct'], 70.9)
    check('...and the window is marked INFERRED, not presented as measured',
          r['window_source'], 'inferred')
    fake_clone = os.path.join(sandbox, 'SAIRN-freshagent')
    os.makedirs(os.path.join(fake_clone, '.git'))
    check('an unprovisioned clone declares nothing, and that is not an error',
          declared_window('freshagent', clone=fake_clone, session='fresh'),
          (None, ''))
    wp, wsid, wn = provision_window(1000000, clone=fake_clone,
                                    agent='freshagent', base=sandbox)
    check('--provision-window writes the marker beside the identity one, '
          'inside .git/ so it cannot travel in a commit, KEYED BY SESSION',
          (os.path.basename(wp), os.path.basename(os.path.dirname(wp)),
           wsid, wn), (WINDOW_MARKER, '.git', 'fresh', 1000000))
    check('...and it reads back for THAT session',
          declared_window('freshagent', clone=fake_clone, session='fresh'),
          (1000000, ''))
    check('...AND NOT FOR ANOTHER ONE -- a declaration speaks only for the '
          'session that made it, which is what closes the too-LARGE '
          'direction the observed prompt cannot witness',
          declared_window('freshagent', clone=fake_clone,
                          session='some-other-session'), (None, ''))
    r = verify('freshagent', base=sandbox, clone=fake_clone)
    check('WITH THE MARKER the same transcript reads 14.2% of 1M and is no '
          'longer ambiguous',
          (r['pct'], r['window'], r['ambiguous'], r['window_source']),
          (14.2, 1000000, False, 'declared'))
    wp2, _, _ = provision_window(200000, clone=fake_clone, agent='freshagent',
                                 base=sandbox)
    check('RE-PROVISIONING REPLACES that session\'s line rather than adding a '
          'second answer to one question',
          len([x for x in io.open(wp2, encoding='utf-8').read().splitlines()
               if x.strip()]), 1)
    io.open(wp, 'w', encoding='utf-8', newline=chr(10)).write(
        'fresh a-million' + chr(10))
    got = declared_window('freshagent', clone=fake_clone, session='fresh')
    check('a marker PRESENT BUT UNREADABLE is a third state with a reason, '
          'never silently the inference',
          (got[0], 'not a token count' in got[1]), (None, True))
    r = verify('freshagent', base=sandbox, clone=fake_clone)
    check('...and that reason stops the row rather than producing a figure',
          (r['pct'], 'not a token count' in r['why']), (None, True))
    os.remove(wp)
    os.rmdir(os.path.join(fake_clone, '.git'))
    os.rmdir(fake_clone)
    for f in os.listdir(fresh_dir):
        os.remove(os.path.join(fresh_dir, f))
    os.rmdir(fresh_dir)

    # SCOPE, asserted rather than left to a comment.
    check('hover and hover2 are NOT in the agent list -- the separation '
          'boundary, stated as an arm so a later edit has to argue with it',
          [a for a in BUILD_AGENTS if a.startswith('hover')], [])
    check('...and the four build agents are',
          sorted(BUILD_AGENTS), ['cc', 'cody', 'fourth', 'hank'])

    # ── THE DIGEST LINE (b21) ──────────────────────────────────────────────
    REAL = 'CONTEXT 69.6% of 1,000,000 -- 696,085 tokens, measured.'
    check('b20\'s own digest line parses -- the shape already in use, not a '
          'new one', parse_digest_line(REAL), (69.6, 1000000, 696085))
    check('...and the producer regenerates it byte for byte from a row',
          digest_line({'pct': 69.6, 'window': 1000000, 'prompt': 696085}),
          REAL)
    check('the line is found inside a whole digest file, not only alone',
          parse_digest_line('STATUS: x' + chr(10) + REAL + chr(10)),
          (69.6, 1000000, 696085))
    check('the LAST CONTEXT line wins, so an appended correction is the '
          'answer',
          parse_digest_line(REAL + chr(10) +
                            'CONTEXT 70.0% of 1,000,000 -- 700,000 tokens, '
                            'measured.')[0], 70.0)
    check('a BARE percentage -- the shape every self-estimate took -- does '
          'not parse at all', parse_digest_line('CONTEXT 61.9%'), None)
    check('...nor does one that drops the word measured',
          parse_digest_line('CONTEXT 69.6% of 1,000,000 -- 696,085 tokens.'),
          None)
    check('an unmeasurable row produces NO line rather than a 0% one',
          digest_line({'pct': None}), None)

    # check_digest, against a transcript whose real turns are known.
    DIG = 'CONTEXT 40.1% of 1,000,000 -- 400,502 tokens, measured.'
    r = check_digest(DIG, 'fakeagent', base=sandbox, clone=sandbox)
    check('an agent outside the four is NOT CHECKED rather than refused',
          (r['verdict'], 'separation boundary' in r['why']), (UNTOLD, True))
    # The same fixture transcript, under a BUILD AGENT's folder name, so the
    # arms below exercise the real path rather than the early return.
    build_dir = os.path.join(sandbox, PROJECT_FMT % 'cc')
    os.makedirs(build_dir)
    io.open(os.path.join(build_dir, 'cccc-dddd.jsonl'), 'w',
            encoding='utf-8', newline=chr(10)).write(
        chr(10).join(json.dumps(x) for x in recs) + chr(10))
    r = check_digest(DIG, 'cc', base=sandbox, clone=sandbox)
    check('a line whose COUNT matches a real assistant turn is OK',
          r['verdict'], OK)
    check('...and the evidence names the transcript it matched',
          'matched a real assistant turn' in r['why'], True)
    r = check_digest('STATUS: done.', 'cc', base=sandbox, clone=sandbox)
    check('NO CONTEXT line is MISSING, and the reason is the command to run',
          (r['verdict'], '--digest-line' in r['why']), (MISSING, True))
    r = check_digest('CONTEXT 48.0% of 1,000,000 -- 400,502 tokens, '
                     'measured.', 'cc', base=sandbox, clone=sandbox)
    check('A REAL COUNT WITH A HAND-EDITED PERCENTAGE IS REFUSED -- this is '
          'the exact b20 under-read shape, 48.0 typed over a 40.1 fact',
          r['verdict'], INCONSISTENT)
    r = check_digest('CONTEXT 30.0% of 1,000,000 -- 300,000 tokens, '
                     'measured.', 'cc', base=sandbox, clone=sandbox)
    check('AN INTERNALLY CONSISTENT ESTIMATE IS STILL REFUSED, because no '
          'real turn carried 300,000 tokens -- the arm with teeth',
          r['verdict'], NOT_MEASURED)
    check('...and the reason says what was searched rather than accusing',
          'matches no assistant turn' in
          check_digest('CONTEXT 30.0% of 1,000,000 -- 300,000 tokens, '
                       'measured.', 'cc', base=sandbox, clone=sandbox)['why'], True)
    r = check_digest('CONTEXT 40.1% of 999,999 -- 400,502 tokens, measured.',
                     'cc', base=sandbox, clone=sandbox)
    check('a window that is not a PUBLISHED size is refused',
          r['verdict'], INCONSISTENT)
    r = check_digest('CONTEXT 200.0% of 200,000 -- 400,000 tokens, '
                     'measured.', 'cc', base=sandbox, clone=sandbox)
    check('a prompt larger than its own window is refused, not reported at '
          '200%', r['verdict'], INCONSISTENT)
    # AND THE COULD-NOT-TELL ARM: a real count, but every transcript too old.
    old = os.path.join(sandbox, PROJECT_FMT % 'cody')
    os.makedirs(old)
    op = os.path.join(old, 'eeee-ffff.jsonl')
    io.open(op, 'w', encoding='utf-8', newline=chr(10)).write(
        chr(10).join(json.dumps(x) for x in recs) + chr(10))
    os.utime(op, (0, 0))
    r = check_digest(DIG, 'cody', base=sandbox, clone=sandbox)
    check('NO RECENT TRANSCRIPT IS COULD-NOT-TELL, never NOT_MEASURED -- '
          '"I could not look" is not an accusation',
          (r['verdict'], 'not a mismatch' in r['why']), (UNTOLD, True))

    check('resolve_agent passes a named agent through untouched',
          resolve_agent('hank')[0], 'hank')

    for f in os.listdir(build_dir):
        os.remove(os.path.join(build_dir, f))
    os.rmdir(build_dir)
    for f in os.listdir(old):
        os.remove(os.path.join(old, f))
    os.rmdir(old)
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

    if '--provision-window' in argv:
        try:
            p, sid, n = provision_window(
                argv[argv.index('--provision-window') + 1])
        except (OSError, ValueError, IndexError) as exc:
            print('COULD NOT RUN: %s' % exc)
            return EXIT_COULD_NOT_RUN
        print('declared window: %s tokens for session %s'
              % ('{:,}'.format(n), sid))
        print('  %s' % p)
        print('  Untracked, per-clone and KEYED BY SESSION, so it cannot '
              'travel in a commit and')
        print('  cannot speak for a later session on a different model. It is '
              'a DECLARATION, not')
        print('  a measurement: a prompt observed above it is refused rather '
              'than reported as')
        print('  over 100%, and a NEW session declares again.')
        return EXIT_CLEAN

    one = argv[argv.index('--agent') + 1] if '--agent' in argv else None
    if one:
        one, why = resolve_agent(one)
        if one is None:
            print('COULD NOT RUN: %s' % why)
            return EXIT_COULD_NOT_RUN

    # ── THE LINE A DIGEST MUST CARRY ───────────────────────────────────────
    if '--digest-line' in argv:
        agent = one
        if agent is None:
            agent, why = resolve_agent('self')
            if agent is None:
                print('COULD NOT RUN: %s' % why)
                return EXIT_COULD_NOT_RUN
        if agent not in BUILD_AGENTS:
            print('COULD NOT RUN: %r is not one of the four build agents (%s). '
                  'hover and hover2 are outside this tool by the separation '
                  'boundary.' % (agent, ', '.join(BUILD_AGENTS)))
            return EXIT_COULD_NOT_RUN
        row = verify(agent)
        line = digest_line(row)
        if line is None:
            print('COULD NOT RUN: %s' % row['why'])
            return EXIT_COULD_NOT_RUN
        if row['ambiguous']:
            # REFUSE rather than emit the ceiling as if it were the figure.
            # This is the whole point of b21: a wrong denominator wired into
            # every digest is worse than a digest that says it does not know.
            print('COULD NOT RUN: %s' % row['why'])
            print('')
            print('  the measured part, which is NOT in doubt: %s tokens'
                  % '{:,}'.format(row['prompt']))
            return EXIT_COULD_NOT_RUN
        print(line)
        return EXIT_CLEAN

    # ── AND THE RE-DERIVATION THE PUSH GATE RUNS ───────────────────────────
    if '--check-digest' in argv:
        path = argv[argv.index('--check-digest') + 1]
        agent = one
        if agent is None:
            agent, why = resolve_agent('self')
            if agent is None:
                print('COULD NOT TELL: %s' % why)
                return EXIT_COULD_NOT_RUN
        try:
            text = io.open(path, encoding='utf-8', errors='replace').read()
        except OSError as exc:
            print('COULD NOT RUN: %s is unreadable (%s)' % (path, exc))
            return EXIT_COULD_NOT_RUN
        r = check_digest(text, agent)
        print('%-14s %s  (%s)' % (r['verdict'], os.path.basename(path), agent))
        print('  %s' % r['why'])
        if r['verdict'] == OK:
            return EXIT_CLEAN
        if r['verdict'] == UNTOLD:
            return EXIT_COULD_NOT_RUN
        return EXIT_FINDING

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
        print('  %-7s %7.1f%% %12s %11s %7s  %s%s'
              % (r['agent'], r['pct'], '{:,}'.format(r['prompt']),
                 '{:,}'.format(r['window']), r['age_h'], r['session'],
                 '' if r['window_source'] == 'declared' else '  [window '
                 'INFERRED]'))
        if r['ambiguous']:
            unknown += 1
            print('           ? %s' % r['why'])
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
