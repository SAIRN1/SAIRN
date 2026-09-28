#!/usr/bin/env python3
"""tools/fail_open_scan.py -- a gate that reports SUCCESS when it could not run.

    python tools/fail_open_scan.py
    python tools/fail_open_scan.py --list
    python tools/fail_open_scan.py --baseline

Exit 0 no worse than pinned, 1 a regression, 2 COULD NOT TELL.

── THE DEFECT, MEASURED ───────────────────────────────────────────────────
.githooks/prepare-commit-msg read:

    ROOT=$(git rev-parse --show-toplevel) || exit 0
    [ -f "$ROOT/tools/staged_conflict_marker_check.py" ] || exit 0
    exec "$PY" "$ROOT/tools/staged_conflict_marker_check.py"

FROM A GIT HOOK, `exit 0` MEANS ALLOW THE COMMIT. So a git-discovery failure
allowed it and a MISSING CHECKER allowed it -- and `exec` meant a second check
appended later would have looked correct and never run. On 2026-09-28 a GitHub
token was staged and reached a commit with no commit-time content check of any
kind looking at it.

CLAUDE.md names this the most common defect shape on this platform: "a check
that depends on another tool must fail CLOSED when that tool is absent... it
does not skip one check, it reports a pass it never performed."

── THE DISCRIMINATOR, AND WITHOUT IT THIS TOOL INVENTS FINDINGS ──────────
`|| exit 0` is not the defect. The question is what the guarded test MEANS:

  SCOPE TEST       "does this gate apply HERE?" -- absent means NOT APPLICABLE,
                   and exiting 0 is correct. .githooks/pre-commit tests for
                   `.git/sairn-hover-auditor-clone`; in a build clone the
                   auditor gate genuinely does not apply, and refusing every
                   build commit would be a far worse bug than the one being
                   fixed.
  DEPENDENCY TEST  "can I check at all?" -- absent means COULD NOT RUN, and
                   exiting 0 is a pass nobody performed.

A tool that flagged both would have demanded the hover gate refuse every commit
in four clones. So SCOPE-shaped guards are classified apart and never counted as
findings; the classification is by what the guard NAMES -- a marker file, a
clone marker, an applicability flag -- not by a hand-kept list of line numbers.

── THE FOUR SHAPES IT LOOKS FOR ──────────────────────────────────────────
  exit-0-on-failure   `... || exit 0`, `|| true` on a guard
  swallowed-error     stderr to /dev/null with the status ignored
  exec-blocks-rest    `exec` in a hook, so no later check can be added
  bare-except-pass    Python `except: pass` / `except Exception: return 0`

── WHAT IT CANNOT DO ─────────────────────────────────────────────────────
It reads source text, so a fail-open expressed through a helper, a trap, or a
Python default argument is invisible; the universe is a FLOOR. And it cannot
tell whether a DEPENDENCY-shaped guard protects something that matters -- a
cosmetic reporter exiting 0 when its input is missing is fine. That judgement is
per gate and is why the output is a list to READ.

A RATCHET on docs/fail-open-coverage.json: `dependency_failopen` must never rise.
"""
import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN = os.path.join(REPO, 'docs', 'fail-open-coverage.json')

HOOK_DIRS = ('.githooks',)
SCAN_DIRS = ('tools', 'scripts', '.githooks')

EXIT0 = re.compile(r'\|\|\s*(exit\s+0|true)\b')
DEVNULL_IGNORED = re.compile(r'2>\s*/dev/null\s*(\|\||;|$)')
EXEC_HOOK = re.compile(r'^\s*exec\s+', re.M)
BARE_EXCEPT = re.compile(
    r'except\s*(?:Exception)?\s*(?:as\s+\w+)?\s*:\s*(?:\n\s+)?(pass|return\s+0|return\s+True)')

# ── WHAT THE `try` ACTUALLY WRAPS (2026-09-29) ───────────────────────────
# Reading all 30 dependency-shaped sites showed most of them are CORRECT, and
# several carry a written argument for being correct. A count of a SHAPE is not
# a count of defects, and ratcheting on the raw number would have driven 30
# edits to code that is already right.
#
# BENIGN is decided from the BODY OF THE TRY, not from a list of file names:
#   * `sys.stdout.reconfigure(...)`  -- best-effort encoding. Failing means
#     mojibake, never a wrong verdict, and refusing to run because stdout could
#     not be reconfigured would be absurd.
#   * `os.chmod(...)`, `os.remove(...)`, `worktree remove` -- best-effort
#     cleanup and permissions.
# DOCUMENTED is a nearby comment that STATES the decision -- tools/
# deploy_verify_notify.py:93 says "Fails OPEN (checks anyway) ... because the
# alternative is silently skipping a real verification", which is fail-open in
# the SAFE direction. A decision somebody wrote down and argued is not the same
# finding as one nobody noticed.
BENIGN_BODY = re.compile(
    r'\.reconfigure\(|os\.chmod\(|os\.remove\(|worktree|st_mode|unlink\(')
DOCUMENTED = re.compile(
    r'fails?\s+open|deliberate|best[- ]effort|on purpose|silently skipping',
    re.I)

# A guard whose SUBJECT is applicability, not capability. Absent => not here.
SCOPE_WORDS = re.compile(
    r'auditor-clone|-clone\b|marker|applies|applicable|opt-?in|enabled'
    r'|sairn-hover|\.git/[a-z-]*clone', re.I)


class CouldNotTell(Exception):
    pass


def mask_python(src):
    """`src` with every STRING and COMMENT blanked, same length, via tokenize.

    ── THIS TOOL REPORTED ITSELF SIX TIMES (2026-09-29) ─────────────────────
    Its first version matched raw source, so its own docstring -- which quotes
    `|| exit 0` and `except: pass` to EXPLAIN them -- counted as six findings,
    and tools/tooling_inventory.py added two more from the PURPOSES entry
    describing this very tool. EIGHT OF EIGHTEEN REPORTED SITES WERE PROSE, and
    the published figures (21 dependency, then 16) were inflated by a scanner
    reading its own description of the thing it looks for.

    That is exactly the class tools/text_gate_literal_sweep.py was built to
    measure, committed by the scanner written after it -- the third instance in
    one session.

    TOKENIZE, NOT A REGEX. A regex for Python strings has to model triple
    quotes, raw and f prefixes, escapes and nesting; the tokenizer already
    does. On a file that will not tokenize -- a syntax error, a bad encoding --
    this raises, and the caller turns that into COULD NOT TELL rather than
    scanning the raw text and pretending.
    """
    import io as _io
    import tokenize as _tok
    out = list(src)
    rdr = _io.StringIO(src).readline
    lines = src.splitlines(keepends=True)
    starts = []
    pos = 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln)
    for tok in _tok.generate_tokens(rdr):
        if tok.type not in (_tok.STRING, _tok.COMMENT):
            continue
        (r1, c1), (r2, c2) = tok.start, tok.end
        a = starts[r1 - 1] + c1
        b = starts[r2 - 1] + c2
        for k in range(a, min(b, len(out))):
            if out[k] != '\n':
                out[k] = ' '
    return ''.join(out)


def mask_shell(src):
    """`src` with shell comments and quoted strings blanked, same length.

    A `#` inside a quoted string is not a comment and a quote inside a comment
    does not open a string, so this is one left-to-right pass rather than two
    regex sweeps -- the same correction made to sairn_sql_preflight.strip_noise.
    """
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '#':
            j = src.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
            continue
        if c in '\'"':
            q, j = c, i + 1
            while j < n and src[j] != q:
                if src[j] == '\\':
                    j += 1
                j += 1
            for k in range(i, min(j + 1, n)):
                if out[k] != '\n':
                    out[k] = ' '
            i = min(j + 1, n)
            continue
        i += 1
    return ''.join(out)


def files():
    out = []
    for d in SCAN_DIRS:
        base = os.path.join(REPO, d)
        if not os.path.isdir(base):
            continue
        for root, _, names in os.walk(base):
            for n in sorted(names):
                p = os.path.join(root, n)
                if n.endswith(('.py', '.sh')) or d == '.githooks':
                    out.append(p)
    if not out:
        raise CouldNotTell('no hook or tool files found under %s'
                           % ', '.join(SCAN_DIRS))
    return out


def classify_line(masked, raw, is_hook):
    """(shape, scope) for one line, or (None, False).

    ── THE SHAPE COMES FROM CODE, THE SUBJECT FROM THE LITERAL ─────────────
    Two different questions need two different inputs, and conflating them
    broke this twice in opposite directions.

    SHAPE is matched on the MASKED line, because `|| exit 0` written inside a
    docstring is prose about the defect, not the defect -- this tool reported
    ITSELF six times before the mask existed.

    SCOPE is matched on the RAW line, because the thing that makes a guard a
    scope test is the NAME IT TESTS FOR -- `$GITDIR/sairn-hover-auditor-clone`
    -- and that name lives in a string literal, which the mask blanks. Reading
    scope from the masked line made every scope guard vanish and reclassified
    the hover-auditor marker test as a hook fail-open, which would have demanded
    every commit in four build clones be refused.
    """
    if EXIT0.search(masked):
        return 'exit-0-on-failure', bool(SCOPE_WORDS.search(raw))
    if DEVNULL_IGNORED.search(masked) and '||' in masked and 'exit' in masked:
        return 'swallowed-error', bool(SCOPE_WORDS.search(raw))
    return None, False


def scan():
    res = {}
    for path in files():
        rel = os.path.relpath(path, REPO).replace(os.sep, '/')
        try:
            src = io.open(path, encoding='utf-8', errors='replace').read()
        except OSError as exc:
            raise CouldNotTell('%s could not be read (%s) -- NOT a pass'
                               % (rel, exc))
        is_hook = rel.startswith('.githooks/')
        # ── MATCH CODE, NOT PROSE ────────────────────────────────────────
        # Every shape below is a phrase this repo also WRITES ABOUT. Matching
        # raw source made this tool report itself six times from its own
        # docstring. The mask keeps offsets, so line numbers stay true.
        try:
            if rel.endswith('.py'):
                masked = mask_python(src)
            else:
                masked = mask_shell(src)
        except Exception as exc:                                 # noqa: BLE001
            raise CouldNotTell(
                '%s could not be tokenised (%s), so its shapes were NOT '
                'measured. Scanning the raw text instead would count prose as '
                'code, which is the defect this mask exists for.'
                % (rel, str(exc)[:80]))
        hits = []
        raw_lines = src.splitlines()
        for i, line in enumerate(masked.splitlines(), 1):
            if not line.strip():
                continue
            raw_line = raw_lines[i - 1] if i <= len(raw_lines) else ''
            shape, scope = classify_line(line, raw_line, is_hook)
            if shape:
                hits.append({'line': i, 'shape': shape, 'scope': scope,
                             'text': raw_line.strip()[:78]})
        if is_hook and EXEC_HOOK.search(masked):
            m = EXEC_HOOK.search(masked)
            hits.append({'line': masked.count('\n', 0, m.start()) + 1,
                         'shape': 'exec-blocks-rest', 'scope': False,
                         'text': 'exec -- no later check can run'})
        raw_all = src.splitlines()
        for m in BARE_EXCEPT.finditer(masked):
            ln = masked.count('\n', 0, m.start()) + 1
            # Walk back to this handler's own `try:` so the classification is
            # made from WHAT IS BEING GUARDED, not from the file's name.
            lo = ln - 1
            while lo > 0 and 'try:' not in raw_all[lo - 1]:
                lo -= 1
                if ln - lo > 14:
                    break
            body = '\n'.join(raw_all[max(0, lo - 1):ln])
            near = '\n'.join(raw_all[max(0, ln - 6):min(len(raw_all), ln + 3)])
            hits.append({'line': ln, 'shape': 'bare-except-pass',
                         'scope': False,
                         'benign': bool(BENIGN_BODY.search(body)),
                         'documented': bool(DOCUMENTED.search(near)),
                         'text': m.group(0).replace('\n', ' ')[:70]})
        if hits:
            res[rel] = hits
    if not res:
        raise CouldNotTell(
            'no fail-open shape matched anywhere -- the shapes moved and '
            'NOTHING was measured. This is NOT "every gate fails closed".')
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--baseline', action='store_true')
    args = ap.parse_args(argv)

    try:
        res = scan()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2

    dep, scope, benign, documented = [], [], [], []
    for rel, hits in res.items():
        for h in hits:
            if h['scope']:
                scope.append((rel, h))
            elif h.get('benign'):
                benign.append((rel, h))
            elif h.get('documented'):
                documented.append((rel, h))
            else:
                dep.append((rel, h))
    hooks = [(r, h) for r, h in dep if r.startswith('.githooks/')]

    print('FAIL-OPEN SCAN -- a gate reporting SUCCESS when it could not run')
    print('')
    print('  DEPENDENCY-shaped (could not check -> reported clean) : %d' % len(dep))
    print('    of those, in a GIT HOOK, where exit 0 means ALLOW   : %d' % len(hooks))
    print('  SCOPE-shaped (does not apply here -> exit 0 is right) : %d' % len(scope))
    print('  BENIGN   (best-effort encoding, chmod, cleanup)       : %d' % len(benign))
    print('  DOCUMENTED (the decision is written down and argued)  : %d' % len(documented))
    print('')
    if hooks:
        print('  IN HOOKS -- highest consequence, because exit 0 is a decision:')
        for rel, h in hooks:
            print('   %-34s :%-4d %-20s %s'
                  % (rel, h['line'], h['shape'], h['text'][:38]))
        print('')
    if args.list:
        print('  ALL DEPENDENCY-SHAPED:')
        for rel, h in dep:
            print('   %-40s :%-4d %s' % (rel, h['line'], h['shape']))
        print('')
        print('  SCOPE-SHAPED (not findings, listed so the judgement is visible):')
        for rel, h in scope:
            print('   %-40s :%-4d %s' % (rel, h['line'], h['text'][:44]))
        print('')

    print('CHECKED / UNIVERSE: %d file(s) carry a shape, out of %d scanned.'
          % (len(res), len(files())))
    print('A LIST TO READ. `|| exit 0` is not itself the defect -- the question')
    print('is whether the guard asks "does this apply here" (absent = not')
    print('applicable, exit 0 correct) or "can I check at all" (absent = could')
    print('not run, exit 0 is a pass nobody performed). A tool that flagged both')
    print('would demand the hover gate refuse every commit in four clones.')
    print('')
    print('IT READS TEXT: a fail-open through a helper, a trap or a default')
    print('argument is invisible, so this is a FLOOR.')
    print('')

    if args.baseline:
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            '_what': 'Pinned fail-open coverage. Written by '
                     'tools/fail_open_scan.py --baseline. A ratchet: '
                     '`dependency_failopen` and `hook_failopen` must never rise.',
            '_why': 'From a git hook, exit 0 means ALLOW. A missing checker or a '
                    'failed git discovery that exits 0 is a pass nobody '
                    'performed -- which is how a credential reached a commit on '
                    '2026-09-28.',
            'files_with_a_shape': len(res),
            'dependency_failopen': len(dep),
            'hook_failopen': len(hooks),
            'scope_shaped': len(scope),
            'hook_sites': ['%s:%d' % (r, h['line']) for r, h in hooks],
        }, indent=2, sort_keys=True) + '\n')
        print('wrote %s' % os.path.relpath(PIN, REPO))
        return 0

    if not os.path.isfile(PIN):
        sys.stderr.write('COULD NOT TELL -- %s does not exist, so NOTHING was '
                         'compared. Run --baseline once.\n'
                         % os.path.relpath(PIN, REPO))
        return 2
    try:
        pin = json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        sys.stderr.write('COULD NOT TELL -- %s will not parse (%s).\n'
                         % (os.path.relpath(PIN, REPO), e))
        return 2
    was = pin.get('dependency_failopen')
    if not isinstance(was, int):
        sys.stderr.write('COULD NOT TELL -- the pin carries no integer '
                         '`dependency_failopen`.\n')
        return 2
    if len(dep) > was:
        print('REGRESSION -- dependency fail-opens rose from %d to %d.'
              % (was, len(dep)))
        return 1
    if len(dep) < was:
        print('IMPROVED -- fell from %d to %d. Re-pin:' % (was, len(dep)))
        return 0
    print('OK -- no worse than pinned (%d dependency, %d of them in hooks).'
          % (was, len(hooks)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
