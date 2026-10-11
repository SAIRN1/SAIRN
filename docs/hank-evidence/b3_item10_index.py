# -*- coding: utf-8 -*-
"""ITEM 10 -- build docs/external-files-index.json from the real filesystem.

EVERY ENTRY IS MEASURED, NOT LISTED FROM MEMORY. Each directory is walked, each
file is sized and dated, and anything unreadable is recorded as UNREADABLE rather
than skipped -- a register that silently drops what it could not read is the
third-state collapse this platform keeps finding.

SCOPE, which is the four places the item names:
  working dir   untracked files inside the clone
  scratchpad    both of my session scratchpads
  home          what I keep under ~ that is mine
  temp          the clones, worktrees and sandboxes I created

SHAPE: {"agents": {"hank": {"dirs": [...], "files": [...]}}} -- created if absent,
MERGED if present, because another agent registering itself later must not lose me
and I must not lose them.
"""
import hashlib
import io
import json
import os
import subprocess
import time

REPO = r'C:\Users\marsh\Documents\SAIRN-hank'
OUT = os.path.join(REPO, 'docs', 'external-files-index.json')
HOME = os.path.expanduser('~')
S_THIS = (r'C:\Users\marsh\AppData\Local\Temp\claude'
          r'\C--Users-marsh-Documents-SAIRN-hank'
          r'\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad')
S_PREV = (r'C:\Users\marsh\AppData\Local\Temp\claude'
          r'\C--Users-marsh-Documents-SAIRN-hank'
          r'\16753c01-e018-4c71-af08-342c1baa72e6\scratchpad')

DIRS = [
    (S_THIS, 'scratchpad', 'batch 18 and 19 working directory: every captured '
     'exit code, sweep script, mutation backup and verdict body. EPHEMERAL -- '
     'under %TEMP% and cleared without notice. Anything here that a committed '
     'document cites has been copied to docs/hank-evidence/.'),
    (S_PREV, 'scratchpad', 'batch b1 and earlier working directory. Holds '
     'tools_sweep.tsv (the 315-script exit-code sweep) and f.rat.out (the 47KB '
     'suite run whose zero-byte predecessors were a buffering artefact). '
     'EPHEMERAL.'),
    (os.path.join(HOME, 'SAIRN-SESSION-LOCKS'), 'home',
     'SHARED, NOT MINE ALONE -- the cross-clone lock and status registry every '
     'session reads. Outside every clone on purpose, which is why it is current '
     'without a fetch, and why a write here is invisible to a repo-scoped check. '
     'Listed so it is on the map; I own only hank.lock and the rows I write.'),
    (r'G:\My Drive\SAIRN-status', 'drive',
     'the per-batch final report files. OUTSIDE GIT ON PURPOSE -- they carry a '
     'SHA256 of their own body and are handed to Michael, not merged.'),
]

TEMP_DIRS = [
    (r'C:\Users\marsh\AppData\Local\Temp\b2-i6-clone',
     'throwaway CLONE, batch 18 item 6 and batch 19 item 4 -- write-when-run '
     'tools driven here so the live clone is untouched'),
    (r'C:\Users\marsh\AppData\Local\Temp\b3-brwc-scratch',
     'throwaway CLONE, batch 19 item 6 -- the widened bare-run sweep'),
    (r'C:\Users\marsh\AppData\Local\Temp\b3-drs-clone',
     'throwaway CLONE, batch 19 item 8 -- dead_rule_sweep timed to completion'),
    (r'C:\Users\marsh\AppData\Local\Temp\b3-locks-sandbox',
     'sandbox lock registry for the widened sweep, so a lock-writing tool is '
     'still caught and the REAL registry is never written to (RULE G)'),
    (r'C:\Users\marsh\AppData\Local\Temp\b2-barerun-scratch',
     'throwaway CLONE, batch 18 -- bare_run_write_check subject'),
    (r'C:\Users\marsh\AppData\Local\Temp\barehunt-b2',
     'throwaway CLONE, batch 18 item 6a -- the core.bare negative control'),
    (r'C:\Users\marsh\AppData\Local\Temp\barehunt-b2-wt',
     'LINKED WORKTREE of barehunt-b2, the second negative control (the one that '
     'added a worktree to see if that was the differentiating condition)'),
]


def walk(root, cap=4000):
    files, total, trunc = [], 0, False
    for dirpath, dirnames, filenames in os.walk(root):
        if '.git' in dirnames:
            dirnames.remove('.git')
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                files.append({'path': os.path.relpath(p, root).replace('\\', '/'),
                              'bytes': 'UNREADABLE', 'mtime': 'UNREADABLE'})
                continue
            files.append({
                'path': os.path.relpath(p, root).replace('\\', '/'),
                'bytes': st.st_size,
                'mtime': time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                       time.gmtime(st.st_mtime))})
            total += st.st_size
            if len(files) >= cap:
                trunc = True
                return files, total, trunc
    return files, total, trunc


dirs = []
for path, kind, note in DIRS + [(p, 'temp', n) for p, n in TEMP_DIRS]:
    exists = os.path.isdir(path)
    if exists:
        files, total, trunc = walk(path)
    else:
        files, total, trunc = [], 0, False
    dirs.append({
        'path': path.replace('\\', '/'),
        'kind': kind,
        'exists_at_audit': exists,
        'file_count': len(files) if exists else 0,
        'bytes_total': total,
        'listing_truncated': trunc,
        'note': note,
        # A THROWAWAY CLONE'S FILE LIST IS NOISE, NOT A RECORD. Each of these is
        # ~3,200 files that are just a copy of the repo; naming them would make
        # this index 147KB of things nobody needs and bury the 226 scratchpad
        # files that are the actual point. Count and size are kept; the listing
        # is omitted ON PURPOSE and the omission is stated rather than silent.
        'files': ([f['path'] for f in files][:400] if kind != 'temp'
                  else []),
        'listing_omitted_reason': (None if kind != 'temp' else
                                   'a throwaway clone of this repo -- count and '
                                   'size recorded, per-file listing omitted as '
                                   'noise'),
    })
    print('%-62s exists=%-5s files=%-5s bytes=%-10s%s'
          % (path[-60:], exists, len(files), total,
             '  TRUNCATED' if trunc else ''), flush=True)

# -- untracked files INSIDE the clone: these are the ones that could have been
#    committed and were not, so each is named rather than counted.
p = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'],
                   cwd=REPO, capture_output=True, text=True)
untracked = sorted(l[3:].strip() for l in (p.stdout or '').split('\n')
                   if l.startswith('??'))
print('\nuntracked inside the clone: %d' % len(untracked))
for u in untracked:
    print('    %s' % u)

ev = os.path.join(REPO, 'docs', 'hank-evidence')
committed = sorted(os.listdir(ev)) if os.path.isdir(ev) else []

entry = {
    'audited_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'audited_by': 'hank, batch 19 item 10',
    'how': ('every directory WALKED and every file sized and dated; anything '
            'unreadable is recorded as UNREADABLE rather than skipped. Nothing '
            'here is listed from memory.'),
    'what_was_committed_instead_of_registered': {
        'dir': 'docs/hank-evidence/',
        'why': ('a committed document, test header or defect-register record '
                'that CITES a file in %TEMP% is a dangling citation the moment '
                'that directory is cleared. The audit found six of my '
                'scratchpad files cited by name in committed artefacts; those, '
                'plus the generators of committed documents, are now in the '
                'repo. NOT in tools/ -- they are one-off evidence, and tools/ '
                'enrols a file in four governance populations.'),
        'files': committed,
    },
    'other_sessions_have_the_same_defect_and_it_is_not_mine_to_fix': {
        'cited_from_scratchpad_by_other_sessions': [
            'gapverify.py', 'verify_specs.py', 'prefix_demo.py', 'grd_enum.py',
            'cite_measure.py', 'sfdrift.py'],
        'note': ('found by the same grep over committed docs. Named for their '
                 'owners rather than relocated by me.'),
    },
    'untracked_inside_the_clone': untracked,
    'dirs': dirs,
    'files': [],
    'limits': [
        'EPHEMERAL BY DEFINITION: everything under %TEMP% can vanish between '
        'sessions. This index records what existed at the audit time and is not '
        'a promise that it still does.',
        'A directory listing is capped at 4000 files and 400 names per entry; '
        '"listing_truncated" says so per directory rather than silently cutting.',
        'G:\\My Drive is a Google Drive mount. A file can exist in the index and '
        'be a placeholder on disk until Drive hydrates it.',
        '~/SAIRN-SESSION-LOCKS is SHARED. It is listed because it is state I '
        'write to, not because it is mine to clear.',
    ],
}

if os.path.isfile(OUT):
    doc = json.load(io.open(OUT, encoding='utf-8'))
    if 'agents' not in doc or not isinstance(doc['agents'], dict):
        doc['agents'] = {}
    print('\nMERGING into an existing index; other agents present: %s'
          % sorted(k for k in doc['agents'] if k != 'hank'))
else:
    doc = {'agents': {'hank': {'dirs': [], 'files': []}}}
    print('\nCREATING docs/external-files-index.json')
doc['agents']['hank'] = entry
io.open(OUT, 'w', encoding='utf-8', newline='\n').write(
    json.dumps(doc, indent=1, ensure_ascii=False) + '\n')

back = json.load(io.open(OUT, encoding='utf-8'))
assert 'hank' in back['agents']
assert back['agents']['hank']['dirs'], 'no dirs recorded'
print('wrote %s  (%d bytes, %d dir entries, %d untracked)'
      % (OUT, os.path.getsize(OUT), len(dirs), len(untracked)))
