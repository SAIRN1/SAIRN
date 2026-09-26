#!/usr/bin/env python
"""copy_exactly_gate.py -- methodology item 43, made mechanical.

    python tools/copy_exactly_gate.py --fixtures        # the blind lock alone
    python tools/copy_exactly_gate.py --range A..B       # what that range propagates
    python tools/copy_exactly_gate.py --pre-push         # ref lines on stdin
    python tools/copy_exactly_gate.py --measure 300      # calibration over history

── WHAT THIS ENFORCES ──────────────────────────────────────────────────────
docs/2026-09-13-cross-domain-disciplines.md item 7 (Ariane 5 Flight 501):
propagating a proven pattern to a new place requires an explicit
re-qualification against the TARGET's operating conditions -- SCALE, INPUT
RANGE, CRITICALITY TIER -- not merely a diff proving the bytes match.

That convention has been written down since 2026-09-13 and enforced by nothing.
This is the enforcement: a push that COPIES A BLOCK OF CODE from somewhere it
already exists into somewhere new must carry the three answers, or say in a real
sentence why the match is not a propagation.

THE DISCIPLINE ITSELF DEMANDS THIS SHAPE, in its own words: *"Any mechanism
built to propagate a must-copy-exactly pattern automatically must carry the
re-qualification check BY CONSTRUCTION -- a propagation tool that verifies
byte-identity and nothing else is faster at making this exact mistake, on more
resources, than a human doing it by hand."* A human with an editor is such a
mechanism.

── WHAT IT DOES NOT DO, SAID FIRST ─────────────────────────────────────────
It does not judge whether a propagation is SAFE. It cannot: safety is the answer
to the three questions and the answers are judgements. It refuses a propagation
with NO RECORDED ANSWER, which is a different and much weaker claim -- and is
exactly the gap item 7 describes, because the Ariane copy was faithful and the
review that would have caught it was never asked for.

It is also NOT a clone detector for code quality. Duplication that is already in
the tree is none of its business; only NEWLY ADDED duplication of something that
already existed is.

── AND IT IS NOT tools/copy_exactly_check.py, WHICH IS THE OTHER HALF ──────
The two are complements, not copies, and each answers a question the other
deliberately refuses:

  copy_exactly_check.py   IS THE SOURCE STILL RIGHT? It compares the one
                          literal "SAIRN CLAUDE ENGINE -- Copy Exactly" block in
                          SAIRNVET-FINAL-SPEC.md against what sairnvet.html
                          actually runs. Measured 2026-09-14: 0 of 5 functions
                          byte-identical, four differing in substance because
                          the APP had been fixed and the spec had not. A
                          Copy-Exactly block is a propagation VECTOR.
  copy_exactly_gate.py    WAS THE TARGET RE-QUALIFIED? (this file)

copy_exactly_check.py's own header says it "does NOT answer section 7's actual
question ... the disciplines doc calls for a refusal to propagate without a
recorded answer to each, not an automatic verdict." This is that refusal. Their
probes are tests/run_copy_exactly_probe.py and
tests/run_copy_exactly_gate_probe.py respectively -- names one word apart, which
is worth knowing before editing either.

── THE RECORD IT REQUIRES ──────────────────────────────────────────────────
In the commit message of the commit that does the propagating:

    copy-exactly: api/sd-data.js <- api/sd-render.js
      scale: target holds ~40k rows against the source's ~200; the loop is
        O(n) and the cap at :412 still bounds it
      input-range: target can receive a negative amount (refunds) which the
        source never could; the guard at :418 covers it, driven in the probe
      tier: source xx_prefs is Tier C, target xx_ledger is Tier A/A --
        re-read the money path rather than inheriting the source's proof

All three keys are required and each must be a real sentence. `tier:` must name
something, because "same tier" with no names is the answer that gets typed when
nobody looked.

THE EXAMPLE ABOVE USES ILLUSTRATIVE RESOURCE NAMES (`xx_prefs`, `xx_ledger`) AND
THAT IS DELIBERATE. The first version used real ones and
tools/tier_a_review_gate.py correctly read this file as code serving a Tier A
resource -- a resource name in EXAMPLE PROSE is indistinguishable from one in
code to a name matcher, which is PR 1.2 arriving in a fixture. Use real names in
a real record; not in the documentation of the format.

If the detected match is NOT a propagation -- a shared header, a generated file,
a fixture repeated on purpose -- say so:

    copy-exactly-none: both hunks are the standard CORS preamble every api/
      handler carries; there is no pattern being moved

── WHY IT FAILS OPEN ON ITS OWN ERRORS, AND CLOSED ON A FINDING ────────────
Same standard as .githooks/pre-push: an internal error exits 0, because a gate
that crashes closed gets disabled and then protects nothing. A DETECTED
propagation with no record exits 1. A range it cannot read exits 2 --
could-not-run, never folded into a pass (PR 1.11).
"""
import io
import os
import re
import subprocess
import sys

# ── THE REPO IS THE ONE WE ARE INVOKED IN, NOT THE ONE THIS FILE LIVES IN ──
# The first version derived REPO from __file__ alone. That is right for a push
# gate -- it is always run inside the clone it guards -- and it made the tool
# UNTESTABLE: tests/run_copy_exactly_probe.py builds throwaway repositories and
# asks the gate to judge a range inside them, and every such range resolved
# against THIS repo instead and came back "does not resolve".
#
# CAUGHT BY THE PROBE'S FIRST ARM, which exists to check its own assumption
# before anything rests on it, and it failed on the first run. A tool that can
# only ever judge one repository cannot be shown to judge correctly -- which is
# the testability defect this platform has a standing discipline about, arriving
# here as "the harness cannot reach the thing it is testing".
#
# Falls back to the file's own location so a run from outside any repo still
# has an answer rather than crashing.
def _repo_root():
    try:
        r = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=30)
        if r.returncode == 0 and (r.stdout or '').strip():
            return (r.stdout or '').strip()
    except Exception:                                            # noqa: BLE001
        pass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


REPO = None          # resolved in main(); the fixtures reassign it deliberately

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

EXIT_OK, EXIT_DENY, EXIT_COULD_NOT_RUN = 0, 1, 2

# ── THE CRITERIA, AND EVERY NUMBER HERE WAS MEASURED BEFORE IT WAS CHOSEN ───
# `--measure N` walks the last N real commits and reports how many would have
# been flagged. The numbers below are what made that count small enough to be
# read rather than dismissed; run it again before changing one.
#
# CRITERIA_VERSION is stamped so a later reader can tell which thresholds a
# recorded verdict was reached under -- the same reason
# tools/sabotage_control_check.py carries one.
CRITERIA_VERSION = '2026-09-26.1'

# A block has to be long enough that copying it was a decision. Eight
# significant lines is not a shared idiom; it is a pattern.
MIN_SIGNIFICANT = 8
# ...and varied enough that it is not a table. A 20-line block of nine distinct
# lines repeated is a data literal, not a propagated mechanism.
MIN_DISTINCT_RATIO = 0.6

CODE_SUFFIXES = ('.js', '.py', '.sql', '.html', '.mjs', '.cjs')

# Files whose whole job is to be identical, or to be regenerated.
EXEMPT_RE = re.compile(
    r'(^|/)(node_modules|\.git|__pycache__)/'
    r'|(^|/)docs/[A-Z-]*\.md$'
    r'|(^|/)package-lock\.json$')

# A line that carries no logic. Dropped before anything is measured, so
# comment-only and blank differences never make two blocks look different, and
# never make two unrelated blocks look the same either.
TRIVIAL_RE = re.compile(
    r'^\s*($'
    r'|//|#|/\*|\*/|\*\s|--\s'                     # comments, js/py/sql
    r'|[{}\[\]();,]+$'                             # punctuation-only
    r'|\}\s*(else|catch|finally)?\s*[{(]?\s*$'
    r"|('use strict'|\"use strict\");?$"
    r'|(import|from|require|const\s+\w+\s*=\s*require)\b'  # module preamble
    r')')

TRAILER_RE = re.compile(r'^copy-exactly:\s*(.+)$', re.I | re.M)
NONE_RE = re.compile(r'^copy-exactly-none:\s*(.+)$', re.I | re.M)
KEY_RE = {
    'scale': re.compile(r'^\s*scale:\s*(.+)$', re.I | re.M),
    'input-range': re.compile(r'^\s*input-range:\s*(.+)$', re.I | re.M),
    'tier': re.compile(r'^\s*tier:\s*(.+)$', re.I | re.M),
}
MIN_ANSWER = 25
MIN_NONE_REASON = 40


def git(*args, **kw):
    cwd = kw.pop('cwd', REPO)
    r = subprocess.run(['git', '-C', cwd] + list(args), capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=180)
    return r.returncode, (r.stdout or ''), (r.stderr or '')


def significant(lines):
    """The logic-bearing lines of a block, left-trimmed. Order preserved."""
    return [l.strip() for l in lines if not TRIVIAL_RE.match(l)]


def is_code(path):
    p = path.replace('\\', '/')
    return p.endswith(CODE_SUFFIXES) and not EXEMPT_RE.search(p)


def added_runs(base, tip):
    """[(path, [lines])] for every run of consecutive ADDED lines in the range.

    -U0 so a run is exactly what the diff added, with no shared context stuck
    to either end -- context lines in a run would make two unrelated additions
    in similar surroundings look like one block.
    """
    code, out, err = git('diff', '-U0', base, tip)
    if code != 0:
        return None, 'git diff %s..%s failed: %s' % (base[:8], tip[:8], err.strip())
    runs, path, cur = [], None, []
    for line in out.split('\n'):
        if line.startswith('diff --git '):
            if cur:
                runs.append((path, cur)); cur = []
            path = None
        elif line.startswith('+++ b/'):
            path = line[6:].strip()
        elif line.startswith('@@'):
            if cur:
                runs.append((path, cur)); cur = []
        elif line.startswith('+') and not line.startswith('+++'):
            cur.append(line[1:])
        else:
            if cur:
                runs.append((path, cur)); cur = []
    if cur:
        runs.append((path, cur))
    return [(p, ls) for p, ls in runs if p and is_code(p)], ''


def find_source(base, needle, target_path):
    """(path, line) in the BASE tree where `needle` (significant lines) already
    exists as a consecutive significant run, or None.

    SEEDED ON ONE LINE, THEN CONFIRMED. Grepping the tree for the first line is
    cheap; the confirmation is what makes a hit mean something. A seed that hits
    hundreds of files is abandoned rather than confirmed one by one -- a line
    that common is an idiom, not a pattern, and the seed being useless is
    itself the answer.
    """
    seed = needle[0]
    if len(seed) < 12:
        return None
    code, out, _e = git('grep', '-F', '-n', '--', seed, base)
    if code not in (0, 1):
        return None
    hits = [l for l in out.split('\n') if l.strip()]
    if not hits or len(hits) > 40:
        return None
    for hit in hits:
        # format: <rev>:<path>:<lineno>:<text>
        parts = hit.split(':', 3)
        if len(parts) < 4:
            continue
        hpath, hline = parts[1], parts[2]
        if hpath.replace('\\', '/') == target_path.replace('\\', '/'):
            continue                      # the same file is not a propagation
        if not is_code(hpath):
            continue
        c2, body, _ = git('show', base + ':' + hpath)
        if c2 != 0:
            continue
        sig = significant(body.split('\n'))
        # Where does the needle start in the source's significant stream?
        for i in range(len(sig) - len(needle) + 1):
            if sig[i:i + len(needle)] == needle:
                return hpath, hline
    return None


def propagations(base, tip):
    """([finding], problem). A finding is (target, source, n_lines, first_line)."""
    runs, problem = added_runs(base, tip)
    if runs is None:
        return None, problem
    found, seen = [], set()
    for path, lines in runs:
        sig = significant(lines)
        if len(sig) < MIN_SIGNIFICANT:
            continue
        if len(set(sig)) / float(len(sig)) < MIN_DISTINCT_RATIO:
            continue
        key = (path, tuple(sig))
        if key in seen:
            continue
        seen.add(key)
        src = find_source(base, sig, path)
        if src:
            found.append((path, src[0], len(sig), sig[0][:90]))
    return found, ''


# ── THE RECORD, PARSED FROM THE COMMIT MESSAGES IN THE RANGE ────────────────
def records(base, tip):
    """(declared_targets, none_reasons, problems) from the range's messages."""
    code, out, _e = git('log', '--format=%B%x1e', base + '..' + tip)
    if code != 0:
        return set(), [], ['could not read the commit messages for the range']
    targets, nones, problems = set(), [], []
    for body in out.split('\x1e'):
        if not body.strip():
            continue
        for m in NONE_RE.finditer(body):
            reason = m.group(1).strip()
            if len(reason) < MIN_NONE_REASON:
                problems.append('a copy-exactly-none note with only %d characters '
                                'of reason; %d are required, because a bare '
                                'refusal is what makes the field meaningless'
                                % (len(reason), MIN_NONE_REASON))
            else:
                nones.append(reason)
        for m in TRAILER_RE.finditer(body):
            subject = m.group(1).strip()
            block = body[m.end():m.end() + 1200]
            missing, thin = [], []
            for key, rx in KEY_RE.items():
                km = rx.search(block)
                if not km:
                    missing.append(key)
                elif len(km.group(1).strip()) < MIN_ANSWER:
                    thin.append('%s (%d chars, %d required)'
                                % (key, len(km.group(1).strip()), MIN_ANSWER))
            if missing or thin:
                problems.append(
                    'copy-exactly: %s is recorded but incomplete -- %s%s. All '
                    'three questions are the re-qualification; two of them is a '
                    'diff with a note on it.'
                    % (subject,
                       ('missing ' + ', '.join(sorted(missing))) if missing else '',
                       ('; too short: ' + ', '.join(thin)) if thin else ''))
            else:
                # The declared target is whatever path appears first.
                for tok in re.split(r'[\s<>,]+', subject):
                    if is_code(tok):
                        targets.add(tok.replace('\\', '/'))
                        break
    return targets, nones, problems


def prepush_range():
    try:
        data = sys.stdin.read()
    except Exception:
        return None, None, 'stdin could not be read'
    refs = [p.split() for p in data.splitlines() if p.split()]
    refs = [p for p in refs if len(p) == 4]
    if not refs:
        return None, None, 'no ref lines on stdin -- cannot tell what is being pushed'
    if all(set(p[1]) == {'0'} for p in refs):
        return None, None, 'DELETE_ONLY'
    local = next((p[1] for p in refs if set(p[1]) != {'0'}), None)
    remote = next((p[3] for p in refs if set(p[3]) != {'0'}), None)
    return remote, local, ''


# ── THE BLIND LOCK ─────────────────────────────────────────────────────────
# Both directions, built in a throwaway repository so the criteria are exercised
# against real git output rather than against a hand-made diff. Item 1 of the
# cross-domain disciplines: criteria that cannot classify a known case cannot
# classify an unknown one, so this runs FIRST and a failure stops the sweep.
FIXTURE_BLOCK = """function guardRow(row) {
  var amount = Number(row && row.amount);
  if (!isFinite(amount)) { return refuse('BAD_AMOUNT', 'amount must be a number'); }
  if (amount < 0) { return refuse('NEGATIVE', 'a refund is not a charge'); }
  var cents = Math.round(amount * 100);
  if (cents > MAX_CENTS) { return refuse('TOO_LARGE', 'over the per-row cap'); }
  var tag = String(row.tag || '').trim().toUpperCase();
  if (!TAGS[tag]) { return refuse('BAD_TAG', 'unknown tag ' + tag); }
  return { ok: true, cents: cents, tag: tag };
}"""

TABLE_BLOCK = '\n'.join(["  ['x%d', 'y'], ['x%d', 'y']," % (i, i) for i in range(12)])


def _fx_repo(td):
    git('init', '-q', cwd=td)
    git('config', 'user.email', 'fx@example.invalid', cwd=td)
    git('config', 'user.name', 'fx', cwd=td)
    return td


def run_fixtures(verbose=True):
    import tempfile
    bad = []

    def case(label, build, want_count):
        with tempfile.TemporaryDirectory() as td:
            _fx_repo(td)
            build(td)
            code, base, _ = git('rev-list', '--max-parents=0', 'HEAD', cwd=td)
            base = base.strip().split('\n')[0]
            code, tip, _ = git('rev-parse', 'HEAD', cwd=td)
            tip = tip.strip()
            global REPO
            real, REPO = REPO, td
            try:
                found, problem = propagations(base, tip)
            finally:
                REPO = real
            got = -1 if found is None else len(found)
            ok = got == want_count
            if verbose:
                print('  %-4s %-62s %s' % ('ok' if ok else 'FAIL', label[:62],
                                           '' if ok else 'found %s, want %d%s'
                                           % (got, want_count,
                                              (' (' + problem + ')') if problem else '')))
            if not ok:
                bad.append(label)

    def w(td, name, text):
        io.open(os.path.join(td, name), 'w', encoding='utf-8', newline='\n').write(text)

    # POSITIVE: the real shape -- a proven guard moved to a second file.
    def p1(td):
        w(td, 'a.js', 'var MAX_CENTS = 1;\nvar TAGS = {};\n' + FIXTURE_BLOCK + '\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'one', cwd=td)
        w(td, 'b.js', 'var MAX_CENTS = 1;\nvar TAGS = {};\n' + FIXTURE_BLOCK + '\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'propagate', cwd=td)
    case('a proven guard copied into a SECOND file -- THE finding', p1, 1)

    # NEGATIVE: brand-new code that resembles nothing.
    def n1(td):
        w(td, 'a.js', 'var MAX_CENTS = 1;\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'one', cwd=td)
        w(td, 'b.js', '\n'.join('function f%d(){ return %d * 3 + 7; }' % (i, i)
                                for i in range(12)) + '\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'new code', cwd=td)
    case('genuinely new code matching nothing -- NOT a finding', n1, 0)

    # NEGATIVE: the same file edited in place. Moving a block within one file is
    # not a propagation, and this is the near-miss that matters most: the diff
    # looks identical to p1 from the added-lines side alone.
    def n2(td):
        w(td, 'a.js', 'var MAX_CENTS = 1;\nvar TAGS = {};\n' + FIXTURE_BLOCK + '\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'one', cwd=td)
        w(td, 'a.js', 'var MAX_CENTS = 1;\nvar TAGS = {};\n// moved\n'
                      + FIXTURE_BLOCK + '\n' + FIXTURE_BLOCK + '\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'duplicate in place', cwd=td)
    case('the SAME file gaining a second copy -- NOT this gate\'s subject', n2, 0)

    # NEGATIVE: a short shared idiom. Below MIN_SIGNIFICANT on purpose.
    def n3(td):
        w(td, 'a.js', "res.setHeader('A','*');\nres.setHeader('B','*');\n"
                      "if (req.method === 'OPTIONS') { res.status(204).end(); return; }\n")
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'one', cwd=td)
        w(td, 'b.js', "res.setHeader('A','*');\nres.setHeader('B','*');\n"
                      "if (req.method === 'OPTIONS') { res.status(204).end(); return; }\n")
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'same preamble', cwd=td)
    case('a SHORT shared preamble -- below the block floor, NOT a finding', n3, 0)

    # NEGATIVE: a long but repetitive data table.
    def n4(td):
        w(td, 'a.js', 'var T = [\n' + TABLE_BLOCK + '\n];\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'one', cwd=td)
        w(td, 'b.js', 'var T = [\n' + TABLE_BLOCK + '\n];\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'same table', cwd=td)
    case('a long but REPETITIVE table -- a literal, not a mechanism', n4, 0)

    # POSITIVE: comments and whitespace differ; the logic does not. This is the
    # one a byte-comparison misses and is precisely the Ariane case -- the copy
    # was faithful, and a copy with a reworded comment is just as faithful.
    def p2(td):
        w(td, 'a.js', 'var MAX_CENTS = 1;\nvar TAGS = {};\n' + FIXTURE_BLOCK + '\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'one', cwd=td)
        # AN INTERNAL COMMENT ADDED AND THE WHOLE BLOCK RE-INDENTED -- the shape
        # a person actually produces when they paste a block and tidy it up.
        # A byte comparison sees two different files; the pattern is the same.
        lines = FIXTURE_BLOCK.split('\n')
        reworded = '\n'.join(
            [lines[0], '  // TODO: is this still right here? nobody said.']
            + ['  ' + l for l in lines[1:]])
        w(td, 'b.js', 'var MAX_CENTS = 1;\nvar TAGS = {};\n' + reworded + '\n')
        git('add', '-A', cwd=td); git('commit', '-q', '-m', 'propagate + recomment', cwd=td)
    case('same logic, INTERNAL comment added and re-indented -- still a propagation',
         p2, 1)

    return bad


def report(found, targets, nones, problems, stream=sys.stderr):
    w = stream.write
    w('\nCOPY-EXACTLY (item 43 / Ariane 5) -- criteria %s\n' % CRITERIA_VERSION)
    uncovered = [f for f in found if f[0].replace('\\', '/') not in targets]
    if nones and uncovered:
        # A `none` note covers the whole push: it is a statement that the
        # detected matches are not propagations. Recorded, and it does not
        # silently cover a target that was ALSO declared -- that would be a
        # contradiction rather than a cover.
        w('  %d copy-exactly-none note(s) recorded; treating the remaining '
          'match(es) as declared not-a-propagation.\n' % len(nones))
        uncovered = []
    if found:
        w('  %d propagation(s) detected in this range:\n' % len(found))
        for tgt, src, n, first in found:
            mark = 'RECORDED' if tgt.replace('\\', '/') in targets else 'NO RECORD'
            w('    %-10s %s  <-  %s   (%d significant lines)\n' % (mark, tgt, src, n))
            w('               first line: %s\n' % first)
    else:
        w('  no propagation detected in this range.\n')
    for p in problems:
        w('  PROBLEM: %s\n' % p)
    return uncovered


def deny_text(uncovered):
    out = []
    out.append('')
    out.append('Blocked: this push copies a pattern into a new place with no '
               'recorded re-qualification.')
    out.append('')
    out.append('ITEM 43, AND IT IS THE ONE WHERE THE CODE IS CORRECT. Ariane 5 '
               'Flight 501 reused')
    out.append('inertial reference software that was right on Ariane 4, '
               'propagated without')
    out.append('unexplained variation, into a flight profile whose horizontal '
               'velocity the source')
    out.append('could never reach. Both redundant units failed identically, '
               'because a second copy')
    out.append('of correct software is not a second opinion. THE COPY WAS '
               'FAITHFUL. THE CONTEXT WAS NOT.')
    out.append('')
    for tgt, src, n, first in uncovered:
        out.append('  %s' % tgt)
        out.append('      %d significant lines that already exist in %s' % (n, src))
        out.append('      starting: %s' % first)
    out.append('')
    out.append('Answer the three questions in the commit message. All three, '
               'because two of')
    out.append('them is a diff with a note on it:')
    out.append('')
    out.append('    copy-exactly: %s <- %s'
               % (uncovered[0][0], uncovered[0][1]))
    out.append('      scale: does the target carry the same order of magnitude '
               'the pattern was')
    out.append('        proven at')
    out.append('      input-range: can the target receive values the source '
               'could not -- this is')
    out.append('        the Ariane case exactly')
    out.append('      tier: name both resources and their tiers from '
               'docs/CRITICALITY-TIERS.md')
    out.append('')
    out.append('Or, if this is not a propagation at all:')
    out.append('')
    out.append('    copy-exactly-none: <at least %d characters saying why>'
               % MIN_NONE_REASON)
    out.append('')
    out.append('THIS GATE DOES NOT JUDGE WHETHER THE COPY IS SAFE and cannot: '
               'safety is the')
    out.append('answer to those questions and the answers are judgements. It '
               'refuses a')
    out.append('propagation with NO ANSWER RECORDED, which is the gap item 7 '
               'describes -- the')
    out.append('review that would have caught Ariane was never asked for.')
    return '\n'.join(out) + '\n'


def main(argv):
    global REPO
    REPO = _repo_root()
    if '--fixtures' in argv:
        print('COPY-EXACTLY BLIND LOCK -- criteria %s' % CRITERIA_VERSION)
        bad = run_fixtures()
        if bad:
            print('\n%d fixture(s) FAILED: %s' % (len(bad), ', '.join(bad)))
            return EXIT_COULD_NOT_RUN
        print('\nall fixtures classified correctly.')
        return EXIT_OK

    # The lock runs first on every real path too. Criteria that cannot classify
    # a known case must not be used on an unknown one.
    bad = run_fixtures(verbose=False)
    if bad:
        sys.stderr.write('COULD NOT RUN: the blind lock failed (%s), so the '
                         'criteria are not fit to judge a real range. '
                         'Nothing was checked.\n' % ', '.join(bad))
        return EXIT_COULD_NOT_RUN

    if '--measure' in argv:
        i = argv.index('--measure')
        n = int(argv[i + 1]) if len(argv) > i + 1 else 200
        code, out, _e = git('log', '--format=%H', '-n', str(n))
        shas = [s for s in out.split('\n') if s.strip()]
        print('CALIBRATION over %d commits, criteria %s' % (len(shas), CRITERIA_VERSION))
        flagged = 0
        for sha in shas:
            found, problem = propagations(sha + '^', sha)
            if found:
                flagged += 1
                print('  %s  %d propagation(s)' % (sha[:8], len(found)))
                for tgt, src, nl, first in found[:3]:
                    print('      %s <- %s (%d lines) %s' % (tgt, src, nl, first[:60]))
        print('\n%d of %d commits would be flagged (%.1f%%)'
              % (flagged, len(shas), 100.0 * flagged / max(1, len(shas))))
        print('A GATE NOBODY CAN SATISFY GETS OVERRIDDEN. If that share is '
              'large, the thresholds')
        print('are wrong and this number is the evidence, not the gate.')
        return EXIT_OK

    if '--pre-push' in argv:
        base, tip, problem = prepush_range()
        if problem == 'DELETE_ONLY':
            return EXIT_OK
        if problem:
            sys.stderr.write('COULD NOT RUN: %s. Denying rather than passing.\n' % problem)
            return EXIT_COULD_NOT_RUN
        if not base or set(base) == {'0'}:
            # A brand-new branch has no base. Fall back to origin/main, and say
            # so -- guessing silently is how a gate judges the wrong range.
            code, out, _e = git('rev-parse', 'origin/main')
            base = out.strip()
            sys.stderr.write('copy-exactly: new branch, no remote base -- '
                             'comparing against origin/main (%s)\n' % base[:8])
    elif '--range' in argv:
        i = argv.index('--range')
        rng = argv[i + 1] if len(argv) > i + 1 else ''
        if '..' not in rng:
            sys.stderr.write('--range needs A..B\n')
            return EXIT_COULD_NOT_RUN
        base, tip = rng.split('..', 1)
    else:
        base, tip = 'origin/main', 'HEAD'

    for ref in (base, tip):
        code, _o, _e = git('rev-parse', '--verify', ref + '^{commit}')
        if code != 0:
            sys.stderr.write('COULD NOT RUN: %s does not resolve in this clone, '
                             'so the range cannot be read and nothing was '
                             'checked (PR 1.11).\n' % ref)
            return EXIT_COULD_NOT_RUN

    found, problem = propagations(base, tip)
    if found is None:
        sys.stderr.write('COULD NOT RUN: %s\n' % problem)
        return EXIT_COULD_NOT_RUN
    targets, nones, problems = records(base, tip)
    uncovered = report(found, targets, nones, problems)
    if problems:
        sys.stderr.write(deny_text(uncovered) if uncovered else
                         '\nBlocked: a copy-exactly record in this range is '
                         'incomplete -- see PROBLEM above.\n')
        return EXIT_DENY
    if uncovered:
        sys.stderr.write(deny_text(uncovered))
        return EXIT_DENY
    return EXIT_OK


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:                                    # noqa: BLE001
        # FAILS OPEN on its own errors, same standard as .githooks/pre-push and
        # for the reason its header gives: a gate that crashes closed gets
        # disabled, and then protects nothing. The error is printed, never
        # swallowed.
        sys.stderr.write('copy_exactly_gate: internal error, ALLOWING the push '
                         'and reporting it: %r\n' % (exc,))
        sys.exit(EXIT_OK)
