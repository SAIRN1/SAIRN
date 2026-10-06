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
    return bad, len(cases)


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
