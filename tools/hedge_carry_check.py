r"""A HEDGE IN A DISPATCH IS THE MOST INFORMATION-DENSE WORD IN IT.

    python tools/hedge_carry_check.py --item "<the dispatched text>" --range A..B
    python tools/hedge_carry_check.py --item-file <path> --range A..B
    python tools/hedge_carry_check.py --selftest

REPORT ONLY. Exit 0 clean, 1 findings, 2 COULD NOT RUN. Writes nothing.

── WHY THIS AND NOT THE GATE THAT WAS SCOPED ───────────────────────────────
`docs/2026-09-29-gray-error-check-scope.md` designed a restatement gate: store the
dispatched paste, make the working session restate each item before its first file
read, diff the two. **Its fatal failure mode is that the same session writes the
restatement and does the work** -- then it compares a session's plan to its own
plan, which is a detector blessing its own subject.

**What survives that objection is one rule that needs no second reader.** A
dispatch that says *"likely Tier A"*, *"possible"*, *"probably"* is making a
WEAKER claim than one that says *"promote it"*. The hedge is the first thing lost
in restatement and the last thing anybody notices missing. So:

> extract every hedge from the dispatched item, and require the commit message
> to either CARRY THE HEDGE FORWARD or state the finding that REMOVED it.

The commit message already exists, is already written by the working session, and
is already read by the push gate. No new artifact, no second session, no new cost.

── THE REAL INSTANCE, FROM THIS PLATFORM ───────────────────────────────────
Dispatched: *"sv_financials, dnt_vendor_orders, leg_insurance and msb_food_waste
are LIKELY Tier A on the money limb."*

`msb_food_waste` is not -- `computeMsbFoodCostPct()` never reads it. Every
mechanical check on the platform was green for both the right answer and the wrong
one: `criticality_tier_check.py` exits 0 whether that row is A or B. **The only
thing between the dispatch and a wrong Tier A was a session choosing to read the
consumers and report that the premise was false.**

The commit that did the work says, in terms: *"the routed finding said LIKELY TIER
A. IT IS NOT, and the re-read is recorded rather than the finding quietly
dropped."* That is a PASS. A commit promoting the row with no such sentence is
what this check is for.

── WHAT IT CANNOT DO, so nothing reads it as more than it is ───────────────
* It cannot tell whether the finding that removed a hedge is CORRECT. It checks
  that one was stated.
* It cannot see a hedge that was never written. A dispatch stating a false premise
  flatly is invisible here, and that is the restatement gate's job -- which is on
  the shelf for the reason above.
* It is DISPATCH-TEXT IN, COMMIT-TEXT OUT. It has no memory and no store, because
  a store is the artifact this design exists to avoid.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

CRITERIA_VERSION = '2026-09-29.2'

# ── THE HEDGES. A small closed set, and the closure is the criterion.
# Every entry is a word that makes a claim WEAKER than its unhedged form, and
# nothing else. "likely" belongs; "important" does not, because it is emphasis
# rather than uncertainty. A wide list would fire on every dispatch and the check
# would be switched off in a day.
#
# ── THREE OF THEM WERE MATCHED AS BARE WORDS AND THREE OF THEM ARE POLYSEMOUS.
#    FIXED 2026-09-29 (hank), and the false DROPPED is reproduced in the probe.
#
# The first version matched each entry with nothing but word boundaries around
# it. Driven against a real dispatch, three entries fired on sentences that make
# a FLAT factual claim and hedge nothing at all:
#
#   `appears`   "The resource name APPEARS IN citation_drift_hook.py's docstring"
#               -- `appears` here means OCCURS. It is a hedge only in
#               "appears to <verb>" and "appears that".
#   `possible`  "confirm the only POSSIBLE VALUES are A and B" -- enumerative,
#               not uncertain. It IS a hedge in "possible Tier A" and "it is
#               possible that", which is why the word stays and only the
#               enumerating determiners are excluded.
#   `suspect`   "The named SUSPECT is the matcher, not the tool" -- a NOUN. It is
#               a hedge only as a verb: "I suspect", "we suspect that".
#
# Each of those produced a DROPPED verdict against a commit that had nothing to
# answer for, which is a FALSE FINDING -- and a false finding on a check about
# honesty is the worst possible defect for it to have.
#
# AND THE SAME LINE CAUSED A FALSE NEGATIVE, which is the half worth naming: the
# loop `break`s after the first occurrence of each word, so a non-hedging
# "appears in" EARLIER in a dispatch SHADOWED a real "appears to be" later. One
# bug, both directions. The break is gone; every distinct occurrence is judged,
# bounded at MAX_CONTEXTS per word so the report stays readable.
#
# The entries are now (label, pattern) pairs. The fourteen unambiguous ones keep
# a plain escaped-word pattern so nothing changes for them.
MAX_CONTEXTS = 3

def _word(w):
    return r'(?<![a-z])' + w.replace(' ', r'\s+') + r'(?![a-z])'

HEDGE_PATTERNS = (
    ('likely',     _word('likely')),
    ('possibly',   _word('possibly')),
    ('probably',   _word('probably')),
    ('probable',   _word('probable')),
    ('may be',     _word('may be')),
    ('might be',   _word('might be')),
    ('seems',      _word('seems')),
    ('i think',    _word('i think')),
    ('i believe',  _word('i believe')),
    ('unclear',    _word('unclear')),
    ('not sure',   _word('not sure')),
    ('perhaps',    _word('perhaps')),
    ('arguably',   _word('arguably')),
    ('could be',   _word('could be')),
    ('looks like', _word('looks like')),
    # ── the three disambiguated ones ──────────────────────────────────────
    # `appears`/`appear` hedge only before `to` or `that`.
    ('appears to', r'(?<![a-z])appears?\s+(?:to|that)(?![a-z])'),
    # `possible` is not a hedge when it enumerates. The excluded determiners are
    # the ones that make it a completeness claim rather than an uncertain one.
    ('possible',   r'(?<!\bonly\s)(?<!\ball\s)(?<!\bevery\s)(?<!\beach\s)'
                   r'(?<!\bany\s)(?<!\bno\s)(?<!\bthe\s)'
                   r'(?<![a-z])possible(?![a-z])'),
    # `suspect` hedges only as a verb: a pronoun before it, or `that` after it.
    ('suspect',    r'(?:(?<![a-z])(?:i|we|they|you)\s+suspect(?:s|ed)?(?![a-z])'
                   r'|(?<![a-z])suspects?(?:ed)?\s+that(?![a-z]))'),
)

# Kept as a name for anything that imported it, and derived rather than
# restated, so the two can no longer disagree.
HEDGES = tuple(label for label, _ in HEDGE_PATTERNS)

# ── WHAT COUNTS AS CARRYING IT FORWARD OR RESOLVING IT.
# Either the hedge word itself survives into the message -- the claim stayed
# hedged -- or the message states an outcome ABOUT the uncertainty. Both are
# honest; only silence is not.
RESOLVED = re.compile(
    r'\bis not\b|\bwas not\b|\bnot supported\b|\bdoes not\b|\bturned out\b|'
    r'\bconfirmed\b|\bverified\b|\bmeasured\b|\bre-?read\b|\bchecked\b|'
    r'\bit is\b|\bproved\b|\bdisproved\b|\bfalse\b|\bholds\b|'
    r'\bnot supported\b|\bre-derived\b', re.I)


# A SENTENCE END IS A DOT FOLLOWED BY WHITESPACE OR THE END OF THE TEXT.
# The first version used a bare `.`, so the context for a dispatch naming
# `citation_drift_hook.py` was cut to "The resource name appears in
# citation_drift_hook." -- a reader could not see what was hedged, on a report
# whose whole value is showing them.
_SENT_END = re.compile(r'\.(?=\s|$)')


def _sentence_around(text, lo_i, hi_i):
    low = text.lower()
    lo = 0
    for m in _SENT_END.finditer(low, 0, lo_i):
        lo = m.end()
    m = _SENT_END.search(low, hi_i)
    hi = len(text) if not m else m.end()
    return ' '.join(text[lo:hi].split())[:220]


def hedges_in(text):
    """Every hedge occurrence, with the sentence it sits in.

    EVERY OCCURRENCE, not the first. The first version broke after one match per
    word, so a non-hedging use earlier in a dispatch hid a real hedge later.
    """
    src = text or ''
    low = src.lower()
    out = []
    for label, pat in HEDGE_PATTERNS:
        seen = 0
        for m in re.finditer(pat, low):
            if seen >= MAX_CONTEXTS:
                break
            out.append({'hedge': label,
                        'context': _sentence_around(src, m.start(), m.end())})
            seen += 1
    return out


def commit_text(rng):
    """Every commit message in the range, joined. (text, None) or (None, why)."""
    try:
        p = subprocess.run(['git', '-C', REPO, 'log', '--format=%B', rng],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=60)
    except Exception as exc:
        return None, 'git log raised %s' % type(exc).__name__
    if p.returncode != 0:
        return None, ('git log %s exited %d (%s)'
                      % (rng, p.returncode, (p.stderr or '').strip()[:120]))
    body = p.stdout or ''
    if not body.strip():
        return None, ('the range %s contains no commits, so there is no message '
                      'to check a hedge against' % rng)
    return body, None


PATTERN_BY_LABEL = dict(HEDGE_PATTERNS)


def judge(item, commits):
    """[(hedge, verdict, context)] -- verdict CARRIED | RESOLVED | DROPPED.

    CARRIED is decided with the hedge's OWN pattern, not with its label spelled
    out -- `appears to` is a label, and looking for the literal string
    "appears to" in a commit would miss "appears that" and would have been a
    second place for the two spellings to disagree.
    """
    low = (commits or '').lower()
    out = []
    for h in hedges_in(item):
        label = h['hedge']
        pat = PATTERN_BY_LABEL.get(label, r'(?<![a-z])' + re.escape(label)
                                   + r'(?![a-z])')
        if re.search(pat, low):
            out.append((label, 'CARRIED', h['context']))
        elif RESOLVED.search(commits or ''):
            out.append((label, 'RESOLVED', h['context']))
        else:
            out.append((label, 'DROPPED', h['context']))
    return out


def selftest():
    """Every criterion against a known-bad fixture BEFORE any real dispatch.

    The standing rule after two criteria came out wrong this week: a sweep that
    counted `open(` as corroboration reported 3 of 263 and looked like good news,
    and a citation repoint was not idempotent. A vacuous pass has to be
    impossible by construction.
    """
    bad = 0

    def arm(name, cond, detail=''):
        nonlocal bad
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))
        if not cond:
            bad += 1
            if detail:
                print('       %s' % str(detail)[:300])

    item = ('sv_financials, dnt_vendor_orders, leg_insurance and msb_food_waste '
            'are likely Tier A on the money limb.')
    arm('the hedge is found in the real dispatch sentence',
        [h['hedge'] for h in hedges_in(item)] == ['likely'], hedges_in(item))
    arm('and the CONTEXT comes with it, so a reader sees WHAT was hedged',
        'msb_food_waste' in (hedges_in(item)[0]['context'] if hedges_in(item)
                             else ''), hedges_in(item))

    # DROPPED: a commit that promotes with no sentence about the uncertainty.
    v = judge(item, 'feat(tiers): promote msb_food_waste to Tier A on the money limb')
    arm('KNOWN-BAD: a commit that promotes and says nothing about the hedge is '
        'DROPPED', v and v[0][1] == 'DROPPED', v)

    # RESOLVED: the real commit's own wording.
    real = ('the routed finding said LIKELY TIER A. IT IS NOT, and the re-read is '
            'recorded rather than the finding quietly dropped')
    v = judge(item, real)
    arm('the REAL commit that did this work passes -- it carries the hedge AND '
        'states what removed it', v and v[0][1] in ('CARRIED', 'RESOLVED'), v)

    # CARRIED: the hedge survives verbatim.
    v = judge(item, 'chore: msb_food_waste is likely A, not yet decided')
    arm('a commit that keeps the hedge is CARRIED', v and v[0][1] == 'CARRIED', v)

    # NO HEDGE: nothing to check, and that is not a pass to celebrate.
    v = judge('promote msb_food_waste to Tier A', 'feat: promoted it')
    arm('an UNHEDGED dispatch produces no findings -- and the report says it '
        'checked nothing rather than printing a clean line', v == [], v)

    # EMPHASIS IS NOT A HEDGE. The closure of the list is the criterion.
    v = judge('this is IMPORTANT and URGENT', 'feat: did it')
    arm('KNOWN-BAD THE OTHER WAY: emphasis is NOT a hedge, so a wide word list '
        'cannot make this fire on every dispatch', v == [], v)

    # ── THE FALSE DROPPED, REPRODUCED. Three polysemous entries, each on the
    #    real sentence that produced the false finding, against a REAL PLAIN
    #    COMMIT MESSAGE -- the shape the item named. Every one must be silent.
    plain = 'chore(register): reseat after the rebase'
    v = judge("The resource name appears in citation_drift_hook.py's DOCSTRING "
              'and in invocation_path_scan.py\'s docstring, as the worked '
              'example.', plain)
    arm('FALSE DROPPED, FIXED: `appears` meaning OCCURS is not a hedge, and a '
        'real plain commit no longer answers for it', v == [], v)
    v = judge('Strip comments and block comments, then confirm the only '
              'possible values are A and B.', plain)
    arm('FALSE DROPPED, FIXED: `possible` ENUMERATING is not a hedge', v == [], v)
    v = judge('The named suspect is the matcher, not the tool.', plain)
    arm('FALSE DROPPED, FIXED: `suspect` as a NOUN is not a hedge', v == [], v)

    # ── AND THE REAL FORMS MUST STILL FIRE, or the fix is a deletion.
    v = judge('This appears to be a Tier A resource.', plain)
    arm('and `appears to` STILL fires -- the fix disambiguates, it does not '
        'delete the entry', v and v[0][1] == 'DROPPED', v)
    v = judge('It is possible that the register is right.', plain)
    arm('and `possible that` STILL fires', v and v[0][1] == 'DROPPED', v)
    v = judge('I suspect the matcher is reading the wrong column.', plain)
    arm('and `I suspect` STILL fires', v and v[0][1] == 'DROPPED', v)

    # ── THE SHADOWING, which is the same bug pointing the other way.
    shadowed = ('The name appears in the docstring. Separately, the row '
                'appears to be Tier A on the money limb.')
    v = judge(shadowed, plain)
    arm('THE FALSE NEGATIVE THE SAME LINE CAUSED: a non-hedging "appears in" '
        'earlier in the dispatch used to SHADOW a real "appears to be" later, '
        'because the loop broke after the first match. The real hedge is now '
        'reported UNDER ITS OWN LABEL -- `appears to`, which the bare-word '
        'version could not produce',
        len(v) == 1 and v[0][0] == 'appears to' and v[0][1] == 'DROPPED', v)
    arm('and its CONTEXT is the sentence with the real hedge in it, not the '
        'first one', v and 'appears to be Tier A' in v[0][2], v)

    # ── THE CONTEXT BOUNDARY, which used to break on a filename.
    # THE FILENAME SITS BEFORE THE HEDGE ON PURPOSE. With it after, the old
    # bare-dot boundary happened to produce the right answer and the arm proved
    # nothing -- which is the fixture-validity trap this file already records
    # about its own first version.
    h = hedges_in('The row appears to be Tier A because '
                  'citation_drift_hook.py reads it that way.')
    arm('a sentence boundary is a dot followed by SPACE -- a dot inside '
        '`citation_drift_hook.py` no longer TRUNCATES the context at the '
        'filename, which is the half a reader needs',
        h and h[0]['context'] == 'The row appears to be Tier A because '
        'citation_drift_hook.py reads it that way.', h and h[0]['context'])

    print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
    return EXIT_CLEAN if not bad else EXIT_FINDING


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--item', default=None)
    ap.add_argument('--item-file', default=None)
    ap.add_argument('--range', default=None)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        print('HEDGE CARRY -- selftest, fixtures before any real dispatch')
        return selftest()

    item = args.item
    if args.item_file:
        if not os.path.isfile(args.item_file):
            print('COULD NOT RUN: --item-file %s is not on disk.' % args.item_file)
            return EXIT_COULD_NOT_RUN
        item = io.open(args.item_file, encoding='utf-8', errors='replace').read()
    if not (item or '').strip():
        print('COULD NOT RUN: no dispatched text was given. Pass --item or '
              '--item-file. An empty item yields no hedges, which would read as '
              '"nothing was dropped".')
        return EXIT_COULD_NOT_RUN
    if not args.range:
        print('COULD NOT RUN: no --range. The check compares a dispatch against '
              'the COMMIT MESSAGES of the work, and without a range there is '
              'nothing to compare.')
        return EXIT_COULD_NOT_RUN

    commits, why = commit_text(args.range)
    if commits is None:
        print('COULD NOT RUN: %s' % why)
        print('That is a third state, not "no hedge was dropped".')
        return EXIT_COULD_NOT_RUN

    found = hedges_in(item)
    print('HEDGE CARRY -- a weaker claim must not silently become a stronger one')
    print('  criteria : %s' % CRITERIA_VERSION)
    print('  range    : %s' % args.range)
    print('  hedges in the dispatched item: %d' % len(found))
    if not found:
        print()
        print('  NOTHING TO CHECK. The item carries no hedge, so this check made')
        print('  no assertion about it -- which is not the same as the work being')
        print('  faithful to the item. A flat false premise is invisible here and')
        print('  is the restatement gate\'s job; see')
        print('  docs/2026-09-29-gray-error-check-scope.md for why that is not built.')
        return EXIT_CLEAN

    verdicts = judge(item, commits)
    dropped = [v for v in verdicts if v[1] == 'DROPPED']
    print()
    for word, verdict, ctx in verdicts:
        print('  %-9s %-9s %s' % (verdict, '`%s`' % word, ctx))
    print()
    if dropped:
        print('DROPPED (%d) -- the dispatch hedged and no commit message either '
              'carried the hedge forward or said what removed it. The hedge is '
              'the most information-dense word in a dispatch and the first thing '
              'lost in restatement.' % len(dropped))
    else:
        print('Every hedge is either carried forward or resolved in the commit '
              'messages.')
    print()
    print('  IT CANNOT TELL WHETHER THE FINDING THAT REMOVED A HEDGE IS CORRECT.')
    print('  It checks that one was STATED. And it cannot see a hedge that was')
    print('  never written -- a dispatch asserting a false premise flatly is')
    print('  invisible here by construction.')

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'range': args.range,
                          'verdicts': [{'hedge': w, 'verdict': v,
                                        'context': c} for w, v, c in verdicts]},
                         indent=2))
    return EXIT_FINDING if dropped else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
