"""cleanup_confirm_check.py -- a cleanup file must be able to answer "did it run?"

    python tools/cleanup_confirm_check.py            # every cleanup/migration file
    python tools/cleanup_confirm_check.py sql/x.sql  # one file

── THE RULE THIS ENFORCES ALREADY EXISTS ───────────────────────────────────
`CLAUDE.md`, Verification Discipline:

    Every cleanup or migration file ends with a per-statement confirm query,
    with the expected answer written next to it --
    `select count(*) from public.x where id = 'Y';  -- expect 0`.
    One per statement, not one for the file: a single count at the end cannot
    tell a full apply from a partial one.

It was written after two real failures on 2026-08-26 -- a multi-statement paste
in the Supabase editor that applied only partway and reported success, and a
table that was created and reported provisioned while every signup 502'd. **The
SQL editor returns success for the statements it did run**, so a partial apply
is indistinguishable from a full one from the outside.

── WHY A CHECKER, AND WHAT IT CANNOT DO ────────────────────────────────────
The open-work row on this says every cleanup file carries a **NOT RUN** label,
and that "the label is a claim about the file, not about the database" -- it had
already gone stale for at least six files, whose rows were verified GONE from
the live database while the file still said NOT RUN.

**This checker cannot tell you whether a file was run. Nothing in the repo can.**
What it can tell you is whether the file is even CAPABLE of answering the
question: a cleanup that deletes from three tables and carries no confirm query
leaves no way, ever, to find out what happened. That is the half that is fixable
without a database, and it is the half that makes the other half answerable.

── THE MATCHER IS CALIBRATED, NOT GUESSED ──────────────────────────────────
The first version counted `select\\s+count\\s*\\(` and `--\\s*expect` and called
17 of 26 files non-compliant. Hand-reading three of them showed two were FALSE
POSITIVES of exactly the kind this repo keeps recording:

  * `sairnroofing_verify_3b_cleanup.sql` ships one `select count(*)` per table
    and says "Expect 0 here anyway" -- missed because the word sat mid-sentence
    rather than straight after the `--`;
  * `sairnlaw_remove_probe_rule_2026-08-25.sql` has a grouped count and an
    exact expected list -- missed because `select` and `count(*)` are on
    DIFFERENT LINES.

Only `sairndesign_synctest_cleanup.sql` was real: three deletes, no confirm of
any kind. So the matcher below is multi-line, accepts the several real spellings
of an expectation, and **counts a query that lives inside a `--` comment**,
because that is how every compliant file in this repo actually ships one -- they
are instructions to paste, not statements to run.

Every finding this reports has been hand-read once. That is the standard the
nav_panel_check fix set the same day, after its own first real run reported a
working app as entirely unreachable.
"""
import glob
import os
import io
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A destructive statement and the table it names. `update ... set` counts: it
# is how a cleanup un-sets a flag, and it is just as invisible when half-applied.
DESTRUCTIVE = re.compile(
    r'\b(delete\s+from|drop\s+table(?:\s+if\s+exists)?|truncate(?:\s+table)?|update)\s+'
    r'(?:public\.)?([a-z_][a-z0-9_]*)', re.I)

# An expectation, in every spelling these files really use. Deliberately broad:
# a file that states an expected answer in prose has met the intent of the rule,
# and refusing it on wording would be a checker arguing about style.
EXPECT = re.compile(
    r'expect(?:ed|s)?\b|should\s+(?:be|return|show)|must\s+(?:be|return)|'
    r'->\s*\d|returns?\s+(?:0|zero|nothing|no\s+rows)|no\s+rows', re.I)


def verifies(text, table):
    """Is there a query in this file that reads `table` back?

    Multi-line by construction: the compliant files in this repo put `select`
    and `count(*)` on different lines, and put the whole query inside a `--`
    comment because it is meant to be pasted into the SQL editor after the
    destructive half has run.
    """
    for m in re.finditer(r'\bselect\b', text, re.I):
        span = text[m.start():m.start() + 500]
        stop = span.find(';')
        if stop != -1:
            span = span[:stop]
        if re.search(r'\bfrom\s+(?:public\.)?%s\b' % re.escape(table), span, re.I):
            return True
    return False


def commented(text, pos):
    """Is the statement at `pos` inside a `--` comment line?

    A COMMENTED STATEMENT IS AN OFFER, NOT AN ACTION, and conflating the two
    produced a false positive on the very first run.
    `sairnroofing_verify_damage_cleanup_2026-08-26.sql` was flagged for
    `sairnroofing_employee_auth` -- a delete that is commented out under a
    header reading "SEPARATE, AND NOT THIS RUN'S DEBRIS", left for the session
    that created the row. Its two LIVE deletes are both confirmed, with an
    explicit "expect 0 from each of the first two". The file was right and the
    checker was wrong.
    """
    line_start = text.rfind('\n', 0, pos) + 1
    return text[line_start:pos].lstrip().startswith('--')


def api_verified(text):
    """Does this file verify through the live ENDPOINT instead of a re-select?

    `CLAUDE.md` PREFERS this: "Where an API path exists, prefer the live
    endpoint over a re-select -- it proves the APP can see the change, which a
    select as owner does not." `sairncash_waitlist` re-selected fine as owner
    the whole time it was 502ing for every real user. A checker that demanded
    SQL would mark the better practice non-compliant.
    """
    return bool(re.search(r'curl\b[\s\S]{0,600}?(?:sairn\.vercel\.app|/api/)',
                          text, re.I)) and bool(EXPECT.search(text))


def audit(path):
    text = io.open(os.path.join(REPO, path), encoding='utf-8',
                   errors='replace').read()
    live, offered, seen = [], [], set()
    for m in DESTRUCTIVE.finditer(text):
        t = m.group(2).lower()
        # `update` is a common word inside prose; require it to reach a SET.
        if m.group(1).lower().startswith('update'):
            tail = text[m.end():m.end() + 200]
            if not re.search(r'\bset\b', tail, re.I):
                continue
        bucket = offered if commented(text, m.start()) else live
        key = (t, bucket is offered)
        if key in seen:
            continue
        seen.add(key)
        bucket.append(t)
    live = [t for t in live if True]
    offered = [t for t in offered if t not in live]
    if not live and not offered:
        return None                       # nothing destructive: nothing to confirm
    by_api = api_verified(text)
    missing = [] if by_api else [t for t in live if not verifies(text, t)]
    stated = bool(EXPECT.search(text))
    return {'path': path, 'live': live, 'offered': offered, 'missing': missing,
            'expectation_stated': stated, 'api_verified': by_api,
            # A file whose statements are ALL commented is a menu somebody
            # chooses from, not a script. Reported, never a GAP -- the reader
            # is already making a decision at that point.
            'menu_only': not live and bool(offered)}


def files():
    out = []
    for pat in ('sql/*cleanup*.sql', 'sql/*remove_probe*.sql'):
        out += glob.glob(os.path.join(REPO, pat))
    return sorted({os.path.relpath(p, REPO).replace(os.sep, '/') for p in out})


def main(argv):
    targets = [a for a in argv if not a.startswith('-')] or files()
    reports = [r for r in (audit(t) for t in targets) if r]
    bad = [r for r in reports
           if not r['menu_only'] and (r['missing'] or not r['expectation_stated'])]
    menus = [r for r in reports if r['menu_only']]
    for r in reports:
        flag = 'MENU' if r['menu_only'] else ('OK  ' if r not in bad else 'GAP ')
        note = ''
        if r['api_verified']:
            note = '  [verified through the live endpoint]'
        elif not r['expectation_stated'] and not r['menu_only']:
            note = '  [no expected answer stated]'
        print('%s %-56s %d live, %d offered%s' % (
            flag, r['path'], len(r['live']), len(r['offered']), note))
        for t in r['missing']:
            print('        no query reads back: %s' % t)
    print('')
    print('%d file(s) with destructive statements, %d with a gap, %d menu-only'
          % (len(reports), len(bad), len(menus)))
    if menus:
        print('')
        print('MENU-ONLY files have every statement commented out -- a list a')
        print('human chooses from, not a script. Reported, never a gap:')
        for r in menus:
            print('    %s' % r['path'])
    if bad:
        print('')
        print('A cleanup with no confirm query cannot answer "did it run?" -- not')
        print('now and not in six months. The Supabase editor reports success for')
        print('the statements it DID run, so a partial apply looks like a full')
        print('one from the outside. Add, next to each destructive statement:')
        print("    select count(*) from public.<table> where <id> = '<x>';  -- expect 0")
        print('')
        print('THIS CANNOT TELL YOU WHETHER A FILE WAS RUN. Nothing in the repo')
        print('can. It tells you whether the file could ever answer that.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
