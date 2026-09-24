"""temporary_state_check.py -- state meant to be temporary, with no declared scope.

    python tools/temporary_state_check.py
    python tools/temporary_state_check.py --json
    python tools/temporary_state_check.py --check

── ITEM 34, AND WHY THE DECLARATION COMES FIRST ──────────────────────────
Three real instances now, three different substrates, one shape:

  * a probe wrote `user.name = probe@local` into a clone's PERSISTENT git
    config instead of passing `-c` per command. 131 real commits on origin/main
    were then authored by a test identity.
  * `sdSyncSuppressed = true` was set during hydration with no `finally`, so a
    throw mid-hydration left every later server write silenced FOR THE WHOLE
    SESSION, and the surrounding `.catch` swallowed the throw. This one is NOT
    historical: the shape is live in `stonedesk.html` at 2286/2299 and 6350 as
    of 2026-09-14 -- set true, call `st(...)`, set false, no `finally`.
  * (2026-09-24, the third, and the reason shape 3 below exists) a MUTATION
    HARNESS writes a change into a live tracked file, runs a suite, and writes
    the original back -- with nothing guaranteeing the second write runs. The
    sabotage-control work produces one of these ad hoc almost daily, each
    carrying the same three lines of discipline by hand (dirty-check,
    finally-restore, git-diff verify), and nothing noticed when one did not.
    The residue is a REAL EDIT to a REAL file, indistinguishable from work.

All three are: **something set on the way in, meant to come off on the way
out, and nothing that guarantees it does.**

**A CHECKER CANNOT TELL A LEAKED FLAG FROM A DELIBERATELY LONG-LIVED ONE.** A
session token with a long expiry, an hours-long cache, a feature switch read at
boot -- all look identical to the leak above. Any detector that guesses will
either flood the report with legitimate state or stay silent to avoid it.

**So the requirement is the declaration, not the detection.** "Meant to be
temporary" has to become a written, checkable claim at the point the state is
set -- item 3/33's falsifiable-requirement discipline applied to lifetime. What
this tool reports is state that LOOKS temporary and DECLARES NOTHING.

── THE DECLARATION ───────────────────────────────────────────────────────
A comment on, or immediately above, the line that sets the state:

    // TEMPORARY-STATE: scope=<one of the words below> released-by=<how>

    scope=command    lives for one subprocess invocation (git -c ...)
    scope=call       lives for one function call (try/finally)
    scope=request    lives for one HTTP request
    scope=session    lives until the page or process ends -- DELIBERATE
    scope=persistent not temporary at all; declared so it stops being reported

`released-by` is free text and is not verified: naming the mechanism is what
makes a wrong claim visible to a reader, and a checker that tried to verify it
would be guessing again.

── WHAT IT REPORTS, AND THE HONEST DIRECTION OF ITS ERROR ────────────────
UNDECLARED is a READ-LIST, not a defect count. Most entries will be fine. The
tool over-reports on purpose: a legitimate long-lived flag costs one declaration
line, and a missed leak costs 131 misattributed commits.

── WHAT IT CANNOT SEE, NAMED RATHER THAN IMPLIED ─────────────────────────
  * The flag shape matches lowercase `= true;` only, so PYTHON state -- `flag
    = True` -- is invisible to it. Python files are scanned for the git-config
    shape and for nothing else. This is a real gap, not a hedge, and
    tests/run_temporary_state_probe.py section G asserts it stays true so the
    sentence cannot quietly become false.
  * A flag set through a computed name, state held in a database or in
    localStorage, and anything set inside a library.
  * `released-by` is free text and is NOT verified.

── WHY --check FAILS ON SO LITTLE ────────────────────────────────────────
The bare run prints a read-list and exits 0 whatever it finds, so inside a
runner that is silent on a clean run it would never say anything at all -- the
failure two other report-only tools on this platform were registered to avoid.

`--check` therefore fails on ONE thing, and it is not the count: a declaration
naming a scope that does not exist. That is an objective defect -- the comment
claims a lifetime the vocabulary has no word for, so no reader and no tool can
act on it -- and it needs no threshold and no policy. The UNDECLARED count is
printed on every run and gates NOTHING, because choosing a number for it would
be exactly the guess this tool was built to refuse.

REPORT ONLY. Exit 0 with findings, 2 when it could not look. With `--check`,
exit 1 when a declaration names an unknown scope.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import jscomments                                             # noqa: E402

SCOPES = ('command', 'call', 'request', 'session', 'persistent')
DECL = re.compile(r'TEMPORARY-STATE:\s*scope=([a-z]+)\s+released-by=(\S.*)', re.I)

# Shape 1: a boolean-ish module or file scope flag being switched ON.
#
# `[ \t]*` AND NOT `\s*`, FIXED 2026-09-14. `\s` matches a newline, so under
# re.M the leading `^\s*` would start the match at the first line of a
# whitespace run and swallow every blank line down to the assignment. Comments
# are BLANKED TO SPACES before this runs, so a 20-line comment block above the
# assignment became 20 lines of whitespace and the reported line number was the
# top of the COMMENT, not the assignment: sairnvet.html:2396 was reported as
# :2376. It also made the declaration window (comment, +1, +2) line up by
# accident rather than by construction. Found by the probe's section F after it
# was re-aimed to compute the truth independently instead of trusting a proxy.
FLAG_ON = re.compile(r'^[ \t]*([A-Za-z_$][\w$.]*)\s*=\s*true\s*;', re.M)
# Shape 2: a persistent git config write -- the substrate of the 131-commit leak.
# Two spellings: an argv token (`['git', 'config', ...]`) and a shell string
# (`git config user.email ...`). The argv token is deliberately CASE-SENSITIVE
# and additionally requires a `git` word within GIT_NEAR characters before it:
# a bare case-insensitive /config/ matched `storeError('CONFIG', ...)` in
# api/_lib/sd-store.js, which has nothing to do with git.
GIT_CONFIG = re.compile(r"""['"]config['"]\s*,|\bgit\s+config\s+(?!--get)""")
GIT_NEAR = 100

# Shape 3: a probe that MUTATES A TRACKED FILE with no `finally` anywhere in
# it -- the third real instance of this class (2026-09-24), after the git
# identity and the suppression flag. A mutation harness writes a change into a
# live source file, runs a suite, and writes the original back; the restore is
# the released-by, and when it is not in a `finally` the mutation persists the
# moment anything between the two writes raises. This repo's own words:
# "a probe which edits tracked files is indistinguishable from residue when it
# dies" -- and the residue is a REAL EDIT to a REAL file, the worst possible
# thing to leak. Found generalising the sabotage-control work of 2026-09-24,
# where every ad-hoc mutation script had to carry the same three lines of
# discipline by hand (dirty-check, finally-restore, git-diff verify) and
# nothing noticed when one did not.
#
# THE PROXY IS DELIBERATELY PER-FILE AND DELIBERATELY WEAK, in the same way
# and for the same reason as the flag proxy above: whether a given write is
# the mutation or the restore, and whether the control flow between them can
# raise, is not derivable by regex. What IS derivable: this file (a) writes in
# 'w' mode to a path it did not just create under tempfile, and (b) contains
# no `finally` at all. A file with even one `finally` is assumed to have
# thought about it -- over- and under-reporting both possible, both accepted,
# because the declaration is still the requirement and this is the read-list.
PY_WRITE = re.compile(r"""\bio\.open\([^)\n]*,\s*['"]w b?['"]""".replace('w b', 'wb?'))
PY_WRITE = re.compile(r"""\b(?:io\.)?open\(\s*[^)\n]*,\s*['"]wb?['"]""")
JS_WRITE = re.compile(r"""\bfs\.writeFileSync\(""")
TEMP_MARKS = ('tempfile', 'mkdtemp', 'TemporaryDirectory', 'tmpdir', 'os.tmpdir',
              'scratch')
MUTATE_INTENT = re.compile(r'restor|mutat|sabotag|revert|put back|byte-identical',
                           re.I)

SKIP_DIRS = ('node_modules', '.git', 'archive', 'dist', 'docs')


def sources():
    out = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for f in files:
            if f.endswith('.js') or f.endswith('.html') or f.endswith('.py'):
                out.append(os.path.relpath(os.path.join(root, f), REPO).replace(os.sep, '/'))
    return sorted(out)


def declared_lines(raw):
    """Line numbers covered by a declaration: the comment's own line and the next."""
    covered, bad = set(), []
    for i, line in enumerate(raw.split('\n'), 1):
        m = DECL.search(line)
        if not m:
            continue
        if m.group(1).lower() not in SCOPES:
            bad.append((i, m.group(1)))
            continue
        covered.add(i)
        covered.add(i + 1)
        covered.add(i + 2)
    return covered, bad


def findings_for(rel, raw):
    code = jscomments.strip_comments(raw) if not rel.endswith('.py') else raw
    covered, bad_scope = declared_lines(raw)
    out = []
    for m in FLAG_ON.finditer(code):
        line = code[:m.start()].count('\n') + 1
        name = m.group(1)
        # A local `var x = true` inside a function is not module state; the
        # cheap proxy is that leaked flags are referenced somewhere else too.
        if code.count(name) < 3:
            continue
        if line in covered:
            continue
        out.append({'file': rel, 'line': line, 'shape': 'flag-on', 'what': name})
    if rel.endswith('.py') or rel.endswith('.js'):
        for m in GIT_CONFIG.finditer(code):
            line = code[:m.start()].count('\n') + 1
            if line in covered:
                continue
            before = code[max(0, m.start() - GIT_NEAR):m.start()]
            if m.group(0).startswith(("'", '"')) and not re.search(r'\bgit\b', before):
                continue
            seg = before[-120:] + code[m.start():m.start() + 160]
            if '--get' in seg or '--unset' in seg or "'-c'" in seg:
                continue
            out.append({'file': rel, 'line': line, 'shape': 'git-config-write',
                        'what': 'persistent git config'})
    # Shape 3 binds to PROBES AND TOOLS only. An app or an endpoint writing a
    # file is its job; a test writing one is a mutation that had better come
    # back. One finding per file -- the first uncovered write -- because the
    # unit of the defect is "this harness has no finally", not each write.
    if rel.startswith(('tests/', 'tools/')) and (rel.endswith('.py') or rel.endswith('.js')):
        # THE PROXY WAS NARROWED TWICE ON MEASUREMENT, and both cuts are
        # recorded because each one is a stated blind spot:
        #   v1: any 'w'-mode write with no tempfile within 200 chars -- 74
        #       files, because a harness makes its tempdir at the top and
        #       writes to it hundreds of lines later. Noise.
        #   v2: tempdir detected at FILE level -- 38 files, still mostly
        #       generators and registers, whose single permanent write is
        #       their JOB and not temporary state at all.
        #   v3 (shipped): the signal for MEANT-to-be-temporary is the file's
        #       own vocabulary. A mutation harness writes at least TWICE
        #       (mutate, restore) and says so -- restore/mutate/sabotage/
        #       revert. A file that writes twice, says restore, and has no
        #       `finally` is precisely the harness whose mutation persists
        #       the moment anything between the two writes raises.
        # WHAT v3 CANNOT SEE, stated: a harness that never uses the
        # vocabulary, and one that spreads mutate/restore across two files.
        # Measured against this repo the day it shipped: ONE finding
        # (tools/sabotage_control_check.py, 18 writes, no finally), which is
        # a real instance and not a tuned-to-zero result.
        # A QUOTED WRITE IS NOT A WRITE, and this was not caution -- it was
        # the first thing the shape got wrong. Run raw, its single repo
        # finding was tools/sabotage_control_check.py "18 writes, no finally":
        # every one of the eighteen was a write pattern QUOTED in that tool's
        # docstrings and probe fixtures, because analysing write patterns is
        # that tool's SUBJECT. PR 1.2 -- text that describes code is not code
        # -- committed by the detector whose sibling shapes each carry their
        # own version of the same scar.
        #
        # The regex cannot simply run on a string-blanked copy, because the
        # thing it matches CONTAINS a string (the 'w' mode) that blanking
        # erases. So it matches on the RAW text and each match is kept only if
        # its `open`/`fs` token SURVIVES string-blanking at the same offset --
        # a token inside a docstring or fixture string is blanked there, a
        # real call is not. Offsets line up because strip_comments preserves
        # them by contract.
        try:
            import checker_kit
            code3 = checker_kit.strip_comments(raw, strings=True)
        except Exception:                            # noqa: BLE001
            code3 = None
        has_finally = re.search(r'\bfinally\b', code) is not None
        uses_temp = any(t in code for t in TEMP_MARKS)
        if code3 is not None and not has_finally and not uses_temp:
            wr = PY_WRITE if rel.endswith('.py') else JS_WRITE
            writes = [m for m in wr.finditer(code)
                      if code3[m.start():m.start() + 4] == code[m.start():m.start() + 4]]
            if len(writes) >= 2 and MUTATE_INTENT.search(code):
                lines = [code[:m.start()].count('\n') + 1 for m in writes]
                # ONE declaration anywhere on the harness's writes covers the
                # FILE, because the finding is per-file: the declaration says
                # "this mutation is deliberate and here is how it comes back",
                # and demanding it on every write of one harness would be
                # punctuation, not information.
                if not any(l in covered for l in lines):
                    out.append({'file': rel, 'line': lines[0],
                                'shape': 'tracked-write-no-finally',
                                'what': '%d writes, restore vocabulary, no finally'
                                        % len(writes)})
    return out, bad_scope


def main(argv):
    files = sources()
    if not files:
        print('COULD NOT CHECK: no source files found. ZERO TARGETS IS NOT A '
              'CLEAN SWEEP.')
        return 2
    rows, bad_scopes, declared = [], [], 0
    for rel in files:
        p = os.path.join(REPO, rel.replace('/', os.sep))
        try:
            raw = io.open(p, encoding='utf-8', errors='replace').read()
        except IOError:
            continue
        if 'TEMPORARY-STATE:' in raw:
            declared += len(DECL.findall(raw))
        f, bs = findings_for(rel, raw)
        rows.extend(f)
        bad_scopes.extend([(rel, i, s) for i, s in bs])

    if '--json' in argv:
        print(json.dumps({'undeclared': rows, 'declarations': declared,
                          'bad_scopes': bad_scopes}, indent=1))
        return 0

    if '--check' in argv:
        print('TEMPORARY STATE --check : %d declaration(s) over %d files, '
              '%d undeclared candidate(s) (NOT gated)'
              % (declared, len(files), len(rows)))
        if not bad_scopes:
            return 0
        print('  A DECLARATION WITH AN UNKNOWN SCOPE IS NOT A DECLARATION:')
        for rel, i, s in bad_scopes:
            print('    %s:%d  scope=%r is not one of %s'
                  % (rel, i, s, ', '.join(SCOPES)))
        return 1

    print('TEMPORARY STATE -- report only, nothing was written')
    print('  files read                    : %d' % len(files))
    print('  declarations found            : %d' % declared)
    print('  UNDECLARED candidates         : %d' % len(rows))
    print('')
    if bad_scopes:
        print('  A DECLARATION WITH AN UNKNOWN SCOPE IS NOT A DECLARATION:')
        for rel, i, s in bad_scopes:
            print('    %s:%d  scope=%r is not one of %s' % (rel, i, s, ', '.join(SCOPES)))
        print('')
    by = {}
    for r in rows:
        by.setdefault(r['shape'], []).append(r)
    for shape in sorted(by):
        print('  %s (%d)' % (shape, len(by[shape])))
        for r in by[shape][:12]:
            print('    %-46s :%-5d %s' % (r['file'][:46], r['line'], r['what'][:28]))
        if len(by[shape]) > 12:
            print('    ... and %d more' % (len(by[shape]) - 12))
        print('')
    print('  THIS IS A READ-LIST AND ITS COUNT IS NOT A SCORE. Most entries are')
    print('  fine. The tool over-reports ON PURPOSE: a legitimate long-lived')
    print('  flag costs ONE declaration line, and a missed leak cost 131')
    print('  misattributed commits on origin/main.')
    print('')
    print('  IT CANNOT SEE a flag set through a computed name, state held in a')
    print('  database or localStorage, or anything set by a library. And a')
    print('  declaration is a CLAIM -- `released-by` is free text and is not')
    print('  verified, because a checker that tried would be guessing again.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
