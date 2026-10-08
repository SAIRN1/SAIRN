# -*- coding: utf-8 -*-
"""ITEM 11 -- MERGE two keys into ~/.claude/settings.json. Never overwrite.

THE FILE IS 9KB OF PERMISSIONS, DENY RULES AND HOOKS that four other sessions
depend on. The failure this guards against is specific and has happened on this
box: batch 23 of cody spent an item on "find what removed the model key from the
global settings file between 12:44 and 14:30". A whole-file write is how that
happens.

SO: read, back up with a timestamp, set exactly two keys, write, re-read, and
DIFF THE KEY SETS -- if any key present before is absent after, that is a
failure, not a warning.
"""
import io
import json
import os
import shutil
import sys
import time

P = os.path.join(os.path.expanduser('~'), '.claude', 'settings.json')
S = os.path.dirname(os.path.abspath(__file__))

if not os.path.isfile(P):
    sys.stderr.write('COULD NOT RUN: %s does not exist. Nothing written -- '
                     'creating it would discard whatever the real one holds '
                     'elsewhere.\n' % P)
    sys.exit(2)

raw = io.open(P, encoding='utf-8').read()
try:
    before = json.loads(raw)
except ValueError as e:
    sys.stderr.write('COULD NOT RUN: %s is not valid JSON (%s). NOTHING '
                     'WRITTEN -- a rewrite of a file I cannot parse would '
                     'destroy it.\n' % (P, e))
    sys.exit(2)

bak = os.path.join(S, 'settings.json.bak.%s'
                   % time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
shutil.copy(P, bak)
print('backed up to %s (%d bytes)' % (bak, os.path.getsize(bak)))


def keyset(d, prefix=''):
    out = set()
    for k, v in (d or {}).items():
        out.add(prefix + k)
        if isinstance(v, dict):
            out |= keyset(v, prefix + k + '.')
    return out


ks_before = keyset(before)
print('keys before: %d   top level: %s' % (len(ks_before), sorted(before)))

after = json.loads(json.dumps(before))      # deep copy, not a reference

# 1. autoCompactWindow
prev = after.get('autoCompactWindow')
after['autoCompactWindow'] = 150000
print('autoCompactWindow: %s -> 150000' % ('(absent)' if prev is None else prev))

# 2. env.BASH_MAX_OUTPUT_LENGTH -- MERGED INTO env, not replacing it
if not isinstance(after.get('env'), dict):
    after['env'] = {}
prev_b = after['env'].get('BASH_MAX_OUTPUT_LENGTH')
after['env']['BASH_MAX_OUTPUT_LENGTH'] = '10000'
print('env.BASH_MAX_OUTPUT_LENGTH: %s -> 10000  %s'
      % ('(absent)' if prev_b is None else prev_b,
         '(ALREADY SET TO THIS VALUE -- no change)' if prev_b == '10000'
         else ''))

io.open(P, 'w', encoding='utf-8', newline='\n').write(
    json.dumps(after, indent=2, ensure_ascii=False) + '\n')

# -- VERIFY BY RE-READING FROM DISK, and compare the KEY SETS.
back = json.loads(io.open(P, encoding='utf-8').read())
ks_after = keyset(back)
lost = sorted(ks_before - ks_after)
if lost:
    shutil.copy(bak, P)
    sys.stderr.write('FAILED: %d key(s) would have been LOST: %s\n'
                     'The backup has been restored and the file is as it was.\n'
                     % (len(lost), ', '.join(lost[:20])))
    sys.exit(1)
gained = sorted(ks_after - ks_before)
print('keys after : %d   gained: %s   lost: none' % (len(ks_after), gained))
print('autoCompactWindow on disk        : %r' % back.get('autoCompactWindow'))
print('env.BASH_MAX_OUTPUT_LENGTH on disk: %r'
      % back.get('env', {}).get('BASH_MAX_OUTPUT_LENGTH'))
print('permissions.allow entries kept   : %d'
      % len(back.get('permissions', {}).get('allow', [])))
print('permissions.deny entries kept    : %d'
      % len(back.get('permissions', {}).get('deny', [])))
print('hooks kept                       : %s'
      % sorted(back.get('hooks', {})))
