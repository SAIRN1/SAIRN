#!/usr/bin/env python
# OWNER: cody
"""Who owns each tool, derived from the claim-commit history rather than guessed.

    python tools/tool_owner_map.py              # report, and write the JSON
    python tools/tool_owner_map.py --check      # is the JSON current?
    python tools/tool_owner_map.py --fixtures   # the criteria lock, alone
    python tools/tool_owner_map.py --ownerless  # tools with no owner at all

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY -- it reads git and
writes exactly one file, `docs/tool-owner-map.json`, and never touches a tool.

── THE DEFECT IT EXISTS FOR, MEASURED 2026-10-06 ───────────────────────────
Routing a finding needs an owner, and **most tracked tools carry no `# OWNER:`
line.** THE RATIO IS NOT WRITTEN HERE ON PURPOSE -- this tool prints it on every
run and a number in a docstring drifts from the thing it describes. (It was "13
of 297" when this file was written and "16 of 311" an hour later, which is the
argument.) For every file without one, routing in the 2026-10-06 queue was
reconstructed by hand from the `chore(claims)` subjects -- once per batch,
un-reviewably, with the reconstruction thrown away afterwards.

Three findings that batch could not be routed to anybody because of it: 30
dead-to-their-own-evidence rules across 16 tools, 64 undecoded subprocess sites,
and three selftests that never drive their CLI.

── WHAT IT DERIVES, AND WHY THAT IS WEAKER THAN A LINE IN THE FILE ─────────
A claim commit's subject carries `FILES: a.py b.py ...`, so the session that
last claimed a file is recoverable. **THAT IS NOT THE SAME AS THE AUTHOR** and
the output says so per row:

  OWNER_LINE   the file carries `# OWNER: x` (or `// OWNER: x` in a .js file).
               AUTHORITATIVE -- nothing else is.
  LAST_CLAIM   derived. The most recent session to name it in a FILES list.
  CONTESTED    derived, and more than one session has claimed it. The last
               claimer wins the `owner` field and the others are listed, because
               `push_retry.py` resolves to fourth while hank has edited it too
               and a single name would hide that.
  CLAIM_SUBJECT_ONLY
               derived, and WEAKER than LAST_CLAIM: a claim commit's SUBJECT
               names the path and no FILES list does. A subject is prose, not a
               declaration of scope, and the row cites the commit.
  UNRECORDED   no OWNER line, no claim -- but the file HAS git history, so
               ownership is unrecorded rather than absent and the first/last
               commits say where to start. ROUTABLE.
  UNKNOWN      no OWNER line, no claim, and NO resolvable history here. A
               genuine could-not-tell.

  **UNRECORDED AND UNKNOWN WERE ONE BUCKET CALLED `NONE` UNTIL 2026-10-07**,
  whose own vocabulary entry read "UNKNOWN, not unowned" -- so the prose drew a
  distinction the data did not, and every consumer had to re-interpret the
  field to use it. They are now separate states with separate counts, plus an
  OWNERLESS TOTAL, because two numbers are harder to ignore than one.

── WHAT IT CANNOT DO, NAMED RATHER THAN DISCOVERED ─────────────────────────
  * It cannot see a tool somebody built WITHOUT claiming it. That is the
    UNRECORDED bucket and it is the largest one.
  * It attributes to the last CLAIMER, not the author. A session that claimed a
    file to read it outranks the session that wrote it.
  * A claim subject that lists a file it never touched is indistinguishable from
    one that did.
  * `git log --grep` reads the subject line only, so a FILES list wrapped into
    the body is invisible. Reported as a count, not silently dropped.

**SO THE OWNER_LINE COUNT IS THE NUMBER TO WATCH.** Every file that gains one
is a row this tool stops having to guess, and the report prints that ratio first.
"""
import argparse
import collections
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                # noqa: E402

CRITERIA_VERSION = '2026-10-07.1'
OUT = os.path.join('docs', 'tool-owner-map.json')
MAX_CLAIM_COMMITS = 6000

# `# OWNER: name` in the first few lines. Anchored at line start so a mention
# inside a docstring does not read as a declaration.
# `#` OR `//`, because TRACKED_EXT includes .js and a JavaScript file cannot
# carry a `#` comment. Until 2026-10-07 the ONLY authoritative basis was
# inexpressible in one of the three languages this tool tracks, so every .js
# file was permanently stuck on a derived basis however much its author wanted
# to state ownership. Found while routing tests/sairnfreedom_server_backup.js.
OWNER_LINE = re.compile(r'^(?:#|//)\s*OWNER:\s*([A-Za-z0-9_]+)\s*$', re.M)
CLAIM_SUBJ = re.compile(r'^chore\(claims\):\s+([A-Za-z0-9_]+)\s+claims\b')
FILES_IN_SUBJ = re.compile(r'FILES:\s*(.*)$')
TRACKED_EXT = ('.py', '.js', '.sh')


class CouldNotTell(Exception):
    pass


# ── THE UNIVERSE WAS tools/ ONLY, AND THAT WAS A GAP (widened 2026-10-06) ──
# Routing a finding in tests/ asked this map and got "NOT IN MAP". Measured the
# day it was widened: tests/push_gate/check8_probe.py and
# tests/seam_check/run_delegation_probe.py were both named as suspects in a
# clone-corruption hunt and NEITHER could be attributed, because the universe
# stopped at tools/. A map that cannot answer for the directory a finding is in
# is an owner map for one directory.
#
# AND A SECOND BASIS WAS BUILT AND THEN REMOVED, which is recorded so nobody
# pays for the idea twice. `--infer-creator` derived an owner from the commit
# that CREATED a file and the session its message names. In isolation it works
# -- tools/benford_check.py resolves to `Fourth` from df3f194e -- but wired into
# the full run it reported ZERO across 718 unattributed files, and I could not
# explain the gap inside the batch. A FLAG THAT REPORTS NOTHING WHERE A HAND
# DERIVATION FOUND FIVE IS THE DEFECT SHAPE THIS PLATFORM KEEPS PAYING FOR, so
# it was removed rather than shipped. The idea is sound; the wiring was not
# measured. Next attempt: assert the inference on a KNOWN file first, as an arm,
# before trusting any aggregate.
ROOTS = ('tools/', 'tests/', 'scripts/')


def tracked_tools():
    r = subprocess.run(['git', '-C', REPO, 'ls-files'] + list(ROOTS),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        raise CouldNotTell('git ls-files failed, so the population is unknown. '
                           'NOT an empty population.')
    out = [f.strip() for f in (r.stdout or '').split('\n')
           if f.strip().endswith(TRACKED_EXT)]
    if not out:
        raise CouldNotTell('%s hold no tracked .py/.js/.sh file -- the '
                           'layout moved and NOTHING was read.'
                           % ', '.join(ROOTS))
    return sorted(out)


def owner_lines(paths):
    """{relpath: session} for every file carrying an `# OWNER:` line."""
    out = {}
    for rel in paths:
        p = os.path.join(REPO, rel.replace('/', os.sep))
        try:
            head = io.open(p, encoding='utf-8', errors='replace').read(4000)
        except OSError:
            continue
        m = OWNER_LINE.search(head)
        if m:
            out[rel] = m.group(1)
    return out


def claim_history():
    """{basename: [(session, sha), ...]} oldest first, plus how much was read."""
    r = subprocess.run(['git', '-C', REPO, 'log', '--format=%H%x09%s',
                        '--grep=chore(claims):', '-n', str(MAX_CLAIM_COMMITS)],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        raise CouldNotTell('git log failed, so no claim history was read')
    rows = [l.split('\t', 1) for l in (r.stdout or '').split('\n') if '\t' in l]
    hist = collections.defaultdict(list)
    with_files = 0
    # REVERSED: git log is newest-first and the LAST claim must win.
    for sha, subj in reversed(rows):
        m = CLAIM_SUBJ.match(subj)
        if not m:
            continue
        f = FILES_IN_SUBJ.search(subj)
        if not f:
            continue
        with_files += 1
        for tok in f.group(1).split():
            if tok.endswith(TRACKED_EXT):
                base = os.path.basename(tok.replace('\\', '/'))
                hist[base].append((m.group(1), sha[:8]))
    return hist, len(rows), with_files


# ── THE TWO NEW PREDICATES, AS FUNCTIONS SO THE LOCK TESTS THE REAL ONES ───
# Written as named functions rather than inline `if`s for one reason: a fixture
# that re-implements the condition locks a COPY, and a copy drifts. These are
# called by build() and by run_fixtures(), so there is one of each.
def subject_only_hit(subj, basename):
    """Does this claim subject name `basename` and carry NO FILES list?

    The FILES-list case is already handled by claim_history(); a subject that
    has one must NOT reach the weaker CLAIM_SUBJECT_ONLY basis.
    """
    m = CLAIM_SUBJ.search(subj)
    if not m:
        return None
    if 'FILES:' in subj:
        return None
    if basename not in subj:
        return None
    return m.group(1)


def ownerless_basis(file_history_for_path):
    """UNRECORDED when the file has git history, UNKNOWN when it does not.

    The whole point of the split: the first is routable (the commits are named),
    the second is a could-not-tell. Folding them into one `NONE` reported an
    unanswerable question and an actionable one as the same number.
    """
    return 'UNRECORDED' if file_history_for_path else 'UNKNOWN'


def build():
    paths = tracked_tools()
    lines = owner_lines(paths)
    hist, claim_commits, with_files = claim_history()
    subject_only = claim_subject_mentions(paths)
    history = file_history(paths)
    rows = {}
    for rel in paths:
        base = os.path.basename(rel)
        claims = hist.get(base, [])
        sessions = []
        for s, _sha in claims:
            if s not in sessions:
                sessions.append(s)
        if rel in lines:
            rows[rel] = {'owner': lines[rel], 'basis': 'OWNER_LINE',
                         'also_claimed_by': [s for s in sessions
                                             if s != lines[rel]]}
        elif len(sessions) > 1:
            rows[rel] = {'owner': claims[-1][0], 'basis': 'CONTESTED',
                         'last_claim': claims[-1][1],
                         'also_claimed_by': [s for s in sessions
                                             if s != claims[-1][0]]}
        elif sessions:
            rows[rel] = {'owner': sessions[0], 'basis': 'LAST_CLAIM',
                         'last_claim': claims[-1][1], 'also_claimed_by': []}
        elif rel in subject_only:
            # ── CLAIM_SUBJECT_ONLY (2026-10-07, cc) ────────────────────────
            # A claim commit that NAMES a file in its subject but carries no
            # `FILES:` list was invisible here, because the derivation reads
            # FILES lists and nothing else. Real instance:
            #   c1e06f33  "chore(claims): cody claims cody -- negative control
            #              for tests/sairnfreedom_server_backup.js -- ..."
            # no FILES section at all, so the map said NONE for a file with a
            # real claim commit naming it, and fourth routed the discrepancy as
            # "owner cody, claim c1e06f33, owner map says None". It was not a
            # bad owner, it was an UNREAD SOURCE.
            # WEAKER THAN LAST_CLAIM AND SAID SO: a subject is prose. It names a
            # session and a path and it is not a declaration of scope.
            who, subj_sha = subject_only[rel]
            rows[rel] = {'owner': who, 'basis': 'CLAIM_SUBJECT_ONLY',
                         'claim_subject_commit': subj_sha,
                         'also_claimed_by': []}
        else:
            # ── UNRECORDED vs UNKNOWN (2026-10-07, cc) ─────────────────────
            # `NONE` carried TWO different facts behind one number while its own
            # vocabulary entry said "UNKNOWN, not unowned" -- so the prose drew a
            # distinction the data did not, and a reader could not act on either.
            #
            #   UNRECORDED  nothing has recorded an owner, AND the file has git
            #               history, so there IS something to route: the commits
            #               are named. This is the actionable bucket.
            #   UNKNOWN     nothing has recorded an owner and the file has NO
            #               resolvable history in this clone. A genuine
            #               could-not-tell, and it must not be counted with the
            #               routable ones.
            #
            # tools/va_rule_currency.py's own comment is the evidence the split
            # was needed: it reads `"basis": "NONE"` and glosses it "not UNKNOWN,
            # but NO OWNER AT ALL", i.e. a consumer had to RE-INTERPRET the field
            # in prose to use it, which is the field failing to carry its meaning.
            # NOT `hist`: that name holds the claim-history dict this loop reads
            # on EVERY iteration (`hist.get(base)` above). Rebinding it here
            # turned it into a list and the next file raised
            # AttributeError: 'list' object has no attribute 'get'.
            fhist = history.get(rel) or []
            if ownerless_basis(fhist) == 'UNRECORDED':
                rows[rel] = {'owner': None, 'basis': 'UNRECORDED',
                             'first_commit': fhist[-1], 'last_commit': fhist[0],
                             'also_claimed_by': []}
            else:
                rows[rel] = {'owner': None, 'basis': 'UNKNOWN',
                             'also_claimed_by': []}
    return rows, {'tools': len(paths), 'owner_line': len(lines),
                  'claim_commits_read': claim_commits,
                  'claim_commits_with_files': with_files,
                  'criteria': CRITERIA_VERSION}


def claim_subject_mentions(paths):
    """{relpath: (session, sha)} for a claim commit whose SUBJECT names the path.

    Read because a FILES-only derivation misses them, which is a real instance
    rather than a hypothetical -- see CLAIM_SUBJECT_ONLY above. Only paths with no
    FILES-list claim reach this bucket, so this never overrides a declaration.
    """
    out = {}
    r = subprocess.run(['git', '-C', REPO, 'log', '--format=%H%x09%s',
                        '--grep', '^chore(claims):'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return out
    log = r.stdout.strip()
    if not log:
        return out
    byname = {}
    for rel in paths:
        byname.setdefault(os.path.basename(rel), []).append(rel)
    for line in log.split('\n'):
        if '\t' not in line:
            continue
        sha, subj = line.split('\t', 1)
        for base, rels in byname.items():
            who = subject_only_hit(subj, base)
            if not who:
                continue
            for rel in rels:
                # The log is newest-first, so the FIRST hit is the most recent
                # claim -- the same rule LAST_CLAIM uses.
                out.setdefault(rel, (who, sha[:12]))
    return out


def file_history(paths):
    """{relpath: [sha, ...]} newest first, for the UNRECORDED/UNKNOWN split.

    ONE git call, not one per file: a per-file log over 980 paths is slow enough
    that somebody would turn the split off.
    """
    out = {}
    r = subprocess.run(['git', '-C', REPO, 'log', '--format=%H', '--name-only'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return out
    log = r.stdout.strip()
    if not log:
        return out
    cur = None
    want = set(paths)
    for line in log.split('\n'):
        line = line.strip()
        if not line:
            continue
        if len(line) == 40 and all(c in '0123456789abcdef' for c in line):
            cur = line[:12]
            continue
        if cur and line in want:
            out.setdefault(line, []).append(cur)
    return out


# ── THE CRITERIA LOCK (discipline 1), on hand-built subjects only ───────────
# The classifier is the whole tool, so it is locked before any real git read.
# Every arm is paired: a shape that must classify one way AND one that must not.
FIXTURES = [
    ('chore(claims): cody claims Tooling -- x FILES: tools/a.py tools/b.py',
     ('cody', ['a.py', 'b.py']), 'a normal claim with two files'),
    ('chore(claims): hank claims platform -- y FILES: tools\\c.py',
     ('hank', ['c.py']), 'a WINDOWS path separator, which this repo produces'),
    ('chore(claims): cc releases cc -- FILES: tools/d.py',
     None, 'a RELEASE is not a claim and must not assign ownership'),
    ('docs(thing): unrelated commit FILES: tools/e.py',
     None, 'a non-claim commit that happens to carry a FILES: list'),
    # MY EXPECTATION HERE WAS WRONG AND THE LOCK SAID SO BEFORE ANY GIT READ.
    # I wrote `None`, reasoning "no files means nothing". The parser recognises
    # the SESSION and returns an EMPTY file list, which is the correct and more
    # informative answer -- and build() then skips the commit entirely at
    # `if not f: continue`, so it still assigns nothing. Corrected to what the
    # code does, in the arm, rather than bent to what I assumed.
    ('chore(claims): fourth claims x -- no file list at all',
     ('fourth', []), 'a claim with NO FILES list names its session and '
                     'contributes ZERO files -- build() skips it, so nothing '
                     'is assigned, but "unparsed" and "parsed with no files" '
                     'are different answers'),
    ('chore(claims): cody claims z -- FILES: docs/x.md sql/y.sql',
     ('cody', []), 'a claim naming only non-tool files yields no tool rows'),
]


def run_fixtures(verbose=False):
    """-> (failures, arms_run). The ARM COUNT IS COUNTED, NOT WRITTEN.

    It used to be `len(FIXTURES) + 3`, a literal for the arms that are not in
    FIXTURES -- and adding nine arms on 2026-10-07 would have left the tool
    reporting "7/7 classify correctly" while running sixteen. The denominator
    is now incremented where an arm actually runs.
    """
    bad = []
    arms = 0
    for subj, want, why in FIXTURES:
        arms += 1
        m = CLAIM_SUBJ.match(subj)
        got = None
        if m:
            f = FILES_IN_SUBJ.search(subj)
            toks = []
            if f:
                toks = [os.path.basename(t.replace('\\', '/'))
                        for t in f.group(1).split() if t.endswith(TRACKED_EXT)]
            got = (m.group(1), toks)
        if got != want:
            bad.append('%s -- wanted %r got %r' % (why, want, got))
        elif verbose:
            print('  ok   %s' % why)
    # And the OWNER_LINE anchor, both directions.
    for src, want, why in (
            ('# OWNER: cody\n"""doc"""\n', 'cody', 'a real OWNER line'),
            ('"""see # OWNER: cody in the other file"""\n', None,
             'a MENTION inside a docstring is NOT a declaration'),
            ('  # OWNER: cody\n', None,
             'an INDENTED owner line is a comment in code, not a header'),
            # ── THE // ARM (2026-10-07) ────────────────────────────────────
            # TRACKED_EXT carries .js and a .js file cannot write a `#`
            # comment, so before this the authoritative basis was unreachable
            # for a third of the universe.
            ('// OWNER: fourth\nconst x = 1;\n', 'fourth',
             'a JavaScript OWNER line -- `//`, because a .js file cannot '
             'carry a `#` comment and .js IS tracked'),
            ('  // OWNER: fourth\n', None,
             'an INDENTED // owner line is a comment in code, not a header'),
            ('const s = "// OWNER: fourth";\n', None,
             'a // OWNER line inside a JS STRING is not a declaration')):
        arms += 1
        m = OWNER_LINE.search(src)
        got = m.group(1) if m else None
        if got != want:
            bad.append('%s -- wanted %r got %r' % (why, want, got))
        elif verbose:
            print('  ok   %s' % why)
    # CLAIM_SUBJECT_ONLY, both directions, on the predicate build() calls.
    for subj, base, want, why in (
            ('chore(claims): cody claims cody -- negative control for '
             'tests/sairnfreedom_server_backup.js', 'sairnfreedom_server_backup.js',
             'cody', 'a claim SUBJECT naming a path with NO FILES list -- the '
                     'real c1e06f33 shape that read as NONE'),
            ('chore(claims): cody claims cody -- x FILES: tools/a.py',
             'a.py', None,
             'a claim WITH a FILES list must NOT reach the weaker basis -- '
             'claim_history() already owns it'),
            ('chore(claims): cody claims cody -- nothing about it', 'a.py',
             None, 'a claim that does not name the file at all'),
            ('docs(thing): mentions tools/a.py', 'a.py', None,
             'a NON-claim commit mentioning the path is not a claim')):
        arms += 1
        got = subject_only_hit(subj, base)
        if got != want:
            bad.append('%s -- wanted %r got %r' % (why, want, got))
        elif verbose:
            print('  ok   %s' % why)
    # UNRECORDED vs UNKNOWN, both directions.
    for fhist, want, why in (
            (['abc123def456'], 'UNRECORDED',
             'no owner recorded but the file HAS history -- ROUTABLE'),
            ([], 'UNKNOWN',
             'no owner AND no resolvable history -- a COULD-NOT-TELL, and it '
             'must not be counted with the routable ones')):
        arms += 1
        got = ownerless_basis(fhist)
        if got != want:
            bad.append('%s -- wanted %r got %r' % (why, want, got))
        elif verbose:
            print('  ok   %s' % why)
    return bad, arms


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true',
                    help='does the written JSON match what git says now?')
    ap.add_argument('--fixtures', action='store_true')
    ap.add_argument('--ownerless', action='store_true',
                    help='only the tools nobody owns')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)

    print('TOOL OWNER MAP -- criteria %s' % CRITERIA_VERSION)
    bad, arms = run_fixtures(verbose=a.fixtures)
    if bad:
        print('\nCRITERIA LOCK FAILED -- %d of %d:' % (len(bad), arms))
        for b in bad:
            print('  ! %s' % b)
        print('\nNOTHING REAL WAS DERIVED. A misclassifying parser would assign '
              'every tool to\nwhoever released it last, which is worse than no '
              'map at all.')
        return EXIT_COULD_NOT_RUN
    print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
          'subjects only' % (arms, arms))
    if a.fixtures:
        return 0

    try:
        rows, meta = build()
    except CouldNotTell as exc:
        print('\nCOULD NOT RUN -- %s' % exc)
        return EXIT_COULD_NOT_RUN

    by = collections.Counter(v['basis'] for v in rows.values())
    print('  tracked files in %-14s %4d'
          % (','.join(r.rstrip('/') for r in ROOTS), meta['tools']))
    print('  with an `# OWNER:` line       %4d   <- AUTHORITATIVE, the only '
          'basis that is not a guess' % meta['owner_line'])
    print('  derived LAST_CLAIM            %4d' % by.get('LAST_CLAIM', 0))
    print('  derived CONTESTED             %4d   (>1 session has claimed it)'
          % by.get('CONTESTED', 0))
    print('  derived CLAIM_SUBJECT_ONLY    %4d   (a claim SUBJECT names it and '
          'no FILES list does -- weaker than LAST_CLAIM)'
          % by.get('CLAIM_SUBJECT_ONLY', 0))
    # ── TWO NUMBERS WHERE THERE WAS ONE, AND A TOTAL (2026-10-07, cc) ───────
    # The single `NONE` line said "UNKNOWN, not unowned" and counted both. A
    # reader could not tell how many were routable from how many were
    # unanswerable, and those need different actions.
    _unrec = by.get('UNRECORDED', 0)
    _unk = by.get('UNKNOWN', 0)
    print('  UNRECORDED                   %4d   <- no owner recorded, but the '
          'file HAS history: ROUTABLE' % _unrec)
    print('  UNKNOWN                      %4d   <- no owner AND no resolvable '
          'history: a COULD-NOT-TELL' % _unk)
    print('  OWNERLESS TOTAL              %4d   = UNRECORDED + UNKNOWN. Printed '
          'because two numbers are easier to ignore than one.' % (_unrec + _unk))
    print('  claim commits read            %4d, of which %d carry a FILES list'
          % (meta['claim_commits_read'], meta['claim_commits_with_files']))

    if a.ownerless:
        print('\nTOOLS WITH NO OWNER AT ALL -- no OWNER line and no claim has '
              'ever named them. The two buckets need DIFFERENT actions:')
        _u = sorted(k for k, v in rows.items() if v['basis'] == 'UNRECORDED')
        _k = sorted(k for k, v in rows.items() if v['basis'] == 'UNKNOWN')
        print('\n  UNRECORDED (%d) -- routable: the commits are named in the map'
              % len(_u))
        for rel in _u:
            print('    %-62s last %s' % (rel, (rows[rel].get('last_commit') or '?')))
        print('\n  UNKNOWN (%d) -- a COULD-NOT-TELL: no resolvable history here'
              % len(_k))
        for rel in _k:
            print('    %s' % rel)

    payload = {'_what_this_is': __doc__.split('\n')[0],
               '_basis_vocabulary': {
                   'OWNER_LINE': 'the file says so. Authoritative.',
                   'LAST_CLAIM': 'derived from the most recent claim commit.',
                   'CONTESTED': 'derived, and more than one session has claimed '
                                'it; `also_claimed_by` lists the others.',
                   'CLAIM_SUBJECT_ONLY':
                       'a claim commit SUBJECT names this path and no FILES '
                       'list does. Derived and WEAKER than LAST_CLAIM: a '
                       'subject is prose, not a declaration of scope. '
                       '`claim_subject_commit` cites it.',
                   'UNRECORDED':
                       'no OWNER line and no claim, but the file HAS git '
                       'history -- so ownership is UNRECORDED rather than '
                       'absent, and `first_commit`/`last_commit` say where to '
                       'start. ROUTABLE.',
                   'UNKNOWN':
                       'no OWNER line, no claim, and NO resolvable history in '
                       'this clone. A genuine could-not-tell, kept separate '
                       'from UNRECORDED because the two need different '
                       'actions. Replaces the old single NONE, which carried '
                       'both and said so only in prose.'},
               '_regenerate': 'python tools/tool_owner_map.py',
               '_meta': meta, 'tools': rows}
    body = json.dumps(payload, indent=1, sort_keys=True) + '\n'
    path = os.path.join(REPO, OUT)
    if a.check:
        try:
            have = io.open(path, encoding='utf-8').read()
        except OSError:
            print('\n%s does not exist yet.' % OUT)
            return 1
        if have != body:
            print('\nFAIL: %s no longer matches what git says. A tool was '
                  'added, claimed or\ngiven an OWNER line and the map was not '
                  'regenerated.\n    python tools/tool_owner_map.py' % OUT)
            return 1
        print('\n%s matches git. Note: a MATCH means no source is missing; it '
              'does not mean\nany derived owner is the real author.' % OUT)
        return 0

    io.open(path, 'w', encoding='utf-8', newline='\n').write(body)
    print('\nwrote %s' % OUT)

    return finish(
        ['%s -- no OWNER line and no claim has ever named it (%s)' % (rel, v['basis'])
         for rel, v in sorted(rows.items())
         if v['basis'] in ('UNRECORDED', 'UNKNOWN')],
        quiet=False,
        clean_line='\nCLEAN -- every tracked tool resolves to a session.')


if __name__ == '__main__':
    sys.exit(main())
