"""Item 102 -- ONE freshness gate for every register cell, replacing four narrow ones.

    python tools/register_freshness_check.py                # both registers
    python tools/register_freshness_check.py --json
    python tools/register_freshness_check.py --fixtures     # blind lock, judges nothing real

Exit 0 every checked citation verifies, 1 any DRIFTED, 2 when nothing could be
checked at all. REPORT ONLY, ADVISORY PER ITEM -- never a fleet-wide hard
block, by decision: a register with one stale cell must not freeze every
unrelated push, which is the exact refusal shape check 12's scoping already
established for generated documents.

── WHY ONE TOOL AND NOT A FIFTH NARROW ONE ─────────────────────────────────
The platform re-invented this check four times, each scoped to one subject:
`sairn_app_map_check.py` (Guardian's app map vs live routes),
`tool_provenance_check.py` (tool docs vs their sources, where it exists),
`sairn_claim_doc_freshness.py` (sairn_claim.py's own docstring rows), and the
SPOF retirement checker's citation half. Each does the same thing with a
different walker: compare COMMITTED EVIDENCE against FRESHLY-RECOMPUTED TRUTH
and fail loud on mismatch. Meanwhile the two documents auditors actually read
-- docs/CRITICALITY-TIERS.md and docs/tier-a-reviews.json -- had NO citation
check at all, and the cost is measured, not argued: on 2026-09-24 all NINE
line citations on one tier row (`sc_anesthesia_base_units`) were found 30-45
lines stale within a DAY of being written, caught only because a review
obligation happened to send a reader to that exact row. Sourced context:
Tan/Wagner/Treude 2022 (arXiv 2212.01479) measure the same decay in
code-comment/README drift at scale; the pattern here is their finding, local.

── THE ONE RULE THAT IS NOT NEGOTIABLE ─────────────────────────────────────
COMPARE, NEVER REGENERATE-THEN-PASS. This tool re-derives the truth and
reports the mismatch; it never edits a register to make the comparison come
out clean. A freshness gate that repairs its subject is a generator, and a
generator judging its own output is the drift shape discipline 8 exists for
(`--check` comparing a document to its own output).

── WHAT A CITATION IS, PER REGISTER ────────────────────────────────────────
docs/CRITICALITY-TIERS.md evidence cells carry three checkable claim shapes:

  file:line   `sairncode.html:4989` and the short form `` `:5014` `` (resolved
              against the nearest preceding full cite in the same cell).
              TRUTH: the file's current content. COMPARATOR: the nearest
              backtick `identifier` written within 90 characters BEFORE the
              cite in the cell -- the register's own convention is to name the
              function beside its line -- must appear within +/-8 lines of the
              cited line. A cite with no adjacent identifier is UNVERIFIABLE:
              counted, printed, never folded into pass, because an
              uncheckable citation is exactly where drift hides.
  bare path   `api/sd-data.js`, `sql/...` -- must exist in the tree.
  short sha   8-12 hex -- must resolve to a commit.

docs/tier-a-reviews.json records carry `files` (paths -- must exist; a record
about a file that is GONE is a record a reader can no longer check) and shas
embedded in `what`/`verdict` prose (must resolve).

── HONEST LIMITS, NAMED ────────────────────────────────────────────────────
* The identifier-within-8-lines comparator verifies the cite still points AT
  the named thing; it cannot verify the surrounding ARGUMENT is still true.
  That stays a human read, per the tier file's own note that nothing
  mechanical can say the tier is right.
* Shas the reseat tool repairs may be transiently dangling mid-rebase; this
  runs against the working tree and says so rather than guessing.
* The four narrow tools are NOT retired, and after measuring, they must not
  be. PARITY AUDIT, 2026-09-25, before any retirement: 0 of 4 are covered by
  this tool, so retiring any would DELETE a check rather than consolidate
  one. `sairn_app_map_check.py` compares a declared route against a LIVE
  FETCH of the deployment -- nothing here fetches anything. `claim_provenance
  .py` is item 23's RECORDING half and deliberately judges nothing, so there
  is no comparison to be at parity with. `sairn_claim_doc_freshness.py`
  checks a TOOL'S OWN prose against CLAUDE.md, the claims directory and the
  status directory -- none of which this reads. `dependency_graph.py`'s SPOF
  retirement half recomputes a dependency GRAPH against
  docs/SPOF-REGISTER.md, a register this tool does not open.
  WHAT WAS TRUE was that each re-invented the SHAPE -- compare committed
  evidence against freshly recomputed truth. Sharing a shape is not sharing a
  subject, and consolidation that goes by resemblance is how coverage
  disappears quietly.
  DECIDED 2026-09-25 (Michael), and this paragraph is the record so nobody
  re-opens it: KEEP ALL FOUR. The parity audit proved they cover genuinely
  different subjects, and there is NO shared-helper refactor -- the
  re-invention is a cost worth paying against the alternative of a fifth
  abstraction that every future checker has to be bent to fit. This tool is
  the fifth CHECK, not the one that replaces four.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIERS = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
REVIEWS = os.path.join(REPO, 'docs', 'tier-a-reviews.json')

# Backtick file:line, e.g. `sairncode.html:4989` or `api/sd-data.js:11749`
FULL_CITE = re.compile(r'`([A-Za-z0-9_./-]+\.(?:html|js|py|sql|md)):(\d{1,6})`')
# Backtick short form `:5014`
SHORT_CITE = re.compile(r'`:(\d{1,6})`')
# The identifier the register names beside a cite. Searched BEFORE the cite.
NEAR_IDENT = re.compile(r'`([A-Za-z_$][A-Za-z0-9_$.]{2,60})(?:\(\))?`')
BARE_PATH = re.compile(r'`((?:api|sql|tools|tests|docs)/[A-Za-z0-9_./-]+\.[a-z]{2,4})`')
SHA = re.compile(r'\b([0-9a-f]{8,12})\b')

IDENT_WINDOW = 8      # lines either side of the cited line
IDENT_LOOKBACK = 90   # chars before the cite in which the identifier is named


class CouldNotTell(Exception):
    pass


def _lines_of(path_cache, rel):
    if rel not in path_cache:
        p = os.path.join(REPO, rel)
        if not os.path.isfile(p):
            path_cache[rel] = None
        else:
            path_cache[rel] = io.open(p, encoding='utf-8',
                                      errors='replace').read().split('\n')
    return path_cache[rel]


def _sha_resolves(sha, memo):
    if sha not in memo:
        r = subprocess.run(['git', 'rev-parse', '--verify', '--quiet',
                            sha + '^{commit}'], cwd=REPO, capture_output=True)
        memo[sha] = (r.returncode == 0)
    return memo[sha]


def check_cell(cell_id, text, path_cache, sha_memo):
    """-> list of (status, detail) where status is OK|DRIFTED|UNVERIFIABLE."""
    out = []
    current_file = None
    # walk cites in order so short cites resolve against the last full one
    events = sorted(
        [(m.start(), 'full', m) for m in FULL_CITE.finditer(text)] +
        [(m.start(), 'short', m) for m in SHORT_CITE.finditer(text)])
    for pos, kind, m in events:
        if kind == 'full':
            rel, line = m.group(1), int(m.group(2))
            current_file = rel
        else:
            if not current_file:
                out.append(('UNVERIFIABLE',
                            '%s: short cite `:%s` with no preceding file cite '
                            'in the cell' % (cell_id, m.group(1))))
                continue
            rel, line = current_file, int(m.group(1))
        lines = _lines_of(path_cache, rel)
        if lines is None:
            out.append(('DRIFTED', '%s: cites %s:%d and the FILE DOES NOT '
                        'EXIST' % (cell_id, rel, line)))
            continue
        if line > len(lines):
            out.append(('DRIFTED', '%s: cites %s:%d and the file has only %d '
                        'lines' % (cell_id, rel, line, len(lines))))
            continue
        # the identifier named just before the cite
        back = text[max(0, pos - IDENT_LOOKBACK):pos]
        idents = NEAR_IDENT.findall(back)
        ident = idents[-1] if idents else None
        if not ident:
            out.append(('UNVERIFIABLE', '%s: %s:%d has no named identifier '
                        'within %d chars before it -- the cite cannot be '
                        'checked against anything' % (cell_id, rel, line,
                                                      IDENT_LOOKBACK)))
            continue
        lo, hi = max(0, line - 1 - IDENT_WINDOW), min(len(lines), line + IDENT_WINDOW)
        window = '\n'.join(lines[lo:hi])
        base = ident.split('.')[-1]
        if base in window:
            out.append(('OK', '%s: %s:%d ~ `%s`' % (cell_id, rel, line, ident)))
        else:
            hits = [n + 1 for n, l in enumerate(lines) if base in l]
            hint = (' -- `%s` now appears at line(s) %s' %
                    (base, ', '.join(map(str, hits[:4])))) if hits else \
                   (' -- `%s` appears NOWHERE in the file' % base)
            out.append(('DRIFTED', '%s: %s:%d no longer near `%s`%s'
                        % (cell_id, rel, line, ident, hint)))
    for m in BARE_PATH.finditer(text):
        rel = m.group(1)
        if _lines_of(path_cache, rel) is None:
            out.append(('DRIFTED', '%s: names %s, which does not exist'
                        % (cell_id, rel)))
    return out


# ── A FUNCTION THAT NO LONGER EXISTS AT ALL (2026-09-25) ────────────────────
# A LINE can drift; a NAME can die, and the two need different answers. The
# sdn_timeentries cell cited `saveTimeEntry()` -- which had been RENAMED to
# `saveTime()` -- so a line-number repoint would have papered over a cell
# citing a function that was gone. This asks the question independently of
# line numbers: does the named function exist ANYWHERE in the files this cell
# cites?
#
# TWO NARROWINGS, BOTH MEASURED RATHER THAN GUESSED. The unnarrowed version
# reported 131 and nearly every one was correct prose:
#   * a name that is a REGISTERED RESOURCE anywhere in the register is a
#     cross-reference -- `sb_train`'s cell cites `rf_certifications` as its
#     precedent, and nobody expects that in sairnbiz.html;
#   * a name must LOOK like a function -- written `name()` in the cell, or
#     camelCase. A bare field name belonging to another row is prose too.
# After both, the sweep reports ONE candidate, and that one is a genuine
# cross-reference (`sbThreeWayMatch` lives in sairnbiz.html and is cited by
# bld_deliveries as the SAIRNbiz precedent) -- so the real count is zero, and
# it is zero as a STANDING check rather than as a one-off sweep.
CELL_FILE = re.compile(r'`([A-Za-z0-9_./-]+\.(?:html|js|py|sql))(?::\d+)?`')
CELL_CALL = re.compile(r'`([A-Za-z_$][A-Za-z0-9_$.]{2,60})\(\)`')
CELL_CAMEL = re.compile(r'`([a-z$_][A-Za-z0-9_$]*[A-Z][A-Za-z0-9_$]*)`')


def _exists_anywhere(name, _memo={}):
    """Is this identifier present anywhere in the tracked sources at all?

    THE EXCLUSION IS BY EXISTENCE, NOT BY NAME, and that is deliberate. The
    one survivor of both narrowings was `sbThreeWayMatch` -- real, living in
    sairnbiz.html, cited by bld_deliveries as the SAIRNbiz precedent it is
    being compared against. Excluding it by name would have been a suppression
    list; excluding it by EXISTENCE means a genuinely dead function -- one
    that exists nowhere at all -- still reports, which is the case this check
    was built for.

    ── AND IT WENT BLIND ON ITS OWN SUBJECT WITHIN THE HOUR (2026-09-25) ────
    The first version grepped every tracked .html/.js/.py, which includes
    THIS FILE -- and this file's comment block names `saveTimeEntry()` as the
    defect it was built to catch. So the check was silent on the exact case
    it exists for: the documentation of a dead function kept that function
    alive. Found by an adversarial pass driving planted names through it, not
    by review, and it is the self-reference trap this repo has now recorded
    three times (the `--self-check` regex, the never-merges fixture arm, and
    this).

    So the search is scoped to what a citation could legitimately mean: APP
    AND API SOURCES. tools/ and tests/ are excluded because a tool naming a
    function in prose is not that function existing, and a register cell
    never cites a tool as the home of an app function.
    """
    if name not in _memo:
        r = subprocess.run(['git', 'grep', '-l', '-w', '--', name,
                            '--', '*.html', 'api/*.js', 'api/_lib/*.js',
                            'api/_resources/*.js'], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
        _memo[name] = bool((r.stdout or '').strip())
    return _memo[name]


def check_dead_functions(cell_id, evidence, path_cache, known_resources):
    files = list(dict.fromkeys(CELL_FILE.findall(evidence)))
    readable = {}
    for f in files:
        lines = _lines_of(path_cache, f)
        if lines is not None:
            readable[f] = '\n'.join(lines)
    if not readable:
        return []
    out = []
    for ident in dict.fromkeys(CELL_CALL.findall(evidence)
                               + CELL_CAMEL.findall(evidence)):
        base = ident.split('.')[-1]
        if base in known_resources:
            continue
        # A cross-app precedent cited by name -- see _exists_anywhere.
        if _exists_anywhere(base):
            continue
        if re.fullmatch(r'[0-9a-f]{6,}', base):
            continue
        if not any(base in src for src in readable.values()):
            out.append(('DRIFTED',
                        '%s: names `%s()` which exists in NONE of the files it '
                        'cites (%s) -- a RENAME or a deletion, not a line '
                        'drift, and a repoint would hide it'
                        % (cell_id, base, ', '.join(sorted(readable)))))
    return out


def check_tiers(path, path_cache, sha_memo):
    if not os.path.isfile(path):
        raise CouldNotTell('%s does not exist -- nothing was checked'
                           % os.path.relpath(path, REPO))
    src = io.open(path, encoding='utf-8', errors='replace').read()
    known = set(re.findall(r'^\| `([a-z0-9_]+)` \|', src, re.M))
    results = []
    for line in src.split('\n'):
        m = re.match(r'^\| `([a-z0-9_]+)` \|', line)
        if not m:
            continue
        cells = line.split('|')
        if len(cells) < 7:
            continue
        evidence = cells[-2]  # the Evidence column
        cell_id = 'tiers/' + m.group(1)
        results.extend(check_cell(cell_id, evidence, path_cache, sha_memo))
        results.extend(check_dead_functions(cell_id, evidence, path_cache,
                                            known))
    return results


def check_reviews(path, path_cache, sha_memo):
    if not os.path.isfile(path):
        raise CouldNotTell('%s does not exist -- nothing was checked'
                           % os.path.relpath(path, REPO))
    try:
        data = json.load(io.open(path, encoding='utf-8'))
    except Exception as e:
        raise CouldNotTell('%s is unreadable: %s' % (path, e))
    results = []
    for r in data.get('records') or []:
        rid = 'reviews/%s@%s' % (r.get('author_session'), r.get('opened_at'))
        for f in r.get('files') or []:
            if _lines_of(path_cache, f) is None:
                results.append(('DRIFTED', '%s: files[] names %s, which does '
                                'not exist -- the change this record covers '
                                'can no longer be found by its own pointer'
                                % (rid, f)))
            else:
                results.append(('OK', '%s: %s' % (rid, f)))
        # ── A FROZEN LITERAL IS NOT DRIFT, AND THE RECORD SAYS WHICH (2026-09-26)
        # Two shapes in this ledger produce a hex run that will NEVER resolve and
        # must never be re-seated, and reporting them as drift is a permanent
        # false positive a reader learns to scroll past:
        #
        #   * a reviewer's finding ABOUT a dead pointer -- "This record cites
        #     a49edd00 and no such commit exists in the repo. The change is
        #     5c781b99" -- where rewriting the literal makes the sentence deny
        #     what its author verified; and
        #   * a literal that is not a commit reference at all: `1234abcd`, quoted
        #     as an illustrative example inside a finding narrative, reported here
        #     as citation drift since the day that review landed.
        #
        # The record declares them in `frozen_shas`, authored by a person --
        # deciding that a sentence is ABOUT a pointer rather than citing one is a
        # reading of prose and no regex can make it. Counted as OK-BY-DECLARATION
        # rather than dropped: a suppression nothing reports is the next thing
        # that goes stale. Written and enforced by tools/review_ledger_reseat.py.
        frozen = set()
        for e in r.get('frozen_shas') or []:
            if e.get('literal'):
                frozen.add(e['literal'])
        prose = (r.get('what') or '') + ' ' + (r.get('verdict') or '')
        for sha in set(SHA.findall(prose)):
            # skip things that are obviously not shas (all digits = a count)
            if sha.isdigit():
                continue
            if _sha_resolves(sha, sha_memo):
                results.append(('OK', '%s: sha %s resolves' % (rid, sha)))
            elif sha in frozen:
                results.append(('FROZEN', '%s: %s is declared in frozen_shas -- '
                                'a literal this prose is ABOUT, not a pointer to '
                                'follow' % (rid, sha)))
            else:
                results.append(('DRIFTED', '%s: cites sha %s which does not '
                                'resolve -- rebased away without a reseat, or '
                                'mistyped. If the prose is ABOUT this dead '
                                'pointer, declare it in frozen_shas; if it is a '
                                'citation, `python tools/review_ledger_reseat.py'
                                ' --reseat` repairs it once a subject is '
                                'recorded' % (rid, sha)))
    return results


# ── THE BLIND LOCK (discipline 1): judge fixtures before anything real ──────
def fixtures():
    import shutil
    import tempfile
    out, bad = [], 0

    def ck(name, cond, detail=''):
        nonlocal bad
        out.append(('  ok   ' if cond else '  FAIL ') + name
                   + ('' if cond else '  <- ' + str(detail)[:200]))
        if not cond:
            bad += 1

    d = tempfile.mkdtemp(prefix='regfresh-fx-')
    try:
        # a fixture source file whose function REALLY sits at a known line
        src = ['// filler'] * 30
        src[19] = 'function realThing() {'
        io.open(os.path.join(d, 'app.js'), 'w', encoding='utf-8',
                newline='\n').write('\n'.join(src))
        global REPO
        real = REPO
        REPO = d
        try:
            pc = {}
            ok_cell = check_cell('fx', 'the gate `realThing()` at `app.js:20` holds', pc, {})
            ck('a TRUE citation verifies OK',
               ok_cell and ok_cell[0][0] == 'OK', ok_cell)
            drift = check_cell('fx', 'the gate `realThing()` at `app.js:5` holds', pc, {})
            ck('a DRIFTED citation is caught and the new location is NAMED',
               drift and drift[0][0] == 'DRIFTED' and 'line(s) 20' in drift[0][1],
               drift)
            gone = check_cell('fx', 'the gate `vanishedFn()` at `app.js:20` holds', pc, {})
            ck('an identifier that appears NOWHERE says so, not just "drifted"',
               gone and gone[0][0] == 'DRIFTED' and 'NOWHERE' in gone[0][1], gone)
            short = check_cell('fx', '`realThing()` at `app.js:20` then (`:20`) again', pc, {})
            ck('a SHORT cite resolves against the preceding full cite',
               len(short) == 2 and all(s == 'OK' for s, _ in short), short)
            noid = check_cell('fx', 'stored at `app.js:20` with nothing named', pc, {})
            ck('a cite with NO adjacent identifier is UNVERIFIABLE, never OK '
               'and never silently dropped',
               noid and noid[0][0] == 'UNVERIFIABLE', noid)
            nofile = check_cell('fx', '`realThing()` at `ghost.js:20`', pc, {})
            ck('a cite into a MISSING file is DRIFTED',
               nofile and nofile[0][0] == 'DRIFTED' and 'DOES NOT EXIST' in nofile[0][1],
               nofile)
            past = check_cell('fx', '`realThing()` at `app.js:999`', pc, {})
            ck('a cite past EOF is DRIFTED naming the real length',
               past and past[0][0] == 'DRIFTED' and 'only 30 lines' in past[0][1],
               past)
            orphan = check_cell('fx', 'a bare short cite (`:12`) first', pc, {})
            ck('a short cite with NO preceding file is UNVERIFIABLE',
               orphan and orphan[0][0] == 'UNVERIFIABLE', orphan)
        finally:
            REPO = real
        ck('NEGATIVE CONTROL: the comparator can tell 8 lines from 80 -- the '
           'window is +/-%d, not the whole file' % IDENT_WINDOW,
           IDENT_WINDOW < 20)
        ck('THE TOOL HAS NO WRITE PATH: it never regenerates its subject to '
           'make a comparison pass',
           not any(name in globals() for name in ('fix', 'repair', 'rewrite',
                                                  'regenerate')))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return out, bad


def main(argv):
    if '--fixtures' in argv:
        out, bad = fixtures()
        for l in out:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad
                        else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    out, bad = fixtures()
    if bad:
        print('THE FIXTURE LOCK FAILED -- nothing real was judged.')
        for l in out:
            print(l)
        return 2

    path_cache, sha_memo = {}, {}
    results = []
    could_not = []
    for fn, src in ((check_tiers, TIERS), (check_reviews, REVIEWS)):
        try:
            results.extend(fn(src, path_cache, sha_memo))
        except CouldNotTell as e:
            could_not.append(str(e))

    drifted = [d for s, d in results if s == 'DRIFTED']
    unver = [d for s, d in results if s == 'UNVERIFIABLE']
    # ── A FOURTH STATE, AND IT IS LISTED RATHER THAN ADDED TO `ok` (2026-09-26)
    # A literal a record declares in `frozen_shas` is a deliberate non-pointer --
    # see check_reviews. Folding it into "citations verified OK" would make a
    # SUPPRESSION indistinguishable from a VERIFICATION, which is the shape this
    # whole tool exists to refuse: every declaration is printed, so a stale
    # frozen_shas entry is something a reader can see rather than something the
    # count absorbed.
    frozen = [d for s, d in results if s == 'FROZEN']
    okc = sum(1 for s, _ in results if s == 'OK')

    if '--json' in argv:
        print(json.dumps({'ok': okc, 'drifted': drifted,
                          'unverifiable': unver, 'frozen': frozen,
                          'could_not_tell': could_not}, indent=2))
    else:
        print('REGISTER FRESHNESS -- committed evidence vs freshly-recomputed truth')
        print('  citations verified OK   %4d' % okc)
        print('  UNVERIFIABLE            %4d   <- counted, never folded into pass' % len(unver))
        print('  DRIFTED                 %4d' % len(drifted))
        print('  FROZEN                  %4d   <- declared non-pointers, listed '
              'not absorbed' % len(frozen))
        for d in drifted:
            print('  DRIFTED  %s' % d)
        for d in frozen:
            print('  FROZEN  %s' % d)
        for d in unver[:15]:
            print('  UNVERIFIABLE  %s' % d)
        if len(unver) > 15:
            print('  ... and %d more unverifiable' % (len(unver) - 15))
        for c in could_not:
            print('  COULD NOT TELL  %s' % c)
        print('')
        print('ADVISORY PER ITEM, by decision: a drifted cell is a finding about')
        print('THAT cell, and this tool never edits a register to make its own')
        print('comparison pass. The four narrow freshness tools are not retired')
        print('by this landing -- that is a decision with an owner, not a side')
        print('effect.')

    if could_not and not results:
        return 2
    if drifted:
        return 1
    if not results:
        sys.stderr.write('COULD NOT TELL: both registers parsed and yielded '
                         'ZERO checkable citations -- nothing was measured, '
                         'and exit 0 here would be indistinguishable from '
                         'all-clean.\n')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
