#!/usr/bin/env python
# OWNER: cc
# written 2026-10-14, batch b13, queue item 3
"""Prove a document's QUOTED-TEXT citations still resolve, and resolve ONCE.

    python tools/citation_anchor_rot_check.py docs/CRITICALITY-TIERS.md
    python tools/citation_anchor_rot_check.py <doc> --target <file>
    python tools/citation_anchor_rot_check.py --selftest

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

Built to the spec in docs/2026-10-14-fourth-b20-anchor-rot-check-spec.md
(fourth b20, specced and deliberately not written there: `tools/` is cc's).
The name is cc's call, per that spec; the behaviour is the spec's.

── THE MEASUREMENT THAT MOTIVATES IT ───────────────────────────────────────
The `sf_events` row of docs/CRITICALITY-TIERS.md carried SEVEN line citations
into sairnfreedom.html. At the HEAD before fourth b20, ALL SEVEN WERE WRONG.
Every function the cell named was real and did what the cell said -- only the
numbers had moved. The cell's own named trigger says to re-read the row if the
event->session link stops being a single stored id; NOTHING in it fired when
the citations stopped pointing at the code.

fourth found this shape live in a document in three consecutive batches, twice
in one it or a peer wrote, and the b20 leg review found a citation stamped
"RE-DERIVED 2026-10-14 rather than carried" that was wrong anyway. **A
freshness stamp is the thing a reader checks INSTEAD of checking, so a wrong
stamp is worse than no stamp.** That is why this is mechanical.

── IT IS NOT A LINE-NUMBER DRIFT CHECKER ───────────────────────────────────
tools/citation_line_drift_check.py owns the `file:line` form and requires
--app and --prefix, which makes it inapplicable to a cross-app register row --
fourth hit that in b19 and recorded it as "does not apply". This one owns the
ANCHOR form, which is the form that cannot rot in the first place, and its job
is to prove the anchors still resolve and still resolve UNIQUELY.

R3 is the bridge: this check COUNTS the surviving `file:line` citations so a
reader knows what the other tool should be pointed at. It does not judge them.

── EXACTLY ONCE, NOT AT LEAST ONCE ─────────────────────────────────────────
A count of 2 is a FINDING, not a pass. It is the arm a reviewer would cut --
"it resolves, so it's fine" -- and it is the only arm that catches the NEXT
silent rot rather than this one: an anchor matching two sites is a citation
pointing at a site the author did not choose. Same guard
tools/sabotage_control_check.py was corrected to recognise (`count != 1`),
which it originally scored as unguarded.

── WHAT IT DOES NOT DO ─────────────────────────────────────────────────────
IT WRITES NOTHING. It reports the finding and the nearest surviving candidate;
it does not rewrite the document. Eleventh cross-domain convention: a fixer
that applies its own repair is a detector blessing its own fix. And a document
edit here means rebuilding a table row whole, which PR 2.1 requires.

AND A RENAMED FUNCTION BREAKS AN ANCHOR TOO. That is the point: it breaks
LOUDLY, as a count of 0, instead of silently pointing at an unrelated line.
"""
import argparse
import io
import os
import re
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-14.1'

# THE EXACTLY-ONCE RULE, as a named hook. `n != 1` inline would make
# the ablation a rewrite of check() instead of the removal of one
# layer, and an ablation that rewrites the thing it measures tells you
# nothing about which layer caught the defect.
def _COUNT_IS_FINDING(n):
    return n != 1


# Does the declared target exist. Named for the same reason as
# _COUNT_IS_FINDING: a layer that cannot be removed cannot be measured.
def _TARGET_EXISTS(path):
    return os.path.isfile(path)

NL = chr(10)

# ── R1: THE ANCHOR FORM ────────────────────────────────────────────────────
# The literal convention the register already uses: the word `anchor` followed
# by a backticked string. NOT "every backticked string", which would make
# every identifier in a prose cell an anchor.
ANCHOR_RE = re.compile(r'anchor\s+`([^`]+)`')

# ── R2: THE TARGET IS DECLARED, NEVER INFERRED ─────────────────────────────
# This is the sentence fourth's worked example actually wrote into the cell:
# "so every quoted anchor in this cell must resolve EXACTLY ONCE in
# sairnfreedom.html". Inferring the target from the nearest filename is how a
# checker measures the wrong file -- the exact defect
# citation_line_drift_check.py refuses to commit by requiring both flags.
TARGET_RE = re.compile(
    r'resolve\s+EXACTLY\s+ONCE\s+in\s+`?([A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+)`?',
    re.IGNORECASE)

# ── R3: THE OTHER CLASS, COUNTED APART ─────────────────────────────────────
# Two spellings, because the register carries both: a qualified `file.ext:NNN`
# and the bare `:NNNN` the spec's section 4 counted with `grep -o`.
LINECITE_RE = re.compile(
    r'(?:[A-Za-z0-9_./\\-]+\.(?:html|js|cjs|mjs|py|sql|md|json|tla|cfg)):\d+')
BARE_LINECITE_RE = re.compile(r'`:\d{2,}`')

# ── R6: WHAT IS NOT AN ANCHOR ──────────────────────────────────────────────
# MEASURED NEED, NOT HYPOTHETICAL. Writing the spec's own instruction produced
# a phantom eighth anchor from a literal ellipsis, and this document really
# does carry `anchor `^| `` on line 40 as an editing instruction about
# anchors. A rot check that treats prose about anchors as anchors reports rot
# in its own documentation.
MIN_ANCHOR_CHARS = 8
_NOISE_ONLY = re.compile(r'^[\s.…]*$')
_NONWORD = re.compile(r'[^\w\s]')


def is_real_anchor(text):
    """(ok, why_not). >= 8 chars, at least one non-word char, not all dots."""
    if _NOISE_ONLY.match(text):
        return False, 'it is only dots/ellipsis/whitespace'
    if len(text) < MIN_ANCHOR_CHARS:
        return False, ('it is %d characters, under the %d-character floor -- '
                       'prose about anchors rather than an anchor'
                       % (len(text), MIN_ANCHOR_CHARS))
    if not _NONWORD.search(text):
        return False, ('it contains no non-word character, so it is a bare '
                       'identifier rather than a quoted line of code')
    return True, ''


# ── reading ────────────────────────────────────────────────────────────────

def read_text(path):
    """(text, why). Binary-decoded leniently; a read failure is never a pass."""
    try:
        with io.open(path, encoding='utf-8', errors='replace') as fh:
            return fh.read(), ''
    except OSError as exc:
        return None, str(exc)


def extract(doc_text):
    """([anchor dicts], [skipped dicts], line_cites, bare_cites).

    Each anchor carries the document line it came from (R7) and the target in
    scope at that line (R2). A declaration governs the line it is ON and every
    line after it until the next declaration -- which is exactly right for a
    Markdown table, where the cell and its declaration are one line.
    """
    anchors, skipped = [], []
    target = None
    lines = doc_text.split(NL)
    for n, line in enumerate(lines, 1):
        m = TARGET_RE.search(line)
        if m:
            target = m.group(1).replace('\\', '/')
        for am in ANCHOR_RE.finditer(line):
            text = am.group(1)
            ok, why = is_real_anchor(text)
            if not ok:
                skipped.append({'text': text, 'line': n, 'why': why})
                continue
            anchors.append({'text': text, 'line': n, 'target': target})
    cites = LINECITE_RE.findall(doc_text)
    bare = BARE_LINECITE_RE.findall(doc_text)
    return anchors, skipped, cites, bare


def near_match(anchor_text, target_text):
    """A whitespace-relaxed candidate line, or None. (R7, and R9's bar.)

    THE RELAXATION IS FOR REPORTING ONLY and never for matching. A
    whitespace-normalising MATCH would quietly bless a rewritten line; naming
    the near-match helps the reader without lowering the bar.
    """
    want = ' '.join(anchor_text.split())
    if not want:
        return None
    for line in target_text.split(NL):
        if want in ' '.join(line.split()):
            return line.strip()
    return None


def check(doc_path, text_override=None, target_override=None, repo=None):
    """(exit_code, lines). Never raises. Writes nothing, ever."""
    repo = repo or REPO
    out = []
    out.append('citation_anchor_rot_check  (criteria %s)' % CRITERIA_VERSION)

    if text_override is None:
        full = doc_path if os.path.isabs(doc_path) else os.path.join(repo,
                                                                    doc_path)
        if not os.path.isfile(full):
            out.append('COULD NOT RUN -- the document is not a file: %s'
                       % doc_path)
            out.append('  Nothing was checked. This is not a pass (PR 1.11).')
            return EXIT_COULD_NOT_RUN, out
        doc_text, why = read_text(full)
        if doc_text is None:
            out.append('COULD NOT RUN -- %s is unreadable: %s'
                       % (doc_path, why))
            return EXIT_COULD_NOT_RUN, out
    else:
        doc_text = text_override

    anchors, skipped, cites, bare = extract(doc_text)
    if target_override:
        # ANNOUNCED, because R2 is about the document declaring its target.
        # A caller-supplied target is a different provenance and the output
        # says which one it used rather than presenting them as the same.
        out.append('  TARGET SUPPLIED BY THE CALLER (--target %s), not read '
                   'from the document. R2 wants the document to declare it; '
                   'this override is printed so nobody reads a caller flag as '
                   'a document fact.' % target_override)
        for a in anchors:
            a['target'] = target_override

    out.append('  %d anchor(s), %d line citation(s), %d bare `:NNNN` '
               'citation(s)' % (len(anchors), len(cites), len(bare)))

    # ── R10's CONTROL: A ZERO MUST BE SAID OUT LOUD ────────────────────────
    # A silent tool and an absent tool look identical, which is the
    # shared-status-registry lesson. A document with nothing to check is CLEAN
    # and says so with both numbers.
    if not anchors:
        out.append('  0 anchors, 0 line citations to attribute -- there is '
                   'nothing of the anchor form in this document. CLEAN, and '
                   'that is a measurement rather than a silence.'
                   if not cites and not bare else
                   '  0 anchors of the checkable form. The %d line citation(s) '
                   'below are the OTHER class and are not judged here.'
                   % (len(cites) + len(bare)))
        for s in skipped:
            out.append('    skipped (not an anchor): %r -- %s'
                       % (s['text'][:50], s['why']))
        _append_cite_class(out, cites, bare)
        return EXIT_CLEAN, out

    # ── R2 / A5: an anchor with no declared target is COULD NOT RUN ────────
    undeclared = [a for a in anchors if not a['target']]
    if undeclared:
        out.append('COULD NOT RUN -- %d anchor(s) have NO declared target '
                   'file in scope:' % len(undeclared))
        for a in undeclared[:8]:
            out.append('    line %d: %r' % (a['line'], a['text'][:60]))
        out.append('  The target is DECLARED, never inferred. Write a '
                   'sentence the check can read -- the convention this '
                   'document already uses is "... must resolve EXACTLY ONCE '
                   'in <file>" -- or pass --target, which is printed as a '
                   'caller fact rather than a document one.')
        out.append('  Nothing was guessed from a nearby filename. That is how '
                   'a checker measures the wrong file.')
        return EXIT_COULD_NOT_RUN, out

    # ── R4: the target must be readable, or the run did not happen ────────
    targets = sorted({a['target'] for a in anchors})
    bodies = {}
    for t in targets:
        tfull = t if os.path.isabs(t) else os.path.join(repo, t)
        # THE FAIL-CLOSED LEG, through a named hook so the ablation can REMOVE
        # it. The first version of that ablation patched read_text() instead
        # and the ablation reported this layer UNPROVEN -- correctly: the leg
        # A4 exercises is this existence test, which runs BEFORE any read. An
        # ablation that misses its own layer is the thing ablations are for.
        if not _TARGET_EXISTS(tfull):
            out.append('COULD NOT RUN -- the declared target file does not '
                       'exist: %s' % t)
            out.append('  %d anchor(s) point into it and NONE was checked. A '
                       'rot check that silently passes when the app moves is '
                       'worse than none: the absence of a finding becomes '
                       'evidence of freshness.'
                       % len([a for a in anchors if a['target'] == t]))
            return EXIT_COULD_NOT_RUN, out
        body, why = read_text(tfull)
        if body is None:
            out.append('COULD NOT RUN -- the declared target %s is unreadable: '
                       '%s' % (t, why))
            return EXIT_COULD_NOT_RUN, out
        bodies[t] = body

    findings = []
    for a in anchors:
        body = bodies[a['target']]
        n = body.count(a['text'])
        a['count'] = n
        # EXACTLY ONCE, through a module-level hook so the ablation can REMOVE
        # this one rule rather than rewrite the checker around it.
        if _COUNT_IS_FINDING(n):
            findings.append(a)

    for t in targets:
        mine = [a for a in anchors if a['target'] == t]
        ok = len([a for a in mine if a['count'] == 1])
        out.append('  %s: %d anchor(s), %d resolving EXACTLY ONCE, %d not'
                   % (t, len(mine), ok, len(mine) - ok))

    for s in skipped:
        out.append('    skipped (not an anchor, R6): %r -- %s'
                   % (s['text'][:50], s['why']))

    for a in findings:
        out.append('')
        out.append('  FINDING  count %d  document line %d'
                   % (a['count'], a['line']))
        out.append('    anchor : %r' % a['text'])
        out.append('    target : %s' % a['target'])
        if a['count'] == 0:
            cand = near_match(a['text'], bodies[a['target']])
            if cand:
                out.append('    NEAREST SURVIVING CANDIDATE, found by relaxing '
                           'runs of whitespace ONLY:')
                out.append('      %r' % cand[:160])
                out.append('    The relaxation is for READING, not for '
                           'matching -- a whitespace-normalising match would '
                           'bless a rewritten line. This is still a finding.')
            else:
                out.append('    no near match even with whitespace relaxed, so '
                           'the cited text is gone rather than reformatted.')
        else:
            out.append('    IT RESOLVES %d TIMES, AND THAT IS A FINDING, not a '
                       'pass. The citation points at a site the author did not '
                       'choose, and it will start pointing at the other one '
                       'the next time either moves.' % a['count'])

    _append_cite_class(out, cites, bare)

    if findings:
        out.append('')
        out.append('  %d of %d anchor(s) DO NOT resolve exactly once.'
                   % (len(findings), len(anchors)))
        out.append('  NOTHING WAS REWRITTEN. The suggested text is above; the '
                   'edit is a human one, and a table row is rebuilt WHOLE '
                   '(PR 2.1) rather than patched by splitting on a pipe.')
        return EXIT_FINDING, out
    out.append('')
    out.append('  every anchor resolves EXACTLY ONCE in its declared target.')
    out.append('  THAT IS NOT A CLAIM ABOUT THE DOCUMENT BEING RIGHT. An '
               'anchor can quote real code and sit beside a sentence that '
               'misdescribes it; this check reads the quote, not the argument.')
    return EXIT_CLEAN, out


def _append_cite_class(out, cites, bare):
    """R3: the other class, counted and listed, never judged here."""
    total = len(cites) + len(bare)
    if not total:
        out.append('  0 surviving `file:line` citations -- this document is '
                   'fully converted to the anchor form.')
        return
    out.append('')
    out.append('  SECOND CLASS, COUNTED APART AND NOT JUDGED HERE: %d '
               '`file:line`-style citation(s) survive. Each one is an anchor '
               'waiting to rot, and a half-converted document reads as a '
               'converted one -- which is why this is a second number and '
               'never folded into the first.' % total)
    seen = []
    for c in cites:
        if c not in seen:
            seen.append(c)
    for c in seen[:12]:
        out.append('    %s' % c)
    if len(seen) > 12:
        out.append('    ... and %d more distinct' % (len(seen) - 12))
    if bare:
        out.append('    plus %d bare `:NNNN` citation(s), whose target is '
                   'whatever the surrounding prose says -- point '
                   'tools/citation_line_drift_check.py at those with its '
                   '--app and --prefix.' % len(bare))


# ── R8: the criteria lock, run BEFORE any verdict about a real document ────

_ARMS = []


def arm(name, bad_input, must):
    def deco(fn):
        _ARMS.append((name, bad_input, must, fn))
        return fn
    return deco


def _tree(tmp, doc, target_name=None, target_body=None):
    """Write a fixture document (and optionally a target) and return the dir."""
    d = tempfile.mkdtemp(prefix='anchor-', dir=tmp)
    with io.open(os.path.join(d, 'doc.md'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        fh.write(doc)
    if target_name is not None:
        with io.open(os.path.join(d, target_name), 'w', encoding='utf-8',
                     newline='\n') as fh:
            fh.write(target_body or '')
    return d


DECL = 'every quoted anchor in this cell must resolve EXACTLY ONCE in app.html'


@arm('A1-zero-count', 'a document anchoring a function that never existed',
     'FINDING, count 0')
def _a1(tmp):
    d = _tree(tmp,
              '%s and anchor `function thisNeverExisted(){`\n' % DECL,
              'app.html', 'function realThing(){ return 1; }\n')
    rc, out = check('doc.md', repo=d)
    body = NL.join(out)
    return (rc == EXIT_FINDING and 'count 0' in body
            and 'thisNeverExisted' in body), body


@arm('A2-two-counts', 'an anchor appearing TWICE in the target',
     'FINDING, count 2 -- the arm a reviewer would cut')
def _a2(tmp):
    d = _tree(tmp, '%s and anchor `var x = compute(a, b);`\n' % DECL,
              'app.html',
              'var x = compute(a, b);\nif (y) { var x = compute(a, b); }\n')
    rc, out = check('doc.md', repo=d)
    body = NL.join(out)
    return (rc == EXIT_FINDING and 'count 2' in body
            and 'RESOLVES 2 TIMES' in body), body


@arm('A3-exactly-once', 'an anchor appearing exactly once',
     'CLEAN -- the over-refusal control')
def _a3(tmp):
    d = _tree(tmp, '%s and anchor `var x = compute(a, b);`\n' % DECL,
              'app.html', 'var x = compute(a, b);\nvar y = 2;\n')
    rc, out = check('doc.md', repo=d)
    return (rc == EXIT_CLEAN
            and 'resolves EXACTLY ONCE' in NL.join(out)), NL.join(out)


@arm('A4-target-absent', 'the declared target file does not exist',
     'EXIT 2, naming the missing file -- the load-bearing arm')
def _a4(tmp):
    d = _tree(tmp, '%s and anchor `var x = compute(a, b);`\n' % DECL)
    rc, out = check('doc.md', repo=d)
    body = NL.join(out)
    return (rc == EXIT_COULD_NOT_RUN and 'app.html' in body
            and 'COULD NOT RUN' in body), body


@arm('A5-no-declaration', 'the document declares no target',
     'EXIT 2 -- must not guess from a nearby filename')
def _a5(tmp):
    d = _tree(tmp,
              'See app.html for the code. anchor `var x = compute(a, b);`\n',
              'app.html', 'var x = compute(a, b);\n')
    rc, out = check('doc.md', repo=d)
    body = NL.join(out)
    return (rc == EXIT_COULD_NOT_RUN and 'NO declared target' in body
            and 'Nothing was guessed' in body), body


@arm('A6-mixed-classes', '3 anchors and 2 file:line citations',
     'anchors checked; the line citations reported as a SECOND count')
def _a6(tmp):
    doc = ('%s\n'
           'anchor `var a = one(1);` and anchor `var b = two(2);` and '
           'anchor `var c = three(3);`\n'
           'older notes: app.html:412 and lib/thing.js:88\n' % DECL)
    d = _tree(tmp, doc, 'app.html',
              'var a = one(1);\nvar b = two(2);\nvar c = three(3);\n')
    rc, out = check('doc.md', repo=d)
    body = NL.join(out)
    return (rc == EXIT_CLEAN
            and '3 anchor(s), 2 line citation(s)' in body
            and 'SECOND CLASS' in body
            and 'app.html:412' in body), body


# ── A7 WAS RE-SPECIFIED ON ITS FIRST RUN, AND THAT IS THE FINDING ─────────
# The spec's A7 asked for: the real sf_events row against the real
# sairnfreedom.html, CLEAN, 7 anchors all unique, as "the regression that pins
# this batch's work".
#
# ITS FIRST RUN RETURNED 6 OF 7. Diagnosed rather than adjusted:
#
#   git show 924085fb:sairnfreedom.html | grep -c '<the anchor>'   ->  1
#   grep -c '<the anchor>' sairnfreedom.html  (HEAD)               ->  0
#   git log --oneline 924085fb..HEAD -- sairnfreedom.html
#     31406a87  fix(N1-N4,F6): ... and a delete that lied
#
# fourth's anchor resolved EXACTLY ONCE when fourth wrote it. hank's 31406a87
# then refactored that one-liner -- `if (ev && ev.sessionId) {` opening a block
# -- and the quoted form now survives only inside an elided comment at
# sairnfreedom.html:5228. So the anchor went to ZERO within hours of being
# written, and THE ANCHOR FORM DID EXACTLY WHAT IT IS FOR: it broke LOUDLY, as
# a count of 0, where a line number would have gone on pointing at whatever
# moved into its place. Nobody did anything wrong; the citation is simply out
# of date, and now something says so.
#
# SO A7 IS TWO ARMS. A frozen one that pins fourth's work for ever against the
# revision fourth measured, and a live one that asserts only what cannot rot.
# Asserting "exactly 1 finding at HEAD" would have been a third rotting
# citation inside the rot checker.
@arm('A7-frozen-at-b20', 'the real sf_events row against sairnfreedom.html AS '
                         'OF 924085fb, the revision fourth measured',
     'CLEAN -- 7 anchors, all unique. Pins fourth b20 permanently')
def _a7(tmp):
    import subprocess
    d = tempfile.mkdtemp(prefix='anchor-b20-', dir=tmp)
    os.makedirs(os.path.join(d, 'docs'))
    for rev_path, dest in (
            ('924085fb:docs/CRITICALITY-TIERS.md',
             os.path.join(d, 'docs', 'CRITICALITY-TIERS.md')),
            ('924085fb:sairnfreedom.html',
             os.path.join(d, 'sairnfreedom.html'))):
        try:
            blob = subprocess.check_output(
                ['git', '-C', REPO, 'show', rev_path],
                stderr=subprocess.STDOUT)
        except Exception as exc:                                 # noqa: BLE001
            return False, ('could not extract %s: %s -- the frozen fixture '
                           'is unavailable in this clone, which is a COULD '
                           'NOT RUN for this arm and not a pass'
                           % (rev_path, str(exc)[:90]))
        with open(dest, 'wb') as fh:
            fh.write(blob)
    rc, out = check('docs/CRITICALITY-TIERS.md', repo=d)
    body = NL.join(out)
    return (rc == EXIT_CLEAN
            and '7 anchor(s), 7 resolving EXACTLY ONCE, 0 not' in body), body


@arm('A7b-live-at-HEAD', 'the same row at HEAD, where the code has since moved',
     'the row is READ and attributed -- 7 anchors found, a real verdict, '
     'never COULD NOT RUN. The COUNT is reported, not asserted')
def _a7b(tmp):
    rc, out = check('docs/CRITICALITY-TIERS.md')
    body = NL.join(out)
    # DELIBERATELY NOT ASSERTING THE NUMBER OF FINDINGS. b13 got that right
    # and then pinned the ANCHOR COUNT instead, which rotted for the same
    # reason within a day: fourth b22 re-anchored the cell, so the row went
    # from 7 anchors with 1 dead to 8 anchors all resolving, and this arm went
    # red on somebody else's CORRECT FIX. Twice now, in the rot checker.
    #
    # SO THE ARM ASSERTS ONLY WHAT CANNOT ROT: the document is read, its
    # declaration resolves, a real verdict comes out rather than COULD NOT
    # RUN, and the row still carries AT LEAST the seven anchors fourth
    # established -- a floor, which a re-anchoring can raise and only a
    # deletion can break. The live numbers are REPORTED by the tool and not
    # pinned here.
    m = re.search(r'sairnfreedom\.html: (\d+) anchor\(s\)', body)
    n = int(m.group(1)) if m else 0
    return (rc in (EXIT_CLEAN, EXIT_FINDING) and n >= 7), \
        'exit %d, %d anchors into sairnfreedom.html' % (rc, n)


@arm('A8-prose-about-anchors', 'a backticked ellipsis inside prose about '
                              'anchors',
     'NOT treated as an anchor (R6) -- from a real mistake in the spec')
def _a8(tmp):
    doc = ('%s\n'
           'Write it as anchor `...` in the cell, like anchor `^| ` is used.\n'
           'anchor `var a = one(1);`\n' % DECL)
    d = _tree(tmp, doc, 'app.html', 'var a = one(1);\n')
    rc, out = check('doc.md', repo=d)
    body = NL.join(out)
    return (rc == EXIT_CLEAN and '1 anchor(s)' in body
            and 'skipped (not an anchor, R6)' in body), body


@arm('A9-whitespace-only-diff', 'an anchor differing from the target only by '
                               'run-length whitespace',
     'FINDING, with the near-match named -- a relaxed MATCH would bless a '
     'rewritten line')
def _a9(tmp):
    d = _tree(tmp, '%s and anchor `var x  =  compute(a, b);`\n' % DECL,
              'app.html', 'var x = compute(a, b);\n')
    rc, out = check('doc.md', repo=d)
    body = NL.join(out)
    return (rc == EXIT_FINDING and 'NEAREST SURVIVING CANDIDATE' in body
            and 'still a finding' in body), body


@arm('A10-no-anchors-control', 'a document with no anchors at all',
     'CLEAN exit 0, and the zero SAID OUT LOUD')
def _a10(tmp):
    d = _tree(tmp, 'A document about nothing in particular.\n')
    rc, out = check('doc.md', repo=d)
    body = NL.join(out)
    return (rc == EXIT_CLEAN and '0 anchor(s)' in body
            and 'that is a measurement rather than a silence' in body), body


@arm('A11-criteria-version', 'the criteria version asserting its OWN floor',
     'the version is this tool\'s, not a neighbour\'s')
def _a11(tmp):
    # Per the b19 review of run_rotation_blast_radius_probe.py: the version
    # arm must assert ITS OWN floor rather than inheriting one.
    return (CRITERIA_VERSION >= '2026-10-14.1'
            and CRITERIA_VERSION.startswith('2026-')), CRITERIA_VERSION


def run_arms(verbose=True):
    passed = failed = 0
    fails = []
    tmp = tempfile.mkdtemp(prefix='anchor-arms-')
    try:
        for name, bad, must, fn in _ARMS:
            try:
                ok, detail = fn(tmp)
            except Exception as exc:                             # noqa: BLE001
                ok, detail = False, 'arm raised: %s' % exc
            if ok:
                passed += 1
                if verbose:
                    print('  PASS  %-24s %s' % (name, must))
            else:
                failed += 1
                fails.append((name, bad, must, str(detail)[:400]))
                if verbose:
                    print('  FAIL  %-24s %s' % (name, must))
                    print('        bad input: %s' % bad)
                    print('        %s' % str(detail)[:400])
    finally:
        _rm(tmp)
    return passed, failed, fails


def _rm(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
            except OSError:
                pass
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def selftest():
    print('citation_anchor_rot_check --selftest  (criteria %s)'
          % CRITERIA_VERSION)
    print('%d arm(s), each with the bad input it was written against.'
          % len(_ARMS))
    print('BOTH DIRECTIONS: A1, A2, A9 require a FINDING; A4 and A5 require '
          'COULD NOT RUN; A3, A6, A7, A8 and A10 require a CLEAN pass. A tool '
          'that refuses everything scores perfectly on the first three and '
          'gets switched off.')
    print('')
    p, f, fails = run_arms()
    print('')
    print('  %d/%d arm(s) pass' % (p, len(_ARMS)))
    if f:
        print('  %d ARM(S) FAILED -- the requirement each one stands for is '
              'UNPROVEN, not proven absent.' % f)
        return EXIT_FINDING
    return EXIT_CLEAN


# ── THE ABLATION (added 2026-10-14, cc b14 item 5) ─────────────────────────
# THIS TOOL LANDED IN b13 WITH 12 ARMS AND NO ABLATION, which is the gap item
# 5 of b14 was sent to close across b12-b13. An arm proves a check FIRES on
# bad input; it does not prove the check is what caught it. Only removing the
# layer and watching a named arm go red does that, and the one time this
# platform skipped it -- b12's `latest-ceiling` -- the layer turned out to be
# deletable with no arm noticing.
#
# PER ARM, NOT PER EXIT CODE. Each entry removes exactly one layer from
# otherwise-clean code and re-runs every arm; the measurement is WHICH arms go
# quiet. A layer that breaks nothing is UNPROVEN and said so.
_ABLATIONS = (
    ('exactly-once',
     'a count of 2 is a FINDING -- the arm a reviewer would cut, and the only '
     'one that catches the NEXT rot rather than this one',
     lambda: _patch_count_rule(lambda n: n < 1)),
    ('zero-count-finding',
     'a count of 0 is a FINDING rather than "well, nothing matched"',
     lambda: _patch_count_rule(lambda n: n > 1)),
    ('declared-target',
     'the target is DECLARED and never inferred, so an anchor with no '
     'declaration is COULD NOT RUN instead of being measured against a '
     'filename guessed from nearby prose',
     lambda: _patch('extract', _infer_target_extract)),
    ('fail-closed-target',
     'a missing or unreadable target file is exit 2 NAMING the file, never 0 '
     '-- otherwise the absence of a finding becomes evidence of freshness',
     lambda: _patch_fail_open_target()),
    ('r6-anchor-filter',
     'an anchor must be >= 8 chars with a non-word character, so prose ABOUT '
     'anchors is not counted as one. Measured need: the spec\'s own '
     'instruction produced a phantom eighth anchor from a literal ellipsis',
     lambda: _patch('is_real_anchor', lambda text: (True, ''))),
    ('near-match-report',
     'a zero-count anchor names its nearest surviving candidate, found by '
     'relaxing whitespace FOR READING ONLY -- a relaxed MATCH would bless a '
     'rewritten line',
     lambda: _patch('near_match', lambda a, t: None)),
)


def _patch(name, replacement):
    old = globals()[name]
    globals()[name] = replacement
    return lambda: globals().__setitem__(name, old)


def _patch_count_rule(predicate):
    """Replace the exactly-once rule with a weaker one.

    The rule lives inline in check() as `n != 1`, so it is ablated through a
    module-level hook rather than by editing the function -- which keeps the
    ablation a REMOVAL of one layer instead of a rewrite of the checker.
    """
    old = globals().get('_COUNT_IS_FINDING')
    globals()['_COUNT_IS_FINDING'] = predicate
    return lambda: globals().__setitem__('_COUNT_IS_FINDING', old)


def _patch_fail_open_target():
    """Remove BOTH legs of the fail-closed path, because it is one layer
    implemented twice.

    FOUND BY THIS ABLATION REPORTING THE LAYER UNPROVEN, TWICE. Patching
    read_text() alone left the os.path.isfile guard; patching the guard alone
    left read_text() returning None for a missing file, which the next branch
    turns into COULD NOT RUN. Either half alone is invisible, which means
    neither half alone is what A4 was testing -- the LAYER is "an unusable
    target is never a pass", and an ablation has to remove the whole of it.
    That redundancy is a good property of the code and a trap for a lazy
    ablation.
    """
    restore_a = _patch('_TARGET_EXISTS', lambda path: True)
    restore_b = _patch('read_text', _absent_target_is_empty)

    def restore():
        restore_a()
        restore_b()
    return restore


def _infer_target_extract(doc_text):
    """extract() with R2 removed: guess the target from any filename in sight."""
    anchors, skipped, cites, bare = _real_extract(doc_text)
    guess = None
    m = re.search(r'\b([A-Za-z0-9_./\\-]+\.(?:html|js|py|sql|md))\b', doc_text)
    if m:
        guess = m.group(1).replace('\\', '/')
    for a in anchors:
        if not a['target']:
            a['target'] = guess
    return anchors, skipped, cites, bare


def _absent_target_is_empty(path):
    """read_text() with the fail-closed leg removed: an unreadable file reads
    as empty, so every anchor into it silently counts zero... or, with the
    isfile guard also bypassed, as clean."""
    if not os.path.isfile(path):
        return '', ''
    return _real_read_text(path)



def ablation():
    print('citation_anchor_rot_check --ablation  (criteria %s)'
          % CRITERIA_VERSION)
    print('ONE layer removed at a time from clean code; every arm re-run. The')
    print('measurement is WHICH arms go quiet, never the exit code.')
    print('')
    bp, bf, _ = run_arms(verbose=False)
    print('  baseline: %d pass / %d fail' % (bp, bf))
    if bf:
        print('  ABLATION NOT RUN -- the baseline is not clean, so nothing '
              'below could be attributed to the removed layer.')
        return EXIT_COULD_NOT_RUN
    print('')
    naked = []
    for name, what, patcher in _ABLATIONS:
        restore = patcher()
        try:
            _p, f, fails = run_arms(verbose=False)
        finally:
            restore()
        if f == 0:
            naked.append(name)
            print('  %-22s NOTHING CAUGHT IT -- UNPROVEN. This layer can be '
                  'deleted today and no arm notices.' % name)
        else:
            print('  %-22s %d arm(s) fail without it: %s'
                  % (name, f, ', '.join(n for n, _b, _m, _w in fails)))
        print('    %s' % what)
    print('')
    if naked:
        print('  %d LAYER(S) UNPROVEN: %s' % (len(naked), ', '.join(naked)))
        return EXIT_FINDING
    print('  every layer is load-bearing.')
    return EXIT_CLEAN


_real_extract = extract
_real_read_text = read_text


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Prove a document\'s quoted-text citations still resolve, '
                    'and resolve exactly once.')
    ap.add_argument('document', nargs='?',
                    help='the document to check, repo-relative')
    ap.add_argument('--target', default=None,
                    help='override the in-document target declaration. '
                         'PRINTED when used -- R2 wants the document to '
                         'declare its own target')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--ablation', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.ablation:
        return ablation()
    if not args.document:
        ap.print_usage()
        print('COULD NOT RUN -- no document given. Nothing was checked.')
        return EXIT_COULD_NOT_RUN

    # ── R8: THE LOCK RUNS BEFORE ANY VERDICT ABOUT A REAL DOCUMENT ────────
    # A rule that has stopped working produces a clean, empty and completely
    # wrong answer, which is the shape dispatch_state.py and sairn_status.py
    # both guard the same way.
    _p, f, fails = run_arms(verbose=False)
    if f:
        print('COULD NOT RUN -- the criteria lock failed its own fixtures, so '
              'nothing was checked:')
        for name, _bad, must, why in fails:
            print('  %s -- wanted: %s' % (name, must))
            print('    %s' % why[:200])
        return EXIT_COULD_NOT_RUN

    code, lines = check(args.document, target_override=args.target)
    for ln in lines:
        print(ln)
    return code


if __name__ == '__main__':
    sys.exit(main())
