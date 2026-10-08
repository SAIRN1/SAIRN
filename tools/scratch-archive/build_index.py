# OWNER: cody
"""Item 6, THIRD pass -- write docs/external-files-index.json from the two raws.

Registers everything of cody's that lives OUTSIDE git: the non-empty session
scratchpads, the shared status registry, the Drive report directory, the loose
files in the home directory, and every script authored only outside the repo --
with a sha256 prefix per script so a figure quoted from one can be traced after
the directory is gone.

THE INDEX IS DERIVED, NOT HAND-WRITTEN, and it says so in its own header. A
hand-maintained index of files that move is the drift this platform keeps paying
for.

── THE CHAIN, ALL THREE LINKS, ALL COMMITTED ────────────────────────────────
    python tools/scratch-archive/inventory.py  --out <scratch>   -> i6_raw.json
    python tools/scratch-archive/inventory2.py --out <scratch>   -> i6_raw2.json
    python tools/scratch-archive/build_index.py --raw-dir <scratch> --repo <repo>

── WHY THIS FILE IS COMMITTED, AND IT WAS NOT AT FIRST ──────────────────────
The index's first version named this script as `scratchpad/b26/build_index.py`
and named `inventory.py` not at all. Neither was committed and neither was in the
index's own 64-script register -- so **the generator excluded itself from its own
population**, and the "derived" claim in the header would have gone false and
silent on the day that %TEMP% directory cleared, with the header still asserting
it. Caught by `tools/external_file_index_audit.py` arm GENERATOR, which was
written for that shape and found it on its first live run.

── BOTH PATHS ARE REQUIRED ARGUMENTS, WITH NO DEFAULTS ──────────────────────
This script WRITES into a repo. Convention 26: the mistake must not be able to
reach production at all, so `--repo` has no default and `--raw-dir` has no
default. The earlier version hardcoded `REPO = C:\\Users\\marsh\\Documents\\SAIRN-cody`.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

# Committed to tools/scratch-archive/ under the index's own admission rule: a
# script is committed only if it is named in a committed document AND that
# mention is an open NEXT STEP. All three chain links qualify -- the index's
# header names them as the regeneration command, which is an open instruction.
COMMITTED = {'childwatch.py', 'launch_suite.ps1', 'analyse_times.py',
             'prove_childwatch.py', 'triage86.py', 'inventory2.py',
             'inventory.py', 'build_index.py'}

HEADER_DERIVED = (
    'Regenerate, all three links committed: python '
    'tools/scratch-archive/inventory.py --out <scratch>, then '
    'tools/scratch-archive/inventory2.py --out <scratch>, then '
    'tools/scratch-archive/build_index.py --raw-dir <scratch> --repo <repo>. A '
    'hand-maintained index of files that move is the drift this platform keeps '
    'paying for, so this one is derived and the command is recorded here rather '
    'than in a handoff.')

# Kept in its OWN key rather than inside the regeneration prose above. The audit
# reads that prose to check every script named in it is locatable, so a pointer
# to the audit itself sitting in there makes the audit a named regeneration link,
# which it is not.
HEADER_AUDIT = ('Audit this index with python tools/external_file_index_audit.py '
                '-- it checks the counts against the lists, that every script '
                'named in the regeneration command is locatable, and that every '
                'row claiming COMMITTED resolves to a tracked path. Exit 1 on a '
                'finding, exit 2 COULD NOT RUN, never 0 for either.')


def build(raw_dir, repo):
    raw1 = json.load(io.open(os.path.join(raw_dir, 'i6_raw.json'),
                             encoding='utf-8'))
    raw2 = json.load(io.open(os.path.join(raw_dir, 'i6_raw2.json'),
                             encoding='utf-8'))

    tracked = {os.path.basename(t) for t in subprocess.run(
        ['git', 'ls-files'], cwd=repo, capture_output=True,
        encoding='utf-8').stdout.split()}

    # A script already tracked under the same basename is not "outside git" --
    # except for the chain links themselves, which are tracked BECAUSE this
    # inventory decided they must be and still belong in their own register.
    mine = [r for r in raw2['scripts']
            if r['name'] not in tracked or r['name'] in COMMITTED]
    # newest copy per name -- the same script exists in several sessions
    newest = {}
    for r in mine:
        k = r['name']
        if k not in newest or r['mtime'] > newest[k]['mtime']:
            newest[k] = r

    scripts = []
    for name in sorted(newest):
        r = newest[name]
        g = subprocess.run(['git', 'grep', '-l', '--', name], cwd=repo,
                           capture_output=True, encoding='utf-8')
        cites = sorted({h for h in (g.stdout or '').split() if h.endswith('.md')})
        scripts.append({
            'name': name,
            'newest_copy': '%s/%s' % (r['session'], r['rel']),
            'bytes': r['bytes'],
            'sha256_16': r['sha256_16'],
            'mtime': r['mtime'],
            'copies_in_n_sessions': sum(1 for x in mine if x['name'] == name),
            'cited_in_committed_docs': cites,
            'status': ('COMMITTED to tools/scratch-archive/' if name in COMMITTED
                       else 'REGISTERED ONLY -- lives in %TEMP% and will not '
                            'survive a clear'),
        })

    dirs = []
    for s in raw1['sessions']:
        if not s.get('files'):
            continue
        dirs.append({'path': s['path'], 'role': s['label'], 'files': s['files'],
                     'bytes': s['bytes'], 'newest_mtime': s['newest_mtime'],
                     'volatility': 'HIGH -- %TEMP%, cleared without warning'})
    for k, vol in (('locks', 'MEDIUM -- outside every clone, survives a clone wipe'),
                   ('drive', 'LOW -- Google Drive, synced off-machine')):
        s = raw1.get(k) or {}
        if s.get('exists'):
            dirs.append({'path': s['path'], 'role': s['label'],
                         'files': s['files'], 'bytes': s['bytes'],
                         'newest_mtime': s['newest_mtime'], 'volatility': vol})

    loose = []
    for l in raw2['loose']:
        loose.append({
            'path': l['path'], 'bytes': l['bytes'], 'sha256_16': l['sha256_16'],
            'in_repo_byte_identical': l['byte_identical_copy_in_repo'],
            'first_line_seen_in_docs_history': l['first_line_found_in_docs_history'],
            'verdict': ('RESCUED into docs/archive-from-home/ by this batch'
                        if l['path'].lower().endswith('.md')
                        else 'GENERATED app snapshot -- registered, not committed'),
        })

    return {
        '_what_this_is': (
            'Everything cody keeps OUTSIDE git: scratchpad directories, the '
            'shared status registry, the Drive report directory, loose '
            'home-directory files, and every script authored only outside the '
            'repo. Written so a figure quoted from one of them can be traced '
            'after the directory is gone.'),
        '_derived_not_hand_written': HEADER_DERIVED,
        '_audit_with': HEADER_AUDIT,
        '_the_admission_rule': (
            'A script is COMMITTED to tools/scratch-archive/ only if it is named '
            'in a committed document AND that mention is an open NEXT STEP. '
            'Everything else is REGISTERED here and left where it is.'),
        '_measured': {
            'scripts_authored_outside_git': len(newest),
            'of_those_cited_in_a_committed_doc':
                len([s for s in scripts if s['cited_in_committed_docs']]),
            'of_those_committed_to_the_repo':
                len([s for s in scripts if s['name'] in COMMITTED]),
            'first_count_was_wrong': (
                'A first pass reported 2,521 code files across all scratchpads. '
                '2,140 of them were in one session and reading three paths '
                'showed what they are: copies of the repo own api/ and tests/ '
                'trees inside the fa12 and fa14 firebase sandboxes. A second '
                'pass pruning sandbox directories by name, then subtracting the '
                '311 whose basename is already a tracked repo file, gives %d. A '
                'count that includes a copy of the thing it is meant to be '
                'distinguished from is not a measurement.' % len(newest)),
        },
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'generated_at_commit': subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=repo,
            capture_output=True, encoding='utf-8').stdout.strip(),
        'session': 'cody',
        'directories': dirs,
        'loose_home_files': loose,
        'scripts': scripts,
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--raw-dir', required=True,
                    help='directory holding i6_raw.json and i6_raw2.json. '
                         'REQUIRED, no default.')
    ap.add_argument('--repo', required=True,
                    help='repo to write docs/external-files-index.json into. '
                         'REQUIRED, no default -- convention 26.')
    a = ap.parse_args(argv)

    for f in ('i6_raw.json', 'i6_raw2.json'):
        if not os.path.isfile(os.path.join(a.raw_dir, f)):
            print('COULD NOT RUN: %s is not in --raw-dir %s. Re-run '
                  'inventory.py and inventory2.py first. Nothing written.'
                  % (f, a.raw_dir))
            return 2
    if not os.path.isdir(os.path.join(a.repo, 'docs')):
        print('COULD NOT RUN: --repo %s has no docs/ directory. Nothing written.'
              % a.repo)
        return 2

    doc = build(a.raw_dir, a.repo)
    p = os.path.join(a.repo, 'docs', 'external-files-index.json')
    io.open(p, 'w', encoding='utf-8',
            newline='\n').write(json.dumps(doc, indent=2) + '\n')
    print('wrote %s' % p)
    print('  directories      : %d' % len(doc['directories']))
    print('  loose home files : %d' % len(doc['loose_home_files']))
    c = len([s for s in doc['scripts'] if s['name'] in COMMITTED])
    print('  scripts          : %d (%d committed, %d registered only)'
          % (len(doc['scripts']), c, len(doc['scripts']) - c))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
