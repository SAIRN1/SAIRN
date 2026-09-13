"""closing_error.py -- a generated document must CLOSE against its sources.

    from closing_error import Traverse
    t = Traverse('docs/TOOLING-INVENTORY.md')
    t.leg('tools on disk', len(tools), 'git ls-files tools/')
    t.leg('hook entries', len(hk), '.claude/settings.json')
    t.close()                      # refuses, loudly, if any leg is empty

── WHY THIS EXISTS ──────────────────────────────────────────────────────────
`--check` on a generated document compares it to what the generator produces
TODAY. Both ends of that comparison come from the same instrument. It proves
nobody hand-edited the file. **It cannot prove the generator still reads what
it used to read**, and a generator that has quietly stopped reading a source
produces a document that is confidently, consistently wrong -- and passes its
own check every time.

In surveying terms `--check` re-measures the last leg and calls the traverse
closed. A real traverse returns to a KNOWN POINT and reports the closing error.

**IT IS NOT A HYPOTHETICAL. Both demonstrations are from tooling_inventory.py
on 2026-09-13, and `--check` was byte-clean through both:**

  * its probe column named the wrong test file for TWENTY-SEVEN tools, because
    a comment mentioning a tool counted as running it. The document faithfully
    matched a reader that was wrong.
  * fixing that, the pre-filter tested the FILENAME while `import x as M` never
    writes `.py`, so five promoted checkers with thorough controls briefly
    showed NO PROBE AT ALL.

The second one is exactly what this module catches: a source going to zero.
The first is not, and that is said plainly below rather than implied away.

── WHAT IT CATCHES, AND WHAT IT CANNOT ──────────────────────────────────────

  IT CATCHES   a derivation source that contributes NOTHING. A renamed key, a
               moved file, a regex that stopped matching, a directory that is
               no longer walked. Zero is the one value a broken reader and an
               empty repo both produce, and only one of those is a document.

  IT CANNOT    tell a source that returns the WRONG non-zero answer from one
               that returns the right one. Twenty-seven wrong probe
               attributions is a non-zero count. That needs the source's own
               control, not this. **A closed traverse is not a correct survey**
               -- it only means no leg is missing.

So this is a floor, and it is stated as a floor in the report it prints. The
alternative -- a document that reads as derived while deriving from nothing --
is the failure mode every convention in
`docs/2026-09-13-cross-domain-disciplines.md` defends against.

── THE REPORT IS A NAMED, ITEMIZED TABLE ────────────────────────────────────
Convention 3: one row per contributor, naming it and what it was read from,
never a combined figure. The generated document carries the table, so a reader
sees which legs closed rather than a bare "OK".

Exit 2 on a refusal, never 1: this is COULD NOT DERIVE, not A FINDING, and the
two must not be confused by anything reading an exit code.
"""
import sys


class EmptyLeg(Exception):
    """A derivation source contributed nothing. The document was not written."""


class Traverse(object):
    """The legs of one document's derivation, and whether they all closed."""

    def __init__(self, doc):
        self.doc = doc
        self.legs = []          # (name, count, source, allow_zero, why)

    def leg(self, name, count, source):
        """One derivation source that MUST contribute. Zero is a refusal."""
        self.legs.append((name, int(count), source, False, ''))
        return count

    def optional_leg(self, name, count, source, why):
        """A source that may legitimately be zero -- with the REASON required.

        An allowance without a reason beside it is a silence, the same rule
        every exemption table in this repo carries. `why` is not optional and
        an empty one raises here rather than at read time.
        """
        if not (why or '').strip():
            raise ValueError(
                'optional_leg(%r) needs a REASON. A source allowed to be empty '
                'without one is indistinguishable from a broken reader.' % name)
        self.legs.append((name, int(count), source, True, why))
        return count

    def empty(self):
        return [l for l in self.legs if l[1] == 0 and not l[3]]

    def table(self):
        """The named, itemized report -- for the document and for stdout."""
        if not self.legs:
            return ['(no legs declared -- this traverse asserts nothing)']
        w = max(len(l[0]) for l in self.legs)
        out = []
        for name, count, source, allow_zero, why in self.legs:
            mark = '' if count else ('  (zero, allowed: %s)' % why[:60]
                                     if allow_zero else '  <<< EMPTY')
            out.append('  %-*s %6d   %s%s' % (w, name, count, source, mark))
        return out

    def close(self, out=None):
        """Print the table; refuse if any required leg is empty.

        Returns the table lines so the caller can embed them in the document.
        """
        write = (out or sys.stdout).write
        write('CLOSING ERROR -- %s derives from %d source(s):\n'
              % (self.doc, len(self.legs)))
        for line in self.table():
            write(line + '\n')
        bad = self.empty()
        if bad:
            write('\n')
            write('REFUSED: %d derivation source(s) contributed NOTHING, so this\n'
                  % len(bad))
            write('document would have been written from less than it claims:\n')
            for name, _c, source, _a, _w in bad:
                write('  %s -- read from %s\n' % (name, source))
            write('\n')
            write('A zero here is a BROKEN READER or a MOVED SOURCE, not an empty\n')
            write('repo -- and the two are indistinguishable downstream, which is\n')
            write('why this refuses instead of writing a thinner document that\n')
            write('would pass its own --check every time.\n')
            raise EmptyLeg('%s: %d empty source(s): %s'
                           % (self.doc, len(bad), ', '.join(b[0] for b in bad)))
        write('every leg closed. NOTE: a closed traverse is not a correct '
              'survey --\n')
        write('it means no source is MISSING, not that any source is RIGHT.\n')
        return self.table()
