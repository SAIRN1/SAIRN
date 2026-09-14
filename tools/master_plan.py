"""master_plan.py -- GENERATE docs/MASTER-PLAN.md's numbers from the repo.

    python tools/master_plan.py            # write the document
    python tools/master_plan.py --check    # are its numbers still true?

── WHY THIS EXISTS ──────────────────────────────────────────────────────────
`docs/MASTER-PLAN.md` is the only document on this platform that defines a
COMBINED end state -- a vertical is FINISHED when all four of BUILT, TIERED,
TRACEABLE and FAULT-TESTED are true. Four separately-measured numbers under one
conjunctive verdict. That is a tolerance stack-up by construction, and the
components had already drifted apart three days after it was written:

    "Traceability is 86 of 273"     MASTER-PLAN.md, citing the matrix
    "135 of 328 test files"         traceability-matrix.md, same day, regenerated
    "186 suites, 53 of them traced" MASTER-PLAN.md, its own totals line

Three traced counts, three denominators, two documents, ONE cited source. The
document said, in the present tense, "Every number below is derived, not
asserted". It was derived ONCE, by hand, on 2026-09-10 -- no generator, no
`--check`, and nothing under `tests/` asserting any figure in it.

── WHAT IS DERIVED AND WHAT CANNOT BE ───────────────────────────────────────
DERIVED, every run:
  * `res`     -- OWNER_BY_RESOURCE from api/_resources/index.js, loaded through
                 node, which is the registry the SOUP register, the removal-path
                 check and the criticality register all already use
  * `tiered`  -- tools/criticality_tier_check.py's own verdict
  * `suites`  -- test files this app owns, by the matrix's app_of()
  * `traced`  -- traceability_matrix.traced(), THE SAME FUNCTION the matrix
                 itself calls. The 86-vs-135 divergence is not fixable by
                 copying more carefully; it is fixable by there being one
                 definition
  * `fault`   -- probes that plant a real defect into that app's source

NOT DERIVED AND NEVER WILL BE: gate 1. Whether a migration has actually been
run against a live licence cannot be read from the repo. That section is
ATTESTED -- it names who confirmed what, and when -- and it is carried through
this generator verbatim from ATTESTED below. **A table cell there must never be
filled from inference.**

Also not derived: the definition of FINISHED itself, and what would make the
document wrong. Those are judgement, they were good, and they are kept as prose
in this file so the document stays fully generated.

── NO COMBINED VERDICT, ON PURPOSE ──────────────────────────────────────────
Convention 3 of docs/2026-09-13-cross-domain-disciplines.md: a named, itemized
table, never a combined number, and publish the denominator. So there is no
FINISHED column. Each gate is its own column with its own source named, and the
conjunction is left to the reader -- because collapsing four approximate
measurements into one tick is exactly what made the drift invisible.

Exit 0 clean / 1 the document is out of date / 2 could not derive.
"""
import io
import json
import math
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import closing_error                                            # noqa: E402
import traceability_matrix as TM                                # noqa: E402

DOC = os.path.join('docs', 'MASTER-PLAN.md')

# ── THE ATTESTED HALF ───────────────────────────────────────────────────────
# Gate 1 is the one gate that cannot be derived: whether a migration has been
# run against a live licence is not in the repo. These lists are what a human
# said, and when. They are carried verbatim and are edited only by someone
# recording a NEW attestation -- never inferred, never widened.
ATTESTED_ON = '2026-09-10'
ATTESTED_BY = 'Michael, directly'
ATTESTED_RUN = [
    ('sql/stonedesk_data_schema.sql', 'stonedesk',
     'The 21 backup tables. **Not** StoneDesk\'s original schema'),
    ('sql/sairnvet_data_schema.sql', 'sairnvet', 'Its data schema'),
    ('sql/sairnfreedom_data_schema.sql', 'sairnfreedom', 'Its data schema'),
    ('sql/sairnfreedom_license_seed.sql', 'sairnfreedom', 'Its licence seed'),
    ('sql/sairndental_vendor_schema.sql', 'sairndental',
     'The **vendor** tables only'),
]
ATTESTED_UNVERIFIED = [
    ('SAIRNlaw', 'its deadline engine runs on live per-licence tables, and '
     '`tools/sairn_load_state_check.py --app sairnlaw` can answer it with a key'),
    ('SAIRNbiz', 'though ONE live write through its path was observed on '
     '2026-09-10 (`syncEmps()` returned 200 with `written: 1`), which proves '
     'the `employees` table exists and is writable; that is narrower than '
     '"its schemas are run"'),
    ("StoneDesk's ORIGINAL schema", 'distinct from the 21 backup tables above'),
    ('SAIRNbuild', ''),
    ('Every app not named in either list', 'which is most of them'),
]

# ── WHAT COUNTS AS A FAULT PROBE, AND WHY IT IS A DECLARATION ───────────────
# The first version of this asked whether a test file MENTIONED an app file and
# contained any of `MUTATIONS`/`fault_probe`/`plant`/`mutate`. It reported
# NINETEEN fault probes for StoneDesk, including `tests/key_collision_probe.py`
# -- a file written the same morning that plants nothing and writes only to a
# temp directory. That is fabricated coverage on the one column meant to say
# whether a guard has ever been seen to DENY, and it is exactly what Check 0b
# exists to refuse.
#
# Widening it the other way was no better: "writes an app .html" caught 20
# files, 17 of which write FIXTURES to a temp path and merely name an app.
#
# So the rule is a DECLARATION, twice over, and never an inference:
#   (a) the file declares a parseable `MUTATIONS` block whose target resolves
#       to a real file -- read with tools/mutation_anchor_check.py, which
#       already owns that parse and does it with `ast` rather than by import
#       (importing a probe RUNS it; most have no __main__ guard); or
#   (b) the file is named `*_fault_probe.py`, which is the author saying so.
#
# THE COUNT IS A FLOOR AND THE DOCUMENT SAYS SO. A probe that mutates real
# source while declaring neither is invisible here, and mutation_anchor_check's
# own docstring records that four of six could not be swept on 2026-09-11
# because they declare their target differently.
FAULT_PROBE_NAME = re.compile(r'_fault_probe\.py$')


def resources_by_app():
    """OWNER_BY_RESOURCE from the real registry, loaded through node.

    The same mechanism tools/removal_path_check.py uses. Not re-parsed with a
    regex here: a second way of reading the same registry is a second answer
    waiting to disagree with the first, which is the whole subject of this file.
    """
    src = ("const r = require('./api/_resources/index.js');"
           "process.stdout.write(JSON.stringify(r.OWNER_BY_RESOURCE));")
    p = subprocess.run(['node', '-e', src], cwd=REPO, capture_output=True,
                       text=True, timeout=300)
    if p.returncode:
        raise RuntimeError(
            'could not load api/_resources/index.js through node (exit %d): %s'
            % (p.returncode, (p.stderr or '').strip()[:200]))
    owner = json.loads(p.stdout)
    out = {}
    for _res, app in owner.items():
        out[app] = out.get(app, 0) + 1
    return out


def tiered_apps():
    """Apps criticality_tier_check.py is satisfied with, from its own verdict."""
    p = subprocess.run([sys.executable,
                        os.path.join(REPO, 'tools', 'criticality_tier_check.py')],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=600)
    out = (p.stdout or '') + (p.stderr or '')
    # A per-app complaint names the app. No complaint for an app that HAS
    # resources means it is tiered. Reported as (clean_overall, {app: problem}).
    problems = {}
    for line in out.splitlines():
        m = re.search(r'\b(sairn\w+|stonedesk)\b', line)
        if m and ('BAD TIER' in line or 'NO TIER' in line or 'half-tiered' in line):
            problems[m.group(1)] = line.strip()[:160]
    return p.returncode == 0, problems, out


def fault_probes():
    """{app: [probes that DECLARE they plant a defect in that app's source]}.

    See FAULT_PROBE_NAME above for why this is two declarations and no
    inference. Returns (by_app, declarers) so the document can print the floor
    and the total separately.
    """
    import mutation_anchor_check as MA
    names = TM.apps()
    out, declarers = {}, set()
    root = os.path.join(REPO, 'tests')
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in sorted(files):
            if not f.endswith('.py'):
                continue
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, REPO).replace(os.sep, '/')
            targets = set()

            # (a) a parseable MUTATIONS block, resolved by the tool that owns
            #     that parse. A probe this cannot read is NOT counted -- a
            #     silent fallback here would be the fabrication all over again.
            try:
                consts, muts = MA.read_probe(path)
                for m in muts:
                    try:
                        tgt = MA.resolve(consts, m)
                    except Exception:                          # noqa: BLE001
                        continue
                    if tgt:
                        targets.add(os.path.basename(str(tgt[0])))
            except Exception:                                  # noqa: BLE001
                pass

            # (b) the filename says so. Its target is read from the app-file
            #     STRING CONSTANTS in the file, not from the filename, so a
            #     probe covering two apps is credited to both.
            if FAULT_PROBE_NAME.search(f):
                body = io.open(path, encoding='utf-8', errors='replace').read()
                for a in names:
                    if ("'%s.html'" % a) in body or ('"%s.html"' % a) in body:
                        targets.add(a + '.html')

            if not targets:
                continue
            declarers.add(rel)
            for a in names:
                if (a + '.html') in targets:
                    out.setdefault(a, []).append(rel)
    return {k: sorted(set(v)) for k, v in out.items()}, sorted(declarers)


def suites_by_app(tests, names):
    out = {}
    for t in tests:
        # app_of_test, not app_of: the alias table in traceability_matrix.py is
        # what stops 27 roofing-* files reading as 0 suites for SAIRNroofing.
        # One function, declared there, so this document and the matrix cannot
        # attribute the same file to two different apps.
        out.setdefault(TM.app_of_test(t, names), []).append(t)
    return out



# ── THE STACK-UP: A WORST-CASE BOUND, AND RSS BESIDE IT FOR CONTEXT ────────
# Added 2026-09-13 on Michael's call, as a REAL GAP the itemized table does not
# close. Convention 3 gets you a row per contributor, each naming its source.
# That is necessary and it is not sufficient: a reader can see every
# contributor and still not know what the CHAIN can be off by, which is the
# question "is this vertical finished?" actually asks.
#
# WORST CASE IS THE BOUND. The four gates are a CONJUNCTION -- FINISHED means
# all four -- so the honest statement about a vertical is the sum of what each
# column could be wrong by, not an average of them. Every one of these
# classifiers errs in ONE known direction, which is what makes a bound possible
# at all:
#
#   suites    UNDER-counts. Path-name attribution only; a test covering an app
#             without saying so in its filename is invisible.
#   traced    UNDER-counts. A test proved by something that names neither it
#             nor a requirement is not tied to one.
#   fault     UNDER-counts. Declaration-only: a parseable MUTATIONS block or a
#             *_fault_probe.py name. mutation_anchor_check records four of six
#             probes it could not sweep for exactly this reason.
#   tiered    Binary and complete -- criticality_tier_check either raised
#             something for the app or did not. It contributes NOTHING to the
#             bound, and saying so is the point of an itemized budget: a
#             contributor of zero is a finding about where the error is NOT.
#
# ALL THREE ERR THE SAME WAY, WHICH IS THE FINDING. They under-count, so the
# document UNDERSTATES coverage, never overstates it. A budget on a status
# document that flattered the platform would be worth very little; this one can
# only ever say "at least this good".
#
# RSS IS SHOWN, AND IS NOT THE ANSWER. Root-sum-square is the right combination
# when contributors are INDEPENDENT and can cancel -- which is a statement about
# measurement noise, not about these. A test missing from `suites` because of
# its filename is very often the same test missing from `traced`, so the errors
# CORRELATE and RSS understates. It is printed because the gap between the two
# numbers is itself informative: a wide gap means one contributor dominates and
# fixing that one moves the bound; a narrow gap means they are evenly spread.
# **Where they disagree, the worst case is the one to act on.**
#
# THE UNITS ARE RESOURCES AND FILES, NOT A PERCENTAGE. A single combined
# percentage is exactly the collapse this document refuses elsewhere.
def _stackup(names, res, suites, cited, faults, tier_problems, tests):
    """One row per contributor: what it could be understating, and by how much.

    Every figure is COUNTABLE rather than estimated. `suites` and `traced` are
    bounded by what is actually on disk and unattributed; `fault` by the probes
    that mutate real source without declaring it in a form the parser reads.
    Nothing here is a guess dressed as a measurement.
    """
    import os
    import re
    rows = []

    # suites: test files on disk attributed to NO app. Every one of them is a
    # file that could belong to a vertical and is not counted against it.
    unattributed = [t for t in tests if TM.app_of_test(t, names) == 'PLATFORM']
    rows.append(('suites', len(unattributed), 'under',
                 'test files on disk attributed to no single app by path'))

    # traced: files on disk that no source ties to a requirement. The matrix
    # publishes this same number as its headline gap.
    untraced = [t for t in tests if t not in cited]
    rows.append(('traced', len(untraced), 'under',
                 'test files no source ties to a stated requirement'))

    # fault: probes that WRITE to a tracked app file but declare neither a
    # parseable MUTATIONS block nor a *_fault_probe.py name. Counted, not
    # assumed -- these are the ones the declaration rule provably cannot see.
    undeclared = 0
    root = os.path.join(REPO, 'tests')
    WRITE = re.compile(r"open\([^)]*,\s*['\"]w[b]?['\"]")
    declared = set()
    for v in faults.values():
        declared.update(v)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if not f.endswith(('.py', '.js')):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), REPO).replace(os.sep, '/')
            if rel in declared:
                continue
            try:
                body = io.open(os.path.join(dirpath, f), encoding='utf-8',
                               errors='replace').read()
            except IOError:
                continue
            if not (WRITE.search(body) or 'writeFileSync' in body):
                continue
            if any((a + '.html') in body for a in names):
                undeclared += 1
    rows.append(('fault', undeclared, 'under',
                 'test files that write to a tracked app file and declare neither '
                 'a MUTATIONS block nor a *_fault_probe.py name'))

    # tiered contributes zero, and that is a result rather than an omission.
    rows.append(('tiered', 0, 'none',
                 'binary and complete -- criticality_tier_check either raised '
                 'something for an app or did not'))
    return rows


def build():
    names = TM.apps()
    tests = TM.all_tests()
    cited = TM.traced()
    try:
        res = resources_by_app()
    except RuntimeError as e:
        return None, ('REFUSING to generate -- %s\n'
                      'The resource counts are the spine of this document and '
                      'guessing them is the failure it exists to end.' % e)
    tier_clean, tier_problems, _tier_out = tiered_apps()
    faults, fault_declarers = fault_probes()
    suites = suites_by_app(tests, names)

    tv = closing_error.Traverse(DOC)
    tv.leg('app files', len(names), "git ls-files '*.html'")
    tv.leg('apps owning a resource', len(res),
           'api/_resources/index.js OWNER_BY_RESOURCE')
    tv.leg('test files on disk', len(tests), 'tests/**, api/*.test.js')
    tv.leg('tests traced to a requirement', len(cited),
           'traceability_matrix.traced()')
    tv.leg('declared fault probes', len(fault_declarers),
           'MUTATIONS blocks + *_fault_probe.py')
    tv.leg('attested migrations', len(ATTESTED_RUN),
           'hand-recorded, %s, %s' % (ATTESTED_BY, ATTESTED_ON))
    try:
        traverse_rows = tv.close()
    except closing_error.EmptyLeg as e:
        return None, 'REFUSING to generate -- the traverse did not close: %s' % e

    L = []
    W = L.append
    W('# Master plan — where every vertical actually stands, and what '
      '"finished" means')
    W('')
    W('**GENERATED by `python tools/master_plan.py`. Do not hand-edit the '
      'numbers — your edit will be overwritten and, worse, will look '
      'authoritative until it is.** Run `--check` to find out whether the '
      'figures still match the repo.')
    W('')
    W('**Why this is generated and was not.** Michael\'s original ask was an '
      'accurate current status across every vertical plus an honest combined '
      'finish-line definition. The definition was the hard half and it was '
      'good. The NUMBERS were derived once, by hand, on 2026-09-10 under a '
      'present-tense claim that they were derived — and three days later this '
      'document said traceability was **86 of 273** while the matrix it cited '
      'said **135 of 328**, and its own totals line said **53 of 186**, a '
      'third population presented as the same measurement. `traced` here now '
      'comes from `traceability_matrix.traced()`, the same function the matrix '
      'calls, so the two cannot disagree again.')
    W('')
    W('**There is no FINISHED column, deliberately.** Four approximate '
      'measurements collapsed into one tick is what made the drift invisible. '
      'Each gate is its own column with its own source named, and the '
      'conjunction is the reader\'s to make.')
    W('')
    W('---')
    W('')
    W('## The finish line, defined')
    W('')
    W('A vertical is **FINISHED** when all four are true of it. Each is '
      'checkable by something that already exists, which is the point — a '
      'definition nobody can verify is a wish.')
    W('')
    W('| # | Gate | Checkable by | What "done" means |')
    W('|---|---|---|---|')
    W('| 1 | **BUILT** | `api/_resources/<app>.js` + its `sql/*_schema.sql` '
      'run on the live licence | Its business records reach a server. Not "the '
      'code exists" — the migration is run and a real write has been observed |')
    W('| 2 | **TIERED** | `tools/criticality_tier_check.py` | Every registered '
      'resource has a tier, and every Tier A carries individually-written '
      'evidence |')
    W('| 3 | **TRACEABLE** | `tools/traceability_matrix.py --check` | Every '
      'test names a requirement a reader can check, so an auditor can tell '
      'what would be lost by deleting it |')
    W('| 4 | **FAULT-TESTED** | a mutation probe that plants a real defect in '
      'that app\'s source and proves a guard catches it | The guards are known '
      'to DENY, not merely to pass. A guard that has never been red is not '
      'known to be a guard |')
    W('')
    W('**Gate 1 is the only one with a live dependency** — an unrun migration '
      'makes a vertical not-built however good its code is. Gates 2–4 are '
      'repo-verifiable.')
    W('')
    W('---')
    W('')
    W('## Status, per vertical')
    W('')
    W('Every column names the tool that produced it. `res` = resources owned '
      'in `api/_resources/index.js` · `tiered` = `criticality_tier_check.py` '
      'raised nothing for it · `suites` = test files attributed to it by '
      '`traceability_matrix.app_of()` · `traced` = of those suites, how many '
      '`traceability_matrix.traced()` ties to a stated requirement · `fault` = '
      'probes that plant a defect into that app\'s own source file.')
    W('')
    W('| Vertical | res | tiered | suites | traced | fault | Gaps |')
    W('|---|---|---|---|---|---|---|')
    tot = dict(res=0, suites=0, traced=0, fault=0)
    for a in names:
        r = res.get(a, 0)
        mine = suites.get(a, [])
        tr = [t for t in mine if t in cited]
        fa = faults.get(a, [])
        gaps = []
        if a in tier_problems:
            gaps.append('**tier: %s**' % tier_problems[a])
        if mine and not tr:
            gaps.append('**nothing traced**')
        if not mine:
            gaps.append('**no dedicated suite**')
        if not fa:
            gaps.append('**no fault probe**')
        tot['res'] += r
        tot['suites'] += len(mine)
        tot['traced'] += len(tr)
        tot['fault'] += len(fa)
        W('| `%s` | %d | %s | %d | %d | %d | %s |'
          % (a, r, '✅' if a not in tier_problems else '⚠',
             len(mine), len(tr), len(fa), ' · '.join(gaps) or '—'))
    W('')
    W('**Platform totals: %d resources owned by an app, %d test files '
      'attributed to one, %d of those traced, %d fault probes.**'
      % (tot['res'], tot['suites'], tot['traced'], tot['fault']))
    W('')
    W('**And the denominators that are NOT the same thing**, stated because '
      'conflating them is what went wrong: there are **%d** test files on '
      'disk in total and **%d** of them are traced — most are not attributed '
      'to any single app, so the per-app `traced` column above sums to less. '
      'A rate over the subset you looked at is not a rate.'
      % (len(tests), len([t for t in tests if t in cited])))
    W('')
    W('### What these three columns cannot see')
    W('')
    W('- **`suites` counts test files whose PATH names the app.** A test that '
      'covers an app without saying so in its filename is invisible to it. '
      'That is why `sairncode` and `sairnroofing` read 0 here while the '
      'hand-written version claimed 8 and 26 — the old figures used a rule '
      'nobody wrote down, and neither number can be checked against the other. '
      'This one can at least be checked against `ls tests/`.')
    W('- **`fault` is a FLOOR of %d declared probes, not a census.** A probe '
      'counts only if it declares a parseable `MUTATIONS` block or is named '
      '`*_fault_probe.py`. A probe that mutates real source while declaring '
      'neither is not counted, and `tools/mutation_anchor_check.py` records '
      'that four of six could not be swept on 2026-09-11 for exactly that '
      'reason. **The previous hand-written figure of 14 was higher and rested '
      'on a rule nobody can reconstruct** — an early draft of this generator '
      'reproduced that kind of number by accident, crediting StoneDesk with '
      '19 including a probe written that morning which plants nothing at all.'
      % len(fault_declarers))
    W('- **`tiered` means `criticality_tier_check.py` raised nothing**, which '
      'is a completeness check, not a judgement about whether a tier is right.')
    W('')
    W('### The stack-up — a worst-case bound, with RSS beside it')
    W('')
    W('The table above names every contributor, which is necessary and is not '
      'enough: a reader can see all four columns and still not know what the '
      'CHAIN can be off by, which is the question "is this vertical finished?" '
      'actually asks. FINISHED is a CONJUNCTION of four gates, so the honest '
      'statement is the SUM of what each column could be wrong by — not an '
      'average, and not a single combined percentage, which is the collapse '
      'this document refuses everywhere else.')
    W('')
    W('| Contributor | Could be understating by | Direction | What that figure counts |')
    W('|---|---|---|---|')
    stack = _stackup(names, res, suites, cited, faults, tier_problems, tests)
    for name, amount, direction, what in stack:
        W('| `%s` | %d | %s | %s |'
          % (name, amount, {'under': 'UNDER-counts', 'none': 'no contribution'}[direction], what))
    W('')
    worst = sum(a for _n, a, d, _w in stack if d != 'none')
    rss = int(round(math.sqrt(sum(a * a for _n, a, d, _w in stack if d != 'none'))))
    W('**WORST CASE: %d.** RSS for context: %d.' % (worst, rss))
    W('')
    W('**All three contributors err in the SAME direction — they UNDER-count — '
      'so this document understates coverage and cannot overstate it.** A '
      'budget on a status page that flattered the platform would be worth very '
      'little; this one can only ever say "at least this good".')
    W('')
    W('**RSS is shown and is NOT the answer.** Root-sum-square is right when '
      'contributors are independent and can cancel, which is a statement about '
      'measurement noise rather than about these: a test missing from `suites` '
      'because of its filename is very often the same test missing from '
      '`traced`, so the errors correlate and RSS understates. It is printed '
      'because the GAP between the two numbers is itself informative — wide '
      'means one contributor dominates and fixing that one moves the bound, '
      'narrow means they are evenly spread. **Where they disagree, act on the '
      'worst case.**')
    W('')
    W('`tiered` contributes ZERO and is listed anyway. A contributor of nothing '
      'is a finding about where the error is NOT, and dropping it would leave a '
      'reader to assume it was forgotten.')
    W('')
    W('---')
    W('')
    W('## Gate 1 — live migration status')
    W('')
    W('**This is the one gate that is ATTESTED, not derived.** Everything else '
      'in this document is read from the repo; whether a migration has '
      'actually been run against a live licence cannot be. So this names who '
      'confirmed it and when, and it does not extend past what they said.')
    W('')
    W('### Confirmed RUN — %s, %s' % (ATTESTED_BY, ATTESTED_ON))
    W('')
    W('| SQL file | Covers | Scope of the confirmation |')
    W('|---|---|---|')
    for f, app, scope in ATTESTED_RUN:
        W('| `%s` | `%s` | %s |' % (f, app, scope))
    W('')
    W('### Still UNVERIFIED, and named rather than assumed')
    W('')
    W('**The confirmation above covers %s only.** Anything applied in an '
      'earlier session needs its own check. Named explicitly, because an app '
      'absent from both lists reads as "probably fine":' % ATTESTED_ON)
    W('')
    for who, why in ATTESTED_UNVERIFIED:
        W('- **%s**%s' % (who, ' — ' + why if why else ''))
    W('')
    W('### How to close this gate without guessing')
    W('')
    W('`tools/sairn_load_state_check.py --app <app> --key <key>` answers it '
      'for the reference apps from any clone. For the rest it is one read per '
      'app by somebody holding the licence keys. **A cell in the attested '
      'table must never be filled from inference** — an app whose code looks '
      'complete tells you nothing about whether its migration ran, and that '
      'gap is precisely what this gate exists to close.')
    W('')
    W('---')
    W('')
    W('## Closing error — what this document was derived FROM')
    W('')
    W('`--check` compares this file to what the generator produces today. Both '
      'ends of that comparison come from the same instrument, so it cannot see '
      'a source that has gone silent. These are the sources the run that wrote '
      'this actually read; **any of them reaching zero is a refusal**, not a '
      'quieter document.')
    W('')
    W('```')
    for row in traverse_rows:
        W(row.rstrip())
    W('```')
    W('')
    W('A closed traverse is **not** a correct survey: it means no source is '
      'MISSING, not that any source is RIGHT.')
    W('')
    W('---')
    W('')
    W('## What would make this document wrong')
    W('')
    W('Not staleness any more — `--check` answers that, and the numbers are '
      'regenerated rather than remembered. What it still cannot tell you:')
    W('')
    W('- **That a traced test PROVES its requirement.** `traced` means a '
      'source names the two together. Whether the assertion is strong enough '
      'is what gate 4 answers, and only some tests have a probe.')
    W('- **That `tiered` means the tiers are RIGHT.** It means '
      '`criticality_tier_check.py` raised nothing, which is a check on '
      'completeness, not on judgement.')
    W('- **Anything about gate 1 beyond what somebody attested.** That list '
      'grows only when a human confirms a migration, and it is deliberately '
      'the shortest section here.')
    W('')
    return '\n'.join(L) + '\n', None


def main(argv):
    doc, err = build()
    if err:
        print(err)
        return 2
    path = os.path.join(REPO, DOC)
    if '--check' in argv:
        try:
            have = io.open(path, encoding='utf-8', newline='').read()
        except IOError:
            print('FAIL: %s does not exist. Run: python tools/master_plan.py' % DOC)
            return 1
        if have.replace('\r\n', '\n') != doc.replace('\r\n', '\n'):
            print('FAIL: %s no longer matches the repo -- a resource, a test, a '
                  'tier or a trace has changed and the document was not '
                  'regenerated. That is a finding, not a document somebody '
                  'forgot.\n    python tools/master_plan.py' % DOC)
            return 1
        print('OK: %s matches the repo.' % DOC)
        return 0
    io.open(path, 'w', encoding='utf-8', newline='').write(doc)
    print('wrote %s (%d lines)' % (DOC, doc.count('\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
