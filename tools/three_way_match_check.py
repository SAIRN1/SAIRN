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


def structure():
    """(findings, could_not_run). The repo half."""
    findings, cnr = [], []
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


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--data', help='JSON export with sd_pos, sd_receiving, sd_ap')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args(argv)

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
