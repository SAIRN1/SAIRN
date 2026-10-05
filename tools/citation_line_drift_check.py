#!/usr/bin/env python
"""Does a `:NNNN` line citation in a tier row still point at a WRITE site?

    python tools/citation_line_drift_check.py --app sairnfreedom.html \\
        --prefix sf_ [--doc docs/CRITICALITY-TIERS.md] [--window 40]

WHY, AND WHAT THE FIRST VERSION GOT WRONG. A throwaway detector asked "does the
resource name appear within 40 lines of the cited number", and for SAIRNfreedom it
answered yes almost everywhere -- because every `sf_*` name appears in TWO
DECLARATION BLOCKS near each other:

    var SF_SYNCED=[ 'sf_accounts', 'sf_bottle_fills', ... ]      <- the sync list
    K_ACCOUNTS='sf_accounts', K_SESSIONS='sf_sessions', ...      <- storage keys

A citation landing in either block is not evidence of anything about that
resource. Both blocks contain EVERY name, so a citation pointing into one of them
is "sound" for all 36 resources simultaneously. The detector produced 40 offsets
computed from the first textual occurrence of the name, which is inside the sync
list, so every offset was measured from a line that is the same for every row.

WHAT A WRITE SITE ACTUALLY IS HERE. The app has no per-resource writer: one
generic `sfData('write', key, r)` serves all of them. The per-resource write is
the LOCAL one, `st(K_<CONST>, ...)`, and the mapping from resource to constant is
in the K_ block itself. So this tool resolves resource -> constant -> `st(K_...)`
call sites, and a citation is SOUND only when it is within --window lines of one
of those.

THREE VERDICTS, and the third is not a failure:
  SOUND        the cited line is within --window of a real write site
  DRIFTED      it is not, and a write site exists -- the nearest one is reported
               with the signed offset, as a CANDIDATE and not as an instruction.
               See the next block: this verdict means NOT ANCHORED TO A WRITE
               SITE, which is not the same claim as "the citation has moved".
  INCONCLUSIVE no write site can be resolved. Reported separately and never
               folded into either of the others: a resource whose constant is
               built dynamically, or one written only through the generic
               transport, has no line for a citation to point AT, and saying
               "drifted" would invite a correction to a line that is also wrong.

── DRIFTED WAS AN INSTRUCTION AND IT WAS WRONG FOUR TIMES OUT OF FOUR ─────
This tool used to close with "Each DRIFTED line above is the correction to
apply." Applied literally to SAIRNgrounds on 2026-10-04, that sentence would
have broken four citations that were CORRECT at HEAD:

  grd_irr_zones  :3694   renders `z.last_service`, and the register cell's
                         argument is precisely that the field "is only rendered
                         (`:3694`) with nothing computing an interval from it".
                         Repointing it at the `st()` call would have made the
                         cell's own sentence false.
  grd_rounds     :2975   `var round = {... player_label ...}`
                 :3004   `round.holes.push({arrived_at, completed_at, ...})`
                 :3046   `hole.shots.push({from, to, meters, band_meters, at})`
                         Three citations naming three different field groups --
                         the evidence for that row's Confidentiality A. The
                         "correction" collapsed all three onto one `st()` line,
                         destroying which field group each was about.

A CITATION IS NOT OBLIGED TO POINT AT A WRITE SITE. A criticality cell cites
whatever its argument rests on: a render site to prove a field is only rendered,
a field-construction site to show WHAT is stored. This tool only resolves write
sites, so it cannot tell a STALE citation from a DELIBERATE read-site one, and
it must not pretend otherwise.

WHAT SEPARATED THE TWO POPULATIONS WAS NOT AVAILABLE TO THE TOOL, which is why
no heuristic was added here rather than a guess that would fail silently later:
  sairnfreedom  32 of 32 genuine -- offsets +825 and +834, one uniform forward
                shift, the signature of a block inserted above them.
  sairngrounds   4 of  4 deliberate -- offsets +75, -88, -117, -159, three of
                them NEGATIVE and three belonging to one resource. Not a shift.
So the output now prints THE CITED LINE'S OWN SOURCE TEXT, which decides it in
one read, and the closing line names the nearest write site as a candidate to be
checked against the cell's prose. The judgement moved to where the evidence is;
it did not get automated.

Exit 0 when every citation is SOUND, 1 when any has DRIFTED, 2 COULD NOT RUN --
the app or the document is unreadable, the K_ block cannot be found, or no
citation matched the prefix at all.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def out(s):
    sys.stdout.write(s + '\n')


def opt(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def declaration_spans(lines, prefix):
    """Line ranges (1-indexed, inclusive) that merely NAME resources.

    Two shapes, both real in this codebase and both fatal to a naive window
    match, because each contains EVERY name: the `var X_SYNCED=[...]` sync list
    and the `K_FOO='res'` storage-constant block. A span is grown from any line
    carrying two or more prefixed names, which is the property that makes it a
    declaration rather than a use.
    """
    spans = []
    start = None
    for i, l in enumerate(lines, 1):
        many = len(re.findall(r"'%s[a-z_]+'" % re.escape(prefix), l)) >= 2
        if many and start is None:
            start = i
        elif not many and start is not None:
            spans.append((start, i - 1))
            start = None
    if start is not None:
        spans.append((start, len(lines)))
    return spans


def in_spans(n, spans):
    return any(lo <= n <= hi for lo, hi in spans)


def const_map(lines, prefix):
    """{resource: [constant, ...]} from `K_FOO='res'` declarations."""
    m = {}
    src = '\n'.join(lines)
    for c, res in re.findall(r"\b([A-Z][A-Z0-9_]*)\s*=\s*'(%s[a-z_]+)'"
                             % re.escape(prefix), src):
        m.setdefault(res, []).append(c)
    return m


def write_sites(lines, consts, resource=None):
    """1-indexed lines where this resource is written to local storage.

    TWO SHAPES, because one model did not generalise (measured 2026-09-30). The
    constant form -- `st(K_FOO, ...)` after `K_FOO='res'` -- is sairnfreedom's,
    which declares 42 such constants. Swept across all fourteen apps, 178 of 230
    citations came back INCONCLUSIVE on that model alone: sairnvet declares 6
    constants for 23 cited resources and sairncode declares 2 for 23, because
    those apps write through a LITERAL key instead --
    `setItem('sc_x', ...)` or `st('sc_x', ...)`, 34 of them in sairncode.

    Both are counted. Neither is guessed at: a citation with no write site under
    EITHER shape stays INCONCLUSIVE, which is what the 178 were telling us.
    """
    hits = []
    for i, l in enumerate(lines, 1):
        got = False
        for c in consts:
            if re.search(r'\bst\(\s*%s\b' % re.escape(c), l):
                got = True
                break
        if not got and resource:
            # The literal-key form. `setItem` and this repo's `st()` wrapper are
            # the same act; a READ (`getItem`) is not a write site and must not
            # count, so the two are matched by NAME rather than by the key alone.
            if re.search(r"(?:setItem|\bst)\(\s*'%s'" % re.escape(resource), l):
                got = True
        if got:
            hits.append(i)
    return hits


def citations(doc_lines, prefix):
    rows = []
    for l in doc_lines:
        if not l.startswith('| `%s' % prefix):
            continue
        name = l.split('`')[1]
        for m in re.finditer(r'`:(\d+)`', l):
            rows.append((name, int(m.group(1))))
    return rows


def main(argv):
    app = opt(argv, '--app')
    prefix = opt(argv, '--prefix')
    doc = opt(argv, '--doc', os.path.join('docs', 'CRITICALITY-TIERS.md'))
    window = int(opt(argv, '--window', '40'))
    if not app or not prefix:
        sys.stderr.write('--app and --prefix are both required. Neither is '
                         'guessed from the other: an app file and a resource '
                         'prefix do not follow one rule, and a guess would '
                         'measure the wrong file.\n')
        return 2
    ap = app if os.path.isabs(app) else os.path.join(REPO, app)
    dp = doc if os.path.isabs(doc) else os.path.join(REPO, doc)
    for p in (ap, dp):
        if not os.path.isfile(p):
            sys.stderr.write('COULD NOT RUN -- no such file: %s\n' % p)
            return 2
    lines = io.open(ap, encoding='utf-8', errors='replace').read().split('\n')
    doc_lines = io.open(dp, encoding='utf-8',
                        errors='replace').read().split('\n')

    rows = citations(doc_lines, prefix)
    if not rows:
        sys.stderr.write(
            'COULD NOT RUN -- no `:NNNN` citation on any `%s` row in %s. An '
            'empty run reporting "no drift" is a measurement that did not '
            'happen.\n' % (prefix, doc))
        return 2

    spans = declaration_spans(lines, prefix)
    cmap = const_map(lines, prefix)
    literal_any = any(
        re.search(r"(?:setItem|\bst)\(\s*'%s[a-z_]+'" % re.escape(prefix), l)
        for l in lines)
    if not cmap and not literal_any:
        sys.stderr.write(
            'COULD NOT RUN -- no `K_FOO=\'%sbar\'` storage constants found in '
            '%s, so a resource cannot be resolved to a write site and every '
            'verdict would be INCONCLUSIVE. That is a fact about this tool\'s '
            'assumptions, not about the citations.\n' % (prefix, app))
        return 2

    out('CITATION LINE DRIFT -- %s against %s' % (doc, app))
    out('  citations found        : %d over %d resource(s)'
        % (len(rows), len(set(r[0] for r in rows))))
    out('  declaration spans      : %s' % ', '.join('%d-%d' % s for s in spans))
    out('      A citation inside one of these is NOT evidence: each span names')
    out('      every resource, so it would read as sound for all of them.')
    out('  storage constants found: %d resource(s) mapped' % len(cmap))
    out('')

    sound, drift, incon = [], [], []
    for name, n in rows:
        consts = cmap.get(name) or []
        sites = write_sites(lines, consts, resource=name)
        if not sites:
            why = ('no storage constant declared for it, and no literal '
                   "setItem('%s') or st('%s') write either" % (name, name)
                   if not consts else
                   'constants %s are declared but never written with st(), '
                   'and there is no literal-key write either'
                   % ','.join(consts))
            incon.append((name, n, why))
            continue
        near = [s for s in sites if abs(s - n) <= window]
        if near:
            sound.append((name, n, near[0]))
            continue
        nearest = min(sites, key=lambda s: abs(s - n))
        # THE CITED LINE ITSELF, because it is what decides stale-vs-deliberate
        # and the reader should not have to open the file to see it. 1-indexed.
        cited = lines[n - 1].strip() if 0 < n <= len(lines) else ''
        drift.append((name, n, nearest, nearest - n,
                      in_spans(n, spans), cited))

    for name, n, site in sound:
        out('  SOUND        %-26s :%-6d write site :%d within %d lines'
            % (name, n, site, window))
    for name, n, site, off, indecl, cited in drift:
        out('  DRIFTED      %-26s :%-6d -> :%-6d offset %+d%s'
            % (name, n, site, off,
               '   (the cited line is INSIDE a declaration block, which is why '
               'the first detector called it sound)' if indecl else ''))
        # Truncated, because one long minified line would bury every other
        # verdict -- but never omitted: this line IS the evidence.
        out('                 cited line reads: %s'
            % ((cited[:140] + ' ...') if len(cited) > 140 else cited))
    for name, n, why in incon:
        out('  INCONCLUSIVE %-26s :%-6d %s' % (name, n, why))

    out('')
    out('  SOUND        : %d' % len(sound))
    out('  DRIFTED      : %d' % len(drift))
    out('  INCONCLUSIVE : %d -- no write site to point at, so NOT reported as '
        'drifted' % len(incon))
    if drift:
        out('')
        out('DRIFTED means NOT ANCHORED TO A WRITE SITE. It does NOT mean the '
            'citation has moved, and the arrow is a CANDIDATE, not a correction '
            'to apply.')
        out('Before repointing any line above, read the register cell\'s own '
            'prose against the `cited line reads:` text. A cell may cite a '
            'render or field-construction site DELIBERATELY -- to prove a field '
            'is only rendered, or to show which fields are stored -- and this '
            'tool resolves write sites only, so it cannot tell those from a '
            'stale citation.')
        out('Measured both ways: sairnfreedom 32/32 were genuine drift (one '
            'uniform +825/+834 shift); sairngrounds 4/4 were deliberate '
            'read-site citations and repointing them would have broken four '
            'correct cells. Nothing here edits the document.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
