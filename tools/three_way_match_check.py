"""Can a purchase order, a goods receipt and a vendor bill be matched at all?

    python tools/three_way_match_check.py
    python tools/three_way_match_check.py --data export.json
    python tools/three_way_match_check.py --json
    python tools/three_way_match_check.py --quiet

Exit 0 clean, 1 on a finding, 2 when part of the run did not happen.
REPORT ONLY. It never refuses a payment and nothing gates on it.

── WHY THIS EXISTS, AND WHAT THE AUDIT FOUND ───────────────────────────────
A three-way match is the control that a payable is not settled until three
independently-produced documents agree: the PURCHASE ORDER (what we agreed to
buy), the GOODS RECEIPT (what actually arrived) and the VENDOR BILL (what we
are being asked to pay). Any one alone is a claim by a single party.

docs/2026-09-14-three-way-match-audit.md measured both apps. StoneDesk shipped
ALL THREE LEGS -- `sd_pos`, `sd_receiving`, `sd_ap` -- and NOT ONE FIELD joined
any of them to either of the others. Matching meant guessing from two free-text
strings a human typed on different days. **The match was not unenforced; it was
UNCONSTRUCTIBLE.** `po_num` on the receipt and the bill is what changed that,
and this checker is what stops it quietly going away again.

── TWO QUESTIONS, AND THEY ARE NOT THE SAME ────────────────────────────────
  STRUCTURE   can a match be performed at all? Does every writer of a receipt
              and of a bill carry the join key, and is the PO number a real
              sequence rather than a count? Answerable from the repo, so it is
              answered on every run.
  DATA        do the three documents actually agree -- vendor, amount -- for
              the records a shop really holds? Answerable only from an EXPORT,
              because these live in localStorage and in the database. With no
              --data the data question is COULD-NOT-RUN, never clean.

Reporting only the first and calling it a pass would be the exact shape this
platform keeps recording: a structural green read as a business green.

── WHY THE JOIN KEY IS OPTIONAL, AND WHY THAT IS NOT A LOOPHOLE ────────────
Stock arrives against no PO. A utility bill and an equipment lease never have
one. A field that REFUSED those would be filled with something untrue to get
past it, which is worse than an empty one. So `po_num` is optional on the
record and this checker asks a different question: that the writer OFFERS it
and stores what it is given. Whether a particular bill should have had one is a
judgement about that bill, and the --data half reports the unmatched rows so a
person can make it.

── WHAT IT CANNOT SEE ──────────────────────────────────────────────────────
  * whether the receipt was made by someone other than the person who raised
    the PO. Separation of duties is the other half of this control and needs
    per-employee identity on the write, which these two panels do not have;
  * SAIRNbiz, which has no purchase-order or receiving concept at all -- the
    audit records that two of the three documents simply do not exist there;
  * whether an amount difference is wrong. A partial delivery legitimately
    bills under the PO. It reports the difference and names both figures.
"""
import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish, read, strip_comments  # noqa: E402

APP = os.path.join(REPO, 'stonedesk.html')

# (writer signature, what it writes, the key it must carry)
WRITERS = [
    ('window.sdRecvLog=function(){', 'sd_receiving', 'po_num'),
    ('window.sdAPAdd=function(){', 'sd_ap', 'po_num'),
]
PO_GENERATOR = 'window.sdPONextNum=function(rows,year){'


def body(src, sig):
    """Brace-match a function out of the file, skipping strings and comments."""
    start = src.find(sig)
    if start < 0:
        return None
    i, depth, q = src.find('{', start + len(sig) - 1), 0, None
    while i < len(src):
        c, p = src[i], src[i - 1]
        if q:
            if c == q and p != '\\':
                q = None
        elif c in '"\'`':
            q = c
        elif c == '/' and src[i + 1:i + 2] == '/':
            i = src.find('\n', i)
        elif c == '/' and src[i + 1:i + 2] == '*':
            i = src.find('*/', i) + 1
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if not depth:
                return src[start:i + 1]
        i += 1
    return None


def structure(src=None):
    """(findings, could_not_run). The repo half.

    `src` is for the BLIND LOCK and for nothing else. It exists because the
    first version of run_fixtures() REIMPLEMENTED these rules inline instead of
    calling this function -- so the lock validated a copy of the logic and
    could have passed while the real sweep was broken. That is the same
    lock-tests-a-different-code-path defect found in tools/new_checker.py's
    scaffold earlier the same day, committed again one task later, which is the
    argument for the seam rather than for care.
    """
    findings, cnr = [], []
    if src is None:
        try:
            src = read(APP)
        except Exception as e:
            return [], ['stonedesk.html could not be read (%s) -- NOT a pass' % e]

    for sig, store, key in WRITERS:
        b = body(src, sig)
        if b is None:
            # A writer that vanished is a could-not-tell, not a pass: the check
            # it carried is gone and so is the evidence either way.
            cnr.append('%s not found in stonedesk.html -- the writer for %s '
                       'moved or was renamed, so nothing was verified about it'
                       % (sig.split('=')[0], store))
            continue
        code = strip_comments(b)
        if (key + ':') not in code:
            findings.append('%s writes %s without a %s -- a receipt or bill '
                            'written with no join key cannot be matched to its '
                            'purchase order by anything'
                            % (sig.split('=')[0], store, key))

    gen = body(src, PO_GENERATOR)
    if gen is None:
        cnr.append('%s not found -- the PO numbering could not be checked'
                   % PO_GENERATOR.split('=')[0])
    else:
        code = strip_comments(gen)
        # A NUMBER DERIVED FROM A COUNT REUSES ITSELF AFTER A DELETE, and the
        # join key is the thing it is used as. This is the defect that was
        # there: `'PO-2024-0' + (50 + d.length)`.
        # ANY `.length` AT ALL, and that bluntness is deliberate. The first
        # version matched `+ x.length` and `.length` at end of line, and the
        # control probe planted `var next=rows.length+1;` -- which is the
        # defect, and which neither alternative caught. A sequence has no
        # legitimate use for a row count: it comes from the persisted counter
        # and the suffixes already issued. So the rule is that the count does
        # not appear, which is checkable without guessing at the shape of the
        # next mistake.
        if '.length' in code:
            findings.append('the PO number generator reads a LENGTH -- a number '
                            'derived from a row count reuses itself after a '
                            'delete, and that number is the match key')
        if re.search(r"'PO-\d{4}-", code):
            findings.append('the PO number carries a HARDCODED YEAR')
        if 'st(' not in code:
            findings.append('the PO sequence is never persisted, so it cannot '
                            'survive a reload and will reissue numbers')
    return findings, cnr


def match_rows(pos, recs, bills):
    """Group the three document sets by po_num and report what disagrees."""
    by = {}
    for p in pos:
        num = str(p.get('num') or '').strip()
        if num:
            by.setdefault(num, {'po': p, 'recs': [], 'bills': []})
    orphan_recs, orphan_bills = [], []
    for r in recs:
        k = str(r.get('po_num') or '').strip()
        (by[k]['recs'].append(r) if k in by else orphan_recs.append(r))
    for b in bills:
        k = str(b.get('po_num') or '').strip()
        (by[k]['bills'].append(b) if k in by else orphan_bills.append(b))

    rows = []
    for num in sorted(by):
        g = by[num]
        po_amt = float(g['po'].get('amt') or 0)
        rec_amt = sum(float(x.get('val') or 0) for x in g['recs'])
        bill_amt = sum(float(x.get('amt') or 0) for x in g['bills'])
        row = {'po_num': num, 'vendor': g['po'].get('vendor'),
               'po_amount': po_amt, 'received_value': rec_amt,
               'billed_amount': bill_amt,
               'receipts': len(g['recs']), 'bills': len(g['bills'])}
        why = []
        if not g['recs']:
            why.append('NO RECEIPT -- nothing records that this arrived')
        if not g['bills']:
            why.append('no bill yet')
        if g['bills'] and abs(bill_amt - po_amt) > 0.005:
            why.append('BILLED %.2f against a PO of %.2f (difference %.2f)'
                       % (bill_amt, po_amt, bill_amt - po_amt))
        if g['recs'] and g['bills'] and abs(bill_amt - rec_amt) > 0.005:
            why.append('BILLED %.2f against %.2f received' % (bill_amt, rec_amt))
        for x in g['recs'] + g['bills']:
            v = str(x.get('vendor') or '').strip()
            if v and v != str(g['po'].get('vendor') or '').strip():
                why.append('vendor differs: PO says %r, a document says %r'
                           % (g['po'].get('vendor'), v))
                break
        row['why'] = why
        rows.append(row)
    return rows, orphan_recs, orphan_bills


def load_export(path):
    try:
        with io.open(path, encoding='utf-8') as fh:
            doc = json.load(fh)
    except Exception as e:
        return None, 'export unreadable (%s): %s' % (type(e).__name__, e)
    if not isinstance(doc, dict):
        return None, 'export must be an object with sd_pos / sd_receiving / sd_ap'
    missing = [k for k in ('sd_pos', 'sd_receiving', 'sd_ap') if k not in doc]
    if missing:
        # PARTIAL IS NOT EMPTY. Matching two legs and calling it a three-way
        # match is the failure this whole control exists to prevent.
        return None, ('export is missing %s -- a match against two of the three '
                      'documents is not a three-way match and is not reported as '
                      'one' % ', '.join(missing))
    return doc, None


# ── THE BLIND LOCK ─────────────────────────────────────────────────────────
# ADDED 2026-09-14, and it was the named blocker on this tool's promotion.
# Convention 1 wants a check's criteria decided against synthetic fixtures
# BEFORE it judges real data, and this checker had none -- while judging MONEY.
# A purchase order, a receipt and a bill agreeing is a Tier A question, and a
# money checker promoted without a blind lock is the combination this platform
# has least appetite for.
#
# TWO SETS, BECAUSE THE TOOL ASKS TWO QUESTIONS. The structural half reads
# JavaScript out of an app file; the data half does arithmetic over three
# document sets. Locking only one would leave the other tunable against real
# data, which is the thing the convention exists to stop.
#
# NO FIXTURE HERE WAS CHANGED TO MATCH TOOL OUTPUT. Convention 1 requires
# saying which kind of correction was made, and the answer is: one EXPECTED
# VERDICT was corrected while writing them, named at the fixture that carries
# it -- the orphan-receipt case, which I first wrote as a finding and which the
# tool's own documented design says is a REPORTED ROW for a human to judge, not
# a defect. Correcting the fixture's expectation to match the DESIGN is not the
# same as bending it to match the OUTPUT, and the difference is written here so
# a reader can check which happened.
STRUCTURE_FIXTURES = [
    ('a receipt writer with no join key is a finding', [
        ('window.sdRecvLog=function(){ st("sd_receiving",{qty:1}); }', True),
        ('window.sdRecvLog=function(){ st("sd_receiving",{qty:1,po_num:p}); }', False),
    ]),
    ('a PO number derived from a ROW COUNT is a finding -- it reuses itself '
     'after a delete, and that number is the match key', [
         ('window.sdPONextNum=function(rows,year){ var n=rows.length+1; st(k,n); }', True),
         ('window.sdPONextNum=function(rows,year){ var n=lastSuffix()+1; st(k,n); }', False),
     ]),
    ('a HARDCODED YEAR in the PO number is a finding', [
        ("window.sdPONextNum=function(rows,year){ var n='PO-2024-'+s; st(k,n); }", True),
        ("window.sdPONextNum=function(rows,year){ var n='PO-'+year+'-'+s; st(k,n); }", False),
    ]),
    ('a sequence that is never PERSISTED is a finding -- it reissues numbers '
     'after a reload', [
         ('window.sdPONextNum=function(rows,year){ var n=lastSuffix()+1; return n; }', True),
         ('window.sdPONextNum=function(rows,year){ var n=lastSuffix()+1; st(k,n); }', False),
     ]),
    # THE ONE THAT KEEPS THE RULE FROM BEING A GREP FOR A WORD. `.length` in a
    # COMMENT is not the defect, and the tool strips comments before asking --
    # so this fixture fails the moment somebody removes that step.
    ('a `.length` inside a COMMENT is not the defect', [
        ('window.sdPONextNum=function(rows,year){ /* not rows.length */ '
         'var n=lastSuffix()+1; st(k,n); }', False),
    ]),
]

# (label, pos, recs, bills, must_flag_po_nums)
DATA_FIXTURES = [
    ('three documents that agree produce NO why',
     [{'num': 'P1', 'vendor': 'Acme', 'amt': 100.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'val': 100.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'amt': 100.0}], False),

    ('a bill ABOVE the purchase order is flagged',
     [{'num': 'P1', 'vendor': 'Acme', 'amt': 100.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'val': 100.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'amt': 130.0}], True),

    ('a bill above what was RECEIVED is flagged even when it matches the PO',
     [{'num': 'P1', 'vendor': 'Acme', 'amt': 100.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'val': 40.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'amt': 100.0}], True),

    ('a VENDOR that differs between documents is flagged',
     [{'num': 'P1', 'vendor': 'Acme', 'amt': 100.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'val': 100.0}],
     [{'po_num': 'P1', 'vendor': 'Not Acme', 'amt': 100.0}], True),

    ('a bill with NO receipt behind it is flagged',
     [{'num': 'P1', 'vendor': 'Acme', 'amt': 100.0}],
     [],
     [{'po_num': 'P1', 'vendor': 'Acme', 'amt': 100.0}], True),

    # THE EXPECTED VERDICT THAT WAS CORRECTED, and which kind it was. I first
    # wrote this expecting a flag. The tool's stated design is that a PO with
    # no bill yet is an ordinary open order -- 'no bill yet' is recorded as a
    # row for a reader, in lower case, deliberately distinct from the shouted
    # 'NO RECEIPT'. A checker that flagged every open purchase order would be
    # switched off in a day. Corrected to match the DESIGN, not the output.
    ('a PO with no bill YET is an open order, not a defect',
     [{'num': 'P1', 'vendor': 'Acme', 'amt': 100.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'val': 100.0}],
     [], 'open'),

    # FLOATING POINT, because this is money. The tolerance is 0.005 and a
    # penny-level difference must still be caught; 0.1+0.2 must not be.
    ('a ONE PENNY difference is still a mismatch',
     [{'num': 'P1', 'vendor': 'Acme', 'amt': 100.00}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'val': 100.00}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'amt': 100.01}], True),

    ('...and float noise inside the tolerance is NOT a mismatch',
     [{'num': 'P1', 'vendor': 'Acme', 'amt': 0.1 + 0.2}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'val': 0.3}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'amt': 0.3}], False),

    ('SPLIT receipts and bills are SUMMED, not compared one at a time',
     [{'num': 'P1', 'vendor': 'Acme', 'amt': 100.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'val': 60.0},
      {'po_num': 'P1', 'vendor': 'Acme', 'val': 40.0}],
     [{'po_num': 'P1', 'vendor': 'Acme', 'amt': 70.0},
      {'po_num': 'P1', 'vendor': 'Acme', 'amt': 30.0}], False),
]


def run_fixtures(verbose=False):
    """Every criterion judged on hand-built input, before a real file is read."""
    wrong = []

    for label, cases in STRUCTURE_FIXTURES:
        for src, must_flag in cases:
            # DRIVES THE REAL FUNCTION, not a copy of its rules. A fixture
            # names only ONE of the three writers, so the other two come back
            # as could-not-run -- which is correct and is why cnr is ignored
            # here: the question is whether THIS construct is flagged.
            got_findings, _cnr = structure(src=src)
            got = bool(got_findings)
            if got != must_flag:
                wrong.append('%s -- %r expected %s, got %s'
                             % (label, src[:60], 'FLAG' if must_flag else 'SILENT',
                                'FLAG' if got else 'SILENT'))
            elif verbose:
                print('  ok   %s [%s]' % (label, 'flag' if must_flag else 'silent'))

    for label, pos, recs, bills, want in DATA_FIXTURES:
        rows, orphan_recs, orphan_bills = match_rows(pos, recs, bills)
        why = [w for r in rows for w in r['why']]
        if want == 'open':
            # An open order: recorded, in the lower-case form, and NOT shouted.
            ok = any('no bill yet' in w for w in why) and not any(
                w.startswith('NO RECEIPT') or w.startswith('BILLED') for w in why)
            detail = 'why=%s' % why
        else:
            hard = [w for w in why if w.startswith('NO RECEIPT')
                    or w.startswith('BILLED') or w.startswith('vendor differs')]
            ok = bool(hard) == bool(want)
            detail = 'why=%s' % why
        if not ok:
            wrong.append('%s -- %s' % (label, detail))
        elif verbose:
            print('  ok   %s' % label)

    return wrong


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--data', help='JSON export with sd_pos, sd_receiving, sd_ap')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--fixtures', action='store_true',
                    help='run the blind lock alone and judge no real file')
    args = ap.parse_args(argv)

    # ── THE LOCK RUNS FIRST, AND A FAILURE MEANS NOTHING REAL WAS JUDGED ───
    wrong = run_fixtures(verbose=args.fixtures)
    if wrong:
        print('REFUSING: the criteria do not classify their own fixtures.')
        for w in wrong:
            print('  x %s' % w)
        print('')
        print('NOTHING REAL WAS JUDGED. This checker answers a MONEY question, '
              'so a criterion that')
        print('cannot classify a hand-built purchase order has no business '
              'reading a real one.')
        print('Fix the criteria, or fix a fixture whose expected verdict was '
              'itself wrong -- and say')
        print('in this file which one you did.')
        return EXIT_COULD_NOT_RUN
    # NOT ON STDOUT UNDER --json, AND THE PROBE CAUGHT THIS IMMEDIATELY.
    # The first version printed the banner unconditionally, so `--json` emitted
    # a human line ahead of the document and tests/run_three_way_match_probe.py
    # died on `Expecting value: line 1 column 1`. A tool whose
    # machine-readable output is preceded by prose is a tool nothing can wire
    # up -- exactly the defect I reported in the push gate's check 10 earlier
    # today, reproduced in my own file within the hour. The refusal above still
    # prints on stdout on purpose: at that point there IS no JSON document to
    # corrupt, and a silent refusal would be worse.
    if not args.quiet and not args.json:
        print('BLIND LOCK: %d structural + %d data fixture(s) correct, judged '
              'before any real file was read.'
              % (sum(len(c) for _l, c in STRUCTURE_FIXTURES), len(DATA_FIXTURES)))
    if args.fixtures:
        return 0

    findings, cnr = structure()
    rows, orphan_recs, orphan_bills = [], [], []

    if args.data:
        doc, err = load_export(args.data)
        if err:
            cnr.append(err)
        else:
            rows, orphan_recs, orphan_bills = match_rows(
                doc['sd_pos'], doc['sd_receiving'], doc['sd_ap'])
            for r in rows:
                for w in r['why']:
                    if w.startswith('NO RECEIPT') or w.startswith('BILLED') \
                            or w.startswith('vendor differs'):
                        findings.append('%s (%s): %s' % (r['po_num'], r['vendor'], w))
            for b in orphan_bills:
                if str(b.get('po_num') or '').strip():
                    findings.append('a bill names %r, which matches no purchase '
                                    'order' % b.get('po_num'))
    else:
        cnr.append('NO --data EXPORT GIVEN, so no purchase order, receipt or bill '
                   'was compared to any other. sd_pos, sd_receiving and sd_ap live '
                   'in the browser; only the STRUCTURAL half ran.')

    if args.json:
        print(json.dumps({'structure_findings': findings, 'rows': rows,
                          'orphan_receipts': len(orphan_recs),
                          'orphan_bills': len(orphan_bills),
                          'could_not_run': cnr}, indent=1))
        return EXIT_COULD_NOT_RUN if cnr else (1 if findings else 0)

    if not args.quiet:
        print('THREE-WAY MATCH -- report only, it never refuses a payment')
        print('  structure: can a match be performed at all?')
        print('    writers checked : %d  (%s)'
              % (len(WRITERS), ', '.join(w[1] for w in WRITERS)))
        print('    PO numbering    : %s' % PO_GENERATOR.split('=')[0])
        if rows:
            print('')
            print('  data: %d purchase order(s) compared' % len(rows))
            for r in rows:
                mark = '  !!' if r['why'] else '  ok'
                print('%s %-16s %-22s PO %10.2f  received %10.2f  billed %10.2f'
                      % (mark, r['po_num'], str(r['vendor'])[:22], r['po_amount'],
                         r['received_value'], r['billed_amount']))
                for w in r['why']:
                    print('       %s' % w)
            print('    receipts naming no PO : %d' % len(orphan_recs))
            print('    bills naming no PO    : %d' % len(orphan_bills))
            print('    (both are NORMAL -- stock arrives unordered and a utility '
                  'bill has no PO. They are counted, not flagged.)')

    return finish(findings, cnr, quiet=args.quiet,
                  clean_line='\n  The join exists and every writer carries it. '
                             'That is a statement about the CODE; whether any '
                             'particular bill should have been matched is a '
                             'judgement about that bill.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
