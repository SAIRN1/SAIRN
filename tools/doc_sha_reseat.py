#!/usr/bin/env python
# OWNER: cc
"""doc_sha_reseat.py -- re-seat commit SHAs in the PROSE tracking documents
from git's own old->new rewrite map, so a rebase stops turning true citations
into false ones.

    python tools/doc_sha_reseat.py --check        # report, change nothing
    python tools/doc_sha_reseat.py --post-rewrite # read git's map on stdin
    python tools/doc_sha_reseat.py --fixtures     # criteria lock, reads no doc

── THE DEFECT THIS EXISTS FOR, MEASURED 2026-10-06 (cc) ──────────────────────
`tools/sairn_claim.py` REBASES BEFORE IT PUSHES. Every local commit therefore
gets a new SHA at push time. A session that writes *"fixed in `<sha>`"* into a
tracking document while that commit is still local has written a SHA that is
dead the moment it lands -- and the document still reads as precise, which is
the whole problem. Nothing announces it.

MEASURED at `411f29ce`, over the backticked 7-12 hex tokens in
`docs/SAIRN-OPEN-WORK-INDEX.md`, classified by reachability from `origin/main`:

    ON-MAIN   321
    ORPHAN      8   the object exists in THIS clone and is reachable from no
                    ref -- so it resolves here and nowhere else
    ABSENT     38   not an object here at all: created in another clone,
                    orphaned there, never fetchable

**46 of 367 = 12.5%, across 37 rows.** And five of the orphans were mine, from
one batch, which is how the shape was recognised rather than theorised.

**DO NOT QUOTE THOSE FOUR NUMBERS AS CURRENT. RUN `--census`.** They are a
dated observation at one commit, kept because the DISCOVERY is the argument,
and they will be wrong tomorrow. Guardian v2's own Check 0c is about exactly
this -- a count carried in prose, with nothing forcing it to match -- and that
skill has had the same figure wrong in three places at once. `--census` is the
derived source: it prints the two definitions it uses, counts by reachability,
and splits the dead rows into the ones a rewrite map could name and the ones no
map ever will.

── THE HALF THAT ALREADY EXISTED, AND WHY THIS IS NOT A SECOND COPY OF IT ────
`.githooks/post-rewrite` has done exactly the right thing since 2026-09-24: it
fires once after a rebase or an `--amend` with git's own `<old> <new>` map on
stdin and hands it to `defect_register.py --post-rewrite`. That is strictly
better than any subject match, because it is git's own record of which commit
became which.

ITS SCOPE IS ONE FILE. `docs/defect-density-register.json` is re-seated and
nothing else is -- so the register stayed healthy (546 ON-MAIN of 564 hexish
tokens at the same commit) while the prose documents beside it rotted. The gap
was never the mechanism; it was the list of files the mechanism covered.

── WHY A SEPARATE TOOL AND NOT A FLAG ON defect_register.py ──────────────────
That file is ~1,700 lines about ONE register with a schema: a typed `commit`
field, a validator, a density calculation. Re-seating free prose is a different
problem with a different failure mode -- a 7-hex token in a markdown table may
not be a SHA at all. Bolting it on would mean one tool whose `--post-rewrite`
means two unrelated things. The hook already invokes a list of programs; this
is the second entry on it.

── WHAT IT WILL AND WILL NOT SUBSTITUTE ──────────────────────────────────────
ONLY A TOKEN THAT IS A PREFIX OF AN `old` SHA GIT ITSELF NAMED. There is no
subject matching, no patch-id, no heuristic. If git says X became Y and the
document contains a 7-to-12 character prefix of X, then the document is citing
X and the answer is Y -- one right answer, no judgement. Where the map is
silent this writes nothing, and says it wrote nothing.

THE PREFIX COMPARISON RUNS IN ONE DIRECTION ONLY, copied deliberately from
`defect_register.cmd_post_rewrite`: the DOCUMENT's token must be a prefix of
the map's `old`, never the reverse. A 7-character token cannot be allowed to
match a 40-character SHA that merely starts the same way as a different
commit's abbreviation.

AND A SUBSTITUTION THAT WOULD NOT CHANGE ANYTHING IS NOT MADE. If `new` also
starts with the token -- which happens when a rebase was a fast-forward -- the
citation is still correct and is left exactly as it was.

── THE HUMAN GATE, WHICH IS NOT OPTIONAL ─────────────────────────────────────
Cross-domain discipline 11: a fixer may propose a repair and may not apply its
own. This tool splits the difference the way the existing hook already does,
and the split is by FILE OWNERSHIP rather than by taste:

  * A file in NO other session's live claim is REWRITTEN IN THE WORKING TREE
    and never staged, never committed. That is the identical contract
    `defect_register.py --post-rewrite` has carried since 2026-09-24, and its
    reasoning holds here: the hook runs at the end of a rebase, when the next
    thing a person does is look at the tree, and `git status` plus `git diff`
    is a stronger gate than a suggestion nobody re-runs.

  * A file inside another session's LIVE CLAIM is only PROPOSED -- printed as
    an exact old->new list and not touched. The hazard there is not
    correctness, it is a write race with a session editing that file right
    now, and no mechanical substitution is worth one.

  * `--check` proposes for everything and writes nothing, always.

── WHAT IT DOES NOT CLAIM ────────────────────────────────────────────────────
That a document whose SHAs all resolve is CORRECT. A citation can point at a
real commit and still be the wrong one -- `defect_register.is_bookkeeping_only`
exists because `--commit $(git rev-parse HEAD)` cited three bookkeeping commits
that resolved perfectly. This tool repairs pointers a rewrite BROKE. It cannot
see a pointer that was wrong when it was written.

And it does not fix history. `SAIRN-ACTIVE-WORK-*.md` files are append-only
logs of what was true when each entry was written; they are deliberately
EXCLUDED from the rewrite set and listed under `--check` as report-only, so a
stale pointer in a log is visible without being silently rewritten.
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_COULD_NOT_RUN = 2

# .1 -- first version. The stamp exists so that a past report naming a
# criteria version cannot be confused with a run under different criteria.
CRITERIA_VERSION = '2026-10-06.1'

# ── THE DOCUMENT SET, AND THE THREE CLASSES IN IT ───────────────────────────
# REWRITE: hand-authored standing documents whose SHAs are evidence pointers.
# A broken pointer here costs a reader a search and teaches them to distrust
# the column.
#
# GENERATED: never rewritten, because the generator is the fix. Re-seating a
# generated file writes an edit the next generation silently discards, and the
# push gate already refuses a push that leaves one stale -- so a re-seat here
# would look like a repair and expire at the next run.
#
# REPORT_ONLY: append-only logs. These record what was true at the moment of
# writing. Re-seating them would make a past report quietly describe a present
# tree, which is the instrument-drift failure (discipline 8) wearing a repair's
# clothing.
#
# ── THE FIRST VERSION OF THIS LIST WAS WRONG AND THE DRIVE FOUND IT ─────────
# `docs/traceability-matrix.md` and `docs/TOOLING-INVENTORY.md` were in
# REWRITE. The end-to-end drive re-seated two real citations in the
# traceability matrix, correctly, and only then did the obvious question
# surface: that file is GENERATED -- `tools/traceability_matrix.py` writes it
# from `docs/SAIRN-OPEN-WORK-INDEX.md`, which is where those same SHAs come
# from. The repair would have been overwritten by the next generation while
# reading, in the meantime, as a fix that had been applied. Both moved to
# GENERATED, and the membership is taken from `invocation_path_scan.
# GENERATED_DOCS` rather than from my own reading of which files look
# generated. `docs/recurring-bug-classes.md` was dropped outright: it does not
# exist at this commit, and a permanent COULD-NOT-READ line on every run is
# noise that trains a reader to skip the third state.
REWRITE = (
    'docs/SAIRN-OPEN-WORK-INDEX.md',
    'docs/CRITICALITY-TIERS.md',
    'docs/known-red-suites.json',
)
GENERATED = (
    'docs/traceability-matrix.md',
    'docs/TOOLING-INVENTORY.md',
    'docs/MASTER-PLAN.md',
)
REPORT_ONLY_GLOBS = (
    'SAIRN-ACTIVE-WORK-',
)

# A backticked 7-12 character lowercase hex run. BACKTICKS ARE REQUIRED and
# that is a measurement, not a style preference: over the open-work index the
# bare-word form matched 404 tokens against the backticked form's 367, and the
# extra 37 were decimal figures, register record ids and one illustrative
# literal (`1234abcd`). A repair tool with a 9% false-candidate rate on a
# 900-line standing document is not one anybody should run.
TOKEN = re.compile(r'`([0-9a-f]{7,12})`')

# ── ONE CANDIDATE RULE FOR EVERY MODE, 2026-10-07 (cc) ──────────────────────
# `--census` excluded all-digit tokens, 12-hex register record ids and the
# illustrative literal `1234abcd` in a filter written inline in its own loop.
# `--register-absent` did not -- so the register listed `1234abcd` from
# SAIRN-ACTIVE-WORK-hank.md as a PERMANENTLY ABSENT citation, which is a
# finding about nothing: it is a documentation example and was never a commit.
#
# TWO MODES OF ONE TOOL WERE USING TWO CANDIDATE RULES, and the one that WRITES
# A STANDING RECORD had the looser one. Found by reading the register's own
# output rather than the code. The rule now lives in one function that both
# modes call.
NOT_A_CITATION = frozenset(('1234abcd', 'deadbeef', 'abcdef0', '0000000',
                            'deadbeefcafe'))


def is_citation(tok):
    """True when this token could be a commit citation at all.

    EXCLUDES: an all-digit run (a figure that happens to be valid hex), a
    12-character token (this repo's register RECORD IDs are 12 hex and are not
    commits), and the documentation literals above. Everything excluded here is
    excluded from EVERY mode, which is the point.
    """
    t = str(tok or '').lower()
    if not t or t.isdigit():
        return False
    if len(t) == 12:
        return False
    return t not in NOT_A_CITATION


def git(*args):
    try:
        out = subprocess.run(('git',) + args, cwd=REPO, capture_output=True,
                             text=True, encoding='utf-8', errors='replace')
    except Exception:                                          # noqa: BLE001
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def parse_map(raw):
    """git's post-rewrite stdin: `<old> <new>` per line, full SHAs.

    Anything shorter than 7 characters on either side is not a SHA and is
    dropped rather than guessed at.
    """
    mapping = {}
    for line in (raw or '').split('\n'):
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) >= 7 and len(parts[1]) >= 7:
            mapping[parts[0]] = parts[1]
    return mapping


def substitutions(src, mapping):
    """Every (token, new) this map licenses for one document's text.

    Returns a list of (old_token, new_token). A token appearing many times
    yields one entry; the caller substitutes all occurrences of it.
    """
    out = []
    seen = set()
    for m in TOKEN.finditer(src):
        tok = m.group(1)
        if tok in seen:
            continue
        seen.add(tok)
        for old, new in mapping.items():
            # ONE DIRECTION ONLY. The document's token must be a prefix of the
            # map's old sha. See the header.
            if not old.startswith(tok):
                continue
            # A rewrite that did not move this commit changes no citation.
            if new.startswith(tok):
                break
            out.append((tok, new[:len(tok)]))
            break
    return out


def apply_subs(src, subs):
    """Substitute inside the backticks only, so prose that happens to contain
    the same hex run is untouched."""
    for old, new in subs:
        src = src.replace('`%s`' % old, '`%s`' % new)
    return src


def claimed_elsewhere():
    """Paths inside another session's LIVE claim, read from the claim records.

    FAILS CLOSED AND SAYS SO. If the claim records cannot be read, this returns
    None and every file is treated as PROPOSE-only -- because "I could not tell
    whether somebody is editing this" must never resolve to "so I edited it".
    """
    try:
        import sairn_claim
    except Exception:                                          # noqa: BLE001
        return None
    try:
        me = sairn_claim.session_name()
    except Exception:                                          # noqa: BLE001
        me = None
    held = set()
    base = os.path.join(REPO, '.claude', 'claims')
    try:
        names = sorted(os.listdir(base))
    except Exception:                                          # noqa: BLE001
        return None
    import json
    for fn in names:
        if not fn.endswith('.json'):
            continue
        who = fn[:-5]
        if me and who == me:
            continue
        try:
            d = json.load(io.open(os.path.join(base, fn), encoding='utf-8'))
        except Exception:                                      # noqa: BLE001
            return None
        for c in (d.get('claims') or []):
            if c.get('released_at'):
                continue
            for p in (c.get('files') or []):
                held.add(str(p).replace('\\', '/'))
    return held


def census_state(tok, on_main, local):
    """ON-MAIN / ORPHAN / ABSENT for one token, by REACHABILITY.

    THE TEST IS REACHABILITY FROM origin/main, NOT OBJECT EXISTENCE, and the
    difference is not pedantic: `git cat-file -e <sha>^{commit}` is
    CLONE-DEPENDENT. An orphan left by this clone's own rebase passes it here
    and fails it in every other clone on the machine. Measured 2026-10-06: the
    object-existence test reported 38 dead in the open-work index and
    reachability reported 46. A check whose verdict depends on which clone runs
    it is not a check.
    """
    t = tok.lower()
    if t in on_main[0] or on_main[1].get(t):
        return 'ON-MAIN'
    if t in local[0] or local[1].get(t):
        return 'ORPHAN'
    return 'ABSENT'


def _prefix_index(shas):
    idx = {}
    for s in shas:
        for n in range(7, 13):
            idx.setdefault(s[:n], s)
    return idx


def census_universe():
    """(on_main, local) each as (set, prefix-index). One git call apiece."""
    full = (git('rev-list', 'origin/main') or '').split()
    on_main = (set(full), _prefix_index(full))
    try:
        out = subprocess.run(
            ['git', 'cat-file', '--batch-all-objects',
             '--batch-check=%(objectname) %(objecttype)'],
            cwd=REPO, capture_output=True, text=True,
            encoding='utf-8', errors='replace')
        loc = set(l.split()[0] for l in out.stdout.splitlines()
                  if l.endswith(' commit'))
    except Exception:                                          # noqa: BLE001
        loc = set()
    return on_main, (loc, _prefix_index(loc))


def cmd_census():
    """Count this repo's SHA citations by state, with the definitions stated.

    ── THE TWO DEFINITIONS, BECAUSE THE NUMBER IS MEANINGLESS WITHOUT THEM ───
    CITATION: a BACKTICKED run of 7 to 12 lowercase hex characters. Backticks
    are required and that is a measurement, not a style preference -- over
    docs/SAIRN-OPEN-WORK-INDEX.md the bare-word form matched 404 tokens against
    the backticked form's 367, and the 37 extra were decimal figures, 12-hex
    REGISTER RECORD IDS and one illustrative literal (`1234abcd`). A repair
    tool with a 9% false-candidate rate on a 900-line standing document is not
    one anybody should run, so the census counts exactly what the repairer
    would act on and nothing else.

    POPULATION: the documents this tool knows about -- REWRITE, GENERATED and
    REPORT-ONLY -- and NOTHING ELSE. It is not "every citation in the repo".
    Every other dated inventory, handoff and design note in docs/ also carries
    citations and is deliberately out of scope: they are point-in-time reports,
    and a report whose SHAs were repointed would describe a tree it never saw.

    AND THE SPLIT THAT MATTERS: of the dead citations, how many could this tool
    actually fix? Only one it can see in a rewrite map, which means only one
    whose commit this clone still holds. An ABSENT citation was created and
    orphaned in another clone and is not fetchable from anywhere -- no map will
    ever name it. Reporting a dead count without that split would imply a
    repair that is not available.
    """
    on_main, local = census_universe()
    held = claimed_elsewhere()
    print('DOC SHA CITATION CENSUS -- criteria %s, HEAD %s'
          % (CRITERIA_VERSION, (git('rev-parse', '--short', 'HEAD') or '?')))
    print('  CITATION   : a BACKTICKED 7-12 character lowercase hex run')
    print('  POPULATION : the %d REWRITE + %d GENERATED + the REPORT-ONLY logs'
          % (len(REWRITE), len(GENERATED)))
    print('  STATE      : reachability from origin/main, never object existence')
    print()
    rows, totals = [], {'ON-MAIN': 0, 'ORPHAN': 0, 'ABSENT': 0}
    fixable, unfixable = [], []
    groups = ([(r, 'REWRITE') for r in REWRITE]
              + [(g, 'GENERATED') for g in GENERATED]
              + [(p, 'REPORT-ONLY') for p in report_only_paths()])
    for rel, cls in groups:
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            rows.append((rel, cls, 'COULD NOT READ -- not a file here',
                         0, 0, 0, 0))
            continue
        try:
            src = io.open(path, encoding='utf-8', errors='replace').read()
        except Exception as e:                                 # noqa: BLE001
            rows.append((rel, cls, 'COULD NOT READ -- %s' % e, 0, 0, 0, 0))
            continue
        seen, c = set(), {'ON-MAIN': 0, 'ORPHAN': 0, 'ABSENT': 0}
        for m in TOKEN.finditer(src):
            t = m.group(1)
            if t in seen or not is_citation(t):
                continue
            seen.add(t)
            s = census_state(t, on_main, local)
            c[s] += 1
            if s == 'ORPHAN':
                fixable.append((rel, cls, t))
            elif s == 'ABSENT':
                unfixable.append((rel, cls, t))
        for k in totals:
            totals[k] += c[k]
        note = ''
        if cls == 'REWRITE' and held is not None and rel in held:
            note = 'held by another session -- PROPOSE only'
        elif cls == 'GENERATED':
            note = 'never patched -- regenerate'
        elif cls == 'REPORT-ONLY':
            note = 'never rewritten -- append-only log'
        rows.append((rel, cls, note, len(seen),
                     c['ON-MAIN'], c['ORPHAN'], c['ABSENT']))

    print('%-42s %-12s %5s %7s %6s %6s' % ('document', 'class', 'cites',
                                           'ON-MAIN', 'ORPH', 'ABSENT'))
    for rel, cls, note, n, a, o, b in rows:
        print('%-42s %-12s %5s %7s %6s %6s' % (rel[:42], cls, n, a, o, b))
        if note:
            print('%-42s   %s' % ('', note))
    dead = totals['ORPHAN'] + totals['ABSENT']
    tot = dead + totals['ON-MAIN']
    print()
    print('  %d DEAD of %d citations in the population (%.1f%%)'
          % (dead, tot, (100.0 * dead / tot) if tot else 0.0))
    print('    ON-MAIN %d   ORPHAN %d   ABSENT %d'
          % (totals['ON-MAIN'], totals['ORPHAN'], totals['ABSENT']))
    print()
    print('  WHAT THIS TOOL CAN FIX AND WHAT IT CANNOT:')
    print('    FIXABLE IN PRINCIPLE   %d  ORPHAN -- the commit is still in '
          'this clone, so a' % len(fixable))
    print('                              rewrite map COULD name it. It will '
          'only do so if the')
    print('                              rewrite that orphaned it happens '
          'again; these predate the')
    print('                              post-rewrite wiring and their maps '
          'expired with the reflog.')
    print('    NOT FIXABLE BY ANY MAP %d  ABSENT -- not an object in this '
          'clone at all. Created' % len(unfixable))
    print('                              and orphaned in another clone, never '
          'fetchable. No map will')
    print('                              ever name it, from here or anywhere.')
    print('    SO THE HONEST FIGURE FOR *THIS TOOL* IS %d of %d, and the other'
          ' %d need a' % (len(fixable), dead, len(unfixable)))
    print('    subject match or a human, which is why the batch-11 residual '
          'table exists.')
    return 0


ABSENT_REGISTER = 'docs/citation-absent-register.json'


def other_clone_gitdirs():
    """Sibling clones on this machine, DERIVED rather than listed.

    CLAUDE.md's own correction is the precedent: that file named four clones
    for weeks after a fifth existed and was pushing commits, and the fix was to
    COUNT THE DIRECTORIES. So this globs for a sibling holding a .git and
    carries no roster.
    """
    import glob
    here = os.path.abspath(REPO)
    parent = os.path.dirname(here)
    out = []
    for d in sorted(glob.glob(os.path.join(parent, '*'))):
        if os.path.abspath(d) == here:
            continue
        g = os.path.join(d, '.git')
        if os.path.isdir(g):
            out.append(g)
    return out


def cmd_register_absent():
    """Record every PERMANENTLY ABSENT citation, with the cause ESTABLISHED.

    WHY A SEPARATE RECORD AND NOT A `resolved` FIELD. An ABSENT citation is not
    a pointer waiting to be repaired: the commit is not an object in this clone,
    so there is nothing for `--post-rewrite` to match and nothing a subject
    search can confirm. Writing it anywhere that reads as "handled" would be
    this tool's own defect one level up -- a record that looks precise and is
    not.

    THE CAUSE IS TESTED, NOT ASSUMED. For each one this asks every sibling
    clone on the machine whether IT holds the object. That is the only test
    that separates "orphaned in a clone that still has it" -- recoverable, by
    asking that clone -- from "orphaned in a clone that has since dropped it"
    -- permanently gone. The answer is stored per citation so nobody re-derives
    it.

    IT NEVER WRITES `resolved`. The only states are PERMANENTLY-ABSENT and
    RECOVERABLE-FROM-CLONE.
    """
    on_main, local = census_universe()
    gitdirs = other_clone_gitdirs()
    groups = ([(r, 'REWRITE') for r in REWRITE]
              + [(g, 'GENERATED') for g in GENERATED]
              + [(p, 'REPORT-ONLY') for p in report_only_paths()])
    recs, unread = [], []
    for rel, cls in groups:
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            unread.append('%s -- not a file in this clone' % rel)
            continue
        try:
            src = io.open(path, encoding='utf-8', errors='replace').read()
        except Exception as e:                             # noqa: BLE001
            unread.append('%s -- %s' % (rel, e))
            continue
        seen = set()
        for m in TOKEN.finditer(src):
            t = m.group(1)
            if t in seen or not is_citation(t):
                continue
            seen.add(t)
            if census_state(t, on_main, local) != 'ABSENT':
                continue
            where = None
            for g in gitdirs:
                try:
                    r = subprocess.run(['git', '--git-dir', g, 'cat-file',
                                        '-e', t], capture_output=True,
                                       timeout=20)
                    if r.returncode == 0:
                        where = g
                        break
                except Exception:                          # noqa: BLE001
                    continue
            recs.append({
                'citation': t,
                'document': rel,
                'document_class': cls,
                'state': ('RECOVERABLE-FROM-CLONE' if where
                          else 'PERMANENTLY-ABSENT'),
                'recoverable_from': where,
                'cause': (('the object is in %s and can be fetched from there'
                           % where) if where else
                          ('created and orphaned in a clone that no longer '
                           'holds the object -- not reachable from '
                           'origin/main, not an object in this clone, and not '
                           'an object in any sibling clone on this machine. '
                           'No rewrite map and no fetch can name it.')),
            })
    recs.sort(key=lambda r: (r['document'], r['citation']))
    perm = [r for r in recs if r['state'] == 'PERMANENTLY-ABSENT']
    payload = {
        '_what_this_is':
            'Citations in the tracking documents whose commit is NOT AN OBJECT '
            'in this clone. Each carries its cause TESTED against every '
            'sibling clone on this machine. These are not pending repairs -- '
            'there is nothing for a rewrite map to match.',
        '_what_it_does_NOT_claim':
            'That the work the citation refers to never landed. It almost '
            'always did, under a different sha. This records that the POINTER '
            'is unresolvable, not that the fix is missing.',
        '_never_written_here': 'resolved',
        'measured_at_head': (git('rev-parse', '--short', 'HEAD') or '?'),
        'criteria_version': CRITERIA_VERSION,
        'sibling_clones_queried': gitdirs,
        'counts': {'absent_total': len(recs),
                   'permanently_absent': len(perm),
                   'recoverable_from_a_sibling_clone': len(recs) - len(perm)},
        'documents_not_read': unread,
        'records': recs,
    }
    out = os.path.join(REPO, ABSENT_REGISTER)
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        io.open(out, 'w', encoding='utf-8', newline='').write(
            json.dumps(payload, indent=1) + chr(10))
    except Exception as e:                                 # noqa: BLE001
        print('COULD NOT WRITE %s: %s' % (ABSENT_REGISTER, e))
        return EXIT_COULD_NOT_RUN
    print('ABSENT CITATION REGISTER -- %s at HEAD %s'
          % (ABSENT_REGISTER, payload['measured_at_head']))
    print('  sibling clones queried      : %d' % len(gitdirs))
    for g in gitdirs:
        print('      %s' % g)
    print('  absent citations recorded   : %d' % len(recs))
    print('  PERMANENTLY ABSENT          : %d  (no clone on this machine '
          'holds the object)' % len(perm))
    print('  recoverable from a sibling  : %d' % (len(recs) - len(perm)))
    if unread:
        print('  COULD NOT READ, so NOT examined:')
        for u in unread:
            print('      %s' % u)
    import collections as _c
    for doc, n in _c.Counter(r['document'] for r in recs).most_common():
        print('      %-44s %d' % (doc, n))
    print('  THE WORD `resolved` IS NEVER WRITTEN IN THIS FILE. The only '
          'states are')
    print('  PERMANENTLY-ABSENT and RECOVERABLE-FROM-CLONE.')
    return 0


def run_fixtures(verbose=False):
    """Hand-built cases, locked before the tool was pointed at a real document.

    Discipline 1: the criteria are fixed against sources whose right answer is
    known, so a flattering result on the real tree cannot be what sets them.
    """
    A = 'a' * 40
    B = 'b' * 40
    cases = [
        ('a cited token that the map moved is substituted',
         'fixed in `%s` today' % A[:8], {A: B},
         'fixed in `%s` today' % B[:8]),
        ('the substitution keeps the ORIGINAL TOKEN WIDTH',
         'see `%s`' % A[:12], {A: B},
         'see `%s`' % B[:12]),
        ('a token the map does not mention is untouched',
         'see `%s`' % ('c' * 9), {A: B},
         'see `%s`' % ('c' * 9)),
        ('a rewrite that did not move the commit changes nothing',
         'see `%s`' % A[:8], {A: A},
         'see `%s`' % A[:8]),
        ('an UNBACKTICKED hex run is not a candidate',
         'see %s plain' % A[:8], {A: B},
         'see %s plain' % A[:8]),
        ('a 6-character run is too short to be a sha',
         'see `%s`' % A[:6], {A: B},
         'see `%s`' % A[:6]),
        ('a 13-character run is not a sha citation either',
         'see `%s`' % A[:13], {A: B},
         'see `%s`' % A[:13]),
        ('an UPPERCASE hex run is not a candidate -- git prints lower case',
         'see `%s`' % A[:8].upper(), {A: B},
         'see `%s`' % A[:8].upper()),
        ('a decimal figure that is also valid hex is left alone when the map '
         'does not name it',
         'row `38471260` of the table', {A: B},
         'row `38471260` of the table'),
        ('every occurrence of one moved token is substituted',
         '`%s` and again `%s`' % (A[:8], A[:8]), {A: B},
         '`%s` and again `%s`' % (B[:8], B[:8])),
        ('an EMPTY map substitutes nothing',
         'fixed in `%s`' % A[:8], {},
         'fixed in `%s`' % A[:8]),
        ('a token must be a prefix of OLD, never the reverse -- a 40-char old '
         'sha in the text is not matched by a 8-char map key',
         'see `%s`' % ('d' * 12), {('d' * 6): B},
         'see `%s`' % ('d' * 12)),
    ]
    bad = []
    for name, src, mapping, want in cases:
        got = apply_subs(src, substitutions(src, mapping))
        if got != want:
            bad.append('%s\n       want %r\n       got  %r' % (name, want, got))
        elif verbose:
            print('  ok   %s' % name)

    # ── ONE ARM PER FALSE-POSITIVE SHAPE OF is_citation (2026-10-07, cc) ────
    # The twelve cases above lock the SUBSTITUTION criteria. They do not touch
    # is_citation, which is the function that decides what counts as a citation
    # at all -- and it is the one that was wrong. Until 2026-10-07 `--census`
    # filtered these shapes inline in its own loop and `--register-absent` did
    # not, so the WRITING mode recorded `1234abcd` from this tool's own comment
    # as an absent citation and reported a count 11 too high.
    #
    # The shared rule now exists. What was still missing is an arm per shape:
    # a rule with no arm is a rule that can be edited back out without anything
    # failing, which is exactly how the two modes diverged in the first place.
    # The ANTI-arms are the point -- every one of these returned True before.
    cases2 = [
        # ── must NOT be treated as citations ──
        ('an all-digit run that is valid hex is not a citation', '38471260', False),
        ('a 12-hex register RECORD ID is not a citation', 'a1b2c3d4e5f6', False),
        ('the documentation literal 1234abcd is not a citation', '1234abcd', False),
        ('the documentation literal deadbeef is not a citation', 'deadbeef', False),
        ('the 7-char literal abcdef0 is not a citation', 'abcdef0', False),
        ('the all-zero literal 0000000 is not a citation', '0000000', False),
        ('the 12-char literal deadbeefcafe is not a citation', 'deadbeefcafe', False),
        ('an empty token is not a citation', '', False),
        ('None is not a citation', None, False),
        # A literal in the exclusion list is excluded by NAME and must stay
        # excluded when its case changes -- the register is lower-cased hex.
        ('an UPPERCASE documentation literal is still not a citation',
         '1234ABCD', False),
        # ── must still BE treated as citations ──
        ('an ordinary 8-char sha prefix IS a citation', 'a27cd83b', True),
        ('a 7-char sha prefix IS a citation', 'a27cd83', True),
        ('a full 40-char sha IS a citation', 'a' * 40, True),
        ('an 11-char prefix IS a citation -- only 12 is the record-id width',
         'a27cd83b23e', True),
        ('a 13-char prefix IS a citation -- the 12 exclusion is exact, not >=',
         'a27cd83b23e34', True),
        # The shape that makes the 12-char exclusion a real trade and not a
        # free win. Stated as an arm so nobody "fixes" it by accident.
        ('a REAL 12-char sha prefix is excluded TOO, and that is the known cost',
         'a27cd83b23e3', False),
    ]
    for name, tok, want in cases2:
        got = bool(is_citation(tok))
        if got != want:
            bad.append('%s\n       want %r\n       got  %r' % (name, want, got))
        elif verbose:
            print('  ok   %s' % name)
    return bad, len(cases) + len(cases2)


def classify(path):
    """REWRITE, GENERATED, REPORT-ONLY, or None for a path not covered."""
    p = path.replace('\\', '/')
    for g in REPORT_ONLY_GLOBS:
        if os.path.basename(p).startswith(g):
            return 'REPORT-ONLY'
    if p in REWRITE:
        return 'REWRITE'
    if p in GENERATED:
        return 'GENERATED'
    return None


def generated_citing(mapping):
    """Generated documents that cite a moved SHA -- REGENERATE, do not patch.

    Reported rather than silently skipped: a stale SHA in a generated file is
    a real signal that its SOURCE is stale, and that is the actionable fact.
    """
    out = []
    for rel in GENERATED:
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            continue
        try:
            src = io.open(path, encoding='utf-8').read()
        except Exception:                                      # noqa: BLE001
            continue
        subs = substitutions(src, mapping)
        if subs:
            out.append((rel, subs))
    return out


def report_only_paths():
    out = []
    for fn in sorted(os.listdir(REPO)):
        if any(fn.startswith(g) for g in REPORT_ONLY_GLOBS):
            out.append(fn)
    return out


def main(argv):
    ap = argparse.ArgumentParser(add_help=True,
                                 description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true',
                    help='report what a rewrite map would change; write nothing')
    ap.add_argument('--post-rewrite', action='store_true',
                    help="read git's old->new map on stdin and re-seat")
    ap.add_argument('--fixtures', action='store_true',
                    help='run the criteria lock alone -- reads no document')
    ap.add_argument('--census', action='store_true',
                    help='count citations by state, with the definitions '
                         'stated; writes nothing')
    ap.add_argument('--register-absent', action='store_true',
                    help='record every permanently-absent citation with its '
                         'cause TESTED against every sibling clone')
    a = ap.parse_args(argv)

    bad, n = run_fixtures(verbose=a.fixtures)
    if bad:
        print('CRITERIA LOCK FAILED -- %d of %d fixtures misclassified.'
              % (len(bad), n))
        for b in bad:
            print('  ! %s' % b)
        print('\nNOTHING REAL WAS READ OR WRITTEN. A tool that rewrites '
              'standing documents does\nnot get to skip its own lock.')
        return EXIT_COULD_NOT_RUN
    if a.fixtures:
        print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
              'sources only (criteria %s)' % (n, n, CRITERIA_VERSION))
        return 0

    if a.census:
        return cmd_census()

    if a.register_absent:
        return cmd_register_absent()

    if a.post_rewrite:
        try:
            raw = sys.stdin.read()
        except Exception as e:                                 # noqa: BLE001
            print('doc-sha-reseat: could not read the rewrite map (%s). '
                  'Nothing was changed; run --check by hand if a citation '
                  'looks dead.' % e)
            return 0
        mapping = parse_map(raw)
    elif a.check:
        # --check has no map of its own. It answers the question a reader
        # actually has -- "would a re-seat change anything right now" -- which
        # with no rewrite in flight is honestly NO, and it says so rather than
        # inventing a map from the reflog and presenting the guess as a result.
        mapping = {}
    else:
        ap.print_help()
        return EXIT_COULD_NOT_RUN

    held = claimed_elsewhere()
    if held is None and not a.check:
        print('doc-sha-reseat: THE CLAIM RECORDS COULD NOT BE READ, so this '
              'cannot tell which\n  documents another session is editing right '
              'now. Nothing was written. Every\n  substitution below is a '
              'PROPOSAL.')
        held = set(REWRITE)

    print('DOC SHA RE-SEAT -- criteria %s, %d commit(s) in the rewrite map'
          % (CRITERIA_VERSION, len(mapping)))

    if not mapping:
        print('\nNO REWRITE MAP, SO NOTHING WAS COMPARED AND NOTHING WAS '
              'CHANGED.\nThis is the normal answer outside a rebase or an '
              '--amend: `post-rewrite` is\nwhere the map exists, and without '
              'it there is no old->new pair to apply. It is\nNOT a statement '
              'that every citation resolves -- that is a different question,\n'
              'and `tools/doc_sha_reseat.py` deliberately does not answer it '
              'from a guess.')
        print('\nREPORT-ONLY, never rewritten (append-only logs): %s'
              % ', '.join(report_only_paths()))
        return 0

    wrote, proposed, missing = [], [], []
    for rel in REWRITE:
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            missing.append(rel)
            continue
        try:
            src = io.open(path, encoding='utf-8').read()
        except Exception as e:                                 # noqa: BLE001
            missing.append('%s (%s)' % (rel, e))
            continue
        subs = substitutions(src, mapping)
        if not subs:
            continue
        if a.check or rel in held:
            proposed.append((rel, subs, rel in held))
            continue
        try:
            io.open(path, 'w', encoding='utf-8', newline='').write(
                apply_subs(src, subs))
        except Exception as e:                                 # noqa: BLE001
            proposed.append((rel, subs, False))
            print('  ! %s needed %d substitution(s) and COULD NOT BE WRITTEN '
                  '(%s)' % (rel, len(subs), e))
            continue
        wrote.append((rel, subs))

    if missing:
        # PR 1.11. A document in the set that could not be read is a third
        # state, not a clean one.
        print('\nCOULD NOT READ these documents, so they were NOT examined:')
        for m in missing:
            print('    %s' % m)

    for rel, subs in wrote:
        print('\nRE-SEATED %s -- %d citation(s), from git\'s own rewrite map:'
              % (rel, len(subs)))
        for old, new in subs:
            print('    %s -> %s' % (old, new))
    if wrote:
        print('\n  These files are MODIFIED AND NOT STAGED. A hook does not '
              'commit on your\n  behalf -- read the diff before it goes '
              'anywhere.')

    for rel, subs, is_held in proposed:
        why = ('another session holds it under a LIVE CLAIM'
               if is_held else 'this is --check')
        print('\nPROPOSED for %s -- %d citation(s), NOT WRITTEN because %s:'
              % (rel, len(subs), why))
        for old, new in subs:
            print('    %s -> %s' % (old, new))

    gen = generated_citing(mapping)
    for rel, subs in gen:
        print('\nGENERATED, so NOT PATCHED -- %s cites %d moved SHA(s). '
              'REGENERATE it;\n  patching the output would be discarded by '
              'the next run and would read as fixed\n  in the meantime. Its '
              'stale SHA means its SOURCE is stale:' % (rel, len(subs)))
        for old, new in subs:
            print('    %s -> %s' % (old, new))

    if not wrote and not proposed and not gen:
        print('\nThe map named %d rewritten commit(s) and NONE of them is '
              'cited in the\ntracking documents. Nothing to do.' % len(mapping))

    print('\nREPORT-ONLY, never rewritten (append-only logs): %s'
          % ', '.join(report_only_paths()))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
