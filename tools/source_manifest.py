"""A SOURCE MANIFEST OF WHAT A COMMIT WAS SUPPOSED TO DEPLOY.

    python tools/source_manifest.py --out manifest.json

THIS IS NOT SLSA BUILD PROVENANCE AND MUST NEVER BE DESCRIBED AS IT.
That sentence is the first line of this file because the word is the whole
risk. `docs/2026-09-18-slsa-build-provenance-scoping.md` sets out why the
deployed product cannot have build provenance today: Vercel builds and deploys
from the git push, no GitHub Actions workflow touches the deployed bytes, and
`vercel.json`'s build command is a file copy. Option A of that document -- move
the build into Actions -- is the only route to real provenance on the product,
and it trades a working zero-config deploy for a stronger word. Michael chose
option C: attest a MANIFEST.

So what this emits is a signed-able record of `{deployed path: sha256 of the
source bytes}` at one commit. Read plainly, it says:

    THIS workflow, from THIS commit, computed these digests for the files
    vercel.json says get copied into dist/.

and it does NOT say:

    * that Vercel deployed those bytes. Nothing here observes the deploy.
      `tools/deploy_verify_notify.py` is the control that compares live bytes
      against origin/main, and it is a DETECTION, after the fact, on one file.
      A manifest is what that check would compare against if it were widened;
      it is not a substitute for it.
    * that the bytes are good. A signature is not a quality judgement -- the
      same point already written into the attest step of nightly-backup.yml.
    * anything about api/ serverless functions. `cp *.html` does not touch
      them; they are deployed by Vercel's filesystem routing from the repo and
      are OUT OF SCOPE of this manifest. Stated because a manifest that looks
      complete and is not is worse than an obviously partial one.

── WHY THE BUILD COMMAND IS COMPARED VERBATIM AND A DIFFERENCE IS FATAL ──────
The manifest's entire meaning is "the files vercel.json copies". If somebody
edits `buildCommand` -- adds a directory, changes the index source, starts
running a real bundler -- then this generator is describing a file set that is
no longer the deployed one, AND IT WOULD KEEP EMITTING A CLEAN MANIFEST. That
is the eighth standing discipline in docs/2026-09-13-cross-domain-disciplines.md:
nothing announces the day a check stops testing anything.

So EXPECTED_BUILD_COMMAND below is an exact string and any difference REFUSES
with exit 2. It is deliberately brittle. A refusal costs somebody five minutes
of re-deriving the file map; a silent stale manifest costs a wrong answer at
the one moment anybody reads it.

── AND IT HASHES GIT BLOBS, NOT THE WORKING TREE ─────────────────────────────
`git cat-file blob <commit>:<path>`, not `open(path, 'rb')`. Two reasons, and
the second is the one that would actually have bitten:

  1. A clone's working tree can hold CRLF while the blob is LF -- .gitattributes
     fixes that going forward but is NOT retroactive, and that mismatch produced
     three false alarms in one session on 2026-09-03. A manifest generated on a
     Windows clone and a manifest generated on a Linux runner have to be the
     same file or the whole thing is noise.
  2. The working tree holds UNTRACKED files. `cp *.html dist/` on a Vercel
     checkout expands against tracked content only; a stray local `piac.html`
     would have entered a filesystem-glob manifest and never enters a deploy.

Exit 0 manifest written, 2 refused / could not run. There is no exit 1: this
tool does not render a verdict about anything, so it has nothing to fail on.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCHEMA = 'sairn.source-manifest/1'

# Verbatim from vercel.json. See the header: any difference is a refusal.
EXPECTED_BUILD_COMMAND = (
    'mkdir -p dist && cp *.html dist/ && cp stonedesk.html dist/index.html '
    '&& cp sw.js dist/sw.js'
)
EXPECTED_OUTPUT_DIR = 'dist'

# The two named copies in the build command, as {source: destination}. Kept
# beside the expected command rather than inferred from it -- parsing a shell
# line to discover them would be a parser that can be wrong quietly, and the
# verbatim compare above already guarantees these two are what it says.
NAMED_COPIES = [
    ('stonedesk.html', 'dist/index.html'),
    ('sw.js', 'dist/sw.js'),
]


def refuse(message):
    sys.stderr.write('REFUSED: %s\n' % message)
    sys.stderr.write('No manifest was written. This is a COULD-NOT-RUN, not a pass.\n')
    sys.exit(2)


def git(repo, args):
    try:
        return subprocess.run(
            ['git'] + args, cwd=repo, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=True).stdout
    except FileNotFoundError:
        refuse('git is not on PATH, so nothing could be read from the object store.')
    except subprocess.CalledProcessError as e:
        refuse('git %s failed in %s: %s'
               % (' '.join(args), repo, e.stderr.decode('utf-8', 'replace').strip()))


def build(repo, commit, vercel_json_path):
    if not os.path.isfile(vercel_json_path):
        refuse('%s does not exist, so the deployed file set is unknown.'
               % vercel_json_path)
    try:
        with open(vercel_json_path, 'rb') as fh:
            cfg = json.loads(fh.read().decode('utf-8'))
    except ValueError as e:
        refuse('%s is not valid JSON (%s).' % (vercel_json_path, e))

    actual = cfg.get('buildCommand')
    if actual != EXPECTED_BUILD_COMMAND:
        refuse(
            'vercel.json buildCommand is not the one this generator models.\n'
            '  expected: %r\n'
            '  found   : %r\n'
            'The deployed file set may have changed. Re-derive the map in '
            'tools/source_manifest.py before trusting any manifest.'
            % (EXPECTED_BUILD_COMMAND, actual))

    out_dir = cfg.get('outputDirectory')
    if out_dir != EXPECTED_OUTPUT_DIR:
        refuse('vercel.json outputDirectory is %r, not %r. The destination '
               'paths in this manifest would be wrong.'
               % (out_dir, EXPECTED_OUTPUT_DIR))

    sha = git(repo, ['rev-parse', commit]).decode('ascii').strip()
    listing = git(repo, ['ls-tree', '--name-only', sha]).decode('utf-8')
    top_level = [n for n in listing.splitlines() if n]
    html = sorted(n for n in top_level if n.endswith('.html'))

    if not html:
        refuse('no top-level *.html exists at %s. `cp *.html dist/` would '
               'deploy nothing, which is not a state this manifest should '
               'describe as normal.' % sha[:12])

    files = {}
    for name in html:
        files['%s/%s' % (EXPECTED_OUTPUT_DIR, name)] = name
    for source, dest in NAMED_COPIES:
        if source not in top_level:
            refuse('%s is named in the build command but is not in the tree at '
                   '%s. The deploy would fail or serve a stale copy; either way '
                   'a manifest listing it would be a lie.' % (source, sha[:12]))
        files[dest] = source

    entries = {}
    for dest in sorted(files):
        source = files[dest]
        blob = git(repo, ['cat-file', 'blob', '%s:%s' % (sha, source)])
        entries[dest] = {
            'source': source,
            'bytes': len(blob),
            'sha256': hashlib.sha256(blob).hexdigest(),
        }

    return {
        'schema': SCHEMA,
        'what_this_is': (
            'sha256 of the SOURCE BYTES that vercel.json copies into the '
            'deploy output, at one commit. NOT SLSA build provenance: nothing '
            'here observes the Vercel build or the deployed site.'),
        'commit': sha,
        'vercel_build_command': EXPECTED_BUILD_COMMAND,
        'output_directory': EXPECTED_OUTPUT_DIR,
        'hashed_from': 'git blob at the commit, not the working tree',
        'out_of_scope': [
            'api/ serverless functions -- routed by Vercel from the repo, not '
            'copied by the build command',
            'whether Vercel actually deployed these bytes',
        ],
        'file_count': len(entries),
        'files': entries,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', help='write the manifest here (default: stdout)')
    ap.add_argument('--commit', default='HEAD', help='commit-ish (default HEAD)')
    ap.add_argument('--repo', default=REPO,
                    help='repository root (default: this checkout). Exists so '
                         'the refusal paths can be exercised against a real '
                         'fixture repo rather than argued about.')
    ap.add_argument('--vercel-json',
                    help='path to vercel.json (default: <repo>/vercel.json)')
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    vercel = a.vercel_json or os.path.join(repo, 'vercel.json')

    manifest = build(repo, a.commit, vercel)
    text = json.dumps(manifest, indent=2, sort_keys=True) + '\n'

    if a.out:
        with open(a.out, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        sys.stderr.write('%s: %d files, commit %s\n'
                         % (a.out, manifest['file_count'], manifest['commit'][:12]))
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
