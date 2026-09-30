#!/usr/bin/env python
"""stale_basis_check.py -- catch a register row whose evidence cell claims it
was "Classified by the stated B rule rather than individually read" AFTER it
has, in fact, been individually read.

WHY THIS EXISTS. Across this session, row after row in docs/CRITICALITY-TIERS.md
kept the boilerplate basis sentence "Classified by the stated B rule rather
than individually read" long after the resource had been read (by the hover
auditor, or by a tier-a-reviews.json verdict). The VERDICT was right; the basis
sentence was a lie about how it was reached. This is the checker for that lie.

TWO SIGNALS, DELIBERATELY SEPARATED BY HOW RELIABLY EACH CAN BE GATED:

  (1) IN-FILE CONTRADICTION -- a single row that contains BOTH the boilerplate
      "rather than individually read" AND a real-read marker ("individually
      read", "read out of the app", a file:line citation). The cell contradicts
      ITSELF, with no external source needed. This is the shape a half-applied
      paste leaves (new read sentence added, old boilerplate not removed), and
      it is detectable purely from the file -- so it is GATEABLE at pre-commit.

  (2) CROSS-SOURCE STALENESS -- a row carrying the boilerplate whose resource
      appears in an in-repo tier-a-reviews.json verdict, OR (report-only) in the
      hover self-log. The verdict source is in-repo and checkable; the self-log
      is per-clone and OUTSIDE the repo, so that half is REPORT-ONLY and cannot
      be a reliable gate.

REPORT-ONLY. It never edits docs/CRITICALITY-TIERS.md -- naming the stale row is
the auditor's job; rewriting the cell is the file owner's.

    python stale_basis_check.py                 # scan the real tier file
    python stale_basis_check.py --json
    python stale_basis_check.py --selftest       # blind-locked fixtures
"""
import io
import os
import re
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = r'C:\Users\marsh\Documents\SAIRN-hover2'
TIER_FILE = os.path.join(DEFAULT_REPO, 'docs', 'CRITICALITY-TIERS.md')
REVIEWS = os.path.join(DEFAULT_REPO, 'docs', 'tier-a-reviews.json')

BOILERPLATE = re.compile(r'rather than individually read', re.I)
ROW_RE = re.compile(r'^\|\s*`([a-z0-9_]+)`\s*\|', re.I)
# A LIVE boilerplate basis is a bare trailing statement. A QUOTED one -- inside
# straight or markdown-emphasised quotes, or introduced by a past-tense
# "carried"/"used to"/"that said" -- is a row EXPLAINING it was read and no
# longer uses the phrase (e.g. bld_tasks: 'the 15 bld_ rows that carried
# "...rather than individually read"'). Those are NOT stale; excluding them is
# what stops the check crying wolf on every correctly-read row.
_QUOTED = re.compile(
    r'(?:carried|used to|that said|no longer|which read|previously|removed|'
    r'gone false|boilerplate|had said|the old|replaced)[^|]{0,90}'
    r'rather than individually read'
    r'|(?:["“”*]|&ldquo;|&rdquo;|&quot;)[^|]{0,140}rather than individually read',
    re.I)


def _boilerplate_is_live(cell_text):
    """The boilerplate is the row's LIVE basis (not a quotation of the old one)."""
    if not BOILERPLATE.search(cell_text):
        return False
    return not _QUOTED.search(cell_text)


def scan_text(md):
    """Return rows whose LIVE boilerplate basis is contradicted by a real-read
    marker in the SAME cell -- the half-applied-paste shape. Pure."""
    hits = []
    for i, line in enumerate(md.splitlines(), 1):
        m = ROW_RE.match(line)
        if not m or not _boilerplate_is_live(line):
            continue
        # a read marker that is NEITHER the boilerplate's own 'individually
        # read' NOR a NEGATED one ('NOT YET INDIVIDUALLY READ' is the pending
        # marker, not a read -- sdn_team's shape).
        scrubbed = BOILERPLATE.sub('', line)
        scrubbed = re.sub(r'not(?:\s+yet)?\s+individually read', '', scrubbed, flags=re.I)
        if re.search(r'individually read|read out of the app|\.(?:html|js):\d+',
                     scrubbed, re.I):
            hits.append({'resource': m.group(1), 'line': i})
    return hits


def _reviewed_resources(reviews_path):
    try:
        d = json.load(io.open(reviews_path, encoding='utf-8'))
    except (OSError, ValueError):
        return set()
    recs = d.get('records', d) if isinstance(d, dict) else d
    out = set()
    for r in recs if isinstance(recs, list) else []:
        for res in r.get('resources', []) or []:
            out.add(res)
    return out


_SELFLOG = os.path.join(HERE, 'hover-audit-log.jsonl')


def _selflog_read_resources(path=_SELFLOG):
    """Resources this clone's own self-log records as individually read -- a
    check or finding whose target names them. This is the signal that actually
    catches the real stale rows, and it is per-clone and OUTSIDE the repo."""
    out = set()
    try:
        for ln in io.open(path, encoding='utf-8'):
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            if e.get('type') not in ('check', 'finding'):
                continue
            for tok in (e.get('target') or '').split(','):
                tok = tok.strip()
                if re.match(r'^[a-z0-9_]+$', tok):
                    out.add(tok)
    except OSError:
        return set()
    return out


def scan_file(tier_path=TIER_FILE, reviews_path=REVIEWS, selflog_path=_SELFLOG):
    md = io.open(tier_path, encoding='utf-8', errors='replace').read()
    infile = scan_text(md)
    reviewed = _reviewed_resources(reviews_path)
    read_in_log = _selflog_read_resources(selflog_path)
    already = {h['resource'] for h in infile}
    crosssource = []
    for i, line in enumerate(md.splitlines(), 1):
        m = ROW_RE.match(line)
        if not m or not _boilerplate_is_live(line):
            continue
        res = m.group(1)
        if res in already:
            continue
        srcs = []
        if res in reviewed:
            srcs.append('tier-a-reviews')
        if res in read_in_log:
            srcs.append('self-log')
        if srcs:
            crosssource.append({'resource': res, 'line': i, 'read_by': srcs})
    return infile, crosssource


# ── FIXTURES, blind-locked ────────────────────────────────────────────────
_FIX_CONTRADICT = (
    "| `sv_x` | **B** | **B** | op | INDIVIDUALLY READ 2026-09-30: "
    "sairnvet.html:6591 writes {id, species}. Classified by the stated B rule "
    "rather than individually read |")
_FIX_PENDING = (
    "| `sv_y` | **B** | **B** | op | No elevated class -- Classified by the "
    "stated B rule rather than individually read |")
_FIX_READ = (
    "| `sv_z` | **B** | **B** | op | INDIVIDUALLY READ 2026-09-30: "
    "sairnvet.html:100 writes {id} |")


def selftest():
    bad = []

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    ck('a row with BOTH a real-read marker AND the boilerplate is flagged '
       'as an in-file contradiction',
       scan_text(_FIX_CONTRADICT) == [{'resource': 'sv_x', 'line': 1}])
    ck('KNOWN-BAD CONTROL: a genuinely PENDING row (boilerplate, no read '
       'marker) is NOT flagged -- the phrase is a valid state for an unread '
       'row', scan_text(_FIX_PENDING) == [])
    ck('a fully-read row with no boilerplate at all is not flagged',
       scan_text(_FIX_READ) == [])
    ck('the boilerplate\'s own "individually read" substring does not count '
       'as a read marker (no false contradiction on a pending row)',
       _boilerplate_is_live(_FIX_PENDING) is True and scan_text(_FIX_PENDING) == [])
    _FIX_QUOTED = ("| `bld_q` | **B** | **B** | op | INDIVIDUALLY READ "
                   "2026-09-23: sairnbuild.html:3267. All 15 rows that carried "
                   '"Classified by the stated B rule rather than individually '
                   'read" |')
    ck('KNOWN-BAD CONTROL: a row that QUOTES the boilerplate while explaining '
       'it WAS read (bld_tasks shape) is NOT flagged -- the quotation is not a '
       'live basis', scan_text(_FIX_QUOTED) == [])
    if bad:
        print('%d of 5 selftest arm(s) failed' % len(bad))
        return 1
    print('OK -- 5 arms passed')
    return 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    infile, crosssource = scan_file()
    if '--json' in argv:
        print(json.dumps({'in_file_contradiction': infile,
                          'cross_source_stale': crosssource}, indent=2))
        return 1 if (infile or crosssource) else 0
    print('STALE-BASIS CHECK -- report only, nothing changed')
    print('  tier file: %s' % TIER_FILE)
    if not infile and not crosssource:
        print('  clean: no row contradicts its own read basis')
        return 0
    if infile:
        print('  %d IN-FILE CONTRADICTION(S) -- row claims BOTH a read and the '
              '"rather than individually read" boilerplate (gateable):' % len(infile))
        for h in infile:
            print('  ! %s (line %d)' % (h['resource'], h['line']))
    if crosssource:
        print('  %d CROSS-SOURCE STALE -- boilerplate row whose resource has a '
              'tier-a-reviews verdict (report-only):' % len(crosssource))
        for h in crosssource:
            print('  ~ %s (line %d)' % (h['resource'], h['line']))
    print('\n  REPORT-ONLY. The self-log half (a row read by the auditor but '
          'never reviewed) is NOT visible here -- the self-log is per-clone and '
          'outside this repo.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
