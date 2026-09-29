"""
PostToolUse hook for Write|Edit, and a CLI. Runs the citation-drift checker
when the file just written is one the checker actually reads.

── THE GAP THIS CLOSES (2026-09-26) ────────────────────────────────────────
`tools/register_freshness_check.py` landed 2026-09-24 and is registered in
`report_only_checks.py`. That registry is wired to **PostToolUse on Bash**. So
the checker ran after a shell command and never after an edit -- and the two
documents it checks, `docs/CRITICALITY-TIERS.md` and `docs/tier-a-reviews.json`,
are edited with Write/Edit, not with Bash. Editing a citation-bearing document
triggered nothing at all.

The freshness of a citation was therefore held by manual discipline, which is
the thing that had already failed once and produced the tool: all NINE line
citations on `sc_anesthesia_base_units` went 30-45 lines stale within a DAY and
were found only because a review obligation happened to send a reader there.
Then it failed again, in the narrowest possible way: `8d0430c3` records five
drifted cites introduced BY A CORRECTION TO THAT SAME DOCUMENT -- a bare `:N`
resolving against the last file named in the cell. The edit that breaks a
citation is almost always an edit to the document the citation lives in, which
is the one moment nothing was watching.

── WHICH FILES, DERIVED AND NOT LISTED ─────────────────────────────────────
The paths come from `register_freshness_check.TIERS` and `.REVIEWS`, imported.
A list here would be a second declaration of which documents bear citations,
and the Guardian App File Map in this repo has been corrected for exactly that
shape seven times. When the checker learns a third document, this hook covers
it with no edit.

── IT FAILS CLOSED, AND THAT IS THE POINT (PR 1.11) ────────────────────────
If the checker cannot be imported or cannot be run, this prints WHICH tool was
missing, says plainly that no citation was checked, and exits non-zero. A hook
wrapped in `if os.path.isfile(checker):` would not skip one check -- it would
report a pass it never performed, and nothing downstream could tell that from a
real one. "Could not run" is a third state and is never folded into "passed".

── THERE IS A FOURTH PATH AND IT DOES EXIT 0. THE PARAGRAPH ABOVE WAS
   UNQUALIFIED AND THAT WAS WRONG (corrected 2026-09-29, hank) ─────────────
The sentence above said could-not-run "exits non-zero" with no exception, and
there are FOUR could-not-* paths in main(), not three. Three return 2: the
checker could not be imported (twice), and the checker returned zero checkable
citations. THE FOURTH IS COULD-NOT-ATTRIBUTE, and it returns 0 when nothing in
the document is drifted. Driven rather than read: a no-baseline report with an
empty drift list exits 0; the same report with one drifted cite exits 1.

THAT EXIT CODE IS CORRECT AND IS NOT A FOLD, and the reason has to be written
down or somebody will "fix" it:

  1. WHAT COULD NOT RUN IS ATTRIBUTION, NOT THE DRIFT CHECK. The check ran and
     its counts are printed -- N OK, M UNVERIFIABLE, 0 DRIFTED, K FROZEN. What
     is unavailable is the HEAD baseline, which is needed only to SPLIT drift
     into "yours" and "already there".
  2. WITH ZERO DRIFT THERE IS NOTHING TO SPLIT. "No citation in this document is
     drifted" entails "this edit drifted none". The hook's question is answered
     -- derived rather than measured directly, which is weaker PROVENANCE and
     the same ANSWER.
  3. EXITING 2 HERE WOULD FIRE ON A PROVABLY CLEAN DOCUMENT in every ordinary
     condition where `git show HEAD:<file>` has nothing to give -- a fresh
     clone, a detached head, a document not yet in HEAD. A could-not-run state
     that fires on clean input under normal conditions is a hook somebody turns
     off, which is the same argument this file already makes for being advisory
     per item rather than blocking.

WHAT WAS ACTUALLY WRONG ON THAT PATH, and it is fixed: it printed the
could-not-attribute note, then the line "Listing ALL drift in the document", and
then nothing at all, and exited 0. A COULD-NOT banner followed by an empty list
and no verdict is this file's own documented defect one step along -- "exit 0
with no output is indistinguishable from a hook that never ran". The verdict is
now stated explicitly, together with the fact that its basis is weaker than a
before/after comparison. THE EXIT CODE DID NOT CHANGE; THE SILENCE DID.

── ADVISORY, NOT BLOCKING, AND NOT BY ACCIDENT ─────────────────────────────
PostToolUse cannot block a tool call at all, so the only honest options are
"say something" and "say nothing". But the underlying tool is also advisory
**per item** by an explicit earlier decision: a register with one stale cell
must not freeze every unrelated edit. This hook keeps that. It reports the
drift it found, names the file that triggered it, and returns 1 so the exit
code carries the finding even though nothing is refused.

Every exit path prints. Exit 0 with no output is indistinguishable from a hook
that never ran, which is the defect `html_script_check.py` was rewritten to
stop making and is written up in its own docstring.

CLI:
    python tools/citation_drift_hook.py docs/CRITICALITY-TIERS.md
    python tools/citation_drift_hook.py --which     # print the covered paths
    python tools/citation_drift_hook.py --selftest  # prove the arms can fail
"""
import sys, os, json, threading, subprocess

STDIN_TIMEOUT_SECONDS = 10
CHECKER_TIMEOUT_SECONDS = 180

BANNER = ('--- citation_drift_hook: runs register_freshness_check on an edit to '
          'a citation-bearing document. ADVISORY, never blocking. ---')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, 'tools', 'register_freshness_check.py')


def read_stdin_with_timeout(seconds):
    """Return stdin's text, or None on timeout. Threaded because Windows
    cannot select() on a pipe, so this is the portable way to bound it.

    DUPLICATED FROM html_script_check.py DELIBERATELY, and the reason is worth
    the four lines it costs: importing it would make this hook fail when that
    unrelated hook is edited, and a hook that cannot start is a hook that
    reports nothing. The function is pure, twenty lines, and has no
    repo-specific knowledge to drift.
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


def covered_paths():
    """The citation-bearing documents, taken from the checker itself.

    Returns a list of absolute paths, or None if the checker could not be
    read -- which the caller MUST treat as could-not-check. Returning an empty
    list on failure would make "the checker is gone" look exactly like "this
    edit touched nothing citation-bearing", and every later edit would be
    silently unguarded.
    """
    if not os.path.isfile(CHECKER):
        return None
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    try:
        import register_freshness_check as rfc
    except Exception:
        return None
    finally:
        sys.path.pop(0)
    paths = []
    for attr in ('TIERS', 'REVIEWS'):
        p = getattr(rfc, attr, None)
        if p:
            paths.append(os.path.abspath(p))
    return paths or None


def resolve_file_path(argv):
    """CLI mode wins. Returns (path, mode) or exits non-zero, loudly."""
    args = [a for a in argv[1:] if not a.startswith('-')]
    if args:
        return args[0], 'cli'

    raw = read_stdin_with_timeout(STDIN_TIMEOUT_SECONDS)
    if raw is None:
        print(BANNER)
        print('ERROR: no argument given and nothing arrived on stdin within '
              '%ds. This script takes a hook payload on stdin OR a file path '
              'as argv[1]. NO CITATION WAS CHECKED.' % STDIN_TIMEOUT_SECONDS,
              file=sys.stderr)
        sys.exit(2)
    if not raw.strip():
        print(BANNER)
        print('ERROR: empty stdin and no file argument. NO CITATION WAS '
              'CHECKED.', file=sys.stderr)
        sys.exit(2)
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        print(BANNER)
        print('ERROR: stdin was not valid JSON (%s). NO CITATION WAS CHECKED.'
              % exc, file=sys.stderr)
        sys.exit(2)
    tool_input = payload.get('tool_input', {}) or {}
    return (tool_input.get('file_path', '') or ''), 'hook'


def is_covered(file_path, paths):
    """True when `file_path` is one of the citation-bearing documents.

    Compared as resolved absolute paths with case folded, because the hook
    payload carries whatever the caller typed -- a relative path, a different
    drive-letter case, forward or back slashes -- and a string compare on those
    answers "not covered" for the very file that was just edited. That failure
    is silent and looks exactly like success.
    """
    target = os.path.normcase(os.path.abspath(file_path))
    return any(os.path.normcase(p) == target for p in paths)


def _rfc():
    """The checker module, or None. Same could-not-check contract as above."""
    if not os.path.isfile(CHECKER):
        return None
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    try:
        import register_freshness_check as rfc
        return rfc
    except Exception:
        return None
    finally:
        sys.path.pop(0)


def _judge(rfc, abs_path, doc_path):
    """Run the checker's OWN per-document function against `doc_path`.

    `abs_path` selects WHICH function (tiers or reviews); `doc_path` is the file
    actually read, so a baseline copy can be judged with identical logic. The
    alternative -- reimplementing the comparison here -- is the second-copy
    defect this repo has corrected seven times in one document alone.
    """
    fn = (rfc.check_tiers
          if os.path.normcase(abs_path) == os.path.normcase(os.path.abspath(rfc.TIERS))
          else rfc.check_reviews)
    return fn(doc_path, {}, {})


def _head_copy(rel):
    """This file as HEAD has it, in a temp file. (path, None) or (None, why).

    NEVER writes the working tree. An earlier sketch of this restored HEAD over
    the real document, re-ran, and restored the edit -- which loses the user's
    work outright if anything in between raises, on a hook that is supposed to
    be advisory.
    """
    # BYTES, NOT text=True. On Windows subprocess decodes with the ANSI code
    # page (cp1252 here) and both of these documents are UTF-8 with em dashes
    # and arrows in them -- text mode raised UnicodeDecodeError inside a reader
    # THREAD, which surfaced as a bare traceback and exit 120 rather than as
    # anything this function could catch. Decoding explicitly also keeps the
    # baseline byte-faithful: `errors='replace'` would corrupt the copy and
    # invent drift that is really a mangled character.
    try:
        proc = subprocess.run(['git', 'show', 'HEAD:' + rel.replace('\\', '/')],
                              cwd=REPO, capture_output=True, timeout=30)
    except Exception as exc:
        return None, 'git show failed to launch: %s' % exc
    if proc.returncode != 0:
        return None, ('not in HEAD (%s) -- a newly added document has no '
                      'baseline to compare against'
                      % (proc.stderr or b'').decode('utf-8', 'replace').strip()[:120])
    import tempfile
    fh = tempfile.NamedTemporaryFile('wb', suffix=os.path.splitext(rel)[1],
                                     delete=False)
    fh.write(proc.stdout)
    fh.close()
    return fh.name, None


def drift_report(abs_path, rel):
    """What this edit did to the citations in one document.

    Returns a dict, or None for could-not-check. `introduced` is the set
    difference current-minus-baseline: drift that exists now and did not exist
    in the committed version of this same document.

    ── WHY THE DIFFERENCE AND NOT THE TOTAL ────────────────────────────────
    docs/CRITICALITY-TIERS.md carries 43 drifted citations today, none of them
    from the edit in front of you. A hook that prints all 43 after every save
    is noise, and the honest description of noise on this platform is "a check
    somebody turns off" -- which is worse than the gap it closed. The push
    gate's generated-document check already made exactly this decision in its
    own words: "This check refuses only what THIS push broke. A document left
    stale by somebody else is reported above and does not block you."
    """
    rfc = _rfc()
    if rfc is None:
        return None
    try:
        current = _judge(rfc, abs_path, abs_path)
    except Exception as exc:
        return {'error': 'the checker raised on the current document: %s' % exc}

    cur_drift = set(d for s, d in current if s == 'DRIFTED')
    out = {
        'ok': sum(1 for s, _ in current if s == 'OK'),
        'unverifiable': [d for s, d in current if s == 'UNVERIFIABLE'],
        'frozen': [d for s, d in current if s == 'FROZEN'],
        'drifted': sorted(cur_drift),
        'introduced': None,
        'baseline_note': None,
    }
    base_path, why = _head_copy(rel)
    if base_path is None:
        # NAMED, not swallowed. Without a baseline this hook cannot attribute
        # drift to this edit, and saying nothing would let a reader assume the
        # list below is theirs -- or that an empty list means they broke
        # nothing, when nothing was compared.
        out['baseline_note'] = why
        return out
    try:
        base = _judge(rfc, abs_path, base_path)
        out['introduced'] = sorted(cur_drift - set(d for s, d in base if s == 'DRIFTED'))
    except Exception as exc:
        out['baseline_note'] = 'the checker raised on the HEAD baseline: %s' % exc
    finally:
        try:
            os.unlink(base_path)
        except OSError:
            pass
    return out


def selftest():
    """Prove the arms can fail, on fixtures, before any of this is trusted.

    Item 1 of the cross-domain disciplines: lock the criteria against synthetic
    fixtures rather than against whatever the real documents happen to say
    today. A hook whose path-matching is wrong reports "nothing to check" on
    every edit forever and looks identical to a clean repo.
    """
    out, bad = [], 0

    def arm(name, ok, detail=''):
        nonlocal bad
        out.append('  %s %s%s' % ('ok  ' if ok else 'FAIL', name,
                                  '' if ok else '\n       ' + detail))
        if not ok:
            bad += 1

    tiers = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
    reviews = os.path.join(REPO, 'docs', 'tier-a-reviews.json')
    paths = [os.path.abspath(tiers), os.path.abspath(reviews)]

    arm('the covered paths come from the checker, not from this file',
        covered_paths() is not None,
        'covered_paths() returned None -- register_freshness_check could not be '
        'imported from %s. This hook cannot know which documents bear '
        'citations and must not claim a clean result.' % CHECKER)
    cp = covered_paths() or []
    arm('both known citation-bearing documents are covered',
        all(any(os.path.normcase(p) == os.path.normcase(q) for q in cp)
            for p in paths),
        'covered_paths() returned %r, which does not include both %s and %s'
        % (cp, tiers, reviews))

    arm('an absolute path to a covered document matches',
        is_covered(tiers, paths), 'is_covered said no to %s' % tiers)
    # THE THREE SPELLINGS THAT REALLY ARRIVE. Each of these was a plausible
    # silent miss: a relative path from the repo root, a forward-slash path on
    # Windows, and a lower-cased drive letter.
    arm('a repo-relative spelling of the same file matches',
        is_covered(os.path.join('docs', 'CRITICALITY-TIERS.md'), paths),
        'a relative path did not match, so an edit reported that way is '
        'silently unguarded')
    arm('a forward-slash spelling matches on this platform',
        is_covered(tiers.replace('\\', '/'), paths),
        'forward slashes did not match')
    arm('an UNRELATED file does NOT match',
        not is_covered(os.path.join(REPO, 'sairnvet.html'), paths),
        'is_covered matched a file that bears no register citations, so this '
        'hook would run the checker on every edit in the repo and be switched '
        'off within a day')
    arm('an empty path does NOT match',
        not is_covered('', paths),
        'an empty file_path matched a covered document')

    # THE CONTROL. Without it every arm above is satisfied by an is_covered()
    # that returns True for everything, or by a `paths` list that is empty.
    arm('CONTROL -- the fixture list is non-empty and is_covered discriminates',
        len(paths) == 2 and is_covered(tiers, paths)
        and not is_covered(os.path.join(REPO, 'README.md'), paths),
        'is_covered does not discriminate between a covered and an uncovered '
        'file, so the arms above are checking one answer twice')

    # ── THE ARM THAT MATTERS: DOES IT ACTUALLY CATCH A DRIFTED EDIT? ────────
    # Every arm above tests the ROUTING -- does the right file reach the
    # checker. None of them tests the ANSWER. A hook that routes perfectly to a
    # comparison that never reports anything is the exact shape of a check that
    # passes without testing: it would print "NO citation was drifted by this
    # edit" after every edit, forever, and read as a clean bill.
    #
    # SYNTHETIC FIXTURES, NOT THE REAL DOCUMENT (item 1). The criteria are
    # locked against two tiny tier tables built here -- one citing a line that
    # is right, one citing a line that is wrong -- so this arm keeps meaning
    # the same thing when the real register's 43 drifted cells are fixed.
    rfc = _rfc()
    if rfc is None:
        arm('the drift comparison catches a drifted cite', False,
            'register_freshness_check could not be imported, so the comparison '
            'itself was NOT exercised. This is a could-not-check and is being '
            'reported as an arm FAILURE rather than skipped (PR 1.11).')
        return out, bad

    import tempfile
    me = 'tools/register_freshness_check.py'
    # ── THE IDENTIFIER IS CHOSEN AT RUNTIME, AND THE FIRST VERSION OF THIS ARM
    #    IS WHY. It cited `covered_paths` in this file at a line 200 away --
    #    and the checker correctly said NOT DRIFTED, because `covered_paths`
    #    appears a dozen times in this file and the window 200 lines later
    #    contained one of them. The fixture was wrong, not the checker, and an
    #    arm that had merely been asserted rather than run would have shipped
    #    reading "the comparison does not work".
    #
    # So: find a name that occurs on EXACTLY ONE line, far enough from both
    # ends to have a genuinely distant wrong line. Derived, so it survives the
    # file being edited.
    lines = io_read_lines(os.path.join(REPO, me))
    ident, good_line = None, None
    import re as _re
    counts = {}
    for line in lines:
        for w in _re.findall(r'\b([A-Za-z_][A-Za-z0-9_]{5,40})\b', line):
            counts[w] = counts.get(w, 0) + 1
    for n, line in enumerate(lines, 1):
        if n < 120 or n > len(lines) - 120:
            continue
        for w in _re.findall(r'\b([A-Za-z_][A-Za-z0-9_]{5,40})\b', line):
            if counts.get(w) == 1:
                ident, good_line = w, n
                break
        if ident:
            break

    def fixture(cited_line):
        row = ('| `fx_probe` | A | B | C | D | E | `%s` at `%s:%d` |\n'
               % (ident, me, cited_line))
        fh = tempfile.NamedTemporaryFile('w', suffix='.md', delete=False,
                                         encoding='utf-8', newline='')
        fh.write('| `id` | a | b | c | d | e | Evidence |\n')
        fh.write(row)
        fh.close()
        return fh.name

    arm('the fixture found a name occurring EXACTLY ONCE in %s' % me,
        ident is not None,
        'no identifier in %s occurs on exactly one line away from both ends, so '
        'both arms below would be judging an ambiguous citation and a '
        'NOT-DRIFTED verdict would mean nothing.' % me)

    if ident is not None:
        # A cite well outside the +/-8-line window, and inside the file.
        bad_line = good_line + 100 if good_line + 100 <= len(lines) else good_line - 100
        gp, bp = fixture(good_line), fixture(bad_line)
        try:
            gres = _judge(rfc, os.path.abspath(rfc.TIERS), gp)
            bres = _judge(rfc, os.path.abspath(rfc.TIERS), bp)
            gd = set(d for s, d in gres if s == 'DRIFTED')
            bd = set(d for s, d in bres if s == 'DRIFTED')
            arm('a CORRECT cite is judged clean, not drifted',
                not gd,
                'the checker called a correct cite (%s:%d, where covered_paths '
                'really is) DRIFTED: %r. Every comparison below inherits this, '
                'so a false positive here makes the whole hook noise.'
                % (me, good_line, sorted(gd)))
            arm('a WRONG cite is judged drifted',
                bool(bd),
                'the checker did NOT flag a cite to %s:%d, %d lines away from '
                'the identifier it names. The comparison reports nothing, so '
                'this hook would say "no citation was drifted by this edit" '
                'after every edit forever.' % (me, bad_line,
                                               abs(bad_line - good_line)))
            arm('the DIFFERENCE is what the hook reports -- wrong minus right '
                'is non-empty, right minus wrong is empty',
                bool(bd - gd) and not (gd - bd),
                'the set difference the hook uses to attribute drift to an edit '
                'does not separate these two fixtures: wrong-minus-right=%r, '
                'right-minus-wrong=%r' % (sorted(bd - gd), sorted(gd - bd)))
        finally:
            for p in (gp, bp):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    # ── THE FOURTH COULD-NOT PATH, DRIVEN IN BOTH SUB-CASES ──────────────
    # Added 2026-09-29 (hank). Every arm above tests ROUTING or the COMPARISON;
    # none of them ever reached main()'s no-baseline branch, which is how its
    # silence survived. These arms call main() with drift_report stubbed to the
    # two shapes that branch can see, and assert on the EXIT CODE and on the
    # PRESENCE of a verdict -- never on the wording of one.
    #
    # THE KNOWN-BAD DIRECTION IS BUILT IN: the empty-drift arm fails if the
    # output carries no verdict line, which is exactly what this file printed
    # before the fix. Run these arms against the previous revision and two fail.
    import io as _io2
    _saved = {'drift_report': globals().get('drift_report'),
              'covered_paths': globals().get('covered_paths'),
              'is_covered': globals().get('is_covered')}
    _saved_argv = sys.argv
    _real_out, _real_err = sys.stdout, sys.stderr

    def _drive(report):
        """Run main() over a covered path with this report, capturing output."""
        globals()['drift_report'] = lambda a, r: report
        globals()['covered_paths'] = lambda: [os.path.abspath(
            os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md'))]
        globals()['is_covered'] = lambda pth, paths: True
        sys.argv = ['citation_drift_hook.py',
                    os.path.join('docs', 'CRITICALITY-TIERS.md')]
        buf = _io2.StringIO()
        sys.stdout = buf
        sys.stderr = buf
        try:
            rc = main()
        finally:
            sys.stdout, sys.stderr = _real_out, _real_err
        return rc, buf.getvalue()

    try:
        clean = {'ok': 12, 'unverifiable': ['u'], 'frozen': [], 'drifted': [],
                 'introduced': None,
                 'baseline_note': 'no HEAD copy of this file in this clone'}
        rc, txt = _drive(clean)
        arm('COULD-NOT-ATTRIBUTE with an EMPTY drift list exits 0', rc == 0,
            'exit was %r. If this is now 2, read the fourth-path block in this '
            'file\'s header: ATTRIBUTION is what could not run, and a zero-drift '
            'document entails zero drift from this edit. Exiting 2 here fires on '
            'a provably clean document in a fresh clone.' % rc)
        arm('...and it STATES A VERDICT instead of printing an empty list',
            'NO CITATION IN THIS DOCUMENT IS DRIFTED' in txt,
            'the no-baseline path printed no verdict. THIS IS THE DEFECT THIS '
            'ARM EXISTS FOR: a COULD-NOT banner, then nothing, then exit 0 -- '
            'indistinguishable from a hook that never ran. Output was:\n' + txt)
        arm('...and it names its basis as WEAKER rather than claiming a '
            'comparison it did not make',
            'whole-document answer' in txt and 'not a ' in txt,
            'the verdict is stated with no account of what it rests on, which is '
            'the over-claim in the other direction. Output was:\n' + txt)
        arm('...and it does NOT print the "Listing ALL drift" header with '
            'nothing under it',
            'Listing ALL drift' not in txt,
            'a listing header with no list beneath it is the shape being '
            'removed. Output was:\n' + txt)

        dirty = {'ok': 12, 'unverifiable': [], 'frozen': [],
                 'drifted': ['sd_x cites :99, real :140'],
                 'introduced': None,
                 'baseline_note': 'no HEAD copy of this file in this clone'}
        rc2, txt2 = _drive(dirty)
        arm('CONTROL -- the SAME path with drift present still exits 1 and lists '
            'it, so the arms above cannot be satisfied by a branch that always '
            'returns 0',
            rc2 == 1 and 'sd_x cites :99' in txt2 and 'Listing ALL drift' in txt2,
            'exit was %r and the drifted cite was %sin the output'
            % (rc2, '' if 'sd_x cites :99' in txt2 else 'NOT '))
        arm('CONTROL -- with drift present it does NOT claim the document is '
            'clean',
            'NO CITATION IN THIS DOCUMENT IS DRIFTED' not in txt2,
            'the clean verdict was printed over a drifted document, which is the '
            'same fold in the other direction')
    finally:
        for k, v in _saved.items():
            if v is not None:
                globals()[k] = v
        sys.argv = _saved_argv

    return out, bad


def io_read_lines(path):
    """Lines of a UTF-8 file, newline-stripped. Explicit encoding because this
    repo's documents carry em dashes and Windows would otherwise decode them
    with the ANSI code page."""
    import io as _io
    with _io.open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read().split('\n')


def main():
    if '--which' in sys.argv:
        print(BANNER)
        cp = covered_paths()
        if cp is None:
            print('COULD NOT TELL: register_freshness_check.py could not be '
                  'imported from %s, so the covered-document list is unknown. '
                  'NOT reporting an empty list -- that would read as "no '
                  'document bears citations".' % CHECKER, file=sys.stderr)
            return 2
        print('citation-bearing documents this hook watches (from the checker '
              'itself, not a list here):')
        for p in cp:
            print('  %s%s' % (os.path.relpath(p, REPO),
                              '' if os.path.isfile(p) else '   <- MISSING ON DISK'))
        return 0

    if '--selftest' in sys.argv:
        print(BANNER)
        out, bad = selftest()
        for line in out:
            print(line)
        print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
        return 1 if bad else 0

    file_path, mode = resolve_file_path(sys.argv)
    if not file_path:
        print(BANNER)
        print('ERROR: payload carried no file_path. NO CITATION WAS CHECKED.',
              file=sys.stderr)
        return 2

    paths = covered_paths()
    if paths is None:
        print(BANNER)
        print('COULD NOT RUN: register_freshness_check.py could not be imported '
              'from %s.' % CHECKER, file=sys.stderr)
        print('  NO CITATION WAS CHECKED for %s. This is a third state, not a '
              'pass: a hook that skipped quietly here would report a clean '
              'citation set it never looked at (PR 1.11).' % file_path,
              file=sys.stderr)
        return 2

    if not is_covered(file_path, paths):
        # SILENT BY DESIGN, AND THE ONLY SILENT PATH. Almost every edit in this
        # repo lands here; printing a line each time would make the hook noise
        # somebody turns off, and the honest summary of this path is genuinely
        # "this edit cannot have broken a register citation".
        return 0

    abs_path = os.path.abspath(file_path)
    rel = os.path.relpath(abs_path, REPO)
    rep = drift_report(abs_path, rel)
    print(BANNER)
    print('%s was just written, and it bears register citations.' % rel)

    if rep is None:
        print('COULD NOT RUN: register_freshness_check.py could not be imported '
              'from %s, so NO CITATION WAS CHECKED for this edit.' % CHECKER,
              file=sys.stderr)
        return 2
    if rep.get('error'):
        print('COULD NOT CHECK: %s' % rep['error'], file=sys.stderr)
        print('  NO CITATION WAS CHECKED for this edit. Run it yourself: '
              'python tools/register_freshness_check.py', file=sys.stderr)
        return 2

    okc, drifted = rep['ok'], rep['drifted']
    unver, frozen = rep['unverifiable'], rep['frozen']
    introduced, note = rep['introduced'], rep['baseline_note']

    if okc == 0 and not drifted and not unver:
        print('COULD NOT CHECK: the checker returned ZERO checkable citations '
              'for this document. Nothing was measured, and reporting this edit '
              'as clean would be indistinguishable from a real pass.',
              file=sys.stderr)
        return 2

    print('  in this document now: %d OK, %d UNVERIFIABLE (counted, never '
          'folded into pass), %d DRIFTED, %d FROZEN'
          % (okc, len(unver), len(drifted), len(frozen)))

    if introduced is None:
        # NO BASELINE. Everything drifted is printed, and the reason attribution
        # was impossible is printed WITH it -- an unattributed list presented as
        # "yours" is a false accusation, and presented as "pre-existing" is a
        # missed finding. Neither is available, so both are refused and the
        # reader is told which.
        print('  COULD NOT ATTRIBUTE: %s' % note)
        if not drifted:
            # THE VERDICT IS STATED RATHER THAN LEFT AS AN EMPTY LIST. This
            # path used to print the listing header below, list nothing, and
            # exit 0 -- so a reader saw a COULD-NOT banner followed by
            # silence and could not tell a clean document from a listing
            # that failed. The exit code was and is 0, and the header block
            # at the top of this file says why; what was missing was the
            # sentence.
            print('  NO CITATION IN THIS DOCUMENT IS DRIFTED, so nothing '
                  'needed attributing and this edit drifted none.')
            print('  AND THE BASIS IS WEAKER THAN USUAL, WHICH IS THE POINT '
                  'OF SAYING SO: this is the whole-document answer, not a '
                  'before/after comparison. It entails what you asked (no '
                  'drift at all means none from you), but it cannot tell '
                  'you about a cite this edit FIXED, and it would not '
                  'separate drift introduced and then removed inside one '
                  'write.')
            return 0
        print('  Listing ALL drift in the document, not just this edit\'s:')
        for d in drifted:
            print('    DRIFTED  %s' % d)
        return 1

    pre = len(drifted) - len(introduced)
    if introduced:
        print('')
        print('  *** %d CITATION(S) DRIFTED BY THIS EDIT ***' % len(introduced))
        for d in introduced:
            print('    %s' % d)
        print('')
        print('  (%d further drifted citation(s) in this document were already '
              'in HEAD and are NOT this edit\'s -- not listed, and not yours to '
              'fix right now.)' % pre)
        print('')
        print('ADVISORY, PER ITEM, and nothing is blocked: a register with one '
              'stale cell must not freeze every unrelated edit, which is the '
              'decision the checker was landed under. But the drift above did '
              'not exist in HEAD and does exist now, which makes this the one '
              'moment it is cheap to fix -- and the moment that, until this '
              'hook, nothing was watching. `8d0430c3` is five cites drifted by '
              'a CORRECTION to this same document.')
        print('  Mechanical repairs only, human-merged: '
              'python tools/register_freshness_propose.py')
        return 1

    print('  NO citation was drifted by this edit. (%d pre-existing in HEAD, '
          'unchanged by you.)' % pre)
    return 0


if __name__ == '__main__':
    sys.exit(main())
