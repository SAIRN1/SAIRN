# OWNER: cody
"""Item 6, FIRST pass -- inventory everything of cody's that lives OUTSIDE git.

Scoped and bounded on purpose. `du -sh` over a scratchpad containing several
node_modules trees took longer than the shell's two-minute ceiling, so this walks
with explicit prunes and counts rather than shelling out per directory.

FOUR PLACES, named rather than globbed from the whole disk:
  1. the session scratchpads under %TEMP%\\claude\\C--Users-marsh-Documents-SAIRN-cody
  2. the shared status registry at ~/SAIRN-SESSION-LOCKS
  3. the Drive report directory G:\\My Drive\\SAIRN-status
  4. loose SAIRN-ish files directly under ~ (not recursive -- that is the user's
     whole home directory and not mine to enumerate)

── WHY IT IS COMMITTED, AND IT WAS NOT AT FIRST ─────────────────────────────
It is link 1 of 3 in the regeneration chain that `docs/external-files-index.json`
declares in its own header. The first version of that index named only links 1
and 3 as `scratchpad/b26/...` paths and committed neither, so the index's
"derived, not hand-written" claim would have become false, and silent, on the day
that %TEMP% directory cleared. Found by `tools/external_file_index_audit.py`,
which exists for exactly that arm.

── PASS 1'S NUMBER WAS WRONG AND THAT IS WHY THERE IS A PASS 2 ──────────────
This pass reports "code files across all scratchpads", which came out at 2,521.
2,140 of those are copies of the repo's own api/ and tests/ trees inside the fa12
and fa14 firebase sandboxes. `inventory2.py` prunes them and re-derives. Both
numbers are kept in the index so the correction is visible rather than replaced.

── THE OUTPUT PATH IS A REQUIRED ARGUMENT, WITH NO DEFAULT ──────────────────
Convention 26: a write path that falls back to a live location is how a failed
redirection reaches production. `--out` is required, so this cannot silently drop
`i6_raw.json` into a tracked directory.

    python tools/scratch-archive/inventory.py --out <scratch-dir>
"""
import argparse
import io
import json
import os
import sys
import time

HOME = r'C:\Users\marsh'
TEMPROOT = os.path.join(HOME, r'AppData\Local\Temp\claude',
                        'C--Users-marsh-Documents-SAIRN-cody')
LOCKS = os.path.join(HOME, 'SAIRN-SESSION-LOCKS')
DRIVE = r'G:\My Drive\SAIRN-status'
PRUNE = {'node_modules', '__pycache__', '.git', 'fa145'}
CODEEXT = ('.py', '.ps1', '.sh', '.js', '.mjs')
DOCEXT = ('.md', '.txt', '.json', '.tsv', '.csv', '.out', '.status', '.patch')


def walk(root, maxdepth=6):
    base = root.rstrip('\\/').count(os.sep)
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PRUNE]
        if dp.count(os.sep) - base >= maxdepth:
            dirs[:] = []
        for f in files:
            yield os.path.join(dp, f)


def summarise(root, label, maxdepth=6):
    if not os.path.isdir(root):
        return {'path': root, 'label': label, 'exists': False}
    n = code = doc = 0
    size = 0
    newest = 0.0
    codefiles = []
    for p in walk(root, maxdepth):
        try:
            st = os.stat(p)
        except OSError:
            continue
        n += 1
        size += st.st_size
        newest = max(newest, st.st_mtime)
        low = p.lower()
        if low.endswith(CODEEXT):
            code += 1
            codefiles.append(os.path.relpath(p, root).replace('\\', '/'))
        elif low.endswith(DOCEXT):
            doc += 1
    return {'path': root, 'label': label, 'exists': True, 'files': n,
            'code_files': code, 'data_or_doc_files': doc,
            'bytes': size,
            'newest_mtime': time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                          time.gmtime(newest)) if newest else None,
            'code_sample': sorted(codefiles)[:40]}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True,
                    help='directory to write i6_raw.json into. REQUIRED, no '
                         'default -- convention 26.')
    a = ap.parse_args(argv)
    if not os.path.isdir(a.out):
        print('COULD NOT RUN: --out %s is not a directory. Nothing written.'
              % a.out)
        return 2

    out = {}
    sessions = []
    if os.path.isdir(TEMPROOT):
        for d in sorted(os.listdir(TEMPROOT)):
            full = os.path.join(TEMPROOT, d)
            if os.path.isdir(full):
                sessions.append(summarise(full,
                                          'session transcript + scratchpad'))
    out['sessions'] = sessions
    out['locks'] = summarise(LOCKS,
                             'shared status registry (outside every clone)')
    out['drive'] = summarise(DRIVE, 'Drive report directory Michael reads')
    loose = []
    for f in sorted(os.listdir(HOME)):
        p = os.path.join(HOME, f)
        if os.path.isfile(p) and ('sairn' in f.lower() or 'handoff' in f.lower()):
            loose.append({'path': p, 'bytes': os.path.getsize(p)})
    out['loose_home_files'] = loose

    dest = os.path.join(a.out, 'i6_raw.json')
    io.open(dest, 'w', encoding='utf-8',
            newline='\n').write(json.dumps(out, indent=2))

    print('SESSION SCRATCHPADS: %d' % len(sessions))
    for s in sessions:
        print('  %-38s %6d files  %8.1f MB  code %3d  newest %s'
              % (os.path.basename(s['path']), s['files'], s['bytes'] / 1e6,
                 s['code_files'], s['newest_mtime']))
    for k in ('locks', 'drive'):
        s = out[k]
        if s.get('exists'):
            print('%-20s %6d files  %8.1f MB  newest %s'
                  % (k.upper(), s['files'], s['bytes'] / 1e6, s['newest_mtime']))
        else:
            print('%-20s ABSENT (%s)' % (k.upper(), s['path']))
    print('LOOSE ~ FILES: %d' % len(loose))
    for l in loose:
        print('  %s  %d bytes' % (l['path'], l['bytes']))
    print()
    print('CODE FILES ACROSS ALL SCRATCHPADS: %d  <- PASS 1, and it is INFLATED '
          'by repo copies. See inventory2.py.'
          % sum(s.get('code_files', 0) for s in sessions))
    print('wrote %s' % dest)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
