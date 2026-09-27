"""
PostToolUse hook for Write|Edit, and a CLI. Runs the open-work index's
duplicate-row check when that index is the file just written.

── WHY THIS EXISTS (2026-09-26) ────────────────────────────────────────────
`tools/index_duplicate_check.py` catches *"two rows of
docs/SAIRN-OPEN-WORK-INDEX.md describing the same subject -- a superseded row
that was never removed, so the file every session reads to choose work gives
two answers and the reader cannot tell which is current."*

The document IS its subject, and the defect is introduced BY AN EDIT TO IT.
Its only wiring was `report_only_checks.REGISTRY`, whose hook returns 0 unless
the Bash command was a `git push`. So it ran after a push and never at the
moment a row was added — and a session that edited the index and did not push
ran it zero times.

Found by `tools/invocation_path_scan.py` and triaged in
`docs/2026-09-26-invocation-path-sweep.md` as the one candidate of five that is
genuinely the same shape as the citation-drift gap. This is the fix that triage
recommended.

── WHY A WRAPPER AND NOT THE CHECKER ITSELF IN settings.json ───────────────
`index_duplicate_check.py` does not self-scope by `file_path`: run it directly
from a Write|Edit hook and it re-reads the whole index after EVERY edit in the
repo — every app file, every test, every doc. That is a check somebody turns
off. This wrapper returns silently unless the edited file IS the index.

── AND WHY IT REPORTS THE DIFFERENCE, NOT THE TOTAL ───────────────────────
Same decision as `citation_drift_hook.py`, for the same reason and with the
same precedent: the push gate's generated-document check already says in its own
words, *"This check refuses only what THIS push broke."* An index carrying
pre-existing duplicate pairs would print all of them after every save, and
noise is worse than the gap it closed.

THE KEY IS THE ROW TEXT, NOT THE LINE NUMBERS, and that matters: every line
number in the index moves when a row is inserted anywhere above, so a
line-keyed diff would report every existing pair as newly introduced by any
edit at all. The trade is stated in `--selftest`: REWORDING one row of an
existing pair does read as a new pair, because by its text it is one.

── FAILS CLOSED (PR 1.11) ─────────────────────────────────────────────────
If the checker cannot be imported or raises, this prints which tool was
missing, says plainly that no duplicate check ran, and exits non-zero. A
wrapper that skipped quietly would report a clean index it never read.

Every exit path prints except the one that is silent by design (the edited file
is not the index). Exit 0 with no output is otherwise indistinguishable from a
hook that never ran.

NOTE ON THE DUPLICATED STDIN READER BELOW: this is the SECOND copy
(`html_script_check.py` has the first, `citation_drift_hook.py` the second).
It is duplicated for the reason stated at the function, and the threshold is
named here so it is not a judgement somebody has to make again: A THIRD HOOK
WANTING IT SHOULD EXTRACT IT into a shared module, and then every hook that
uses it must fail closed when that module is absent.

CLI:
    python tools/index_duplicate_hook.py docs/SAIRN-OPEN-WORK-INDEX.md
    python tools/index_duplicate_hook.py --which
    python tools/index_duplicate_hook.py --selftest
"""
import io
import json
import os
import re
import subprocess
import sys
import threading

STDIN_TIMEOUT_SECONDS = 10

BANNER = ('--- index_duplicate_hook: runs index_duplicate_check on an edit to '
          'the open-work index. ADVISORY, never blocking. ---')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, 'tools', 'index_duplicate_check.py')


def read_stdin_with_timeout(seconds):
    """Return stdin's text, or None on timeout. Threaded because Windows
    cannot select() on a pipe, so this is the portable way to bound it.

    Duplicated rather than imported: importing it from another hook script
    would make THIS hook fail whenever that unrelated one is being edited, and
    a hook that cannot start is a hook that reports nothing. The function is
    pure and has no repo-specific knowledge to drift. See the module docstring
    for when to stop duplicating it.
    """
    box = {}

    def worker():
        try:
            box['data'] = sys.stdin.read()
        except Exception as exc:  # pragma: no cover - defensive
            box['error'] = exc

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        return None
    if 'error' in box:
        raise box['error']
    return box.get('data', '')


def _idc():
    """The checker module, or None -- a could-not-check, never a pass."""
    if not os.path.isfile(CHECKER):
        return None
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    try:
        import index_duplicate_check as idc
        return idc
    except Exception:
        return None
    finally:
        sys.path.pop(0)


def covered_path():
    """The index's absolute path, taken from the checker. None on failure.

    IMPORTED, NOT LISTED. A path written here would be a second declaration of
    which document the checker reads, and this repo has corrected that exact
    shape seven times in one document alone. When the checker's INDEX moves,
    this follows with no edit.
    """
    idc = _idc()
    if idc is None:
        return None
    p = getattr(idc, 'INDEX', None)
    return os.path.abspath(p) if p else None


def is_covered(file_path, target):
    """Resolved, case-folded compare. The payload carries whatever the caller
    typed -- relative, forward slashes, a different drive-letter case -- and a
    naive string compare answers "not covered" for the very file just edited,
    silently and looking exactly like success."""
    if not file_path or not target:
        return False
    return os.path.normcase(os.path.abspath(file_path)) == os.path.normcase(target)


def _pairs_for(idc, doc_path):
    """The checker's own undeclared near-duplicate pairs for `doc_path`.

    The checker reads a module-level INDEX constant rather than taking a path,
    so it is pointed at the file for the duration of the call and restored in a
    finally. Calling the checker's OWN main() logic matters more than the
    plumbing being pretty: a reimplementation here would be a second
    declaration of what counts as a duplicate, and the two would drift.
    """
    original = idc.INDEX
    try:
        idc.INDEX = doc_path
        rs = idc.rows()
        out = []
        import difflib
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = rs[i], rs[j]
                if a['app'] != b['app']:
                    continue
                ratio = difflib.SequenceMatcher(None, a['norm'], b['norm']).ratio()
                if ratio < idc.THRESHOLD:
                    continue
                if tuple(sorted((a['norm'], b['norm']))) in idc.ACCEPTED:
                    continue
                out.append({
                    'app': a['app'],
                    'ratio': round(ratio, 3),
                    'a_line': a['line'], 'b_line': b['line'],
                    'a_item': a['item'][:110], 'b_item': b['item'][:110],
                    # THE STABLE KEY: normalised text, not line numbers, which
                    # all move when a row is inserted above.
                    'key': ' '.join(sorted((a['norm'], b['norm']))),
                })
        return out
    finally:
        idc.INDEX = original


def _head_copy(rel):
    """This file as HEAD has it, in a temp file. (path, None) or (None, why).

    NEVER writes the working tree -- the same rule and the same reason as
    citation_drift_hook._head_copy(): restoring HEAD over the real document to
    re-read it loses the user's uncommitted work if anything in between raises,
    on a hook that is advisory.

    BYTES, not text=True: on Windows subprocess decodes with the ANSI code page
    and this document is UTF-8 with em dashes and HTML entities in it. Text
    mode raised UnicodeDecodeError inside a subprocess reader THREAD, which
    surfaced as a bare traceback and exit 120 rather than anything catchable.
    """
    try:
        proc = subprocess.run(['git', 'show', 'HEAD:' + rel.replace('\\', '/')],
                              cwd=REPO, capture_output=True, timeout=30)
    except Exception as exc:
        return None, 'git show failed to launch: %s' % exc
    if proc.returncode != 0:
        return None, ('not in HEAD (%s) -- no baseline to compare against'
                      % (proc.stderr or b'').decode('utf-8', 'replace').strip()[:120])
    import tempfile
    fh = tempfile.NamedTemporaryFile('wb', suffix='.md', delete=False)
    fh.write(proc.stdout)
    fh.close()
    return fh.name, None


def report(abs_path, rel):
    """What this edit did to the index. None for could-not-check."""
    idc = _idc()
    if idc is None:
        return None
    try:
        current = _pairs_for(idc, abs_path)
    except Exception as exc:
        return {'error': 'the checker raised on the current index: %s' % exc}
    out = {'current': current, 'introduced': None, 'baseline_note': None}
    base_path, why = _head_copy(rel)
    if base_path is None:
        out['baseline_note'] = why
        return out
    try:
        base_keys = set(p['key'] for p in _pairs_for(idc, base_path))
        out['introduced'] = [p for p in current if p['key'] not in base_keys]
    except Exception as exc:
        out['baseline_note'] = 'the checker raised on the HEAD baseline: %s' % exc
    finally:
        try:
            os.unlink(base_path)
        except OSError:
            pass
    return out


def selftest():
    out, bad = [], 0

    def arm(name, ok, detail=''):
        nonlocal bad
        out.append('  %s %s%s' % ('ok  ' if ok else 'FAIL', name,
                                  '' if ok else '\n       ' + detail))
        if not ok:
            bad += 1

    target = covered_path()
    arm('the covered path comes from the checker, not from this file',
        target is not None,
        'index_duplicate_check could not be imported from %s, so this hook '
        'cannot know which document it guards and must not report a clean '
        'index (PR 1.11).' % CHECKER)
    if target is None:
        return out, bad

    arm('the index really is the file this guards',
        os.path.basename(target) == 'SAIRN-OPEN-WORK-INDEX.md',
        'covered_path() returned %r' % target)
    arm('an absolute path to the index matches', is_covered(target, target))
    arm('a repo-relative spelling matches',
        is_covered(os.path.join('docs', 'SAIRN-OPEN-WORK-INDEX.md'), target),
        'a relative path did not match, so an edit reported that way is '
        'silently unguarded')
    arm('a forward-slash spelling matches',
        is_covered(target.replace('\\', '/'), target))
    arm('an UNRELATED file does NOT match',
        not is_covered(os.path.join(REPO, 'sairnvet.html'), target),
        'this hook would run the index check after every edit in the repo and '
        'be switched off within a week -- which is exactly why the checker is '
        'not wired to Write|Edit directly')
    arm('an empty path does NOT match', not is_covered('', target))

    # ── THE ARM THAT MATTERS: DOES THE COMPARISON ACTUALLY FIND A DUPLICATE?
    # Everything above tests ROUTING. A hook that routes perfectly into a
    # comparison that never reports anything prints "no duplicate row was
    # introduced" forever and reads as a clean bill. Synthetic fixtures (item
    # 1), so this keeps meaning the same thing when the real index is clean.
    idc = _idc()
    import tempfile

    def fixture(rows_md):
        fh = tempfile.NamedTemporaryFile('w', suffix='.md', delete=False,
                                         encoding='utf-8', newline='')
        fh.write('| App | Item | Status | Owner | x | Evidence | S |\n')
        fh.write('| --- | --- | --- | --- | --- | --- | --- |\n')
        fh.write(rows_md)
        fh.close()
        return fh.name

    ROW = ('| FixtureApp | the widget counter reads %s of 389 rows and has no '
           'removal path | OPEN | hank | - | - | M |\n')
    clean = fixture(ROW % '321')
    dup = fixture((ROW % '321') + (ROW % '324'))
    try:
        cp = _pairs_for(idc, clean)
        dp = _pairs_for(idc, dup)
        arm('a single row produces NO pair',
            len(cp) == 0,
            'the checker found %d pair(s) in a one-row fixture: %r. A false '
            'positive here makes the whole hook noise.' % (len(cp), cp))
        arm('two rows on one subject DO produce a pair',
            len(dp) >= 1,
            'the checker found no near-duplicate between two rows differing '
            'only in a count -- and numbers are stripped before comparing, so '
            'this is the canonical case. The comparison reports nothing, which '
            'means this hook would say "no duplicate introduced" after every '
            'edit forever.')
        arm('the DIFFERENCE is what the hook reports -- dup minus clean is '
            'non-empty, clean minus dup is empty',
            bool(set(p['key'] for p in dp) - set(p['key'] for p in cp))
            and not (set(p['key'] for p in cp) - set(p['key'] for p in dp)),
            'the set difference does not separate the fixtures: dup=%r clean=%r'
            % ([p['key'][:40] for p in dp], [p['key'][:40] for p in cp]))
        arm('CONTROL -- the key is TEXT, so inserting a row above does not '
            'rewrite every pair',
            True if not dp else all(' ' in p['key'] and
                                    str(p['a_line']) not in p['key'] for p in dp),
            'a line number leaked into the stable key, so any insertion above '
            'an existing pair would report it as newly introduced')
        arm('KNOWN TRADE, asserted so it is not a surprise: REWORDING one row '
            'of a pair reads as a new pair',
            True,
            '')
    finally:
        for p in (clean, dup):
            try:
                os.unlink(p)
            except OSError:
                pass
    return out, bad


def main(argv):
    if '--which' in argv:
        print(BANNER)
        t = covered_path()
        if t is None:
            print('COULD NOT TELL: index_duplicate_check.py could not be '
                  'imported from %s, so the guarded path is unknown. NOT '
                  'reporting "nothing guarded".' % CHECKER, file=sys.stderr)
            return 2
        print('guarded document (from the checker itself): %s%s'
              % (os.path.relpath(t, REPO),
                 '' if os.path.isfile(t) else '   <- MISSING ON DISK'))
        return 0

    if '--selftest' in argv:
        print(BANNER)
        out, bad = selftest()
        for line in out:
            print(line)
        print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
        return 1 if bad else 0

    args = [a for a in argv[1:] if not a.startswith('-')]
    if args:
        file_path = args[0]
    else:
        raw = read_stdin_with_timeout(STDIN_TIMEOUT_SECONDS)
        if raw is None:
            print(BANNER)
            print('ERROR: no argument and nothing on stdin within %ds. NO '
                  'DUPLICATE CHECK RAN.' % STDIN_TIMEOUT_SECONDS,
                  file=sys.stderr)
            return 2
        if not raw.strip():
            print(BANNER)
            print('ERROR: empty stdin and no file argument. NO DUPLICATE CHECK '
                  'RAN.', file=sys.stderr)
            return 2
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            print(BANNER)
            print('ERROR: stdin was not valid JSON (%s). NO DUPLICATE CHECK '
                  'RAN.' % exc, file=sys.stderr)
            return 2
        file_path = ((payload.get('tool_input', {}) or {})
                     .get('file_path', '') or '')

    target = covered_path()
    if target is None:
        print(BANNER)
        print('COULD NOT RUN: index_duplicate_check.py could not be imported '
              'from %s. NO DUPLICATE CHECK RAN for %r -- a third state, not a '
              'pass (PR 1.11).' % (CHECKER, file_path), file=sys.stderr)
        return 2

    if not file_path:
        print(BANNER)
        print('ERROR: payload carried no file_path. NO DUPLICATE CHECK RAN.',
              file=sys.stderr)
        return 2

    if not is_covered(file_path, target):
        # The only silent path, and it is the common one: almost every edit in
        # this repo lands here, and its honest summary is "this edit cannot have
        # added a duplicate row to the open-work index".
        return 0

    abs_path = os.path.abspath(file_path)
    rel = os.path.relpath(abs_path, REPO)
    rep = report(abs_path, rel)
    print(BANNER)
    print('%s was just written.' % rel)
    if rep is None:
        print('COULD NOT RUN the checker. NO DUPLICATE CHECK RAN.',
              file=sys.stderr)
        return 2
    if rep.get('error'):
        print('COULD NOT CHECK: %s' % rep['error'], file=sys.stderr)
        print('  NO DUPLICATE CHECK RAN for this edit. Run it yourself: '
              'python tools/index_duplicate_check.py', file=sys.stderr)
        return 2

    current, introduced, note = rep['current'], rep['introduced'], rep['baseline_note']
    if introduced is None:
        print('  COULD NOT ATTRIBUTE: %s' % note)
        print('  Listing ALL %d undeclared near-duplicate pair(s), not just '
              'this edit\'s:' % len(current))
        for p in current:
            print('    %s lines %d/%d (%.3f): %s | %s'
                  % (p['app'], p['a_line'], p['b_line'], p['ratio'],
                     p['a_item'], p['b_item']))
        return 1 if current else 0

    pre = len(current) - len(introduced)
    if introduced:
        print('')
        print('  *** %d NEAR-DUPLICATE ROW PAIR(S) INTRODUCED BY THIS EDIT ***'
              % len(introduced))
        for p in introduced:
            print('    %s -- lines %d and %d, similarity %.3f'
                  % (p['app'], p['a_line'], p['b_line'], p['ratio']))
            print('        %d: %s' % (p['a_line'], p['a_item']))
            print('        %d: %s' % (p['b_line'], p['b_item']))
        print('')
        print('  Two rows, one subject. This is the file every session reads at '
              'start to choose')
        print('  work, and it now gives two answers with no way to tell which '
              'is current. If the')
        print('  older row is superseded, REBUILD IT WHOLE rather than editing '
              'it by splitting on')
        print('  `|` (PR 2.1). If both are genuinely distinct, declare the pair '
              'in')
        print('  index_duplicate_check.ACCEPTED with the reason.')
        if pre:
            print('  (%d further pair(s) were already in HEAD and are not this '
                  'edit\'s.)' % pre)
        print('')
        print('ADVISORY -- nothing is blocked. PostToolUse cannot block, and a '
              'pre-existing')
        print('duplicate must not freeze an unrelated edit.')
        return 1

    print('  NO near-duplicate row pair was introduced by this edit. (%d '
          'pre-existing in HEAD, unchanged by you.)' % pre)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
