"""Item 6, second pass -- the first count was wrong in the inflating direction.

Pass 1 reported 2,521 "code files across all scratchpads". 2,140 of them were in
one session, and reading three of the paths showed what they are: COPIES OF THE
REPO'S OWN api/ AND tests/ TREES inside fa12/ and fa14/, the firebase-admin
version sandboxes from batch 20. They are not scripts I wrote and keep; they are
a checkout of the repo sitting in a temp directory.

So the sandbox directories are pruned by NAME and the number is re-derived. A
count that includes a copy of the thing it is supposed to be distinguished from
is not a measurement.

PRUNED, each because it is a repo/dependency copy rather than my own work:
  node_modules, __pycache__, .git, fa12, fa14, fa145, wt-*, *-clone, dist
"""
import fnmatch
import hashlib
import io
import json
import os
import subprocess
import time

HOME = r'C:\Users\marsh'
REPO = os.path.join(HOME, r'Documents\SAIRN-cody')
TEMPROOT = os.path.join(HOME, r'AppData\Local\Temp\claude',
                        'C--Users-marsh-Documents-SAIRN-cody')
PRUNE_EXACT = {'node_modules', '__pycache__', '.git', 'fa12', 'fa14', 'fa145',
               'dist', 'tasks'}
PRUNE_GLOB = ('wt-*', '*-clone', 'sairn-suite-*', 'tmp.*')
MINE = ('.py', '.ps1', '.sh')


def pruned(name):
    return name in PRUNE_EXACT or any(fnmatch.fnmatch(name, g) for g in PRUNE_GLOB)


rows = []
for sess in sorted(os.listdir(TEMPROOT)) if os.path.isdir(TEMPROOT) else []:
    root = os.path.join(TEMPROOT, sess)
    if not os.path.isdir(root):
        continue
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not pruned(d)]
        for f in files:
            if not f.lower().endswith(MINE):
                continue
            p = os.path.join(dp, f)
            try:
                st = os.stat(p)
                body = io.open(p, 'rb').read()
            except OSError:
                continue
            rows.append({
                'session': sess, 'name': f,
                'rel': os.path.relpath(p, root).replace('\\', '/'),
                'bytes': st.st_size,
                'sha256_16': hashlib.sha256(body).hexdigest()[:16],
                'mtime': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(st.st_mtime)),
            })

print('MY OWN SCRIPTS OUTSIDE GIT (py/ps1/sh, sandboxes pruned): %d' % len(rows))
bysess = {}
for r in rows:
    bysess.setdefault(r['session'], []).append(r)
for s in sorted(bysess):
    print('  %s  %d' % (s[:8], len(bysess[s])))

# Is any of them ALREADY in the repo under the same name?
tracked = set(subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True,
                             encoding='utf-8').stdout.split())
tracked_names = {os.path.basename(t): t for t in tracked}
dupes = [(r, tracked_names[r['name']]) for r in rows if r['name'] in tracked_names]
print()
print('scripts whose NAME already exists in the repo: %d' % len(dupes))
for r, t in dupes[:12]:
    print('  %-34s <- also tracked at %s' % (r['name'], t))

loose = []
for f in sorted(os.listdir(HOME)):
    p = os.path.join(HOME, f)
    if not os.path.isfile(p):
        continue
    if not ('sairn' in f.lower() or 'handoff' in f.lower()):
        continue
    body = io.open(p, 'rb').read()
    h = hashlib.sha256(body).hexdigest()
    same = [t for t in tracked if os.path.basename(t) == f]
    in_repo_same_bytes = False
    for t in same:
        try:
            if hashlib.sha256(io.open(os.path.join(REPO, t), 'rb').read()).hexdigest() == h:
                in_repo_same_bytes = True
        except OSError:
            pass
    # does the repo hold this content under ANY name?
    g = subprocess.run(['git', 'log', '--all', '--oneline', '-S',
                        body.decode('utf-8', 'replace')[:80], '--', 'docs/'],
                       cwd=REPO, capture_output=True, encoding='utf-8')
    loose.append({'path': p, 'bytes': len(body), 'sha256_16': h[:16],
                  'same_name_tracked': same,
                  'byte_identical_copy_in_repo': in_repo_same_bytes,
                  'first_line_found_in_docs_history':
                      bool((g.stdout or '').strip())})

print()
print('LOOSE SAIRN-ish FILES DIRECTLY UNDER ~ : %d' % len(loose))
for l in loose:
    print('  %-62s %7d b  same-name-tracked=%s  identical-copy=%s  '
          'first-line-in-docs-history=%s'
          % (os.path.basename(l['path']), l['bytes'],
             bool(l['same_name_tracked']), l['byte_identical_copy_in_repo'],
             l['first_line_found_in_docs_history']))

io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'i6_raw2.json'), 'w', encoding='utf-8',
        newline='\n').write(json.dumps({'scripts': rows, 'loose': loose}, indent=2))
