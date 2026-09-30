r"""A ROW MAY NOT SAY "neither money nor a regulated record" OVER A FIELD CALLED `amount`.

    python tools/tier_sentence_gate.py                  # the whole register
    python tools/tier_sentence_gate.py --resource mech_checks
    python tools/tier_sentence_gate.py --coverage        # can this ever block?
    python tools/tier_sentence_gate.py --json
    python tools/tier_sentence_gate.py --selftest

REPORT ONLY, AND THE ANSWER TO "SHOULD IT BLOCK" IS NO -- MEASURED, NOT ASSUMED.
Exit 0 clean, 1 findings, 2 COULD NOT RUN. Writes nothing anywhere.

── WHY, AND IT IS SIX ROWS ─────────────────────────────────────────────────
`docs/CRITICALITY-TIERS.md` states the B rule as *"is neither money nor regulated
-- internal operational data, scheduling, non-financial records"*, and 47 rows
carried that sentence together with *"classified by the stated B rule rather than
individually read"*. Reading them found it FALSE on six rows over four days --
`sd_exec_msgs`, `bld_change_orders`, `bld_warranty`, `bld_inspections`,
`bld_toolbox_talks`, and on 2026-09-30 `mech_checks`, whose `saveCheck()` stores
`{id, num, date, payee, amount, memo}`.

**Every one was found by a human opening the file.** Nothing mechanical objected,
and `criticality_tier_check.py` exits 0 whether a row is A or B -- it checks that
a tier EXISTS and carries evidence, never that the tier is right.

THE ONE LIMB THAT IS DECIDABLE FROM A FIELD NAME IS MONEY, and that is the whole
scope of this check:

> if a row asserts the money clause, and the resource persists a field whose NAME
> is in a small closed money list, the row and the field are reported together.

── WHAT IT DELIBERATELY DOES NOT DO, each for a measured reason ────────────
* **It does not screen the REGULATED limb.** Nothing in a field name distinguishes
  a regulated record. `sv_herdhealth.scc` is SOMATIC CELL COUNT, the milk-quality
  figure a dairy is held to for saleability, and no pattern would know; `sv_staff`'s
  `credential` holds the string `'Current'`, a currency flag and not a licence
  number, so a `credential` pattern would fire on a row where B is correct. Both
  were settled by reading. A regex that guessed at either would produce exactly the
  confident-and-wrong finding this platform keeps paying for.
* **It does not screen the "no PII" clause.** Two of the three rows found false on
  2026-09-29 -- `dnt_vendor_contacts` and `sv_staff` -- failed on PII, not on
  money, and a `name`/`phone`/`email` screen fires on most business-contact rows
  where B is the correct answer on the CLASS. That is a judgement, not a match.
* **IT WOULD HAVE CAUGHT ONE OF THE THREE 2026-09-29 ROWS AND THE ONE THIS WEEK.**
  Stated up front rather than left for a reader to work out: the value is
  `mech_checks`-shaped rows, where a field is literally called `amount` or `payee`.

── AND IT MUST NOT BE MADE A BLOCKING PRE-COMMIT GATE, WHICH IS A MEASUREMENT ──
Run `--coverage`. The write-shape extractor resolves a field list for only some
resources; for the rest there is no shape to screen, and the two ways to treat that
are both wrong for a gate:

  * FAIL OPEN on an unresolved resource -- report a pass it never performed. That
    is PR 1.11 verbatim, inside the gate meant to enforce the register.
  * FAIL CLOSED on an unresolved resource -- refuse most register edits, on a file
    five sessions touch. A gate that blocks the ordinary case gets switched off,
    and then protects nothing.

So the third state is printed per resource and the check stays REPORT-ONLY. The
threshold at which it could block is stated in the output and is not met.
"""
import argparse
import glob
import io
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

CRITERIA_VERSION = '2026-09-30.1'
DOC = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')

# The row shape, identical to criticality_tier_check's so the two cannot disagree
# about what a row is.
ROW = re.compile(r'^\| `([a-z0-9_]+)` \| \*\*([ABC])\*\* \| \*\*([ABC])\*\* \|')

# The money clause, and its near variants as they actually appear.
MONEY_CLAUSE = re.compile(
    r'neither money nor a regulated|neither money nor regulated|'
    r'not money and not a regulated|no money and no regulated|'
    r'neither a payment nor a regulated', re.I)

# A row QUOTING the clause to say it was wrong is doing the opposite of asserting
# it. Same exclusion criticality_tier_check applies to its own access-control arm.
QUOTED = re.compile(
    r'(&ldquo;|&rsquo;|["“‘])[^|]{0,180}?'
    r'neither money nor', re.I)
CORRECTED = re.compile(
    r'RE-TIERED|was B on|it was b on the|the B sentence|old (?:wording|sentence)|'
    r'generic sentence|blanket sentence|still said|used to (?:say|read)', re.I)

# ── THE MONEY FIELD LIST. SMALL AND CLOSED, and the closure IS the criterion.
# Every entry names a sum of money or the party it moved to. `quantity`, `qty`,
# `rate` and `units` are deliberately ABSENT: `leg_keepsakeorders` carries
# `quantity` with no price (the charge is on the invoice) and `sb_hire` carries a
# POSTED RANGE on a job advert, and both are correctly B. A wider list fires on
# those and the check gets switched off.
MONEY_FIELDS = (
    'amount', 'amount_paid', 'amount_received', 'amount_billed', 'payee',
    'price', 'total_price', 'subtotal', 'total_amount', 'balance', 'deposit',
    'deposit_amount', 'charge', 'paid', 'unpaid', 'fee', 'cents', 'tax',
    'invoice_amount', 'lien_amount', 'retainage_held', 'refund',
)
MONEY_RE = re.compile(r'^(?:%s)$' % '|'.join(re.escape(f) for f in MONEY_FIELDS))

APPS = [os.path.basename(p)[:-5] for p in glob.glob(os.path.join(REPO, '*.html'))]


def _src(rel):
    p = os.path.join(REPO, rel)
    if not os.path.isfile(p):
        return None
    return io.open(p, encoding='utf-8', errors='replace').read()


def _obj_keys(s, i, limit=20000):
    """Top-level keys of the object literal whose `{` is at s[i]."""
    depth, keys, j, start = 0, [], i, i
    while j < len(s):
        c = s[j]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                break
        elif depth == 1:
            m = re.match(r"[\s,]*(?:'([A-Za-z_]\w*)'|\"([A-Za-z_]\w*)\"|([A-Za-z_]\w*))\s*:",
                         s[j:j + 60])
            if m and (j == start + 1 or s[j - 1] in ',{' or s[j - 1].isspace()):
                keys.append((m.group(1) or m.group(2) or m.group(3)))
        j += 1
        if j - start > limit:
            break
    return keys


def write_shape(resource):
    """(sorted field names, where) or (None, why-it-could-not-be-told).

    THE EXTRACTION IS BRACE-MATCHED, NOT WINDOWED, and the first version of this
    was windowed: a plus/minus 4000-character window around a resource name
    flagged 62 of 69 rows on 2026-09-29, because SAIRNlegacy's writers sit
    adjacent in one file and every `leg_` row came back with the identical field
    set. A screen that flags 90% of its population has found nothing.
    """
    q = re.escape(resource)
    calls = [
        r"""(?:Data|data)\s*\(\s*['"]write['"]\s*,\s*['"]%s['"]\s*,\s*([A-Za-z_]\w*)""" % q,
        # CASE-INSENSITIVE ON THE HELPER NAME, and the first version was not:
        # the real call is `window.mechPushRecord('mech_checks', entry)` with a
        # CAPITAL P, so a lowercase `push(?:Record|One)` matched nothing and the
        # one row this check was built for came back COULD-NOT-TELL. Caught by
        # the selftest arm below on the first run, which is what it is for.
        r"""[Pp]ush(?:Record|One)\s*\(\s*['"]%s['"]\s*,\s*([A-Za-z_]\w*)""" % q,
        r"""\bst\s*\(\s*['"]%s['"]\s*,\s*([A-Za-z_]\w*)\s*\)""" % q,
    ]
    for app in ['api/sd-data.js'] + ['%s.html' % a for a in APPS]:
        s = _src(app)
        if not s:
            continue
        for pat in calls:
            for m in re.finditer(pat, s):
                var = m.group(1)
                if var in ('list', 'arr', 'rows', 'all'):
                    continue
                seg = s[max(0, m.start() - 9000):m.start()]
                last = None
                for am in re.finditer(r'\b' + re.escape(var) + r'\s*=\s*\{', seg):
                    last = am
                if last:
                    at = max(0, m.start() - 9000) + last.end() - 1
                    ks = _obj_keys(s, at)
                    if ks:
                        return sorted(set(ks)), '%s (var %s)' % (app, var)
        # the seed/save literal-array form
        for m in re.finditer(r"""['"]%s['"]\s*,\s*\[\s*\{""" % q, s):
            i = s.index('{', m.start() + len(resource) + 2)
            ks = _obj_keys(s, i)
            if ks:
                return sorted(set(ks)), '%s (literal array)' % app
    return None, ('no brace-matched write shape found -- the resource may use a '
                  'per-app helper this extractor does not know, may be written '
                  'through a constant alias, or may not be written by the client '
                  'at all')


def scan(doc_text=None):
    text = doc_text if doc_text is not None else _src(os.path.relpath(DOC, REPO))
    if text is None:
        return None
    out = []
    for line in text.split('\n'):
        m = ROW.match(line)
        if not m:
            continue
        res = m.group(1)
        if not MONEY_CLAUSE.search(line):
            continue
        if QUOTED.search(line) or CORRECTED.search(line):
            out.append({'resource': res, 'state': 'QUOTED',
                        'detail': 'the clause appears inside a quotation or beside '
                                  'a correction verb, so the row is not asserting it'})
            continue
        fields, where = write_shape(res)
        if fields is None:
            out.append({'resource': res, 'state': 'COULD-NOT-TELL',
                        'detail': where})
            continue
        hits = [f for f in fields if MONEY_RE.match(f)]
        out.append({'resource': res,
                    'state': 'MONEY-FIELD' if hits else 'CLEAR',
                    'fields': hits or fields[:10], 'where': where,
                    'detail': ('the row says neither money nor a regulated record '
                               'and the resource persists %s'
                               % ', '.join('`%s`' % h for h in hits)) if hits
                              else 'no field name in the closed money list'})
    return out


def selftest():
    """Fixtures first, in both directions, on hand-built rows."""
    bad = 0

    def arm(name, cond, detail=''):
        nonlocal bad
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))
        if not cond:
            bad += 1
            if detail:
                print('       %s' % str(detail)[:300])

    def row(res, ev):
        return '| `%s` | **B** | **B** | consequence | confidentiality | %s |' % (res, ev)

    # THE REAL POSITIVE. mech_checks persists `payee` and `amount`.
    r = scan(row('mech_checks', 'Operational data lost or wrong: neither money nor '
                                'a regulated record.'))
    got = [x for x in r if x['resource'] == 'mech_checks']
    arm('THE ARM THAT MATTERS: a row asserting the clause over `mech_checks`, whose '
        'saveCheck() persists `payee` and `amount`, is reported MONEY-FIELD',
        got and got[0]['state'] == 'MONEY-FIELD'
        and 'amount' in (got[0].get('fields') or []), got)

    # KNOWN-BAD THE OTHER WAY: a row QUOTING the clause to correct it.
    r = scan(row('mech_checks', 'RE-TIERED B -> A. The B sentence read &ldquo;neither '
                                'money nor a regulated record&rdquo; and was false.'))
    got = [x for x in r if x['resource'] == 'mech_checks']
    arm('KNOWN-BAD THE OTHER WAY: a row QUOTING the clause beside a correction verb '
        'is QUOTED, not a finding -- a row saying the sentence was wrong is doing '
        'the opposite of asserting it',
        got and got[0]['state'] == 'QUOTED', got)

    # A resource with no money field must come back CLEAR, not flagged.
    r = scan(row('leg_guestbook', 'neither money nor a regulated record'))
    got = [x for x in r if x['resource'] == 'leg_guestbook']
    arm('KNOWN-BAD THE OTHER WAY: `leg_guestbook` persists {id, memorial_id, name, '
        'message, created_at} and comes back CLEAR, so the check is not simply '
        'reporting every row that carries the sentence',
        got and got[0]['state'] == 'CLEAR', got)

    # A row that does NOT carry the clause is not examined at all.
    r = scan(row('mech_checks', 'Money. Confidentiality individually read.'))
    arm('a row that does not carry the clause is not examined -- the check is about '
        'the SENTENCE, not about the resource', r == [], r)

    # THE THIRD STATE IS REAL AND IS NOT A PASS.
    r = scan(row('zz_no_such_resource', 'neither money nor a regulated record'))
    got = [x for x in r if x['resource'] == 'zz_no_such_resource']
    arm('a resource with NO extractable write shape is COULD-NOT-TELL, never CLEAR '
        '-- fail-open here is PR 1.11 inside the gate meant to enforce the register',
        got and got[0]['state'] == 'COULD-NOT-TELL', got)

    # `quantity` is DELIBERATELY absent from the money list.
    arm('KNOWN-BAD THE OTHER WAY: `quantity` is NOT in the money list, because '
        '`leg_keepsakeorders` carries it with no price and is correctly B',
        not MONEY_RE.match('quantity') and not MONEY_RE.match('rate'),
        [f for f in ('quantity', 'rate') if MONEY_RE.match(f)])
    arm('...and `amount` and `payee` ARE, so the narrowing did not empty the list',
        bool(MONEY_RE.match('amount')) and bool(MONEY_RE.match('payee')))

    # THE EXTRACTOR MUST FIND A camelCase HELPER. The first version of the push
    # pattern was lowercase-only and matched nothing against the real call,
    # `window.mechPushRecord('mech_checks', entry)`. An extractor that silently
    # resolves nothing reports COULD-NOT-TELL, which reads as "nobody could tell"
    # rather than "the regex has a capital letter wrong".
    fields, where = write_shape('mech_checks')
    arm('the extractor resolves a camelCase push helper -- `mechPushRecord`, with '
        'a capital P, which a lowercase-only pattern missed entirely',
        fields is not None and 'payee' in fields and 'amount' in fields,
        (fields, where))
    fields, where = write_shape('zz_definitely_not_a_resource')
    arm('...and it still resolves NOTHING for a name that is not written anywhere, '
        'so the widening did not make every lookup succeed', fields is None, where)

    print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
    return EXIT_CLEAN if not bad else EXIT_FINDING


# The share of asserting rows that must resolve to a write shape before anyone
# may argue this should block. REASONED, NOT CALIBRATED, and said so: below it,
# fail-closed refuses the ordinary case and fail-open reports a pass it never
# performed, so neither direction is available.
BLOCK_THRESHOLD = 0.95


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--resource', default=None)
    ap.add_argument('--coverage', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        print('TIER SENTENCE GATE -- selftest, fixtures before the register')
        return selftest()

    print('TIER SENTENCE GATE -- a row may not assert the money clause over a '
          'field called `amount`')
    print('  criteria : %s' % CRITERIA_VERSION)
    print()
    print('  FIXTURE GATE -- run before the register so a vacuous pass is impossible:')
    if selftest() != EXIT_CLEAN:
        print()
        print('COULD NOT RUN: the fixture arms did not pass, so nothing below would '
              'mean anything.')
        return EXIT_COULD_NOT_RUN
    print()

    rows = scan()
    if rows is None:
        print('COULD NOT RUN: %s is not on disk. An absent register is not a clean '
              'one.' % os.path.relpath(DOC, REPO))
        return EXIT_COULD_NOT_RUN
    if args.resource:
        rows = [r for r in rows if r['resource'] == args.resource]
        if not rows:
            print('COULD NOT RUN: %r either has no row or does not assert the money '
                  'clause. Neither is a pass.' % args.resource)
            return EXIT_COULD_NOT_RUN

    by = {}
    for r in rows:
        by.setdefault(r['state'], []).append(r)
    print('  rows ASSERTING the money clause : %d' % len(rows))
    for st in ('MONEY-FIELD', 'CLEAR', 'COULD-NOT-TELL', 'QUOTED'):
        print('    %-16s %d' % (st, len(by.get(st, []))))
    print()

    findings = by.get('MONEY-FIELD', [])
    if findings:
        print('MONEY-FIELD (%d) -- the row says neither money nor a regulated record, '
              'and the resource persists a field named for money:' % len(findings))
        for r in findings:
            print('  ! %-26s %s' % (r['resource'], ', '.join(r['fields'])))
            print('      shape read from %s' % r['where'])
    else:
        print('MONEY-FIELD (0) -- no asserting row persists a field in the closed '
              'money list.')
        print('  THAT IS NOT "the sentence is true everywhere". The regulated limb '
              'and the "no PII" clause are NOT screened here, and four of the six '
              'rows this check exists for failed on something a field name cannot '
              'see.')
    print()

    cnt = {k: len(v) for k, v in by.items()}
    decidable = cnt.get('MONEY-FIELD', 0) + cnt.get('CLEAR', 0)
    unresolved = cnt.get('COULD-NOT-TELL', 0)
    denom = decidable + unresolved
    cov = (decidable / denom) if denom else 0.0
    print('CAN THIS BLOCK? NO, AND HERE IS THE MEASUREMENT.')
    print('  asserting rows with an extractable write shape : %d of %d  (%.0f%%)'
          % (decidable, denom, cov * 100))
    print('  the threshold at which blocking becomes arguable : %.0f%%'
          % (BLOCK_THRESHOLD * 100))
    print('  %s' % ('MET -- and it is still a decision with an owner, not a side '
                    'effect of coverage rising' if cov >= BLOCK_THRESHOLD
                    else 'NOT MET. Fail-closed would refuse the ordinary edit to a '
                         'file five sessions touch; fail-open would report a pass it '
                         'never performed. Neither direction is available, so this '
                         'stays report-only.'))
    if unresolved:
        print()
        print('COULD-NOT-TELL (%d) -- named, never folded into CLEAR:' % unresolved)
        for r in by['COULD-NOT-TELL'][:12]:
            print('    ? %s' % r['resource'])
        if unresolved > 12:
            print('    ... and %d more' % (unresolved - 12))

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'rows': rows,
                          'coverage': cov, 'block_threshold': BLOCK_THRESHOLD},
                         indent=2))
    return EXIT_FINDING if (findings or unresolved) else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
