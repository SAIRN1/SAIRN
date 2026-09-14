"""Did the FMEA drafts actually predict the defects that then happened?

    python tools/fmea_prediction_check.py
    python tools/fmea_prediction_check.py --json
    python tools/fmea_prediction_check.py --since 2026-09-01

── THIS IS THE CADENCE MECHANISM, AND IT IS DELIBERATELY SUBJECT-SPECIFIC ─
The obvious build was a general "re-trigger the audits on a schedule"
scheduler. That is infrastructure with nothing to carry: an abstraction
extracted from ONE instance is a guess about the second. This checks one real
thing -- whether a saved risk draft predicted a real later defect -- and it
recurs because the answer changes every time the defect register grows. If a
second subject ever needs the same shape, extract the general mechanism THEN,
from two real implementations.

── WHAT IT SCORES ────────────────────────────────────────────────────────
tools/fmea_draft.py --save writes docs/fmea/<slug>.json. Each is a dated
prediction about one file. This walks forward from each draft's date and asks,
for every defect recorded in that file AFTER it:

  PREDICTED   a risk in the draft cites the same rule or names the same
              failure shape as the defect that then happened.
  MISSED      a defect landed in a drafted file and no risk matched it.
  NO DRAFT    a defect landed in a file that was never drafted at all.
  DRAFT NEWER a draft exists for the file but postdates the defect, so it
              cannot have predicted it. UNSCOREABLE BY CONSTRUCTION, and a
              separate bucket since 2026-09-13 -- it used to be folded into
              NO DRAFT, which called twelve drafts on disk "no draft".

── THE NUMBER THAT MATTERS IS THE THIRD ONE, AND IT IS WHY THIS EXISTS ────
A hit rate computed only over drafted files is the truncation shape this
platform keeps finding: it would read as "the FMEA is 80% accurate" while
saying nothing about the files nobody drafted. So NO DRAFT is reported first
and counted in the denominator of the honest figure. A rate quoted without it
is wrong, not partial.

── WHAT IT CANNOT SEE, said here rather than discovered later ────────────
  * whether a PREDICTED risk actually caused anyone to look. A draft that
    predicted a defect nobody read is scored the same as one that prevented it,
    and this cannot tell them apart;
  * a defect that was prevented and therefore never recorded. The register
    holds confirmed defects, so successful prevention is invisible here BY
    CONSTRUCTION and the hit rate is a floor, never a ceiling;
  * matching is by RULE CITATION ONLY. Word-overlap scoring was tried, scored
    38%, and EVERY ONE OF THOSE FIVE HITS WAS A FALSE POSITIVE -- see matched().
    A prediction phrased differently from the eventual defect scores as a miss,
    which biases the number DOWN, the safe direction.
  * THE CITATION GAP IS CLOSED as of 2026-09-13. All 54 register records now
    carry `rules`, `citation_confidence` and, where they need one, a note:
    48 cited (32 clean, 16 arguable) and 6 deliberately NOT-CITABLE. Four of
    the six that had been not-citable became clean the moment PR 1.11 was
    written, because they were four instances of a rule that did not exist yet.
  * CLOSING IT DID NOT PRODUCE A NUMBER, AND THAT IS THE HONEST OUTCOME. Every
    draft on disk was saved after every defect on record, so nothing is
    scoreable yet: 0 predicted, 0 missed, 0%. The first defect that lands in a
    drafted file after today is the first one this can score.

Exit 0 always. This reports; it never gates.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')
FMEA_DIR = os.path.join(REPO, 'docs', 'fmea')

# Words that carry no failure-shape signal. Without this, "the" and "a" match
# everything and every defect scores as predicted -- the horoscope failure one
# level up from the detectors.
STOP = set(('the a an and or of to in is was were it its that this for on with '
            'not no be been has have had by from as at so what when which who '
            'than then there here they them their all any one two into out up '
            'only also more most some such each every both other same').split())


def words(s):
    return set(w for w in re.findall(r'[a-z_]{4,}', (s or '').lower()) if w not in STOP)


def load_register():
    with io.open(REGISTER, encoding='utf-8') as fh:
        return json.load(fh).get('records', [])


def load_drafts():
    out = []
    if not os.path.isdir(FMEA_DIR):
        return out
    for name in sorted(os.listdir(FMEA_DIR)):
        if not name.endswith('.json'):
            continue
        p = os.path.join(FMEA_DIR, name)
        try:
            d = json.load(io.open(p, encoding='utf-8'))
        except Exception:
            continue
        d['_file'] = 'docs/fmea/' + name
        # The draft's own date is the mtime of the file it was saved as, which
        # is not durable. Prefer an explicit field; fall back to the newest
        # defect it cites, which is a LOWER bound on when it was written.
        dates = [r.get('date') for r in d.get('risks', []) if r.get('date')]
        d['_asof'] = d.get('drafted_on') or (max(dates) if dates else None)
        out.append(d)
    return out


def matched(draft, rec):
    """Did any risk in this draft name the shape this defect turned out to be?

    ── THE FIRST VERSION SCORED 38% AND EVERY ONE WAS A FALSE POSITIVE ────
    It matched on three shared content words. Measured on the real corpus that
    produced five "predictions", ALL FIVE from one draft of a WORKLOG file, on
    overlaps like (never, nothing, push) and (could, pass, reported). A worklog
    accumulates the prose of every defect ever recorded, so drafting one
    produces risks containing every word, and a three-word bar matches
    anything. That is the fabrication risk this whole tool was designed against,
    arriving through the MATCHER instead of the generator.

    So word-overlap scoring is GONE. The only match that means "the same named
    failure mode" is a rule citation on both sides.

    IT CAN FIRE AS OF 2026-09-13. The register carried
    app/files/layer/severity/detection_method and NOT which standing rule each
    defect instantiated, so this scored 0 and said so. All 54 records now carry
    `rules`. Inventing a looser matcher in the meantime is how the 38% happened,
    and it was not done.

    NOTE WHAT `rules` MUST NOT BECOME. The register admits three confidences --
    clean, arguable and NOT-CITABLE -- precisely so that a record with no
    matching rule can say so instead of being pushed into the nearest one. If
    every record were made to cite something, this matcher would start hitting
    on manufactured agreement, and the 38% would come back through the DATA
    instead of through the matcher.
    """
    want = rec.get('rules') or []
    for r in draft.get('risks', []):
        cite = r.get('cite', '')
        if 'SAIRN-PROCESS-RULES' in cite:
            rid = cite.rsplit(' ', 1)[-1]
            if rid and rid in want:
                return ('rule ' + rid, r)
            continue
        # ── A SAME-FILE REGISTER RISK NOW CARRIES ITS OWN RULE IDS ────────
        # Added 2026-09-14. Everything above scores only on a risk that cites
        # the rules document, and no defect-register risk does -- it cites a
        # commit SHA. MEASURED before the change, over the 12 drafts then on
        # disk: 19 of 274 risks, 6.9%, could EVER match. So drafting the 60
        # undrafted code files would have raised coverage while leaving the
        # scoreable surface almost exactly where it was.
        #
        # STILL EXACT-ID EQUALITY, not the word-overlap matcher that scored
        # 38% with five false positives. The ids come from the register's
        # `rules` field, which a person set per record with a confidence flag,
        # and a `not-citable` record carries [] and matches nothing.
        #
        # ONLY SAME-FILE RISKS CARRY THEM -- fmea_draft.py withholds `rules`
        # from the same-app block on purpose, because a rule that bit a
        # SIBLING file would make almost every PLATFORM draft carry the
        # commonest ids and turn PREDICTED into "this platform has seen this
        # kind of thing before".
        #
        # IT CHANGES NOTHING TODAY AND THAT WAS KNOWN BEFORE IT WAS RUN: every
        # draft on disk postdates every defect, so the scoreable set is empty
        # and this cannot flatter the current number. It takes effect only on
        # defects recorded from here on.
        for rid in (r.get('rules') or []):
            if rid in want:
                return ('rule ' + rid + ' (same-file register risk)', r)
    return (None, None)


# Targets that are RECORDS OF defects rather than code that can have one. A
# draft for a worklog is a category error -- it matches prose ABOUT failures,
# which is docs/SAIRN-PROCESS-RULES.md section 1.2 one level up.
NOT_A_CODE_TARGET = re.compile(r'(^|/)(SAIRN-ACTIVE-WORK|docs/|.*\.md$)')


def main(argv):
    since = None
    if '--since' in argv:
        i = argv.index('--since')
        since = argv[i + 1] if i + 1 < len(argv) else None

    try:
        records = load_register()
    except Exception as e:
        print('docs/defect-density-register.json could not be read: %s. NOT a pass.' % e)
        return 2
    drafts = load_drafts()
    by_target = {}
    for d in drafts:
        by_target.setdefault(d.get('target'), []).append(d)

    # TWO BUCKETS, NOT ONE, SPLIT 2026-09-13. `nodraft` used to hold both "no
    # draft exists for this file" and "a draft exists but is NEWER than the
    # defect, so it cannot have predicted it", and the report called the whole
    # pile "FILES WITH A DEFECT AND NO DRAFT". The moment twelve drafts existed
    # that label was false for every one of them: drafts were on disk, for
    # exactly those files, and the output said there were none. Two different
    # states with two different things to do about them -- one needs a draft
    # written, the other needs TIME TO PASS -- and merging them made the second
    # look like unfinished work.
    predicted, missed, nodraft, too_new = [], [], [], []
    for rec in records:
        if since and str(rec.get('date', '')) < since:
            continue
        files = rec.get('files') or []
        cand, any_draft = [], False
        for f in files:
            for d in by_target.get(f, []):
                any_draft = True
                # Only a draft written BEFORE the defect can have predicted it.
                #
                # `>=`, NOT `>`, CORRECTED 2026-09-13 ON THE FIRST RUN THAT EVER
                # HAD DRAFTS ON DISK. With `>`, a draft dated the SAME DAY as a
                # defect counted as having predicted it -- and twelve drafts
                # saved that afternoon immediately scored one PREDICTION against
                # a defect from that morning. The draft was written after the
                # defect, cited the record describing it, and matched it.
                #
                # A same-day draft cannot be SHOWN to precede the defect, and
                # this tool exists to be the honest measure of exactly that. The
                # dates here are day-resolution, so equality is a could-not-tell
                # and could-not-tell is never credited. It costs real predictions
                # -- a draft written in the morning that catches something that
                # afternoon scores nothing -- and that is the right direction:
                # this number is quoted as evidence the method works.
                if d['_asof'] and rec.get('date') and d['_asof'] >= rec['date']:
                    continue
                cand.append((f, d))
        if not cand:
            (too_new if any_draft else nodraft).append(rec)
            continue
        hit = None
        for f, d in cand:
            why, risk = matched(d, rec)
            if why:
                hit = (f, d, why, risk)
                break
        (predicted if hit else missed).append((rec, hit or cand[0]))

    total = len(predicted) + len(missed) + len(nodraft) + len(too_new)
    if '--json' in argv:
        print(json.dumps({
            'drafts_on_disk': len(drafts),
            'defects_considered': total,
            'no_draft': len(nodraft),
            'draft_newer_than_defect': len(too_new),
            'predicted': len(predicted),
            'missed': len(missed),
            'honest_rate_over_all_defects':
                (round(100.0 * len(predicted) / total, 1) if total else None),
            'rate_over_drafted_only_DO_NOT_QUOTE_ALONE':
                (round(100.0 * len(predicted) / (len(predicted) + len(missed)), 1)
                 if (predicted or missed) else None)
        }, indent=1))
        return 0

    print('FMEA PREDICTION CHECK -- report only, nothing was written')
    print('  drafts on disk        : %d' % len(drafts))
    print('  defects considered    : %d%s' % (total, (' since ' + since) if since else ''))
    print('')
    print('  NO DRAFT AT ALL       : %d   <- READ THIS FIRST' % len(nodraft))
    print('  DRAFT EXISTS BUT IS NEWER THAN THE DEFECT: %d' % len(too_new))
    print('    (unscoreable BY CONSTRUCTION, not unfinished work -- a draft')
    print('     cannot predict what already happened. These need TIME, not a')
    print('     draft. Split out 2026-09-13, when twelve drafts on disk were')
    print('     being reported as NO DRAFT AT ALL.)')
    print('  predicted             : %d' % len(predicted))
    print('  missed (drafted, not predicted): %d' % len(missed))
    if total:
        print('')
        print('  HONEST RATE, over every defect: %.0f%%'
              % (100.0 * len(predicted) / total))
        if predicted or missed:
            print('  (over drafted files only : %.0f%% -- DO NOT QUOTE THIS ALONE. It'
                  % (100.0 * len(predicted) / (len(predicted) + len(missed))))
            print('   excludes the %d defect(s) in files nobody drafted and the %d'
                  % (len(nodraft), len(too_new)))
            print('   whose only draft postdates them, which is the')
            print('   truncation shape this platform keeps finding.)')

    if not drafts:
        print('')
        print('  NO DRAFTS EXIST YET, so every defect is NO DRAFT and the rate is 0%.')
        print('  That is an honest zero, not a failure of the method. Draft a file:')
        print('     python tools/fmea_draft.py <path> --save')
    elif not predicted and not missed:
        print('')
        print('  EVERY DRAFT POSTDATES EVERY DEFECT, so nothing is scoreable yet and')
        print('  the rate is 0%. That is the CORRECT reading of a loop that has just')
        print('  been closed, not a failed method and not a coverage gap: the drafts')
        print('  are in place and the first defect that lands in a drafted file after')
        print('  today is the first one this can score.')

    for rec, hit in predicted[:10]:
        print('')
        print('  PREDICTED  %s  %s' % (rec.get('date'), (rec.get('summary') or '')[:90]))
        print('             by %s (%s)' % (hit[1]['_file'], hit[2]))
    for rec, _ in missed[:10]:
        print('')
        print('  MISSED     %s  %s' % (rec.get('date'), (rec.get('summary') or '')[:90]))
        print('             a draft existed for this file and named nothing like it')
    if nodraft:
        print('')
        print('  FILES WITH A DEFECT AND NO DRAFT (first 10 of %d):' % len(nodraft))
        for rec in nodraft[:10]:
            print('     %-12s %s' % (rec.get('date'), ', '.join(rec.get('files') or [])[:80]))
    return 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
