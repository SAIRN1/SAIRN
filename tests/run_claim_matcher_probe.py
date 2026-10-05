#!/usr/bin/env python
"""Two things the claim matcher counts as a subject and should not.

    python tests/run_claim_matcher_probe.py

Exit 0 all arms pass, 1 any arm fails.

── THE TWO, BOTH REPRODUCED FROM REAL REFUSALS ─────────────────────────────
1. A DISCLOSURE OF DISJOINTNESS IS NOT A CLAIM. PR 4.3 requires a session to
   NAME the file it is deliberately NOT touching -- "api/sd-data.js is fourth's
   and is NOT taken here" -- and the matcher reads that sentence as evidence
   that both claims want the file. Following the rule makes the rule refuse you,
   which is the worst possible shape for a disclosure convention: the honest
   session is the one that gets blocked.

2. SHARED METHODOLOGY VOCABULARY IS NOT A SHARED SUBJECT. "tests first",
   "known-bad control", "fixture set", "silent half" describe HOW work is done
   on this platform, not WHAT it is done to. Every well-written claim carries
   them, so a bigram drawn from that register blocks essentially any two careful
   sessions.

── AND THE FIX IS MEASURED, NOT A WORD LIST ────────────────────────────────
tools/sairn_claim.py records its own history with a blocklist that "lost six
times" and says it "must not be added to". So (2) is NOT another hand-kept list
of English. A phrase that appears in the claims of MANY DIFFERENT SESSIONS is
common vocabulary by measurement -- the corpus says so, nobody curates it, and a
phrase that stops being common stops being exempt on its own.
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'sairn_claim.py')
CONTROLS_FOR = ['sairn_claim.py']

import sairn_claim as C                                          # noqa: E402

_pass, _fail = 0, 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


def section(t):
    print('\n' + t)


print('CLAIM MATCHER -- a disclosure is not a claim, vocabulary is not a subject')

# ── A. THE KNOWN-BAD, REPRODUCED ───────────────────────────────────────────
section('A. the two refusals this file exists for, driven as they happened')

# CORRECTED AFTER THE FIRST RUN, and the correction was to the FIXTURE rather
# than to the threshold -- discipline 1's first kind. Both strings originally
# read "tests first, plus a known-bad control", which makes the bigram
# `first plus` ACROSS THE COMMA. The corpus says `first plus` is used by two
# sessions and `tests first` by five, so the matcher was right to block on it:
# `first plus` is an artefact of my punctuation, not shared methodology. The
# strings now share the real phrases and nothing else.
MINE_METH = ('build a gap ledger with a known-bad control per tool, tests '
             'first, reporting checked over universe after each batch')
THEIRS_METH = ('wire the citation checker into the push gate with a known-bad '
               'control, tests first, and publish the denominator')
check('A1. KNOWN-BAD: two claims on DIFFERENT subjects sharing only '
      'methodology wording must not block. "tests first" and "known-bad '
      'control" describe how work is done here, not what it is done to',
      C.block_reason('cody-ledger', MINE_METH, 'cc-citation', THEIRS_METH)
      is None,
      C.block_reason('cody-ledger', MINE_METH, 'cc-citation', THEIRS_METH))

MINE_DISC = ('extend the label-shape checker; CONFLICT DECLARED PER PR 4.3 '
             'RATHER THAN REWORDED: api/sd-data.js is fourth\'s and is NOT '
             'taken here, only read')
THEIRS_DISC = 'caregiver role enforcement in api/sd-data.js roleSets'
check('A2. KNOWN-BAD: a DISCLOSURE naming the file it is not touching must not '
      'collide with the session that holds it. PR 4.3 requires that sentence, '
      'so the matcher was refusing the sessions that follow the rule',
      C.block_reason('cody-labels', MINE_DISC, 'fourth-care', THEIRS_DISC)
      is None,
      C.block_reason('cody-labels', MINE_DISC, 'fourth-care', THEIRS_DISC))

# ── B. THE SILENT HALF. Without these, A is satisfied by a matcher that has
#      stopped blocking anything at all. ────────────────────────────────────
section('B. it still blocks what it should -- the half that makes A mean '
        'something')

check('B1. a REAL shared file still blocks. The disclosure exemption must only '
      'reach a file the sentence says it is NOT taking',
      C.block_reason('cody-x', 'rewrite api/sd-data.js roleSets',
                     'fourth-y', 'caregiver role in api/sd-data.js') is not None,
      'a genuine collision on api/sd-data.js was cleared')

check('B2. the same subject still blocks',
      C.block_reason('platform', 'the denominator sweep',
                     'platform', 'the denominator sweep') is not None,
      'identical claims were cleared')

check('B3. a shared phrase that is NOT common vocabulary still blocks. '
      '"overrun inversion" appears in one session\'s work, not in everyone\'s',
      C.block_reason('cody-a', 'the overrun inversion sweep across apps',
                     'cc-b', 'register the overrun inversion class')
      is not None,
      'a genuinely specific shared phrase was cleared')

check('B4. a shared app name still blocks, regardless of vocabulary',
      C.block_reason('a', 'sairnvet formulary sourcing, tests first',
                     'b', 'sairnvet dose audit, tests first') is not None,
      'two claims on the same app were cleared')

# ── C. THE MEASURED HALF -- the exemption is derived, not curated ───────────
section('C. common vocabulary is MEASURED from the claim corpus')

check('C1. common_phrases() exists and is derived from the claim records, not '
      'from a hand-kept list. This file\'s own history records a blocklist that '
      'lost six times and says it must not be added to',
      hasattr(C, 'common_phrases') and callable(C.common_phrases),
      'the exemption is not a measured one')

_common = C.common_phrases()
check('C2. ...and it found a NON-EMPTY set. An empty one would make A1 pass for '
      'the wrong reason -- no exemption fired, the phrase simply was not shared',
      isinstance(_common, set) and len(_common) > 0, len(_common or []))

check('C3. ...and it is a MINORITY of all phrases. If most phrases counted as '
      'common the matcher would stop blocking on wording at all, which is the '
      'failure this exemption is one step away from',
      len(_common) < C.corpus_phrase_count() / 2,
      (len(_common), C.corpus_phrase_count()))

check('C4. the threshold is a NAMED constant, so a change to it is visible '
      'rather than buried in a literal',
      isinstance(getattr(C, 'COMMON_PHRASE_SESSIONS', None), int)
      and C.COMMON_PHRASE_SESSIONS >= 2,
      getattr(C, 'COMMON_PHRASE_SESSIONS', None))

# ── D. THE DISCLOSURE RULE, both directions ────────────────────────────────
section('D. what counts as a disclosure, and what does not')


# THE FIXTURE PREFIX USED TO BE `FILES: api/sd-data.js. ` AND IT HAD TO MOVE
# (2026-10-05). That prefix CLAIMS the file, and under the only-inside rule in
# section E a path claimed anywhere in the string is no longer disclosed by a
# disclaimer elsewhere in it -- correctly. So the old fixture asserted the
# contract the only-inside change deliberately reverses, and four arms went red
# on a fix rather than on a defect. Replaced with a prefix that claims a
# DIFFERENT file, which is what these six arms were always about: does the
# SENTENCE read as a disclosure. Every expectation below is unchanged.
for phrase, disclosed in (
        ('api/sd-data.js is NOT taken here', True),
        ('api/sd-data.js is NOT touched', True),
        ('api/sd-data.js is NOT TOUCHING anything here', True),
        ('api/sd-data.js is DELIBERATELY EXCLUDED', True),
        ('api/sd-data.js is fourth\'s and I do not edit it', True),
        ('api/sd-data.js: add the caregiver role', False),
        ('rewrite api/sd-data.js roleSets', False)):
    got = C.disclosed_files('FILES: sairncare.html. ' + phrase)
    check('D. %-52s -> %s' % ('"' + phrase[:50] + '"',
                              'disclosure' if disclosed else 'a real claim'),
          ('api/sd-data.js' in got) == disclosed, sorted(got))

check('D2. ANCHOR: declared_files still returns None when a claim declares '
      'none, so the disclosure rule cannot turn "no evidence" into "cleared"',
      C.declared_files('no file names here at all') is None,
      C.declared_files('no file names here at all'))

# ── E. ONLY-INSIDE, AND THE MARKERS THE 09-29 FINDING NAMED ────────────────
# docs/2026-09-29-claim-matcher-prose-collisions.md stated the test the rule
# had to obey: *"a token that occurs ONLY inside a blocker clause contributes
# no identifier and no bigram. A claim that both holds and waits on the same
# file must still block, because the token also occurs outside one."* The
# implementation that landed that day took the first half only. These arms hold
# BOTH halves, and the five wordings that were still blocking at HEAD on
# 2026-10-05 are driven by name rather than described.
section('E. a disclosure is ONLY a disclosure when nothing else claims it')

check('E1. a path claimed in one clause and disclaimed in another is NOT '
      'disclosed -- the finding\'s own second half, which the 09-29 '
      'implementation did not carry. Loose direction: it answered CLEAR on '
      'api/sd-data.js to every other session',
      C.disclosed_files('rewrite the sd_crm branch in api/sd-data.js. '
                        'api/sd-data.js is not touched by the hover half')
      == set(),
      sorted(C.disclosed_files(
          'rewrite the sd_crm branch in api/sd-data.js. '
          'api/sd-data.js is not touched by the hover half')))

check('E2. ...and it therefore still BLOCKS another session wanting that file',
      C.block_reason('x', 'fix api/sd-data.js dispatch', 'cody',
                     'rewrite the sd_crm branch in api/sd-data.js. '
                     'api/sd-data.js is not touched by the hover half')
      is not None)

check('E3. UNBLOCKED is not BLOCKED. `blocked` was matched as a bare '
      'substring, so fourth\'s "queue9 items 1,5,6 in api/sd-data.js, NOW '
      'UNBLOCKED" -- a claim TAKING the file -- read as a disclosure of not '
      'taking it. The marker is anchored on a word boundary now',
      C.block_reason(
          'x', 'FILES: api/sd-data.js -- LEG_RESOURCES session gate', 'fourth',
          'queue9 items 1,5,6 in api/sd-data.js, NOW UNBLOCKED '
          '(cc-queue11 explicitly leaves this file to fourth)') is not None)

check('E4. ...and the boundary is on the FRONT ONLY, because a boundary on '
      'both ends stops `not touch` matching NOT TOUCHING and breaks a wording '
      'this list always covered',
      'api/sd-data.js' in C.disclosed_files(
          'tier cells; NOT TOUCHING api/sd-data.js'),
      sorted(C.disclosed_files('tier cells; NOT TOUCHING api/sd-data.js')))

for phrase in ('waiting for api/sd-data.js',
               'blocked on api/sd-data.js',
               'resume when api/sd-data.js frees',
               'skip api/sd-data.js this round',
               'api/sd-data.js belongs to hank'):
    check('E5. blocker clause now clears: "%s"' % phrase,
          C.block_reason('x', 'alf_mar identity fix in api/sd-data.js',
                         'cody', 'tier cells; ' + phrase) is None,
          C.block_reason('x', 'alf_mar identity fix in api/sd-data.js',
                         'cody', 'tier cells; ' + phrase))

# ── E6. THE RESIDUAL IS ASSERTED OPEN, NOT LEFT UNSAID ────────────────────
# Two of the finding's eight wordings are NOT closed, and the arms say so, so
# that closing them later turns an arm red rather than passing silently. The
# reason is the CLAUSE SPLITTER, not the marker list: hank's real claim runs
# "...is not held by another session FILES: api/sd-data.js ..." with no `. `,
# `;` or ` -- ` between the disclaimer and the declared file list, so a marker
# that fired there would exempt a file the session genuinely holds. Measured:
# `holds` costs 61 real blocks, `is <session>'s` 50, `deferred` 73, `conflict
# declared` 22, over all 532,512 cross-session pairs.
for phrase in ("api/sd-data.js is hank's",
               "api/sd-data.js is another session's",
               'deferred, see refusals: api/sd-data.js'):
    check('E6. RESIDUAL, still blocks on purpose: "%s"' % phrase,
          C.block_reason('x', 'alf_mar identity fix in api/sd-data.js',
                         'cody', 'tier cells; ' + phrase) is not None)

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
