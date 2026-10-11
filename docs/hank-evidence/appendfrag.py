# -*- coding: utf-8 -*-
"""Append scratchpad/frag.md to the handoff, LF, UTF-8, then empty the fragment.

A heredoc kept breaking on the apostrophes and backticks this handoff is full
of, which is the kind of quoting accident that silently truncates a document.
A file-to-file append cannot do that.
"""
import io
import os
import sys

S = os.path.dirname(os.path.abspath(__file__))
FRAG = os.path.join(S, 'frag.md')
TARGET = sys.argv[1]

frag = io.open(FRAG, encoding='utf-8').read().replace('\r\n', '\n')
if not frag.strip():
    print('COULD NOT RUN: frag.md is empty. Nothing appended.')
    sys.exit(2)
cur = io.open(TARGET, encoding='utf-8').read().replace('\r\n', '\n') \
    if os.path.isfile(TARGET) else ''
if not cur.endswith('\n') and cur:
    cur += '\n'
io.open(TARGET, 'w', encoding='utf-8', newline='\n').write(cur + frag)
io.open(FRAG, 'w', encoding='utf-8', newline='\n').write('')
print('appended %d chars to %s (now %d lines); frag.md emptied'
      % (len(frag), TARGET,
         len(io.open(TARGET, encoding='utf-8').read().split('\n'))))
