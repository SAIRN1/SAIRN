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

for phrase, disclosed in (
        ('api/sd-data.js is NOT taken here', True),
        ('api/sd-data.js is NOT touched', True),
        ('api/sd-data.js is DELIBERATELY EXCLUDED', True),
        ('api/sd-data.js is fourth\'s and I do not edit it', True),
        ('api/sd-data.js: add the caregiver role', False),
        ('rewrite api/sd-data.js roleSets', False)):
    got = C.disclosed_files('FILES: api/sd-data.js. ' + phrase)
    check('D. %-52s -> %s' % ('"' + phrase[:50] + '"',
                              'disclosure' if disclosed else 'a real claim'),
          ('api/sd-data.js' in got) == disclosed, sorted(got))

check('D2. ANCHOR: declared_files still returns None when a claim declares '
      'none, so the disclosure rule cannot turn "no evidence" into "cleared"',
      C.declared_files('no file names here at all') is None,
      C.declared_files('no file names here at all'))

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
