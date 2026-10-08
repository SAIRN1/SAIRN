# OWNER: cody
"""tools/external_file_index_audit.py -- audit docs/external-files-index.json
against itself and against the repo. The INDEX is the subject here, not the tree.

── WHY THIS EXISTS, AND IT FOUND ITS OWN DEFECT ON THE FIRST RUN ────────────
`docs/external-files-index.json` registers everything cody keeps outside git so
a figure quoted from one of those directories can still be traced after the
directory is gone. It declares itself DERIVED, with the regeneration command in
its own header:

    "Regenerate: python tools/scratch-archive/inventory2.py, then
     scratchpad/b26/build_index.py"

`inventory2.py` is committed. **`build_index.py` is not, and the index does not
list it either** -- it exists in exactly one place, a `%TEMP%` scratchpad the
index itself classifies as *"HIGH -- cleared without warning"*. So the generator
excluded itself from its own population, and the `_derived_not_hand_written`
claim stops being true on the day that directory clears, silently, with the
header still asserting it. That is the defect this tool was written to catch and
it is arm GENERATOR below.

── WHAT IT IS NOT, AND WHOSE TOOL IT IS NOT ─────────────────────────────────
This is NOT `tools/external_file_index_check.py`, which is **cc's** and runs the
other direction: cc's gate asks *"is there a file in a declared external
directory that is neither git-tracked nor indexed"* -- it audits the TREE against
the index and refuses a push. This one asks *"is the index internally consistent
and are the things it points at still there"* -- it audits the INDEX, writes
nothing, and gates nothing. Two tools, opposite subjects, and neither covers the
other's case. If cc's lands, both should run.

It also does NOT re-derive the inventory. It cannot tell a correct 64 from a
wrong 64; it can only tell a 64 that disagrees with the list beside it.

── EXIT CODES ───────────────────────────────────────────────────────────────
  0  every arm clean
  1  at least one FINDING -- stated per arm, with the count and the names
  2  COULD NOT RUN -- the index is missing, unparseable, or git is unavailable.
     Never folded into 0. "Could not tell" is a third state (PR 1.11).
"""

import argparse
import json
import os
import re
import subprocess
import sys

INDEX = os.path.join('docs', 'external-files-index.json')
CRITERIA_VERSION = '2026-10-08.1'


def _tracked(repo='.'):
    """Every git-tracked path, as a set of forward-slash relative paths.

    Raises on failure rather than returning an empty set: an empty set would
    make every COMMITTED claim below look like a finding, which is the same
    class of wrong answer as a silent pass.
    """
    out = subprocess.run(['git', '-C', repo, 'ls-files'],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError('git ls-files exited %d: %s'
                           % (out.returncode, out.stderr.strip()[:200]))
    paths = [p.strip() for p in out.stdout.splitlines() if p.strip()]
    if not paths:
        raise RuntimeError('git ls-files returned nothing -- not a repo?')
    return set(paths)


# A path-shaped token ending in a script extension. Deliberately loose: the
# header is prose, and the point is to find every script it NAMES, not to parse
# a grammar it does not have.
_SCRIPT_RE = re.compile(r'[A-Za-z0-9_./\\-]+\.(?:py|ps1|sh|js)\b')


def named_scripts(text):
    """Script paths named in the regeneration prose, in order, de-duplicated."""
    seen, out = set(), []
    for m in _SCRIPT_RE.finditer(text or ''):
        p = m.group(0).replace('\\', '/')
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def audit(index_path=INDEX, repo='.'):
    """Return (findings, notes, data). findings is a list of strings."""
    with open(index_path, 'r', encoding='utf-8') as fh:
        d = json.load(fh)
    tracked = _tracked(repo)
    findings, notes = [], []

    scripts = d.get('scripts') or []
    dirs = d.get('directories') or []
    loose = d.get('loose_home_files') or []
    measured = d.get('_measured') or {}

    # ── arm COUNTS ──────────────────────────────────────────────────────────
    # A headline figure beside the list it is drawn from can disagree with it,
    # and a reader quoting the figure has no way to tell. Convention 28: every
    # figure carries its denominator -- this is the denominator being checkable.
    claimed = measured.get('scripts_authored_outside_git')
    if claimed is None:
        findings.append('COUNTS: _measured.scripts_authored_outside_git is '
                        'ABSENT, so the headline figure cannot be checked '
                        'against the %d-entry scripts list' % len(scripts))
    elif claimed != len(scripts):
        findings.append('COUNTS: _measured.scripts_authored_outside_git = %r '
                        'but the scripts list holds %d'
                        % (claimed, len(scripts)))
    else:
        notes.append('COUNTS: headline %d == len(scripts) %d'
                     % (claimed, len(scripts)))

    committed_rows = [s for s in scripts
                      if 'COMMITTED' in str(s.get('status', '')).upper()]
    claimed_c = measured.get('of_those_committed_to_the_repo')
    if claimed_c is not None and claimed_c != len(committed_rows):
        findings.append('COUNTS: _measured.of_those_committed_to_the_repo = %r '
                        'but %d script rows carry a COMMITTED status'
                        % (claimed_c, len(committed_rows)))
    else:
        notes.append('COUNTS: committed claim %r vs %d COMMITTED rows'
                     % (claimed_c, len(committed_rows)))

    # ── arm GENERATOR ───────────────────────────────────────────────────────
    # The arm this tool exists for. A file that says "regenerate me with X" and
    # does not say where X lives is hand-maintained the moment X is gone.
    prose = str(d.get('_derived_not_hand_written', ''))
    named = named_scripts(prose)
    if not named:
        findings.append('GENERATOR: _derived_not_hand_written names NO script, '
                        'so the "derived" claim has no regeneration path at all')
    index_names = {s.get('name') for s in scripts}
    for p in named:
        base = p.rsplit('/', 1)[-1]
        if p in tracked:
            notes.append('GENERATOR: %s is git-tracked' % p)
        elif base in index_names:
            notes.append('GENERATOR: %s is not tracked but IS registered in '
                         'this index, so it can be located' % p)
        else:
            findings.append(
                'GENERATOR: %s is named as the regeneration path and is '
                'NEITHER git-tracked NOR registered in this index -- the '
                '"derived, not hand-written" claim becomes false and silent '
                'the moment its directory clears' % p)

    # ── arm COMMITTED ───────────────────────────────────────────────────────
    # A row that says COMMITTED and is not in the tree is the inverse of the
    # above: the index asserting a safety that is not there.
    bad_c = []
    for s in committed_rows:
        where = str(s.get('committed_to') or s.get('repo_path') or '')
        cand = [where.replace('\\', '/')] if where else []
        cand.append('tools/scratch-archive/%s' % s.get('name'))
        if not any(c in tracked for c in cand if c):
            bad_c.append(s.get('name'))
    if bad_c:
        findings.append('COMMITTED: %d row(s) claim a COMMITTED status but no '
                        'matching tracked path exists: %s'
                        % (len(bad_c), ', '.join(sorted(map(str, bad_c)))))
    else:
        notes.append('COMMITTED: all %d COMMITTED rows resolve to a tracked '
                     'path' % len(committed_rows))

    # ── arm LIVENESS ────────────────────────────────────────────────────────
    # NOT a finding by itself -- these directories are registered BECAUSE they
    # are expected to vanish. What is reported is how many REGISTERED-ONLY
    # script rows have become unrecoverable, because that is the number the
    # index exists to make visible and it is the one nobody would compute.
    gone_dirs = [x.get('path') for x in dirs
                 if x.get('path') and not os.path.exists(x['path'])]
    gone_loose = [x.get('path') for x in loose
                  if x.get('path') and not os.path.exists(x['path'])]
    unrecoverable = 0
    for s in scripts:
        if 'COMMITTED' in str(s.get('status', '')).upper():
            continue
        newest = str(s.get('newest_copy') or '')
        if not newest:
            continue
        hit = any(newest.replace('\\', '/').startswith(
            os.path.basename(str(g)).replace('\\', '/')) for g in gone_dirs)
        if hit:
            unrecoverable += 1
    notes.append('LIVENESS: %d of %d directories gone, %d of %d loose files '
                 'gone, %d REGISTERED-ONLY script row(s) now unrecoverable'
                 % (len(gone_dirs), len(dirs), len(gone_loose), len(loose),
                    unrecoverable))

    data = {'scripts': len(scripts), 'directories': len(dirs),
            'loose': len(loose), 'named_generators': named,
            'gone_dirs': gone_dirs, 'unrecoverable': unrecoverable}
    return findings, notes, data


def report(index_path, as_json):
    if not os.path.isfile(index_path):
        print('COULD NOT RUN: %s does not exist. This audit says NOTHING about '
              'the external files -- it did not run.' % index_path)
        return 2
    try:
        findings, notes, data = audit(index_path)
    except (ValueError, RuntimeError, OSError) as exc:
        print('COULD NOT RUN: %s' % exc)
        print('This audit says NOTHING about the external files -- it did not '
              'run. That is not a pass.')
        return 2

    if as_json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'findings': findings,
                          'notes': notes, 'data': data}, indent=1))
        return 1 if findings else 0

    print('EXTERNAL FILE INDEX AUDIT -- %s (criteria %s)'
          % (index_path, CRITERIA_VERSION))
    print('  subject: the INDEX. cc\'s external_file_index_check.py audits the '
          'TREE; this does not replace it.')
    print('  population: %d scripts, %d directories, %d loose files'
          % (data['scripts'], data['directories'], data['loose']))
    for n in notes:
        print('  ok   %s' % n)
    for f in findings:
        print('  FINDING  %s' % f)
    print('%d FINDING(S)' % len(findings) if findings else 'CLEAN')
    return 1 if findings else 0


# ── SELFTEST ────────────────────────────────────────────────────────────────
# Fixtures carry the shape the real file carries, including the parts that look
# like noise, per the fixture convention routed on 2026-10-06: a fixture tidier
# than production tests a system that does not exist.
def selftest():
    import tempfile
    ok = {'v': True}
    n = {'armed': 0, 'neg': 0}

    def arm(label, cond, detail=''):
        n['armed'] += 1
        if label.startswith('NEGATIVE'):
            n['neg'] += 1
        print(('  ok   ' if cond else '  FAIL ') + label
              + ('' if cond else '\n         %s' % str(detail)[:300]))
        if not cond:
            ok['v'] = False

    print('EXTERNAL FILE INDEX AUDIT -- selftest (criteria %s)'
          % CRITERIA_VERSION)

    def write(obj):
        fh = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                         encoding='utf-8')
        json.dump(obj, fh)
        fh.close()
        return fh.name

    base = {
        '_what_this_is': 'fixture',
        '_derived_not_hand_written': 'Regenerate: python '
            'tools/scratch-archive/inventory2.py, then scratchpad/b26/'
            'build_index.py. A hand-maintained index drifts.',
        '_measured': {'scripts_authored_outside_git': 2,
                      'of_those_cited_in_a_committed_doc': 1,
                      'of_those_committed_to_the_repo': 1},
        'directories': [{'path': os.path.join(tempfile.gettempdir(),
                                              'no-such-dir-xyz'),
                         'role': 'scratchpad', 'volatility': 'HIGH'}],
        'loose_home_files': [],
        'scripts': [
            {'name': 'inventory2.py',
             'newest_copy': 'no-such-dir-xyz/scratchpad/inventory2.py',
             'bytes': 10, 'sha256_16': 'aa', 'copies_in_n_sessions': 1,
             'cited_in_committed_docs': ['docs/x.md'],
             'status': 'COMMITTED to tools/scratch-archive/'},
            {'name': 'abl_r1.sh',
             'newest_copy': 'no-such-dir-xyz/scratchpad/abl_r1.sh',
             'bytes': 195, 'sha256_16': 'bb', 'copies_in_n_sessions': 1,
             'cited_in_committed_docs': [],
             'status': 'REGISTERED ONLY -- lives in %TEMP%'},
        ],
    }

    # The real defect, reproduced: build_index.py is named as the regeneration
    # path, is not tracked, and is not in the scripts list.
    p = write(base)
    f, notes, _ = audit(p)
    gen = [x for x in f if x.startswith('GENERATOR')]
    arm('GENERATOR arm fires on a named regeneration script that is neither '
        'tracked nor registered -- the real 2026-10-08 defect', len(gen) == 1,
        f)
    arm('...and it names the script rather than reporting a count',
        gen and 'build_index.py' in gen[0], gen)
    arm('...and the TRACKED generator in the same prose string is NOT flagged, '
        'so the arm is not answering true to everything',
        gen and 'inventory2.py' not in gen[0],
        [x for x in notes if 'inventory2' in x])
    os.unlink(p)

    # NEGATIVE: register the generator and the arm must go quiet.
    fixed = json.loads(json.dumps(base))
    fixed['scripts'].append(
        {'name': 'build_index.py',
         'newest_copy': 'no-such-dir-xyz/scratchpad/b26/build_index.py',
         'bytes': 1, 'sha256_16': 'cc', 'copies_in_n_sessions': 1,
         'cited_in_committed_docs': [], 'status': 'REGISTERED ONLY'})
    fixed['_measured']['scripts_authored_outside_git'] = 3
    p = write(fixed)
    f, _, _ = audit(p)
    arm('NEGATIVE: once the generator is registered, GENERATOR goes quiet -- so '
        'the arm clears when the defect is fixed and is not a permanent red',
        not [x for x in f if x.startswith('GENERATOR')], f)
    os.unlink(p)

    # COUNTS, both directions.
    skew = json.loads(json.dumps(fixed))
    skew['_measured']['scripts_authored_outside_git'] = 99
    p = write(skew)
    f, _, _ = audit(p)
    arm('COUNTS fires when the headline figure disagrees with the list beside it',
        any(x.startswith('COUNTS') and '99' in x for x in f), f)
    os.unlink(p)

    missing = json.loads(json.dumps(fixed))
    del missing['_measured']['scripts_authored_outside_git']
    p = write(missing)
    f, _, _ = audit(p)
    arm('COUNTS fires on an ABSENT headline figure rather than treating a '
        'missing key as agreement',
        any(x.startswith('COUNTS') and 'ABSENT' in x for x in f), f)
    os.unlink(p)

    # COMMITTED, both directions.
    liar = json.loads(json.dumps(fixed))
    liar['scripts'][0]['name'] = 'never_committed_xyz.py'
    p = write(liar)
    f, _, _ = audit(p)
    arm('COMMITTED fires on a row claiming COMMITTED with no tracked path',
        any(x.startswith('COMMITTED') for x in f), f)
    os.unlink(p)

    p = write(fixed)
    f, _, _ = audit(p)
    arm('NEGATIVE: and the real tracked inventory2.py does NOT trip COMMITTED, '
        'so that arm is reading the tree and not guessing',
        not [x for x in f if x.startswith('COMMITTED')], f)
    os.unlink(p)

    # No regeneration prose at all.
    bare = json.loads(json.dumps(fixed))
    bare['_derived_not_hand_written'] = 'This index is derived.'
    p = write(bare)
    f, _, _ = audit(p)
    arm('GENERATOR fires when the "derived" claim names no script at all',
        any('names NO script' in x for x in f), f)
    os.unlink(p)

    # COULD NOT RUN is a third state, in both of its forms.
    arm('NEGATIVE: a MISSING index exits 2 COULD NOT RUN, never 0',
        report(os.path.join(tempfile.gettempdir(), 'no-such-index.json'),
               False) == 2)
    bad = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                      encoding='utf-8')
    bad.write('{not json')
    bad.close()
    arm('NEGATIVE: an UNPARSEABLE index exits 2 COULD NOT RUN, never 0',
        report(bad.name, False) == 2)
    os.unlink(bad.name)

    # named_scripts: the prose parser, in both directions.
    arm('named_scripts finds both scripts in the real header prose',
        named_scripts(base['_derived_not_hand_written'])
        == ['tools/scratch-archive/inventory2.py',
            'scratchpad/b26/build_index.py'],
        named_scripts(base['_derived_not_hand_written']))
    arm('NEGATIVE: named_scripts finds nothing in prose with no script path',
        named_scripts('Regenerate by hand. See the handoff.') == [])

    print('  criteria lock: %d arms, %d of them negative (criteria %s)'
          % (n['armed'], n['neg'], CRITERIA_VERSION))
    return ok['v']


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--index', default=INDEX)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest:
        return 0 if selftest() else 1
    return report(a.index, a.json)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
