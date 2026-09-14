"""Can this write path be retried, and does it check a key against DURABLE storage?

    python tools/idempotency_check.py
    python tools/idempotency_check.py --fixtures    # the blind lock alone
    python tools/idempotency_check.py --json

── THE DEFECT SHAPE, FROM THIS PLATFORM'S OWN RECORD ─────────────────────
A write that can be retried and does not check a key processes the same
business event twice. The dangerous variant is not the missing key -- it is a
key checked against an IN-MEMORY map: it looks like idempotence, passes review,
and fails the moment there are two processes, or one process restarted. That is
the shape of this session's suite-lock race, where a second run snapshotted a
first run's in-flight mutation as its baseline because the guard lived in
memory rather than on disk.

── THE BLIND LOCK ────────────────────────────────────────────────────────
Pass/fail is decided against SYNTHETIC fixtures below and this tool REFUSES TO
JUDGE A SINGLE REAL FILE until they all classify as written. Criteria tuned
against the real corpus would pass by construction.

THE POSITIVE FIXTURE IS REAL, NOT SYNTHETIC, on Michael's instruction:
`api/ledger.js` is idempotent on the business event (source_kind + source_id),
checked against durable storage BEFORE writing anything, and it REFUSES rather
than posting unchecked when the check itself fails. Using the real thing means
the criteria are calibrated against an implementation somebody defended, not
against a sample written to be recognised.

THE NEGATIVE FIXTURE STAYS SYNTHETIC, and that is disclosed rather than
implied: there is no in-memory-keyed write path on this platform to point at.
The fixture is a constructed example, so this checker has never been shown to
catch a REAL instance of the shape it most wants to catch.

── WHAT IT CANNOT SEE, said here rather than discovered later ───────────
  * whether a retry actually happens. It reads the code, not the traffic;
  * a key checked in a database CONSTRAINT rather than in the handler -- a
    unique index is durable idempotence and this would report the handler as
    unguarded. Counted separately as UNIQUE-CONSTRAINT-MAYBE, never as a
    finding;
  * writes outside api/. The client push helpers retry and are not read here.

Exit 0 when every retryable write is guarded or declared, 1 when one is not,
2 when the fixtures fail -- which means nothing real was judged.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRITERIA_VERSION = '2026-09-13.1'

# A caller-supplied key the handler reads. Names seen in real handlers here.
# ── THE VOCABULARY IS HAND-WRITTEN, AND ON 2026-09-14 IT WAS WRONG ─────────
# `submission_key` was added after this checker called
# api/sairndental/public-complaint-submit.js UNGUARDED. That file has a full,
# deliberate, durable guard built the same week: a sha256 over
# license_hash + NUL + name + NUL + message, a PostgREST read on
# `submission_key=eq.<hash>` inside a ten-minute window, and it returns the
# ORIGINAL complaint's answer on a duplicate rather than an error. It even has
# its own migration, sql/sairndental_complaint_idempotency_2026-09-13.sql. The
# guard was invisible for one reason: it is not named any of the seven things
# this list knew about.
#
# THE SHAPE OF THE MISTAKE IS WORTH MORE THAN THE MISSING WORD. This list was
# written from what an idempotency key is usually CALLED, not from what this
# platform actually names them -- and measured on 2026-09-14, THREE of the
# original seven (`idempotency_key`, `client_token`, `external_id`) match ZERO
# files and never have, while the one real guard on the platform used an eighth
# name. An aspirational vocabulary reads exactly like a complete one.
#
# IT IS STILL A LIST, DELIBERATELY. The derived alternative was tried and
# REJECTED, and is recorded here so it is not rebuilt: "a non-scope column that
# is both filtered on with =eq. and written in a body" matches 37 files,
# including sixteen whose column is `active` -- a deactivation flag -- and
# others keyed on ordinary record ids. It would have flipped dozens of files to
# GUARDED, and a checker that says "guarded" where nothing guards is the
# fail-open direction and far worse than the false negative it fixes.
#
# What IS derived is the disclosure: the run prints how many files each term
# matched, so a term that has never matched and a key this list does not know
# are both visible rather than silent.
KEY_NAMES = (r'(source_id|source_kind|idempotency[_-]?key(?:_hash)?|request_id|'
             r'client_token|order_id|external_id|submission_key)')
KEY_TERMS = ['source_id', 'source_kind', 'idempotency_key',
             # Added 2026-09-14 BY THE CANDIDATE REPORTER, on its first day:
             # api/sairncash/trial-start.js stores a sha256 of its key, so the
             # column is idempotency_key_HASH and the vocabulary did not have
             # it. The reporter surfaced it as UNCLASSIFIED within minutes of
             # the column being written -- which is exactly the gap that let
             # submission_key sit unnoticed for a day.
             'idempotency_key_hash', 'request_id',
             'client_token', 'order_id', 'external_id', 'submission_key']

# --- DERIVING THE VOCABULARY: THREE ATTEMPTS, ALL MEASURED, ALL WORSE ------
# Asked on 2026-09-14 to derive this list from real usage rather than maintain
# it by hand. Three derivations were built and MEASURED against two known true
# positives -- api/ledger.js (source_id/source_kind) and
# api/sairndental/public-complaint-submit.js (submission_key):
#
#   A. "a non-scope column both filtered with =eq. AND written in a body"
#      -> 37 files, SIXTEEN of them keyed on `active`, a deactivation flag.
#      Would have flipped dozens of files to GUARDED. Fail-open.
#   B. "a read whose result short-circuits a later write" -- the actual
#      semantic -- approximated by regex -> 24 files, admits `license_hash`
#      (which is in every query on this platform), AND MISSES
#      public-complaint-submit.js, whose early return is nested two `if` levels
#      deep. Wrong in both directions at once.
#   C. "a column the SCHEMA declares UNIQUE and api/ filters on"
#      -> 50 columns, because every record id is unique in its own table. Also
#      misses submission_key, which deliberately carries an INDEX and not a
#      UNIQUE constraint -- its own migration says why: a unique constraint
#      "would refuse that second, legitimate complaint forever".
#
# B is the right semantic and it needs an AST. There is no JS parser here:
# nothing in node_modules, and this repo's package.json records that it carries
# three dependencies on purpose, one added only because hand-rolling WebAuthn
# crypto was the wrong call. Adding a parser to power a checker is not that.
#
# SO THE CLASSIFICATION STAYS HAND-WRITTEN AND THE CANDIDATES ARE DERIVED --
# which is the half that actually failed. submission_key sat in the tree for a
# day and nothing pointed at it. A candidate reporter would have, the day it was
# written. It never classifies anything: it produces a lead a human judges, the
# same shape secrets_inventory.py already uses for a newly-introduced env var.
KEY_SHAPE = re.compile(r'(_key$|_token$|_hash$|idempot|dedup|submission|nonce)')
# The scoping columns every query on this platform carries. Not a second
# vocabulary -- they are excluded because they appear EVERYWHERE, which is the
# opposite of the property a key needs.
SCOPE_COLS = ('license_hash', 'app_id')
FILTER_COL = re.compile(r'[?&]([a-z][a-z0-9_]{2,40})=eq\.')
MUTATING = re.compile(r"method:\s*'(?:POST|PATCH|PUT)'")

# Hand-written judgments on the DERIVED candidates. A candidate with no entry
# here is reported UNCLASSIFIED on every run, because a guard built on a name
# this vocabulary does not know reads as UNGUARDED -- which is what happened.
KEY_CANDIDATES_JUDGED = {
    'token_hash': 'NOT an idempotency key. A hashed bearer credential looked '
                  'up to authenticate a caller; the write that follows is the '
                  'point of the request, not a duplicate of it',
    'access_token': 'NOT an idempotency key. Same shape as token_hash -- it '
                    'says WHO is asking, not WHICH submission this is',
    'link_token': 'NOT an idempotency key. A share/track link identifier',
    'ip_hash': 'NOT an idempotency key. A rate-limit bucket, keyed with '
               'window_start; suppressing duplicates is not its job',
    'setting_key': 'NOT an idempotency key. A settings column name',
    'trial_token': 'NOT an idempotency key, and the trial-start finding is why '
                   'it is worth saying: the token is the RESULT of the write, '
                   'minted per request, so it cannot key the write that '
                   'produces it. See tools/idempotency_triage.json',
}


def derive_key_candidates(repo):
    """Columns filtered with =eq. inside a file that WRITES, whose name is
    key-shaped, and which the vocabulary does not already know.

    DERIVED FROM api/ ON EVERY RUN, so a new key cannot sit in the tree
    unnamed. It reports; it never classifies.
    """
    out = {}
    for root, _dirs, files in os.walk(os.path.join(repo, 'api')):
        for f in files:
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            p = os.path.join(root, f)
            try:
                code = io.open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            if not MUTATING.search(code):
                continue
            rel = os.path.relpath(p, repo).replace(os.sep, '/')
            for col in set(FILTER_COL.findall(code)):
                if col in KEY_TERMS or col in SCOPE_COLS:
                    continue
                if KEY_SHAPE.search(col):
                    out.setdefault(col, []).append(rel)
    return dict((k, sorted(v)) for k, v in out.items())
# Evidence the key is checked against something that OUTLIVES the process.
DURABLE = r'(fetch\(\s*rest\(|await\s+\w*[Ff]etch|select=|\.from\(|SELECT\s)'
# Evidence it is checked against something that does NOT outlive the process.
# NARROWED after the lock caught the first version: it matched any `new Set(`,
# and api/ledger.js -- the REAL positive fixture -- has one at line 312 to
# dedupe ids in a RESPONSE. That read a defended, correct implementation as the
# dangerous shape. A criteria correction against a real implementation, declared
# here rather than made quietly.
#
# The shape that actually bites is a key store at MODULE SCOPE (it outlives the
# request, which is exactly why it looks like it works) that is then CONSULTED
# with a key. Both halves are required.
IN_MEMORY_STORE = re.compile(
    r'^(?:const|let|var)\s+(\w+)\s*=\s*(?:new\s+(?:Map|Set)\(|\{\s*\})', re.M)


def analyse(rel, src):
    code = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))
    writes = len(re.findall(r"method:\s*'(?:POST|PATCH|PUT)'", code))
    if not writes:
        return None
    reads_key = bool(re.search(KEY_NAMES, code))
    durable = bool(re.search(DURABLE, code))
    in_mem = False
    for m in IN_MEMORY_STORE.finditer(code):
        name = m.group(1)
        # ... and consulted with a caller key. A module-level Map that nothing
        # looks a key up in is a cache, not a false idempotence guard.
        # THE KEY MUST BE IN THE LOOKUP ITSELF, not merely somewhere in the
        # file. Narrowed a THIRD time after the lock and a hand check caught
        # two false positives in a row: api/ledger.js's response-dedupe Set,
        # then api/sd-data.js's BOUNDARY_LOGGED, a LOG-dedupe store consulted
        # with `seenKey`. In a 10,000-line file some key name always appears
        # somewhere, so 'key present in file' is not evidence of anything.
        consulted = re.search(chr(92) + 'b' + re.escape(name) +
                              r'\s*\.\s*(?:has|get|includes)\s*\(\s*([^)]{0,80})\)', code)
        if consulted and re.search(KEY_NAMES, consulted.group(1)):
            in_mem = True
            break
    unique_idx = bool(re.search(r'on_conflict=|ON CONFLICT|unique\s*\(', code, re.I))

    # ── RETRYABILITY TRIAGE (2026-09-13) ──────────────────────────────────
    # AN UNGUARDED WRITE IS ONLY A FINDING IF SOMETHING CAN RETRY IT. Counting
    # all 41 as risk overstates it, and an overstated number is how a real
    # finding gets discounted. Each class below is mechanical; the ones that
    # matter are then read by hand and recorded in RETRY_NOTES.
    is_handler = bool(re.search(r'module\.exports\s*=\s*(?:async\s*)?\(?\s*(?:req|request)',
                                code))
    # A WRITE THAT ONLY EVER SETS A FIELD TO THE SAME VALUE IS IDEMPOTENT
    # WITHOUT A KEY, and calling it a finding is how a real finding gets
    # discounted. Measured, not assumed: the highest-risk row this tool first
    # produced was api/agent/stripe-webhook.js -- and its ONLY write is a PATCH
    # setting plan_status to a constant. A Stripe retry sets 'canceled' to
    # 'canceled'. Not a defect.
    #
    # The signal is PATCH-only with no INSERT: a PATCH addresses an existing
    # row by id, so replaying it converges. A POST creates a second row.
    patches = len(re.findall(r"method:\s*'PATCH'", code))
    posts = len(re.findall(r"method:\s*'(?:POST|PUT)'", code))
    if patches and not posts:
        retry = 'IDEMPOTENT-BY-SHAPE'
    elif re.search(r'stripe|webhook', rel, re.I) or re.search(r'constructEvent|webhook', code):
        retry = 'WEBHOOK'          # the sender retries BY DESIGN. Highest risk.
    elif not is_handler:
        # An internal helper inherits its caller's retryability; classifying it
        # separately would double-count the handler that calls it.
        retry = 'HELPER-INHERITS'
    elif re.search(r'public|unauthenticated', rel + ' ' + code[:2000], re.I):
        retry = 'PUBLIC-FORM'      # a double-click is a retry
    else:
        retry = 'AUTHED-ENDPOINT'  # a client timeout is a retry


    if reads_key and durable and not in_mem:
        verdict = 'GUARDED-DURABLE'
    elif reads_key and in_mem:
        verdict = 'GUARDED-IN-MEMORY'          # the dangerous one
    elif unique_idx:
        verdict = 'UNIQUE-CONSTRAINT-MAYBE'    # not a finding; not proof either
    else:
        verdict = 'UNGUARDED'
    return {'file': rel, 'writes': writes, 'verdict': verdict, 'retry': retry,
            'reads_key': reads_key, 'durable_check': durable,
            'in_memory_check': in_mem, 'upsert_or_unique': unique_idx}


# ── FIXTURES: hand-decided. The POSITIVE one is the real api/ledger.js.
SYNTHETIC = [
    ('in-memory key store is the DANGEROUS shape and must be named as such',
     "const seen = new Map();\nif (seen.has(payload.idempotency_key)) return;\n"
     "await fetch(rest('t'), { method: 'POST' });",
     'GUARDED-IN-MEMORY'),
    ('a retryable write with no key at all is UNGUARDED',
     "await fetch('https://x/y', { method: 'POST', body: b });",
     'UNGUARDED'),
    ('CONTROL: a file with no write at all is not judged',
     "const x = await fetch(rest('t?select=id'));", None),
]


def run_fixtures():
    bad = []
    for name, src, want in SYNTHETIC:
        got = analyse('fixture.js', src)
        got_v = got['verdict'] if got else None
        if got_v != want:
            bad.append((name, want, got_v))
    # The real positive: api/ledger.js must read as durably guarded.
    p = os.path.join(REPO, 'api', 'ledger.js')
    if not os.path.exists(p):
        bad.append(('api/ledger.js is missing -- the real positive fixture is gone',
                    'GUARDED-DURABLE', None))
    else:
        got = analyse('api/ledger.js', io.open(p, encoding='utf-8', errors='replace').read())
        if not got or got['verdict'] != 'GUARDED-DURABLE':
            bad.append(('the REAL positive fixture api/ledger.js must read as durably '
                        'guarded -- it checks source_kind+source_id before writing',
                        'GUARDED-DURABLE', got['verdict'] if got else None))
    # A SECOND REAL POSITIVE, ADDED 2026-09-14 BECAUSE THIS CHECKER GOT IT
    # WRONG. api/ledger.js alone could not catch the vocabulary being
    # incomplete: it uses two of the terms the list already knew. This one uses
    # `submission_key`, which the list did not, and it was read as UNGUARDED
    # for a day. Pinned here so the term cannot be dropped and the guard go
    # invisible again.
    q = os.path.join(REPO, 'api', 'sairndental', 'public-complaint-submit.js')
    if not os.path.exists(q):
        bad.append(('api/sairndental/public-complaint-submit.js is missing -- the '
                    'second real positive fixture is gone',
                    'GUARDED-DURABLE', None))
    else:
        got = analyse('api/sairndental/public-complaint-submit.js',
                      io.open(q, encoding='utf-8', errors='replace').read())
        if not got or got['verdict'] != 'GUARDED-DURABLE':
            bad.append(('the REAL positive fixture public-complaint-submit.js must read '
                        'as durably guarded -- it hashes a submission_key and reads it '
                        'back inside a ten-minute window before writing',
                        'GUARDED-DURABLE', got['verdict'] if got else None))
    return bad


TRIAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'idempotency_triage.json')


def load_triage():
    """The hand-written judgments. Item 6.

    Returns (entries, error). AN UNREADABLE REGISTER IS AN ERROR, NOT AN EMPTY
    ONE: falling back to {} would report every file as untriaged, which reads
    as "nobody has looked" and is indistinguishable from the register having
    been deleted.
    """
    try:
        d = json.loads(io.open(TRIAGE, encoding='utf-8').read())
    except Exception as e:
        return None, '%s: %s' % (type(e).__name__, e)
    f = d.get('files')
    if not isinstance(f, dict):
        return None, 'no "files" object -- the register has the wrong shape'
    return f, None


def key_term_coverage():
    """How many api/ files contain each vocabulary term.

    A term matching ZERO files has never contributed to a verdict, and an
    aspirational vocabulary reads exactly like a complete one. Printed on every
    run so the list's own coverage is visible rather than assumed.
    """
    counts = dict((t, 0) for t in KEY_TERMS)
    for root, _dirs, files in os.walk(os.path.join(REPO, 'api')):
        for f in files:
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            try:
                code = io.open(os.path.join(root, f), encoding='utf-8',
                               errors='replace').read()
            except Exception:
                continue
            for t in KEY_TERMS:
                if t in code:
                    counts[t] += 1
    return counts


def main(argv):
    bad = run_fixtures()
    print('IDEMPOTENCY CHECK -- criteria %s, report only' % CRITERIA_VERSION)
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING REAL WAS JUDGED.')
        for n, w, g in bad:
            print('     expected %-22s got %-22s %s' % (w, g, n))
        return 2
    # TWO real positives now, not one. api/ledger.js alone could never have
    # caught the vocabulary being incomplete -- it uses two terms the list
    # already knew. The count is computed, not typed, so adding a third fixture
    # cannot leave this sentence stale.
    print('  blind lock: %d/%d fixtures correct -- %d synthetic plus the REAL '
          'api/ledger.js and api/sairndental/public-complaint-submit.js'
          % (len(SYNTHETIC) + 2, len(SYNTHETIC) + 2, len(SYNTHETIC)))
    if '--fixtures' in argv:
        return 0

    rows = []
    for root, _dirs, files in os.walk(os.path.join(REPO, 'api')):
        for f in sorted(files):
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO).replace(os.sep, '/')
            a = analyse(rel, io.open(p, encoding='utf-8', errors='replace').read())
            if a:
                rows.append(a)

    by = {}
    for r in rows:
        by.setdefault(r['verdict'], []).append(r)

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'files': rows}, indent=1))
        return 1 if by.get('UNGUARDED') or by.get('GUARDED-IN-MEMORY') else 0

    tot = sum(r['writes'] for r in rows)
    print('  files with a mutating fetch: %d   mutating calls: %d' % (len(rows), tot))
    for v in ('GUARDED-IN-MEMORY', 'UNGUARDED', 'UNIQUE-CONSTRAINT-MAYBE',
              'GUARDED-DURABLE'):
        n = len(by.get(v, []))
        w = sum(r['writes'] for r in by.get(v, []))
        note = {'GUARDED-IN-MEMORY': '  <- looks idempotent, is not across processes',
                'UNGUARDED': '  <- a retry processes the event twice',
                'UNIQUE-CONSTRAINT-MAYBE': '  <- upsert/unique may carry it; NOT proof',
                'GUARDED-DURABLE': ''}[v]
        print('    %-24s %3d file(s), %4d write(s)%s' % (v, n, w, note))
    print('')
    # ── THE VOCABULARY'S OWN COVERAGE, PRINTED (2026-09-14) ─────────────────
    # A guard named outside this list reads as UNGUARDED, and that is exactly
    # how public-complaint-submit.js -- which has a real durable guard and its
    # own migration -- sat in the UNGUARDED column. The list cannot be derived
    # (the attempt is recorded at KEY_NAMES), so its limits are disclosed
    # instead of assumed.
    cov = key_term_coverage()
    never = [t for t in KEY_TERMS if cov[t] == 0]
    print('')
    print('  THE KEY VOCABULARY IS HAND-WRITTEN, AND A GUARD NAMED OUTSIDE IT')
    print('  READS AS UNGUARDED. Files containing each term:')
    print('    ' + '  '.join('%s=%d' % (t, cov[t]) for t in KEY_TERMS))
    if never:
        print('    %d term(s) match NO file and never have: %s'
              % (len(never), ', '.join(never)))
        print('    That is not an error -- it is the list being aspirational')
        print('    rather than derived, which reads exactly like a complete one.')
    print('    If a real guard is in the UNGUARDED list below, READ IT before')
    print('    triaging it: it may be guarded under a name this list lacks.')
    # ── THE DERIVED HALF (2026-09-14) ──────────────────────────────────────
    # The classification cannot be derived -- three attempts are recorded at
    # KEY_SHAPE, each measured and each worse. The CANDIDATES can, and that is
    # the half that failed: submission_key sat in the tree for a day with a
    # real guard on it and nothing pointed at it. This never classifies; it
    # produces a lead, and an unclassified lead is loud.
    cands = derive_key_candidates(REPO)
    unclassified = sorted(k for k in cands if k not in KEY_CANDIDATES_JUDGED)
    print('')
    print('  KEY-SHAPED COLUMNS DERIVED FROM api/, NOT FROM A LIST: %d'
          % len(cands))
    print('    Filtered with =eq. inside a file that writes, name not already')
    print('    in the vocabulary. %d judged, %d UNCLASSIFIED.'
          % (len(cands) - len(unclassified), len(unclassified)))
    if unclassified:
        print('    !! UNCLASSIFIED -- a guard built on one of these reads as')
        print('       UNGUARDED until somebody decides. Add it to')
        print('       KEY_CANDIDATES_JUDGED (or to KEY_TERMS if it IS a key):')
        for k in unclassified:
            print('         %-18s %s' % (k, ', '.join(cands[k][:3])))
    else:
        print('    Every derived candidate has a judgment. That is not the same')
        print('    as the vocabulary being complete -- a key whose name is not')
        print('    key-shaped at all is invisible to this too, and would come')
        print('    back as a false UNGUARDED exactly as submission_key did.')
    print('')
    # ── ITEM 6: HOW MANY OF THESE HAS ANYBODY ACTUALLY READ ────────────────
    # "Being triaged" with no denominator is indistinguishable from nothing
    # happening, and that is what this row existed as for a day. Every UNGUARDED
    # file either has a hand-written judgment in tools/idempotency_triage.json
    # or is counted as untriaged, by name.
    tri, terr = load_triage()
    unguarded_files = [r['file'] for r in by.get('UNGUARDED', [])]
    print('')
    if terr:
        # NOT an empty register. See load_triage().
        print('  !! THE TRIAGE REGISTER COULD NOT BE READ (%s).' % terr)
        print('     Every file below is reported as UNTRIAGED because nothing')
        print('     could be looked up -- that is this tool failing, NOT a')
        print('     statement that nobody has judged them.')
        tri = {}
    judged = dict((f, v) for f, v in tri.items()
                  if v.get('verdict') and v.get('verdict') != 'UNTRIAGED')
    untriaged = [f for f in unguarded_files if f not in judged]
    covered = [f for f in judged if f in unguarded_files]
    # THREE NUMBERS AND THEY DO NOT ADD UP TO EACH OTHER, ON PURPOSE. A file can
    # be judged and no longer UNGUARDED -- public-complaint-submit.js is exactly
    # that, judged as a checker false negative and then reclassified. Printing
    # one fused "N of M judged" made the list below contradict its own headline
    # on the first run.
    print('  ITEM 6 TRIAGE -- %d UNGUARDED file(s); %d judged, %d untriaged'
          % (len(unguarded_files), len(covered), len(untriaged)))
    if len(judged) != len(covered):
        print('    (%d entr(y/ies) in the register are for files the checker no '
              'longer flags -- listed below)' % (len(judged) - len(covered)))
    if judged:
        counts = {}
        for v in judged.values():
            counts[v['verdict']] = counts.get(v['verdict'], 0) + 1
        print('    verdicts: ' + '  '.join('%s=%d' % kv for kv in sorted(counts.items())))
        for f in sorted(judged):
            print('      %-46s %s' % (f, judged[f]['verdict']))
    if untriaged:
        print('    UNTRIAGED (nobody has read these; no statement covers them):')
        for f in sorted(untriaged):
            print('      ' + f)
    # A judgment about a file the checker no longer flags is stale, and a stale
    # exemption is how a real finding goes quiet. Named rather than ignored.
    stale = [f for f in judged if f not in unguarded_files]
    if stale:
        print('    JUDGED BUT NO LONGER UNGUARDED -- re-read or drop the entry:')
        for f in sorted(stale):
            print('      %-46s (%s)' % (f, judged[f]['verdict']))
    print('')
    print('  THE NEGATIVE FIXTURE IS SYNTHETIC AND THAT IS A REAL LIMIT: no')
    print('  in-memory-keyed write path exists on this platform to point at, so')
    print('  this checker has never caught a real instance of the shape it most')
    print('  wants to catch. A zero in that row is not yet evidence.')
    for r in by.get('GUARDED-IN-MEMORY', []) + by.get('UNGUARDED', [])[:15]:
        print('    %-46s %s (%d write(s))' % (r['file'], r['verdict'], r['writes']))
    if len(by.get('UNGUARDED', [])) > 15:
        print('    ... and %d more UNGUARDED (--json for all)'
              % (len(by['UNGUARDED']) - 15))
    return 1 if (by.get('UNGUARDED') or by.get('GUARDED-IN-MEMORY')) else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
