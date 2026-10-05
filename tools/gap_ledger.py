#!/usr/bin/env python
# OWNER: cody
"""The competitive-gap ledger -- DERIVED from the audit documents, never kept.

    python tools/gap_ledger.py                  # every app, report-only
    python tools/gap_ledger.py --app sairnlaw   # one app, with its rows
    python tools/gap_ledger.py --fixtures       # the criteria lock, alone
    python tools/gap_ledger.py --json

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY -- a bare run writes
nothing, which is `tools/bare_run_writers.py`'s rule and the reason this tool is
not in that list.

── WHY IT IS DERIVED AND NOT A DOCUMENT ────────────────────────────────────
`docs/2026-09-29-competitive-gap-doc-inventory.md` was written FOR this ledger
and says so in its first line. It is also already carrying an addendum
correcting itself, because one of the ten refs it describes was deleted the
following week. A hand-kept ledger over a moving corpus is the eighth
cross-domain discipline waiting to happen: nothing announces the day a row
stops matching its source.

So the ledger is COMPUTED. Its subject is this repository, which means
`--check` would compare a document to its own generator -- the failure
`docs/MASTER-PLAN.md` records about itself -- so there is no document and no
`--check`. The run IS the ledger.

── WHAT A ROW IS, AND WHERE IT COMES FROM ──────────────────────────────────
Each audit document ends with a `## N. Synthesis` section of NUMBERED items,
each opening with a bolded sentence that states one finding. Those sentences
are the rows. They are LIFTED, not summarised: a ledger that paraphrases a
competitive claim is a second source that can disagree with the first, and the
whole point is to be able to follow the row back.

Every row carries its file and line so it can be checked in one step.

── THREE THINGS EVERY ROW IS SHIPPED WITH, because a gap list without them
── OVERSTATES WHAT IS KNOWN ────────────────────────────────────────────────
  AS-OF      the date in the document's own filename. A competitive fact has
             an expiry and a ledger that prints a gap with no date is asserting
             currency it has not got.
  NON-CLAIMS the count of items in the document's own "What this document does
             not establish or decide" section. Both pilot audits have one; a
             document WITHOUT one is reported as a finding, because an audit
             that names no limits is the one to trust least.
  DECAY      whether the document carries its own staleness statement.

── DEDICATED VERSUS SHARED, AND THE DISTINCTION IS cc's ────────────────────
From the inventory document: DEDICATED means the app's name is in the FILENAME
and no other app's is; SHARED means the filename names several apps and this one
is one line inside a sweep. They are counted apart deliberately -- "a ledger
that scores a line in a five-app sweep the same as a dedicated audit is
overstating its own coverage." That rule is adopted here rather than re-derived.

── AN APP WITH NO DOCUMENT GETS A ROW, EMPTY ───────────────────────────────
Three apps had none when the inventory was written. An app omitted from a
coverage table reads as covered; an app present with zero rows reads as what it
is. The inventory's own instruction was that those rows "open empty".

── WHAT THIS CANNOT SEE, stated rather than discovered later ───────────────
  * A GAP THAT IS NOT IN A SYNTHESIS SECTION. A finding buried in section 3 and
    never carried into the synthesis is invisible here. That is a property of
    the documents, not a bug to be regexed around: the synthesis is the part the
    author decided was a finding.
  * WHETHER A GAP IS REAL, OPEN, CLOSED OR IMPORTANT. There is no status column
    and no priority column, deliberately. Both are human judgements and a
    column this tool filled in would be a fabricated KPI -- the exact shape
    `sairn-guardian-v2`'s Check 0b exists to catch. What the ledger provides is
    the question; the answer has a person's name on it.
  * A DOCUMENT ON A BRANCH. Only the working tree is read. The inventory records
    that nine of fourteen covered apps had their newest audit on a cloud branch
    alone; PR #18 merged on 2026-10-05, so most of those are on main now, and
    the figure below is what the tree holds TODAY rather than what any document
    says it holds.
"""
import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

CONTROLLED_BY = ['tests/run_gap_ledger_probe.py']
CRITERIA_VERSION = '2026-10-05.1'

# Where audits live. Both directories, because the corpus is split: the cloud
# research lane writes to docs/cloud-research/ and earlier audits sit in
# docs/ and docs/superpowers/specs/.
SEARCH_DIRS = ('docs', os.path.join('docs', 'cloud-research'),
               os.path.join('docs', 'superpowers', 'specs'))

# A document is an audit if its NAME says so. Reading every doc for the word
# "competitor" would pull in this file's own siblings and every triage note.
AUDIT_NAME = re.compile(r'competitive[-_]?gap|competitive[-_]research', re.I)

# ── THE SECTION NUMBER IS OPTIONAL, AND THE FIRST RUN PROVED IT ────────────
# These three regexes were written from the TWO PILOT documents, which both
# number every heading, and the first full run over all 22 then reported
# "has no Synthesis section", "names NO LIMITS" and "carries no Decay
# statement" against documents that have all three. sairnbiz's are
# `## Synthesis`, `## What this document does not establish or decide` and
# `## Decay` -- unnumbered, identical in content, invisible to a `\d+\.`
# requirement.
#
# THAT IS A FIXTURE-SAMPLE DEFECT, NOT A LOOSENING. A two-document sample of a
# twenty-two document corpus is what discipline 1 warns about from the other
# direction: the criteria were locked against fixtures, the fixtures were
# correct, and they did not describe the corpus. Had the first run been
# believed it would have published 25 findings against documents that are fine.
#
# `Limits` IS ALSO A LIMITS SECTION. The re-derived audits
# (2026-09-17-sairndental, 2026-09-17-sairnroofing) head it `## 3. Limits`. It
# is the same thing and reporting it as absent was wrong.
SYNTH_HEAD = re.compile(r'^##\s+(?:\d+\.\s*)?Synthesis\b', re.I | re.M)
LIMITS_HEAD = re.compile(
    r'^##\s+(?:\d+\.\s*)?(?:What this document does not\b|Limits\b)',
    re.I | re.M)
DECAY_HEAD = re.compile(r'^##\s+(?:\d+\.\s*)?Decay\b', re.I | re.M)
# A numbered synthesis item. The lead sentence is bolded in both pilots.
ITEM = re.compile(r'^\s*(\d+)\.\s+\*\*(.+?)\*\*', re.M | re.S)
# A numbered item with NO bold lead -- counted separately rather than dropped.
ITEM_PLAIN = re.compile(r'^\s*(\d+)\.\s+(?!\*\*)(\S.*)$', re.M)
DATE_IN_NAME = re.compile(r'(\d{4}-\d{2}-\d{2})')


def app_names():
    """Every app on the platform, from the html files. Never a hand-kept list."""
    out = set()
    for f in sorted(os.listdir(REPO)):
        if f.endswith('.html'):
            out.add(os.path.splitext(f)[0].lower())
    return out


def audit_docs():
    """[(relpath, text)] for every document whose NAME says it is an audit."""
    out = []
    for d in SEARCH_DIRS:
        full = os.path.join(REPO, d)
        if not os.path.isdir(full):
            continue
        for f in sorted(os.listdir(full)):
            if not f.endswith('.md') or not AUDIT_NAME.search(f):
                continue
            p = os.path.join(full, f)
            try:
                txt = io.open(p, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            out.append((os.path.relpath(p, REPO).replace(os.sep, '/'), txt))
    return out


def apps_in_name(name, apps):
    """Which apps a FILENAME names. The dedicated/shared test, cc's rule.

    LONGEST FIRST, and that is not tidiness: `stonedesk-catalog` contains
    `stonedesk`. Matching short names first would report both for one document
    and file a dedicated audit as a shared sweep.

    ── IT READS FULL APP NAMES ONLY, AND THREE REAL DOCUMENTS ESCAPE IT ──────
    `2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md` names its
    five apps by their `sairn`-STRIPPED names and this matcher sees NONE of
    them. Same for the roofing-dental-senior and senior-mechanical sweeps.
    cc's inventory counts those against five, three and two apps; this tool
    counts them against nobody, and the run PRINTS that disagreement instead of
    letting the shared column read as complete.

    AN ALIAS RULE WAS CONSIDERED AND NOT TAKEN. Stripping `sairn` and matching
    whole filename tokens would attribute all three -- and the aliases it
    produces include `design`, `care`, `code` and `cash`, which are ordinary
    English words that can appear in a filename for an unrelated reason. A
    wrong attribution gives an app a shared sweep it has not got, which is the
    direction that overstates coverage. Three documents named explicitly is a
    smaller and checkable error than a rule that can quietly mis-file any
    future one.
    """
    low = name.lower()
    hit, taken = set(), low
    for a in sorted(apps, key=len, reverse=True):
        if a in taken:
            hit.add(a)
            taken = taken.replace(a, ' ' * len(a))
    return hit


def section(text, head_re, stop_re=re.compile(r'^##\s+', re.M)):
    """The body of the section `head_re` opens, or None if it is absent.

    None and '' ARE DIFFERENT and the caller must not fold them: an absent
    limits section is a finding about the document, and an empty one is a
    different finding about the same document.
    """
    m = head_re.search(text)
    if not m:
        return None
    rest = text[m.end():]
    nxt = stop_re.search(rest)
    return rest[:nxt.start()] if nxt else rest


def rows_for(path, text):
    """One record per synthesis item, plus the document's own limits."""
    synth = section(text, SYNTH_HEAD)
    limits = section(text, LIMITS_HEAD)
    decay = section(text, DECAY_HEAD)
    rows = []
    if synth:
        # the line number of the synthesis heading, so each row can be found
        base = text[:SYNTH_HEAD.search(text).start()].count('\n') + 1
        for m in ITEM.finditer(synth):
            lead = ' '.join(m.group(2).split())
            rows.append({'n': int(m.group(1)),
                         'line': base + synth[:m.start()].count('\n') + 1,
                         'lead': lead})
    plain = len(ITEM_PLAIN.findall(synth)) if synth else 0
    return {
        'doc': path,
        'as_of': (DATE_IN_NAME.search(os.path.basename(path)) or [None])[0]
        if DATE_IN_NAME.search(os.path.basename(path)) else None,
        'rows': rows,
        'unbolded_items': plain,
        'has_synthesis': synth is not None,
        'limits_items': None if limits is None
        else len(ITEM_PLAIN.findall(limits)) + len(ITEM.findall(limits)),
        'has_decay': decay is not None,
    }


def ledger():
    """{app: {'dedicated': [rec], 'shared': [path], ...}} or None if no corpus."""
    apps = app_names()
    if not apps:
        return None
    docs = audit_docs()
    if not docs:
        # PR 1.11: an empty corpus is not an empty ledger. Every app would read
        # as uncovered and the output would be a confident wrong answer about
        # the whole platform.
        return None
    out = {a: {'dedicated': [], 'shared': []} for a in sorted(apps)}
    for path, text in docs:
        named = apps_in_name(os.path.basename(path), apps)
        if not named:
            # A platform-wide audit, or a short-name sweep this matcher cannot
            # attribute. Recorded against nobody rather than against everybody
            # -- and surfaced by name in the run, see UNATTRIBUTABLE_BY_NAME.
            out.setdefault('_unattributed', []).append(path)
            continue
        if len(named) == 1:
            a = next(iter(named))
            out[a]['dedicated'].append(rows_for(path, text))
        else:
            for a in named:
                out[a]['shared'].append(path)
    return out


# ── THE CRITERIA LOCK ──────────────────────────────────────────────────────
# Hand-built documents, not samples of the real ones: a fixture cut from
# docs/cloud-research/ moves whenever the cloud lane pushes, and the lock would
# then move without anybody deciding (discipline 1).
FIXTURES = [
    ('a dedicated audit with two bolded synthesis items', 'x.md', """
# Fixture audit

## 1. Competitors
prose

## 5. Synthesis -- what changed

1. **The first gap is real and quantified.** Supporting prose that should not
   become part of the row.
2. **The second gap is narrow.** More prose.

## 6. What this document does not establish or decide

1. Whether any of it is current.
2. Whether the pricing holds.

## 7. Decay
Every source is a snapshot.
""", {'rows': 2, 'limits_items': 2, 'has_decay': True, 'unbolded': 0}),

    ('an audit with NO limits section is a finding, not a clean row',
     'y.md', """
# Fixture audit

## 5. Synthesis

1. **One gap.** prose
""", {'rows': 1, 'limits_items': None, 'has_decay': False, 'unbolded': 0}),

    ('an UNBOLDED synthesis item is counted, never silently dropped',
     'z.md', """
# Fixture audit

## 5. Synthesis

1. **A bolded one.** prose
2. An unbolded one that this tool cannot turn into a row.
""", {'rows': 1, 'limits_items': None, 'has_decay': False, 'unbolded': 1}),

    ('a document with no synthesis at all yields no rows and says so',
     'w.md', """
# Fixture audit

## 1. Competitors
prose only
""", {'rows': 0, 'limits_items': None, 'has_decay': False, 'unbolded': 0}),

    # ── THE HEADING VARIANTS THE FIRST FULL RUN FOUND, ADDED AFTER IT ───────
    # Both pilots number every heading, so the first criteria set required a
    # number and reported 25 false findings against documents that are fine.
    # These two arms are the corpus answering back.
    ('UNNUMBERED headings are the same sections -- sairnbiz writes all three '
     'this way', 'v.md', """
# Fixture audit

## Synthesis

1. **A gap.** prose

## What this document does not establish or decide

1. Whether it is current.

## Decay
A snapshot.
""", {'rows': 1, 'limits_items': 1, 'has_decay': True, 'unbolded': 0}),

    ('`## N. Limits` IS a limits section -- the re-derived audits head it that '
     'way', 'u.md', """
# Fixture audit

## 2. Synthesis

1. **A gap.** prose

## 3. Limits

1. One limit.
2. Another.
""", {'rows': 1, 'limits_items': 2, 'has_decay': False, 'unbolded': 0}),
]

NAME_FIXTURES = [
    # (filename, apps it should name) -- the dedicated/shared test
    ('sairnlaw-external-competitive-gap-audit-2026-09-26.md', {'sairnlaw'}),
    ('sairncode-external-competitive-gap-audit-2026-09-26.md', {'sairncode'}),
    # THE LONGEST-FIRST RULE, driven rather than described: sairndental
    # contains the letters of no other app, but stonedesk-catalog contains
    # stonedesk, and a short-first matcher would report both.
    ('stonedesk-catalog-competitive-gap-audit.md',
     {'stonedesk-catalog'}),
    # ── MY FIRST EXPECTATION HERE WAS WRONG AND THE FIXTURE RECORDS IT ──────
    # I wrote this arm expecting all five apps and the matcher returned NONE.
    # The matcher is right: the real document names its apps by their
    # `sairn`-STRIPPED names -- build, vet, biz, grounds, cash -- and this
    # matcher reads FULL app names out of a filename, by design. So the
    # expectation is the empty set, and the consequence is disclosed in
    # apps_in_name() and in the run's own output rather than fixed by
    # loosening the rule.
    ('2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md', set()),
]

# ── TWO RULES THE LOCK DID NOT REACH, ADDED BY ITS OWN CONTROL ─────────────
# tests/run_gap_ledger_probe.py neutralises each criteria rule one at a time
# and requires --fixtures to go red. On its first run DATE_IN_NAME and
# AUDIT_NAME stayed GREEN under ablation: nothing in the lock asked what the
# as-of date was, and nothing asked which documents count as audits at all --
# which is the rule that decides the whole corpus. Both directions each,
# because "it finds a date" is satisfied by a rule that returns a date for
# everything, and "it finds audits" by one that admits every document.
DATE_FIXTURES = [
    ('sairnlaw-external-competitive-gap-audit-2026-09-26.md', '2026-09-26'),
    ('competitive-gap-audit-sairncode.md', None),
]
AUDIT_NAME_FIXTURES = [
    ('sairnlaw-external-competitive-gap-audit-2026-09-26.md', True),
    ('2026-08-27-sairnmechanical-shared-platform-competitive-research.md', True),
    # NOT audits, and each is a real filename from docs/ -- an audit matcher
    # that admitted these would pull triage notes and probes into the corpus.
    ('2026-09-29-sairnbiz-preview-check.md', False),
    ('2026-10-05-cody-queue13-report.md', False),
]

# THE THREE DOCUMENTS THIS MATCHER CANNOT ATTRIBUTE, by name, measured rather
# than guessed at. Every one is a multi-app sweep that uses short names, so it
# is counted against NOBODY here while cc's inventory counts it against five,
# three and two apps respectively. The gap is printed on every run.
UNATTRIBUTABLE_BY_NAME = (
    '2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md',
    '2026-08-26-competitive-gap-audit-roofing-dental-senior.md',
    '2026-09-17-senior-mechanical-competitive-gap-rederived.md',
)


def run_fixtures(verbose=True):
    bad = []
    for label, name, text, want in FIXTURES:
        got = rows_for(name, text)
        checks = [
            (len(got['rows']), want['rows'], 'row count'),
            (got['limits_items'], want['limits_items'], 'limits items'),
            (got['has_decay'], want['has_decay'], 'decay present'),
            (got['unbolded_items'], want['unbolded'], 'unbolded items'),
        ]
        for g, w, what in checks:
            if g != w:
                bad.append((label, what, w, g))
        if verbose:
            mark = 'ok  ' if all(g == w for g, w, _ in checks) else 'FAIL'
            print('  %s %s' % (mark, label))
    # the lead sentence must be the SENTENCE, not the whole item
    one = rows_for('x.md', FIXTURES[0][2])['rows'][0]['lead']
    if 'Supporting prose' in one:
        bad.append(('the row LEAD is the bolded sentence only', 'lead',
                    'no trailing prose', one[:80]))
    elif verbose:
        print('  ok   the row lead is the bolded sentence, not the whole item')

    # ── THE LOCK SUPPLIES ITS OWN APP SET, AND IT USED TO BORROW THE REPO'S ──
    # This read `app_names() | {'stonedesk-catalog'}`, so the criteria lock
    # depended on which *.html files happen to be in the tree. Caught by
    # tests/run_gap_ledger_probe.py on its first run: in a sandbox holding one
    # app the lock went RED with "wanted ['sairnlaw'], got []" -- a criteria
    # failure that was really a corpus difference, which is the first
    # cross-domain discipline exactly backwards. A hand-built set makes the
    # lock blind, portable, and about the matcher rather than about the tree.
    apps = {'sairnlaw', 'sairncode', 'sairnbiz', 'sairnbuild', 'sairncash',
            'sairngrounds', 'sairnvet', 'stonedesk', 'stonedesk-catalog'}
    for name, want in NAME_FIXTURES:
        got = apps_in_name(name, apps)
        ok = got == want
        if not ok:
            bad.append(('filename -> apps: %s' % name, 'apps', sorted(want),
                        sorted(got)))
        if verbose:
            print('  %s filename names %s'
                  % ('ok  ' if ok else 'FAIL',
                     ', '.join(sorted(want)) or '(nobody -- short-name sweep)'))

    for name, want in DATE_FIXTURES:
        got = rows_for(name, '# x\n')['as_of']
        ok = got == want
        if not ok:
            bad.append(('filename -> as-of: %s' % name, 'as_of', want, got))
        if verbose:
            print('  %s as-of %-12s from %s'
                  % ('ok  ' if ok else 'FAIL', want or '(none)', name[:52]))

    for name, want in AUDIT_NAME_FIXTURES:
        got = bool(AUDIT_NAME.search(name))
        ok = got == want
        if not ok:
            bad.append(('is it an audit: %s' % name, 'audit', want, got))
        if verbose:
            print('  %s %-9s is%s an audit document'
                  % ('ok  ' if ok else 'FAIL', '', '' if want else ' NOT'))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--app')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fixtures', action='store_true')
    args = ap.parse_args(argv)

    # THE LOCK RUNS ON EVERY INVOCATION, not only under --fixtures. A criteria
    # failure makes every number below meaningless, so it is a refusal rather
    # than a flag somebody has to remember to pass.
    print('GAP LEDGER -- derived, report only (criteria %s)' % CRITERIA_VERSION)
    bad = run_fixtures(verbose=args.fixtures)
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING WAS READ.')
        for row in bad:
            print('     %s -- %s: wanted %r, got %r' % row)
        return 2
    print('  criteria lock: %d document + %d filename + %d as-of + %d '
          'is-it-an-audit fixtures,'
          % (len(FIXTURES), len(NAME_FIXTURES), len(DATE_FIXTURES),
             len(AUDIT_NAME_FIXTURES)))
    print('                 hand-built and REPO-INDEPENDENT. One per criteria '
          'rule: the control')
    print('                 neutralises each rule in turn and requires this '
          'lock to go red.')
    if args.fixtures:
        return 0

    led = ledger()
    if led is None:
        print('COULD NOT RUN: no app files or no audit documents were found, '
              'and an empty\ncorpus is not an empty ledger -- every app would '
              'read as uncovered.\nExit 2, not a pass.')
        return 2

    if args.app:
        if args.app not in led:
            print('No such app %r. Known: %s'
                  % (args.app, ', '.join(sorted(led))))
            return 2
        led = {args.app: led[args.app]}

    if args.json:
        print(json.dumps(led, indent=1, sort_keys=True))
        return 0

    unattributed = led.pop('_unattributed', [])
    findings = []
    total_rows = 0
    print('')
    # LIMITS IS PRESENCE, NOT A COUNT, and the count was the wrong column.
    # Both pilots write their limits section as PROSE PARAGRAPHS, not as a
    # numbered list, so the item count is 0 for a section that is there -- and
    # a column reading 0 for every app looks exactly like "nobody states their
    # limits", which is the opposite of the truth. Presence is the question the
    # finding below actually asks.
    print('%-21s %-9s %-6s %-5s %-7s %s'
          % ('app', 'dedicated', 'shared', 'rows', 'limits', 'newest as-of'))
    for a in sorted(led):
        d = led[a]
        rows = sum(len(r['rows']) for r in d['dedicated'])
        total_rows += rows
        dates = [r['as_of'] for r in d['dedicated'] if r['as_of']]
        newest = max(dates) if dates else '--'
        withlim = sum(1 for r in d['dedicated'] if r['limits_items'] is not None)
        lim = ('%d/%d' % (withlim, len(d['dedicated']))) if d['dedicated'] \
            else '--'
        print('%-21s %-9d %-6d %-5d %-7s %s'
              % (a, len(d['dedicated']), len(d['shared']), rows, lim, newest))
        if not d['dedicated'] and not d['shared']:
            findings.append('%s has NO competitive-gap document of any kind, '
                            'dedicated or shared -- the row is open and empty'
                            % a)
        for r in d['dedicated']:
            if not r['has_synthesis']:
                findings.append('%s: %s has no Synthesis section, so it '
                                'yields no rows' % (a, r['doc']))
            if r['limits_items'] is None:
                findings.append('%s: %s names NO LIMITS -- an audit that '
                                'states what it does not establish is the one '
                                'to trust; one that does not is not clean'
                                % (a, r['doc']))
            if not r['has_decay']:
                findings.append('%s: %s carries no Decay statement, so every '
                                'competitive fact in it reads as current'
                                % (a, r['doc']))
            if r['unbolded_items']:
                findings.append('%s: %s has %d numbered synthesis item(s) with '
                                'no bolded lead, which yield no row'
                                % (a, r['doc'], r['unbolded_items']))

    if args.app:
        for a in sorted(led):
            for r in led[a]['dedicated']:
                print('\n%s  (as of %s, %s limits, decay %s)'
                      % (r['doc'], r['as_of'], r['limits_items'],
                         'yes' if r['has_decay'] else 'NO'))
                for row in r['rows']:
                    print('  %d. %s:%d' % (row['n'], r['doc'], row['line']))
                    print('     %s' % row['lead'][:150])
            for s in led[a]['shared']:
                print('\nSHARED SWEEP (one line inside a multi-app document, '
                      'counted apart): %s' % s)

    if unattributed:
        print('\nATTRIBUTED TO NOBODY -- %d document(s) whose filename this '
              'matcher cannot\nresolve to an app, so the SHARED column above '
              'is INCOMPLETE by exactly these:' % len(unattributed))
        for p in unattributed:
            short = os.path.basename(p) in UNATTRIBUTABLE_BY_NAME
            print('  ? %s%s' % (p, '   <- a short-name multi-app sweep'
                                if short else ''))
        findings.append('%d audit document(s) are attributed to no app, so the '
                        'shared-sweep coverage printed above is a FLOOR. '
                        'apps_in_name() reads full app names out of a filename '
                        'and three real sweeps use sairn-stripped short names.'
                        % len(unattributed))

    print('\nrows: %d across %d app(s)' % (total_rows, len(led)))
    print('NO STATUS COLUMN AND NO PRIORITY COLUMN, deliberately -- whether a '
          'gap is\nopen, closed or important is a human judgement, and a column '
          'this tool filled\nin would be a fabricated figure.')
    if findings:
        print('\n%d FINDING(S):' % len(findings))
        for f in findings:
            print('  - %s' % f)
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
