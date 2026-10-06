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

  OWNER_LINE   the file carries `# OWNER: x`. AUTHORITATIVE -- nothing else is.
  LAST_CLAIM   derived. The most recent session to name it in a FILES list.
  CONTESTED    derived, and more than one session has claimed it. The last
               claimer wins the `owner` field and the others are listed, because
               `push_retry.py` resolves to fourth while hank has edited it too
               and a single name would hide that.
  NONE         no OWNER line and no claim has ever named it. **UNKNOWN, NOT
               UNOWNED** -- the two are opposite findings and must not print the
               same.

── WHAT IT CANNOT DO, NAMED RATHER THAN DISCOVERED ─────────────────────────
  * It cannot see a tool somebody built WITHOUT claiming it. That is the NONE
    bucket and it is the largest one.
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

CRITERIA_VERSION = '2026-10-06.1'
OUT = os.path.join('docs', 'tool-owner-map.json')
MAX_CLAIM_COMMITS = 6000

# `# OWNER: name` in the first few lines. Anchored at line start so a mention
# inside a docstring does not read as a declaration.
OWNER_LINE = re.compile(r'^#\s*OWNER:\s*([A-Za-z0-9_]+)\s*$', re.M)
CLAIM_SUBJ = re.compile(r'^chore\(claims\):\s+([A-Za-z0-9_]+)\s+claims\b')
FILES_IN_SUBJ = re.compile(r'FILES:\s*(.*)$')
TRACKED_EXT = ('.py', '.js', '.sh')


class CouldNotTell(Exception):
    pass


def tracked_tools():
    r = subprocess.run(['git', '-C', REPO, 'ls-files', 'tools/'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        raise CouldNotTell('git ls-files failed, so the population is unknown. '
                           'NOT an empty population.')
    out = [f.strip() for f in (r.stdout or '').split('\n')
           if f.strip().endswith(TRACKED_EXT)]
    if not out:
        raise CouldNotTell('tools/ holds no tracked .py/.js/.sh file -- the '
                           'layout moved and NOTHING was read.')
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


def build():
    paths = tracked_tools()
    lines = owner_lines(paths)
    hist, claim_commits, with_files = claim_history()
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
        else:
            rows[rel] = {'owner': None, 'basis': 'NONE', 'also_claimed_by': []}
    return rows, {'tools': len(paths), 'owner_line': len(lines),
                  'claim_commits_read': claim_commits,
                  'claim_commits_with_files': with_files,
                  'criteria': CRITERIA_VERSION}


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
    bad = []
    for subj, want, why in FIXTURES:
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
             'an INDENTED owner line is a comment in code, not a header')):
        m = OWNER_LINE.search(src)
        got = m.group(1) if m else None
        if got != want:
            bad.append('%s -- wanted %r got %r' % (why, want, got))
        elif verbose:
            print('  ok   %s' % why)
    return bad


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
    bad = run_fixtures(verbose=a.fixtures)
    if bad:
        print('\nCRITERIA LOCK FAILED -- %d of %d:' % (len(bad), len(FIXTURES) + 3))
        for b in bad:
            print('  ! %s' % b)
        print('\nNOTHING REAL WAS DERIVED. A misclassifying parser would assign '
              'every tool to\nwhoever released it last, which is worse than no '
              'map at all.')
        return EXIT_COULD_NOT_RUN
    print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
          'subjects only' % (len(FIXTURES) + 3, len(FIXTURES) + 3))
    if a.fixtures:
        return 0

    try:
        rows, meta = build()
    except CouldNotTell as exc:
        print('\nCOULD NOT RUN -- %s' % exc)
        return EXIT_COULD_NOT_RUN

    by = collections.Counter(v['basis'] for v in rows.values())
    print('  tracked tools                 %4d' % meta['tools'])
    print('  with an `# OWNER:` line       %4d   <- AUTHORITATIVE, the only '
          'basis that is not a guess' % meta['owner_line'])
    print('  derived LAST_CLAIM            %4d' % by.get('LAST_CLAIM', 0))
    print('  derived CONTESTED             %4d   (>1 session has claimed it)'
          % by.get('CONTESTED', 0))
    print('  NONE -- UNKNOWN, not unowned  %4d' % by.get('NONE', 0))
    print('  claim commits read            %4d, of which %d carry a FILES list'
          % (meta['claim_commits_read'], meta['claim_commits_with_files']))

    if a.ownerless:
        print('\nTOOLS WITH NO OWNER AT ALL -- no `# OWNER:` line and no claim '
              'has ever named them:')
        for rel in sorted(k for k, v in rows.items() if v['basis'] == 'NONE'):
            print('  %s' % rel)

    payload = {'_what_this_is': __doc__.split('\n')[0],
               '_basis_vocabulary': {
                   'OWNER_LINE': 'the file says so. Authoritative.',
                   'LAST_CLAIM': 'derived from the most recent claim commit.',
                   'CONTESTED': 'derived, and more than one session has claimed '
                                'it; `also_claimed_by` lists the others.',
                   'NONE': 'UNKNOWN, not unowned.'},
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
        ['%s -- no `# OWNER:` line and no claim has ever named it' % rel
         for rel in sorted(k for k, v in rows.items() if v['basis'] == 'NONE')],
        quiet=False,
        clean_line='\nCLEAN -- every tracked tool resolves to a session.')


if __name__ == '__main__':
    sys.exit(main())
