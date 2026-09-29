"""hover_log.py -- the hover auditor's own black-box self-log.

WHAT THIS IS. An append-only, hash-chained record of the hover auditor's own
actions: every check run, every finding made, and every time a finding was
deliberately NOT reported. Built 2026-09-14 on direct instruction, because an
auditor whose own actions are not independently verifiable is asking everyone
else to meet a standard it does not meet itself.

REUSES ITEM 35'S PATTERN, on purpose, not reinvented: each entry's hash folds
in the previous entry's hash (api/audit-checkpoint.js's digestOf/canonical
shape, ported here). A retroactive edit to any entry changes its hash, which
breaks every hash after it -- `--verify` walks the chain from GENESIS and
says exactly where it broke, the same three-state contract (clean / broken /
could-not-check) as the platform's own checkpoint tooling.

WHERE THIS LIVES, AND WHY. Outside SAIRN-hover's git repository entirely --
this is the hover auditor's own operational tooling, not platform code, and
logging its own actions inside the repo it audits would blur exactly the
line this role exists to hold: never build and verify the same thing.

    python hover_log.py --add --type check    --target <agent-or-subject> --summary "..."
    python hover_log.py --add --type finding  --target <agent-or-subject> --summary "..." [--severity ...] [--vector ...]
    python hover_log.py --add --type no-report --target <agent-or-subject> --summary "..."
    python hover_log.py --verify
    python hover_log.py --tail 20
    python hover_log.py --tail 20 --json

USE --summary-file INSTEAD OF --summary WHENEVER THE TEXT CONTAINS A
BACKTICK, A CODE IDENTIFIER, OR ANYTHING ELSE A SHELL MIGHT TOUCH -- put the
usage note here, not only buried at the --summary-file flag's own definition
below, because two real entries this session (seq 193, 196) were silently
mangled by bash command-substitution on an unescaped backtick inside
--summary, and both happened because this top-of-file block is what gets
read before typing the command, and it never mentioned --summary-file was an
option at all:
    Write the text to a scratch file, then:
    python hover_log.py --add --type check --target <x> --summary-file <path>
--summary is fine for a short line with no inline code; anything longer or
carrying a `backtick`, a function name, or a file path should go through
--summary-file instead of trusting careful quoting to survive the shell.

OPTIONAL --vector ON A FINDING, CVSS-STYLE COMPACT NOTATION ADAPTED TO
THIS PLATFORM'S OWN REAL SEVERITY AXES -- not CVSS's exact fields (AV/AC/
PR/UI don't all map onto a structural finding), but the same idea: a short,
comparable string alongside the free-text severity word, so findings are
comparable to each other over time and not only describable in prose.

    T:{A,B,C}/EX:{L,M,H,NA}/IM:{L,M,H}/SC:{C,S}

    T   Tier of the asset (A/B/C, this platform's own tiering)
    EX  Exploitability -- how easy to trigger (L/M/H), or NA for a
        structural/operational finding where nothing has to be exploited
        (the existing rule: drop exploitability, don't force a number)
    IM  Impact -- how much damage if it fires (L/M/H)
    SC  Scope -- C(ontained, stays inside the affected component) or
        S(preading, reaches resources outside it) -- CVSS's own Scope idea

    Example, security-shaped: T:A/EX:H/IM:H/SC:S
    Example, structural:      T:A/EX:NA/IM:M/SC:C

Validated on --add; malformed vectors are refused rather than stored
wrong, the same fail-closed standard as the rest of this tool.

Exit 0 clean / verified, 1 a finding was just added or the chain is broken,
2 could not run (log unreadable, bad args). Three states, never two --
same convention as every checker on this platform, because "could not tell"
folded into "fine" is the single most repeated defect class here.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
# HOVER_LOG_PATH_OVERRIDE, added 2026-09-23. Real incident: a DIFFERENT
# tool's selftest shelled out to `python hover_log.py --add` as a real
# subprocess to test end-to-end, monkey-patching its OWN in-process LOG_PATH
# first -- which does nothing to a separate interpreter that re-imports this
# module fresh and reads the hardcoded default below. The fixture's write
# landed for real in the production log (entry #464), a test artifact
# permanently in a hash-chained history that cannot be edited out. Opt-in
# only, and empty-by-default: unset, this resolves to the exact same path
# as before for every normal invocation -- nothing about ordinary --add/
# --verify/--tail usage changes. A subprocess-based test sets this env var
# on ITS OWN call to redirect the child process's write, the only way to
# actually isolate a real subprocess round-trip.
LOG_PATH = os.environ.get('HOVER_LOG_PATH_OVERRIDE') or os.path.join(HERE, 'hover-audit-log.jsonl')
GENESIS = 'genesis:hover-auditor-self-log:v1'
# KNOWN_INSTANCE_LOGS, added 2026-09-28 for --contradicts-external. Same
# literal-list convention hover_cold_scan_pool.py's _KNOWN_CLONES and
# hover_coverage_ledger.py's own copy already use for finding OTHER
# platform git clones -- reused here for the SAME reason (every tool in
# this directory is deliberately standalone, no cross-file import), applied
# to the one other hover instance's self-log instead of a platform repo.
# A plain module global, not an env-var override, because every test below
# monkeypatches it in-process (the same pattern BEACON_PATH/LOG_PATH already
# use in this file's own --selftest) -- no subprocess round-trip is needed,
# so there is no HOVER_LOG_PATH_OVERRIDE-style real-write risk to guard
# against here.
KNOWN_INSTANCE_LOGS = {
    'hover': r'C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hover\hover-audit-log\hover-audit-log.jsonl',
    'hover2': r'C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hover2\hover-audit-log\hover-audit-log.jsonl',
}
TYPES = ('check', 'finding', 'no-report', 'note')
SEVERITIES = ('critical', 'high', 'moderate', 'low', '')

# ── STALENESS GUARD, ADDED 2026-09-23 ───────────────────────────────────────
# Real incident: hover2 logged leg_aftercare against a pre-fix version of a
# row hank had already landed on origin/main -- the read happened against a
# local clone that had not pulled hank's fix yet, and nothing caught it
# before the finding was committed to the hash-chained log, where nothing can
# be un-said. This closes that gap the same way cc's claim-matcher fix
# closed its own: CHECK AT THE LAST POSSIBLE MOMENT, not back when the read
# happened. --source <path>[:<sha>][,<path>...] on a finding stamps, for each
# path, the sha this role's OWN LOCAL CLONE had committed for it (git
# rev-parse HEAD:<path> -- the honest proxy for 'what I actually read', since
# that is genuinely the content the Read tool returned) unless the caller
# supplies an explicit override (path:sha, for the case worked several times
# tonight -- extracting a file from a specific commit via `git show <sha>:
# <path>` because the local clone was already known stale). Immediately
# before the log write -- after every other check in cmd_add has already
# run, the last line before the file is opened -- every captured sha is
# re-derived against CURRENT origin/main and compared. A real mismatch (the
# path answers cleanly with a DIFFERENT sha, or answers cleanly that the
# path no longer exists there at all) is a CONFIRMED, non-ambiguous signal
# and REFUSES the write outright -- nothing is appended, the caller is told
# to re-read and re-derive the finding before trying again.
#
# FAIL-OPEN ON AMBIGUITY IS DELIBERATE HERE AND IS NOT THE SAME RULE AS
# EVERY OTHER CHECKER ON THIS PLATFORM, stated so a future reader does not
# read this file's own fail-CLOSED doctrine (PR SS1.11, quoted at the top of
# this file) and conclude this contradicts it. A checker reports a verdict
# ABOUT THE WORLD, and folding "could not tell" into "passed" there means a
# false claim gets trusted. This is a WRITE-PATH GUARD deciding whether to
# let an already-formed, independently-derived finding land in an
# append-only log -- refusing it on infrastructure noise (git unreachable,
# a fetch timeout) costs a REAL, valid finding for a reason that has nothing
# to do with whether it is actually stale, which is the exact "a gate that
# must be talked past routinely is a gate people learn to talk past" failure
# CLAUDE.md already names, and the identical shape cc's own claim-matcher
# fix just chose for the identical reason (lexical overlap: warn, never
# refuse; file-set intersection: the real signal, still refuses). So: a
# CONFIRMED mismatch refuses. An UNRESOLVABLE check does not refuse -- it
# still logs, but the entry carries staleness_check='could_not_verify' and a
# reason, printed to the terminal too, so "could not tell" is disclosed
# rather than silently indistinguishable from "confirmed fresh". Never
# folded into a silent pass; only ever not turned into a silent block.

_KNOWN_CLONES = (
    'C:/Users/marsh/Documents/SAIRN-hover',
    'C:/Users/marsh/Documents/SAIRN-hover2',
)


def discover_repo(argv=None):
    """Identical contract to every other tool in this directory's own
    discover_repo() -- --repo, then $HOVER_LEDGER_REPO, then the first
    existing known clone, then None (COULD NOT TELL)."""
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


def _git(repo, args, timeout=20):
    """(returncode, stdout, stderr). Never raises on a nonzero exit -- a
    nonzero exit from git is often the real answer (path not found), not a
    failure of this function. Only OSError/TimeoutExpired (git itself could
    not be run) is a genuine could-not-verify condition, and those ARE
    caught here and turned into a synthetic nonzero/blank result so callers
    have one shape to handle rather than two."""
    try:
        r = subprocess.run(['git'] + args, cwd=repo, capture_output=True,
                            text=True, encoding='utf-8', timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, '', 'could not run git %s: %s' % (args, e)


def local_head_sha(repo, path):
    """The blob sha this clone's own local HEAD has committed for path --
    the honest 'what I actually read' proxy, captured at --source parse
    time. Returns (sha, error); error is None on success."""
    rc, out, err = _git(repo, ['rev-parse', 'HEAD:' + path])
    if rc == 0:
        return out.strip(), None
    return None, err.strip() or 'git rev-parse HEAD:%s failed (rc=%d)' % (path, rc)


def current_origin_sha(repo, path):
    """The blob sha CURRENTLY on origin/main for path, fetched fresh right
    now. Returns (sha, status, detail):
      status='ok'              sha is real and current
      status='not_found'       origin/main answered cleanly: no such path
                                there any more -- a REAL, confirmed change,
                                not ambiguous
      status='could_not_verify' fetch or git itself failed -- infrastructure
                                noise, genuinely ambiguous
    """
    rc, _, err = _git(repo, ['fetch', 'origin', '--quiet'], timeout=30)
    if rc != 0:
        return None, 'could_not_verify', 'git fetch failed: %s' % err.strip()
    rc, out, err = _git(repo, ['rev-parse', 'origin/main:' + path])
    if rc == 0:
        return out.strip(), 'ok', None
    if 'does not exist' in err or 'exists on disk, but not in' in err:
        return None, 'not_found', err.strip()
    return None, 'could_not_verify', err.strip() or 'git rev-parse failed (rc=%d)' % rc


def parse_source_arg(raw):
    """'path1,path2:sha2' -> [(path, explicit_sha_or_None), ...]. Empty
    segments are ignored (a trailing comma is not an error)."""
    out = []
    for seg in raw.split(','):
        seg = seg.strip()
        if not seg:
            continue
        if ':' in seg:
            path, sha = seg.split(':', 1)
            out.append((path.strip(), sha.strip()))
        else:
            out.append((seg, None))
    return out


def capture_read_time_shas(repo, sources):
    """For each (path, explicit_sha) pair: use the explicit sha if given,
    else derive it from this clone's own local HEAD. Returns
    {path: {'sha': str_or_None, 'source': 'explicit'|'local-head',
             'capture_error': str_or_None}} -- a path whose sha could not be
    captured at all still gets an entry, with sha=None and capture_error
    set, so the write-time check has something to report rather than a
    silently missing key."""
    out = {}
    for path, explicit in sources:
        if explicit:
            out[path] = {'sha': explicit, 'source': 'explicit', 'capture_error': None}
            continue
        if not repo:
            out[path] = {'sha': None, 'source': 'local-head',
                          'capture_error': 'no readable clone to derive a local sha from'}
            continue
        sha, err = local_head_sha(repo, path)
        out[path] = {'sha': sha, 'source': 'local-head', 'capture_error': err}
    return out


def verify_freshness_at_write_time(repo, source_shas):
    """The LAST check before the log file is opened for writing. Mutates
    nothing; returns (verdict_per_path, stale_paths, could_not_verify_paths).
    stale_paths non-empty means the caller MUST refuse the write. Never
    raises."""
    verdict = {}
    stale, unresolved = [], []
    for path, info in source_shas.items():
        read_sha = info.get('sha')
        if not read_sha:
            verdict[path] = {'status': 'could_not_verify',
                              'detail': info.get('capture_error') or 'no read-time sha captured'}
            unresolved.append(path)
            continue
        if not repo:
            verdict[path] = {'status': 'could_not_verify', 'detail': 'no readable clone'}
            unresolved.append(path)
            continue
        current, status, detail = current_origin_sha(repo, path)
        if status == 'could_not_verify':
            verdict[path] = {'status': 'could_not_verify', 'detail': detail}
            unresolved.append(path)
        elif status == 'not_found':
            verdict[path] = {'status': 'stale',
                              'detail': 'no longer exists on origin/main: %s' % detail}
            stale.append(path)
        elif current != read_sha:
            verdict[path] = {'status': 'stale',
                              'detail': 'read-time sha %s != current origin/main sha %s'
                                        % (read_sha[:12], current[:12])}
            stale.append(path)
        else:
            verdict[path] = {'status': 'fresh', 'detail': None}
    return verdict, stale, unresolved
VECTOR_FIELDS = {
    'T': ('A', 'B', 'C'),
    'EX': ('L', 'M', 'H', 'NA'),
    'IM': ('L', 'M', 'H'),
    'SC': ('C', 'S'),
}
VECTOR_ORDER = ('T', 'EX', 'IM', 'SC')

EXIT_CLEAN = 0
EXIT_FINDING_OR_BROKEN = 1
EXIT_COULD_NOT_RUN = 2


def canonical(value):
    """Same recursive, sorted-key canonicalisation as api/audit-checkpoint.js's
    canonical(), so the hashing rule is auditable by comparison rather than by
    trust: two independent implementations of the same idea, not one hoping to
    be read correctly twice."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return json.dumps(value)
    if isinstance(value, list):
        return '[' + ','.join(canonical(v) for v in value) + ']'
    if isinstance(value, dict):
        keys = sorted(value.keys())
        return '{' + ','.join(json.dumps(k) + ':' + canonical(value[k]) for k in keys) + '}'
    raise TypeError('cannot canonicalise %r' % (value,))


def digest_of(prev_digest, entry_without_hash):
    h = hashlib.sha256()
    h.update((prev_digest + '\n').encode('utf-8'))
    h.update((canonical(entry_without_hash) + '\n').encode('utf-8'))
    return h.hexdigest()


def read_all():
    """Every line, in file order. Returns [] if the file does not exist yet --
    that is a fresh log, not a could-not-read error."""
    if not os.path.isfile(LOG_PATH):
        return []
    out = []
    with open(LOG_PATH, encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception as e:
                raise ValueError('line %d is not valid JSON: %s' % (i, e))
    return out


def _current_instance_name():
    """Which of KNOWN_INSTANCE_LOGS this running copy IS -- derived from
    LOG_PATH, never hardcoded, so a clone's own contradicts_external cannot
    accidentally point at itself under the wrong assumption."""
    log_path_norm = os.path.normcase(os.path.abspath(LOG_PATH))
    for name, path in KNOWN_INSTANCE_LOGS.items():
        if os.path.normcase(os.path.abspath(path)) == log_path_norm:
            return name
    return None


def read_external_seqs(path):
    """Read ONLY the 'seq' values out of another hover instance's raw
    hover-audit-log.jsonl -- DATA, never code. No .py file under the other
    instance's directory is opened, imported, or executed by this function
    or anything it calls; it is a plain JSON-lines parse of one field.

    Returns (seqs_set, error). error is None on success, a short string on
    any failure (file missing, unreadable, malformed) -- the caller turns
    that into the COULD-NOT-VERIFY third state, never a silent pass and
    never a silent full refuse on mere unreadability (only a CONFIRMED
    missing seq refuses; see cmd_add)."""
    if not os.path.isfile(path):
        return None, 'no such file'
    try:
        seqs = set()
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if 'seq' in row:
                    seqs.add(row['seq'])
        return seqs, None
    except OSError as e:
        return None, 'could not open (%s)' % e
    except Exception as e:
        return None, 'could not parse (%s)' % e


def last_entry():
    rows = read_all()
    return rows[-1] if rows else None


def parse_vector(v):
    """Parse and validate a T:x/EX:x/IM:x/SC:x vector. Returns (dict, None)
    on success, (None, error_message) on failure -- never a partial guess,
    the same fail-closed standard as the register's own --add validation
    this tool otherwise mirrors."""
    parts = v.split('/')
    seen = {}
    for p in parts:
        if ':' not in p:
            return None, 'malformed segment %r -- expected KEY:VALUE' % p
        k, val = p.split(':', 1)
        if k not in VECTOR_FIELDS:
            return None, 'unknown vector field %r -- known: %s' % (k, ', '.join(VECTOR_ORDER))
        if val not in VECTOR_FIELDS[k]:
            return None, '%s=%r not in %s' % (k, val, VECTOR_FIELDS[k])
        seen[k] = val
    missing = [k for k in VECTOR_ORDER if k not in seen]
    if missing:
        return None, 'vector missing field(s): %s' % ', '.join(missing)
    return seen, None


SAME_EVENT_MAX_GAP_S = 2


def _prev_rotation_entry(prior):
    """The last entry that actually represents a rotation decision.

    target == 'self' is excluded on purpose: an entry about this role's own
    tooling or process is not a pick from the rotation, and counting it would
    let the rule be satisfied by writing about myself between two checks of
    the same agent -- which is a loophole, not a rotation.
    """
    for e in reversed(prior):
        if e.get('type') in ('check', 'finding') and e.get('target') != 'self':
            return e
    return None


def rotation_gate(prior, etype, target, same_target_reason):
    """INTERLOCK, not a detector -- refuse to record a rotation repeat unless
    it is declared. Returns an error string to refuse on, or None to allow.

    WHY THIS IS A GATE AND NOT A WARNING. The rule "never check the same agent
    twice in a row" existed only as prose in SKILL.md for this role's entire
    history, and hover_self_health.py could only ever report violations AFTER
    they were already in the append-only log, where nothing can remove them.
    Measured 2026-09-16: 20 real adjacent repeats, and the rate had risen from
    11.6% of transitions in the first half of the log to 34.1% in the second
    -- a 2.9x drift that a detector faithfully reported for two days and never
    once prevented. This is Toyota's Jidoka distinction stated in code: an
    Andon that notices a skipped step is weaker than an interlock that will
    not let the next step begin. Placed inside --add specifically because that
    is the one chokepoint every check and every finding must physically pass
    through (the FedEx/UPS in-line scanner principle from SKILL.md), rather
    than as a separate pass competing for attention with everything else.

    THE ESCAPE HATCH IS DELIBERATE AND IS THE POINT. 4 of the 17 real
    agent-repeats measured were structurally FORCED: this role's own FIA/TUV
    rule makes re-verification of a fix MANDATORY, so a gate with no override
    would put two of its own rules in direct conflict and the weaker one would
    quietly lose. --same-target-reason does not weaken the gate; it converts an
    invisible drift into a declared, stored, countable exception. A reason is
    written into the entry itself, so the ratio of declared repeats to total
    repeats is auditable later from the log alone -- and a session that starts
    declaring a reason every round is visible as exactly that.

    A same-event check->finding pair is allowed with no reason, because it is
    one review producing two log rows rather than two picks. Criteria match
    hover_self_health.py's _is_same_event() exactly: check->finding, gap <=
    SAME_EVENT_MAX_GAP_S. Kept deliberately identical so the gate and the
    measurement cannot disagree about what a repeat is.
    """
    if etype not in ('check', 'finding') or target == 'self':
        return None
    prev = _prev_rotation_entry(prior)
    if prev is None or prev.get('target') != target:
        return None

    if etype == 'finding' and prev.get('type') == 'check':
        try:
            prev_ts = datetime.strptime(prev['ts'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - prev_ts).total_seconds() <= SAME_EVENT_MAX_GAP_S:
                return None
        except (KeyError, ValueError):
            # FAIL CLOSED. An unparseable timestamp means the same-event
            # question COULD NOT BE ANSWERED -- which is a third state, never
            # folded into "allowed". Fall through to requiring a reason.
            pass

    if same_target_reason.strip():
        return None

    others = sorted({
        e.get('target') for e in prior
        if e.get('type') in ('check', 'finding') and e.get('target') not in (None, 'self', target)
    })
    return (
        'ROTATION GATE: REFUSED -- nothing was appended.\n'
        '  This would be %r twice in a row: seq %s already targeted %r, and no\n'
        '  different target has been checked since.\n'
        '  Eligible instead: %s\n'
        '  If this repeat is genuinely forced (re-verifying a fix to work just\n'
        '  flagged, or the only agent with fresh work in this window), declare it:\n'
        '    --same-target-reason "<why this specific repeat is unavoidable>"\n'
        '  The reason is stored in the entry and counted against the rotation\n'
        '  record. Declaring one every round is itself the drift this gate exists\n'
        '  to make visible.'
        % (target, prev.get('seq'), target, ', '.join(others) or '(no other target on record)')
    )


def cmd_add(argv):
    def opt(name, required=True, default=None):
        if name in argv:
            return argv[argv.index(name) + 1]
        if required:
            print('missing %s' % name)
            sys.exit(EXIT_COULD_NOT_RUN)
        return default

    etype = opt('--type')
    if etype not in TYPES:
        print('--type must be one of %s' % (TYPES,))
        return EXIT_COULD_NOT_RUN
    target = opt('--target')
    # ── --summary-file, ADDED 2026-09-15 ────────────────────────────────────
    # Two real content-loss incidents (entries 78, 102): a backtick pair
    # anywhere in a --summary string passed through bash is command
    # substitution, not a quote, and the shell silently drops whatever it
    # "ran" (usually nothing, sometimes an error) before this process ever
    # sees the argument. --summary still works for a short line with no
    # inline code; --summary-file reads the text from a file instead, which
    # never touches a shell command line as a literal to be word-split or
    # substituted -- write the file with a real editor tool, pass its path
    # here, and no quoting question exists to get wrong a third time.
    summary_file = opt('--summary-file', required=False, default=None)
    if summary_file:
        if '--summary' in argv:
            print('--summary and --summary-file are exclusive -- pick one')
            return EXIT_COULD_NOT_RUN
        try:
            with open(summary_file, encoding='utf-8') as f:
                summary = f.read().strip()
        except OSError as e:
            print('could not read --summary-file %r: %s' % (summary_file, e))
            return EXIT_COULD_NOT_RUN
        if not summary:
            print('--summary-file %r is empty' % summary_file)
            return EXIT_COULD_NOT_RUN
    else:
        summary = opt('--summary')
        # ── REFUSE RATHER THAN RISK IT A FIFTH TIME (2026-09-17) ────────────
        # The docstring above already named two incidents (78, 102) before
        # this session added three more (193, 196, 220) -- five real
        # instances of the identical defect, and the warning in this file's
        # own usage
        # block at the top was not enough to stop a fifth one happening in
        # the moment of typing a command quickly. A backtick in --summary is
        # never valid content that survived the shell; it is always either
        # already-stripped text (silent data loss already happened) or about
        # to be stripped (this call). Refusing outright, rather than logging
        # a plausible-looking but silently damaged entry, is the same
        # fail-closed standard this file already holds every other checker
        # on this platform to.
        if '`' in summary:
            print('--summary contains a backtick -- the shell has already '
                  'stripped or is about to strip whatever it thought was a '
                  'command substitution, and this file has lost real content '
                  'to exactly this five times already (entries 78, 102, 193, '
                  '196, 220). Refusing rather than logging a damaged entry. '
                  'Write the text to a file and pass --summary-file instead.')
            return EXIT_COULD_NOT_RUN
    severity = opt('--severity', required=False, default='')
    if severity not in SEVERITIES:
        print('--severity must be one of %s' % (SEVERITIES,))
        return EXIT_COULD_NOT_RUN
    ref = opt('--ref', required=False, default='')  # commit sha / file / claim id being audited
    retrospective = '--retrospective' in argv

    # ── STALENESS GUARD, READ-TIME CAPTURE ──────────────────────────────────
    # See the module-level comment above capture_read_time_shas() for the
    # full design. Captured HERE, near the top of cmd_add, deliberately as
    # close as this process can get to "when the caller is telling me about
    # what they read" -- the write-time re-check happens at the very end,
    # right before the file is opened, which is what actually matters.
    source_raw = opt('--source', required=False, default='')
    # Required for a PLATFORM finding (target != 'self') -- that is the exact
    # shape of the real incident (a finding about platform data, read against
    # a clone that had not pulled a fix). NOT required for target == 'self':
    # this role's own tooling (hover_log.py itself, hover_pure_js_exec.py,
    # ...) lives outside every platform repo and is built, run and reported
    # on in the same turn, so there is no separate earlier "read" moment
    # this guard could meaningfully check a git sha against -- requiring one
    # anyway would just make every self-tooling entry supply a value that
    # answers a question that does not apply to it.
    if etype == 'finding' and target != 'self' and not source_raw.strip():
        print('missing --source -- every PLATFORM finding (target != self) must '
              'stamp the git sha of the file(s) it was read against '
              '(--source path[:sha][,path...]). This is not optional; see the '
              'module docstring\'s staleness-guard section for why. (target == '
              '"self" findings about this role\'s own tooling are exempt -- see '
              'the comment here for the reason.)')
        return EXIT_COULD_NOT_RUN
    repo = discover_repo(argv)
    source_shas = {}
    if source_raw.strip():
        source_shas = capture_read_time_shas(repo, parse_source_arg(source_raw))
    vector_raw = opt('--vector', required=False, default='')
    vector = ''
    if vector_raw:
        if etype != 'finding':
            print('--vector only makes sense on --type finding')
            return EXIT_COULD_NOT_RUN
        parsed, err = parse_vector(vector_raw)
        if err:
            print('bad --vector %r: %s' % (vector_raw, err))
            return EXIT_COULD_NOT_RUN
        vector = '/'.join('%s:%s' % (k, parsed[k]) for k in VECTOR_ORDER)

    try:
        prior = read_all()
    except ValueError as e:
        print('COULD NOT RUN: %s -- refusing to append onto a log that does not '
              'parse, rather than silently starting a second chain.' % e)
        return EXIT_COULD_NOT_RUN

    same_target_reason = opt('--same-target-reason', required=False, default='') or ''
    gate_err = rotation_gate(prior, etype, target, same_target_reason)
    if gate_err:
        print(gate_err)
        return EXIT_COULD_NOT_RUN

    # ── EQA CADENCE FIELDS, ADDED 2026-09-16 ────────────────────────────────
    # Structured fields, not a "PROCESS PASS" keyword match over prose -- the
    # identical reason --same-target-reason exists as a field rather than a
    # text convention. process_pass marks an entry as a genuine cross-agent
    # process pass (SKILL.md's "Who checks the auditor" / EQA gap material).
    # eqa_checkpoint marks an entry as an INDEPENDENT external validation of
    # a prior self-audit -- performed by a reviewer with no hand in producing
    # the self-audit under review, never by this role re-grading itself.
    is_process_pass = '--process-pass' in argv
    is_eqa_checkpoint = '--eqa-checkpoint' in argv
    if is_process_pass and is_eqa_checkpoint:
        print('--process-pass and --eqa-checkpoint are exclusive -- an entry is one or the other')
        return EXIT_COULD_NOT_RUN

    # ── UNDIRECTED-SWEEP FIELD, ADDED 2026-09-17 ────────────────────────────
    # Same reason as process_pass/eqa_checkpoint: a structured field, not a
    # prose keyword a future reader has to trust was worded consistently.
    # Marks an entry as a genuinely undirected pass -- no target and no seed
    # chosen in advance (SKILL.md's Von Arx/wiki-discovery item, round 3) --
    # distinct from a risk-weighted targeted pick, even a randomly-selected
    # one. undirected_sweep_freshness.py reads this field, never the prose.
    is_undirected_sweep = '--undirected-sweep' in argv

    # ── ROUTABLE FIELD, ADDED 2026-09-29 ─────────────────────────────────────
    # Same reason as process_pass/undirected_sweep: a structured field, not
    # the prose word ROUTABLE a future reader (or a checker) has to trust was
    # spelled consistently. Built on direct instruction after a real routing
    # failure: three findings (leg_petcases, leg_processions, msb_sale_hours)
    # sat in this log for anywhere from one day to six days without reaching
    # docs/SAIRN-OPEN-WORK-INDEX.md, because the only live path was a human
    # reading chat and pasting by hand, and nothing checked the two sides
    # against each other. --routable <name>[,<name>...] names the resource(s)
    # this entry is ready to hand to a build agent / register owner for, so a
    # future report-only checker (scoped, not yet built -- see log seq 675)
    # can compare this field against the open-work index by exact name
    # rather than parsing prose. NAMES ONLY, no existence check against the
    # register here -- this tool does not require network/repo access to log
    # an entry, and a checker with repo access is the right place to catch a
    # typo'd resource name, not this write path.
    routable_raw = opt('--routable', required=False, default='')
    routable = None
    if routable_raw.strip():
        names = [n.strip() for n in routable_raw.split(',')]
        bad = [n for n in names if not n or not re.match(r'^[a-z][a-z0-9_]*$', n)]
        if bad:
            print('bad --routable %r -- each name must be a non-empty lowercase '
                  'identifier (letters, digits, underscore, starting with a '
                  'letter); got: %s. Nothing was appended.'
                  % (routable_raw, ', '.join(repr(b) for b in bad)))
            return EXIT_COULD_NOT_RUN
        routable = names

    # ── CONTRADICTS FIELD, ADDED 2026-09-28 ─────────────────────────────────
    # Same reason as the three fields above: a structured pointer, not prose
    # a future reader has to trust was worded consistently ("this contradicts
    # #553" buried in a paragraph is not queryable). Marks that THIS entry's
    # verdict on a resource directly CONTRADICTS an earlier entry's verdict on
    # the SAME resource -- a later read found something wrong that an earlier
    # read called clean, not merely an UPDATE (new information added to a
    # still-correct earlier call) or a DRIFT note (the world moved after a
    # correct-at-the-time read). Built on direct instruction: a contradiction
    # of this role's own prior clean verdict is a higher-salience event than
    # an ordinary re-check and must be findable as one, not folded into "the
    # verdict changed" the way an ordinary supersede would read.
    contradicts_raw = opt('--contradicts', required=False, default='')
    contradicts = None
    if contradicts_raw.strip():
        try:
            contradicts = int(contradicts_raw.strip())
        except ValueError:
            print('bad --contradicts %r -- must be an integer seq number, '
                  'not a hash or a description. Nothing was appended.' % contradicts_raw)
            return EXIT_COULD_NOT_RUN
        real_seqs = {e['seq'] for e in prior}
        if contradicts not in real_seqs:
            print('REFUSED: --contradicts %d does not exist in this log. A '
                  'pointer to a seq that is not real is worse than no pointer '
                  '-- it would look like a genuine contradiction forever in an '
                  'append-only log. Nothing was appended.' % contradicts)
            return EXIT_COULD_NOT_RUN
        if etype != 'finding':
            print('REFUSED: --contradicts is only for type=finding -- a '
                  'contradiction of a prior CLEAN verdict is itself a finding '
                  'by definition, not a check. Nothing was appended.')
            return EXIT_COULD_NOT_RUN

    # ── CONTRADICTS_EXTERNAL FIELD, ADDED 2026-09-28 ────────────────────────
    # Same purpose as --contradicts, scoped to the OTHER hover instance:
    # this entry overturns a CLEAN verdict recorded in H2's log (or vice
    # versa), not this log's own. Kept as a SEPARATE field on purpose --
    # mixing a bare same-log int and a cross-instance pointer into one field
    # would force every future reader to branch on shape to know which
    # question is being answered. THREE HONEST TIERS, never a false binary:
    # format-invalid refuses outright; the other log being UNREADABLE is
    # COULD-NOT-VERIFY (fail-open on ambiguity, the entry still logs, exactly
    # --source's own staleness-guard posture); the other log being readable
    # AND the seq genuinely absent is a hard REFUSE (a confirmed-wrong
    # pointer is worse than an unverifiable one). This function reads DATA
    # ONLY from the other instance's log (read_external_seqs, a plain
    # JSON-lines parse) -- it never imports, opens, or executes any .py file
    # under the other instance's directory, and it never adjudicates whether
    # the contradiction is SUBSTANTIVELY correct, only that the pointer is
    # real -- the same narrow scope tool_provenance_check.py already holds
    # for its own citations.
    contradicts_external_raw = opt('--contradicts-external', required=False, default='')
    contradicts_external = None
    contradicts_external_verified = None
    if contradicts_external_raw.strip():
        raw = contradicts_external_raw.strip()
        if ':' not in raw:
            print("bad --contradicts-external %r -- expected 'instance:seq', "
                  "e.g. 'hover2:523'. Nothing was appended." % raw)
            return EXIT_COULD_NOT_RUN
        inst, _, seq_part = raw.partition(':')
        if inst not in KNOWN_INSTANCE_LOGS:
            print('REFUSED: --contradicts-external names unknown instance %r '
                  '-- known instances: %s. Nothing was appended.'
                  % (inst, ', '.join(sorted(KNOWN_INSTANCE_LOGS))))
            return EXIT_COULD_NOT_RUN
        me = _current_instance_name()
        if inst == me:
            print('REFUSED: --contradicts-external names THIS instance (%r) '
                  '-- use --contradicts for a same-log contradiction instead. '
                  'Nothing was appended.' % inst)
            return EXIT_COULD_NOT_RUN
        try:
            ext_seq = int(seq_part)
        except ValueError:
            print('bad --contradicts-external %r -- the seq half must be an '
                  'integer. Nothing was appended.' % raw)
            return EXIT_COULD_NOT_RUN
        if etype != 'finding':
            print('REFUSED: --contradicts-external is only for type=finding '
                  '-- same reason as --contradicts. Nothing was appended.')
            return EXIT_COULD_NOT_RUN
        ext_seqs, ext_err = read_external_seqs(KNOWN_INSTANCE_LOGS[inst])
        if ext_err is not None:
            print('COULD NOT VERIFY --contradicts-external %s -- %s. Logging '
                  'anyway (fail-open on ambiguity, never on a confirmed '
                  'mismatch), but this is NOT the same as confirmed real.'
                  % (raw, ext_err))
            contradicts_external = {'instance': inst, 'seq': ext_seq}
            contradicts_external_verified = False
        elif ext_seq not in ext_seqs:
            print('REFUSED: --contradicts-external %s -- seq %d does not '
                  'exist in %s\'s log. A pointer to a seq that is not real '
                  'is worse than no pointer. Nothing was appended.'
                  % (raw, ext_seq, inst))
            return EXIT_COULD_NOT_RUN
        else:
            contradicts_external = {'instance': inst, 'seq': ext_seq}
            contradicts_external_verified = True

    # ── STALENESS GUARD, WRITE-TIME CHECK -- THE LAST THING BEFORE THE WRITE
    # Everything above (rotation gate, summary/vector validation, --same-
    # target-reason) has already run. This is deliberately the final gate,
    # immediately before the log is opened for writing -- re-deriving each
    # source path's CURRENT origin/main sha right now, not trusting the
    # capture from minutes (or longer) ago at the top of this function.
    staleness_verdict, stale_paths, unresolved_paths = ({}, [], [])
    if source_shas:
        staleness_verdict, stale_paths, unresolved_paths = \
            verify_freshness_at_write_time(repo, source_shas)
    if stale_paths:
        lines = ['STALE -- REREAD REQUIRED. Nothing was appended.', '']
        for p in stale_paths:
            lines.append('  %s: %s' % (p, staleness_verdict[p]['detail']))
        lines += [
            '',
            'One or more --source paths have changed on origin/main since this '
            'role read them. The finding this would have logged may already be '
            'wrong, exactly the shape that put a pre-fix row into the log once '
            'before. Re-read the current file(s), re-derive the finding against '
            'what is actually there now, and re-run --add.',
        ]
        print('\n'.join(lines))
        return EXIT_COULD_NOT_RUN
    if unresolved_paths:
        print('STALENESS CHECK COULD NOT VERIFY %d path(s) -- logging anyway '
              '(fail-open on ambiguity, never on a confirmed mismatch), but '
              'this is NOT the same as confirmed fresh:' % len(unresolved_paths))
        for p in unresolved_paths:
            print('  %s: %s' % (p, staleness_verdict[p]['detail']))

    prev_hash = prior[-1]['hash'] if prior else GENESIS
    seq = (prior[-1]['seq'] + 1) if prior else 1
    entry = {
        'same_target_reason': same_target_reason,
        'process_pass': is_process_pass,
        'eqa_checkpoint': is_eqa_checkpoint,
        'undirected_sweep': is_undirected_sweep,
        'routable': routable,
        'contradicts': contradicts,
        'contradicts_external': contradicts_external,
        'contradicts_external_verified': contradicts_external_verified,
        'seq': seq,
        'ts': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'type': etype,
        'target': target,
        'summary': summary,
        'severity': severity,
        'ref': ref,
        'vector': vector,
        'retrospective': retrospective,
        'prev_hash': prev_hash,
        'source_shas': {p: {'sha': i['sha'], 'source': i['source']}
                         for p, i in source_shas.items()},
        'staleness_check': {p: v['status'] for p, v in staleness_verdict.items()},
    }
    entry['hash'] = digest_of(prev_hash, entry)

    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, sort_keys=True) + '\n')

    print('logged #%d (%s, %s) hash=%s' % (seq, etype, target, entry['hash'][:12]))
    return EXIT_FINDING_OR_BROKEN if etype == 'finding' else EXIT_CLEAN


def run_staleness_fixtures():
    """Reproduces the real leg_aftercare scenario -- a local clone that read
    a file BEFORE a fix landed on origin/main, and confirms the write-time
    guard refuses rather than silently logging the pre-fix conclusion.
    Never touches the real hover-audit-log.jsonl -- LOG_PATH is monkey-
    patched to a scratch file for the duration and restored in a finally."""
    import io
    import contextlib
    import tempfile
    global LOG_PATH

    ok_count = [0]
    fail_count = [0]

    def ck(name, cond):
        if cond:
            ok_count[0] += 1
            print('  ok   ' + name)
        else:
            fail_count[0] += 1
            print('  FAIL ' + name)

    real_log_path = LOG_PATH
    tmpdir = tempfile.mkdtemp(prefix='hover_log_staleness_selftest_')

    # --- unit-level: parse_source_arg() ---
    ck('bare path with no sha parses to (path, None)',
       parse_source_arg('a.txt') == [('a.txt', None)])
    ck('path:sha parses the explicit override',
       parse_source_arg('a.txt:deadbeef') == [('a.txt', 'deadbeef')])
    ck('multiple comma-separated sources parse independently',
       parse_source_arg('a.txt,b.txt:cafe') == [('a.txt', None), ('b.txt', 'cafe')])
    ck('a trailing comma does not produce a phantom empty entry',
       parse_source_arg('a.txt,') == [('a.txt', None)])

    # --- real git fixture: bare origin + a work_repo standing in for this
    # role's own local clone, exactly the shape every other tool in this
    # directory already uses. ---
    bare_repo = os.path.join(tmpdir, 'origin.git')
    work_repo = os.path.join(tmpdir, 'work')
    subprocess.run(['git', 'init', '-q', '--bare', bare_repo], check=True)
    subprocess.run(['git', 'init', '-q', work_repo], check=True)
    subprocess.run(['git', 'config', 'user.email', 'x@x.com'], cwd=work_repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 'x'], cwd=work_repo, check=True)
    subprocess.run(['git', 'checkout', '-q', '-b', 'main'], cwd=work_repo, check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', bare_repo], cwd=work_repo, check=True)
    target_path = 'leg_aftercare_fixture.md'
    with open(os.path.join(work_repo, target_path), 'w', encoding='utf-8') as f:
        f.write('v1 -- the row this role is about to cite\n')
    subprocess.run(['git', 'add', '.'], cwd=work_repo, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'v1'], cwd=work_repo, check=True)
    subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=work_repo, check=True)

    # --- capture: local HEAD sha, matching origin/main at this instant ---
    sha_v1, cap_err = local_head_sha(work_repo, target_path)
    ck('read-time capture succeeds against a real local clone', sha_v1 and not cap_err)

    # ── THE ACTUAL INCIDENT, REPRODUCED ──────────────────────────────────
    # A SECOND session (hank) pushes a fix to origin -- from a SEPARATE
    # clone, so work_repo's own local HEAD is untouched, exactly the real
    # shape: hover2's clone had not pulled hank's fix, not merely "a
    # variable changed under it".
    hank_repo = os.path.join(tmpdir, 'hank_clone')
    subprocess.run(['git', 'clone', '-q', bare_repo, hank_repo], check=True)
    # The bare repo's own HEAD symref was never pointed at 'main' (created
    # empty, before the first push) -- point the clone at it explicitly, the
    # same fixture quirk every other tool in this directory's own selftest
    # already works around; a real GitHub-backed clone would not need this.
    subprocess.run(['git', 'checkout', '-q', '-b', 'main', 'origin/main'],
                    cwd=hank_repo, check=True)
    with open(os.path.join(hank_repo, target_path), 'w', encoding='utf-8') as f:
        f.write('v2 -- hank already fixed this row\n')
    subprocess.run(['git', 'add', '.'], cwd=hank_repo, check=True)
    subprocess.run(['git', 'config', 'user.email', 'h@h.com'], cwd=hank_repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 'hank'], cwd=hank_repo, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'v2 fix'], cwd=hank_repo, check=True)
    subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=hank_repo, check=True)

    ck('work_repo\'s own local HEAD is still v1 -- the real precondition, '
       'not assumed', open(os.path.join(work_repo, target_path), encoding='utf-8')
       .read().startswith('v1'))

    try:
        LOG_PATH = os.path.join(tmpdir, 'test-log.jsonl')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_add(['--add', '--type', 'finding', '--target', 'hank',
                          '--summary', 'fixture finding citing a now-stale row',
                          '--source', target_path, '--repo', work_repo])
        out = buf.getvalue()
        ck('STALE: the write-time check catches the real incident shape and '
           'refuses (nonzero rc)', rc == EXIT_COULD_NOT_RUN)
        ck('STALE: the refusal message names it plainly', 'STALE' in out
           and 'REREAD REQUIRED' in out)
        ck('STALE: nothing was appended to the log',
           not os.path.isfile(LOG_PATH) or read_all() == [])

        # --- now advance work_repo's own local HEAD to match (a real
        # `git pull`), and confirm the SAME finding logs cleanly this time,
        # with staleness_check='fresh' stamped into the persisted entry ---
        subprocess.run(['git', 'pull', '-q', 'origin', 'main'], cwd=work_repo, check=True)
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = cmd_add(['--add', '--type', 'finding', '--target', 'hank',
                           '--summary', 'fixture finding, now re-read fresh',
                           '--source', target_path, '--repo', work_repo])
        ck('FRESH: after a real pull, the identical --source now logs cleanly',
           rc2 == EXIT_FINDING_OR_BROKEN)
        rows = read_all()
        ck('FRESH: exactly one entry landed', len(rows) == 1)
        ck('FRESH: the persisted entry stamps staleness_check=fresh',
           rows and rows[0].get('staleness_check', {}).get(target_path) == 'fresh')
        ck('FRESH: the persisted entry stamps the real read-time sha, not a '
           'placeholder', rows and rows[0]['source_shas'][target_path]['sha'])

        # --- explicit path:sha override form, unit-level (no CLI round-trip
        # needed -- already proven end-to-end above) ---
        captured = capture_read_time_shas(work_repo, [(target_path, 'deadbeefcafe')])
        ck('explicit path:sha override is used verbatim, local HEAD not consulted',
           captured[target_path]['sha'] == 'deadbeefcafe'
           and captured[target_path]['source'] == 'explicit')

        # --- fail-OPEN on genuine infrastructure noise: a real unreachable
        # origin (chaos-injection, same technique used earlier tonight for
        # hover_coverage_ledger.py/hover_pure_js_exec.py), not simulated ---
        broken_repo = os.path.join(tmpdir, 'broken_clone')
        subprocess.run(['git', 'init', '-q', broken_repo], check=True)
        subprocess.run(['git', 'config', 'user.email', 'x@x.com'], cwd=broken_repo, check=True)
        subprocess.run(['git', 'config', 'user.name', 'x'], cwd=broken_repo, check=True)
        subprocess.run(['git', 'checkout', '-q', '-b', 'main'], cwd=broken_repo, check=True)
        subprocess.run(['git', 'remote', 'add', 'origin',
                        'https://127.0.0.1:1/nonexistent-unreachable.git'],
                        cwd=broken_repo, check=True)
        with open(os.path.join(broken_repo, target_path), 'w', encoding='utf-8') as f:
            f.write('content only this broken clone has ever seen\n')
        subprocess.run(['git', 'add', '.'], cwd=broken_repo, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'v1'], cwd=broken_repo, check=True)

        LOG_PATH = os.path.join(tmpdir, 'test-log-2.jsonl')
        buf3 = io.StringIO()
        with contextlib.redirect_stdout(buf3):
            rc3 = cmd_add(['--add', '--type', 'finding', '--target', 'hank',
                           '--summary', 'fixture finding against an unreachable origin',
                           '--source', target_path, '--repo', broken_repo])
        out3 = buf3.getvalue()
        ck('COULD-NOT-VERIFY: a real unreachable origin does NOT block the '
           'write (fail-open on ambiguity)', rc3 == EXIT_FINDING_OR_BROKEN)
        ck('COULD-NOT-VERIFY: the ambiguity is printed, not silent',
           'COULD NOT VERIFY' in out3)
        rows2 = read_all()
        ck('COULD-NOT-VERIFY: the entry still landed',
           rows2 and rows2[0].get('type') == 'finding')
        ck('COULD-NOT-VERIFY: the persisted entry HONESTLY stamps '
           'could_not_verify, never silently "fresh"',
           rows2 and rows2[0].get('staleness_check', {}).get(target_path)
           == 'could_not_verify')

        # --- a finding with NO --source at all is refused outright ---
        LOG_PATH = os.path.join(tmpdir, 'test-log-3.jsonl')
        buf4 = io.StringIO()
        with contextlib.redirect_stdout(buf4):
            rc4 = cmd_add(['--add', '--type', 'finding', '--target', 'hank',
                           '--summary', 'a finding with no --source at all'])
        ck('a finding with NO --source is refused before anything runs',
           rc4 == EXIT_COULD_NOT_RUN and 'missing --source' in buf4.getvalue())

        # --- backward compatibility: a --type check needs no --source ---
        LOG_PATH = os.path.join(tmpdir, 'test-log-4.jsonl')
        buf5 = io.StringIO()
        with contextlib.redirect_stdout(buf5):
            rc5 = cmd_add(['--add', '--type', 'check', '--target', 'hank',
                           '--summary', 'a plain check, no --source required'])
        ck('a --type check with no --source still logs (unchanged behaviour '
           'for every entry made before this guard existed)', rc5 == EXIT_CLEAN)

        # --- target='self' findings (this role's own tooling) are exempt --
        # no platform repo owns those files, so there is no sha to check ---
        LOG_PATH = os.path.join(tmpdir, 'test-log-5.jsonl')
        buf6 = io.StringIO()
        with contextlib.redirect_stdout(buf6):
            rc6 = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                           '--summary', 'a self-tooling finding, exempt from --source'])
        ck('a target=self finding with NO --source still logs (self-tooling '
           'is exempt from a guard that cannot apply to it)', rc6 == EXIT_FINDING_OR_BROKEN)

        # --- --contradicts: locked in both directions, 2026-09-28 ---
        LOG_PATH = os.path.join(tmpdir, 'test-log-6.jsonl')
        buf7 = io.StringIO()
        with contextlib.redirect_stdout(buf7):
            rc7a = cmd_add(['--add', '--type', 'check', '--target', 'self',
                            '--summary', 'an earlier clean verdict on some resource'])
        earlier_seq = read_all()[-1]['seq']
        buf8 = io.StringIO()
        with contextlib.redirect_stdout(buf8):
            rc7b = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                            '--summary', 'a later read contradicts the earlier clean call',
                            '--contradicts', str(earlier_seq)])
        ck('a valid --contradicts on a real prior seq, type=finding, logs clean',
           rc7b == EXIT_FINDING_OR_BROKEN)
        ck('the persisted entry carries the structured contradicts pointer, '
           'not just prose', read_all()[-1].get('contradicts') == earlier_seq)
        buf9 = io.StringIO()
        with contextlib.redirect_stdout(buf9):
            rc7c = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                            '--summary', 'contradicts a seq that does not exist',
                            '--contradicts', '999999'])
        ck('TEETH: --contradicts pointing at a NONEXISTENT seq is REFUSED, '
           'never silently accepted', rc7c == EXIT_COULD_NOT_RUN
           and 'does not exist' in buf9.getvalue())
        buf10 = io.StringIO()
        with contextlib.redirect_stdout(buf10):
            rc7d = cmd_add(['--add', '--type', 'check', '--target', 'self',
                            '--summary', 'a plain check cannot claim to contradict',
                            '--contradicts', str(earlier_seq)])
        ck('TEETH: --contradicts on type=check (not finding) is REFUSED -- a '
           'contradiction of a clean verdict IS a finding by definition',
           rc7d == EXIT_COULD_NOT_RUN and 'only for type=finding' in buf10.getvalue())
        buf11 = io.StringIO()
        with contextlib.redirect_stdout(buf11):
            rc7e = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                            '--summary', 'garbage contradicts value',
                            '--contradicts', 'not-a-number'])
        ck('TEETH: a non-integer --contradicts is REFUSED, not coerced',
           rc7e == EXIT_COULD_NOT_RUN)
        ck('an ORDINARY finding with no --contradicts stores contradicts=None, '
           'never a false 0 or missing key', 'contradicts' in rows2[0]
           and rows2[0]['contradicts'] is None)

        # --- --routable: locked in both directions, 2026-09-29. Built after
        # a REAL routing failure (three findings sat unrouted for up to six
        # days with nothing checking hover's log against the open-work index)
        # -- see log seq 675 for the scoped checker this field exists to feed.
        buf_r1 = io.StringIO()
        with contextlib.redirect_stdout(buf_r1):
            rc_r1 = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                             '--summary', 'a routable finding naming two resources',
                             '--routable', 'leg_petcases,msb_sale_hours'])
        ck('a valid multi-name --routable logs clean', rc_r1 == EXIT_FINDING_OR_BROKEN)
        ck('the persisted entry carries the STRUCTURED name list, not prose '
           '-- exactly the two names, in order, never re-sorted or deduped '
           'behind the caller\'s back',
           read_all()[-1].get('routable') == ['leg_petcases', 'msb_sale_hours'])

        buf_r2 = io.StringIO()
        with contextlib.redirect_stdout(buf_r2):
            rc_r2 = cmd_add(['--add', '--type', 'check', '--target', 'self',
                             '--summary', 'a plain check with no routable claim'])
        ck('an ORDINARY entry with no --routable stores routable=None, never '
           'an empty list or a missing key -- None and [] mean different '
           'things to a future checker (never claimed routable, vs. claimed '
           'and named nothing)', 'routable' in read_all()[-1]
           and read_all()[-1]['routable'] is None)

        # KNOWN-BAD CONTROL, MUST KEEP FAILING: a malformed name (uppercase,
        # a stray comma producing an empty token, a bare space) must be
        # REFUSED outright, never silently accepted or silently dropped --
        # a checker trusting this field to be clean identifiers must never
        # receive one that is not. Three shapes in one call, any one of
        # which must trip the refusal.
        for bad_raw, why in (
            ('Leg_Petcases', 'uppercase'),
            ('leg_petcases,,msb_sale_hours', 'empty token from a stray comma'),
            ('leg pets', 'a bare space, not an identifier'),
        ):
            buf_bad = io.StringIO()
            with contextlib.redirect_stdout(buf_bad):
                rc_bad = cmd_add(['--add', '--type', 'check', '--target', 'self',
                                  '--summary', 'malformed routable attempt',
                                  '--routable', bad_raw])
            ck('TEETH: --routable %r (%s) is REFUSED, not silently accepted '
               'or silently trimmed' % (bad_raw, why),
               rc_bad == EXIT_COULD_NOT_RUN and 'bad --routable' in buf_bad.getvalue())

        # --- --contradicts-external: locked in both directions, 2026-09-28.
        # KNOWN_INSTANCE_LOGS is swapped for scratch entries for the WHOLE
        # block -- this NEVER reads the real hover/hover2 logs, the same
        # discipline HOVER_LOG_PATH_OVERRIDE exists to enforce for LOG_PATH
        # itself (a real production write landed once, entry #464, because a
        # test trusted an in-process monkeypatch a subprocess never saw --
        # this block avoids that class differently, by never touching a real
        # path for either read OR write).
        real_known = dict(KNOWN_INSTANCE_LOGS)
        try:
            other_log = os.path.join(tmpdir, 'other_instance.jsonl')
            with io.open(other_log, 'w', encoding='utf-8') as f:
                f.write(json.dumps({'seq': 523, 'type': 'check'}) + '\n')
                f.write(json.dumps({'seq': 524, 'type': 'finding'}) + '\n')
            KNOWN_INSTANCE_LOGS.clear()
            KNOWN_INSTANCE_LOGS['test_self'] = LOG_PATH
            KNOWN_INSTANCE_LOGS['test_other'] = other_log
            KNOWN_INSTANCE_LOGS['test_unreadable'] = os.path.join(tmpdir, 'never_created.jsonl')

            buf12 = io.StringIO()
            with contextlib.redirect_stdout(buf12):
                rc8a = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                                '--summary', 'H1 contradicts the other instance seq 523',
                                '--contradicts-external', 'test_other:523'])
            ck('a valid --contradicts-external on a real, readable other-'
               'instance seq logs clean', rc8a == EXIT_FINDING_OR_BROKEN)
            persisted = read_all()[-1]
            ck('the persisted entry carries the structured cross-instance '
               'pointer, not just prose', persisted.get('contradicts_external')
               == {'instance': 'test_other', 'seq': 523})
            ck('...and is marked VERIFIED true, since the other log genuinely '
               'has that seq (read as DATA, not by importing anything)',
               persisted.get('contradicts_external_verified') is True)

            buf13 = io.StringIO()
            with contextlib.redirect_stdout(buf13):
                rc8b = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                                '--summary', 'points at a seq the other log does not have',
                                '--contradicts-external', 'test_other:999999'])
            ck('TEETH: pointing at a NONEXISTENT seq in a READABLE other log '
               'is REFUSED, never silently accepted',
               rc8b == EXIT_COULD_NOT_RUN and 'does not exist' in buf13.getvalue())

            buf14 = io.StringIO()
            with contextlib.redirect_stdout(buf14):
                rc8c = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                                '--summary', 'the other log cannot be read at all',
                                '--contradicts-external', 'test_unreadable:1'])
            ck('COULD-NOT-VERIFY: an UNREADABLE other-instance log does NOT '
               'block the write (fail-open on ambiguity, not on a confirmed '
               'mismatch)', rc8c == EXIT_FINDING_OR_BROKEN)
            ck('...the ambiguity is printed, not silent',
               'COULD NOT VERIFY' in buf14.getvalue())
            persisted3 = read_all()[-1]
            ck('...the persisted entry HONESTLY stamps verified=False, never '
               'silently True on an unreadable log',
               persisted3.get('contradicts_external_verified') is False)
            ck('...but the pointer itself is STILL stored -- a could-not-'
               'verify pointer is data for a human to chase, not nothing',
               persisted3.get('contradicts_external')
               == {'instance': 'test_unreadable', 'seq': 1})

            buf15 = io.StringIO()
            with contextlib.redirect_stdout(buf15):
                rc8d = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                                '--summary', 'unknown instance name',
                                '--contradicts-external', 'nonexistent_instance:1'])
            ck('TEETH: an UNKNOWN instance name is REFUSED outright, no file '
               'lookup even attempted',
               rc8d == EXIT_COULD_NOT_RUN and 'unknown instance' in buf15.getvalue())

            buf16 = io.StringIO()
            with contextlib.redirect_stdout(buf16):
                rc8e = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                                '--summary', 'malformed, no colon at all',
                                '--contradicts-external', 'test_other523'])
            ck('TEETH: a malformed instance:seq string with no colon is '
               'REFUSED', rc8e == EXIT_COULD_NOT_RUN)

            buf17 = io.StringIO()
            with contextlib.redirect_stdout(buf17):
                rc8f = cmd_add(['--add', '--type', 'check', '--target', 'self',
                                '--summary', 'a plain check cannot claim a cross-instance contradiction',
                                '--contradicts-external', 'test_other:523'])
            ck('TEETH: --contradicts-external on type=check is REFUSED, same '
               'reason as --contradicts', rc8f == EXIT_COULD_NOT_RUN)

            # THE FIXTURE THAT MUST FAIL BY DESIGN, per direct instruction:
            # 'test_self' resolves to THIS run's own current LOG_PATH, so
            # _current_instance_name() correctly identifies it as self.
            buf18 = io.StringIO()
            with contextlib.redirect_stdout(buf18):
                rc8g = cmd_add(['--add', '--type', 'finding', '--target', 'self',
                                '--summary', 'pointing at myself instead of using --contradicts',
                                '--contradicts-external', 'test_self:1'])
            ck('TEETH, THE FIXTURE THAT MUST FAIL: --contradicts-external '
               'naming THIS instance itself is REFUSED -- a same-log '
               'contradiction must use --contradicts, not this field',
               rc8g == EXIT_COULD_NOT_RUN and 'THIS instance' in buf18.getvalue())
        finally:
            KNOWN_INSTANCE_LOGS.clear()
            KNOWN_INSTANCE_LOGS.update(real_known)
    finally:
        LOG_PATH = real_log_path

    print()
    print('%d ok, %d failed' % (ok_count[0], fail_count[0]))
    return fail_count[0] == 0


def cmd_verify(argv):
    try:
        rows = read_all()
    except ValueError as e:
        print('COULD NOT VERIFY: %s' % e)
        return EXIT_COULD_NOT_RUN
    if not rows:
        print('EMPTY LOG -- nothing to verify. Not the same as a clean chain: '
              'a clean run over zero entries is a statement about nothing.')
        return EXIT_COULD_NOT_RUN

    prev = GENESIS
    for i, row in enumerate(rows):
        stored_hash = row.get('hash')
        without_hash = {k: v for k, v in row.items() if k != 'hash'}
        if row.get('prev_hash') != prev:
            print('CHAIN_BROKEN at seq %s: expected prev_hash %s, found %s'
                  % (row.get('seq'), prev[:16], str(row.get('prev_hash'))[:16]))
            return EXIT_FINDING_OR_BROKEN
        recomputed = digest_of(prev, without_hash)
        if recomputed != stored_hash:
            print('TAMPERED at seq %s: stored hash does not match recomputed digest. '
                  'Either this entry or something upstream of it was edited after '
                  'the fact.' % row.get('seq'))
            return EXIT_FINDING_OR_BROKEN
        prev = stored_hash
    print('VERIFIED -- %d entries, genesis to tip, chain intact.' % len(rows))
    return EXIT_CLEAN


def cmd_tail(argv):
    n = 20
    if '--tail' in argv:
        try:
            n = int(argv[argv.index('--tail') + 1])
        except Exception:
            pass
    try:
        rows = read_all()
    except ValueError as e:
        print('COULD NOT READ: %s' % e)
        return EXIT_COULD_NOT_RUN
    tail = rows[-n:]
    if '--json' in argv:
        print(json.dumps(tail, indent=1))
        return EXIT_CLEAN
    for r in tail:
        flag = '!' if r['type'] == 'finding' else ('.' if r['type'] == 'no-report' else ' ')
        vec = (' [%s]' % r['vector']) if r.get('vector') else ''
        contra = '  [[CONTRADICTS #%s]]' % r['contradicts'] if r.get('contradicts') else ''
        print('%4d %s %-10s %-28s%s %s%s%s' % (
            r['seq'], flag, r['type'], r['target'][:28], vec, r['summary'][:100],
            '  [retro]' if r.get('retrospective') else '', contra))
    return EXIT_CLEAN


def main(argv):
    if '--selftest' in argv:
        ok = run_staleness_fixtures()
        return EXIT_CLEAN if ok else EXIT_FINDING_OR_BROKEN
    if '--add' in argv:
        return cmd_add(argv)
    if '--verify' in argv:
        return cmd_verify(argv)
    if '--tail' in argv or argv == []:
        return cmd_tail(argv)
    print('unknown invocation. Use --add / --verify / --tail / --selftest.')
    return EXIT_COULD_NOT_RUN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
