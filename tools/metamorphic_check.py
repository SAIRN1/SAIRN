"""Does an ANSWER survive a change that cannot change the answer?

    python tools/metamorphic_check.py                 # lock, then measure BOTH
    python tools/metamorphic_check.py --fixtures      # the blind lock alone
    python tools/metamorphic_check.py --all           # every root app file
    python tools/metamorphic_check.py --targets 5
    python tools/metamorphic_check.py --max-bytes 600000 --targets 1   # registry
    python tools/metamorphic_check.py --prose         # the REWORDING family alone
    python tools/metamorphic_check.py --no-prose      # the FILE family alone
    python tools/metamorphic_check.py --json
    python tools/metamorphic_check.py --quiet

Exit 0 when every relation holds, 1 when one is violated, 2 when any part of the
run did not happen. Report-only in the registry.

── TWO FAMILIES, AND THE SECOND IS NOT A WIDER VERSION OF THE FIRST ────────
FILE TRANSFORMS, over checkers that take a file and report findings. Flip the
line endings, add trailing spaces, insert blank lines, duplicate the file --
byte-level perturbations of the CONTAINER. Built 2026-09-13 and documented
from "THE RELATIONS" below.

REWORDING, over verdicts that are JUDGEMENT CALLS. Several tools here do not
find defects at all; they grade English and return an opinion --
`testability_gate.classify()` on a requirement sentence, `fmea_draft`'s
detectors on a source file. Those have no oracle either, and for a worse
reason: there is no correct answer even in principle, because the thing being
graded is a judgement somebody made in prose. Bold it, swap `&mdash;` for the
character it names, shout it, double the spaces, add a full stop -- none of
that changes what it MEANS, so none of it may change the verdict. Added
2026-09-24; documented at "FAMILY 2" in the body.

The first family's own limits section says checkers taking no file argument are
out of scope. THAT IS WHERE THE SECOND FAMILY GOES, rather than a second tool:
the frame here is that relations are data, and a subject is now data too.

── WHAT A METAMORPHIC RELATION IS, AND WHY THIS REPO NEEDS ONE ──────────────
Almost every check in this repo has NO ORACLE. Nobody can write down the
correct output of `literal_drift_check.py` on a 2.5MB file, so nobody can test
it by comparing against the right answer -- there isn't one to compare to. A
control pair (`checker_control_check.py`) gets around that by planting a defect
and asserting the checker fires. That proves the checker CAN fire. It says
nothing about whether it fires for the right reason.

A metamorphic relation is the other half: transform the INPUT in a way that
cannot legitimately change the ANSWER, and assert the answer did not change.
No oracle needed. It finds the class where a checker is right by accident --
matching a byte pattern that happens to correlate with the defect rather than
the defect itself.

── THE INSTANCES THAT ALREADY HAPPENED ──────────────────────────────────────
This is not speculative. Every relation below is here because the repo has
already paid for it at least once:

  `literal_drift_check.py` answered DIFFERENTLY ON IDENTICAL INPUT -- its
  near-duplicate pairs came back with A and B swapped between runs, because set
  iteration order depends on PYTHONHASHSEED. Found by hand, fixed in ac8f8491.

  A CRLF-vs-LF difference produced THREE SEPARATE FALSE ALARMS IN ONE SESSION
  on 2026-09-03, and CLAUDE.md now carries a standing instruction to compare
  after `tr -d '\\r'` before reporting drift. Every one of those was a tool
  answering differently about the same content.

  `comment_quote_check.py`'s first version blanked from any `//` to end of line
  and swallowed every `https://` -- its answer depended on text that was not
  code.

── WHAT THIS TOOL DOES *NOT* OWN, STATED SO NOBODY BUILDS A SECOND COPY ─────
Two metamorphic relations are already owned by dedicated tools and are NOT
re-implemented here. This is printed on every run rather than left in a
docstring, because an unstated exclusion reads as coverage:

  BLANKING COMMENTS must not change the answer
      -> tools/comment_sensitivity_check.py (2026-09-11). It also supplies the
         population under test here; see CHECKERS below.
  RE-RUNNING ON AN UNCHANGED TREE must not change the answer
      -> tools/flaky_checker_quarantine.py (2026-09-13), which additionally
         owns the flip-rate ledger, the quarantine process and the re-entry
         bar. Sampling repeated runs is its job, not this one's.

What is NEW here is the FRAME -- relations are data, so the next one is a table
entry rather than a new tool -- plus five relations nothing covered.

── THE RELATIONS ────────────────────────────────────────────────────────────
Each is (transform, expectation). Two expectations only, deliberately:

  SAME       the transform cannot change the answer at all. Exit code AND
             normalised report must match.
  NO_ERASE   the transform legitimately ADDS content, so the report may grow --
             but a finding on the original must not VANISH. Used where SAME
             would be false for an honest reason.

  identity    a byte-identical copy at a different path            SAME
  crlf        every line ending flipped LF<->CRLF                  SAME
  trailing_ws one space appended to every non-empty line           SAME
  blank_lines a blank line inserted after every line               SAME
  duplicate   the whole file concatenated with itself              NO_ERASE

`identity` is the harness's own control and runs first. If a checker's answer
differs between two byte-identical files at different paths, every other row
for that checker is meaningless -- so identity failing is reported as such
rather than as one violation among five.

`duplicate` is NO_ERASE rather than SAME on purpose: doubling an HTML file
genuinely creates duplicate ids, so a checker reporting MORE is correct. What
cannot be correct is a defect being ERASED by adding a second copy of it.

── THE BLIND LOCK ───────────────────────────────────────────────────────────
The criteria are decided against synthetic fixtures BEFORE any real checker is
measured, and a failed lock refuses the real run rather than reporting it. Two
fixtures: one checker that is genuinely whitespace-sensitive (every SAME
relation must catch it) and one that normalises first (nothing must fire). A
comparison that can never differ would also report zero violations, which is
why the sensitive fixture exists at all.

── WHAT IT CANNOT SEE, said here rather than discovered later ───────────────
  * checkers that take no file argument -- they resolve their own targets, and
    running those against a transformed tree would mean MUTATING the tree,
    which is what a read-only checker must not do. Six of the fleet take a
    file; the rest are out of scope, not quietly skipped;
  * a checker that is wrong on the original AND wrong on the transform in the
    same direction. Perfectly consistent and perfectly useless looks identical
    to perfectly consistent and correct;
  * whether a relation SHOULD hold for a given checker. Every relation here is
    argued in this docstring; a checker that legitimately depends on line
    endings would need an exemption with a reason, and there is no exemption
    list because nothing has earned one yet.

AND FOR THE REWORDING FAMILY, whose limits are different in kind:
  * whether a REWORDING is meaning-preserving is itself a judgement, and it is
    MINE. Every transform is argued where it is defined, and the blind lock
    refuses one that turns out not to be -- which is not a formality: the
    naive `text.upper()` was refused on the first run because an HTML entity
    is case-sensitive and `&MDASH;` is not `&mdash;`;
  * a grader that is consistently wrong. Invariance is not correctness, and
    `testability_gate` being stable under all five relations says nothing
    about whether its verdicts are right;
  * a DEGENERATE grader measures nothing, and that is detected rather than
    trusted -- but only for subjects that are actually run. A subject in
    DECLARED_UNMEASURABLE is a decision with a stated trigger, not a result;
  * SYNONYMS AND CLAUSE ORDER ARE NOT COVERED. Every transform here is
    presentational. "the endpoint returns 404" -> "the endpoint responds with
    404" is the relation a reader will assume is here and it is not, because
    deciding two phrasings mean the same thing needs a model call -- the same
    line api/claude-guardrail-metamorphic.test.js draws for the same reason.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish           # noqa: E402


def read_raw(path):
    """Read WITHOUT universal newlines, so a transform sees the real bytes.

    `checker_kit.read()` is the right reader for a checker and the wrong one
    here. Python text mode converts CRLF to LF on the way in, so reading a CRLF
    file that way and writing the copy back out produces an LF file -- which
    means `identity` was not identity at all, it was silently the `crlf`
    transform wearing identity's label.

    THAT IS NOT HYPOTHETICAL: the first real run of this tool reported
    `key_collision_check.py` as violating IDENTITY on stonedesk.html, which
    reads as nondeterminism -- the most serious verdict this tool can return.
    A byte-exact `cp` of the same file reproduced nothing. The harness had
    flipped the line endings of a CRLF file and blamed the checker. The finding
    was real; the label was wrong, and a wrong label on the most serious verdict
    is worse than no verdict.
    """
    with io.open(path, encoding='utf-8', errors='replace', newline='') as fh:
        return fh.read()
# THE POPULATION IS IMPORTED, NOT COPIED. `comment_sensitivity_check.py` already
# decided which checkers take the file to inspect as argv[1] and wrote down why
# the rest are out of scope. A second hand-maintained list would drift from it
# the first time a checker was added, and the two harnesses would then disagree
# about what "the fleet" means.
from comment_sensitivity_check import CHECKERS               # noqa: E402

PER_RUN_TIMEOUT = 120          # seconds. A timeout is COULD-NOT-RUN, not a pass.

SAME = 'SAME'
NO_ERASE = 'NO_ERASE'


# ── the transforms ───────────────────────────────────────────────────────────
def t_identity(src):
    return src


def t_crlf(src):
    """Flip line endings. Whichever the file has, give it the other one."""
    lf = src.replace('\r\n', '\n')
    return lf if '\r\n' in src else lf.replace('\n', '\r\n')


def t_trailing_ws(src):
    lf = src.replace('\r\n', '\n')
    return '\n'.join((l + ' ') if l.strip() else l for l in lf.split('\n'))


def t_blank_lines(src):
    lf = src.replace('\r\n', '\n')
    return '\n\n'.join(lf.split('\n'))


def t_duplicate(src):
    lf = src.replace('\r\n', '\n')
    return lf + '\n' + lf


RELATIONS = [
    ('identity', t_identity, SAME,
     'a byte-identical copy at a different path'),
    ('crlf', t_crlf, SAME,
     'every line ending flipped LF<->CRLF'),
    ('trailing_ws', t_trailing_ws, SAME,
     'one space appended to every non-empty line'),
    ('blank_lines', t_blank_lines, SAME,
     'a blank line inserted after every line'),
    ('duplicate', t_duplicate, NO_ERASE,
     'the whole file concatenated with itself'),
]


# ── running a checker and reading its answer ─────────────────────────────────
_LINE_NO = re.compile(r'\bline \d+', re.I)
_LEAD_NO = re.compile(r'^\s*\d+:', re.M)
# `lines [12, 34]` AND `A line(s) [1802]` -- literal_drift_check.py uses the
# second form and the first version of this pattern only knew the first, so
# every one of its position lists survived normalisation and it was reported as
# violating `blank_lines` on all three targets. The verdict was wrong and the
# mechanism is worth naming: THIS LIST OF POSITION FORMATS IS HAND-MAINTAINED,
# so a checker inventing a new one reads as a violation until it is added here.
# That direction is the safe one for a report-only tool -- a false violation
# gets read, a missed one does not -- but it is a real limitation, not a detail.
_LINES_LIST = re.compile(r'lines?(?:\(s\))?\s*\[[\d, ]*\]')
_BYTES = re.compile(r'\b\d+ bytes\b')


def normalise(out, path):
    """Strip the metadata a transform is ALLOWED to move.

    LINE NUMBERS ARE METADATA, NOT THE ANSWER. `blank_lines` shifts every
    position in the file by construction, so a checker reporting the identical
    finding one line down has not changed its answer -- and a harness that
    flagged that would be measuring its own side effects. The same argument
    `comment_sensitivity_check.py` makes for the same reason; it is repeated
    here because the transforms are different and the list is longer.

    THE FULL PATH is normalised because the temp copy legitimately lives
    elsewhere. BYTE COUNTS are normalised for the same reason line numbers are.

    THE BASENAME IS DELIBERATELY *NOT* NORMALISED, and that was the second
    defect this harness found in itself. It used to rewrite the bare filename
    too, and `key_collision_check.py` prints an ACKNOWLEDGEMENT NOTE whose prose
    contains the words "stonedesk.html". Normalising the basename rewrote that
    sentence in the baseline output and not in the copy's, so the two reports
    differed and the tool reported the checker as VIOLATING IDENTITY -- which is
    a nondeterminism verdict, the most serious thing it can say.

    That is the comment-quoting defect (PR §1.2) committed by the normaliser
    rather than by a checker: it rewrote text that merely MENTIONED the target.
    The fix is structural rather than another pattern -- every transformed copy
    is written into its own subdirectory under the SAME basename, so the two
    outputs mention the filename identically and only the directory differs.

    Nothing else is touched. Finding TEXT, finding COUNTS, section headings and
    the exit code all survive -- those are the answer.
    """
    out = out.replace(path, '<TARGET>').replace(path.replace(os.sep, '/'), '<TARGET>')
    d = os.path.dirname(path)
    out = out.replace(d, '<DIR>').replace(d.replace(os.sep, '/'), '<DIR>')
    out = _LINE_NO.sub('line <N>', out)
    out = _LEAD_NO.sub('<N>:', out)
    out = _LINES_LIST.sub('lines <L>', out)
    out = _BYTES.sub('<N> bytes', out)
    return out


def run(tool_path, target):
    """(exit, normalised_output) or (None, reason) when it did not run."""
    try:
        p = subprocess.run([sys.executable, tool_path, target],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=REPO, timeout=PER_RUN_TIMEOUT,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                    PYTHONUTF8='1'))
    except subprocess.TimeoutExpired:
        return None, 'timed out after %ds' % PER_RUN_TIMEOUT
    except OSError as e:
        return None, 'could not launch: %s' % e
    return p.returncode, normalise((p.stdout or '') + (p.stderr or ''), target)


def compare(expectation, base, trans):
    """(holds, why). `base`/`trans` are (exit, output) pairs."""
    (rc_a, out_a), (rc_b, out_b) = base, trans
    if expectation == SAME:
        if rc_a != rc_b:
            return False, 'exit %d -> %d' % (rc_a, rc_b)
        if out_a != out_b:
            return False, 'same exit (%d) but the report changed' % rc_a
        return True, ''
    # NO_ERASE: a finding on the original must not vanish.
    if rc_a != 0 and rc_b == 0:
        return False, 'a finding (exit %d) was ERASED by the transform' % rc_a
    return True, ''


# ── the blind lock ───────────────────────────────────────────────────────────
_FIXTURE_SENSITIVE = '''\
"""A fixture checker that is GENUINELY whitespace-sensitive. Not real."""
import hashlib, io, sys
# newline="" ON PURPOSE -- see the note beside this fixture in the module.
src = io.open(sys.argv[1], encoding="utf-8", errors="replace", newline="").read()
# A HASH, NOT A LENGTH. The answer must be a function of the raw bytes and
# nothing weaker -- see the note beside this fixture in the module.
print("raw digest: %s" % hashlib.sha1(src.encode("utf-8")).hexdigest()[:16])
sys.exit(1 if "PLANTED_DEFECT" in src else 0)
'''
# ── AND THE CONTROL PROBE CAUGHT THE FIXTURE ITSELF ────────────────────────
# This fixture used to print `raw length` and `newline chars`, and on a CRLF
# target the `trailing_ws` relation HELD when it was supposed to be violated.
# Not a bug in the relation: converting 6 CRLF endings to LF removes exactly 6
# bytes and appending one space to 6 non-empty lines adds exactly 6, so the
# length collided and the newline count never moved. THE FIXTURE AGREED WITH
# ITSELF BY ARITHMETIC ACCIDENT.
#
# A fixture that is only sensitive by a SUMMARY of the bytes can coincide. A
# hash cannot. Found by tests/run_metamorphic_probe.py, whose target is CRLF
# where the lock's is LF -- two line-ending regimes, which is the only reason
# the collision showed up at all.
# ── THE LOCK CAUGHT THIS TOOL ON ITS FIRST RUN, AND IT IS WORTH KEEPING ─────
# The sensitive fixture originally read with a plain `io.open(..., encoding=)`
# and the lock refused: `crlf` HELD where it was supposed to be VIOLATED, so
# the relation was UNFALSIFIABLE AS WRITTEN and would have reported a clean
# fleet forever.
#
# The cause is the useful part. Python's text mode does UNIVERSAL NEWLINES: it
# converts CRLF to LF on read, so a checker using the ordinary idiom cannot see
# the difference and is CRLF-immune for free. That is why the whole fleet passes
# `crlf` -- not because anyone hardened it. The relation is still worth having:
# it stops holding the moment a checker reads bytes, passes `newline=''`, or
# shells out to a tool that does. `newline=''` here is what makes the fixture
# able to fail at all.
#
# This is precisely what a blind lock is for, and it fired on the first run
# against the tool that wrote it.

_FIXTURE_ROBUST = '''\
"""A fixture checker that normalises first. Nothing here should fire."""
import io, re, sys
src = io.open(sys.argv[1], encoding="utf-8", errors="replace").read()
norm = re.sub(r"[ \\t]+$", "", src.replace(chr(13) + chr(10), chr(10)), flags=re.M)
norm = re.sub(chr(10) + "{2,}", chr(10), norm)
print("defects: %d" % norm.count("PLANTED_DEFECT"))
sys.exit(1 if "PLANTED_DEFECT" in norm else 0)
'''

_FIXTURE_TARGET = ('<html>\n<body>\n'
                   '<div>ordinary line</div>\n'
                   '<div>PLANTED_DEFECT</div>\n'
                   '</body>\n</html>\n')


def blind_lock():
    """Classify the relations against synthetic fixtures before real data.

    Returns (ok, rows, problems). The sensitive fixture must be caught by every
    SAME relation; the robust one must be caught by none. If either side comes
    out wrong the criteria are not locked and the real measurement is refused --
    a relation that can never fire would report zero violations on the fleet and
    read exactly like a clean fleet.

    `duplicate`/NO_ERASE is asserted separately and in the other direction: the
    sensitive fixture must PASS it (doubling the file keeps the planted defect,
    so the finding survives), which is what proves NO_ERASE is not just SAME
    under another name.
    """
    tmp = tempfile.mkdtemp(prefix='metamorphic_lock_')
    rows, problems = [], []
    try:
        sens = os.path.join(tmp, 'sensitive_fixture_check.py')
        robust = os.path.join(tmp, 'robust_fixture_check.py')
        io.open(sens, 'w', encoding='utf-8').write(_FIXTURE_SENSITIVE)
        io.open(robust, 'w', encoding='utf-8').write(_FIXTURE_ROBUST)
        target = os.path.join(tmp, 'fixture_target.html')
        io.open(target, 'w', encoding='utf-8', newline='').write(_FIXTURE_TARGET)

        for tool_path, label, expect_caught in ((sens, 'sensitive', True),
                                                (robust, 'robust', False)):
            base = run(tool_path, target)
            if base[0] is None:
                problems.append('fixture %s would not run: %s' % (label, base[1]))
                continue
            for name, fn, expectation, _ in RELATIONS:
                # SAME BASENAME, own subdirectory -- see normalise().
                sub = os.path.join(tmp, label, name)
                os.makedirs(sub, exist_ok=True)
                dst = os.path.join(sub, os.path.basename(target))
                io.open(dst, 'w', encoding='utf-8', newline='').write(fn(_FIXTURE_TARGET))
                trans = run(tool_path, dst)
                if trans[0] is None:
                    problems.append('fixture %s/%s would not run: %s'
                                    % (label, name, trans[1]))
                    continue
                holds, why = compare(expectation, base, trans)
                rows.append({'fixture': label, 'relation': name,
                             'holds': holds, 'why': why})
                if name == 'identity':
                    want_hold = True          # identity holds for both fixtures
                elif expectation == NO_ERASE:
                    want_hold = True          # doubling never erases the defect
                else:
                    want_hold = not expect_caught
                if holds != want_hold:
                    problems.append(
                        'LOCK FAILED: %s fixture, relation %s -- expected '
                        '%s, got %s%s'
                        % (label, name,
                           'HOLDS' if want_hold else 'VIOLATED',
                           'HOLDS' if holds else 'VIOLATED',
                           (' (%s)' % why) if why else ''))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return not problems, rows, problems


# ── the real measurement ─────────────────────────────────────────────────────
def app_targets(limit, max_bytes=None):
    """The largest root app files first, plus the names of the ones left out.

    LARGEST FIRST because a relation is a property of the CHECKER, not of the
    file: one target the checker actually produces an answer on is enough to
    falsify a relation, and the biggest files exercise the most of each
    checker's code. The cap is DECLARED and the excluded names are PRINTED --
    a silent top-N reads as "covered everything" when it did not.

    `max_bytes` EXISTS FOR THE REGISTRY AND IT WAS EARNED (2026-09-13).
    Promoting this into tools/report_only_checks.py pushed the whole
    report-only sweep past the 600s budget in its own probe, and the cost is
    almost entirely one file: 6 checkers x 6 runs over stonedesk.html at 2.6MB
    is ~160 seconds on its own, against ~40 for everything else put together.
    So the registry runs with a size cap and the deep pass
    (`--all`, 660 comparisons) stays a deliberate command.

    A CAP IS A COVERAGE CLAIM, so it is printed with the file it excluded
    beside it rather than folded into the NOT COVERED count. A sample that
    quietly skips the biggest app is the truncation shape this platform keeps
    finding.
    """
    out = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO,
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    roots = [f for f in out.split('\n') if f.strip() and '/' not in f]
    roots.sort(key=lambda f: -os.path.getsize(os.path.join(REPO, f)))
    too_big = []
    if max_bytes:
        keep = []
        for f in roots:
            (keep if os.path.getsize(os.path.join(REPO, f)) <= max_bytes
             else too_big).append(f)
        roots = keep
    if limit is None or limit >= len(roots):
        return roots, too_big, []
    return roots[:limit], too_big, roots[limit:]


def measure(targets, checkers=None, tools_dir=None, target_root=None):
    """Compare every checker against every relation on every target.

    `checkers`/`tools_dir`/`target_root` exist so the control probe can drive
    THIS code path with fixture checkers instead of re-implementing it. A probe
    that reimplements the thing it is a control for proves nothing about the
    thing that ships -- the harness reimplementing `sdLoad` is a defect this
    repo has already recorded once.
    """
    checkers = CHECKERS if checkers is None else checkers
    tools_dir = os.path.join(REPO, 'tools') if tools_dir is None else tools_dir
    target_root = REPO if target_root is None else target_root
    rows, could_not_run = [], []
    tmp = tempfile.mkdtemp(prefix='metamorphic_')
    try:
        for tool in checkers:
            tool_path = os.path.join(tools_dir, tool)
            if not os.path.exists(tool_path):
                could_not_run.append('%s: not found in %s' % (tool, tools_dir))
                continue
            for t in targets:
                src = read_raw(os.path.join(target_root, t))
                base = run(tool_path, os.path.join(target_root, t))
                if base[0] is None:
                    could_not_run.append('%s on %s (baseline): %s' % (tool, t, base[1]))
                    continue
                identity_ok = True
                for name, fn, expectation, _ in RELATIONS:
                    if not identity_ok:
                        could_not_run.append(
                            '%s on %s, relation %s: NOT MEASURED -- identity '
                            'failed for this checker, so every other relation '
                            'on it is uninterpretable' % (tool, t, name))
                        continue
                    # SAME BASENAME, own subdirectory. A copy renamed to encode
                    # the relation is what made the harness rewrite a checker's
                    # prose and report a false nondeterminism -- see normalise().
                    sub = os.path.join(tmp, tool[:-3], name)
                    os.makedirs(sub, exist_ok=True)
                    dst = os.path.join(sub, os.path.basename(t))
                    io.open(dst, 'w', encoding='utf-8', newline='').write(fn(src))
                    trans = run(tool_path, dst)
                    if trans[0] is None:
                        could_not_run.append('%s on %s, relation %s: %s'
                                             % (tool, t, name, trans[1]))
                        continue
                    holds, why = compare(expectation, base, trans)
                    rows.append({'checker': tool, 'target': t, 'relation': name,
                                 'expectation': expectation, 'holds': holds,
                                 'why': why, 'exit_base': base[0],
                                 'exit_transformed': trans[0]})
                    if name == 'identity' and not holds:
                        identity_ok = False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return rows, could_not_run


# ═════════════════════════════════════════════════════════════════════════════
# FAMILY 2: REWORDING, OVER VERDICTS THAT ARE JUDGEMENT CALLS   (2026-09-24)
# ═════════════════════════════════════════════════════════════════════════════
# Everything above this line transforms a FILE and asks a CHECKER whether its
# findings moved. That family is about byte-level robustness: line endings,
# whitespace, a second copy. It is the right frame and it is the narrow half.
#
# THIS FAMILY ASKS THE HARDER VERSION OF THE SAME QUESTION. Several tools here
# do not find defects at all -- they GRADE PROSE, and return a judgement:
#
#   testability_gate.classify(sentence)          PASS / a named failure
#   criticality_tier_check.asserts_access_control(cell)   True / False
#   fmea_draft's detectors over a source file    which failure modes fire
#
# NONE OF THOSE HAS AN ORACLE EITHER, and the reason is worse than for a
# checker: there is no correct answer to compare against even in principle,
# because the thing being graded is a judgement somebody made in English. You
# cannot write down the right verdict for 450 requirement sentences, so the
# only thing left is CONSISTENCY -- reword the input in a way that cannot
# change what it MEANS, and assert the verdict did not move.
#
# WHY THIS IS NOT THE SAME AS THE FAMILY ABOVE, said plainly because the two
# look alike from a distance. Those relations perturb the CONTAINER of the
# text -- endings, spacing, position. These perturb its PRESENTATION -- the
# emphasis, the entity spelling, the capitalisation, the final full stop --
# and they are applied to subjects that take no file at all. The tool above
# names "checkers that take no file argument" as out of scope; this is where
# that scope goes, rather than a second tool.
#
# WHAT A VIOLATION HERE ACTUALLY MEANS. If bolding a sentence changes whether
# it is judged testable, the grader is keying on markdown rather than on the
# claim. If flipping `&mdash;` to `—` changes whether a tier row is judged to
# assert an access-control gate, the answer depends on which of two spellings
# of one character the author happened to type -- and this register contains
# BOTH spellings today. That is not a hypothetical failure mode here; the
# entity/character split is the same family as the CRLF-vs-LF one that
# produced three false alarms in a single session on 2026-09-03.
#
# ── A RELATION THAT CANNOT FIRE IS NOT A RELATION THAT HELD ─────────────────
# Most of these transforms are no-ops on most units: a sentence containing no
# HTML entity is unchanged by the entity transform, and comparing a verdict
# with itself will hold forever. Reporting that as a pass is exactly the
# "comparison that can never differ reports zero violations" failure the lock
# above exists to prevent, one level down. So every (subject, unit, relation)
# is classified into THREE outcomes -- HELD, VIOLATED, or NOT APPLICABLE
# because the transform changed nothing -- and the applicable count is printed
# per relation. A relation applicable ZERO times is reported as UNEXERCISED
# and is a coverage gap, never a clean row.


# ── the rewording transforms ─────────────────────────────────────────────────
# Each takes prose and returns prose that MEANS THE SAME THING. That claim is
# the load-bearing part of every relation below, so each one is argued rather
# than listed.

def w_emphasis(text):
    """Wrap in markdown bold. Emphasis is typography, not content.

    Chosen first because this repo's registers are saturated with it: the
    criticality table's evidence cells are half bold, and every grader reading
    them sees the asterisks.
    """
    return '**' + text + '**'


# The entity/character pairs that ACTUALLY APPEAR in this repo's documents,
# read off docs/CRITICALITY-TIERS.md rather than taken from a general HTML
# list. A pair nothing uses would make the transform a no-op everywhere and
# the relation unexercised, which the reporting below would then have to
# explain instead of the pair simply not being here.
_ENTITY_PAIRS = [
    ('&mdash;', '—'),
    ('&ndash;', '–'),
    ('&ldquo;', '“'),
    ('&rdquo;', '”'),
    ('&rsquo;', '’'),
    ('&lsquo;', '‘'),
    ('&amp;', '&'),
    ('&nbsp;', ' '),
    ('&rarr;', '→'),
]


def w_entity(text):
    """Swap every HTML entity for the character it names, or back.

    ONE DIRECTION PER UNIT, decided by what the unit already contains, so the
    transform is never a no-op on a unit that has either spelling. A document
    that mixes both -- and this one does -- gets the entities expanded.
    """
    if any(e in text for e, _ in _ENTITY_PAIRS):
        for ent, ch in _ENTITY_PAIRS:
            text = text.replace(ent, ch)
        return text
    for ent, ch in _ENTITY_PAIRS:
        text = text.replace(ch, ent)
    return text


# AN HTML ENTITY IS CASE-SENSITIVE AND IS THEREFORE NOT PROSE. `&mdash;` is a
# character; `&MDASH;` is six wrong characters. The first version of `w_case`
# upper-cased everything and THE LOCK REFUSED IT on the first run -- the
# normalising fixture disagreed with itself, correctly, because the transform
# had stopped being meaning-preserving. That is the lock doing the one job it
# exists for: a relation whose transform changes MEANING reports violations
# that are real about the transform and false about the grader, which is the
# worst kind of finding a report-only tool can produce.
_ENTITY_TOKEN = re.compile(r'&[A-Za-z][A-Za-z0-9]*;')


def w_case(text):
    """Shout it, leaving entities alone. What a sentence CLAIMS cannot depend
    on its capitalisation.

    The weakest-looking transform and the one most likely to find something:
    a grader built from lower-case keyword lists passes every hand-written
    fixture and fails the first row somebody typed in title case.
    """
    out, last = [], 0
    for m in _ENTITY_TOKEN.finditer(text):
        out.append(text[last:m.start()].upper())
        out.append(m.group(0))
        last = m.end()
    out.append(text[last:].upper())
    return ''.join(out)


def w_spacing(text):
    """Double every run of spaces. Whitespace between words is not content."""
    return re.sub(r'[ ]+', '  ', text)


def w_terminal(text):
    """Add a final full stop, or take one away. Punctuation, not claim."""
    stripped = text.rstrip()
    if not stripped:
        return text
    return stripped[:-1] if stripped.endswith('.') else stripped + '.'


PROSE_RELATIONS = [
    ('emphasis', w_emphasis, 'wrapped in markdown bold'),
    ('entity', w_entity, 'HTML entities <-> the characters they name'),
    ('case', w_case, 'upper-cased'),
    ('spacing', w_spacing, 'every run of spaces doubled'),
    ('terminal', w_terminal, 'a final full stop added or removed'),
]


# ── the subjects ─────────────────────────────────────────────────────────────
# A subject is (name, corpus, verdict, reword, what):
#   corpus()          -> [(label, unit)]  REAL units, read out of the repo
#   verdict(unit)     -> a hashable answer, or raises
#   reword(unit, fn)  -> the unit with fn applied to its PROSE only
#
# THE CORPORA ARE REAL AND THAT IS NOT A PREFERENCE. A rewording relation over
# invented sentences measures the relation, not the grader: hand-written units
# are written in one voice -- the author's -- and the whole class this catches
# is a grader that works on the phrasing its author had in mind. The synthetic
# units live in the blind lock, where they belong, and nowhere else.

def _c_testability():
    """The real requirement sentences, read through the gate's own reader.

    THIS CORPUS IS A GENERATED DOCUMENT, and that is worth saying out loud
    (PR §1.10 -- a computed answer is only as current as its oldest input).
    `docs/traceability-matrix.md` is written by tools/traceability_matrix.py,
    so this subject's corpus moves whenever somebody regenerates it. That is
    the RIGHT behaviour -- the point is to grade what the matrix says today,
    not a snapshot of what it said when this was written -- but it means a
    result here is a statement about one revision of that file, and a
    comparison of two runs across a regeneration is comparing two corpora.

    It is read through `matrix_requirements()` rather than by parsing the
    document again, so this and the gate can never disagree about what counts
    as a requirement.
    """
    import testability_gate as _tg
    return [(str(sec)[:40], text) for sec, text in _tg.matrix_requirements()]


def _v_testability(unit):
    import testability_gate as _tg
    return _tg.classify(unit)[0]


def _c_tier_claim():
    import criticality_tier_check as _ct
    _, rows = _ct.parse()
    # The EVIDENCE cell is the one §2.3's judgement reads.
    return [(r[0], r[5]) for r in rows if str(r[5]).strip()]


def _v_tier_claim(unit):
    import criticality_tier_check as _ct
    return bool(_ct.asserts_access_control(unit))


FMEA_SAMPLE = 12

# FMEA's unit is a FILE, and its prose is the full-line comments inside it.
# Rewording those must not change which failure modes fire -- a detector that
# moves is keying on what somebody wrote ABOUT the code rather than on the
# code. Distinct from comment_sensitivity_check.py, which BLANKS comments and
# owns that relation: blanking removes the text, this preserves its meaning
# and changes only how it reads.
_FULL_LINE_COMMENT = re.compile(r'^(\s*#[ ]?)(.*)$')


def _c_fmea():
    tools = os.path.join(REPO, 'tools')
    if not os.path.isdir(tools):
        return []
    names = sorted(f for f in os.listdir(tools)
                   if f.endswith('.py') and not f.startswith('_'))
    # A DECLARED SAMPLE, not a silent one -- the caller prints what was left
    # out. Capped because this subject reads whole files and the others do not.
    out = []
    for f in names[:FMEA_SAMPLE]:
        try:
            out.append((f, read_raw(os.path.join(tools, f))))
        except OSError:
            continue
    return out


def _v_fmea(unit):
    import fmea_draft as _fd
    return tuple(sorted(
        n for n in dir(_fd)
        if n.startswith('_d_') and _fd.__dict__[n](unit, 'tools/<subject>.py')))


def _r_text(unit, fn):
    return fn(unit)


def _r_comments(unit, fn):
    """Apply the transform to full-line comment TEXT and nothing else.

    LIMITATION, STATED: a `#` line inside a triple-quoted string is reworded
    too, because this does not parse Python. That is acceptable here and
    nowhere else -- such a line is still prose, so the relation's claim
    (rewording prose cannot change which failure modes fire) still holds over
    it. What this must never do is touch CODE, and anchoring on `#` as the
    first non-space character is what guarantees that.
    """
    out = []
    for line in unit.split('\n'):
        m = _FULL_LINE_COMMENT.match(line)
        if m and m.group(2).strip():
            out.append(m.group(1) + fn(m.group(2)))
        else:
            out.append(line)
    return '\n'.join(out)


SUBJECTS = [
    ('testability', _c_testability, _v_testability, _r_text,
     'testability_gate.classify() over the real traceability matrix'),
    ('fmea', _c_fmea, _v_fmea, _r_comments,
     'fmea_draft\'s detectors over tools/, reworded in the comments only'),
]

# ── AN EXCLUSION IS A DECISION WITH A REASON, NEVER A SILENCE ───────────────
# The same two-list discipline testability_gate.py uses for its own DECLARED
# set, and it is here because the first version of this family MEASURED the
# subject below and reported five clean relations over 388 units.
#
# `criticality_tier_check.asserts_access_control` answers False on ALL 388
# evidence cells -- correctly. The §2.3 migration is complete and no row
# asserts an access-control gate today. A grader that returns the same value
# on every input is invariant under every transform there is, so those 1940
# comparisons held for a reason that has nothing to do with the grader being
# robust to rewording. Counting them would have inflated the headline by more
# than the two real subjects put together.
#
# IT IS EXCLUDED RATHER THAN LEFT IN AS A PERMANENT COULD-NOT-RUN because the
# degeneracy is STRUCTURAL, not temporary: the check exists to refuse a claim
# nobody makes any more. A subject that can never be non-degenerate is a bad
# subject, and a tool that exits 2 for ever teaches its readers that 2 means
# nothing -- which is the one thing a three-state contract cannot survive.
#
# THE TRIGGER THAT WOULD BRING IT BACK, so this is a decision and not a
# deletion: if `criticality_tier_check` ever reports a non-zero
# ROWS_STILL_ASSERTING_A_GATE, the corpus has positive instances again and
# this subject becomes measurable. The degeneracy detector in measure_prose()
# stays armed for every subject regardless, so one that goes constant in the
# future is caught rather than trusted.
DECLARED_UNMEASURABLE = [
    ('tier_claim',
     'criticality_tier_check.asserts_access_control() over the register\'s '
     'evidence cells',
     'DEGENERATE BY CONSTRUCTION -- False on all 388 cells because the two-axis '
     'migration completed and no row asserts a gate. Restore when '
     'ROWS_STILL_ASSERTING_A_GATE is non-zero.'),
]


# ── the blind lock for THIS family ───────────────────────────────────────────
# Same discipline as the lock above and a separate lock, because these are
# different criteria over different subjects and one lock covering both would
# be a pass borrowed from work that was not done.
#
# TWO SYNTHETIC GRADERS, in opposite directions. The SENSITIVE one answers
# with a hash of the raw text, so EVERY relation must be violated on a unit it
# can change -- if one is not, that relation cannot fire and its zero
# violations over the real corpus mean nothing. The NORMALISING one strips
# emphasis, entities, case, space runs and the final stop before answering, so
# NO relation may fire -- without it the lock is satisfied by a harness that
# reports everything as violated.
_LOCK_UNITS = [
    'the retry budget &mdash; three attempts &mdash; is exhausted.',
    '**The gate REFUSES** when the roster is empty',
    'a wrong invoice is hidden rather than destroyed',
]


def _lock_sensitive(text):
    import hashlib
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:12]


def _lock_normalising(text):
    t = text.replace('**', '')
    for ent, ch in _ENTITY_PAIRS:
        t = t.replace(ent, ch)
    t = re.sub(r'[ ]+', ' ', t).strip().lower()
    return t[:-1] if t.endswith('.') else t


def prose_lock():
    """(locked, rows, problems). A failed lock REFUSES the real run."""
    rows, problems = [], []
    for rel, fn, _ in PROSE_RELATIONS:
        fired_on = 0
        for unit in _LOCK_UNITS:
            moved = fn(unit)
            if moved == unit:
                continue
            fired_on += 1
            if _lock_sensitive(moved) == _lock_sensitive(unit):
                problems.append('%s: the sensitive fixture AGREED with itself '
                                'on %r -- the transform changed the text and '
                                'the verdict did not move, so this relation '
                                'cannot fire' % (rel, unit[:40]))
            if _lock_normalising(moved) != _lock_normalising(unit):
                problems.append('%s: the normalising fixture DISAGREED with '
                                'itself on %r -- so this relation reports a '
                                'violation against a grader that correctly '
                                'ignores the transform' % (rel, unit[:40]))
        rows.append({'relation': rel, 'applicable_units': fired_on,
                     'of': len(_LOCK_UNITS)})
        if not fired_on:
            problems.append('%s: changed NONE of the %d lock units, so it is '
                            'unfalsifiable here and its result over the real '
                            'corpus would be zero violations either way'
                            % (rel, len(_LOCK_UNITS)))
    return (not problems), rows, problems


# ── the measurement ──────────────────────────────────────────────────────────
def measure_prose(subject_names=None, per_subject=0):
    """(rows, could_not_run, distributions).

    Every row is one (subject, unit, relation). `distributions` carries the
    number of DISTINCT verdicts each subject's grader produced over its own
    corpus, because that number is what decides whether the rows mean
    anything -- see the degeneracy block below.
    """
    rows, could_not_run, distributions = [], [], []
    for name, corpus_fn, verdict_fn, reword_fn, _what in SUBJECTS:
        if subject_names and name not in subject_names:
            continue
        try:
            corpus = corpus_fn()
        except Exception as e:                       # noqa: BLE001
            could_not_run.append('%s: corpus could not be read -- %s: %s'
                                 % (name, type(e).__name__, e))
            continue
        if not corpus:
            could_not_run.append('%s: the corpus is EMPTY, so nothing was '
                                 'graded. That is not a clean subject.' % name)
            continue
        if per_subject:
            corpus = corpus[:per_subject]
        # ── A CONSTANT GRADER IS INVARIANT UNDER EVERYTHING ────────────────
        # Found on the first real run, and it is the whole reason this block
        # exists rather than a distribution printed for interest.
        # `asserts_access_control` returned False on ALL 388 evidence cells --
        # correctly, the §2.3 migration is complete and no row asserts a gate
        # today -- so every relation over that subject held for a reason that
        # has nothing to do with the grader being robust. A function that
        # answers the same thing every time cannot fail an invariance test.
        #
        # THAT IS A COULD-NOT-TELL, NOT A PASS (PR §1.11), so it goes in the
        # could-not-run list and the subject's rows are dropped rather than
        # counted as held. A degenerate subject reported as clean is the exact
        # shape this tool exists to refuse, committed by this tool.
        # KEYED BY POSITION, NOT BY LABEL, and that is not a style choice.
        # The first version of this block built `{label: verdict}` -- and the
        # testability corpus labels units by their MATRIX SECTION, so 450
        # requirements share about ten labels. Every unit but the last in each
        # section got compared against a DIFFERENT requirement's verdict, and
        # the tool reported 1184 violations that did not exist. It looked like
        # a spectacular finding about testability_gate and was a dictionary
        # collision in the harness. Every prior defect this file records was
        # also a confidently wrong verdict rather than an error; this is the
        # fifth.
        verdicts, bases = set(), [None] * len(corpus)
        for i, (label, unit) in enumerate(corpus):
            try:
                bases[i] = (True, verdict_fn(unit))
                verdicts.add(repr(bases[i][1]))
            except Exception as e:                   # noqa: BLE001
                could_not_run.append('%s/%s: the grader raised on the ORIGINAL '
                                     '-- %s: %s' % (name, label, type(e).__name__, e))
        if len(verdicts) <= 1:
            could_not_run.append(
                '%s: DEGENERATE -- the grader returned %s on all %d unit(s) of '
                'its corpus, so every relation over it holds vacuously. '
                'Invariance under rewording says nothing about a constant '
                'function. NOTHING was measured for this subject.'
                % (name, (list(verdicts) or ['nothing'])[0][:40], len(corpus)))
            distributions.append({'subject': name, 'units': len(corpus),
                                  'distinct_verdicts': len(verdicts),
                                  'degenerate': True})
            continue
        distributions.append({'subject': name, 'units': len(corpus),
                              'distinct_verdicts': len(verdicts),
                              'degenerate': False})
        for i, (label, unit) in enumerate(corpus):
            if bases[i] is None:
                continue
            base = bases[i][1]
            for rel, fn, _why in PROSE_RELATIONS:
                moved = reword_fn(unit, fn)
                if moved == unit:
                    rows.append({'subject': name, 'unit': label,
                                 'relation': rel, 'applicable': False,
                                 'holds': None, 'why': 'the transform '
                                 'changed nothing on this unit'})
                    continue
                try:
                    after = verdict_fn(moved)
                except Exception as e:               # noqa: BLE001
                    could_not_run.append(
                        '%s/%s relation %s: the grader raised on the REWORDED '
                        'unit but not on the original -- %s: %s'
                        % (name, label, rel, type(e).__name__, e))
                    continue
                holds = (after == base)
                rows.append({'subject': name, 'unit': label, 'relation': rel,
                             'applicable': True, 'holds': holds,
                             'why': '' if holds else '%r -> %r'
                                    % (base, after)})
    return rows, could_not_run, distributions


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--fixtures', action='store_true',
                    help='run the blind lock alone and stop')
    ap.add_argument('--all', action='store_true',
                    help='every root app file, not the declared sample')
    ap.add_argument('--targets', type=int, default=3,
                    help='how many of the largest app files to measure (default 3)')
    ap.add_argument('--max-bytes', type=int, default=0,
                    help='skip app files larger than this; PRINTED, never silent. '
                         'The registry uses it because stonedesk.html alone is '
                         '~160s of a ~200s run.')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--prose', action='store_true',
                    help='the REWORDING family alone -- verdicts that are '
                         'judgement calls, not checkers over files')
    ap.add_argument('--no-prose', action='store_true',
                    help='the file-transform family alone. PRINTED, never '
                         'silent: a family that did not run is an unknown.')
    args = ap.parse_args(argv)
    quiet = args.quiet
    if args.prose and args.no_prose:
        print('--prose and --no-prose are opposites. Pick one, or neither '
              'for both families.')
        return EXIT_COULD_NOT_RUN
    if args.prose:
        return _prose_main(args, quiet)

    locked, lock_rows, lock_problems = blind_lock()

    if not quiet and not args.json:
        print('METAMORPHIC RELATIONS -- report only')
        print('  does a checker\'s answer survive a change that cannot change '
              'the answer?')
        print('  relations: %s' % ', '.join(n for n, _, _, _ in RELATIONS))
        print('  NOT OWNED HERE, and not re-implemented: comment blanking '
              '(tools/comment_sensitivity_check.py)')
        print('                                          repeated runs '
              '(tools/flaky_checker_quarantine.py)')
        print('  blind lock: %s  (%d fixture comparisons)'
              % ('LOCKED' if locked else 'FAILED', len(lock_rows)))

    if not locked:
        if args.json:
            print(json.dumps({'locked': False, 'lock_problems': lock_problems,
                              'lock_rows': lock_rows}, indent=1))
        elif not quiet:
            print('\nTHE CRITERIA ARE NOT LOCKED, so nothing real was measured.')
            print('A relation that cannot fire reports zero violations on the '
                  'fleet and reads exactly like a clean fleet.')
            for p in lock_problems:
                print('  ? %s' % p)
        return EXIT_COULD_NOT_RUN

    if args.fixtures:
        if args.json:
            print(json.dumps({'locked': True, 'lock_rows': lock_rows}, indent=1))
        elif not quiet:
            print('\n--- the lock ---')
            for r in lock_rows:
                print('  %-10s %-12s %s' % (r['fixture'], r['relation'],
                                            'holds' if r['holds'] else 'VIOLATED'))
            print('\nLocked. The sensitive fixture is caught by every SAME '
                  'relation and the robust one by none, so a violation below '
                  'would mean something.')
        return 0

    targets, too_big, skipped = app_targets(
        None if args.all else args.targets, args.max_bytes or None)
    rows, could_not_run = measure(targets)
    violations = [r for r in rows if not r['holds']]

    if args.json:
        print(json.dumps({'locked': True, 'lock_rows': lock_rows,
                          'targets': targets, 'not_covered': skipped,
                          'over_size_cap': too_big,
                          'max_bytes': args.max_bytes or None,
                          'comparisons': rows,
                          'could_not_run': could_not_run}, indent=1))
        return EXIT_COULD_NOT_RUN if could_not_run else (1 if violations else 0)

    if not quiet:
        print('  checkers under test : %d  (those taking the file as argv[1])'
              % len(CHECKERS))
        print('  targets measured    : %d  -- %s'
              % (len(targets), ', '.join(targets)))
        # PRINTED, NEVER SILENT. A declared cap that nobody sees is a silent one.
        print('  NOT COVERED         : %d app file(s)%s'
              % (len(skipped),
                 (' -- ' + ', '.join(skipped)) if skipped else ''))
        # A SIZE CAP IS A COVERAGE CLAIM. Printed separately from the top-N
        # exclusion above, because "we sampled 1 of 22" and "we skipped the
        # biggest app in the fleet" are different things to know.
        if too_big:
            print('  OVER THE %d-BYTE CAP, NOT MEASURED AT ALL : %s'
                  % (args.max_bytes, ', '.join(too_big)))
            print('    run `python tools/metamorphic_check.py --all` for the '
                  'deep pass that includes them')
        print('  comparisons run     : %d' % len(rows))
        print('  relations violated  : %d' % len(violations))
        by_checker = {}
        for r in rows:
            by_checker.setdefault(r['checker'], []).append(r)
        print('')
        for tool in CHECKERS:
            rs = by_checker.get(tool, [])
            bad = [r for r in rs if not r['holds']]
            print('  %-26s %2d compared, %d violated%s'
                  % (tool, len(rs), len(bad),
                     '' if rs else '   (nothing measured -- see COULD NOT RUN)'))

    findings = ['%s on %s, relation %s (%s): %s'
                % (r['checker'], r['target'], r['relation'],
                   r['expectation'], r['why'])
                for r in violations]

    # ── THE SECOND FAMILY, UNLESS IT WAS TURNED OFF OUT LOUD ──────────────
    if args.no_prose:
        if not quiet and not args.json:
            print('\n  REWORDING FAMILY: NOT RUN (--no-prose). That is an '
                  'UNKNOWN about the graders, not a clean result for them.')
    else:
        p_findings, p_cnr = _prose_report(quiet or args.json)
        findings = findings + p_findings
        could_not_run = could_not_run + p_cnr

    return finish(
        findings, could_not_run, quiet=quiet,
        clean_line='\nCLEAN -- every relation held on every comparison run. '
                   'That is a statement about the relations in the tables '
                   'above and the targets named above, not about the fleet.')


def _prose_report(silent):
    """Run the rewording family and print it. Returns (findings, could_not_run).

    SPLIT OUT OF main() so the two families can be run separately without a
    second copy of the reporting -- `--prose` calls this and stops, the
    default run calls it after the file family and adds its findings to the
    same finish(). Two report blocks for one measurement is how the counts in
    a summary stop agreeing with the counts in the detail.
    """
    locked, lock_rows, lock_problems = prose_lock()
    if not silent:
        print('')
        print('REWORDING RELATIONS -- does a JUDGEMENT-CALL verdict survive a '
              'rewording that cannot change what the text means?')
        print('  relations: %s' % ', '.join(n for n, _, _ in PROSE_RELATIONS))
        print('  subjects : %s' % ', '.join(n for n, _, _, _, _ in SUBJECTS))
        for nm, _what, why in DECLARED_UNMEASURABLE:
            print('  DECLARED UNMEASURABLE: %s -- %s' % (nm, why))
        print('  blind lock: %s  (%d relation(s) locked)'
              % ('LOCKED' if locked else 'FAILED', len(lock_rows)))
    if not locked:
        if not silent:
            print('\n  THE REWORDING CRITERIA ARE NOT LOCKED, so no grader was '
                  'measured. A transform that changes MEANING reports '
                  'violations that are true about itself and false about the '
                  'grader, which is the worst finding a report-only tool can '
                  'produce.')
            for pr in lock_problems:
                print('    ? %s' % pr)
        return [], ['the rewording blind lock FAILED, so NOTHING in that '
                    'family was measured: ' + '; '.join(lock_problems)]

    rows, cnr, dists = measure_prose()
    applicable = [r for r in rows if r['applicable']]
    bad = [r for r in applicable if not r['holds']]
    if not silent:
        for d in dists:
            print('  %-12s %4d unit(s), %d distinct verdict(s)%s'
                  % (d['subject'], d['units'], d['distinct_verdicts'],
                     '   <-- DEGENERATE, measured nothing'
                     if d['degenerate'] else ''))
        print('  comparisons applicable : %d of %d  (%d were no-ops on their '
              'own unit and are NOT counted as held)'
              % (len(applicable), len(rows), len(rows) - len(applicable)))
        for rel, _fn, _why in PROSE_RELATIONS:
            n = len([r for r in applicable if r['relation'] == rel])
            v = len([r for r in bad if r['relation'] == rel])
            print('    %-9s %5d applicable, %d violated%s'
                  % (rel, n, v,
                     '   <-- UNEXERCISED, a coverage gap rather than a pass'
                     if not n else ''))
    return (['%s/%s, rewording %s: the verdict MOVED -- %s'
             % (r['subject'], r['unit'], r['relation'], r['why'])
             for r in bad], cnr)


def _prose_main(args, quiet):
    findings, cnr = _prose_report(quiet or args.json)
    if args.json:
        _rows, _c2, dists = measure_prose()
        print(json.dumps({'family': 'rewording', 'findings': findings,
                          'could_not_run': cnr, 'distributions': dists},
                         indent=1))
    return finish(findings, cnr, quiet=quiet,
                  clean_line='\nCLEAN -- every applicable rewording held. That '
                             'is a statement about the relations, subjects and '
                             'corpora named above, not about every judgement '
                             'this platform makes.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
