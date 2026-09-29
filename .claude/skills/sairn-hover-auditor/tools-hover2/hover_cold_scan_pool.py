#!/usr/bin/env python
"""hover_cold_scan_pool.py (hover2's own independent build) -- Tier B/C
resources this role has never once looked at, to counter the structural
bias toward whatever Tier A work is loudest (open obligations, active
claims, fresh review commits). Tier B/C work makes no noise on its own; a
rotation that only follows the loudest signal never reaches it by design.

Built from the CONTRACT in hover-interface-specs-2026-09-22.md #3, not from
hover1's source. Two things done deliberately DIFFERENTLY from what the
contract discloses as hover1's own limits, because the contract explicitly
invites it and a shared method would correlate the two auditors' blind
spots instead of covering for them:

  * REAL RANDOMISATION. hover1's own pool prints the cold list and leaves
    picking to a human/agent glance -- no enforced draw. This tool draws
    with `secrets.choice` (or a risk-weighted draw, `--weighted`) so a
    reader cannot unconsciously always reach for the same-looking names.
  * RISK-WEIGHTED SAMPLING (`--weighted N`). UPGRADED 2026-09-27, closing a
    real capability gap this role's own self-audit named (seq 252): the
    weight now comes from `defect_density_weighting.py` -- real, empirical,
    where-findings-have-actually-landed density per app -- not the crude
    static substring pattern this flag used before that date. Same
    coordinator-directed POLICY SKILL.md's Rotation section describes for
    H1's tool (empirical, real-finding-history-derived weighting); own,
    independent CODE (never read H1's source). ONE DELIBERATE SCOPING
    DECISION, disclosed rather than silently under-delivered: this build
    keeps WEIGHTED-RANDOM SAMPLING (draw() below), not the deterministic
    sorted-top-N mechanic SKILL.md describes for H1's tool. FAIL-CLOSED,
    but SCOPED to what actually depends on the new instrument: `--weighted`
    refuses (exit 2, naming the tool) if defect_density_weighting.py
    cannot be loaded or its own fixture lock fails; `--draw` (genuinely
    unweighted) and the plain cold/warm report do not depend on it and
    keep working.
  * FRESHNESS FLOOR ON THE SAME SCORE, added the SAME day the weighting
    above shipped -- CONFIRMED as a real defect, not assumed: the very
    first real weighted draw (seq 255) drew mech_docs AND mech_takeoffs
    together, both from sairnmechanical's own 7-resource pool boosted 5x
    by that app's density, and every batch after kept re-serving the same
    small already-just-read set, because the weight carried no memory of
    "nothing has changed since I looked at this." `is_floor_suppressed()`
    checks `git log -S <name> --since=<last self-log mention> --
    <app>.html api/sd-data.js` and, ONLY on a confirmed-empty result, caps
    that resource's weight at the SAME floor an unmapped/zero-density
    resource already gets -- one combined score, not a second bucket
    alongside it. FAIL-OPEN on every uncertain case (never mentioned,
    unmapped/shared resource, git unavailable or the call fails) -- staying
    eligible is the safe default here, because being drawn again when
    nothing changed costs a slot, not a missed real signal, which is the
    opposite asymmetry from every OTHER fail-closed rule in this codebase
    and is named as exactly that rather than left to look like an
    inconsistency. REAL, DISCLOSED COST: up to one `git log` subprocess per
    pool member the first time each is weighed (memoized after, so a
    single draw call never re-checks the same name twice) -- measured at
    ~13s for a full 124-resource rolling re-scan against the real repo.
    Acceptable for a batch tool run once per rotation round, not an
    interactive one; named rather than left as an unexplained slowdown.

"COLD"/"WARM", per the contract: a B/C resource name is cold if it appears
as a whole word in NONE of this role's OWN self-log's `summary`, `ref` and
`target` fields, across every entry, ever. It is warm if it appears in ANY
of the three, in any context -- including a resource merely cited as a
COMPARISON PRECEDENT while writing up a finding about something else
entirely (a known false-negative risk the contract names as already
confirmed real against hover1's own log; disclosed here rather than
silently fixed, matching the contract's own choice to accept the coarser
signal and name the tradeoff instead of solving it).

Run:
  python hover_cold_scan_pool.py                -- full cold/warm report
  python hover_cold_scan_pool.py --draw 5        -- a real random draw of 5 cold names
  python hover_cold_scan_pool.py --weighted 5     -- risk-weighted draw of 5
  python hover_cold_scan_pool.py --tiers-md PATH  -- override CRITICALITY-TIERS.md path
  python hover_cold_scan_pool.py --selftest       -- fixture-based self-check

ROLLING RE-SCAN, added 2026-09-23 once the first pass emptied the cold
pool entirely (0 cold of 214, confirmed the same day). STANDING POLICY
(Michael, 2026-09-22, restated when the first pass completed): coverage
does not stop once every resource has been seen once -- re-draw from the
FULL pool on a rolling basis, same as the no-historical-exclusion policy
already named in read_self_log()'s own docstring, extended to mean
"finished once" is not "finished". `--draw`/`--weighted` fall back to
drawing from cold+warm together, UNCHANGED SAMPLING MECHANICS (still
secrets-backed, still optionally risk-weighted), the MOMENT cold is
empty -- never silently returning zero results and calling that a report.
The draw output says ROLLING RE-SCAN rather than RANDOM/WEIGHTED DRAW so
a log entry citing this output is never mistaken for a first-look finding
by a later reader -- a resource drawn this way has been read before by
this role and is being checked again, not discovered for the first time.
"""
import io
import json
import os
import re
import secrets
import sys

REPO_CANDIDATES = (
    'C:/Users/marsh/Documents/SAIRN-hover2',
    'C:/Users/marsh/Documents/SAIRN-hover',
)
SELF_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'hover-audit-log.jsonl')

# The platform's own row shape for docs/CRITICALITY-TIERS.md, reused rather
# than reinvented -- the identical pattern this session already cited from
# tools/removal_path_check.py / hover_cold_scan_pool.py's own TIER_ROW
# comment while writing the two-axis spec doc, so a drift in the register's
# format breaks one pattern everyone shares rather than two that can
# silently disagree.
TIER_ROW = re.compile(r"^\|\s*`([a-z][a-z0-9_]*)`\s*\|\s*\*{0,2}([ABC])\*{0,2}\s*\|")
CONFLICT_MARKER_RE = re.compile(r'^(<{7}|={7}|>{7})', re.M)

SENSITIVITY_RE = re.compile(
    r'price|invoice|ssn|dob|patient|payroll|account|credential|ledger|trust',
    re.I)

# WEIGHT-TRANSFORM CONSTANT, REASONED not calibrated (same disclosure
# standard as every other uncalibrated constant this role's tooling
# carries): observed real density values this run span roughly 0.0-0.43,
# so *10 lands weights in a roughly 1-5 integer range -- a modest, not
# extreme, risk tilt. Revisit once real repeat-gap history exists to
# calibrate against, same as the sweep-cadence and narrowing-threshold
# constants already disclose.
DENSITY_WEIGHT_SCALE = 10


def load_density_weighter(here=None):
    """-> (weight_of_fn, err). Loads defect_density_weighting.py BESIDE this
    file (same directory, same discipline TIER_ROW's reuse-not-duplicate
    comment already states) and runs ITS OWN fixture lock before trusting
    it -- a dependency that has not proven itself is not trusted just
    because the file exists. err is set (weight_of_fn is None) on any
    failure; the caller decides whether that means refuse or fall back."""
    here = here or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, 'defect_density_weighting.py')
    if not os.path.isfile(path):
        return None, 'defect_density_weighting.py not found at %s' % path
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location(
            'defect_density_weighting', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        return None, 'defect_density_weighting.py failed to load (%s)' % e
    try:
        import io as _io
        import contextlib
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod._selftest()
    except Exception as e:
        return None, ('defect_density_weighting.py raised running its own '
                      'fixture lock (%s)' % e)
    if rc != 0:
        return None, ("defect_density_weighting.py's own fixture lock did "
                      'not pass -- refusing to trust an unproven instrument')
    resource_to_app, app_density_count, rerr = mod.load_app_registry(
        _repo_for_density())
    if rerr:
        return None, 'defect_density_weighting.py could not derive apps (%s)' % rerr
    entries = read_self_log()
    if entries is None:
        return None, 'self-log unreadable -- cannot compute real density'
    result = mod.density(entries, resource_to_app, app_density_count)
    density_by_app = {app: d for app, d, _n in result['ranking']}
    repo = _repo_for_density()
    floor_cache = {}

    def weight_of_empirical(name):
        app = resource_to_app.get(name)
        d = density_by_app.get(app, 0.0) if app else 0.0
        base = 1 + round(d * DENSITY_WEIGHT_SCALE)
        if base <= FLOOR_WEIGHT:
            return base  # already at floor; no point checking freshness
        if name not in floor_cache:
            floor_cache[name] = is_floor_suppressed(name, entries, resource_to_app, repo)
        return FLOOR_WEIGHT if floor_cache[name] else base

    return weight_of_empirical, None


# FRESHNESS FLOOR, added 2026-09-27 -- CONFIRMED FIRST, not assumed: the
# very first real draw under empirical-density weighting (seq 255) drew
# mech_docs AND mech_takeoffs together, both from sairnmechanical's own
# 7-resource pool boosted 5x by that app's density -- and every batch since
# has kept re-serving the same small set of already-just-read resources,
# because nothing in the weight carried any memory of "already looked at
# this, nothing has changed since." A resource with NO real code change
# since it was last read adds no new information no matter how high its
# app's density score is -- re-drawing it spends a draw slot confirming
# something already confirmed rather than looking at something new.
FLOOR_WEIGHT = 1  # same baseline an unmapped/zero-density resource gets


def last_mention_ts(name, self_log_entries):
    """-> the ts (str) of the MOST RECENT self-log entry whole-word-matching
    `name` in summary/ref/target, or None if never mentioned. Reuses
    is_warm()'s own match definition so 'has this been read' and 'when was
    it last read' can never quietly disagree with each other."""
    pat = _whole_word_re(name)
    latest = None
    for e in self_log_entries or ():
        for field in ('summary', 'ref', 'target'):
            v = e.get(field) or ''
            if pat.search(v):
                ts = e.get('ts')
                if ts and (latest is None or ts > latest):
                    latest = ts
                break
    return latest


def resource_app_file(name, resource_to_app):
    """-> 'appname.html' or None. 'shared' resources and unmapped names
    return None -- checking every app that could possibly use a shared
    resource is real future work, not this fix; None means 'unknown,'
    which is_floor_suppressed() below treats as fail-open (NOT suppressed,
    stays fully eligible), never as suppressed-by-default."""
    app = resource_to_app.get(name)
    if not app or app == 'shared':
        return None
    return app + '.html'


def _run_git(repo, *args):
    import subprocess
    try:
        r = subprocess.run(['git'] + list(args), cwd=repo,
                          capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=15)
    except Exception:
        return None, None
    return (r.stdout, None) if r.returncode == 0 else (None, r.stderr)


def is_floor_suppressed(name, self_log_entries, resource_to_app, repo):
    """True ONLY on POSITIVE evidence that nothing touching `name` has
    changed since it was last read -- `git log -S name --since=<last
    mention> -- <app>.html api/sd-data.js` ran successfully and returned
    genuinely empty. FAIL-OPEN on every uncertain case (never mentioned,
    unmapped/shared resource, git unavailable, git call failed) -- floor
    suppression needs proof of 'nothing changed,' and an absence of proof
    is not that proof, matching this role's own standing rule that a
    could-not-tell is never folded into a pass in the OTHER direction
    either: here, staying ELIGIBLE is the safe default, not the risky one,
    because being drawn again when nothing changed costs a slot, not a
    missed real signal."""
    ts = last_mention_ts(name, self_log_entries)
    if not ts:
        return False
    app_file = resource_app_file(name, resource_to_app)
    if not app_file:
        return False
    out, err = _run_git(repo, 'log', '-S', name, '--since=%s' % ts,
                        '--oneline', '--', app_file, 'api/sd-data.js')
    if out is None:
        return False
    return out.strip() == ''


def _repo_for_density():
    for candidate in REPO_CANDIDATES:
        if os.path.isdir(os.path.join(candidate, 'api', '_resources')):
            return candidate
    return REPO_CANDIDATES[0]

_WORD_CACHE_RE = {}


def _whole_word_re(name):
    r = _WORD_CACHE_RE.get(name)
    if r is None:
        r = re.compile(r'\b' + re.escape(name) + r'\b')
        _WORD_CACHE_RE[name] = r
    return r


def find_tiers_md(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if '--tiers-md' in argv:
        i = argv.index('--tiers-md')
        if i + 1 < len(argv):
            return argv[i + 1]
    for candidate in REPO_CANDIDATES:
        p = os.path.join(candidate, 'docs', 'CRITICALITY-TIERS.md')
        if os.path.isfile(p):
            return p
    return None


def parse_bc_resources(path):
    """[(name, tier)] for every B/C row, in file order. None, problem if the
    file could not be read at all, OR carries unresolved git conflict
    markers -- CONFIRMED a real, silent gap by driving it directly, not
    assumed: a conflicted CRITICALITY-TIERS.md with sd_comms as B on one
    side and A on the other returned [('sd_comms','B')] with ZERO error,
    silently picking whichever side TIER_ROW happened to match first and
    giving no signal the resolved truth might be different. Refuses the
    whole read now, same fail-closed shape as
    defect_density_weighting.py's identical fix for api/_resources/*.js."""
    try:
        text = io.open(path, encoding='utf-8').read()
    except OSError as exc:
        return None, 'could not read %s: %s' % (path, exc)
    if CONFLICT_MARKER_RE.search(text):
        return None, ('%s carries unresolved git conflict markers -- '
                     'refusing to parse a corrupted register rather than '
                     'silently picking whichever side a row pattern '
                     'happens to match first' % path)
    out = []
    for line in text.split('\n'):
        m = TIER_ROW.match(line)
        if m and m.group(2) in ('B', 'C'):
            out.append((m.group(1), m.group(2)))
    return out, ''


def read_self_log(path=None):
    """DELIBERATELY reads only THIS session's own log, never hover1's, and
    never treats "the other instance probably already looked at this" or
    "this predates hover2 existing" as a reason to mark anything warm.
    STANDING POLICY (Michael, 2026-09-22): historical/pre-hover2 coverage is
    folded into the SAME weighted sampling as everything else, a little at a
    time, not excluded and not swept separately. A resource genuinely is
    cold from THIS session's perspective until THIS session's own log says
    otherwise -- institutional history is not a substitute for an actual
    independent look."""
    path = path or SELF_LOG_PATH
    if not os.path.isfile(path):
        return None
    entries = []
    try:
        with io.open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except (OSError, ValueError):
        return None
    return entries


def is_warm(name, self_log_entries):
    """True if `name` appears as a whole word in ANY of summary/ref/target
    across ANY entry. self_log_entries=None (unreadable log) is treated as
    "nothing is warm" -- an unreadable log is not evidence anything has been
    checked, so nothing should read as safely covered."""
    if not self_log_entries:
        return False
    pat = _whole_word_re(name)
    for e in self_log_entries:
        for field in ('summary', 'ref', 'target'):
            v = e.get(field) or ''
            if pat.search(v):
                return True
    return False


def build_pool(tiers_md_path, self_log_path=None):
    """(cold, warm, problem). cold/warm are [(name, tier)]; problem non-empty
    means the tier register could not be read at all (COULD NOT RUN, never
    silently reported as an empty cold pool)."""
    resources, problem = parse_bc_resources(tiers_md_path)
    if resources is None:
        return None, None, problem
    entries = read_self_log(self_log_path)
    cold, warm = [], []
    for name, tier in resources:
        (warm if is_warm(name, entries) else cold).append((name, tier))
    return cold, warm, ('' if entries is not None else
                        'NOTE: self-log unreadable -- every resource reports '
                        'cold by default, which may undercount real coverage '
                        'rather than overcount it.')


def weight_of(name):
    """FALLBACK ONLY as of 2026-09-27 -- kept, never deleted, so a fixture or
    caller that wants the plain static heuristic still can, but main() no
    longer reaches for this by default; see load_density_weighter()."""
    return 3 if SENSITIVITY_RE.search(name) else 1


def draw(cold, n, weighted=False, weight_fn=None):
    """A REAL random draw (secrets.choice-backed), not a printed list left to
    a human glance -- the concrete difference from hover1's own disclosed
    method. Sampling WITHOUT replacement; n capped at len(cold). weight_fn
    defaults to the static weight_of() ONLY when weighted=True and no
    weight_fn is passed -- main() always passes the empirical one or
    refuses first, so this default only matters to a direct caller/fixture
    that wants the plain heuristic on purpose."""
    fn = weight_fn or weight_of
    pool = list(cold)
    n = min(n, len(pool))
    picked = []
    for _ in range(n):
        if not pool:
            break
        if weighted:
            weights = [fn(name) for name, _t in pool]
            total = sum(weights)
            r = secrets.randbelow(total) if total else 0
            acc = 0
            idx = 0
            for i, w in enumerate(weights):
                acc += w
                if r < acc:
                    idx = i
                    break
        else:
            idx = secrets.randbelow(len(pool))
        picked.append(pool.pop(idx))
    return picked


def pick_for_draw(cold, warm, n, weighted=False, weight_fn=None):
    """(picked, rolling). rolling=False draws from `cold` only (a first-look
    draw); rolling=True means cold was empty and the draw fell back to the
    FULL cold+warm pool (a re-scan of already-seen resources, not a first
    look) -- the caller must label its output/log entry accordingly rather
    than let a rolling re-scan read as a fresh discovery draw."""
    if cold:
        return draw(cold, n, weighted=weighted, weight_fn=weight_fn), False
    return draw(cold + warm, n, weighted=weighted, weight_fn=weight_fn), True


def main(argv):
    if '--selftest' in argv:
        return 0 if run_fixtures() else 1
    path = find_tiers_md(argv)
    if not path:
        print('COULD NOT RUN: no docs/CRITICALITY-TIERS.md found under %s '
             'or --tiers-md' % ', '.join(REPO_CANDIDATES))
        return 2
    cold, warm, note = build_pool(path)
    if cold is None:
        print('COULD NOT RUN: %s' % note)
        return 2
    print('HOVER COLD-SCAN POOL -- %d B/C resources, %d cold, %d warm'
         % (len(cold) + len(warm), len(cold), len(warm)))
    if note:
        print(note)
    print('')
    n = None
    weighted = '--weighted' in argv
    flag = '--weighted' if weighted else ('--draw' if '--draw' in argv else None)
    if flag:
        i = argv.index(flag)
        if i + 1 < len(argv):
            try:
                n = int(argv[i + 1])
            except ValueError:
                n = 5
        else:
            n = 5
        weight_fn = None
        if weighted:
            # FAIL-CLOSED, SCOPED: only --weighted depends on the empirical
            # instrument. A refusal here never silently falls back to the
            # old static heuristic -- that would be scoring real risk as
            # though the crude substring pattern were still the truth.
            weight_fn, werr = load_density_weighter()
            if werr:
                print('COULD NOT RUN --weighted: %s. A missing instrument '
                     'is never scored as flat risk -- refusing rather than '
                     'silently falling back to the old static heuristic. '
                     '(exit 2)' % werr)
                return 2
        picked, rolling = pick_for_draw(cold, warm, n, weighted=weighted,
                                        weight_fn=weight_fn)
        if not rolling:
            print('%s DRAW of %d (out of %d cold):' % ('WEIGHTED (empirical density)' if weighted else 'RANDOM', len(picked), len(cold)))
        else:
            print('ROLLING RE-SCAN of %d (cold pool empty -- drawn from the FULL '
                 '%d-resource B/C pool, already-seen names included by design):'
                 % (len(picked), len(cold) + len(warm)))
        for name, tier in picked:
            tag = ''
            if weighted and weight_fn and weight_fn(name) > 1:
                tag = '  [empirical-density-weighted]'
            print('  %s  (%s)%s' % (name, tier, tag))
        return 0
    print('COLD (%d) -- never once appeared in this role\'s own self-log:' % len(cold))
    for name, tier in cold:
        print('  %s  (%s)' % (name, tier))
    return 0


def run_fixtures():
    ok = [0]
    bad = []

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   ' + name)
        else:
            bad.append(name)
            print('  FAIL ' + name)

    ck('TIER_ROW matches a real B row', bool(TIER_ROW.match('| `sd_comms` | **B** | text | evidence |')))
    ck('TIER_ROW matches a real C row', bool(TIER_ROW.match('| `foo_bar` | **C** | text | evidence |')))
    ck('TIER_ROW does not match an A row (out of scope for this pool)',
       TIER_ROW.match('| `sd_exec_msgs` | **A** | text | evidence |').group(2) == 'A')

    import tempfile
    tmpdir = tempfile.mkdtemp()
    tiers_path = os.path.join(tmpdir, 'CRITICALITY-TIERS.md')
    with io.open(tiers_path, 'w', encoding='utf-8') as f:
        f.write('| Resource | Tier | Worst | Evidence |\n')
        f.write('|---|---|---|---|\n')
        f.write('| `sd_comms` | **B** | x | y |\n')
        f.write('| `sd_exec_msgs` | **A** | x | y |\n')  # A row, must be excluded
        f.write('| `sv_soapnotes` | **B** | x | y |\n')
        f.write('| `bld_comm_log` | **C** | x | y |\n')
    resources, problem = parse_bc_resources(tiers_path)
    ck('parse_bc_resources() picks up exactly the B/C rows, excluding the A row',
       not problem and [n for n, _t in resources] == ['sd_comms', 'sv_soapnotes', 'bld_comm_log'])

    log_path = os.path.join(tmpdir, 'log.jsonl')
    with io.open(log_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'summary': 'reviewed sd_comms today', 'ref': '', 'target': ''}) + '\n')
        f.write(json.dumps({'summary': 'unrelated', 'ref': 'checked sv_soapnotes, clean', 'target': ''}) + '\n')

    cold, warm, note = build_pool(tiers_path, log_path)
    ck('sd_comms (mentioned in summary) is WARM',
       ('sd_comms', 'B') in warm)
    ck('sv_soapnotes (whole-word match inside ref text) is WARM',
       ('sv_soapnotes', 'B') in warm)
    ck('bld_comm_log (never mentioned anywhere) is COLD',
       ('bld_comm_log', 'C') in cold)
    ck('cold+warm together account for every B/C row, nothing dropped',
       len(cold) + len(warm) == 3)

    # A REAL platform collision, not an invented "_v2" example: confirmed by
    # scanning docs/CRITICALITY-TIERS.md's real resource names 2026-09-22 --
    # alf_staff / alf_staff_credentials, sc_auth / sc_auth_requests, and
    # stonedesk / stonedesk_quote_history are genuine prefix-collision pairs
    # already on this platform, so the whole-word requirement is defending
    # against a shape that actually occurs, not a hypothetical one.
    ck('is_warm() with a partial-word match (substring, not whole word) is '
       'NOT warm -- a real platform collision pair, alf_staff_credentials, '
       'should not falsely warm alf_staff',
       not is_warm('alf_staff', [{'summary': 'alf_staff_credentials rewritten', 'ref': '', 'target': ''}]))
    ck('is_warm() returns False (not crash) on a None self-log', is_warm('x', None) is False)

    missing_path = os.path.join(tmpdir, 'does-not-exist.md')
    resources2, problem2 = parse_bc_resources(missing_path)
    ck('parse_bc_resources() on a missing file reports a problem, not an '
       'empty-but-clean result', resources2 is None and problem2)

    # KNOWN-BAD CONTROL, conflict-marker sweep, 2026-09-28: must FAIL
    # (refuse) on a real conflicted register, not silently parse one side.
    conflicted_path = os.path.join(tmpdir, 'conflicted-TIERS.md')
    with io.open(conflicted_path, 'w', encoding='utf-8') as f:
        f.write('| Resource | Tier | Worst | Evidence |\n|---|---|---|---|\n')
        f.write('<<<<<<< HEAD\n| `sd_comms` | **B** | x | y |\n=======\n')
        f.write('| `sd_comms` | **A** | x | y |\n>>>>>>> branch\n')
    resources3, problem3 = parse_bc_resources(conflicted_path)
    ck('KNOWN-BAD CONTROL: a register with unresolved conflict markers is '
       'refused (None, problem), never silently parsed as one side or the '
       'other',
       resources3 is None and problem3 and 'conflict' in problem3.lower())

    ck('weight_of() weights a sensitivity-pattern name higher',
       weight_of('sd_negotiated_prices') > weight_of('sd_photos'))

    drawn = draw([('a', 'B'), ('b', 'B'), ('c', 'B')], 2)
    ck('draw() returns the requested count without replacement',
       len(drawn) == 2 and len(set(n for n, _t in drawn)) == 2)
    ck('draw() caps at the pool size rather than erroring',
       len(draw([('a', 'B')], 5)) == 1)
    ck('draw() on an empty pool returns empty, not a crash',
       draw([], 3) == [])

    some_cold = [('a', 'B'), ('b', 'B')]
    some_warm = [('c', 'B'), ('d', 'C')]
    p1, roll1 = pick_for_draw(some_cold, some_warm, 5)
    ck('pick_for_draw() draws from cold only while cold is non-empty, and '
       'reports rolling=False',
       roll1 is False and set(n for n, _t in p1) <= set(n for n, _t in some_cold))
    p2, roll2 = pick_for_draw([], some_warm, 5)
    ck('pick_for_draw() falls back to the FULL pool once cold is empty, and '
       'reports rolling=True so the caller never mislabels a re-scan as a '
       'first look',
       roll2 is True and set(n for n, _t in p2) == set(n for n, _t in some_warm))
    p3, roll3 = pick_for_draw([], [], 5)
    ck('pick_for_draw() on a fully empty pool (cold and warm both empty) '
       'returns empty rather than crashing',
       p3 == [] and roll3 is True)

    # load_density_weighter() fail-closed fixtures, 2026-09-27.
    empty_dir_fn, empty_dir_err = load_density_weighter(here=tmpdir)
    ck('load_density_weighter() refuses (does not fabricate a weighter) '
       'when defect_density_weighting.py is absent from the given directory',
       empty_dir_fn is None and empty_dir_err)

    real_here = os.path.dirname(os.path.abspath(__file__))
    real_fn, real_err = load_density_weighter(here=real_here)
    ck('load_density_weighter() against the REAL directory succeeds and '
       'returns a callable that never raises on an unmapped name',
       real_err is None and callable(real_fn) and real_fn('not_a_real_resource_xyz') == 1)

    # FRESHNESS FLOOR fixtures, 2026-09-27, driven against a REAL throwaway
    # git repo (not a mock) -- same "drive it, don't mock it" discipline as
    # every other checker in this codebase.
    ck('last_mention_ts() returns None for a name never mentioned anywhere',
       last_mention_ts('never_mentioned_xyz', [{'summary': 'x', 'ts': '2026-01-01T00:00:00Z'}]) is None)
    ck('last_mention_ts() picks the LATEST of multiple mentions, not the first',
       last_mention_ts('res_x', [
           {'target': 'res_x', 'ts': '2026-01-01T00:00:00Z'},
           {'summary': 'unrelated', 'ts': '2026-02-01T00:00:00Z'},
           {'ref': 'res_x re-checked', 'ts': '2026-03-01T00:00:00Z'},
       ]) == '2026-03-01T00:00:00Z')
    ck("resource_app_file() returns None for 'shared' and for an unmapped name",
       resource_app_file('res_y', {'res_y': 'shared'}) is None
       and resource_app_file('never_mapped', {}) is None)
    ck("resource_app_file() derives 'app.html' from the resource->app map",
       resource_app_file('res_z', {'res_z': 'someapp'}) == 'someapp.html')

    fresh_dir = tempfile.mkdtemp()
    genv = dict(os.environ, GIT_AUTHOR_NAME='fx', GIT_AUTHOR_EMAIL='fx@x',
               GIT_COMMITTER_NAME='fx', GIT_COMMITTER_EMAIL='fx@x')

    def g(*args, **kw):
        e = dict(genv); e.update(kw.get('env', {}))
        import subprocess as _sp
        r = _sp.run(['git'] + list(args), cwd=fresh_dir, env=e,
                    capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr)
        return r.stdout.strip()

    g('init', '-q')
    with io.open(os.path.join(fresh_dir, 'appx.html'), 'w', encoding='utf-8') as f:
        f.write('res_stale marker\n')
    g('add', '.')
    g('commit', '-q', '-m', 'first',
     env={'GIT_AUTHOR_DATE': '2026-01-01T10:00:00+00:00',
          'GIT_COMMITTER_DATE': '2026-01-01T10:00:00+00:00'})
    with io.open(os.path.join(fresh_dir, 'appx.html'), 'a', encoding='utf-8') as f:
        f.write('res_changed touched here\n')
    g('add', '.')
    g('commit', '-q', '-m', 'second, touches res_changed',
     env={'GIT_AUTHOR_DATE': '2026-06-01T10:00:00+00:00',
          'GIT_COMMITTER_DATE': '2026-06-01T10:00:00+00:00'})

    r2a = {'res_stale': 'appx', 'res_changed': 'appx', 'res_unmapped_shared': 'shared'}
    last_read = '2026-03-01T00:00:00Z'  # between the two commits above
    entries_stale = [{'target': 'res_stale', 'ts': last_read}]
    entries_changed = [{'target': 'res_changed', 'ts': last_read}]

    ck('is_floor_suppressed() TRUE (suppressed) when git confirms NO commit '
       "touched this resource's own file since its last read -- the "
       'POSITIVE case',
       is_floor_suppressed('res_stale', entries_stale, r2a, fresh_dir) is True)
    ck('is_floor_suppressed() FALSE (stays eligible) when a REAL commit '
       "since the last read DID touch the resource's file -- the "
       'NEGATIVE case, driven against a real second commit, not asserted',
       is_floor_suppressed('res_changed', entries_changed, r2a, fresh_dir) is False)
    ck('is_floor_suppressed() FALSE (fail-open) for a shared/unmapped '
       'resource -- no positive proof of "nothing changed" is possible',
       is_floor_suppressed('res_unmapped_shared', entries_stale, r2a, fresh_dir) is False)
    ck('is_floor_suppressed() FALSE (fail-open) for a resource never '
       'mentioned in the self-log at all',
       is_floor_suppressed('res_stale', [], r2a, fresh_dir) is False)
    ck('is_floor_suppressed() FALSE (fail-open) when git itself cannot run '
       '(bad repo path) -- uncertainty never suppresses',
       is_floor_suppressed('res_stale', entries_stale, r2a,
                          os.path.join(fresh_dir, 'does-not-exist')) is False)

    print('')
    print('%d ok, %d failed' % (ok[0], len(bad)))
    return not bad


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
