"""Control pair for tools/metamorphic_check.py, plus the three defects it
found in ITSELF before it found anything in the fleet.

Run: python tests/run_metamorphic_probe.py

BOTH DIRECTIONS, on the real code path. Arms 1 and 2 call `measure()` itself
with fixture checkers rather than reimplementing the comparison -- a probe that
reimplements the thing it controls proves nothing about the thing that ships,
which is a defect already on this repo's own record (a harness that
reimplemented `sdLoad` and therefore tested its own copy).

  FIRES   a checker whose answer DOES depend on whitespace must be reported.
  SILENT  a checker that normalises first must not be.

ARMS 3-5 ARE NEGATIVE CONTROLS ON THIS TOOL'S OWN THREE SELF-INFLICTED BUGS,
each found by running it, each of which produced a CONFIDENTLY WRONG verdict
rather than an error. They are the reason this file is longer than a control
pair needs to be, and every one asserts BOTH the fix and that the pre-fix
behaviour genuinely failed -- a fix credited for something that already worked
is worth nothing.

  3. READING THE TARGET THROUGH UNIVERSAL NEWLINES made `identity` secretly the
     `crlf` transform, and the tool reported `key_collision_check.py` as
     violating IDENTITY on stonedesk.html. That is a NONDETERMINISM verdict --
     the most serious thing this tool can say -- and it was the harness's own
     line-ending flip.
  4. NORMALISING THE BARE BASENAME rewrote a checker's PROSE. `key_collision_
     check.py` prints an acknowledgement note containing the words
     "stonedesk.html"; the baseline's copy of that sentence was rewritten to
     <TARGET> and the transformed copy's was not, so two identical reports
     compared unequal. That is PR §1.2 -- text that merely DESCRIBES code --
     committed by the normaliser instead of by a checker.
  5. THE POSITION-FORMAT LIST KNEW ONLY `lines [..]`, and
     `literal_drift_check.py` emits `A line(s) [1802]`. Every position in its
     report survived normalisation, so `blank_lines` -- which shifts every line
     in the file by construction -- reported it as violated on all three
     targets. Three false findings from one missing `(s)`.

OFFLINE. Every arm runs against fixtures in a temp directory or calls a
function directly. Nothing touches the network and nothing writes to the repo.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import metamorphic_check as M                                  # noqa: E402
import checker_kit as K                                        # noqa: E402

CONTROLS_FOR = ['metamorphic_check.py']

FAILED = []


def check(label, got, want):
    ok = got == want
    print('  %s %-72s' % ('ok  ' if ok else 'FAIL', label))
    if not ok:
        print('       expected %r, got %r' % (want, got))
        FAILED.append(label)
    return ok


TARGET_HTML = ('<html>\r\n<body>\r\n'
               '<div>ordinary line</div>\r\n'
               '<div>PLANTED_DEFECT</div>\r\n'
               '</body>\r\n</html>\r\n')


def write_fixture_fleet(root):
    """A tools dir with the two fixture checkers, and a target that is CRLF."""
    tools = os.path.join(root, 'tools')
    os.makedirs(tools, exist_ok=True)
    io.open(os.path.join(tools, 'sensitive_fixture_check.py'), 'w',
            encoding='utf-8').write(M._FIXTURE_SENSITIVE)
    io.open(os.path.join(tools, 'robust_fixture_check.py'), 'w',
            encoding='utf-8').write(M._FIXTURE_ROBUST)
    io.open(os.path.join(root, 'fixture_app.html'), 'w',
            encoding='utf-8', newline='').write(TARGET_HTML)
    return tools


def main():
    print('metamorphic_check control pair + three self-inflicted-defect arms\n')
    tmp = tempfile.mkdtemp(prefix='metamorphic_probe_')
    try:
        tools = write_fixture_fleet(tmp)

        # ── 1. FIRES ─────────────────────────────────────────────────────────
        print('1. FIRES -- a whitespace-sensitive checker is REPORTED')
        rows, cnr = M.measure(['fixture_app.html'],
                              checkers=['sensitive_fixture_check.py'],
                              tools_dir=tools, target_root=tmp)
        viol = sorted({r['relation'] for r in rows if not r['holds']})
        check('the sensitive fixture violates at least one relation',
              len(viol) > 0, True)
        # ALL THREE, and this arm is the one that earned itself. With a CRLF
        # target and a fixture that measured LENGTH, `trailing_ws` HELD: six
        # CRLF->LF conversions remove six bytes and six appended spaces add six
        # back, so the fixture agreed with itself by arithmetic accident. The
        # lock never saw it because the lock's target is LF. The fixture prints
        # a HASH now; a summary of the bytes can coincide, a digest cannot.
        check('specifically the three SAME whitespace relations',
              viol, ['blank_lines', 'crlf', 'trailing_ws'])
        check('...and nothing could-not-run, so the count is a total not a floor',
              cnr, [])
        # The exit-code half of the contract, computed the way main() does.
        rc_fires = K.finish(['x' for r in rows if not r['holds']], cnr, quiet=True)
        check('a violation exits 1 (FINDING), not 0', rc_fires, K.EXIT_FINDING)

        # ── 2. SILENT ────────────────────────────────────────────────────────
        print('\n2. SILENT -- a checker that normalises first is NOT reported')
        rows_r, cnr_r = M.measure(['fixture_app.html'],
                                  checkers=['robust_fixture_check.py'],
                                  tools_dir=tools, target_root=tmp)
        check('the robust fixture violates nothing',
              [r['relation'] for r in rows_r if not r['holds']], [])
        check('and it really was compared, five relations x one target',
              len(rows_r), len(M.RELATIONS))
        rc_silent = K.finish([], cnr_r, quiet=True)
        check('clean exits 0', rc_silent, K.EXIT_CLEAN)

        # ── 3. THE READER ────────────────────────────────────────────────────
        print('\n3. read_raw preserves line endings -- identity must BE identity')
        src_path = os.path.join(tmp, 'fixture_app.html')
        raw = M.read_raw(src_path)
        check('read_raw keeps CRLF', '\r\n' in raw, True)
        check('...and a byte-exact round trip through the transform', raw, TARGET_HTML)
        # THE CONTROL: the ordinary reader must genuinely lose them, or this arm
        # is asserting a property nothing was ever at risk of breaking.
        check('CONTROL: checker_kit.read() (text mode) DESTROYS them',
              '\r\n' in K.read(src_path), False)
        check('CONTROL: so the old reader turned identity into the crlf transform',
              M.t_identity(K.read(src_path)) == raw, False)

        # ── 4. THE NORMALISER AND PROSE ──────────────────────────────────────
        print('\n4. normalise() must not rewrite prose that MENTIONS the target')
        prose = ('ACKNOWLEDGED: saveSDProfile() is quarantined in '
                 'stonedesk.html with its own defect documented.')
        a_path = os.path.join(REPO, 'stonedesk.html')
        b_path = os.path.join(tmp, 'identity', 'stonedesk.html')
        check('the same sentence normalises the same from both paths',
              M.normalise(prose, a_path), M.normalise(prose, b_path))
        check('...and the filename SURVIVES, because it is prose not a path',
              'stonedesk.html' in M.normalise(prose, a_path), True)

        def old_normalise(out, path):
            """The pre-fix normaliser: it also rewrote the bare basename."""
            out = out.replace(path, '<TARGET>')
            return out.replace(os.path.basename(path), '<TARGET>')

        check('CONTROL: the pre-fix normaliser made them differ',
              old_normalise(prose, a_path) == old_normalise(prose, b_path), True)
        check('CONTROL: ...by eating the filename out of the sentence',
              'stonedesk.html' in old_normalise(prose, a_path), False)

        # ── 5. POSITION FORMATS ──────────────────────────────────────────────
        print('\n5. every position format a checker in the fleet emits')
        for sample in ('     A line(s) [1802]',
                       '     B line(s) [3603, 3603]',
                       '       lines [11991, 19368]',
                       'reported at line 4471',
                       '  1802: something'):
            norm = M.normalise(sample, a_path)
            check('no bare line number survives: %r' % sample.strip()[:34],
                  bool(re.search(r'\d', norm)), False)
        old_lines = re.compile(r'lines \[[\d, ]*\]')
        check('CONTROL: the pre-fix pattern could not match `line(s) [..]`',
              bool(old_lines.search('A line(s) [1802]')), False)
        check('CONTROL: ...which is why literal_drift read as violated',
              bool(M._LINES_LIST.search('A line(s) [1802]')), True)

        # ── 6. THE BLIND LOCK REFUSES ────────────────────────────────────────
        print('\n6. an unfalsifiable relation FAILS the lock and refuses the run')
        real_relations = M.RELATIONS
        try:
            # A relation whose transform changes nothing can never be violated.
            M.RELATIONS = real_relations + [
                ('never_fires', lambda s: s, M.SAME, 'a no-op, on purpose')]
            ok, _rows, problems = M.blind_lock()
            check('the lock notices the sensitive fixture is not caught', ok, False)
            check('...and says which relation', any('never_fires' in p for p in problems), True)
        finally:
            M.RELATIONS = real_relations
        ok2, _r2, p2 = M.blind_lock()
        check('CONTROL: the real relation table locks clean', (ok2, p2), (True, []))

        # ── 7. THE EXIT-CODE CONTRACT, THIRD STATE ───────────────────────────
        print('\n7. could-not-run is a THIRD STATE, never folded into a pass')
        check('nothing found, nothing failed -> 0',
              K.finish([], [], quiet=True), K.EXIT_CLEAN)
        check('a finding -> 1', K.finish(['f'], [], quiet=True), K.EXIT_FINDING)
        check('could not run, nothing found -> 2 NOT 0',
              K.finish([], ['x'], quiet=True), K.EXIT_COULD_NOT_RUN)
        check('could not run AND a finding -> 2, because the count is a floor',
              K.finish(['f'], ['x'], quiet=True), K.EXIT_COULD_NOT_RUN)

        # ── 8. END TO END ────────────────────────────────────────────────────
        print('\n8. the real tool, end to end')
        p = subprocess.run([sys.executable,
                            os.path.join(REPO, 'tools', 'metamorphic_check.py'),
                            '--fixtures'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=REPO,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                    PYTHONUTF8='1'))
        check('--fixtures exits 0 when the criteria lock', p.returncode, 0)
        check('and it names what it does NOT own, on every run',
              'comment_sensitivity_check.py' in p.stdout and
              'flaky_checker_quarantine.py' in p.stdout, True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ══ THE REWORDING FAMILY (2026-09-24) ══════════════════════════════════
    # Arms above control the FILE-transform family. These control the second
    # family: a judgement-call verdict must survive a rewording that cannot
    # change what the text means. Same both-directions discipline -- a real
    # grader made fragile must be CAUGHT, and the shipped graders must not be.
    print('\n--- the rewording family ---')

    locked, lock_rows, lock_problems = M.prose_lock()
    check('the rewording criteria LOCK on the shipped transforms',
          (locked, len(lock_rows)), (True, len(M.PROSE_RELATIONS)))
    if not locked:
        print('       %s' % '; '.join(lock_problems)[:300])

    # ── P2: THE LOCK MUST REFUSE A TRANSFORM THAT CHANGES MEANING ─────────
    # This replays the real defect the lock caught on its own first run. An
    # HTML entity is case-SENSITIVE: `&mdash;` is a character and `&MDASH;`
    # is six wrong ones, so a naive upper() is not meaning-preserving and
    # every violation it reported would be true about the transform and false
    # about the grader. Without this arm the lock is a sentence in a
    # docstring.
    _real_case = M.w_case
    try:
        M.PROSE_RELATIONS = [(n, (lambda t: t.upper()) if n == 'case' else f, w)
                             for n, f, w in M.PROSE_RELATIONS]
        naive_locked, _rows, naive_problems = M.prose_lock()
        check('a MEANING-CHANGING transform (naive upper() over HTML entities) '
              'is REFUSED by the lock', naive_locked, False)
        check('...and the refusal names the normalising fixture, so the reason '
              'is readable',
              any('normalising fixture DISAGREED' in p for p in naive_problems),
              True)
    finally:
        M.PROSE_RELATIONS = [(n, _real_case if n == 'case' else f, w)
                             for n, f, w in M.PROSE_RELATIONS]

    # ── P3: A REAL GRADER MADE FRAGILE MUST BE CAUGHT ────────────────────
    # The mutation is on `testability_gate.classify` itself, not on a fixture:
    # its lower-casing is removed, which is exactly the defect the `case`
    # relation exists to find -- criteria built from lower-case keyword lists
    # that pass every hand-written fixture and fail the first row somebody
    # typed in capitals.
    _real_subjects = M.SUBJECTS
    import testability_gate as _TG
    _real_classify = _TG.classify

    def _fragile(text):
        """classify() with its lower-casing removed. Nothing else changed."""
        t = _TG._norm(text)
        low = ' ' + t + ' '                       # <-- the mutation: no .lower()
        words = re.findall(r"[A-Za-z_][A-Za-z_'-]*", t)
        import testability_criteria as _C
        for h in _C.HEDGE:
            if h in low:
                return ('UNFALSIFIABLE', '')
        for v in _C.VAGUE:
            if re.search(r'(?<![A-Za-z])' + re.escape(v) + r'(?![A-Za-z])', low):
                return ('VAGUE', '')
        if len(words) < _C.MIN_WORDS:
            return ('TOO-SHORT', '')
        if not any(re.search(r'(?<![A-Za-z])' + re.escape(b) + r'(?![A-Za-z])', low)
                   for b in _C.BEHAVIOUR):
            return ('NO-CLAIM', '')
        return ('PASS', '')

    try:
        M.SUBJECTS = [('testability_fragile', M._c_testability,
                       lambda u: _fragile(u)[0], M._r_text, 'the mutant')]
        rows, cnr, dists = M.measure_prose(per_subject=60)
        bad = [r for r in rows if r['applicable'] and not r['holds']]
        check('a REAL grader made case-sensitive is CAUGHT by the case relation',
              bool([r for r in bad if r['relation'] == 'case']), True)
        check('...and the mutant is not reported DEGENERATE, so the catch is '
              'about the relation and not about a constant answer',
              [d['degenerate'] for d in dists], [False])
    finally:
        M.SUBJECTS = _real_subjects

    # ── P4: THE PAIRED POSITIVE ──────────────────────────────────────────
    # Without this, P3 is satisfied by a family that reports everything as
    # violated.
    rows, cnr, dists = M.measure_prose(per_subject=60)
    bad = [r for r in rows if r['applicable'] and not r['holds']]
    check('the SHIPPED graders are NOT caught, so the family is not one that '
          'flags everything', bad, [])
    check('...and every declared subject actually produced comparisons',
          sorted(set(r['subject'] for r in rows)),
          sorted(n for n, _, _, _, _ in M.SUBJECTS))

    # ── P5: A NO-OP TRANSFORM IS NOT A PASS ──────────────────────────────
    # The failure this arm exists for: most transforms are no-ops on most
    # units, and comparing a verdict with itself holds forever. Counting that
    # as held is "a comparison that can never differ reports zero violations"
    # one level down from the lock.
    noop = [r for r in rows if not r['applicable']]
    check('a transform that changed nothing is recorded NOT APPLICABLE rather '
          'than held', (bool(noop), sorted(set(r['holds'] for r in noop))),
          (True, [None]))

    # ── P6: A CONSTANT GRADER IS A COULD-NOT-TELL, NOT A CLEAN RESULT ────
    # The real instance: asserts_access_control() answers False on all 388
    # evidence cells, and five relations over it held vacuously.
    try:
        M.SUBJECTS = [('always_false', M._c_testability, lambda u: False,
                       M._r_text, 'a constant grader')]
        rows6, cnr6, dists6 = M.measure_prose(per_subject=40)
        check('a grader with ONE distinct verdict is reported DEGENERATE',
              [d['degenerate'] for d in dists6], [True])
        check('...and it lands in COULD NOT RUN, never in the held count',
              (rows6, any('DEGENERATE' in c for c in cnr6)), ([], True))
    finally:
        M.SUBJECTS = _real_subjects

    # ── P7: THE LABEL-COLLISION REGRESSION ───────────────────────────────
    # The harness's own fifth confidently-wrong verdict, found today. The
    # baseline verdicts were keyed by LABEL, and the testability corpus labels
    # units by their matrix SECTION -- 450 requirements over about ten labels.
    # Every unit but the last in each section was compared against a DIFFERENT
    # requirement's verdict and the tool reported 1184 violations that did not
    # exist. A corpus of two units that SHARE a label and disagree reproduces
    # it exactly: keyed by label, one of them is compared to the other.
    _collide = [('same-label', 'the endpoint returns 404 when the roster is empty'),
                ('same-label', 'thing')]

    def _collide_corpus():
        return list(_collide)

    try:
        M.SUBJECTS = [('collision', _collide_corpus,
                       lambda u: _real_classify(u)[0], M._r_text, 'two units, one label')]
        rows7, cnr7, dists7 = M.measure_prose()
        bad7 = [r for r in rows7 if r['applicable'] and not r['holds']]
        check('two corpus units sharing a LABEL are each compared against '
              'their OWN baseline', bad7, [])
        check('...and the fixture really does have two different verdicts, so '
              'the arm above is not passing on a corpus that cannot collide',
              len(set(_real_classify(u)[0] for _l, u in _collide)) > 1, True)
    finally:
        M.SUBJECTS = _real_subjects

    print('')
    if FAILED:
        print('FAILED  metamorphic probe: %d failed' % len(FAILED))
        for f in FAILED:
            print('  - %s' % f)
        return 1
    print('ALL METAMORPHIC PROBE ASSERTIONS PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
