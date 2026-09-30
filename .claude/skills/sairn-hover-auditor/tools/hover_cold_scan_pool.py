#!/usr/bin/env python
"""hover_cold_scan_pool.py -- Tier B/C resources this role has never once
mentioned in its own self-log, to pick a genuinely cold target from during
an undirected sweep rather than defaulting to whatever Tier A work is loudest
that round.

BUILT ON DIRECT INSTRUCTION (2026-09-21), item 2 of a five-item queue about
this role's own setup. Same narrow exception as hover_coverage_ledger.py
(item 1, same queue) and every other tool in this directory: this records
and drives this role's OWN sampling coverage, not platform code.

WHY THIS IS A DIFFERENT LIST FROM THE TWO THAT ALREADY EXIST.
seed_corpus.md is a list of TECHNIQUES and recurring bug SHAPES -- how to
look. undirected_sweep_freshness.py tracks WHEN the last undirected pass
happened -- a cadence, not a target. Neither answers WHERE to point an
undirected pass. This role's own rotation material already names the real
risk plainly: Tier A work is loud (open obligations, active build claims,
fresh review commits) and Tier B/C work is not, so a rotation that always
follows the loudest signal will structurally never reach the quiet half of
the platform -- which is exactly how dnt_supplies (Tier B, swept only
because a HIGH finding's shape happened to reach it) and the SF_RESOURCES
session-gate gap (found only because a dispatcher-suite review happened to
name it) were both found: incidentally, not by design.

WHAT COUNTS AS "READ", STRUCTURALLY (2026-09-28 -- the third definition,
see the signal-history block below for the two it replaced and the
measured failure of each). docs/CRITICALITY-TIERS.md is the platform's own
real, hand-maintained tier register (TIER_ROW below is the identical regex
tools/removal_path_check.py already uses to read it -- reused rather than
reinvented, so a change to the register's own row shape only has one regex
to keep in step, not two). A Tier B/C resource is "cold" if NO entry's
`ref` field ever RESOLVED to it: a bare resource name in ref, a file:line
citation landing in the resource's own register row, or a file:line
citation landing in its own storage lines in an app file, resolved at the
source sha the entry recorded. Prose never counts, in any field.

THIS ANSWERS "WAS A CITATION EVER ANCHORED TO IT", NOT "WAS IT PROPERLY
CHECKED" -- a resolved citation proves the entry pointed at this
resource's real rows, not that the reading was any good. The coverage
ledger still owns the stronger question.

STALENESS, FOUND AND FIXED 2026-09-21, same day and same cause as
hover_coverage_ledger.py's identical fix (read that module's docstring for
the full incident) -- REPO was a single hardcoded path to one session's own
clone, so this tool silently read docs/CRITICALITY-TIERS.md out of whichever
clone happened to be hardcoded, not the clone actually running it and not
necessarily the platform's real current state. Lower-frequency-of-change than
the review-commit history the ledger reads, but the same bug in kind: a
resource re-tiered from B/C to A on origin/main would still show up in this
pool's B/C list until that specific hardcoded clone happened to pull.

FIXED THE SAME WAY: discover_repo() replaces the hardcoded constant, and the
tiers file is now read via `git fetch origin --quiet` + `git show
origin/main:docs/CRITICALITY-TIERS.md` rather than opening the local working
tree file directly -- so the answer no longer depends on whether the
discovered clone's working tree happens to be checked out to the same commit
as origin/main. `git show` reads a blob out of the object database; it does
not touch the working tree, so this stays read-only against a clone this role
does not own, the identical discipline the ledger's fetch-not-pull fix uses.

THE "MENTIONED" SIGNAL HAS BEEN REPLACED TWICE, BOTH ON 2026-09-28, EACH
TIME AGAINST A MEASUREMENT, AND EVERY COUNT BELOW NAMES THE SIGNAL IT WAS
TAKEN UNDER because three different signals produced three different
worlds from the same log:
  PROSE (original, retired): summary+ref+target word scan. 0 of 124 ever
    "unmentioned" -- and #584 caught it crediting bld_selections off a
    passing precedent comparison in an UNRELATED finding's prose.
  REF-ONLY BARE NAMES (intermediate, retired the same day it shipped):
    only a bare resource name in `ref` counted. Overcorrected: 115-121 of
    124 read NEVER MENTIONED (count moved as entries landed), because this
    role's real citation habit is file:line, and the floor gate went
    near-inert.
  RESOLVED READS (current): resolved_read_names() -- bare names still
    count, and a file:line citation counts for the resource whose registry
    row or whose own storage lines it lands in, AT THE ENTRY'S RECORDED
    SOURCE SHA. Measured on adoption: 80 of 124 resources have a resolved
    read, 44 never; the most recent credits reproduce the actual audit
    history exactly (each draw's entry resolves to precisely the resources
    it audited). Do not quote these figures -- re-run the measurement.
--pick's cold bucket is therefore a REAL, meaningful set again (the
"permanently exhausted" claim held only under the prose signal), but
`--undirected N` (undirected_order(), added the same day) is
still the real, permanent successor to --pick regardless of bucket size --
pure staleness order, deliberately blind to app risk so it stays a genuine
check on --draw's own bias rather than a quieter copy of it, and it never
exhausts because staleness is RELATIVE (entries since last mention), not an
ever-shrinking "never touched" set. Use --undirected for every undirected
sweep; --pick is kept only so its historical entries (seq 361, 432, 475)
still explain themselves against the signal that was live when they ran.

Run:
  python hover_cold_scan_pool.py            -- full report
  python hover_cold_scan_pool.py --pick N   -- N candidates from the COLD
                                                bucket (EXHAUSTED as of
                                                2026-09-28 -- will report 0)
  python hover_cold_scan_pool.py --undirected N -- N candidates by PURE
                                                STALENESS, blind to risk --
                                                the real undirected-sweep
                                                mechanism, see
                                                undirected_order's docstring
  python hover_cold_scan_pool.py --draw N   -- N candidates by the COMBINED
                                                draw score (risk primary,
                                                coverage secondary -- see
                                                draw_order's docstring)
  python hover_cold_scan_pool.py --repo <path> -- override clone discovery
  python hover_cold_scan_pool.py --selftest -- fixture-based self-check

THE COMBINED DRAW SCORE (--draw), decided by Michael 2026-09-27: the rotation
combines BOTH signals in ONE score at draw time rather than running as two
separate rules. Before this, the two signals were two rules in two places:
--pick served never-mentioned rows only (coverage, and it went silent the day
the cold bucket emptied), and the risk weighting lived in the operator's head
via defect_density_weighting.py's report, with the within-app slice plain
alphabetical. The de-facto cycle-1/2 practice (app by density, rows
alphabetical) approximated the intent but scored nothing; this makes the
formula real, mechanical, and printed on every run:

    order by  (1) app risk, DESC   -- defect_density_weighting.py's
                                      module_density for the resource's app,
                                      consumed over --json, the app resolved
                                      from api/_resources/*.js (derived, not
                                      a hand map -- the app-map lesson)
              (2) staleness, DESC  -- entries since this resource was last
                                      mentioned in the self-log; never
                                      mentioned sorts as +infinity, so cold
                                      rows still lead within their app
              (3) name, ASC        -- the deterministic tiebreak

Lexicographic, not a weighted sum, ON PURPOSE: a sum needs coefficients and
there is no measured basis to set them (the sweep-cadence lesson -- a made-up
coefficient would be laundered into fact by the code). Lexicographic ordering
is coefficient-free and states its priority exactly: risk first, coverage
second, REASONED not calibrated, revisit when there is history to calibrate
from. FAIL-CLOSED: --draw REFUSES (exit 2, naming the tool) if
defect_density_weighting.py is absent or fails its own control, and REFUSES
if api/_resources yields zero apps -- a missing instrument or an empty
derivation source is never scored as all-zero risk (PR 1.11; a check that
depends on another tool must fail CLOSED when that tool is absent).
"""
import io
import json
import os
import re
import subprocess
import sys

# Same list, same order, same reasoning as hover_coverage_ledger.py's
# _KNOWN_CLONES -- kept as a literal duplicate rather than a shared import
# because every tool in this directory is deliberately standalone (no
# hover_*.py imports another one), so a second session can copy a single
# file and have it work with no path-hunting.
_KNOWN_CLONES = (
    'C:/Users/marsh/Documents/SAIRN-hover',
    'C:/Users/marsh/Documents/SAIRN-hover2',
)
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'hover-audit-log.jsonl')
TIERS_REL_PATH = 'docs/CRITICALITY-TIERS.md'

# Identical to tools/removal_path_check.py's TIER_ROW -- reused, not
# reinvented, so the platform's own register format only has one reader.
TIER_ROW = re.compile(r'^\|\s*`([a-z][a-z0-9_]*)`\s*\|\s*\*{0,2}([ABC])\*{0,2}\s*\|')


def discover_repo(argv=None):
    """Identical contract to hover_coverage_ledger.py's discover_repo() --
    --repo, then $HOVER_LEDGER_REPO, then the first existing known clone,
    then None (COULD NOT TELL). See that module for the incident this closes."""
    argv = sys.argv[1:] if argv is None else argv
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 < len(argv):
            return argv[i + 1]
    env = os.environ.get('HOVER_LEDGER_REPO')
    if env:
        return env
    for candidate in _KNOWN_CLONES:
        if os.path.isdir(os.path.join(candidate, '.git')):
            return candidate
    return None


class NoRepo(Exception):
    pass


def _parse_all_names(text):
    """EVERY registered resource name, all tiers -- the ownership
    vocabulary resolve_citation() decides nearest-owner against (its seq
    280 fix: a Tier A owner must WIN ownership, then credit nobody)."""
    out = set()
    for line in text.splitlines():
        m = TIER_ROW.match(line.strip())
        if m:
            out.add(m.group(1))
    return out


def _parse_tier_rows(text):
    """[(resource, tier)] for every Tier B or C row in raw tiers-file TEXT.
    Pure -- no I/O, so the self-test can drive it directly against a literal
    string with no filesystem or git involved."""
    out = []
    for line in text.splitlines():
        m = TIER_ROW.match(line.strip())
        if m and m.group(2) in ('B', 'C'):
            out.append((m.group(1), m.group(2)))
    return out


def read_tiers_text(repo):
    """The real docs/CRITICALITY-TIERS.md content, as of origin/main, not as
    of whatever the discovered clone's working tree happens to be checked
    out to. Fetches first (read-only); reads via `git show`, which pulls a
    blob out of the object database and never touches the working tree --
    safe against a clone this role does not own, same as review_commits()'s
    fetch-not-pull discipline in hover_coverage_ledger.py."""
    if not repo or not os.path.isdir(repo):
        raise NoRepo('no readable clone: %r (checked --repo, '
                      '$HOVER_LEDGER_REPO, and %s)' % (repo, ', '.join(_KNOWN_CLONES)))
    try:
        subprocess.run(['git', 'fetch', 'origin', '--quiet'],
                        cwd=repo, capture_output=True, text=True,
                        encoding='utf-8', check=True)
    except subprocess.CalledProcessError as e:
        # Same contract fix as hover_coverage_ledger.py's review_commits():
        # a failed fetch must route through NoRepo/"COULD NOT RUN", not an
        # uncaught traceback that exits 1 instead of the documented 2.
        # Verified by chaos-injection against a real unreachable origin.
        raise NoRepo('git fetch failed in %s: %s'
                      % (repo, (e.stderr or str(e)).strip()))
    # encoding='utf-8' explicit -- text=True alone decodes with the OS
    # locale's preferred encoding (cp1252 on Windows), which crashes on the
    # first non-ASCII byte a real file contains. Found live in
    # hover_pure_js_exec.py against the real stonedesk.html; applied here
    # defensively since CRITICALITY-TIERS.md is git-blob UTF-8 same as
    # every other file this platform writes with encoding='utf-8'.
    r = subprocess.run(
        ['git', 'show', 'origin/main:' + TIERS_REL_PATH],
        cwd=repo, capture_output=True, text=True, encoding='utf-8'
    )
    if r.returncode != 0:
        # A missing file at that path on origin/main is COULD NOT TELL, not
        # a quiet empty pool -- the same "absence is not evidence of zero"
        # standard tier_a_review_gate.py already holds itself to.
        raise NoRepo('git show origin/main:%s failed in %s: %s'
                      % (TIERS_REL_PATH, repo, r.stderr.strip()))
    return r.stdout


def tier_bc_resources(path):
    """Local-file variant, kept ONLY for feeding a literal fixture path in
    the self-test -- production code path is read_tiers_text() ->
    _parse_tier_rows(), never this function against a real clone."""
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return _parse_tier_rows(f.read())


def load_log_entries(path=LOG_PATH):
    try:
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
    except OSError as e:
        raise NoRepo('could not read self-log %s: %s' % (path, e))
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except ValueError as e:
            raise NoRepo('self-log %s has a malformed line: %s' % (path, e))
    return entries


def all_mentioned_text_LEGACY_PROSE_SCAN(entries):
    """RETIRED as the staleness signal, 2026-09-28 -- kept ONLY as the
    negative control that proves the bug this fix closes was real (F-LEGACY
    below). This is the ORIGINAL implementation: it scanned summary/ref/
    target together, so a resource named ONLY in passing prose -- comparing
    a NEW finding to an old precedent ("the same convention that held
    grd_dreamclose/rf_buildings/bld_selections at B") -- reset that
    resource's staleness to zero, even though nothing about it was actually
    re-read. Caught happening for real during the freshness-floor
    measurement series (log #584): bld_selections' own staleness ticked
    down by one point from a single incidental mention in an UNRELATED
    finding about leg_keepsakeorders. DO NOT call this from cold_pool() or
    last_mention_seqs() -- see ref_only_mentioned_text() below."""
    parts = []
    for e in entries:
        for field in ('summary', 'ref', 'target'):
            v = e.get(field)
            if v:
                parts.append(str(v))
    return ' '.join(parts).lower()


def ref_only_mentioned_text_RETIRED_BARE_NAME_SCAN(entries):
    """RETIRED the same day it shipped, 2026-09-28 -- kept, like the LEGACY
    prose scan above, as the record of an intermediate signal that
    OVERCORRECTED. This was the first fix for the false-staleness-reset bug:
    scan only `ref`, never `summary` prose. Correct direction, but it only
    credited a resource cited by BARE NAME in ref, and this role's real
    citation habit is file:line ('sairngrounds.html:2308') -- so measured on
    the real log the same day, 121 of 124 resources read NEVER MENTIONED,
    the freshness-floor gate went near-inert, and staleness stopped
    discriminating anything. The permanent replacement is
    resolved_read_names() below: a file:line citation RESOLVES to the
    resource whose registry row or whose own source lines it lands in, at
    the source sha the entry recorded. Not called by any production path;
    see the F-BARENAME fixture, which proves this signal's known blindness
    (a real file:line citation into a resource's own rows earns no credit
    here, and does under the resolver)."""
    parts = []
    for e in entries:
        v = e.get('ref')
        if v:
            parts.append(str(v))
    return ' '.join(parts).lower()


# ── the resolved-read signal, 2026-09-28 ────────────────────────────────────
# A resource counts as READ when a `ref` citation RESOLVES to it:
#   - a bare resource name in ref still counts (unchanged), and
#   - a file:line citation counts FOR resource R when the cited line lands
#     in R's own registry row (docs/CRITICALITY-TIERS.md -- rows are single
#     lines, so this is exact) or in R's own source lines in an app file:
#     the CITED LINE's own resource name(s) if it has any, else the NEAREST
#     resource-naming line within the same FUNCTION BLOCK (function-
#     delimited, not a fixed-width slice window -- hank's queue16(e) names
#     fixed-width windows as a defect class; a function boundary is a
#     structural edge, and "nearest naming line" is a distance MINIMUM, not
#     a width). WHY NEAREST AND NOT THE WHOLE BLOCK, measured before any
#     entry relied on it: the first draft credited every name in the block,
#     and the very first full-log measurement showed a seed() citation
#     crediting ALL of an app's resources at once (every bld_* row read
#     staleness 0 off three citations at log #590) -- register cells cite
#     seed lines constantly, so whole-block resolution silently rebuilt the
#     over-crediting this signal exists to remove.
# Citations resolve AT THE SOURCE SHA THE ENTRY RECORDED (source_shas,
# captured by hover_log.py at write time as the blob sha of what was
# actually read), because line numbers drift: sairnbuild.html:6842 today is
# not :6842 at the sha the entry read. Historical entries are NEVER edited;
# resolution happens at read time, every run. AN ENTRY WITH NO RECORDED
# SHA FOR A CITED PATH EARNS NOTHING FROM THAT CITATION (bare names still
# count). The first version fell back to current origin/main "best-effort"
# and its first measurement caught the mis-credit that design invites:
# #582's sha-less :545 citation credited whatever row holds line 545
# TODAY -- scp_water_features, which #582 never audited. A line number
# without the content it indexed is not a location (F-582/F-582-CONTROL
# lock both directions). DISCLOSED LIMIT: A citation into a region
# with no enclosing function (file head markup) scans from the file start
# to the first function line -- structural, but wide; disclosed rather than
# capped, because a cap would be exactly the fixed-width window this
# design avoids.

_FUNC_LINE = re.compile(r'^\s*function\s+[A-Za-z0-9_$]+\s*\(')
_CITE_TOKEN = re.compile(r'^(.+?):(\d+)(?:-\d+)?$')


def parse_ref_tokens(ref):
    return [t.strip() for t in str(ref).split(',') if t.strip()]


def make_blob_reader(repo):
    """Returns read(path, sha) -> the blob's LINES (a list) or None. sha is
    a BLOB sha (the shape hover_log.py's local_head_sha records: `git
    rev-parse HEAD:path`). sha=None reads the CURRENT origin/main blob and
    is RETAINED ONLY for the F-582-CONTROL known-bad fixture -- production
    resolution never calls it (a sha-less citation is unresolved before
    the reader is ever consulted). Unreadable returns None: no credit
    against guessed content (fail closed, under-count).

    ONE persistent `git cat-file --batch` process serves every read --
    object-database only, never the working tree. Measured before adopting:
    the one-subprocess-per-blob draft took 4m25s over the real 590-entry
    log on this Windows machine (process spawn dominates), and lines are
    split once and cached because the log cites the same 2MB app blob
    hundreds of times. If the batch process dies, every subsequent read is
    None -- fail closed, never a retry loop."""
    cache = {}
    proc = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=repo,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)

    def _read_exact(n):
        chunks = []
        while n > 0:
            c = proc.stdout.read(n)
            if not c:
                raise IOError('git cat-file --batch closed mid-object')
            chunks.append(c)
            n -= len(c)
        return b''.join(chunks)

    def read(path, sha):
        key = (path, sha or '@origin')
        if key in cache:
            return cache[key]
        obj = sha if sha else 'origin/main:' + path
        try:
            proc.stdin.write((obj + '\n').encode('utf-8'))
            proc.stdin.flush()
            header = proc.stdout.readline().decode('utf-8', 'replace').split()
            if len(header) == 3 and header[1] == 'blob':
                data = _read_exact(int(header[2]) + 1)[:-1]
                cache[key] = data.decode('utf-8', 'replace').splitlines()
            else:
                if len(header) == 3:   # a non-blob object: drain its bytes
                    _read_exact(int(header[2]) + 1)
                cache[key] = None
        except (OSError, IOError, ValueError):
            cache[key] = None
        return cache[key]

    return read


_NAME_PAT_CACHE = {}


def _names_pattern(names_set, mode):
    """One combined alternation regex per (names_set, mode) -- 124 separate
    searches per line made the nearest-line scan the new bottleneck once
    the git spawns were batched.

    TWO MODES, both structural, chosen by what a match MEANS in that file
    type -- added after the second full-log measurement caught a real
    cross-app false credit: the SAIRNgrounds resource `jobs` was credited
    from sairnbuild.html citations, because sairnbuild's own jobs() helper
    (which reads 'bld_jobs') matched a bare word scan.
      'storage' (.html single-file apps): the name as an st()/ld() STORAGE
        KEY -- the one place an app file touches a resource as data. A
        nav('jobs') panel id or a jobs() function call is not a read of
        the `jobs` resource and no longer counts.
      'quoted' (everything else -- api/*.js, sql, tools): the name as a
        QUOTED string literal, the shape registries and route handlers
        use. Bare identifiers still do not count."""
    key = (id(names_set), mode)
    hit = _NAME_PAT_CACHE.get(key)
    if hit is None or hit[0] is not names_set:
        alt = '|'.join(sorted(re.escape(n) for n in names_set))
        if mode == 'storage':
            rx = re.compile(r"\b(?:st|ld)\(\s*['\"](" + alt + r")['\"]")
        else:
            rx = re.compile(r"['\"](" + alt + r")['\"]")
        _NAME_PAT_CACHE[key] = hit = (names_set, rx)
    return hit[1]


def resolve_citation(path, line, lines, names_set, all_names_set=None):
    """The pure resolver -- no I/O, fixture-testable against literal
    content (pass text.splitlines()). Which resource names does path:line,
    with the file's LINES as read, resolve to?

    Registry file: the row occupying exactly that line -- exact, no window.
    App file: the cited line's own name(s) if it names any resource, else
    the NEAREST resource-naming line within the enclosing function block
    (see the design comment above for why nearest-line, not whole-block --
    the seed()-blast over-credit was measured, not hypothesized). Ties at
    equal distance credit both directions' names -- a tie is genuine
    ambiguity and crediting one side by scan order would be arbitrary.

    all_names_set (2026-09-28, the OTHER AUDITOR'S find, its seq 280):
    ownership is decided against the FULL registry vocabulary (every tier,
    A included), then the credit is the owners INTERSECTED with names_set.
    Before this, the nearest-owner scan only knew B/C names, so a cited
    line whose true nearest owner was a Tier A resource fell through PAST
    it to a farther B resource that was never audited -- observed for real
    at #603's sairngrounds.html:4286 citation: the nearest storage line is
    st('grd_invoices') (Tier A) at distance 1, and the old scan credited
    st('grd_schedule') (Tier B) at distance 4 instead. The nearest owner
    now WINS ownership even when out of vocabulary, and an out-of-vocab
    owner credits NOBODY. all_names_set=None keeps the old single-vocab
    behavior ONLY for the F-VOCAB-CONTROL known-bad arm."""
    if line < 1 or line > len(lines):
        return set()
    vocab = all_names_set if all_names_set is not None else names_set
    p = path.replace('\\', '/')
    if p.endswith('CRITICALITY-TIERS.md'):
        m = TIER_ROW.match(lines[line - 1].strip())
        return {m.group(1)} if m and m.group(1) in names_set else set()
    rx = _names_pattern(vocab, 'storage' if p.endswith('.html') else 'quoted')
    lo = line - 1
    got = set(rx.findall(lines[lo].lower()))
    if got:
        return got & names_set
    start = lo
    while start > 0 and not _FUNC_LINE.match(lines[start]):
        start -= 1
    end = lo + 1
    while end < len(lines) and not _FUNC_LINE.match(lines[end]):
        end += 1
    best, bestd = set(), None
    for i in range(start, end):
        g = rx.findall(lines[i].lower())
        if not g:
            continue
        d = abs(i - lo)
        if bestd is None or d < bestd:
            best, bestd = set(g), d
        elif d == bestd:
            best |= set(g)
    return best & names_set


def resolved_read_names(entry, names_set, blob_reader=None, all_names_set=None):
    """The set of resource names this ONE entry's ref resolves to. summary
    prose NEVER counts (the #584 bld_selections incident stands closed).
    With blob_reader=None only bare-name tokens resolve -- the pure mode the
    ordering fixtures use; production passes make_blob_reader(repo)."""
    out = set()
    ref = entry.get('ref')
    if not ref:
        return out
    shas = entry.get('source_shas') or {}
    for tok in parse_ref_tokens(ref):
        tl = tok.lower()
        if tl in names_set:
            out.add(tl)
            continue
        m = _CITE_TOKEN.match(tok)
        if not m or blob_reader is None:
            continue
        path, line = m.group(1).replace('\\', '/'), int(m.group(2))
        sha = (shas.get(path) or {}).get('sha')
        if not sha:
            # NO RECORDED SHA -> UNRESOLVED, NO CREDIT (2026-09-28, same
            # day the fallback shipped). The retired best-effort fallback
            # read current origin/main and was caught mis-crediting on its
            # first measurement: #582 cites docs/CRITICALITY-TIERS.md:545
            # sha-less, and that LINE today belongs to scp_water_features,
            # a resource #582 never audited. A line number without the
            # content it indexed is not a location; see F-582/F-582-CONTROL.
            continue
        lines = blob_reader(path, sha)
        if lines is None:
            continue
        # memo per (path, sha, line, names_set identity) on the reader
        # itself: the same seed line is cited by many entries, and each
        # nearest-line scan walks a function block. The names_set identity
        # is part of the key because the first draft keyed without it and
        # its own selftest caught the poisoning immediately -- R9's
        # narrower names_set was served R1's cached answer (KeyError,
        # 2026-09-28); a memo that outlives its vocabulary is wrong.
        try:
            memo = blob_reader.__dict__.setdefault('_resolve_memo', {})
        except AttributeError:
            memo = None
        mkey = (path, sha, line, id(names_set), id(all_names_set))
        if memo is not None and mkey in memo:
            out |= memo[mkey]
            continue
        got = resolve_citation(path, line, lines, names_set, all_names_set)
        if memo is not None:
            memo[mkey] = got
        out |= got
    return out


def cold_pool(repo, log_path=LOG_PATH):
    tiers_text = read_tiers_text(repo)
    resources = _parse_tier_rows(tiers_text)
    entries = load_log_entries(log_path)
    names_set = {n for n, _ in resources}
    all_names = _parse_all_names(tiers_text)
    reader = make_blob_reader(repo)
    ever_read = set()
    for e in entries:
        ever_read |= resolved_read_names(e, names_set, reader, all_names)
    cold = [(n, t) for n, t in resources if n not in ever_read]
    warm = [(n, t) for n, t in resources if n in ever_read]
    return cold, warm


# ── the combined draw score (see module docstring for the decided formula) ──

_APP_LINE = re.compile(r"app\s*:\s*'([a-z0-9_]+)'")
_RES_NAME = re.compile(r"'([a-z][a-z0-9_]*)'")


def resource_app_map(repo):
    """{resource_name: app_name} derived from api/_resources/*.js -- the
    per-app server registries. Derived, never hand-maintained (the app-map
    lesson: a hand map was wrong five times). Raises NoRepo if the
    directory is missing or yields ZERO apps -- an empty derivation source
    is a refusal, not an empty map (disciplines item 8)."""
    d = os.path.join(repo, 'api', '_resources')
    if not os.path.isdir(d):
        raise NoRepo('api/_resources not found under %r -- cannot resolve '
                     'resources to apps, and will not score risk without it' % repo)
    out = {}
    apps = 0
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.js') or fn.endswith('.test.js') or fn == 'index.js':
            continue
        text = open(os.path.join(d, fn), encoding='utf-8', errors='replace').read()
        m = _APP_LINE.search(text)
        if not m:
            continue
        app = m.group(1)
        apps += 1
        # names inside the resources array; the registry files are flat
        # string lists, so every quoted lowercase identifier after the app
        # line that looks like a resource name is one.
        for rm in _RES_NAME.finditer(text[m.end():]):
            out.setdefault(rm.group(1), app)
    if apps == 0:
        raise NoRepo('api/_resources yielded ZERO app registries -- refusing '
                     'to score every resource as risk 0 on an empty source')
    return out


def app_risk_from_ddw(script_dir=None):
    """module_density from defect_density_weighting.py over its --json
    contract. FAILS CLOSED: absent script, nonzero exit or failed control is
    a NoRepo refusal naming the tool -- never an all-zero risk map."""
    here = script_dir or os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, 'defect_density_weighting.py')
    if not os.path.isfile(script):
        raise NoRepo('defect_density_weighting.py is ABSENT from %r -- the '
                     'draw score cannot run without its primary factor; '
                     'this check did not run' % here)
    r = subprocess.run([sys.executable, script, '--json'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise NoRepo('defect_density_weighting.py --json exited %d -- refusing '
                     'to draw on a failed risk instrument: %s'
                     % (r.returncode, (r.stdout or r.stderr)[-200:]))
    data = json.loads(r.stdout)
    if data.get('FAIL_control'):
        raise NoRepo('defect_density_weighting.py failed its own classifier '
                     'control -- its density is not trustworthy right now')
    risk = {}
    for module, n in data.get('module_density', []):
        # normalize 'sairnlegacy.html' -> 'sairnlegacy' so registry app names
        # and ddw module names meet in one vocabulary; SUM on collision, since
        # ddw has emitted both spellings of one app across runs and last-wins
        # would silently drop whichever came first
        key = str(module).replace('.html', '')
        risk[key] = risk.get(key, 0) + int(n)
    return risk


def last_mention_seqs(entries, names, blob_reader=None, all_names_set=None):
    """{name: highest seq whose ref RESOLVES to it, or None if never}.
    REWRITTEN TWICE ON 2026-09-28, both times for a real measured failure:
    first from prose-scan to ref-only (the #584 bld_selections false reset
    -- summary prose must never count, and still does not), then from
    ref-only bare names to RESOLVED READS the same day, when the bare-name
    rule measured 121 of 124 resources as never-mentioned because this
    role's real citation habit is file:line, not bare names. A file:line
    citation now resolves through resolved_read_names() -- registry row or
    function block, at the entry's own recorded source sha. blob_reader
    defaults to None (bare names only, pure, no git) so ordering fixtures
    stay dependency-free; every production caller passes
    make_blob_reader(repo)."""
    names_set = set(names)
    last = {n: None for n in names}
    for e in entries:
        seq = e.get('seq')
        for n in resolved_read_names(e, names_set, blob_reader, all_names_set):
            if n not in last:
                continue
            if last[n] is None or (seq is not None and seq > last[n]):
                last[n] = seq
    return last


# FRESHNESS_FLOOR, added 2026-09-28 after a real, diagnosed failure: three
# consecutive --draw calls landed entirely on already-swept ground (log
# #570/#571/#574). MEASURED, not assumed -- at diagnosis time, sairnbuild
# and sairnvet (tied for the highest app risk, 11) had a MAXIMUM per-app
# staleness of 21 entries each: every one of their B/C rows had been
# individually read so recently that NONE of them were genuinely due.
# Meanwhile sairngrounds (risk 9) and sairnlegacy (risk 9) had rows up to
# 218 and 252 entries stale -- more than TEN TIMES staler -- and stonedesk
# (risk 8) up to 201, none of which pure risk-first ordering could ever
# reach while a higher-risk app existed at all, no matter how thoroughly
# swept that higher-risk app already was. REASONED FROM THAT REAL GAP, not
# picked in the abstract: 30 sits between the exhausted apps' observed
# ceiling (21) and the least-stale surviving app's own maximum (39,
# sairnroofing) at diagnosis time, with margin on both sides. Recalibrate
# once real repeat-gap history exists, the same honesty every other
# REASONED constant in this file carries (STALE_AFTER_ENTRIES,
# NARROWING_THRESHOLD, UNDIRECTED_SWEEP_CADENCE all say the same thing).
FRESHNESS_FLOOR = 30

# DRAW_SHARE_CAP, added 2026-09-28 after the concentration was MEASURED, not
# felt: sairngrounds held 39% of all recently-read resources (14 of 36 with
# staleness < FRESHNESS_FLOOR) and 8 of the last 30 draw entries -- ~70% of
# the last ten -- because its risk score (18, climbing with every finding
# this role logs there, the positive feedback named at #582) outranked every
# other app on every draw. The cap: while ANY other app still has stale
# ground, an app holding MORE THAN A THIRD of the recently-read pool sinks
# to a later bucket regardless of risk. A third is REASONED, not calibrated:
# ~4x the uniform share across the 13 mapped apps, generous to genuine risk
# concentration, fatal to a monopoly; revisit against real post-cap history.
# MIN_SAMPLE guards small-n noise: a share computed from fewer than 6 recent
# reads (two draw batches) is one batch talking to itself and caps nothing.
DRAW_SHARE_CAP = 1.0 / 3.0
DRAW_SHARE_MIN_SAMPLE = 6


def draw_order(resources, app_of, risk_of, last_seq_of, tip_seq,
               share_cap=DRAW_SHARE_CAP):
    """The pure ordering, fixture-testable with no repo and no subprocess.

    Sort key per resource: (0 if its APP has stale ground else 1, -risk,
    -staleness, name). BOTH SIGNALS STAY IN THE ONE SCORE -- this is not a
    third independent axis, it is a THRESHOLD GATE on the staleness signal
    already in the tuple, hoisted in front of risk only when risk's own
    candidates have nothing left to offer. An app "has stale ground" when
    AT LEAST ONE of its own resources is at or above FRESHNESS_FLOOR (a
    never-mentioned resource, staleness = infinity, always counts). An app
    where EVERY resource is fresher than the floor sinks into a strictly
    LATER bucket regardless of its risk score -- it does not disappear, it
    waits until something in it ages back past the floor.

    staleness is tip_seq - last_seq and never-mentioned is +infinity.
    Returns [(name, tier, app, risk, staleness)] sorted."""
    INF = float('inf')
    rows = []
    app_max_staleness = {}
    app_recent = {}
    total_recent = 0
    for name, tier in resources:
        app = app_of.get(name) or '(unmapped)'
        risk = risk_of.get(app_of.get(name), 0) if app_of.get(name) else 0
        last = last_seq_of.get(name)
        staleness = INF if last is None else max(0, tip_seq - last)
        rows.append((name, tier, app, risk, staleness))
        app_max_staleness[app] = max(app_max_staleness.get(app, -1), staleness)
        if staleness < FRESHNESS_FLOOR:
            app_recent[app] = app_recent.get(app, 0) + 1
            total_recent += 1
    app_has_stale_ground = {a: (s >= FRESHNESS_FLOOR) for a, s in app_max_staleness.items()}
    # ── THE PER-WINDOW SHARE CAP (see DRAW_SHARE_CAP's comment for the
    # measured before-state). An app is CAPPED when: the cap is enabled,
    # the recently-read pool is big enough to mean anything, the app holds
    # more than the cap's share of it, and AT LEAST ONE OTHER app still
    # has stale ground to serve instead. A capped app does not disappear
    # -- it waits in the bucket between the live apps and the exhausted
    # ones, and un-caps by itself as other apps' reads age its share down.
    capped = {}
    if share_cap is not None and total_recent >= DRAW_SHARE_MIN_SAMPLE:
        for a in app_max_staleness:
            over = (app_recent.get(a, 0) / float(total_recent)) > share_cap
            others_stale = any(app_has_stale_ground.get(b) for b in app_max_staleness
                               if b != a)
            capped[a] = over and others_stale
    rows.sort(key=lambda r: (
        (0 if not capped.get(r[2]) else 1) if app_has_stale_ground.get(r[2]) else 2,
        -r[3],
        -(r[4] if r[4] != float('inf') else 1e18),
        r[0]))
    return rows


def undirected_order(resources, last_seq_of, tip_seq, seed=None):
    """The permanent undirected-sweep mechanism, added 2026-09-28 to replace
    --pick's original 'never-mentioned' bucket, which is now PERMANENTLY
    EXHAUSTED (0 of 124 resources have never been mentioned -- confirmed at
    log #566, where a one-off HEAD-hash-seeded workaround had to be
    improvised because this function did not yet exist). That workaround is
    retired; this is the real mechanism.

    DELIBERATELY BLIND TO RISK -- structurally different from draw_order(),
    not a smaller version of it. draw_order() exists BECAUSE this role's own
    rotation tends to follow the loudest signal (Tier A proximity, fresh
    commits, now app risk); an "undirected" mechanism that also sorted by
    risk would just be a quieter copy of the same bias, not a check against
    it. Sort key is PURELY (-staleness, name) -- no app, no risk, no
    api/_resources dependency, no defect_density_weighting.py dependency.
    That absence of a shared dependency is itself the point (discipline 6,
    independent method): a fallback that depends on the same fragile chain
    as the mechanism it exists apart from is not really a fallback.

    NEVER EXHAUSTS, unlike the old 'never mentioned' bucket: staleness is
    relative (entries since last mention), so there is always a stalest
    resource, even after every resource has been mentioned at least once.
    A resource just drawn resets to staleness 0 and sinks to the bottom
    until everything else has been drawn at least as recently.

    TIE-BREAK IS SEEDED-RANDOM, NOT ALPHABETICAL (changed 2026-09-28): the
    resolved-read signal leaves large groups tied at identical staleness
    (44 rows tied at NEVER on adoption day), and an alphabetical tiebreak
    turned "undirected" into "alphabetical-first" -- the bld_* rows would
    be swept forever before sen_* ever surfaced. The tiebreak is
    sha256(seed:name): deterministic for a given seed (a draw is exactly
    reproducible -- rerun with the same seed and get the same order), and
    a different seed reshuffles every tie group. Production seeds from the
    LOG TIP's own chain hash, so each logged batch advances the shuffle by
    itself and nobody picks the seed by hand. seed=None keeps the old
    alphabetical order ONLY so the F-SEED fixtures can state the before/
    after difference explicitly -- no production path passes None.
    (Why not oldest-last-read: the dominant tie group IS the never-read
    set, which has no last read to be oldest by.)"""
    import hashlib
    INF = float('inf')

    def tiebreak(name):
        if seed is None:
            return name
        return hashlib.sha256(('%s:%s' % (seed, name)).encode('utf-8')).hexdigest()

    rows = []
    for name, tier in resources:
        last = last_seq_of.get(name)
        staleness = INF if last is None else max(0, tip_seq - last)
        rows.append((name, tier, staleness))
    rows.sort(key=lambda r: (-(r[2] if r[2] != float('inf') else 1e18),
                             tiebreak(r[0]), r[0]))
    return rows


def _print_watch(name):
    """Print a WATCH reminder for a drawn/swept resource if one is open on
    it, e.g. leg_memorials.service_details_visible (2026-09-28): 'no
    consumer yet' is a fact about TODAY, and the only way to catch the day
    a consumer is added is to ask the question again the next time this
    resource is actually read -- not to remember to. Import is local and
    fails SILENT-BUT-NAMED: a missing/broken watchlist module must never
    block a draw over a report-only feature, but it must say so once."""
    try:
        import hover_watchlist as _wl
        line = _wl.check_line(name)
        if line:
            print('    ' + line)
    except Exception as e:
        print('    [watchlist unavailable: %s]' % e)


def undirected_sweep(repo, n, log_path=LOG_PATH):
    tiers_text = read_tiers_text(repo)
    resources = _parse_tier_rows(tiers_text)
    entries = load_log_entries(log_path)
    tip = max((e.get('seq') or 0) for e in entries) if entries else 0
    # seed from the tip entry's own chain hash: advances with every logged
    # batch, reproducible for a given log state, chosen by nobody.
    tip_hash = ''
    for e in entries:
        if (e.get('seq') or 0) == tip:
            tip_hash = e.get('hash') or ''
    seed = tip_hash or str(tip)
    names = [nm for nm, _ in resources]
    last_of = last_mention_seqs(entries, names, make_blob_reader(repo), _parse_all_names(tiers_text))
    rows = undirected_order(resources, last_of, tip, seed=seed)
    import freshness_stamp as _fs
    print(_fs.stamp())
    print('UNDIRECTED SWEEP -- pure staleness order, seeded-random among '
          'ties (seed=%s..., the log tip\'s own chain hash -- rerunning '
          'against the same log reproduces this exact order), DELIBERATELY '
          'BLIND TO APP RISK -- this is not --draw with fewer columns, it '
          'is the mechanism that checks --draw\'s own bias. Never exhausts '
          '(staleness is relative, not "ever mentioned").' % seed[:12])
    print('  %-28s %-4s %s' % ('resource', 'tier', 'staleness'))
    for name, tier, st_ in rows[:n]:
        print('  %-28s %-4s %s'
              % (name, tier, 'NEVER MENTIONED' if st_ == float('inf') else '%d entries' % st_))
        _print_watch(name)
    return rows[:n]


def draw(repo, n, log_path=LOG_PATH):
    tiers_text = read_tiers_text(repo)
    resources = _parse_tier_rows(tiers_text)
    entries = load_log_entries(log_path)
    app_of = resource_app_map(repo)
    risk_of = app_risk_from_ddw()
    tip = max((e.get('seq') or 0) for e in entries) if entries else 0
    names = [nm for nm, _ in resources]
    last_of = last_mention_seqs(entries, names, make_blob_reader(repo), _parse_all_names(tiers_text))
    rows = draw_order(resources, app_of, risk_of, last_of, tip)
    unmapped = sum(1 for r in rows if r[2] == '(unmapped)')
    apps_by_max_stale = {}
    app_recent = {}
    total_recent = 0
    for _, _, app, _, st_ in rows:
        apps_by_max_stale[app] = max(apps_by_max_stale.get(app, -1), st_)
        if st_ < FRESHNESS_FLOOR:
            app_recent[app] = app_recent.get(app, 0) + 1
            total_recent += 1
    exhausted_apps = sorted(a for a, s in apps_by_max_stale.items()
                            if s < FRESHNESS_FLOOR)
    if total_recent >= DRAW_SHARE_MIN_SAMPLE:
        over = sorted('%s (%d/%d)' % (a, n, total_recent)
                      for a, n in app_recent.items()
                      if n / float(total_recent) > DRAW_SHARE_CAP
                      and apps_by_max_stale.get(a, -1) >= FRESHNESS_FLOOR)
        if over:
            print('SHARE CAP (> 1/3 of %d recent reads): %s -- demoted below '
                  'every other app with stale ground until the share ages '
                  'down; not hidden, waiting.' % (total_recent, ', '.join(over)))
    import freshness_stamp as _fs
    print(_fs.stamp())
    print('DRAW SCORE -- lexicographic (freshness-floor bucket, app risk DESC, '
          'staleness DESC, name ASC); REASONED priority, not calibrated -- '
          'see module docstring')
    if exhausted_apps:
        print('FRESHNESS FLOOR (%d entries): %s %s no resource at or past it '
              '-- sunk to a later bucket regardless of app risk, not hidden.'
              % (FRESHNESS_FLOOR, ', '.join(exhausted_apps),
                 'has' if len(exhausted_apps) == 1 else 'have'))
    if unmapped:
        print('DISCLOSED: %d of %d resources have no api/_resources app mapping '
              'and are scored risk 0 -- they sink, they are not hidden.'
              % (unmapped, len(rows)))
    print('  %-28s %-4s %-14s %-5s %s' % ('resource', 'tier', 'app', 'risk', 'staleness'))
    for name, tier, app, risk, st_ in rows[:n]:
        print('  %-28s %-4s %-14s %-5d %s'
              % (name, tier, app, risk,
                 'NEVER MENTIONED' if st_ == float('inf') else '%d entries' % st_))
        _print_watch(name)
    return rows[:n]


def _print_report(cold, warm, pick=None):
    import freshness_stamp as _fs
    print(_fs.stamp())
    print('HOVER COLD-SCAN POOL -- %d Tier B/C resources, %d never mentioned by this role, %d mentioned at least once'
          % (len(cold) + len(warm), len(cold), len(warm)))
    print('"READ" HERE MEANS A REF CITATION RESOLVED TO THE RESOURCE (bare name, '
          'its register row, or its own storage lines at the recorded sha) -- '
          'NOT that the reading was thorough; see the module docstring.')
    print()
    if pick:
        chosen = sorted(cold)[:pick]
        print('PICK (%d, deterministic alphabetical order, not random):' % len(chosen))
        for name, tier in chosen:
            print('  %s  Tier %s' % (name, tier))
        return
    print('COLD (%d) -- no ref citation has ever resolved to these:' % len(cold))
    for name, tier in sorted(cold):
        print('  %s  Tier %s' % (name, tier))
    print()
    print('WARM (%d):' % len(warm))
    for name, tier in sorted(warm):
        print('  %s  Tier %s' % (name, tier))


def run_fixtures():
    import tempfile

    ok_count = [0]
    fail_count = [0]

    def ck(name, cond):
        if cond:
            ok_count[0] += 1
            print('  ok   ' + name)
        else:
            fail_count[0] += 1
            print('  FAIL ' + name)

    # --- TIER_ROW parsing, against real shapes the register actually uses ---
    tmp_md = os.path.join(tempfile.mkdtemp(), 'tiers.md')
    with open(tmp_md, 'w', encoding='utf-8') as f:
        f.write(
            "| Tier | A resource qualifies when it... |\n"
            "|---|---|\n"
            "| `widget_thing` | **A** | money moves |\n"
            "| `gizmo_thing` | **B** | operational only |\n"
            "| `sprocket_thing` | **C** | cosmetic |\n"
            "| `unrelated_prose_row` | not a tier row at all |\n"
        )
    resources = tier_bc_resources(tmp_md)
    names = [n for n, t in resources]
    ck('Tier A row is EXCLUDED from the B/C pool', 'widget_thing' not in names)
    ck('Tier B row IS included', ('gizmo_thing', 'B') in resources)
    ck('Tier C row IS included', ('sprocket_thing', 'C') in resources)
    ck('a malformed/non-tier row is not picked up as a resource',
       'unrelated_prose_row' not in names)
    ck('exactly 2 B/C resources parsed', len(resources) == 2)

    # --- discover_repo(): identical contract to the ledger's, tested here
    # too because this is a separate standalone file with its own copy ---
    ck('--repo on the command line wins over everything',
       discover_repo(['--repo', '/explicit/path']) == '/explicit/path')
    old_env = os.environ.get('HOVER_LEDGER_REPO')
    try:
        os.environ['HOVER_LEDGER_REPO'] = '/env/path'
        ck('$HOVER_LEDGER_REPO is used when --repo is absent',
           discover_repo([]) == '/env/path')
    finally:
        if old_env is None:
            os.environ.pop('HOVER_LEDGER_REPO', None)
        else:
            os.environ['HOVER_LEDGER_REPO'] = old_env

    # --- THE ACTUAL STALENESS FIX, DRIVEN: a real bare "origin", a real
    # push, and a second clone whose own local branch is deliberately behind
    # -- read_tiers_text() must still return the CURRENT content, because it
    # reads origin/main via `git show`, never the discovered clone's working
    # tree. Same fixture shape as hover_coverage_ledger.py's, independently
    # rebuilt here rather than imported, matching this directory's
    # every-tool-standalone convention.
    tmpdir = tempfile.mkdtemp()
    bare_repo = os.path.join(tmpdir, 'origin.git')
    work_repo = os.path.join(tmpdir, 'work')
    subprocess.run(['git', 'init', '-q', '--bare', bare_repo], check=True)
    subprocess.run(['git', 'init', '-q', work_repo], check=True)
    subprocess.run(['git', 'config', 'user.email', 'x@x.com'], cwd=work_repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 'x'], cwd=work_repo, check=True)
    subprocess.run(['git', 'checkout', '-q', '-b', 'main'], cwd=work_repo, check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', bare_repo], cwd=work_repo, check=True)
    docs_dir = os.path.join(work_repo, 'docs')
    os.makedirs(docs_dir)
    tiers_file = os.path.join(docs_dir, 'CRITICALITY-TIERS.md')
    with open(tiers_file, 'w', encoding='utf-8') as f:
        f.write("| `old_only_resource` | **B** | v1 |\n")
    subprocess.run(['git', 'add', '.'], cwd=work_repo, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'v1 tiers'], cwd=work_repo, check=True)
    subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=work_repo, check=True)

    stale_clone = os.path.join(tmpdir, 'stale_clone')
    subprocess.run(['git', 'clone', '-q', bare_repo, stale_clone], check=True)
    subprocess.run(['git', 'checkout', '-q', '-b', 'main', 'origin/main'],
                    cwd=stale_clone, check=True)

    # NOW advance origin past what stale_clone's own working tree holds --
    # a real new resource added on origin/main that the stale clone's local
    # checkout has never seen.
    with open(tiers_file, 'w', encoding='utf-8') as f:
        f.write("| `old_only_resource` | **B** | v1 |\n"
                "| `new_resource_on_origin` | **C** | v2, pushed after the clone |\n")
    subprocess.run(['git', 'add', '.'], cwd=work_repo, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'v2 tiers, adds new_resource_on_origin'],
                    cwd=work_repo, check=True)
    subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=work_repo, check=True)

    stale_tiers_file = os.path.join(stale_clone, 'docs', 'CRITICALITY-TIERS.md')
    with open(stale_tiers_file, encoding='utf-8') as f:
        stale_working_tree = f.read()
    ck('the fixture precondition holds: the stale clone\'s own WORKING TREE '
       'genuinely does not have the new resource yet',
       'new_resource_on_origin' not in stale_working_tree)

    ck('read_tiers_text() on a repo with no --repo/env/candidate refuses',
       _raises(NoRepo, read_tiers_text, None))

    fresh_text = read_tiers_text(stale_clone)
    ck('THE STALE CLONE STILL RETURNS THE NEW RESOURCE -- read_tiers_text() '
       'reads origin/main via git show, past its own stale working tree',
       'new_resource_on_origin' in fresh_text)
    ck('...and the resources it parses to include the new one',
       ('new_resource_on_origin', 'C') in _parse_tier_rows(fresh_text))

    # --- end-to-end: cold_pool() against the same stale clone ---
    # UPDATED 2026-09-28 for the ref-only fix: the mention now lives in
    # `ref` (a real citation), not `summary` prose -- this fixture's own
    # PURPOSE (a genuinely-cited resource reads as WARM end-to-end) is
    # unaffected by the fix; only the shape of the test data changed to
    # match the corrected signal. See F-BLDSEL/F-REFCITE below for fixtures
    # that specifically lock the summary-vs-ref DISTINCTION this fix makes.
    entries = [
        {'type': 'check', 'summary': 'looked at old_only_resource directly today',
         'ref': 'old_only_resource'},
    ]
    log_tmp = os.path.join(tempfile.mkdtemp(), 'fake_log.jsonl')
    with open(log_tmp, 'w', encoding='utf-8') as f:
        for e in entries:
            f.write(json.dumps(e) + '\n')
    cold, warm = cold_pool(stale_clone, log_path=log_tmp)
    warm_names = [n for n, t in warm]
    cold_names = [n for n, t in cold]
    ck('old_only_resource (cited in ref) is WARM', 'old_only_resource' in warm_names)
    ck('new_resource_on_origin (never mentioned, and only reachable at all '
       'because the staleness fix works) is COLD',
       'new_resource_on_origin' in cold_names)

    # --- THE FALSE-STALENESS-RESET FIX, 2026-09-28. Tests written BEFORE ---
    # --- trusting the fix on real data, per the blind-analysis discipline, ---
    # --- against the EXACT real incident (log #584: bld_selections' own   ---
    # --- staleness reset from a precedent mention in an UNRELATED         ---
    # --- finding about leg_keepsakeorders), not a generic stand-in.       ---
    bldsel_entry = {
        'seq': 583, 'type': 'finding',
        'ref': 'docs/CRITICALITY-TIERS.md:469,docs/CRITICALITY-TIERS.md:470,'
               'docs/CRITICALITY-TIERS.md:471,docs/CRITICALITY-TIERS.md:472,'
               'sairnlegacy.html:3979,sairnlegacy.html:4350,sairnlegacy.html:4370',
        'summary': 'leg_keepsakeorders -- confirmed no price field, the '
                   'id-only-reference-to-a-resource-holding-the-real-identity '
                   'convention that has held grd_dreamclose/rf_buildings/'
                   'bld_selections at B all session.',
    }
    ck('F-BLDSEL, THE EXACT REAL INCIDENT: bld_selections named ONLY in '
       "summary prose (a precedent comparison) does NOT count as a mention "
       'under the FIXED signal -- it is genuinely never cited in ref',
       last_mention_seqs([bldsel_entry], ['bld_selections'])['bld_selections'] is None)
    ck('F-LEGACY, THE FIXTURE THAT MUST FAIL: the SAME entry, run through '
       'the RETIRED prose-scanning function, INCORRECTLY finds bld_selections '
       '-- this is not a hypothetical, it is the exact bug that shipped for '
       'real at log #584, proven here by making the old code fail this check',
       'bld_selections' in all_mentioned_text_LEGACY_PROSE_SCAN([bldsel_entry]))
    refcite_entry = {
        'seq': 590, 'type': 'check', 'ref': 'leg_keepsakeorders',
        'summary': 'checked leg_keepsakeorders directly for real this time',
    }
    ck('F-REFCITE, THE POSITIVE CASE, REWRITTEN 2026-09-28 (the original '
       'version only checked a FILE NAME appeared in ref, never a resource, '
       'and had a dead "if False else" branch): a resource genuinely named '
       'IN ref -- a real citation, not a file:line and not a summary-prose '
       'comparison -- DOES still register through last_mention_seqs(), the '
       'exact function cold_pool()/undirected_order() call. The fix narrows '
       'the signal to ref, it does not silence it entirely.',
       last_mention_seqs([refcite_entry], ['leg_keepsakeorders'])['leg_keepsakeorders'] == 590)

    # --- REALISTIC-TRANSITION FIXTURES FOR draw_order/undirected_order,     ---
    # --- added 2026-09-28 (Michael's direct instruction). The ordering      ---
    # --- fixtures added with --draw/--undirected (above, in this same file) ---
    # --- were ALL teleported-in: hand-built {name: seq} dicts, never        ---
    # --- produced by the real workflow. These drive the ACTUAL hover_log.py ---
    # --- machinery and the ACTUAL git-push path this fixture already        ---
    # --- built, so the bad/interesting state is REACHED, not injected.      ---
    import hover_log as _hlog
    real_hlog_path = _hlog.LOG_PATH
    try:
        real_log = os.path.join(tempfile.mkdtemp(), 'real_transitions.jsonl')
        _hlog.LOG_PATH = real_log

        def real_append(summary, ref=''):
            """Drive the REAL cmd_add, not a hand-appended dict -- the same
            function a live session calls, so every field this test reads
            back (seq, ts, hash chain) is genuinely produced by it. Every
            call targets 'platform' on purpose (this fixture is entirely
            about resource staleness, not agent rotation), so the REAL
            adjacent-repeat interlock would refuse every call after the
            first without a reason -- declared honestly here rather than
            varying targets artificially just to dodge it. `ref` is passed
            through to --ref: after the 2026-09-28 ref-only fix, a resource
            name only ever registers as a mention via `ref`, never `summary`
            prose, so a fixture asserting a real mention must cite the
            resource there, the same way a live session's own --ref would."""
            import contextlib
            buf = io.StringIO()
            argv = ['--add', '--type', 'check', '--target', 'platform',
                    '--summary', summary, '--same-target-reason',
                    'realistic-transition fixture, same target by design']
            if ref:
                argv += ['--ref', ref]
            with contextlib.redirect_stdout(buf):
                rc = _hlog.cmd_add(argv)
            if rc != 0:
                raise RuntimeError('real_append failed for fixture: %r -- %s'
                                   % (summary, buf.getvalue()))

        # T1: "right after a log append" -- mention beta, then five filler
        # entries (simulating other real session activity advancing the
        # tip), then mention alpha. gamma is never mentioned at all. The
        # mentions are cited via --ref (real citations), not summary prose,
        # matching the ref-only signal these fixtures are meant to drive.
        real_append('looked at resource_beta today', ref='resource_beta')
        for i in range(5):
            real_append('unrelated filler entry number %d' % i)
        real_append('looked at resource_alpha just now', ref='resource_alpha')
        real_entries = load_log_entries(real_log)
        real_tip = max(e['seq'] for e in real_entries)
        real_last = last_mention_seqs(real_entries, ['resource_alpha', 'resource_beta',
                                                      'resource_gamma'])
        u1 = [r[0] for r in undirected_order(
            [('resource_alpha', 'B'), ('resource_beta', 'B'), ('resource_gamma', 'B')],
            real_last, real_tip)]
        ck('T1 (real log append): resource_alpha, mentioned in the entry that '
           'IS the current tip, has REAL staleness 0 and sinks to the bottom '
           '-- not hand-set to 0, computed from an actual cmd_add call',
           u1[-1] == 'resource_alpha')
        ck('T1: resource_gamma, never mentioned by any real entry, sorts '
           'FIRST (infinity) ahead of resource_beta, which a real entry did '
           'mention, just six entries ago', u1[0] == 'resource_gamma')
        ck('T1: resource_beta sorts between them -- mentioned, but staler '
           'than the just-logged alpha', u1[1] == 'resource_beta')

        # T2: "right after a rotation-cycle close" -- the sweep that just
        # picked resource_gamma (T1's top pick) gets LOGGED for real, the
        # same way a live draw's own findings would be. Re-derive from the
        # REAL log after this second real transition and confirm gamma sinks
        # while nothing else's relative order silently breaks.
        real_append('COLD-SCAN DRAW picked resource_gamma, zero findings',
                    ref='resource_gamma')
        real_entries2 = load_log_entries(real_log)
        real_tip2 = max(e['seq'] for e in real_entries2)
        real_last2 = last_mention_seqs(real_entries2, ['resource_alpha', 'resource_beta',
                                                        'resource_gamma'])
        u2 = [r[0] for r in undirected_order(
            [('resource_alpha', 'B'), ('resource_beta', 'B'), ('resource_gamma', 'B')],
            real_last2, real_tip2)]
        ck('T2 (rotation-cycle close, real second append): resource_gamma, '
           'just drawn and logged, is now the FRESHEST and sinks to the '
           'bottom -- the mechanism self-corrects across a real draw-then-log '
           'cycle without needing to be told gamma was "handled"',
           u2[-1] == 'resource_gamma')
        ck('T2: resource_beta is now the stalest of the three and rises to '
           'the top, purely as a side effect of gamma advancing past it',
           u2[0] == 'resource_beta')
    finally:
        _hlog.LOG_PATH = real_hlog_path

    # T3: "right after a pull" -- reuse the REAL stale_clone/bare_repo/push
    # already built above (a genuine git push advancing origin/main past a
    # clone's own checkout) and combine it with a REAL log, rather than a
    # hand-passed resources list, to drive draw_order/undirected_order
    # end-to-end through the actual post-pull pipeline.
    real_resources_post_pull = _parse_tier_rows(read_tiers_text(stale_clone))
    t3_log = os.path.join(tempfile.mkdtemp(), 'post_pull.jsonl')
    with open(t3_log, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'type': 'check', 'seq': 1,
                            'ref': 'old_only_resource', 'summary':
                            'looked at old_only_resource directly today'}) + '\n')
    t3_entries = load_log_entries(t3_log)
    t3_last = last_mention_seqs(t3_entries, [n for n, t in real_resources_post_pull])
    u3 = [r[0] for r in undirected_order(real_resources_post_pull, t3_last, 1)]
    ck('T3 (real post-pull): new_resource_on_origin -- reachable ONLY because '
       'read_tiers_text() genuinely fetched past the stale clone\'s working '
       'tree -- sorts FIRST as never-mentioned, through the real git pipeline, '
       'not a hand-passed resource tuple', u3[0] == 'new_resource_on_origin')

    # --- draw_order: the combined score, locked on hand-built inputs in ---
    # --- both directions before any real draw trusts it (2026-09-27)    ---
    res = [('a_low_never', 'B'), ('b_high_recent', 'B'),
           ('c_high_stale', 'B'), ('d_high_never', 'B'), ('e_unmapped', 'B')]
    app_of = {'a_low_never': 'lowapp', 'b_high_recent': 'highapp',
              'c_high_stale': 'highapp', 'd_high_never': 'highapp'}
    risk_of = {'lowapp': 1, 'highapp': 9}
    last_of = {'a_low_never': None, 'b_high_recent': 99,
               'c_high_stale': 10, 'd_high_never': None, 'e_unmapped': None}
    order = [r[0] for r in draw_order(res, app_of, risk_of, last_of, 100)]
    ck('risk DOMINATES: every high-risk row beats the low-risk row even '
       'though the low-risk row was never mentioned',
       order.index('a_low_never') > max(order.index('b_high_recent'),
                                        order.index('c_high_stale'),
                                        order.index('d_high_never')))
    ck('within one app, NEVER-mentioned beats stale-mentioned',
       order.index('d_high_never') < order.index('c_high_stale'))
    ck('within one app, stale-mentioned beats recently-mentioned',
       order.index('c_high_stale') < order.index('b_high_recent'))
    ck('an unmapped resource scores risk 0 and SINKS below mapped rows, '
       'never silently wins', order[-1] == 'e_unmapped')
    tie = [r[0] for r in draw_order(
        [('zeta', 'B'), ('alpha', 'B')], {'zeta': 'x', 'alpha': 'x'},
        {'x': 5}, {'zeta': None, 'alpha': None}, 50)]
    ck('equal risk and equal staleness falls to the ALPHABETICAL tiebreak',
       tie == ['alpha', 'zeta'])
    ck('app_risk_from_ddw REFUSES (not all-zero) when the script is absent',
       _raises(NoRepo, app_risk_from_ddw, tempfile.mkdtemp(prefix='no_ddw_')))

    # --- FRESHNESS FLOOR, added 2026-09-28 after the real 3-draws-in-a-row ---
    # --- diagnosis (log #570/#571/#574) -- locked BOTH directions before   ---
    # --- trusting it on real data, per the blind-analysis discipline.     ---
    ff_res = [('exhausted_a', 'B'), ('exhausted_b', 'B'), ('stale_lowrisk', 'B'),
              ('borderline_highrisk', 'B')]
    ff_app = {'exhausted_a': 'highapp', 'exhausted_b': 'highapp',
              'stale_lowrisk': 'lowapp', 'borderline_highrisk': 'edgeapp'}
    ff_risk = {'highapp': 9, 'lowapp': 1, 'edgeapp': 9}
    ff_last = {'exhausted_a': 95, 'exhausted_b': 90,   # staleness 5, 10 -- both < 30
              'stale_lowrisk': 50,                     # staleness 50 -- >= 30
              'borderline_highrisk': 70}                # staleness 30 -- exactly AT the floor
    ff_order = [r[0] for r in draw_order(ff_res, ff_app, ff_risk, ff_last, 100)]
    ck('THE REAL FAILURE THIS FIXES: a HIGH-risk app with NO resource at or '
       'past the floor (max staleness 10, both under 30) no longer beats a '
       'LOW-risk app that genuinely has stale ground (staleness 50) -- '
       'reproduces the exact shape of log #570/#571/#574',
       ff_order.index('stale_lowrisk') < ff_order.index('exhausted_a')
       and ff_order.index('stale_lowrisk') < ff_order.index('exhausted_b'))
    ck('NEGATIVE CASE: a resource EXACTLY AT the floor (staleness 30, not '
       'above it) DOES count as stale ground -- its high-risk app is NOT '
       'gated, and it beats the low-risk app on risk as normal (the gate '
       'must not be so eager it swallows real, merely-adequate staleness)',
       ff_order.index('borderline_highrisk') < ff_order.index('stale_lowrisk'))
    ck('within the exhausted (gated) app, the ORIGINAL staleness ordering '
       'still applies -- the gate demotes the whole app, it does not '
       'reshuffle resources inside it: exhausted_b (staleness 10) is '
       'staler than exhausted_a (staleness 5), so it still sorts first '
       'even though both are below the floor', ff_order.index('exhausted_b')
       < ff_order.index('exhausted_a'))
    # A never-mentioned resource always counts as stale ground, regardless
    # of the floor's numeric value -- infinity is never "under" anything.
    ff_res2 = [('never_seen', 'B'), ('barely_stale', 'B')]
    ff_app2 = {'never_seen': 'quietapp', 'barely_stale': 'quietapp'}
    ff_order2 = [r[0] for r in draw_order(
        ff_res2, ff_app2, {'quietapp': 1}, {'never_seen': None, 'barely_stale': 95}, 100)]
    ck('an app with ANY never-mentioned resource always has stale ground, '
       'no matter how low its risk or how fresh its OTHER resources',
       ff_order2 == ['never_seen', 'barely_stale'])

    # --- THE PER-WINDOW SHARE CAP, 2026-09-28, measured before built:      ---
    # --- sairngrounds at 39% of the recently-read pool and ~70% of the    ---
    # --- last ten draws, purely on risk dominance. Locked both ways plus  ---
    # --- the small-sample guard BEFORE the first capped draw runs.        ---
    # hog: risk 9, 5 of 7 recent reads (share .71 > 1/3), one stale row left.
    # quiet: risk 1, 2 recent reads, one stale row. total_recent = 7 >= 6.
    cap_res = [('hog_stale', 'B'), ('hog_r1', 'B'), ('hog_r2', 'B'),
               ('hog_r3', 'B'), ('hog_r4', 'B'), ('hog_r5', 'B'),
               ('quiet_stale', 'B'), ('quiet_r1', 'B'), ('quiet_r2', 'B')]
    cap_app = {n: ('hogapp' if n.startswith('hog') else 'quietapp') for n, _ in cap_res}
    cap_risk = {'hogapp': 9, 'quietapp': 1}
    cap_last = {'hog_stale': 40, 'hog_r1': 99, 'hog_r2': 98, 'hog_r3': 97,
                'hog_r4': 96, 'hog_r5': 95,
                'quiet_stale': 30, 'quiet_r1': 94, 'quiet_r2': 93}
    cap_order = [r[0] for r in draw_order(cap_res, cap_app, cap_risk, cap_last, 100)]
    ck('F-CAP1, THE MEASURED FAILURE SHAPE: an app holding >1/3 of the '
       'recently-read pool (5/7) sinks below a low-risk app with stale '
       'ground, even though its own risk is 9x and it still has a stale '
       'row of its own -- the monopoly breaks',
       cap_order.index('quiet_stale') < cap_order.index('hog_stale'))
    ck('F-CAP1b: the capped app WAITS, it does not vanish -- its stale row '
       'still outranks every no-stale-ground row and it is still in the list',
       'hog_stale' in cap_order)
    control = [r[0] for r in draw_order(cap_res, cap_app, cap_risk, cap_last,
                                        100, share_cap=None)]
    ck('F-CAP-CONTROL, KNOWN-BAD, MUST KEEP FAILING: the UNCAPPED ordering '
       '(share_cap=None) puts the saturated high-risk app first -- the '
       'exact pre-cap behavior measured live; if this control ever agrees '
       'with F-CAP1, the fixture ground moved',
       control.index('hog_stale') < control.index('quiet_stale'))
    at_cap_last = dict(cap_last)
    # exactly 1/3: hog 3 recent of 9 total -- NOT capped (strict >)
    at_res = [('hog_stale', 'B'), ('hog_r1', 'B'), ('hog_r2', 'B'), ('hog_r3', 'B'),
              ('quiet_stale', 'B'), ('q1', 'B'), ('q2', 'B'), ('q3', 'B'),
              ('q4', 'B'), ('q5', 'B'), ('q6', 'B')]
    at_app = {n: ('hogapp' if n.startswith('hog') else 'quietapp') for n, _ in at_res}
    at_last = {'hog_stale': 40, 'hog_r1': 99, 'hog_r2': 98, 'hog_r3': 97,
               'quiet_stale': 30, 'q1': 99, 'q2': 98, 'q3': 97, 'q4': 96,
               'q5': 95, 'q6': 94}
    at_order = [r[0] for r in draw_order(at_res, at_app, cap_risk, at_last, 100)]
    ck('F-CAP2 NEGATIVE: a share EXACTLY AT one third (3 of 9) is NOT '
       'capped -- risk ordering stands (the cap must not swallow merely '
       'busy apps)', at_order.index('hog_stale') < at_order.index('quiet_stale'))
    solo_res = [('hog_stale', 'B'), ('hog_r1', 'B'), ('hog_r2', 'B'),
                ('hog_r3', 'B'), ('hog_r4', 'B'), ('hog_r5', 'B'),
                ('fresh_only', 'B')]
    solo_app = {n: ('hogapp' if n.startswith('hog') else 'freshapp') for n, _ in solo_res}
    solo_last = {'hog_stale': 40, 'hog_r1': 99, 'hog_r2': 98, 'hog_r3': 97,
                 'hog_r4': 96, 'hog_r5': 95, 'fresh_only': 99}
    solo_order = [r[0] for r in draw_order(solo_res, solo_app, cap_risk, solo_last, 100)]
    ck('F-CAP3: the cap only bites while ANOTHER app has stale ground -- '
       'when the saturated app is the ONLY one with anything due, its '
       'stale row still leads (a cap that starves the only live app '
       'serves nobody)', solo_order[0] == 'hog_stale')
    tiny_res = [('hog_stale', 'B'), ('hog_r1', 'B'), ('quiet_stale', 'B')]
    tiny_app = {'hog_stale': 'hogapp', 'hog_r1': 'hogapp', 'quiet_stale': 'quietapp'}
    tiny_last = {'hog_stale': 40, 'hog_r1': 99, 'quiet_stale': 30}
    tiny_order = [r[0] for r in draw_order(tiny_res, tiny_app, cap_risk, tiny_last, 100)]
    ck('F-CAP4 SMALL-SAMPLE GUARD: one recent read (below MIN_SAMPLE=6) is '
       '100%% share and still caps NOTHING -- one batch talking to itself '
       'is noise, not a monopoly',
       tiny_order.index('hog_stale') < tiny_order.index('quiet_stale'))

    # --- undirected_order: the permanent post-cold-bucket fallback,      ---
    # --- locked in both directions before the first real sweep uses it   ---
    # --- (2026-09-28, replacing the ad-hoc HEAD-hash workaround at #566) ---
    # FIXTURE-NAMING CORRECTION, caught by the lock on its own first run
    # (2026-09-28): the tie-break pair was originally named 'd_zeta_tie' /
    # 'e_alpha_tie' with the assertion expecting alpha before zeta -- but
    # the code sorts the FULL string, and 'd_' < 'e_' regardless of what
    # follows, so the fixture's OWN naming contradicted the ordering it
    # meant to test. The CODE was never wrong; the fixture's names were.
    # Renamed to alpha_tie/zeta_tie directly so the prefix cannot mislead
    # the assertion again -- the fix is here, not in undirected_order().
    u_res = [('a_high_risk_recent', 'B'), ('b_low_risk_never', 'B'),
             ('c_low_risk_stale', 'B'), ('zeta_tie', 'B'), ('alpha_tie', 'B')]
    u_last = {'a_high_risk_recent': 99, 'b_low_risk_never': None,
              'c_low_risk_stale': 10, 'zeta_tie': 30, 'alpha_tie': 30}
    u_order = [r[0] for r in undirected_order(u_res, u_last, 100)]
    ck('BLIND TO RISK: staleness alone decides, so a HIGH-risk-but-recent '
       'resource sinks below a LOW-risk-but-stale one -- if this mechanism '
       'ever agreed with draw_order on a risk-driven pick, it would no '
       'longer be checking draw_order\'s bias, it would be copying it',
       u_order.index('a_high_risk_recent') > u_order.index('c_low_risk_stale'))
    ck('never-mentioned still sorts first (staleness = infinity)',
       u_order[0] == 'b_low_risk_never')
    ck('seed=None keeps the retired alphabetical order -- the explicit '
       'before-state the F-SEED fixtures below diff against',
       u_order.index('alpha_tie') < u_order.index('zeta_tie'))

    # --- F-SEED: the seeded-random tiebreak, 2026-09-28, locked BEFORE ---
    # --- the first real seeded sweep. Replaced alphabetical because the ---
    # --- resolved-read signal leaves 44 rows tied at NEVER and alpha    ---
    # --- order made "undirected" mean "bld_* forever first".            ---
    tie_res = [(n, 'B') for n in ('t_apple', 't_banana', 't_cherry',
                                   't_damson', 't_elder', 't_fig',
                                   't_grape', 't_hazel')]
    tie_last = {n: None for n, _ in tie_res}
    s1a = [r[0] for r in undirected_order(tie_res, tie_last, 100, seed='seed-one')]
    s1b = [r[0] for r in undirected_order(tie_res, tie_last, 100, seed='seed-one')]
    s2 = [r[0] for r in undirected_order(tie_res, tie_last, 100, seed='seed-two')]
    ck('F-SEED determinism: the same seed reproduces the same order '
       'exactly -- a draw is re-derivable, not a dice roll lost to time',
       s1a == s1b)
    ck('F-SEED reshuffle: a different seed produces a different order '
       'over the same 8-way tie (deterministic sha256 tiebreak -- this '
       'comparison never flakes, it is the same two orders every run)',
       s1a != s2)
    ck('F-SEED is not secretly alphabetical: at least one seeded order '
       'differs from the alphabetical one',
       s1a != sorted(s1a) or s2 != sorted(s2))
    mixed_last = dict(tie_last)
    mixed_last['t_apple'] = 90   # staleness 10 -- REAL signal, not a tie
    m_order = [r[0] for r in undirected_order(tie_res, mixed_last, 100, seed='seed-one')]
    ck('F-SEED scope: the shuffle applies ONLY within a tie group -- a '
       'genuinely fresher resource still sorts strictly after every '
       'never-read row, whatever the seed', m_order[-1] == 't_apple')
    ck('the mechanism takes NO app_of/risk_of argument at all -- structurally '
       'independent of resource_app_map()/app_risk_from_ddw(), so it cannot '
       'fail the way --draw fails (discipline 6: a real fallback does not '
       'share its primary\'s dependency chain)',
       'app_of' not in undirected_order.__code__.co_varnames
       and 'risk_of' not in undirected_order.__code__.co_varnames)
    ck('NEVER EXHAUSTS: even when EVERY resource has been mentioned (no '
       'None values at all), a full ranking is still produced -- unlike '
       'the old cold_pool(), which would report zero candidates here',
       len(undirected_order([('x', 'B'), ('y', 'B')], {'x': 5, 'y': 3}, 10)) == 2)

    # --- THE RESOLVED-READ SIGNAL, 2026-09-28: fixtures written BEFORE the ---
    # --- resolver touches real data. Runs LAST on purpose: it advances the ---
    # --- shared work_repo's tiers file, and T3 above re-reads that file    ---
    # --- from origin -- appending here keeps earlier fixtures' ground      ---
    # --- untouched while still reusing the real bare-origin/push plumbing. ---
    fixapp_v1 = (
        '<html>\n'
        '<div>markup filler</div>\n'
        'function unrelatedFn(){\n'
        'var x = 1;\n'
        '}\n'
        'function saveResAlpha(){\n'
        "var list = ld('res_alpha_fix', []);\n"
        'list.push({id:1});\n'
        "st('res_alpha_fix', list);\n"
        '}\n'
        'function otherFn(){\n'
        "st('res_other_fix', []);\n"
        '}\n'
    )
    with open(os.path.join(work_repo, 'fixapp.html'), 'w', encoding='utf-8') as f:
        f.write(fixapp_v1)
    with open(tiers_file, 'w', encoding='utf-8') as f:
        f.write("| `old_only_resource` | **B** | v1 |\n"
                "| `new_resource_on_origin` | **C** | v2 |\n"
                "| `res_alpha_fix` | **B** | resolver fixture |\n"      # line 3
                "| `res_other_fix` | **C** | resolver fixture |\n")     # line 4
    subprocess.run(['git', 'add', '.'], cwd=work_repo, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'resolver fixture v1'],
                    cwd=work_repo, check=True)
    v1_app_sha = subprocess.run(['git', 'rev-parse', 'HEAD:fixapp.html'],
                                 cwd=work_repo, capture_output=True, text=True,
                                 check=True).stdout.strip()
    v1_tiers_sha = subprocess.run(['git', 'rev-parse', 'HEAD:docs/CRITICALITY-TIERS.md'],
                                   cwd=work_repo, capture_output=True, text=True,
                                   check=True).stdout.strip()
    # v2: five filler lines pushed onto the top of the app file -- REAL,
    # git-produced line drift, the same shape as sairnbuild.html's uniform
    # +14 observed live at log #589.
    with open(os.path.join(work_repo, 'fixapp.html'), 'w', encoding='utf-8') as f:
        f.write('<!-- drift -->\n' * 5 + fixapp_v1)
    subprocess.run(['git', 'add', '.'], cwd=work_repo, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'resolver fixture v2, lines drift +5'],
                    cwd=work_repo, check=True)
    subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=work_repo, check=True)

    names_set = {'res_alpha_fix', 'res_other_fix', 'bld_selections_fix'}
    reader = make_blob_reader(work_repo)

    r_entry = {
        'seq': 700, 'type': 'check',
        'ref': 'fixapp.html:8,docs/CRITICALITY-TIERS.md:4',
        'summary': 'checked res_alpha_fix and res_other_fix; unlike '
                   'bld_selections_fix, which this prose merely name-drops',
        'source_shas': {'fixapp.html': {'sha': v1_app_sha, 'source': 'local-head'},
                        'docs/CRITICALITY-TIERS.md': {'sha': v1_tiers_sha,
                                                       'source': 'local-head'}},
    }
    got = resolved_read_names(r_entry, names_set, reader)
    ck('R1 MUST COUNT (registry row): docs/CRITICALITY-TIERS.md:4 resolves '
       'to res_other_fix -- the row occupying exactly that line, no window',
       'res_other_fix' in got)
    ck('R2 MUST COUNT (own source lines): fixapp.html:8 -- a line inside '
       "saveResAlpha() that does NOT itself name the resource -- resolves "
       'to res_alpha_fix through its function block',
       'res_alpha_fix' in got)
    ck('R3 DRIFTED SHA: the same citation resolves AT THE RECORDED v1 SHA, '
       'even though origin/main has since drifted +5 lines and line 8 there '
       'is now a different function entirely', got == {'res_alpha_fix',
                                                        'res_other_fix'})
    ck('R5 PROSE STILL NEVER COUNTS (the #584 incident stays closed under '
       'the resolver too): bld_selections_fix, name-dropped in summary '
       'only, earns nothing', 'bld_selections_fix' not in got)

    # R4, THE KNOWN-BAD ARM THAT MUST FAIL: a deliberately wrong reader
    # that IGNORES the recorded sha and always reads current origin/main.
    # If this arm ever starts succeeding, the sha plumbing has stopped
    # being load-bearing and the drifted-line bug is back.
    bad_reader = lambda path, sha: reader(path, None)
    bad_got = resolved_read_names(r_entry, names_set, bad_reader)
    ck('R4 KNOWN-BAD MUST FAIL: resolving the SAME entry against current '
       'content instead of the recorded sha does NOT find res_alpha_fix -- '
       'line 8 post-drift lands in unrelatedFn(), proving the recorded sha '
       'is what makes R2/R3 pass, not luck',
       'res_alpha_fix' not in bad_got)

    # R6 / F-582, REWRITTEN 2026-09-28 THE SAME DAY R6 FIRST SHIPPED: the
    # original R6 blessed a best-effort fallback (no recorded sha -> read
    # current origin/main), and the very first full-log measurement showed
    # that fallback mis-crediting for real -- entry #582 cites
    # docs/CRITICALITY-TIERS.md:545 with no source_shas, and line 545 TODAY
    # is scp_water_features' row, so a resource #582 never audited showed a
    # resolved read. A citation without its sha cannot be located in time;
    # it is UNRESOLVED, full stop.
    no_sha_entry = dict(r_entry)
    no_sha_entry.pop('source_shas')
    ns_got = resolved_read_names(no_sha_entry, names_set, reader)
    ck('F-582, THE EXACT OBSERVED MIS-CREDIT SHAPE: an entry with NO '
       'recorded source sha earns NOTHING from file:line citations -- not '
       'even the registry-row citation the retired fallback would have '
       'credited to whatever row holds that line today',
       ns_got == set())
    ck('F-582b: a bare resource name in the SAME sha-less entry still '
       'counts -- the guard removes location-in-time guesswork, not names',
       resolved_read_names({'seq': 582, 'ref': 'res_alpha_fix,docs/CRITICALITY-TIERS.md:4'},
                           names_set, reader) == {'res_alpha_fix'})
    ck('F-582-CONTROL, KNOWN-BAD, MUST KEEP FAILING: the retired fallback '
       '(reading current origin/main for a sha-less citation) DOES credit '
       'res_other_fix from that same citation -- if this control ever stops '
       'crediting, the fixture ground moved; if F-582 above ever starts '
       'crediting, the fallback was silently reintroduced',
       'res_other_fix' in resolve_citation('docs/CRITICALITY-TIERS.md', 4,
                                           reader('docs/CRITICALITY-TIERS.md', None),
                                           names_set))
    ck('R7 BARE NAME still counts, reader present or not',
       'res_alpha_fix' in resolved_read_names(
           {'seq': 1, 'ref': 'res_alpha_fix'}, names_set, reader)
       and 'res_alpha_fix' in resolved_read_names(
           {'seq': 1, 'ref': 'res_alpha_fix'}, names_set, None))
    ck('F-BARENAME, the retired intermediate signal\'s documented blindness: '
       'the bare-name scan gives NO credit for the R2 file:line citation '
       'that the resolver correctly credits',
       'res_alpha_fix' not in ref_only_mentioned_text_RETIRED_BARE_NAME_SCAN([r_entry]))
    ck('R8 UNREADABLE BLOB = NO CREDIT, never a guess: a citation whose '
       'recorded sha does not exist in the object database resolves to '
       'nothing', resolved_read_names(
           {'seq': 1, 'ref': 'fixapp.html:8',
            'source_shas': {'fixapp.html': {'sha': 'f' * 40}}},
           names_set, reader) == set())
    ck('R9 end-to-end: last_mention_seqs() through the resolver credits '
       'res_alpha_fix at seq 700',
       last_mention_seqs([r_entry], ['res_alpha_fix'], reader)['res_alpha_fix'] == 700)

    # R10, THE SEED-BLAST CASE -- the defect the FIRST full-log measurement
    # caught in the whole-block draft before any entry relied on it: one
    # giant seed() function names EVERY resource of an app, and register
    # cells cite seed lines constantly, so whole-block resolution credited
    # all of them at once (every bld_* row read staleness 0 at log #590
    # off three citations). Locked here in both directions.
    seed_lines = (
        'function seed(){\n'
        "st('res_seed_a', [1]);\n"     # line 2
        'var filler = 0;\n'            # line 3
        "st('res_seed_b', [2]);\n"     # line 4
        "st('res_seed_c', [3]);\n"     # line 5
        '}\n'
    ).splitlines()
    seed_names = {'res_seed_a', 'res_seed_b', 'res_seed_c'}
    ck('R10a: a citation to a seed line that NAMES its resource credits '
       'THAT resource only, never the sibling seeds sharing the function',
       resolve_citation('app.html', 4, seed_lines, seed_names) == {'res_seed_b'})
    ck('R10b: a citation to an unnamed line credits only the NEAREST '
       'naming line (line 3 -> line 2 at distance 1 beats line 4... both '
       'at distance 1 -- a genuine tie credits both, and c at distance 2 '
       'stays out)',
       resolve_citation('app.html', 3, seed_lines, seed_names)
       == {'res_seed_a', 'res_seed_b'})

    # R11/R12, THE CROSS-APP FALSE-CREDIT CASE -- caught by the SECOND
    # full-log measurement, again before any entry relied on it: the
    # SAIRNgrounds resource `jobs` was credited from sairnbuild.html
    # citations because sairnbuild's own jobs() helper and nav('jobs')
    # panel id matched a bare word scan. In an .html app file only an
    # st()/ld() STORAGE KEY is a read of the resource.
    collide_lines = (
        'function rJobs(){\n'
        'var list = jobs();\n'                        # bare call -- not a read
        "nav('jobs');\n"                              # panel id -- not a read
        "var real = ld('jobs', []);\n"                # storage key -- IS a read
        '}\n'
    ).splitlines()
    ck('R11: a bare jobs() function call and a quoted nav panel id do NOT '
       'credit the jobs resource -- cited at the call line, the nearest '
       'STORAGE match (line 4) wins and that one genuinely is a read',
       resolve_citation('otherapp.html', 2, collide_lines, {'jobs'}) == {'jobs'}
       and resolve_citation('otherapp.html', 1, collide_lines, {'jobs'}) == {'jobs'})
    no_storage = (
        'function rJobs(){\n'
        'var list = jobs();\n'
        "nav('jobs');\n"
        '}\n'
    ).splitlines()
    ck('R12: the same block with NO storage-key use anywhere resolves to '
       'NOTHING -- a function that only calls helpers and switches panels '
       'never read the resource as data',
       resolve_citation('otherapp.html', 2, no_storage, {'jobs'}) == set())

    # --- F-VOCAB, THE OTHER AUDITOR'S FIND (its seq 280), the exact real ---
    # --- shape at #603's sairngrounds.html:4286 citation: the cited line ---
    # --- names nothing; the NEAREST storage line (distance 1) writes a   ---
    # --- Tier A resource the B/C vocabulary cannot see; the old scan     ---
    # --- fell through PAST it and credited a B resource at distance 4    ---
    # --- that was never audited. Fixtures written before the fix ran on  ---
    # --- real data.                                                      ---
    vocab_lines = (
        'function dcApprove(){\n'
        'var irec={id:1,\n'
        'notes:"approved by someone"};\n'          # line 3 <- the citation
        "invoices.push(irec);st('inv_a_fix',invoices);\n"   # d1: TIER A owner
        'var srec={id:2};\n'
        'var filler=0;\n'
        "sched.push(srec);st('sched_b_fix',sched);\n"       # d4: TIER B
        '}\n'
    ).splitlines()
    bc_only = {'sched_b_fix'}
    full_vocab = {'sched_b_fix', 'inv_a_fix'}
    ck('F-VOCAB: with ownership decided against the FULL vocabulary, the '
       'citation whose nearest owner is the Tier A resource credits '
       'NOBODY -- ownership stops at the true nearest line, out of '
       'vocabulary means out of credit, never pass-through',
       resolve_citation('app.html', 3, vocab_lines, bc_only, full_vocab) == set())
    ck('F-VOCAB-CONTROL, KNOWN-BAD, MUST KEEP FAILING: the retired '
       'single-vocabulary scan (all_names_set=None) blows past the unseen '
       'Tier A owner and credits sched_b_fix at distance 4 -- the exact '
       'mis-credit the other auditor caught on my real #603 entry',
       resolve_citation('app.html', 3, vocab_lines, bc_only, None)
       == {'sched_b_fix'})
    ck('F-VOCAB-B: when the nearest owner IS in B/C, the fix changes '
       'nothing -- cited at the schedule push line itself, sched_b_fix '
       'still credits under the full vocabulary',
       resolve_citation('app.html', 7, vocab_lines, bc_only, full_vocab)
       == {'sched_b_fix'})
    tie_lines = (
        "function f(){\n"
        "st('inv_a_fix', a);\n"        # line 2 -- distance 2 from line 4
        "var x=1;\n"
        "var cited=0;\n"               # line 4 <- the citation
        "var y=2;\n"
        "st('sched_b_fix', b);\n"      # line 6 -- distance 2 from line 4
        "}\n").splitlines()
    ck('F-VOCAB-TIE: an A and a B owner at EQUAL distance (both d=2, '
       'verified by construction) credit the B one -- the tie is genuine, '
       'the B resource genuinely is that near, and only the out-of-vocab '
       'half of the tie drops',
       resolve_citation('app.html', 4, tie_lines, bc_only, full_vocab)
       == {'sched_b_fix'}
       # and the same citation under the OLD vocab also credits it -- the
       # tie arm distinguishes tie handling from the pass-through bug:
       and resolve_citation('app.html', 4, tie_lines, bc_only, None)
       == {'sched_b_fix'})
    ck('F-VOCAB-REG: a registry-row citation landing on a Tier A row '
       'credits nobody under the full vocabulary too (was already true '
       'via the names_set filter -- locked so it stays true)',
       resolve_citation('docs/CRITICALITY-TIERS.md', 1,
                        ['| `inv_a_fix` | **A** | **A** | x |'],
                        bc_only, full_vocab) == set())

    # --- _print_watch(), 2026-09-28: a drawn/swept resource with an OPEN ---
    # --- watchlist item must surface it inline, not depend on memory.    ---
    import io as _io
    import contextlib as _ctxlib
    import hover_watchlist as _wl
    real_watch_file = _wl.WATCH_FILE
    try:
        import tempfile as _tf
        _wl.WATCH_FILE = os.path.join(_tf.mkdtemp(prefix='hover_csp_watch_'), 'w.json')
        _wl.cmd_add('watch_fix_res', 'flag', 'looks like a gate, has none yet', seq=1)
        buf = _io.StringIO()
        with _ctxlib.redirect_stdout(buf):
            _print_watch('watch_fix_res')
        ck('_print_watch() surfaces an OPEN watchlist item inline on the '
           'exact resource it is drawn for', 'watch_fix_res' in buf.getvalue()
           and 'flag' in buf.getvalue())
        buf2 = _io.StringIO()
        with _ctxlib.redirect_stdout(buf2):
            _print_watch('some_other_resource_never_watched')
        ck('_print_watch() prints NOTHING for a resource with no open item '
           '-- silence is the normal case, not an error', buf2.getvalue() == '')
    finally:
        _wl.WATCH_FILE = real_watch_file

    print()
    print('%d ok, %d failed' % (ok_count[0], fail_count[0]))
    return fail_count[0] == 0


def _raises(exc_type, fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False
    except exc_type:
        return True


def main(argv):
    if '--selftest' in argv:
        ok = run_fixtures()
        sys.exit(0 if ok else 1)
    pick = None
    if '--pick' in argv:
        i = argv.index('--pick')
        pick = int(argv[i + 1]) if i + 1 < len(argv) else 5
    repo = discover_repo(argv)
    if '--draw' in argv:
        i = argv.index('--draw')
        n = int(argv[i + 1]) if i + 1 < len(argv) else 3
        try:
            draw(repo, n)
        except NoRepo as e:
            print('COULD NOT RUN: %s' % e)
            return 2
        return 0
    if '--undirected' in argv:
        i = argv.index('--undirected')
        n = int(argv[i + 1]) if i + 1 < len(argv) else 3
        try:
            undirected_sweep(repo, n)
        except NoRepo as e:
            print('COULD NOT RUN: %s' % e)
            return 2
        return 0
    try:
        cold, warm = cold_pool(repo)
    except NoRepo as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    _print_report(cold, warm, pick=pick)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
