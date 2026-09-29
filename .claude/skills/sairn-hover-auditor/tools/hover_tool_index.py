#!/usr/bin/env python
"""hover_tool_index.py -- the reuse-loop closer this role's own tools were
missing. Built 2026-09-16, direct instruction, after checking and finding a
real gap: this role's tools were documented across at least two scattered
SKILL.md prose sections ("Four tool proposals", "Two more tools, built
2026-09-16") with no single, current list -- exactly the shape that makes a
future session rebuild something that already exists rather than find it,
which is the specific failure a reuse loop exists to prevent.

GENERATED, NOT HAND-WRITTEN, same discipline docs/TOOLING-INVENTORY.md
already uses for the platform's own tools, for the identical reason: a
hand-maintained list goes stale the moment a tool is added and nobody
remembers to update the list. This reads the real files on disk and each
one's own opening docstring line -- run it, do not trust a prose summary
written about it once and left to rot.

Run:  python hover_tool_index.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {'hover_tool_index.py', '__pycache__'}


def first_summary_line(path):
    """The first real sentence of the file's own opening docstring, or
    '(no docstring found)' -- named honestly rather than skipped, because a
    tool with no summary is itself a finding about the index, not a reason
    to silently omit a row."""
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read(2000)
    except OSError as e:
        return '(could not read: %s)' % e
    m = re.search(r'"""(?:#!.*\n)?\s*r?"""?\s*([^\n]+(?:\n[^\n]+)?)', text)
    # Simpler, more robust: find the first triple-quoted block, take its
    # first non-empty line after the opening quotes.
    q = re.search(r'"""', text)
    if not q:
        return '(no docstring found)'
    after = text[q.end():]
    for line in after.split('\n'):
        line = line.strip()
        if line:
            return line[:140]
    return '(empty docstring)'


def main():
    py_files = sorted(f for f in os.listdir(HERE)
                      if f.endswith('.py') and f not in SKIP)
    if not py_files:
        print('COULD NOT RUN -- no .py files found in %s. An empty index is '
             'not the same as a checked-and-genuinely-empty one.' % HERE)
        return 2

    print('HOVER AUDITOR TOOL INDEX -- generated from %s, %d file(s)' % (HERE, len(py_files)))
    print('Run any tool directly: python <name> [args]')
    print()
    for f in py_files:
        summary = first_summary_line(os.path.join(HERE, f))
        print('  %-38s %s' % (f, summary))
    return 0


if __name__ == '__main__':
    sys.exit(main())
