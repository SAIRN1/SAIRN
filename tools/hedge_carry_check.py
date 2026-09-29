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

CRITERIA_VERSION = '2026-09-29.1'

# ── THE HEDGES. A small closed set, and the closure is the criterion.
# Every entry is a word that makes a claim WEAKER than its unhedged form, and
# nothing else. "likely" belongs; "important" does not, because it is emphasis
# rather than uncertainty. A wide list would fire on every dispatch and the check
# would be switched off in a day.
HEDGES = ('likely', 'possible', 'possibly', 'probably', 'probable', 'may be',
          'might be', 'appears', 'appear to', 'seems', 'i think', 'i believe',
          'unclear', 'not sure', 'suspect', 'perhaps', 'arguably',
          'could be', 'looks like')

# ── WHAT COUNTS AS CARRYING IT FORWARD OR RESOLVING IT.
# Either the hedge word itself survives into the message -- the claim stayed
# hedged -- or the message states an outcome ABOUT the uncertainty. Both are
# honest; only silence is not.
RESOLVED = re.compile(
    r'\bis not\b|\bwas not\b|\bnot supported\b|\bdoes not\b|\bturned out\b|'
    r'\bconfirmed\b|\bverified\b|\bmeasured\b|\bre-?read\b|\bchecked\b|'
    r'\bit is\b|\bproved\b|\bdisproved\b|\bfalse\b|\bholds\b|'
    r'\bnot supported\b|\bre-derived\b', re.I)


def hedges_in(text):
    """Every hedge present, with the sentence it sits in."""
    low = (text or '').lower()
    out = []
    for h in HEDGES:
        for m in re.finditer(r'(?<![a-z])' + re.escape(h) + r'(?![a-z])', low):
            # The sentence around it, so a reader can see WHAT was hedged rather
            # than only that something was. A bare word list would be unusable.
            lo = max(0, low.rfind('.', 0, m.start()) + 1)
            hi = low.find('.', m.end())
            hi = len(text) if hi == -1 else hi + 1
            out.append({'hedge': h, 'context': ' '.join(text[lo:hi].split())[:220]})
            break     # one report per hedge word, not per occurrence
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


def judge(item, commits):
    """[(hedge, verdict, context)] -- verdict CARRIED | RESOLVED | DROPPED."""
    low = (commits or '').lower()
    out = []
    for h in hedges_in(item):
        word = h['hedge']
        if re.search(r'(?<![a-z])' + re.escape(word) + r'(?![a-z])', low):
            out.append((word, 'CARRIED', h['context']))
        elif RESOLVED.search(commits or ''):
            out.append((word, 'RESOLVED', h['context']))
        else:
            out.append((word, 'DROPPED', h['context']))
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
