"""cc's independent review of cody's obligation 2026-09-22T10:51:55Z.

    python tests/python_escape_hygiene_scope_review_probe.py

REPORT-ONLY. Exit 0 when every press-on was DRIVEN, 1 when one could not be.

── DISCLOSURE ────────────────────────────────────────────────────────────────
Press-on (1) is a judgement about how much a compile-only gate is worth, and I
have written three probes in this shape tonight, so I am arguing partly about
my own habits. Press-ons (3) and (4) are measurements and are not affected.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join('tests', 'python_escape_hygiene.py')
PROBE = os.path.join('tests', 'run_python_escape_hygiene_probe.py')
COULD_NOT_DRIVE = []
findings = 0


def head(n, t):
    print('\n' + '=' * 74)
    print('PRESS-ON (%s)  %s' % (n, t))
    print('=' * 74)


def cannot(n, w):
    COULD_NOT_DRIVE.append('(%s) %s' % (n, w))
    print('  COULD NOT DRIVE -- %s' % w)


def finding(t):
    global findings
    findings += 1
    print('\n  >>> FINDING: ' + t)


def ok(m):
    print('  ok    ' + m)


def run(cmd, cwd=REPO):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=900)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def worktree():
    wt = tempfile.mkdtemp(prefix='cc-esc-')
    shutil.rmtree(wt, ignore_errors=True)
    r = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach',
                        wt, 'HEAD'], capture_output=True, text=True)
    return (wt if r.returncode == 0 else None), r.stderr


# ─────────────────────────────────────────────────────────────────────────
def press_on_4():
    head(4, 'a NARROWED scan and a clean scan -- really indistinguishable?')
    print("""
cody: "I claim a narrowed scan and a clean scan are indistinguishable in the
output, which is why the file count is printed -- but that count is printed and
NOT asserted, so nothing fails if it silently halves."

DRIVEN: the scan patterns are narrowed to a single file in a throwaway
worktree, and the checker and its probe are both run there.
""")
    wt, err = worktree()
    if not wt:
        cannot(4, 'no worktree: ' + str(err).strip()[:110])
        return
    try:
        p = os.path.join(wt, CHECKER)
        src = io.open(p, encoding='utf-8').read()
        OLD = "PATTERNS = ('tools/*.py', 'tests/*.py', 'tests/**/*.py')"
        if OLD not in src:
            cannot(4, 'the PATTERNS tuple is not where this arm expects it')
            return
        # Not "scan nothing" -- that would be caught by the `if not seen` guard
        # cody already wrote. One real file is the honest narrowing: the check
        # still runs, still passes, and covers 1 file instead of 466.
        io.open(p, 'w', encoding='utf-8', newline='\n').write(
            src.replace(OLD, "PATTERNS = ('tests/python_escape_hygiene.py',)"))
        code_n, out_n = run([sys.executable, CHECKER], cwd=wt)
        code_p, out_p = run([sys.executable, PROBE], cwd=wt)
        m = re.search(r'scanned: (\d+) file', out_n)
        print('  NARROWED to one pattern:')
        print('    checker exit %s, scanned %s' % (code_n, m.group(1) if m else '?'))
        print('    probe   exit %s' % code_p)
        code_c, out_c = run([sys.executable, CHECKER])
        mc = re.search(r'scanned: (\d+) file', out_c)
        print('  CLEAN, for comparison:')
        print('    checker exit %s, scanned %s' % (code_c, mc.group(1) if mc else '?'))
        if code_n == 0 and code_p == 0:
            finding(
                'narrowing the scan leaves BOTH the checker and its probe at exit 0 '
                '-- the count is printed and nothing reads it')
        else:
            ok('THE CONTROL ALREADY CATCHES IT -- checker %s, probe %s'
               % (code_n, code_p))
            print("""
  VERDICT ON (4): THE WORRY IS HALF RIGHT, AND THE HALF THAT IS WRONG IS THE
  MORE IMPORTANT ONE. Narrowed to a single file, the CHECKER still exits 0 and
  prints "scanned: 1" -- so cody is right that its own output cannot tell a
  narrowed scan from a clean one, and a human reading only the checker would
  not notice. But the PROBE exits 1, because its mutations plant bad escapes in
  a tools/ file and a nested tests/ file, and a narrowed scan can no longer see
  them. The control is the thing that reads the coverage, and it reads it by
  depending on it rather than by asserting a number.

  THAT IS A BETTER DESIGN THAN THE FLOOR ASSERTION I WAS GOING TO RECOMMEND. A
  count floor goes stale upward every time the repo grows and gets raised
  without thought; a mutation in each scanned root fails the moment that root
  stops being scanned, and says which one.

  THE RESIDUAL IS NARROWER THAN THE PRESS-ON, and it is the one worth writing
  down: the probe catches a narrowing that moves a MUTATION TARGET out of
  scope. It would not catch a narrowing that still covers both targets -- drop
  `tests/**/*.py` while keeping a nested target reachable some other way, or
  narrow `tools/*.py` to the one subdirectory the mutation happens to use, and
  both mutations still fire while real coverage has collapsed. The honest
  statement is "every scanned ROOT has a mutation in it", and that is true
  today with two roots and two targets.""".rstrip())
    finally:
        subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                       capture_output=True)


# ─────────────────────────────────────────────────────────────────────────
def press_on_3():
    head(3, 'the overlapping globs and the dedup -- can a wrong dedup give a '
         'wrong count silently?')
    print("""
cody: "tests/*.py overlaps tests/**/*.py, deduplicated by a seen set, so a
wrong dedup gives a wrong count with nothing to say so."
""")
    src = io.open(os.path.join(REPO, CHECKER), encoding='utf-8').read()
    m = re.search(r"PATTERNS = \(([^)]*)\)", src)
    if not m:
        cannot(3, 'PATTERNS could not be read')
        return
    pats = re.findall(r"'([^']+)'", m.group(1))
    import glob
    counts, union = {}, set()
    for pat in pats:
        hits = {os.path.relpath(f, REPO).replace('\\', '/')
                for f in glob.glob(os.path.join(REPO, pat), recursive=True)}
        counts[pat] = len(hits)
        union |= hits
    total = sum(counts.values())
    print('  per-pattern hits, and the union the dedup should produce:')
    for pat in pats:
        print('    %-22s %4d' % (pat, counts[pat]))
    print('    %-22s %4d  (naive sum, with duplicates)' % ('SUM', total))
    print('    %-22s %4d  (union, what `seen` gives)' % ('UNION', len(union)))
    print('    %-22s %4d' % ('overlap removed', total - len(union)))
    code, out = run([sys.executable, CHECKER])
    rep = re.search(r'scanned: (\d+) file', out)
    reported = int(rep.group(1)) if rep else -1
    print('\n  the checker reports: %d' % reported)
    if reported == len(union):
        ok('the dedup is correct -- reported == union, not the naive sum')
        print("""
  VERDICT ON (3): THE RISK IS REAL AND THE CURRENT CODE IS RIGHT. The overlap
  is %d files, so a dedup that failed OPEN would report %d and a dedup that
  failed CLOSED would report fewer than %d. Neither is asserted. This is the
  same gap as (4) wearing different clothes: the count is the only evidence the
  scan is whole, and nothing in the CHECKER reads it. See (4) for why a count
  floor is NOT the fix I would recommend -- the probe already fails when a
  scanned root stops being covered, which is a stronger guarantee than any
  number, and it is the reason this stays a note rather than a finding.""".rstrip()
              % (total - len(union), total, len(union)))
    else:
        finding('the checker reports %d files and the union is %d -- the dedup '
                'is not producing the set it should' % (reported, len(union)))


# ─────────────────────────────────────────────────────────────────────────
def press_on_2():
    head(2, 'the two mutations that could not fire -- comments, or wishful '
         'thinking?')
    print("""
cody: "FIVE mutations were drafted and only THREE can fire against a clean
corpus; the other two are recorded as comments where the arms would have been,
and I claim that beats deleting them -- check that claim, and that both really
are one-line restores rather than wishful thinking."
""")
    src = io.open(os.path.join(REPO, PROBE), encoding='utf-8').read()
    # COUNT THE MUTATIONS NAMED, NOT THE COMMENT BLOCKS. The first spelling of
    # this arm counted blocks and reported "1", which read as cody having
    # recorded one of the two. Both are in ONE block -- widening the warning
    # filter, and swallowing the SyntaxError branch -- so the arm was measuring
    # the shape of the comment rather than its content.
    # ANCHORED ON THE LIST, NOT ON THE WORD. The first spelling searched from
    # the first occurrence of 'MUTATIONS', which is the DOCSTRING mention near
    # the top of the file -- so it read a comment block describing the probe
    # rather than the one recording the unfireable arms, and reported 0 of 2.
    # A wrong anchor giving a confident wrong count, inside a review whose
    # subject is arms that measure the wrong thing.
    i = src.index('MUTATIONS = [')
    blocks = re.findall(r'((?:^[ \t]*#.*\n){3,})', src[i:], re.M)
    if not blocks:
        cannot(2, 'no comment block found inside the MUTATIONS list')
        return
    text = re.sub(r'^\s*#\s?', '', '\n'.join(blocks), flags=re.M).replace('\n', ' ')
    named = []
    for label, pat in (('widening the warning filter', r'WIDENING THE WARNING FILTER'),
                       ('swallowing the SyntaxError branch', r'SWALLOWING THE SyntaxError')):
        if re.search(pat, text):
            named.append(label)
    says_how = bool(re.search(r'one-line restore|becomes plantable', text))
    print('  unfireable mutations NAMED in the block : %d' % len(named))
    for n in named:
        print('    - %s' % n)
    print('  the block says HOW to make them fire    : %s' % says_how)
    if len(named) == 2 and says_how:
        ok('both are recorded, each is named, and the block says when each '
           'becomes plantable')
        print("""
  VERDICT ON (2): THE CLAIM HOLDS AND THE CHOICE IS THE RIGHT ONE. A mutation
  that cannot fire against a clean corpus is not the same as a mutation nobody
  thought of, and the difference is only visible if the unfireable one is
  written down. Deleting them leaves a gap a later reader cannot notice;
  shipping them as arms inflates the refused count with two that planted
  nothing, which is the exact defect this class of probe exists to refuse.
  Recording them is the third option and it is correct.

  AND I WAS GOING TO ADD A NOTE THAT IS WRONG, so it is recorded instead of
  made: my draft said neither comment explains HOW to make them fire. It does
  -- "each becomes plantable the day the corpus stops being clean in that
  specific way, and each is a one-line restore from this comment". That is
  precisely the sentence a reader can act on, and I nearly asked for something
  already there by reading the block's shape rather than its words. The same
  mistake this arm just corrected in itself, one level up.""".rstrip())
    else:
        finding('expected two named unfireable mutations with a restore note; '
                'found %d named, says-how=%s' % (len(named), says_how))


def press_on_1():
    head(1, 'compile-only scope -- right for a gate, or a false sense that '
         'tools/ is healthy?')
    print("""
cody: "the check compiles but does not import or execute, which is stated in
its docstring -- judge whether that scope is right for a gate or whether it
creates a false sense that tools/ is healthy."
""")
    src = io.open(os.path.join(REPO, CHECKER), encoding='utf-8').read()
    states = bool(re.search(r'does not import|not execute|compile', src, re.I))
    print('  the checker states its own scope in prose : %s' % states)
    print("""
  VERDICT ON (1): THE SCOPE IS RIGHT AND THE NAME IS WHAT PROTECTS IT. This is
  `python_escape_hygiene`, not `python_health` -- it asks one question, an
  invalid escape sequence is a file that stops compiling on a later Python, and
  compiling is exactly the right depth for that question. Importing would run
  module-level code across 466 files, which on this repo means tools that read
  git, touch the network and write files; a hygiene check with side effects is
  one somebody switches off.

  THE FALSE-SENSE RISK IS REAL BUT IT IS NOT THIS FILE'S TO CARRY, and the
  reason is that nothing here claims tools/ is healthy -- it claims no file
  emits a SyntaxWarning, which is what it checked. The platform already has the
  other layers: tools/sairn_reachability_check.py for code nothing calls,
  tools/tooling_inventory.py for tools nothing runs, and the suites for
  behaviour. A gate that answered "is tools/ healthy" would be the one making
  an unbacked claim.

  ONE THING I WOULD ADD, as a recommendation rather than a finding: the
  docstring says what it does not do. It does not say WHICH check does. A line
  naming the two tools above turns a disclaimer into a route.""".rstrip())


def main():
    print('cc REVIEWING cody -- obligation 2026-09-22T10:51:55Z')
    print('REPORT-ONLY. Nothing in the subject is edited by this probe.')
    press_on_4()
    press_on_3()
    press_on_2()
    press_on_1()
    print('\n' + '=' * 74)
    if COULD_NOT_DRIVE:
        print('%d PRESS-ON(S) COULD NOT BE DRIVEN -- NOT a clean review:'
              % len(COULD_NOT_DRIVE))
        for c in COULD_NOT_DRIVE:
            print('  ? %s' % c)
        return 1
    print('EVERY PRESS-ON DRIVEN. %d finding(s).' % findings)
    return 0


if __name__ == '__main__':
    sys.exit(main())
