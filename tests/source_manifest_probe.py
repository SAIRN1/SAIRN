"""tools/source_manifest.py must REFUSE rather than emit a stale manifest.

    python tests/source_manifest_probe.py

WHY THIS EXISTS. The manifest's only meaning is "the files vercel.json copies
into the deploy output". Every way that meaning can quietly stop being true is
a way this tool keeps printing a clean, signed-able JSON document about the
wrong file set -- and a manifest is read exactly once, under pressure, by
somebody who will not re-derive it.

So the arms below are the REFUSALS, not the happy path. Each is exercised
against a REAL throwaway git repository built in a temp directory, because a
refusal asserted by reading the source is a refusal nobody has watched fire.
That is what `--repo` on the tool is for; it exists for this probe and says so
in its own help text.

THE FOUR REFUSALS, and what each one is standing in front of:

  1. buildCommand changed        somebody adds a directory, a bundler, or a
                                 different index source. The file map in the
                                 generator is now fiction.
  2. outputDirectory changed     every destination path in the manifest is
                                 wrong, while the digests still look right.
  3. a named copy is missing     stonedesk.html or sw.js gone from the tree.
  4. no top-level *.html         `cp *.html dist/` deploys nothing. An empty
                                 manifest is the shape that reads most like
                                 success and means the least.

AND ONE POSITIVE ARM THAT IS NOT "it ran": the manifest must cover EVERY
top-level .html in the tree, counted independently with `git ls-tree` rather
than taken from the tool's own file_count. A generator that silently dropped
files would satisfy any assertion phrased against its own output.

AND ONE THAT IS DELIBERATELY NOT HERE: nothing in this probe checks that the
digests match the deployed site. They cannot -- see the tool's header. Writing
an arm that looked like it did would be the fabrication this platform's own
checks exist to catch.

Exit 0 pass, 1 fail.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'source_manifest.py')

REAL_BUILD_COMMAND = (
    'mkdir -p dist && cp *.html dist/ && cp stonedesk.html dist/index.html '
    '&& cp sw.js dist/sw.js'
)

fails = []


def check(ok, label):
    print('  %s  %s' % ('PASS' if ok else 'FAIL', label))
    if not ok:
        fails.append(label)


def run_tool(args):
    p = subprocess.run([sys.executable, TOOL] + args, cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')


def fixture(tmp, build_command=REAL_BUILD_COMMAND, output_dir='dist',
            html=('stonedesk.html', 'sairnbiz.html'), sw=True):
    """A real git repo with a controllable deployed file set."""
    root = tempfile.mkdtemp(dir=tmp)
    def g(*a):
        subprocess.run(['git'] + list(a), cwd=root, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    g('init', '-q')
    g('config', 'user.email', 'probe@example.invalid')
    g('config', 'user.name', 'probe')
    cfg = {'buildCommand': build_command, 'outputDirectory': output_dir}
    with open(os.path.join(root, 'vercel.json'), 'w', newline='\n') as fh:
        json.dump(cfg, fh)
    for name in html:
        with open(os.path.join(root, name), 'w', newline='\n') as fh:
            fh.write('<!doctype html><title>%s</title>\n' % name)
    if sw:
        with open(os.path.join(root, 'sw.js'), 'w', newline='\n') as fh:
            fh.write('// probe\n')
    g('add', '-A')
    g('commit', '-q', '-m', 'fixture')
    return root


tmpdir = tempfile.mkdtemp(prefix='source-manifest-probe-')
try:
    print('THE REFUSALS -- each watched to fire against a real fixture repo')

    root = fixture(tmpdir)
    rc, out, err = run_tool(['--repo', root])
    check(rc == 0 and json.loads(out)['file_count'] == 4,
          'the unmodified fixture produces a manifest (2 html + index + sw)')

    root = fixture(tmpdir, build_command=REAL_BUILD_COMMAND + ' && cp -r assets dist/')
    rc, out, err = run_tool(['--repo', root])
    check(rc == 2 and 'buildCommand' in err and out.strip() == '',
          'a CHANGED buildCommand refuses with exit 2 and emits no manifest')

    root = fixture(tmpdir, output_dir='public')
    rc, out, err = run_tool(['--repo', root])
    check(rc == 2 and 'outputDirectory' in err and out.strip() == '',
          'a CHANGED outputDirectory refuses rather than mislabelling every path')

    root = fixture(tmpdir, sw=False)
    rc, out, err = run_tool(['--repo', root])
    check(rc == 2 and 'sw.js' in err and out.strip() == '',
          'a named copy missing from the tree refuses and NAMES the file')

    root = fixture(tmpdir, html=())
    rc, out, err = run_tool(['--repo', root])
    check(rc == 2 and out.strip() == '',
          'zero top-level *.html refuses instead of emitting an empty manifest')

    print('')
    print('COVERAGE, COUNTED INDEPENDENTLY OF THE TOOL')

    rc, out, err = run_tool([])
    check(rc == 0, 'the real repo produces a manifest')
    if rc == 0:
        manifest = json.loads(out)
        listing = subprocess.run(
            ['git', 'ls-tree', '--name-only', manifest['commit']], cwd=REPO,
            stdout=subprocess.PIPE, check=True).stdout.decode('utf-8')
        top = [n for n in listing.splitlines() if n]
        expected_html = sorted(n for n in top if n.endswith('.html'))

        listed = sorted(v['source'] for k, v in manifest['files'].items()
                        if k != 'dist/index.html' and k != 'dist/sw.js')
        check(listed == expected_html,
              'every top-level .html in the tree appears -- %d counted by '
              'git ls-tree, %d in the manifest'
              % (len(expected_html), len(listed)))

        check(manifest['file_count'] == len(expected_html) + 2,
              'file_count is the html set plus the two named copies, not a '
              'number the tool chose')

        idx = manifest['files']['dist/index.html']
        sd = manifest['files']['dist/stonedesk.html']
        check(idx['sha256'] == sd['sha256'] and idx['source'] == 'stonedesk.html',
              'dist/index.html carries stonedesk.html\'s digest -- the build '
              'command copies the same file twice and the manifest says so')

        check('NOT SLSA build provenance' in manifest['what_this_is'],
              'the manifest disclaims build provenance IN THE ARTIFACT, not '
              'only in a comment nobody ships')

    print('')
    print('DETERMINISM -- two runs of the same commit must be byte-identical')
    rc1, out1, _ = run_tool([])
    rc2, out2, _ = run_tool([])
    check(rc1 == 0 and rc2 == 0 and out1 == out2,
          'the manifest is reproducible from the same commit')
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
