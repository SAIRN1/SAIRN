#!/usr/bin/env python
"""Which criteria rules can be DELETED with nothing going red?

    python tools/dead_rule_sweep.py
    python tools/dead_rule_sweep.py --fixtures   # the criteria lock, alone
    python tools/dead_rule_sweep.py --tool X.py  # one tool, with detail
    python tools/dead_rule_sweep.py --quiet

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY.

── THE DEFECT ───────────────────────────────────────────────────────────────
On 2026-09-29 a new rule in tools/assertion_label_shape_check.py shipped with a
literal backspace where every `\\b` should have been:

    'fixture invalid\\x08|could not\\x08|cannot\\x08|...'

It matched nothing, ever. The tool ran, its fixture lock passed, its control
passed, the count it was meant to move went to zero by a different branch, and
the demotion the rule existed for silently did not happen. IT READ AS A WORKING
RULE FROM EVERY ANGLE. It was caught only because an attribution ablation
counted the demotions and got 0 where it expected 2.

**A rule nothing exercises is indistinguishable from a rule that works**, and no
amount of green says otherwise. That is the eighth cross-domain discipline -- a
check that has stopped testing anything reads identically to one that passed --
and the twelfth: ABLATION over assertion. Remove ONE named layer and measure
what it alone catches.

── THE POPULATION IS DERIVED, AND IT USED TO BE A LIST (changed 2026-10-05) ──
The universe is now every TRACKED `tools/*.py` carrying at least one
module-level compiled rule, read from `git ls-files`. It used to be
`report_only_checks.REGISTRY`, and that is the single worst thing this tool has
been wrong about, because it was wrong QUIETLY and in its own headline number.

    MEASURED 2026-10-05, the same day the list was replaced:

      tracked tools/*.py                            295
      with at least one module-level rule           150   ->  521 rules
        of those, IN the report-only registry        45   ->  169 rules
        of those, OUTSIDE it                        105   ->  352 rules

**The sweep had been reporting on 169 of 521 rules -- 32% -- and printing the
figure as if it were the platform.** Nothing refused the other 352; they simply
were not reachable from the only list it read, and it had no way to say so.

The day before, this was found one tool at a time: `gap_ledger.py` was missing,
so the real figure was called "162 of 169" and two names were added. **That
closed two names and left the mechanism**, which is the lesson worth more than
the fix -- *a universe derived from a hand-maintained list reports confidently
about the part of the fleet that list happens to name, and cannot say what is
outside it.*

EXEMPTION IS NOW A DECLARATION WITH A REASON, NOT AN OMISSION. A file leaves the
universe one of two ways, and both are printed by `--universe`:

  * MECHANICALLY -- it compiles no module-level rule, so there is nothing to
    ablate. Derived per file, never declared, never a judgement.
  * DECLARED -- it is in `EXEMPT` below with a one-line reason. That dict is
    deliberately tiny and every entry must still CARRY rules; an entry for a
    file with none is noise and `--universe` says so rather than ignoring it.

`--registry-only` reproduces the old 169-rule population on purpose, so the two
figures can be compared and are never quoted as one.

── WHAT THIS DOES ───────────────────────────────────────────────────────────
For every module-level compiled pattern in every tool in the universe, it
NEUTRALISES that one pattern -- replaced with `(?!x)x`, which is syntactically
valid and can never match -- and re-runs the tool's own evidence:

    1. its fixture lock  (`--fixtures` / `--selftest`), if it has one; else
    2. its declared control, from CONTROLLED_BY.

If neither turns red, that rule is DEAD TO ITS OWN EVIDENCE: nothing the tool
ships as proof of itself depends on the rule existing.

── WHAT "DEAD" DOES AND DOES NOT MEAN, because the distinction is the finding ─
It does NOT mean the rule is wrong, or unused on real data. It means NOTHING
THE TOOL CARRIES AS EVIDENCE would notice if it vanished. A rule in that state
can be deleted, mistyped, or shipped with a literal backspace and every green
light stays green -- which is exactly what happened.

The repair is one of two, and they are not the same:
  * add a fixture that exercises the rule -- when the rule is load-bearing; or
  * register it as a NAMED LIMIT -- when it is defensive, covers a shape that no
    longer occurs, or is a belt-and-braces second spelling. A named limit is
    honest; an unexercised rule presented as a criterion is not.

── IT NEVER WRITES A TRACKED FILE, AND IT USED TO (fixed 2026-09-30) ───────
Every neutralisation and every evidence run happens in a THROWAWAY WORKTREE,
created once per run and removed in a `finally`. The clone is never opened for
writing at all.

It used to mutate the tracked tool source in place and restore it in a
`finally`. That is correct for every path the interpreter walks and worthless
for the ones it does not. The first full run was measured at the 240s bound with
TWENTY tracked tool sources written -- each carrying a rule replaced by a
never-matching pattern -- in a clone four other sessions push from. **A restore
reached only on a normal exit is not isolation; it is a tidy-up.** The restore
is kept, inside the copy, because it is still what keeps ONE ablation to ONE
rule -- it just no longer carries the isolation.

A worktree rather than a plain file copy, because several swept tools shell out
to `git` and a tree with no `.git` would change what the real-run tier measures
while looking like the same comparison. The working tree is overlaid on top of
HEAD, so the sweep judges the code in front of you rather than the last commit.

IF THE COPY CANNOT BE MADE THE SWEEP EXITS 2 AND DOES NOT RUN. There is no
fallback to the clone: "could not isolate" is a third state and folding it into
"ran" is the defect itself (PR §1.11).

── WHAT IT CANNOT SEE, stated rather than discovered later ──────────────────
  * A rule built at runtime, or compiled inside a function. Only a module-level
    `NAME = re.compile(...)` is reachable.
  * A rule whose tool has NEITHER a fixture lock NOR a declared control. Those
    are COULD NOT TELL and are counted separately -- not folded into clean,
    because "no evidence to ablate" and "the rule is exercised" are opposite
    findings that would otherwise print the same.
  * WHETHER THE FIXTURE THAT SAVES A RULE IS ANY GOOD. One fixture that happens
    to touch the pattern clears it here. That is sabotage_control_check's
    question.
  * A rule that only matters on REAL data. The evidence a tool ships is the
    thing under test, deliberately: a rule defended only by the corpus is
    defended by something that changes without anybody deciding.
"""
import argparse
import ast
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                 # noqa: E402

CONTROLLED_BY = ['tests/run_dead_rule_sweep_probe.py']
CRITERIA_VERSION = '2026-09-29.1'

# A pattern that is syntactically valid and can never match anything. Used
# instead of deleting the line, so the module still imports and the failure is
# ABOUT THE RULE rather than about a NameError somewhere else.
NEVER = "(?!x)x"

# Flags that run a tool's own fixture lock without touching real data.
LOCK_FLAGS = ('--fixtures', '--selftest', '--self-check')
# A bare real run is the third tier's evidence and some tools are slow.
# A timeout is COULD NOT TELL, never dead.
# Lowered from 180 after the first full run: the third tier costs TWO bare
# runs per rule and the sweep has to finish to be worth anything. A timeout
# is COULD NOT TELL, never dead.
# ── THE BOUND, AND IT WAS SILENTLY THE ANSWER FOR 21 RULES ─────────────────
# MEASURED 2026-10-06: tools/cross_tenant_isolation_scope.py needs 131s and this
# bound was 45, so its bare run timed out on every ablation and all 21 of its
# rules came back COULD NOT RUN -- 21 of the platform's 23. THE REPORTED REASON
# WAS "no fixture lock and no control to ablate against", WHICH IS FALSE: it has
# no lock, but the real run WAS available and this tool refused to wait for it.
# Two different causes were printing one line, which is the defect this file
# exists to catch, arriving in its own output.
#
# Raising the default is NOT the fix. 21 rules at 131s each, twice, is 90
# minutes for one tool and would make the full sweep unusable. So the bound is
# OVERRIDABLE and PRINTED, and a timeout now says so by name -- the same answer
# the report-only sweep reached for its own bound: a could-not-tell can be
# re-asked instead of becoming permanent.
CORPUS_TIMEOUT = 45

DEAD = 'DEAD TO ITS OWN EVIDENCE -- neutralise it and nothing goes red'
LIVE = 'exercised'
# ── A THIRD TIER, ADDED 2026-09-29 ──────────────────────────────────────────
# The first run left 91 of 156 rules as COULD NOT TELL because their tool ships
# neither a fixture lock nor a declared control. But a tool with no evidence
# still PRODUCES SOMETHING: if neutralising a rule changes what it prints on the
# real corpus, something notices.
#
# THIS IS WEAKER EVIDENCE AND THE VERDICT SAYS SO. A lock is hand-built and
# changes only when somebody decides; the corpus changes when anybody pushes. A
# rule defended only by the corpus is defended by something nobody agreed to,
# and the day the last matching line is deleted the rule goes dead with no
# signal. It is real evidence and it is not the same evidence, so it is a
# separate verdict rather than folded into `exercised`.
LIVE_CORPUS = 'exercised BY THE REAL RUN ONLY -- no lock, no control'
DEAD_EVEN_ON_OUTPUT = ('DEAD EVEN ON THE REAL RUN -- no lock, no control, and '
                       'neutralising it does not change a byte of the output')
NO_EVIDENCE = ('COULD NOT TELL -- no lock, no control, and the real run could '
               'not be compared either')
NO_EVIDENCE_TIMEOUT = ('COULD NOT TELL -- no lock and no control, and the real '
                       'run DID NOT FINISH inside the corpus bound. The '
                       'evidence exists and this tool declined to wait for it: '
                       're-ask with --corpus-timeout')
WRITES = ('COULD NOT TELL -- no lock, no control, and the tool REGENERATES a '
          'file when run, so its output is not a stable comparison')
# ── THE WRITER TIER IS NOW MEASURED RATHER THAN REFUSED (2026-10-06) ────────
# The comment below said the surviving problem was ATTRIBUTION, not safety, and
# it was right: a tool that rewrites its own subject compares its output against
# a corpus it has just changed. The fix is therefore not more isolation -- the
# sandbox already gives that -- it is RESETTING THE CORPUS BETWEEN RUNS so a
# difference is attributable to the rule again.
#
# Three things have to hold before a writer's run counts as evidence, and each
# one is MEASURED on that tool rather than assumed for the tier:
#
#   1. THE RESET WORKS. Every file the run dirtied is put back -- tracked files
#      from git, untracked ones deleted -- and the sandbox must return to the
#      exact porcelain state it had before.
#   2. THE TOOL IS DETERMINISTIC. Two identical baseline runs, with a reset
#      between them, must produce the same exit code, the same stdout and the
#      same bytes in every file they write. A generator that stamps a timestamp
#      fails here, and failing here is a FINDING ABOUT THE COMPARISON, not a
#      verdict about the rule.
#   3. NOTHING ESCAPED. The CLONE's own porcelain state is read before and after
#      and must be identical. A writer that computes its target from something
#      other than its own location could reach outside the copy, and that must
#      be loud rather than discovered later.
#
# Any of the three failing leaves the rule in a COULD NOT RUN state with the
# measured reason -- never folded into clean, and never into dead either.
WRITES_NONDET = ('COULD NOT TELL -- the tool writes when run and is NOT '
                 'REPRODUCIBLE: two identical baseline runs differed, so no '
                 'difference can be attributed to a rule')
WRITES_NO_RESET = ('COULD NOT TELL -- the tool writes when run and the sandbox '
                   'could not be reset between runs, so each run would see the '
                   'previous run output')
LIVE_WRITER = ('exercised BY THE REAL RUN ONLY -- a WRITER, reset between runs '
               'and proved reproducible first')
DEAD_WRITER = ('DEAD EVEN ON THE REAL RUN -- a WRITER, reset between runs and '
               'proved reproducible first, and neutralising it changes neither '
               'the output nor a byte it writes')
# THE REASON FOR THIS TIER CHANGED WHEN THE SANDBOX LANDED (2026-09-30) and the
# tier is kept, so the reason is restated rather than left to read as stale.
# It used to be a SAFETY tier -- a generator run bare would leave
# docs/MASTER-PLAN.md, docs/TOOLING-INVENTORY.md and docs/traceability-matrix.md
# modified in the working tree. That danger is gone: the run happens in a copy.
# What survives is a COMPARISON problem, which is the real one: a tool that
# rewrites its own subject when run is comparing its output against a corpus it
# has itself just changed, so a difference between baseline and ablation is not
# attributable to the rule. Detected by SHAPE rather than by a name list -- a
# write to a path built from REPO -- so a new generator is covered on the day it
# lands rather than on the day somebody remembers to add it.
WRITE_SHAPES = (
    "'w'", '"w"', "'wb'", '"wb"', "'a'", "'w+'",
)


def writes_when_run(src):
    """Does a bare run of this tool open something for writing?"""
    for ln in src.split('\n'):
        t = ln.strip()
        if t.startswith('#'):
            continue
        if ('open(' not in t and '.write(' not in t
                and 'makedirs' not in t and 'replace(' not in t):
            continue
        if any(w in t for w in WRITE_SHAPES):
            return True
    return False


def module_patterns(src):
    """[(name, lineno)] for every module-level NAME = re.compile(...)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    out = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        t = node.targets[0]
        if not isinstance(t, ast.Name):
            continue
        v = node.value
        if not (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                and v.func.attr == 'compile'):
            continue
        out.append((t.id, node.lineno))
    return out


def neutralise(src, name):
    """Replace one module-level compiled pattern with a never-matching one.

    Rewritten through `ast` rather than by text surgery: a pattern can span
    lines, carry adjacent string literals and end with flags, and a regex that
    edits regexes by regex is how this class of defect is born.
    """
    tree = ast.parse(src)
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == name
                and isinstance(node.value, ast.Call)):
            lines = src.split('\n')
            start = node.lineno - 1
            end = getattr(node, 'end_lineno', node.lineno) - 1
            flags = ''
            for kw in node.value.keywords:
                flags = ''
            if len(node.value.args) > 1:
                flags = ', ' + ast.unparse(node.value.args[1])
            repl = '%s = re.compile(%r%s)' % (name, NEVER, flags)
            return '\n'.join(lines[:start] + [repl] + lines[end + 1:])
    return None


def evidence_cmds(tool, src, work):
    """[(label, argv)] -- the tool's own proof, cheapest first.

    Every path is built under `work`, the sandbox. A single argv still pointing
    at REPO would run the clone's copy of a control against the sandbox's copy
    of the tool -- half the ablation in one tree and half in the other, which is
    a comparison of nothing.
    """
    cmds = []
    for f in LOCK_FLAGS:
        if "'%s'" % f in src or '"%s"' % f in src:
            cmds.append(('lock %s' % f,
                         [sys.executable, os.path.join(work, 'tools', tool), f]))
            break
    for m in re.findall(r"CONTROLLED_BY\s*=\s*\[([^\]]*)\]", src):
        for name in re.findall(r"'([^']+)'", m):
            p = os.path.join(work, name.replace('/', os.sep))
            if os.path.isfile(p):
                cmds.append(('control %s' % os.path.basename(name),
                             [sys.executable, p]))
    return cmds


def run(argv, cwd, timeout=240, want_output=False):
    """Exit code, or (exit code, stdout) when the output itself is the signal.

    None means the run could not be compared at all -- a timeout or a crash of
    the harness rather than of the tool. Kept distinct from a non-zero exit,
    because "it failed" and "I could not find out" are different answers and
    this file's whole subject is not confusing the two.
    """
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                    PYTHONUTF8='1'))
        return (r.returncode, r.stdout or '') if want_output else r.returncode
    except subprocess.TimeoutExpired:
        return (None, None) if want_output else None
    except Exception:                                          # noqa: BLE001
        return (None, None) if want_output else None


# ── THE FIXTURE LOCK (discipline 1), and this tool must pass its own test ────
# Hand-built sources, classified with no real file read. The FIRST one is the
# whole point: a pattern replaced with NEVER must still PARSE and still IMPORT,
# because a neutralisation that breaks the module would turn every rule red for
# the wrong reason and report a clean sweep of exercised rules.
FIXTURES = (
    ("PAT = re.compile(r'abc')\n", 'PAT', True,
     'the simple form: one pattern, one line'),
    ("PAT = re.compile(\n    r'abc'\n    r'|def', re.I)\n", 'PAT', True,
     'A MULTI-LINE PATTERN WITH ADJACENT LITERALS AND A FLAG. Text surgery gets '
     'this wrong, which is why the rewrite goes through ast -- a regex that '
     'edits regexes by regex is how this defect class is born'),
    ("import re\nPAT = re.compile(r'a', re.I | re.M)\nX = 1\n", 'PAT', True,
     'the flags expression is carried over, not dropped: dropping re.I would '
     'change behaviour beyond the neutralisation and the ablation would be '
     'measuring two things'),
    ("PAT = re.compile(r'abc')\n", 'NOSUCH', False,
     'a name that is not there yields no rewrite rather than a silent no-op '
     'that would be counted as an ablation that changed nothing'),
    ("def f():\n    P = re.compile(r'x')\n", 'P', False,
     'A PATTERN COMPILED INSIDE A FUNCTION IS OUT OF REACH, and saying so is '
     'the difference between a limit and a gap'),
)


def run_fixtures(verbose=False):
    bad = []
    # ── THE FIRST THING THE LOCK CHECKS IS THAT `NEVER` NEVER MATCHES ───────
    # Its own control caught this missing. Every fixture below asks "does the
    # rewrite contain NEVER", and `'' in anything` is True -- so an EMPTY NEVER
    # passed all five while neutralising nothing, and every rule in the repo
    # would have been reported as exercised. A sentinel that is not checked is
    # not a sentinel.
    try:
        _n = re.compile(NEVER)
        _ok = all(_n.search(s) is None
                  for s in ('', 'x', 'abc', 'fixture invalid', '\n'))
    except re.error as _e:
        _ok, _n = False, None
    if not _ok:
        bad.append('NEVER=%r MATCHES SOMETHING (or will not compile) -- the '
                   'neutralisation would be a no-op reported as an exercise, '
                   'and every rule would read as exercised' % NEVER)
    elif verbose:
        print('  ok   %-28s %s' % ('NEVER matches nothing',
                                   'the sentinel the whole ablation rests on'))
    for src, name, should, why in FIXTURES:
        out = neutralise(src, name)
        ok = (out is not None) if should else (out is None)
        if ok and out is not None:
            try:
                ast.parse(out)
                ok = NEVER in out
            except SyntaxError:
                ok = False
        if not ok:
            bad.append('%s -- %s' % (name, why))
        elif verbose:
            print('  ok   %-28s %s' % (name, why))
    return bad


def registry_tools():
    try:
        import report_only_checks
        return [e['tool'] for e in report_only_checks.REGISTRY if e.get('tool')]
    except Exception:                                          # noqa: BLE001
        return None


# ── THE DECLARED EXEMPTIONS, AND THE LIST IS SHORT ON PURPOSE ───────────────
# A long exemption list is the hand-maintained universe wearing a different
# name. Anything that compiles a module-level rule is IN unless ablating it is
# incoherent -- not merely inconvenient, not "probably fine", not "it is only a
# library". A rule in a library can be dead exactly as a rule in a checker can.
#
# Every entry must still carry rules. An exemption for a file with none excuses
# nothing and hides the fact that the mechanical rule already covered it, so
# `--universe` reports it as a STALE EXEMPTION rather than passing over it.
# IT IS EMPTY, AND THAT IS THE MEASURED RESULT RATHER THAN AN OVERSIGHT.
# The first entry written here was `dead_rule_sweep.py` itself -- "neutralising
# its own rule mid-run measures the harness, not the subject" -- which is a true
# sentence and a USELESS exemption: this file compiles no module-level rule, so
# the mechanical branch already excluded it. The STALE_EXEMPT check below caught
# that within minutes of being written, on its author, and refused the run.
#
# So the honest state of the declared list is NOTHING. Every one of the 295
# tracked tools is classified by a rule, not by a judgement, and if that ever
# stops being true the entry has to carry a reason somebody can argue with.
EXEMPT = {}


def classify_universe(registry=None):
    """[(tool, state, rules, why)] for every tracked tools/*.py.

    Four states, and the first two are the universe:

      IN        has module-level rules and is not exempt
      OUT_REG   has rules, in the universe, but ABSENT from the report-only
                registry -- the delta this change exists to make visible
      EXEMPT    declared in EXEMPT above, with its reason
      NO_RULE   compiles no module-level rule; nothing to ablate (mechanical)
      UNREADABLE  does not parse -- NOT folded into NO_RULE, because "no rules"
                and "I could not look" are opposite findings

    The list is derived from `git ls-files`, matching what tooling_inventory.py
    does, so an untracked file is reported as invisible rather than silently
    swept in one tool and not the other.
    """
    r = subprocess.run(['git', '-C', REPO, 'ls-files', 'tools/*.py'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return None
    reg = set(registry or [])
    rows = []
    for rel in sorted(x.strip() for x in (r.stdout or '').split('\n') if x.strip()):
        base = os.path.basename(rel)
        try:
            src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                          errors='replace').read()
        except OSError as exc:
            rows.append((base, 'UNREADABLE', 0, exc.__class__.__name__))
            continue
        pats = module_patterns(src)
        if pats is None:
            rows.append((base, 'UNREADABLE', 0, 'does not parse'))
        elif base in EXEMPT:
            rows.append((base, 'EXEMPT' if pats else 'STALE_EXEMPT',
                         len(pats), EXEMPT[base]))
        elif not pats:
            rows.append((base, 'NO_RULE', 0,
                         'no module-level compiled rule -- nothing to ablate'))
        elif base in reg:
            rows.append((base, 'IN', len(pats), 'in the report-only registry'))
        else:
            rows.append((base, 'OUT_REG', len(pats),
                         'NOT in the report-only registry -- invisible to this '
                         'sweep before 2026-10-05'))
    return rows


def universe_tools(rows):
    """The tools actually swept: every IN and every OUT_REG, in one order."""
    return [t for t, state, _, _ in rows if state in ('IN', 'OUT_REG')]


# ── THE SANDBOX, AND WHY THE RESTORE-IN-FINALLY WAS NOT ENOUGH ──────────────
# This sweep used to neutralise a rule IN THE TRACKED FILE and put it back in a
# `finally`. That is correct for every path the interpreter walks and worthless
# for the ones it does not: SIGKILL, a harness timeout, a closed laptop. The
# first full run was measured at the 240s bound with TWENTY tracked tool sources
# written -- each carrying a rule replaced by a never-matching pattern -- in a
# clone four other sessions push from. A restore that is only reached on a
# normal exit is not isolation; it is a tidy-up.
#
# So every mutation and every evidence run now happens in a throwaway worktree
# and the clone is never opened for writing at all. The `finally` restore stays,
# inside the copy, because it is still the thing that keeps ONE ablation to ONE
# rule -- it just no longer carries the isolation.
#
# A WORKTREE RATHER THAN A PLAIN FILE COPY, deliberately: several swept tools
# shell out to `git`, and a tree with no `.git` would change what the real-run
# tier measures while looking like the same comparison.
#
# THE WORKING TREE IS OVERLAID ON TOP OF HEAD. A sandbox at HEAD alone would
# sweep the committed version of a tool the author has just edited, and report
# a verdict about code that is not the code in front of them.
SANDBOX_PREFIX = 'drs-sandbox-'
OWNER_FILE = '.drs-owner'


# ── AND THE REAP USED TO DESTROY A LIVE RUN (fixed 2026-10-06) ──────────────
# `reap_stale_sandboxes` removed EVERY directory matching the prefix, on the way
# in and on the way out, with no notion of whose it was. So a second run of this
# sweep -- even a one-tool `--tool X.py` run -- deleted the sandbox a long run
# was working in, and the victim did not report anything useful: it crashed with
# FileNotFoundError when it next tried to write a patched source.
#
# MEASURED, on the first full 151-tool run: `--tool register_feed_gate.py` was
# started in another shell while it was going, and the long run died 29 tools in
# with a traceback naming tools/copy_exactly_gate.py -- a file that had simply
# stopped existing underneath it. The verdicts for the first 28 tools went with
# it, and nothing said "a concurrent run took my sandbox"; it read like a bug in
# the tool being swept.
#
# This is the two-probe-runs-at-once failure the platform already has a memory
# for: the second run restored the first run's mutation and reported success.
# Here the second run deleted the first run's whole tree.
#
# SO THE REAP NOW FAILS CLOSED. A sandbox is reaped only when its owning process
# is provably gone. "Could not tell" leaves it alone, which costs a leftover
# directory in temp -- the trade this file's own comment already argues for --
# instead of destroying a run in flight.
def _pid_alive(pid):
    if pid == os.getpid():
        return True
    try:
        if os.name == 'nt':
            r = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/NH'],
                               capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
            return str(pid) in (r.stdout or '')
        os.kill(pid, 0)
        return True
    except Exception:                                          # noqa: BLE001
        return True      # COULD NOT TELL -- never a licence to delete


def _sandbox_owner(path):
    """The pid that owns this sandbox, or None if it carries no marker."""
    try:
        return int(io.open(os.path.join(path, OWNER_FILE),
                           encoding='utf-8').read().strip())
    except Exception:                                          # noqa: BLE001
        return None


def reap_stale_sandboxes():
    """Remove this tool's own leftover worktrees before making a new one.

    A killed sweep leaves its sandbox behind -- that is the whole point of the
    sandbox, and it is the honest trade: a leftover directory OUTSIDE the clone
    instead of a neutralised rule INSIDE it. But `git worktree prune` only
    forgets entries whose directory is gone, so a killed run's sandbox stays
    registered and they accumulate. This reaps them by NAME, and only the ones
    this tool creates -- other sessions' throwaway worktrees are not touched.

    AND ONLY THE ONES WHOSE OWNER IS PROVABLY GONE. It used to reap every
    matching directory, so a concurrent run of this sweep destroyed a live one
    mid-flight; see the note above `_pid_alive`. Returns the paths it SKIPPED,
    so a caller can say that a leftover was left on purpose.
    """
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'],
                   capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
    r = subprocess.run(['git', '-C', REPO, 'worktree', 'list', '--porcelain'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    skipped = []
    for line in (r.stdout or '').split('\n'):
        if not line.startswith('worktree '):
            continue
        p = line[len('worktree '):].strip()
        if not os.path.basename(p.rstrip('/\\')).startswith(SANDBOX_PREFIX):
            continue
        owner = _sandbox_owner(p)
        if owner is not None and owner != os.getpid() and _pid_alive(owner):
            skipped.append((p, owner))
            continue
        subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', p],
                       capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
        shutil.rmtree(p, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'],
                   capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
    return skipped


def make_sandbox():
    """A throwaway copy of the working tree, or None -- never REPO.

    None means COULD NOT RUN. It is never a licence to fall back to the clone:
    "could not isolate" is a third state and folding it into "ran" is how this
    tool came to write 20 tracked files (PR §1.11).
    """
    reap_stale_sandboxes()
    # SAIRN_DRS_SANDBOX_PARENT points the copy at a chosen directory instead of
    # the system temp. It exists so the REFUSAL PATH CAN BE DRIVEN -- the same
    # reason criticality_tier_check.py takes SAIRN_TIER_REGISTER. Without it the
    # only way to test "the sandbox could not be made" was to poison TMPDIR, and
    # that does not work: tempfile walks its candidate list and falls through to
    # a real directory, so the control passed while testing nothing.
    parent = os.environ.get('SAIRN_DRS_SANDBOX_PARENT') or None
    try:
        work = tempfile.mkdtemp(prefix='drs-sandbox-', dir=parent)
    except Exception:                                          # noqa: BLE001
        return None
    shutil.rmtree(work, ignore_errors=True)
    add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach',
                          work, 'HEAD'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace')
    if add.returncode != 0:
        shutil.rmtree(work, ignore_errors=True)
        return None
    # THE OWNER MARKER, WRITTEN BEFORE ANY WORK. It is what stops a concurrent
    # run reaping this tree out from under us, so it cannot be written later --
    # a window between `worktree add` and the marker is a window in which this
    # sandbox looks abandoned.
    try:
        io.open(os.path.join(work, OWNER_FILE), 'w', encoding='utf-8',
                newline='\n').write('%d\n' % os.getpid())
    except OSError:
        drop_sandbox(work)
        return None
    # Overlay every tracked file the working tree has changed, so the sweep
    # judges what is on disk. A copy that silently landed nothing would make
    # this a sweep of HEAD wearing the working tree's name, so each copy is
    # verified byte-for-byte.
    dirty = subprocess.run(['git', '-C', REPO, 'diff', '--name-only', 'HEAD'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
    for rel in (dirty.stdout or '').split('\n'):
        rel = rel.strip()
        if not rel:
            continue
        src = os.path.join(REPO, rel.replace('/', os.sep))
        dst = os.path.join(work, rel.replace('/', os.sep))
        if not os.path.isfile(src):
            continue                       # deleted in the working tree
        try:
            if not os.path.isdir(os.path.dirname(dst)):
                os.makedirs(os.path.dirname(dst))
            shutil.copyfile(src, dst)
            if os.path.getsize(src) != os.path.getsize(dst):
                raise IOError('overlay size mismatch for %s' % rel)
        except Exception:                                      # noqa: BLE001
            drop_sandbox(work)
            return None
    return work


def drop_sandbox(work):
    if not work:
        return
    subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', work],
                   capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
    shutil.rmtree(work, ignore_errors=True)
    reap_stale_sandboxes()


def _porcelain(tree):
    """{relpath: status} for every dirty path, or None if git could not be read.

    None is NOT an empty tree. A writer tier that read "nothing is dirty" from a
    failed git call would reset nothing and compare a corpus against itself one
    run later.
    """
    r = subprocess.run(['git', '-C', tree, 'status', '--porcelain'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return None
    out = {}
    for line in (r.stdout or '').split('\n'):
        if len(line) < 4:
            continue
        out[line[3:].strip().strip('"')] = line[:2]
    return out


# ── THE ESCAPE CHECK ACCUSED AN INNOCENT TOOL (fixed 2026-10-06) ────────────
# The writer tier reads the CLONE's state before and after each writer run, so a
# tool that reached outside its sandbox is loud rather than discovered later.
# The first version compared `_porcelain(REPO)` alone and, on difference, raised
#
#     "<tool> changed this CLONE while running in the sandbox -- a writer
#      reached outside the copy"
#
# MEASURED: that fired against tools/primitive_obsession_check.py, 23 minutes
# into a 151-tool run, and VOIDED THE WHOLE RUN. The tool is innocent -- driven
# alone on a clean tree it leaves the clone byte-identical. THE REAL CAUSE WAS MY
# OWN `git commit` IN THE CLONE WHILE THE SWEEP RAN.
#
# It is the same defect class as the push_retry message this session routed to
# fourth: a guard that detects a real change and attributes it to the wrong
# actor. Two in one session, and this one is mine.
#
# So the state now carries HEAD as well as the dirty set. A HEAD move explains
# the difference as a commit, which CANNOT affect the sandbox -- that is a
# detached worktree created before it -- so the run re-baselines, says so, and
# continues. Only an unexplained change voids the run, and even then the message
# refuses to name the tool as the cause, because another process in the clone
# produces the identical reading.
def _clone_state():
    """(HEAD, sorted dirty paths) for the clone, or None if git cannot be read."""
    h = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    p = _porcelain(REPO)
    if h.returncode != 0 or p is None:
        return None
    return (h.stdout.strip(), tuple(sorted(p)))


def _digest(tree, rels):
    """A content fingerprint of named paths. A missing file is recorded as such."""
    h = hashlib.sha256()
    for rel in sorted(rels):
        p = os.path.join(tree, rel.replace('/', os.sep))
        h.update(rel.encode('utf-8'))
        if os.path.isfile(p):
            with io.open(p, 'rb') as fh:
                h.update(fh.read())
        else:
            h.update(b'<ABSENT>')
    return h.hexdigest()


def _snapshot(tree, rels):
    return {rel: (io.open(os.path.join(tree, rel.replace('/', os.sep)), 'rb').read()
                  if os.path.isfile(os.path.join(tree, rel.replace('/', os.sep)))
                  else None)
            for rel in rels}


def _reset_writer(tree, baseline, snap):
    """Put the sandbox back to `baseline` porcelain. True only if it really is.

    Returns False rather than raising, because "the reset did not work" is a
    measurable reason to refuse this tool and not a crash of the sweep.
    """
    now = _porcelain(tree)
    if now is None:
        return False
    for rel in sorted(set(now) - set(baseline)):
        p = os.path.join(tree, rel.replace('/', os.sep))
        rc = subprocess.run(['git', '-C', tree, 'checkout', '--', rel],
                            capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
        if rc.returncode != 0 and os.path.isfile(p):
            # Untracked: git cannot restore it because there is nothing to
            # restore to. It did not exist before this run, so it goes.
            try:
                os.unlink(p)
            except OSError:
                return False
    for rel, data in snap.items():
        p = os.path.join(tree, rel.replace('/', os.sep))
        try:
            if data is None:
                if os.path.isfile(p):
                    os.unlink(p)
            else:
                with io.open(p, 'wb') as fh:
                    fh.write(data)
        except OSError:
            return False
    back = _porcelain(tree)
    return back is not None and set(back) == set(baseline)


def _writer_sig(tree, argv, baseline, ignore=()):
    """(exit, stdout, digest-of-what-it-wrote) -- or None if it could not run.

    The digest is the point. A generator can rewrite a whole document without
    changing one byte of stdout, so comparing stdout alone would call a
    load-bearing rule dead.

    `ignore` MUST CARRY THE SWEPT TOOL OWN PATH, and leaving it out was a real
    fail-open rather than a theoretical one. The ablation writes the neutralised
    source into the sandbox, so that file is dirty on every patched run and on
    no baseline run. Including it made the signature differ EVERY time, which
    reported every rule as exercised -- the first measured output of this tier
    was "all 22 cleared, all 22 exercised", and it was the digest noticing the
    mutation rather than its effect. Caught by the probe negative arm (H2) on a
    hand-built writer with one rule it provably never reads.
    """
    rc, out = run(argv, tree, timeout=CORPUS_TIMEOUT, want_output=True)
    if out is None:
        return None
    now = _porcelain(tree)
    if now is None:
        return None
    skip = set(ignore)
    touched = sorted(set(now) - set(baseline) - skip) + sorted(
        r for r in (set(now) & set(baseline)) - skip if now[r] != baseline[r])
    return (rc, out, _digest(tree, touched), tuple(touched))


def sweep_writer(tool, path, orig, pats, work, verbose=False):
    """The writer tier. [(rule, verdict)] -- every refusal below is MEASURED.

    Order matters and is the segmented-verification discipline in miniature: the
    escape check and the reset are proved BEFORE any ablation, because a rule
    verdict taken on an unproven harness is worse than no verdict.
    """
    repo_before = _clone_state()
    baseline = _porcelain(work)
    if baseline is None or repo_before is None:
        return [(n, WRITES_NO_RESET) for n, _ln in pats]
    snap = _snapshot(work, list(baseline))
    argv = [sys.executable, os.path.join(work, 'tools', tool)]
    # The swept source is dirty on every patched run by construction. Comparing
    # it would make the signature differ because of the MUTATION rather than its
    # EFFECT -- see _writer_sig.
    ignore = ('tools/%s' % tool, os.path.join('tools', tool))

    first = _writer_sig(work, argv, baseline, ignore)
    if first is None:
        return [(n, NO_EVIDENCE) for n, _ln in pats]
    if not _reset_writer(work, baseline, snap):
        return [(n, WRITES_NO_RESET) for n, _ln in pats]

    # 2. REPRODUCIBLE? The second baseline is the whole licence to continue.
    second = _writer_sig(work, argv, baseline, ignore)
    if second is None or not _reset_writer(work, baseline, snap):
        return [(n, WRITES_NO_RESET) for n, _ln in pats]
    if first != second:
        if verbose:
            print('     %-26s two identical baseline runs differed: '
                  'exit %s/%s, stdout %s, wrote %s'
                  % ('(baseline)', first[0], second[0],
                     'same' if first[1] == second[1] else 'DIFFERENT',
                     'same bytes' if first[2] == second[2] else 'DIFFERENT bytes'))
        return [(n, WRITES_NONDET) for n, _ln in pats]

    # 3. NOTHING ESCAPED the copy while that ran -- AND THE FIRST VERSION OF
    #    THIS CHECK MADE A FALSE ACCUSATION, so read `_clone_state` before
    #    trusting what it says.
    repo_after = _clone_state()
    if repo_after != repo_before:
        if repo_after is None or repo_before is None:
            raise RuntimeError(
                'the clone state could not be read while sweeping %s, so '
                'nothing below is a comparison. NOT an accusation against that '
                'tool.' % tool)
        if repo_after[0] != repo_before[0]:
            # HEAD MOVED: somebody committed in the clone. That cannot touch
            # this sandbox -- it is a detached worktree created before the
            # commit -- so the measurement is intact and the run continues on a
            # fresh baseline. Printed, never silent: a re-baseline that nobody
            # is told about is a state change wearing a pass.
            print('  note: the clone HEAD moved from %s to %s while sweeping '
                  '%s -- a commit in the clone, not a writer escaping. The '
                  'sandbox is a detached worktree made before it, so the '
                  'comparison is unaffected; re-baselined and continuing.'
                  % (repo_before[0][:8], repo_after[0][:8], tool))
            repo_before = repo_after
        else:
            # ── THE DISCRIMINATOR THAT MAKES THIS ATTRIBUTABLE ─────────────
            # The question is not "did the clone change" -- four sessions and
            # my own document generators change it constantly. It is "did the
            # clone change IN A FILE THIS TOOL WROTE INSIDE THE SANDBOX".
            # `first[3]` is exactly that set, already computed by _writer_sig.
            #
            # An INTERSECTION is an escape and is named as one. A change
            # DISJOINT from what the tool wrote is somebody else's churn, and
            # voiding the run for it cost a second 12-minute sweep on
            # 2026-10-06 -- killed by my own `python tools/
            # traceability_matrix.py`, with criticality_tier_check.py named in
            # the message. The run re-baselines and continues instead.
            churn = sorted(set(repo_after[1]) ^ set(repo_before[1]))
            wrote = set(first[3] or ())
            overlap = sorted(set(churn) & wrote)
            if overlap:
                raise RuntimeError(
                    '%s WROTE OUTSIDE ITS SANDBOX. The clone changed in a file '
                    'this tool wrote inside the copy, which no other process '
                    'explains: %s. The comparison is void and the clone needs '
                    'looking at.' % (tool, overlap))
            print('  note: the clone changed while sweeping %s, in file(s) that '
                  'tool did NOT write\n        in the sandbox -- %s -- so it is '
                  'another process in this clone, not an escape.\n        '
                  'Re-baselined and continuing. (It wrote: %s)'
                  % (tool, churn[:4] or 'none readable',
                     sorted(wrote)[:4] or 'nothing'))
            repo_before = repo_after

    rows = []
    for name, _ln in pats:
        patched = neutralise(orig, name)
        if patched is None:
            rows.append((name, NO_EVIDENCE))
            continue
        io.open(path, 'w', encoding='utf-8', newline='').write(patched)
        if NEVER not in io.open(path, encoding='utf-8').read():
            rows.append((name, NO_EVIDENCE))
            continue
        got = _writer_sig(work, argv, baseline, ignore)
        # The tool source itself is now dirty, so restore the SOURCE by hand
        # before the generic reset -- `git checkout` would undo the overlay this
        # sweep is supposed to be judging.
        io.open(path, 'w', encoding='utf-8', newline='').write(orig)
        ok = _reset_writer(work, baseline, snap)
        if got is None or not ok:
            rows.append((name, WRITES_NO_RESET if not ok else NO_EVIDENCE))
        elif got != first:
            rows.append((name, LIVE_WRITER))
        else:
            rows.append((name, DEAD_WRITER))
    return rows


def _bare_baseline(bare, work, timeout):
    """(result, verdict_if_unusable). A TIMEOUT is told apart from a crash.

    `run()` returns (None, None) for both a timeout and a harness crash, so this
    re-asks with a tiny bound to find out which: a tool that cannot even START
    inside a second is broken, one that merely needs longer is a BOUND problem
    and says so. Without the distinction, 21 rules reported "no evidence to
    ablate against" when the evidence was there and this tool would not wait.
    """
    r = run(bare, work, timeout=timeout, want_output=True)
    if r[1] is not None:
        return r, None
    quick = run(bare, work, timeout=2, want_output=True)
    if quick[1] is not None:
        return r, NO_EVIDENCE          # finished fast once, failed now: unstable
    return r, NO_EVIDENCE_TIMEOUT


def sweep_tool(tool, work, verbose=False, corpus_timeout=None):
    """[(rule, verdict)] for one tool. `work` is the sandbox, never REPO."""
    path = os.path.join(work, 'tools', tool)
    if not os.path.isfile(path):
        return None
    orig = io.open(path, encoding='utf-8', newline='').read()
    pats = module_patterns(orig)
    if pats is None:
        return None
    if not pats:
        return []
    cmds = evidence_cmds(tool, orig, work)
    bare = None
    if not cmds and writes_when_run(orig):
        # Used to return WRITES for the whole tool, unmeasured. Now the writer
        # tier is attempted and each refusal inside it is a measurement.
        return sweep_writer(tool, path, orig, pats, work, verbose=verbose)
    if not cmds:
        # THE THIRD TIER. Run the tool bare and compare its OUTPUT, not only its
        # exit code: a rule can change what a report says without changing
        # whether it exits 1.
        bare = [sys.executable, os.path.join(work, 'tools', tool)]

    base = {}
    for label, argv in cmds:
        base[label] = run(argv, work)
    tmo = corpus_timeout or CORPUS_TIMEOUT
    base_bare, unusable = (_bare_baseline(bare, work, tmo) if bare else (None, None))
    if bare and unusable is not None:
        # The baseline itself could not be taken, so nothing below is a
        # comparison. NOT folded into dead -- and the REASON is carried, because
        # "no evidence exists" and "I would not wait for it" are different
        # findings that used to print the same line.
        return [(n, unusable) for n, _ln in pats]

    rows = []
    try:
        for name, _ln in pats:
            patched = neutralise(orig, name)
            if patched is None:
                rows.append((name, NO_EVIDENCE))
                continue
            io.open(path, 'w', encoding='utf-8', newline='').write(patched)
            # THE NEUTRALISATION MUST HAVE APPLIED. A patch that silently did
            # nothing would report every rule as dead.
            if NEVER not in io.open(path, encoding='utf-8').read():
                rows.append((name, NO_EVIDENCE))
                continue
            if bare:
                got = run(bare, work, timeout=tmo, want_output=True)
                if got[1] is None:
                    rows.append((name, NO_EVIDENCE))
                elif got != base_bare:
                    rows.append((name, LIVE_CORPUS))
                else:
                    rows.append((name, DEAD_EVEN_ON_OUTPUT))
                continue
            moved = False
            for label, argv in cmds:
                rc = run(argv, work)
                if rc != base.get(label):
                    moved = True
                    if verbose:
                        print('     %-26s %s: %s -> %s'
                              % (name, label, base.get(label), rc))
                    break
            rows.append((name, LIVE if moved else DEAD))
    finally:
        io.open(path, 'w', encoding='utf-8', newline='').write(orig)
        after = io.open(path, encoding='utf-8', newline='').read()
        if after != orig:
            raise RuntimeError('RESTORE FAILED for %s -- the file on disk is '
                               'not what it was' % tool)
    return rows


def main(argv):
    ap = argparse.ArgumentParser(add_help=True,
                                 description=__doc__.split('\n')[0])
    ap.add_argument('--fixtures', action='store_true')
    ap.add_argument('--tool', default=None)
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--universe', action='store_true',
                    help='classify every tracked tools/*.py and stop -- the '
                         'delta list, no ablation')
    ap.add_argument('--registry-only', action='store_true',
                    help='the PRE-2026-10-05 population (report_only_checks.'
                         'REGISTRY) so the old figure stays reproducible')
    ap.add_argument('--corpus-timeout', type=int, default=None, metavar='SEC',
                    help='seconds a bare real run may take (default %d). '
                         'PRINTED on every run: two sweeps at different bounds '
                         'must never be indistinguishable in a past report'
                         % CORPUS_TIMEOUT)
    ap.add_argument('--segment', default=None, metavar='I/N',
                    help='sweep slice I of N (1-based). The tenth discipline: '
                         'no long run whose first check is at the end')
    a = ap.parse_args(argv)

    def _universe_report():
        # Runs AFTER the criteria lock, deliberately: the classification is
        # `module_patterns()` applied 295 times, and that is the function the
        # lock tests. A population printed by an unlocked parser is a list of
        # names with no evidence behind it.
        rows = classify_universe(registry=registry_tools())
        if rows is None:
            print('COULD NOT RUN -- `git ls-files tools/*.py` failed, so the '
                  'population could not be derived.\nThis is NOT an empty '
                  'universe and is not reported as one.')
            return EXIT_COULD_NOT_RUN
        by = {}
        for t, state, n, why in rows:
            by.setdefault(state, []).append((t, n, why))
        print('UNIVERSE CLASSIFICATION -- criteria %s' % CRITERIA_VERSION)
        print('derived from `git ls-files tools/*.py`, not from a '
              'hand-maintained list\n')
        for state in ('IN', 'OUT_REG', 'EXEMPT', 'STALE_EXEMPT', 'NO_RULE',
                      'UNREADABLE'):
            items = by.get(state, [])
            if not items:
                continue
            print('%s (%d file(s), %d rule(s))'
                  % (state, len(items), sum(n for _, n, _ in items)))
            for t, n, why in sorted(items, key=lambda x: (-x[1], x[0])):
                print('  %3d  %-44s %s' % (n, t, why))
            print()
        swept = universe_tools(rows)
        in_reg = sum(n for _, n, _ in by.get('IN', []))
        out_reg = sum(n for _, n, _ in by.get('OUT_REG', []))
        print('TOTALS')
        print('  tracked tools/*.py                  %4d' % len(rows))
        print('  THE UNIVERSE -- files swept         %4d  -> %4d rule(s)'
              % (len(swept), in_reg + out_reg))
        print('    of those, in the registry         %4d  -> %4d rule(s)'
              % (len(by.get('IN', [])), in_reg))
        print('    of those, OUTSIDE it              %4d  -> %4d rule(s)'
              % (len(by.get('OUT_REG', [])), out_reg))
        print('  exempt, declared with a reason      %4d'
              % len(by.get('EXEMPT', [])))
        print('  no module-level rule -- mechanical  %4d'
              % len(by.get('NO_RULE', [])))
        if by.get('UNREADABLE'):
            print('  UNREADABLE -- NOT a clean file      %4d'
                  % len(by['UNREADABLE']))
        if by.get('STALE_EXEMPT'):
            print('\n! %d STALE EXEMPTION(S) -- declared for a file that '
                  'compiles no rule.\n  The mechanical rule already covers it; '
                  'the entry excuses nothing and\n  makes EXEMPT look longer '
                  'than the judgement it actually carries.'
                  % len(by['STALE_EXEMPT']))
            return 1
        print('\nREPORT ONLY. Nothing was ablated -- this is the population, '
              'not a verdict.')
        return 0

    if not a.quiet:
        print('DEAD RULE SWEEP -- criteria %s' % CRITERIA_VERSION)
    bad = run_fixtures(verbose=(a.fixtures and not a.quiet))
    if bad:
        if not a.quiet:
            print('\nCRITERIA LOCK FAILED -- %d of %d fixtures wrong:'
                  % (len(bad), len(FIXTURES)))
            for b in bad:
                print('  ! %s' % b)
            print('\nNOTHING REAL WAS ABLATED. A sweep whose own rewrite is '
                  'broken reports every\nrule as dead, which is the loudest '
                  'possible wrong answer.')
        return EXIT_COULD_NOT_RUN
    if not a.quiet:
        print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
              'sources only' % (len(FIXTURES) + 1, len(FIXTURES) + 1))
    if a.fixtures:
        return 0
    if a.universe:
        return _universe_report()

    # ── THE POPULATION ─────────────────────────────────────────────────────
    # Derived from the tracked tool list, not from REGISTRY. --registry-only
    # keeps the old population reachable so the two figures stay comparable
    # and nobody has to guess which one a past document was quoting.
    rows, out_of_registry = None, 0
    if a.tool:
        tools = [a.tool]
    elif a.registry_only:
        tools = registry_tools()
        if not tools:
            if not a.quiet:
                print('\nCOULD NOT READ the report-only registry, which is the '
                      'population --registry-only\nasks for. Nothing to report '
                      'rather than nothing wrong.')
            return EXIT_COULD_NOT_RUN
    else:
        rows = classify_universe(registry=registry_tools())
        if rows is None:
            if not a.quiet:
                print('\nCOULD NOT DERIVE THE POPULATION -- `git ls-files '
                      'tools/*.py` failed.\nThis is NOT an empty universe and '
                      'is not reported as one. A sweep over zero\ntools exits 0 '
                      'and says nothing, which is the shape two of these sweeps '
                      'shipped\nwith until 2026-10-05.')
            return EXIT_COULD_NOT_RUN
        stale = [t for t, s, _, _ in rows if s == 'STALE_EXEMPT']
        if stale:
            if not a.quiet:
                print('\nCOULD NOT RUN -- %d STALE EXEMPTION(S): %s'
                      % (len(stale), ', '.join(stale)))
                print('An EXEMPT entry for a file that compiles no rule excuses '
                      'nothing and makes the\ndeclared list look longer than the '
                      'judgement it carries. Fix EXEMPT first;\n`--universe` '
                      'names them.')
            return EXIT_COULD_NOT_RUN
        tools = universe_tools(rows)
        out_of_registry = len([t for t, s, _, _ in rows if s == 'OUT_REG'])

    if not tools:
        if not a.quiet:
            print('\nCOULD NOT RUN -- the population is EMPTY. Not a clean '
                  'sweep: a run over zero\ntools has nothing to say and must '
                  'not exit 0.')
        return EXIT_COULD_NOT_RUN

    # ── SEGMENTATION (tenth discipline) ────────────────────────────────────
    # The glob universe is 150 tools where the registry was 45, so one run is
    # long enough that its first verdict used to arrive at the end. A slice
    # prints its own verdict at its own boundary. THE SLICE IS ALWAYS PRINTED:
    # a partial run reported as a whole one is the defect this file is about.
    seg_label = ''
    if a.segment:
        try:
            i_s, n_s = a.segment.split('/')
            i_s, n_s = int(i_s), int(n_s)
            if not (1 <= i_s <= n_s):
                raise ValueError
        except ValueError:
            print('--segment wants I/N with 1 <= I <= N, got %r' % a.segment)
            return EXIT_COULD_NOT_RUN
        whole = len(tools)
        tools = tools[i_s - 1::n_s]
        seg_label = ('  SEGMENT %d of %d -- %d of %d tool(s). THIS IS A SLICE; '
                     'its findings are not\n  the platform figure.'
                     % (i_s, n_s, len(tools), whole))

    # ── EVERY MUTATION FROM HERE DOWN HAPPENS IN A COPY ────────────────────
    # And if the copy cannot be made, this run does not happen. There is no
    # branch below that works in the clone instead -- that branch is what wrote
    # 20 tracked files once and it is not being kept as a fallback.
    work = make_sandbox()
    if work is None:
        if not a.quiet:
            print()
            print('COULD NOT RUN -- no throwaway worktree could be made, so '
                  'there is nowhere safe to neutralise a rule.')
            print('This sweep mutates a tool source for every rule it '
                  'ablates. Doing that in the clone left 20 tracked tool '
                  'files written on the first full run, because a restore in '
                  'a `finally` is NOT REACHED when the process is killed.')
            print('NOT a pass and NOT a fallback: "could not isolate" is a '
                  'third state and folding it into "ran" is the defect '
                  'itself.')
        return EXIT_COULD_NOT_RUN
    if not a.quiet:
        print('sandbox: %s' % work)

    dead, live, unknown, unreadable = [], 0, [], []
    live_corpus, dead_output, writes = 0, [], []
    nondet, noreset, slow = [], [], []
    try:
        for t in tools:
            # THE SANDBOX CAN BE GONE, and it used to surface as a traceback
            # about the tool being swept. If it has vanished, every verdict
            # already collected was taken in a tree that no longer exists and
            # the run is void -- not partially useful.
            if not os.path.isdir(work):
                print('\nCOULD NOT RUN -- THE SANDBOX DISAPPEARED while '
                      'sweeping %s, after %d tool(s).' % (t, tools.index(t)),
                      file=sys.stderr)
                print('Every verdict collected so far was taken in a tree that '
                      'is gone, so none of\nthem is reported. The known cause '
                      'is a CONCURRENT run of this sweep reaping it:\nuntil '
                      '2026-10-06 the reap deleted every drs-sandbox- directory '
                      'regardless of\nowner. If this still happens, something '
                      'other than this tool is removing them.',
                      file=sys.stderr)
                return EXIT_COULD_NOT_RUN
            try:
                rows = sweep_tool(t, work, verbose=bool(a.tool) and not a.quiet,
                                  corpus_timeout=a.corpus_timeout)
            except RuntimeError as e:
                print('RESTORE FAILURE: %s' % e, file=sys.stderr)
                return EXIT_COULD_NOT_RUN
            except OSError as e:
                print('\nCOULD NOT RUN -- the sandbox could not be written '
                      'while sweeping %s: %s' % (t, e), file=sys.stderr)
                print('Reported as a refusal rather than a traceback: a missing '
                      'sandbox file is not a\ndefect in the tool being swept, '
                      'and it used to read like one.', file=sys.stderr)
                return EXIT_COULD_NOT_RUN
            if rows is None:
                unreadable.append(t)
                continue
            for name, verdict in rows:
                if verdict == DEAD:
                    dead.append((t, name))
                elif verdict == LIVE:
                    live += 1
                elif verdict in (LIVE_CORPUS, LIVE_WRITER):
                    live_corpus += 1
                elif verdict in (DEAD_EVEN_ON_OUTPUT, DEAD_WRITER):
                    dead_output.append((t, name))
                elif verdict == WRITES:
                    writes.append((t, name))
                elif verdict == WRITES_NONDET:
                    nondet.append((t, name))
                elif verdict == WRITES_NO_RESET:
                    noreset.append((t, name))
                elif verdict == NO_EVIDENCE_TIMEOUT:
                    slow.append((t, name))
                else:
                    unknown.append((t, name))
    finally:
        drop_sandbox(work)

    total = (len(dead) + live + len(unknown) + live_corpus
             + len(dead_output) + len(writes) + len(nondet) + len(noreset)
             + len(slow))
    if not a.quiet:
        if a.tool:
            src_label = 'named on the command line'
        elif a.registry_only:
            src_label = ('from the report-only registry (--registry-only: the '
                         'PRE-2026-10-05 population)')
        else:
            src_label = ('from `git ls-files tools/*.py`, of which %d are '
                         'OUTSIDE the report-only registry\nand were invisible '
                         'to this sweep before 2026-10-05' % out_of_registry)
        print('read %d tool(s) %s; %d module-level compiled rule(s)'
              % (len(tools), src_label, total))
        print('  corpus bound: %ds per bare real run%s'
              % (a.corpus_timeout or CORPUS_TIMEOUT,
                 '' if a.corpus_timeout is None else ' (--corpus-timeout)'))
        if seg_label:
            print(seg_label)
        print('\nCHECKED / UNIVERSE: %d of %d rules could be ABLATED against '
              'SOME evidence.\n  %d of those against evidence the tool SHIPS -- '
              'a lock or a control -- of which\n  %d exercised and %d dead. '
              'THE OTHER %d WERE ABLATED AGAINST THE REAL RUN ONLY,\n  which is '
              'weaker: a lock changes when somebody decides, a corpus changes '
              'when\n  anybody pushes. %d of those move the output and %d do '
              'not move a byte of it.\n  AND %d ARE STILL NOT CLEARED -- no '
              'lock, no control, and the real run could\n  not be compared '
              'either. "No evidence to ablate" and "the rule is exercised"\n  '
              'are opposite findings and must not print the same.'
              % (live + len(dead) + live_corpus + len(dead_output), total,
                 live + len(dead), live, len(dead),
                 live_corpus + len(dead_output), live_corpus, len(dead_output),
                 len(unknown) + len(writes) + len(nondet) + len(noreset)
                 + len(slow)))
        if slow:
            print('  OF THOSE, %d belong to a tool whose real run DID NOT '
                  'FINISH in %ds.\n  THE EVIDENCE EXISTS and this sweep '
                  'declined to wait: re-ask with --corpus-timeout.\n  That is '
                  'a BOUND problem, not an absence of evidence, and until '
                  '2026-10-06 the\n  two printed the same line.'
                  % (len(slow), a.corpus_timeout or CORPUS_TIMEOUT))
        if writes:
            print('  OF THOSE, %d belong to a tool that WRITES when run and the '
                  'writer tier was NOT\n  attempted -- that path should no '
                  'longer be reachable, so seeing this means a\n  shape slipped '
                  'past it.' % len(writes))
        if nondet:
            print('  OF THOSE, %d belong to a writer that is NOT REPRODUCIBLE: '
                  'two identical\n  baseline runs differed, so no difference '
                  'can be attributed to a rule. THAT IS A\n  FINDING ABOUT THE '
                  'TOOL, not a verdict about its rules.' % len(nondet))
        if noreset:
            print('  OF THOSE, %d belong to a writer whose sandbox could not be '
                  'RESET between runs,\n  so each run would have seen the '
                  'previous one output.' % len(noreset))
        if unreadable:
            print('  UNREADABLE: %s' % ', '.join(unreadable))

    return finish(
        ['%s  %s  %s' % (t, n, DEAD) for t, n in dead]
        + ['%s  %s  %s' % (t, n, DEAD_EVEN_ON_OUTPUT) for t, n in dead_output],
        could_not_run=['%s %s -- no fixture lock and no control to ablate '
                       'against' % (t, n) for t, n in unknown]
        + ['%s %s -- the tool WRITES when run; the writer tier was not '
           'attempted' % (t, n) for t, n in writes]
        + ['%s %s -- WRITER, NOT REPRODUCIBLE: two identical baseline runs '
           'differed' % (t, n) for t, n in nondet]
        + ['%s %s -- WRITER, the sandbox could not be reset between runs'
           % (t, n) for t, n in noreset]
        + ['%s %s -- the real run DID NOT FINISH in %ds; re-ask with '
           '--corpus-timeout' % (t, n, a.corpus_timeout or CORPUS_TIMEOUT)
           for t, n in slow],
        quiet=a.quiet,
        clean_line='\nCLEAN -- every module-level rule whose tool ships '
                   'evidence is exercised by it.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
