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
  * and it therefore scores ZERO until docs/defect-density-register.json
    records WHICH standing rule each defect instantiated. That gap is the real
    finding of the first run, not a bug in the scorer.

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

    AND THAT CANNOT FIRE YET, WHICH IS THE REAL FINDING. The defect register
    records app/files/layer/severity/detection_method -- but NOT which standing
    rule each defect instantiated. Until it does, this scores 0 and says so.
    Adding a `rules` field to docs/defect-density-register.json is the small,
    concrete thing that closes the loop; inventing a looser matcher to produce a
    number in the meantime is how the 38% happened.
    """
    for r in draft.get('risks', []):
        cite = r.get('cite', '')
        if 'SAIRN-PROCESS-RULES' not in cite:
            continue
        rid = cite.rsplit(' ', 1)[-1]
        if rid and rid in (rec.get('rules') or []):
            return ('rule ' + rid, r)
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

    predicted, missed, nodraft = [], [], []
    for rec in records:
        if since and str(rec.get('date', '')) < since:
            continue
        files = rec.get('files') or []
        cand = []
        for f in files:
            for d in by_target.get(f, []):
                # Only a draft written BEFORE the defect can have predicted it.
                if d['_asof'] and rec.get('date') and d['_asof'] > rec['date']:
                    continue
                cand.append((f, d))
        if not cand:
            nodraft.append(rec)
            continue
        hit = None
        for f, d in cand:
            why, risk = matched(d, rec)
            if why:
                hit = (f, d, why, risk)
                break
        (predicted if hit else missed).append((rec, hit or cand[0]))

    total = len(predicted) + len(missed) + len(nodraft)
    if '--json' in argv:
        print(json.dumps({
            'drafts_on_disk': len(drafts),
            'defects_considered': total,
            'no_draft': len(nodraft),
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
    print('  predicted             : %d' % len(predicted))
    print('  missed (drafted, not predicted): %d' % len(missed))
    if total:
        print('')
        print('  HONEST RATE, over every defect: %.0f%%'
              % (100.0 * len(predicted) / total))
        if predicted or missed:
            print('  (over drafted files only : %.0f%% -- DO NOT QUOTE THIS ALONE. It'
                  % (100.0 * len(predicted) / (len(predicted) + len(missed))))
            print('   excludes the %d defect(s) in files nobody drafted, which is the'
                  % len(nodraft))
            print('   truncation shape this platform keeps finding.)')

    if not drafts:
        print('')
        print('  NO DRAFTS EXIST YET, so every defect is NO DRAFT and the rate is 0%.')
        print('  That is an honest zero, not a failure of the method. Draft a file:')
        print('     python tools/fmea_draft.py <path> --save')

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
