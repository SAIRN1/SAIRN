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

FOUR VERDICTS, and RANKING IS THE POINT -- see the ranking block further down.
  ANCHORED     the cited line NAMES the resource, or reaches it within two
               hops. A direct reference, and it OUTRANKS distance: proximity
               to a write is only a proxy for "this line is about the
               resource", and on sd_comms the proxy inverted -- a comment 13
               lines from the write scored above the real call site 55 lines
               away, so repointing the citation correctly made the number
               worse.
  SOUND        no direct reference, but within --window of a real write site.
               The original rule, DEMOTED to a fallback
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

Exit 0 when nothing DRIFTED, 1 when anything did, 2 COULD NOT RUN --
the app or the document is unreadable, the K_ block cannot be found, or no
citation matched the prefix at all.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── THIS TOOL CRASHED MID-SWEEP AND REPORTED ZEROS (found 2026-10-05) ──────
# The `cited line reads:` line added yesterday prints ARBITRARY APP SOURCE, and
# sairnlegacy.html carries non-ASCII in a cited line. On a cp1252 console that
# raised UnicodeEncodeError part-way through the leg_ run, so a sweep driving
# all 18 prefixes recorded leg_ as SOUND=0 DRIFTED=0 INCONCLUSIVE=0 over 51
# citations -- a CRASH read as a clean file.
#
# FOURTH INSTANCE OF THIS CLASS IN ONE DAY: tools/push_retry.py could not print
# its own usage, my own derivation script died on it, my own commit-message
# filter died on it, and now this. 237 of 286 tools/*.py carry non-ASCII with
# no reconfigure -- that is a PRECONDITION count and not a crash count, but
# four live hits in a day says the population is not dormant.
#
# AND THE FEATURE THAT BROKE IT WAS MINE, added yesterday for a good reason:
# printing the cited line is what lets a reader tell a stale citation from a
# deliberate one. The lesson is not "do not print source" -- it is that the
# moment a tool starts echoing arbitrary file content, its output encoding
# stops being its own business.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


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


# ── THE TOOL READ 60% OF ITS SUBJECT AND DID NOT SAY SO (found 2026-10-05) ──
# `citations()` matched only the BARE form, `` `:NNN` ``. Measured over
# docs/CRITICALITY-TIERS.md at HEAD before this change:
#
#     bare  `:NNN`            285   <- the only form the tool read
#     named `file.html:NNN`   188   <- INVISIBLE to it, across 147 rows
#
# So every verdict this tool ever printed covered 285 of 473 citations and
# presented it as the answer. That is the coverage-disclosure class, and it is
# not academic: `sb_perf`'s TWO genuinely drifted citations were both in the
# invisible 188 and were found by hand-reading the row, not by the tool --
# `sairnbiz.html:448` had become a Cancel button in the hire modal, and `:4714`
# had become the training KPI tiles. The tool meanwhile reported a DRIFTED
# verdict on that row's only bare citation, where the citation was correct.
#
# A NAMED CITATION MUST BE RESOLVED AGAINST THE FILE IT NAMES, which is the
# half that makes this more than a regex widening. 188 of them include
# `api/sd-data.js:2051` and `stonedesk.html:25608` -- on rows swept with
# `--app sairngrounds.html`. Resolving those against --app would compare a
# line number to the wrong file and invent drift with total confidence. So each
# citation now carries its own file, --app is the default for the bare form
# only, and a file this tool cannot read is COULD-NOT-RESOLVE rather than
# drifted.
#
# RANGES ARE ANCHORED ON THEIR FIRST LINE. `:6752-6760` is one citation whose
# subject starts at 6752; treating the end as a second citation would double
# count, and treating the span as sound-if-any-line-is-near would make a
# 40-line window into an 80-line one.
CITE_RE = re.compile(
    r'`(?:(?P<file>[A-Za-z0-9_./-]+\.(?:html|js))\s*)?:(?P<line>\d+)'
    r'(?:-\d+)?`')


# ── THE RANKING WAS WRONG, NOT THE COUNT (found 2026-10-05) ────────────────
# Distance to a write site was the ONLY signal, so proximity decided the
# verdict -- and proximity is a PROXY for "this line is about the resource".
# Measured on sd_comms, where the proxy inverted:
#
#   :10539  a comment, 13 lines from the write  -> scored SOUND
#   :10582  `var d=commsEnsureIds();`, 55 away  -> scored DRIFTED
#
# The three :10539/:10575/:10606 citations were WRONG -- the auditor's own read
# says they were "the function DEFINITION area and unrelated helpers" -- and
# they scored above the three RIGHT ones at :10582/:10618/:10649, which are the
# real call sites. Repointing them correctly made the tool's number worse. A
# checker that ranks a correct citation below an incorrect one is worse than no
# ranking, because it rewards the wrong edit.
#
# SO A DIRECT REFERENCE NOW OUTRANKS DISTANCE, and the chain is resolved the
# way a reader resolves it rather than by a name heuristic:
#
#   ANCHORED        the cited line itself names the resource -- its literal
#                   key, or one of its storage constants. Unambiguous.
#   ANCHORED-VIA    the cited line CALLS a function that reaches the resource
#                   within two hops, each hop resolved to the NEAREST PRECEDING
#                   definition of that name. commsEnsureIds@10552 calls load;
#                   the nearest preceding `function load` is @10526, which is
#                   `getItem('sd_comms')`. Labelled separately because it is
#                   derived rather than read off the line.
#   SOUND           none of the above, but within --window of a write site.
#                   The old rule, DEMOTED to a fallback.
#   DRIFTED         none of the above.
#
# NEAREST-PRECEDING IS THE HONEST RESOLUTION AND ITS LIMIT IS NAMED. This file
# has 23 functions called `render` and many called `load`; the repo already
# records 34 bare functions as NOT JUDGED for exactly that reason. Nearest
# preceding is what a human reading top-to-bottom would pick, it is right
# inside an IIFE, and it can be wrong across one. Two hops is the cap: a third
# would reach half the file through `load`.
_DEF_RE = r'(?:function\s+%s\s*\(|(?:var|let|const)\s+%s\s*=\s*function|%s\s*[:=]\s*function)'
_CALL_RE = re.compile(r'\b([A-Za-z_$][A-Za-z0-9_$]*)\s*\(')


def _direct_line(line, resource, consts):
    """True when this line names the resource outright."""
    if resource and ("'%s'" % resource) in line:
        return True
    for c in consts:
        if re.search(r'\b%s\b' % re.escape(c), line):
            return True
    return False


def _nearest_def(lines, name, before):
    """Line number of the nearest definition of `name` at or before `before`."""
    pat = re.compile(_DEF_RE % (re.escape(name), re.escape(name),
                                re.escape(name)))
    for i in range(min(before, len(lines)) - 1, -1, -1):
        if pat.search(lines[i]):
            return i + 1
    return None


def _body_lines(lines, start, limit=60):
    """The `limit` lines from a definition -- a bounded read, not a parse.

    A brace-matched body would be better and is not worth it here: the
    question is only whether the resource is reachable, and a definition whose
    reference is more than 60 lines in is not one a reader would call an
    accessor either.
    """
    return lines[start - 1:min(start - 1 + limit, len(lines))]


def anchor_verdict(lines, n, resource, consts, hops=2):
    """(kind, detail) for the cited line itself. kind is '', 'direct' or 'via'."""
    if not (0 < n <= len(lines)):
        return '', ''
    line = lines[n - 1]
    if _direct_line(line, resource, consts):
        return 'direct', 'the cited line names the resource'
    seen = set()
    frontier = [(t, n) for t in _CALL_RE.findall(line)]
    for depth in range(1, hops + 1):
        nxt = []
        for name, before in frontier:
            if name in seen or name in ('if', 'for', 'while', 'return',
                                        'function', 'catch', 'switch',
                                        'typeof', 'parseInt', 'parseFloat'):
                continue
            seen.add(name)
            d = _nearest_def(lines, name, before)
            if d is None:
                continue
            body = _body_lines(lines, d)
            for bl in body:
                if _direct_line(bl, resource, consts):
                    return 'via', ('%s() at :%d reaches it in %d hop(s)'
                                   % (name, d, depth))
            for bl in body:
                for t in _CALL_RE.findall(bl):
                    nxt.append((t, d))
        frontier = nxt
        if not frontier:
            break
    return '', ''


def citations(doc_lines, prefix, default_file=None):
    """[(resource, line, file)] for every citation form on a prefixed row.

    `file` is the file the citation NAMES, or `default_file` for the bare form.
    """
    rows = []
    for l in doc_lines:
        if not l.startswith('| `%s' % prefix):
            continue
        name = l.split('`')[1]
        for m in CITE_RE.finditer(l):
            rows.append((name, int(m.group('line')),
                         m.group('file') or default_file))
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

    rows = citations(doc_lines, prefix, default_file=app)
    if not rows:
        sys.stderr.write(
            'COULD NOT RUN -- no `:NNNN` citation on any `%s` row in %s. An '
            'empty run reporting "no drift" is a measurement that did not '
            'happen.\n' % (prefix, doc))
        return 2

    # ── EVERY CITED FILE IS LOADED, and one that cannot be is NAMED ────────
    # A citation naming api/sd-data.js on a row swept with --app sairnbiz.html
    # must be resolved against api/sd-data.js. Comparing it to --app would
    # measure the wrong file and report drift with total confidence.
    files = {}
    unresolvable = []
    for _f in sorted(set(r[2] for r in rows if r[2])):
        _p = _f if os.path.isabs(_f) else os.path.join(REPO, _f)
        try:
            files[_f] = io.open(_p, encoding='utf-8',
                                errors='replace').read().split('\n')
        except OSError as exc:
            unresolvable.append('%s (%s)' % (_f, exc.strerror or 'unreadable'))

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
    # ── THE DENOMINATOR, PRINTED. This tool read 60% of its subject and said
    # nothing; the whole defect was the silence, not the regex.
    _bare = sum(1 for r in rows if r[2] == app)
    _named = len(rows) - _bare
    out('  by form                : %d bare `:NNN` (resolved against --app), '
        '%d naming their own file' % (_bare, _named))
    if files:
        out('  files resolved         : %s'
            % ', '.join('%s (%d lines)' % (f, len(l))
                        for f, l in sorted(files.items())))
    if unresolvable:
        out('  COULD NOT RESOLVE      : %s' % '; '.join(unresolvable))
        out('      Those citations are reported INCONCLUSIVE below, never '
            'drifted: a line number compared against a file this run could '
            'not read is not a measurement.')
    out('  declaration spans      : %s' % ', '.join('%d-%d' % s for s in spans))
    out('      A citation inside one of these is NOT evidence: each span names')
    out('      every resource, so it would read as sound for all of them.')
    out('  storage constants found: %d resource(s) mapped' % len(cmap))
    out('')

    sound, drift, incon, anchored = [], [], [], []
    for name, n, cfile in rows:
        # RESOLVED AGAINST THE FILE THE CITATION NAMES. `lines` (= --app) is
        # the default for the bare form only.
        flines = files.get(cfile)
        if flines is None:
            incon.append((name, n, 'cites %s, which this run could not read -- '
                                   'COULD NOT RESOLVE, not drifted' % cfile))
            continue
        # Declaration spans and the constant map are properties of --app, so
        # they only apply to citations INTO --app. A citation into another file
        # gets the literal-key shape only, which is the honest subset.
        same_app = (cfile == app)
        consts = (cmap.get(name) or []) if same_app else []
        sites = write_sites(flines, consts, resource=name)
        if not sites:
            why = ('no storage constant declared for it, and no literal '
                   "setItem('%s') or st('%s') write either" % (name, name)
                   if not consts else
                   'constants %s are declared but never written with st(), '
                   'and there is no literal-key write either'
                   % ','.join(consts))
            if not same_app:
                why += ' in %s (the file this citation names)' % cfile
            incon.append((name, n, why))
            continue
        # ── RANKING: A DIRECT REFERENCE OUTRANKS DISTANCE ──────────────────
        # Checked BEFORE the window, which is the whole fix. sd_comms' three
        # correct call sites are 55-122 lines from the write and the three
        # wrong ones were 13-45; under the old order the wrong ones won.
        # ── A DECLARATION BLOCK CAN NEVER ANCHOR, AND THIS ARRIVED AS A
        #    REGRESSION I SHIPPED. ──────────────────────────────────────────
        # The first version of the ranking checked anchoring first, and the
        # existing control caught it immediately: a sync list or a K_ block
        # literally contains EVERY resource name, so `_direct_line` returned
        # True and a citation into one scored ANCHORED -- for all 36 resources
        # at once. That is the ORIGINAL defect this whole tool was built to
        # prevent, reintroduced by the fix for a different one.
        #
        # So the exclusion comes FIRST. A direct reference outranks distance,
        # and a declaration block outranks both.
        _in_decl = in_spans(n, spans) if same_app else False
        kind, why = ('', '') if _in_decl else anchor_verdict(
            flines, n, name, consts)
        if kind:
            anchored.append((name, n, cfile, kind, why))
            continue
        near = [s for s in sites if abs(s - n) <= window]
        if near:
            sound.append((name, n, near[0], cfile))
            continue
        nearest = min(sites, key=lambda s: abs(s - n))
        # THE CITED LINE ITSELF, because it is what decides stale-vs-deliberate
        # and the reader should not have to open the file to see it. 1-indexed.
        cited = flines[n - 1].strip() if 0 < n <= len(flines) else ''
        drift.append((name, n, nearest, nearest - n,
                      in_spans(n, spans) if same_app else False, cited, cfile))

    for name, n, cfile, kind, why in anchored:
        out('  ANCHORED%-4s %-26s %s:%-6d %s'
            % ('' if kind == 'direct' else '-VIA', name,
               '' if cfile == app else cfile, n, why))
    for name, n, site, cfile in sound:
        out('  SOUND        %-26s %s:%-6d write site :%d within %d lines'
            % (name, '' if cfile == app else cfile, n, site, window))
    for name, n, site, off, indecl, cited, cfile in drift:
        out('  DRIFTED      %-26s %s:%-6d -> :%-6d offset %+d%s'
            % (name, '' if cfile == app else cfile, n, site, off,
               '   (the cited line is INSIDE a declaration block, which is why '
               'the first detector called it sound)' if indecl else ''))
        # Truncated, because one long minified line would bury every other
        # verdict -- but never omitted: this line IS the evidence.
        out('                 cited line reads: %s'
            % ((cited[:140] + ' ...') if len(cited) > 140 else cited))
    for name, n, why in incon:
        out('  INCONCLUSIVE %-26s :%-6d %s' % (name, n, why))

    out('')
    out('  ANCHORED     : %d -- the cited line names the resource, or reaches '
        'it in <=2 hops. This OUTRANKS distance: proximity to a write is a '
        'proxy, and on sd_comms the proxy inverted.' % len(anchored))
    out('  SOUND        : %d -- no direct reference, but within the window of '
        'a write site. The old rule, now a FALLBACK.' % len(sound))
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
