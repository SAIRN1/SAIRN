"""Do the money figures have the digit distribution real money has?

    python tools/benford_check.py                    # lock, then the repo corpora
    python tools/benford_check.py --fixtures         # the blind lock alone
    python tools/benford_check.py --data export.json # a REAL exported dataset
    python tools/benford_check.py --json
    python tools/benford_check.py --quiet

Exit 0 when nothing is flagged, 1 when a corpus is flagged, 2 when any part of
the run did not happen. NOT WIRED INTO ANY GATE, and not registered: it is a
"look here" instrument, and the section below says why it must stay one.

── WHAT THIS IS AN AUTOMATED VERSION OF ────────────────────────────────────
Guardian Check 0b -- the fabricated KPI -- is the most common real defect this
platform finds, and it is found by hand every time. Its sharpest recorded
instance is StoneDesk's Slabs panel: with the real store empty, `load()` fell
through to an in-file `SEED` constant and rendered EIGHT INVENTED SLABS, then
computed all four KPIs from them -- Total 8 / Available 5 / Allocated 2 /
Inventory Value $4,420, every figure fabricated, while a genuinely real
server-synced slab was excluded from every count.

Check 0b asks "is there a function behind this number". This asks the question
one step over, and it is the only one that works once a function DOES exist:
**do these numbers look like they were measured, or like they were typed?**

── WHY IT CAN ONLY EVER BE A POINTER ───────────────────────────────────────
Benford's law says the leading digit of many naturally-occurring quantities is
distributed log10(1 + 1/d) -- 1 leads 30.1% of the time, 9 only 4.6%. Real
invoice and ledger amounts, spanning several orders of magnitude, tend to
follow it. Hand-invented figures tend not to: people spread their leading
digits far more evenly than reality does.

TENDENCY IS NOT PROOF, IN EITHER DIRECTION. A conforming distribution is not
evidence of honesty; a non-conforming one is not evidence of fabrication. Real
datasets fail this for entirely innocent reasons every day -- a price list, a
tier table, anything with a floor or a ceiling. So the output says LOOK HERE
and names what to look at. It never says fabricated, and nothing gates on it.

── THE SHAPE PRE-CHECK IS MOST OF THIS FILE, AND THAT IS THE POINT ─────────
Applying Benford to a dataset that cannot satisfy it produces a confident false
positive every single time, and a checker that cries wolf is one nobody reads.
Five refusals, each with the measured number printed beside it:

  TOO FEW VALUES      under MIN_N. The expected count for digit 9 is 4.6% of n;
                      below ~100 a single value moves a whole bin.
  TOO NARROW A SPREAD under MIN_DECADES orders of magnitude. Benford emerges
                      from scale invariance; data confined to one decade has no
                      room to express it. A dataset of prices between $10 and
                      $99 has leading digits fixed by the price list, not by
                      any law.
  TOO ROUNDED         a high share of values that are exact multiples of 100 or
                      1000. Rounding concentrates leading digits and is a
                      property of the recording convention, not of the data.
  TOO FEW DISTINCT    a small number of repeated values -- a tier table or a
                      standard rate wearing a large n.
  ASSIGNED, NOT MEASURED   values in a band that looks like ids, years or
                      sequence numbers. Benford does not apply to a counter.

A REFUSAL IS PRINTED, NEVER SILENT. A corpus this skipped is reported as
SKIPPED with its reason and its numbers, because a skip nobody sees reads as a
pass -- PR 1.11 applied to a statistical precondition.

── TWO NUMBERS, NEVER ONE ──────────────────────────────────────────────────
MAD (mean absolute deviation from the expected proportions) is the primary
measure, with Nigrini's published thresholds. CHI-SQUARE IS REPORTED BESIDE IT
AND NEVER ALONE: chi-square's power grows with n, so on a large dataset it
rejects conformity for deviations far too small to mean anything, and quoting
it by itself would manufacture findings out of sample size. Where they
disagree, that disagreement is the useful output.

── WHAT IT CANNOT SEE ──────────────────────────────────────────────────────
  * THE REAL TABLES. ledger_entries, ledger_lines, sd_invoices and the quote
    amounts live in the database, and nothing in this repo can read it. Pass an
    export with --data. WITHOUT ONE, THE PRODUCTION QUESTION IS REPORTED AS
    COULD-NOT-RUN, never as clean.
  * fabrication that happens to be Benford-shaped, which is easy to produce on
    purpose once you know the test exists;
  * whether a flagged corpus is wrong. It says the distribution is unusual. A
    person decides what that means.
"""
import argparse
import io
import json
import math
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish, strip_comments   # noqa: E402

# ── the shape bars ───────────────────────────────────────────────────────────
MIN_N = 100
MIN_DECADES = 2.0
MAX_ROUND_SHARE = 0.50       # share that are exact multiples of 100
MIN_DISTINCT_SHARE = 0.30    # distinct values / n
ID_BAND = (1900, 2100)       # years; a whole corpus inside this is a counter

# Nigrini's conformity bands for the mean absolute deviation.
FIRST_MAD = ((0.006, 'close conformity'), (0.012, 'acceptable'),
             (0.015, 'marginal'), (float('inf'), 'NONCONFORMITY'))
SECOND_MAD = ((0.008, 'close conformity'), (0.010, 'acceptable'),
              (0.012, 'marginal'), (float('inf'), 'NONCONFORMITY'))

FIRST_EXPECTED = {d: math.log10(1 + 1.0 / d) for d in range(1, 10)}
SECOND_EXPECTED = {
    d: sum(math.log10(1 + 1.0 / (10 * k + d)) for k in range(1, 10))
    for d in range(0, 10)
}

# Fields whose values are MONEY OR QUANTITY, named rather than inferred. A
# regex that took every number in the file would sweep up ids, coordinates,
# colours, timeouts and pixel sizes -- none of which Benford applies to, and
# every one of which would widen the apparent spread and make the result look
# more trustworthy than it is.
MONEY_FIELDS = ('amt', 'amount', 'total', 'subtotal', 'price', 'cost', 'value',
                'paid', 'balance', 'debit', 'credit', 'revenue', 'wage',
                'salary', 'ytd', 'sqft', 'qty')
FIELD_RE = re.compile(r'\b(' + '|'.join(MONEY_FIELDS) + r')\s*:\s*(-?\d+(?:\.\d+)?)',
                      re.I)


def band(mad, table):
    for limit, label in table:
        if mad < limit:
            return label
    return 'NONCONFORMITY'


def digits(values, which):
    """Counter of leading (which=1) or second (which=2) digits."""
    out = {}
    for v in values:
        s = ('%.10f' % abs(v)).replace('.', '').lstrip('0')
        if not s:
            continue
        if which == 1:
            d = int(s[0])
            if d == 0:
                continue
        else:
            if len(s) < 2:
                continue
            d = int(s[1])
        out[d] = out.get(d, 0) + 1
    return out


def analyse(values, which):
    exp = FIRST_EXPECTED if which == 1 else SECOND_EXPECTED
    obs = digits(values, which)
    n = sum(obs.values())
    if not n:
        return None
    mad = sum(abs(obs.get(d, 0) / float(n) - p) for d, p in exp.items()) / len(exp)
    chi = 0.0
    for d, p in exp.items():
        e = p * n
        if e > 0:
            chi += (obs.get(d, 0) - e) ** 2 / e
    return {'n': n, 'observed': obs, 'mad': mad,
            'band': band(mad, FIRST_MAD if which == 1 else SECOND_MAD),
            'chi2': chi, 'df': len(exp) - 1}


def shape_refusal(values):
    """(reason, detail) if this corpus cannot support the test, else None."""
    pos = [v for v in values if v > 0]
    n = len(pos)
    if n < MIN_N:
        return ('TOO FEW VALUES', '%d values, bar is %d' % (n, MIN_N))
    lo, hi = min(pos), max(pos)
    decades = math.log10(hi / lo) if lo > 0 else 0.0
    if decades < MIN_DECADES:
        return ('TOO NARROW A SPREAD',
                '%.1f orders of magnitude (%g to %g), bar is %.1f'
                % (decades, lo, hi, MIN_DECADES))
    rounded = sum(1 for v in pos if v == int(v) and int(v) % 100 == 0)
    if rounded / float(n) > MAX_ROUND_SHARE:
        return ('TOO ROUNDED',
                '%d of %d values are exact multiples of 100 (%.0f%%), bar is %.0f%%'
                % (rounded, n, 100.0 * rounded / n, 100 * MAX_ROUND_SHARE))
    distinct = len(set(pos))
    if distinct / float(n) < MIN_DISTINCT_SHARE:
        return ('TOO FEW DISTINCT VALUES',
                '%d distinct in %d values (%.0f%%), bar is %.0f%%'
                % (distinct, n, 100.0 * distinct / n, 100 * MIN_DISTINCT_SHARE))
    if all(ID_BAND[0] <= v <= ID_BAND[1] and v == int(v) for v in pos):
        return ('ASSIGNED, NOT MEASURED',
                'every value is an integer in %d-%d -- years or a counter' % ID_BAND)
    return None


def report_corpus(name, values, kind):
    """One corpus -> a dict. Never raises; a refusal is a result."""
    row = {'corpus': name, 'kind': kind, 'raw': len(values)}
    refusal = shape_refusal(values)
    if refusal:
        row['skipped'], row['why'] = refusal
        return row
    pos = [v for v in values if v > 0]
    row['first'] = analyse(pos, 1)
    row['second'] = analyse(pos, 2)
    row['flagged'] = (row['first'] and row['first']['band'] == 'NONCONFORMITY')
    # WHERE THE TWO MEASURES DISAGREE, SAY SO. Chi-square at df=8 needs 15.507
    # for p<0.05, and it has n in it; MAD does not. A corpus that trips one and
    # not the other is the most useful row this tool produces, because it is
    # the one a reader would otherwise quote half of. The first real run did
    # exactly that: stonedesk.html came back MAD 0.0260 (nonconformity) with
    # chi2 15.2 -- just UNDER the bar, not significant.
    if row['first']:
        chi_sig = row['first']['chi2'] > 15.507
        mad_sig = row['first']['band'] in ('marginal', 'NONCONFORMITY')
        row['chi_significant'] = chi_sig
        row['agree'] = (chi_sig == mad_sig)
    return row


# ── the repo corpora ─────────────────────────────────────────────────────────
def repo_corpora():
    """Money-ish numeric literals per app file.

    THESE ARE DEMO AND SEED FIGURES, AND THAT IS STATED EVERYWHERE THEY ARE
    REPORTED. A SEED constant is openly invented -- `stonedesk.html` alone
    carries 29 of them -- so a non-conformity here is EXPECTED and is not a
    finding about anybody's books. They are in this tool for one reason: they
    are the only corpus in the repo with real spread, so they are what proves
    the instrument fires on something other than a fixture.
    """
    import subprocess
    out = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO,
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    for f in sorted(x for x in out.split('\n') if x.strip() and '/' not in x):
        try:
            src = strip_comments(io.open(os.path.join(REPO, f), encoding='utf-8',
                                         errors='replace').read())
        except Exception:
            continue
        vals = [float(m.group(2)) for m in FIELD_RE.finditer(src)]
        vals = [v for v in vals if v > 0]
        if vals:
            yield f, vals


# ── the blind lock ───────────────────────────────────────────────────────────
def _benford_sample(n=600):
    """Values that DO follow Benford, built from the law rather than sampled.

    10**u for u uniform on [0, k) is Benford by construction -- scale
    invariance is the property the law comes from. A deterministic sweep of u
    is used rather than a random draw so the lock cannot flicker: this repo
    already has a rule about a checker answering differently on identical
    input.
    """
    return [10 ** (3.0 * i / n) for i in range(n)]


def _typed_sample(n=600):
    """Values a person would type: leading digits spread far too evenly.

    THE FIRST VERSION OF THIS FIXTURE WAS REFUSED BY THE SHAPE PRE-CHECK, and
    the lock caught it on the first run. It emitted four-digit numbers only --
    1,100 to 9,999, barely one order of magnitude -- so TOO NARROW A SPREAD
    fired before the statistic was ever reached, and the lock correctly refused
    to certify a test it had not exercised. The fixture was wrong, not the bar.

    A person inventing amounts across a real range spreads the MAGNITUDE too,
    so the magnitude cycles 2 to 5 digits here while the leading digit cycles
    1..9 in equal measure. That is the signature: enough spread to satisfy every
    precondition, and a flat leading digit where reality is logarithmic.
    """
    out = []
    for i in range(n):
        lead = (i % 9) + 1          # 1..9 in equal measure -- the giveaway
        width = i % 4               # 0..3 more digits, so 2 to 5 in total
        tail = (i * 37) % (10 ** (width + 1))
        out.append(float('%d%0*d' % (lead, width + 1, tail)))
    return out


def blind_lock():
    """Classify the criteria against synthetic data BEFORE any real corpus.

    Without this, a bar set slightly wrong reports a clean fleet forever and
    reads exactly like a clean fleet. Both directions are required: the
    Benford-by-construction sample must PASS and the typed sample must be
    FLAGGED. The typed sample is also run through the shape pre-check first --
    if the pre-check refused it, the lock would be proving nothing about the
    statistic.
    """
    problems, rows = [], []
    good = report_corpus('fixture:benford', _benford_sample(), 'fixture')
    typed = report_corpus('fixture:typed', _typed_sample(), 'fixture')
    rows += [good, typed]
    if good.get('skipped'):
        problems.append('the Benford fixture was refused by the shape pre-check '
                        '(%s) -- the bars are wrong, not the data' % good['skipped'])
    elif good.get('flagged'):
        problems.append('the Benford-by-construction fixture was FLAGGED '
                        '(MAD %.4f) -- the bars reject real data'
                        % good['first']['mad'])
    if typed.get('skipped'):
        problems.append('the typed fixture was refused by the shape pre-check '
                        '(%s) -- the lock proves nothing about the statistic'
                        % typed['skipped'])
    elif not typed.get('flagged'):
        problems.append('the typed fixture was NOT flagged (MAD %.4f) -- the '
                        'test cannot fire' % typed['first']['mad'])
    return (not problems), rows, problems


def load_data(path):
    """(name, values, error). A JSON array of numbers, or of objects+--field."""
    try:
        with io.open(path, encoding='utf-8') as fh:
            doc = json.load(fh)
    except Exception as e:
        return None, None, 'could not read %s (%s): %s' % (path, type(e).__name__, e)
    if isinstance(doc, dict):
        doc = doc.get('values') or doc.get('data') or []
    vals = []
    for x in doc:
        if isinstance(x, (int, float)):
            vals.append(float(x))
        elif isinstance(x, dict):
            for k in MONEY_FIELDS:
                if isinstance(x.get(k), (int, float)):
                    vals.append(float(x[k]))
                    break
    if not vals:
        return None, None, ('%s held no numeric values this understands -- a JSON '
                            'array of numbers, or of objects carrying one of %s'
                            % (path, ', '.join(MONEY_FIELDS[:6]) + ', ...'))
    return os.path.basename(path), vals, None


def line(row):
    if row.get('skipped'):
        return '  SKIPPED  %-26s %-24s %s' % (row['corpus'], row['skipped'], row['why'])
    f, s = row['first'], row['second']
    out = ('  %-8s %-26s n=%-5d first MAD %.4f (%s)  chi2 %.1f/df%d %s'
           % ('LOOK HERE' if row['flagged'] else 'ok', row['corpus'],
              f['n'], f['mad'], f['band'], f['chi2'], f['df'],
              'p<0.05' if row.get('chi_significant') else 'n.s.'))
    if s:
        out += '\n%38s second MAD %.4f (%s)' % ('', s['mad'], s['band'])
    if not row.get('agree', True):
        out += ('\n%38s THE TWO MEASURES DISAGREE -- MAD says %s, chi-square says '
                '%s. That is WEAKER evidence than either alone, not stronger.'
                % ('', f['band'],
                   'significant' if row.get('chi_significant') else 'not significant'))
    return out


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--fixtures', action='store_true')
    ap.add_argument('--data', action='append', default=[],
                    help='a JSON export of REAL amounts; repeatable')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args(argv)

    locked, lock_rows, lock_problems = blind_lock()
    if not args.quiet and not args.json:
        print('BENFORD DIGIT DISTRIBUTION -- a POINTER, never a verdict')
        print('  blind lock: %s' % ('LOCKED' if locked else 'FAILED'))
    if not locked:
        if args.json:
            print(json.dumps({'locked': False, 'problems': lock_problems}, indent=1))
        elif not args.quiet:
            print('\nTHE CRITERIA ARE NOT LOCKED, so nothing real was measured.')
            for p in lock_problems:
                print('  ? %s' % p)
        return EXIT_COULD_NOT_RUN
    if args.fixtures:
        if not args.quiet:
            for r in lock_rows:
                print(line(r))
            print('\nLocked: Benford-by-construction passes, typed data is flagged.')
        return 0

    rows, could_not_run = [], []
    for p in args.data:
        name, vals, err = load_data(p)
        if err:
            could_not_run.append(err)
            continue
        rows.append(report_corpus('data:' + name, vals, 'real'))
    if not args.data:
        # PR 1.11. The production question was not answered, and saying nothing
        # here would let a clean repo run read as a clean set of books.
        could_not_run.append(
            'NO --data EXPORT GIVEN, so the real tables were not examined at all. '
            'ledger_entries, ledger_lines and the StoneDesk invoice and quote '
            'amounts live in the database; nothing in this repo can read them. '
            'The repo corpora below are DEMO AND SEED figures and say nothing '
            'about production.')

    for name, vals in repo_corpora():
        rows.append(report_corpus('seed:' + name, vals, 'seed'))

    flagged = [r for r in rows if r.get('flagged')]
    if args.json:
        print(json.dumps({'locked': True, 'rows': rows,
                          'could_not_run': could_not_run}, indent=1))
        return EXIT_COULD_NOT_RUN if could_not_run else (1 if flagged else 0)

    if not args.quiet:
        print('  expected first digits: ' + '  '.join(
            '%d=%.1f%%' % (d, 100 * p) for d, p in sorted(FIRST_EXPECTED.items())))
        print('')
        for r in rows:
            print(line(r))
        print('')
        print('  SEED CORPORA ARE OPENLY INVENTED and a non-conformity in one is')
        print('  EXPECTED -- stonedesk.html alone carries 29 SEED constants. They')
        print('  are here because they are the only data in this repo with real')
        print('  spread, so they are what proves the instrument fires at all.')
        print('  THE PRODUCTION QUESTION NEEDS --data.')

    return finish(
        ['%s -- first-digit MAD %.4f (%s), chi2 %.1f on %d df, n=%d. '
         'A POINTER: look at where these figures come from.'
         % (r['corpus'], r['first']['mad'], r['first']['band'],
            r['first']['chi2'], r['first']['df'], r['first']['n'])
         for r in flagged],
        could_not_run, quiet=args.quiet,
        clean_line='\n  Nothing flagged. That is not a clean bill of health: a '
                   'conforming distribution is not evidence of honesty.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
