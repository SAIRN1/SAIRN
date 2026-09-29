r"""A FINDING THE AUDITOR MADE AND NOBODY ROUTED IS A FINDING NOBODY HAS.

    python tools/hover_routing_gap_check.py
    python tools/hover_routing_gap_check.py --log <path>   # drive a fixture
    python tools/hover_routing_gap_check.py --json

REPORT ONLY. Exit 0 clean, 1 findings, 2 COULD NOT RUN. It writes nothing
anywhere and it is not wired into a gate.

── WHY, AND IT IS THREE MEASURED MISSES RATHER THAN A WORRY ─────────────────
The hover auditor writes what it finds into its own tamper-evident log. A build
session reads `docs/SAIRN-OPEN-WORK-INDEX.md`. **Nothing connects the two.**

On 2026-09-29 three findings were sitting in the log unrouted:

  * `leg_petcases`   -- a tier row asserting "no PII" over a living person's
                        name, phone and email. Never reached the index.
  * `leg_processions` -- a tier row asserting "no PII" over a resource carrying
                        a device's LIVE GPS position. Never reached the index,
                        and a delegated source-reading pass on the same resource
                        had separately reported it clean.
  * `msb_sale_hours` -- log #608, a tier row whose deciding sentence was FALSE
                        about an alcohol-sale gate. Stood a day unactioned.

All three landed only because a human read the log by hand. That is the gap: not
that the auditor missed anything, but that the transport between two documents
was a person remembering.

── WHAT IT DOES NOT DO, so nothing reads it as more than it is ──────────────
* IT DOES NOT ROUTE ANYTHING. It reports which findings have not landed. A tool
  that filed index rows on the auditor's behalf would be the auto-remediation
  failure the twelve disciplines name: a detector that acts on its own findings.
* IT DOES NOT GO THROUGH `tools/defect_register.py`. The register is a
  RETROSPECTIVE RECORD of confirmed defects with a reviewer behind each one. Using
  it as an intake queue would put unrouted findings into a denominator that is
  supposed to mean something else, and every density figure computed from it
  would quietly change meaning.
* IT DOES NOT JUDGE WHETHER A FINDING IS RIGHT. Only whether it reached the page
  a build session reads.
* IT DOES NOT ARGUE WITH A WITHHELD FINDING. The auditor logs findings it
  deliberately chose NOT to report (`type: no-report`), and those are never
  flagged -- the whole point of recording a decision not to report is that it was
  a decision.

── THE THRESHOLD IS REASONED, NOT CALIBRATED, AND THE OUTPUT SAYS SO ───────
A routable finding is flagged when it is older than SIX HOURS **or** more than
FIFTEEN log entries have been written after it.

**Neither number is measured.** Six hours is a claim's expiry window on this
platform, reused because it is the interval the rest of the coordination system
already treats as "long enough that somebody should have acted". Fifteen entries
is a guess at when a finding has scrolled out of a session's working view. THERE
IS NO DATA BEHIND EITHER, because the routing lag has never been recorded -- which
is itself the reason this tool exists.

**OR rather than AND, deliberately:** a busy hour buries a finding as effectively
as a quiet day does, and requiring both would let thirty entries in twenty minutes
bury one silently.

**Every finding this tool prints repeats that the threshold was chosen.** A number
presented as measured when it was picked is the defect this platform records most
often after a silent failure, and a report-only tool is exactly where that
misreading is cheapest to make and hardest to notice.

── FAIL CLOSED, AND WHY THIS ONE PARTICULARLY ──────────────────────────────
The log lives OUTSIDE every clone, in the hover instance's own project directory,
so on most machines it is legitimately absent. An absent log must therefore be
`COULD NOT RUN` and never "no unrouted findings" -- those two answers look
identical in a terminal and mean opposite things. An empty or unparseable log gets
the same treatment for the same reason: a reader that returns zero rows is
indistinguishable from a log with nothing in it.

── READ-ONLY ACROSS A BOUNDARY, stated because the boundary is real ─────────
`CLAUDE.md` is explicit that a build agent must not reach into the hover
auditor's clone. This tool OPENS ONE FILE FOR READING and writes nothing, to no
path, in any clone. It does not import the auditor's tools, does not touch its
anchors record, and does not run in its directory. The separation control exists
so a build agent cannot alter the audit record; reading what the auditor
published is the opposite of that, and a routing gap nobody can see is worse than
the risk of reading one file.
"""
import argparse
import datetime
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

CRITERIA_VERSION = '2026-09-29.1'

# The auditor's log, outside every clone. Named rather than derived: there is no
# way to compute another project's directory hash, and guessing at one would
# produce a path that is wrong in a way this tool could not detect.
DEFAULT_LOG = os.path.join(
    os.path.expanduser('~'), '.claude', 'projects',
    'C--Users-marsh-Documents-SAIRN-hover', 'hover-audit-log',
    'hover-audit-log.jsonl')

INDEX = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')

# ── THE THRESHOLDS. Read the header: both are CHOSEN, not measured. ─────────
STALE_HOURS = 6
STALE_ENTRIES = 15
THRESHOLD_NOTE = ('flagged on a REASONED, NOT CALIBRATED threshold: older than '
                  '%dh OR more than %d log entries behind. Neither number is '
                  'measured -- the routing lag has never been recorded, which is '
                  'why this tool exists.' % (STALE_HOURS, STALE_ENTRIES))

# A resource name on this platform: a short app prefix, an underscore, and the
# rest. Used ONLY by the prose fallback, to decide which words in a `ref` field
# could be a resource at all. Deliberately narrow: a false negative here means a
# pre-field entry goes unchecked and the output says the fallback is weaker,
# whereas a false positive would flag the auditor for a word that is not a
# resource and make the tool noise.
RESOURCE_RE = re.compile(r'^[a-z]{2,4}_[a-z0-9_]{2,}$')


class CouldNotRead(Exception):
    """The log could not be read. NOT the same as an empty log, and not folded
    into one -- see the header."""


def landed_in(name, text):
    """Is `name` present in `text` as a WHOLE identifier?

    NEVER a substring. `jobs` must not match inside `grd_jobs`, because an
    unrouted finding about one resource would then be reported as landed on the
    strength of an unrelated resource's name containing it. The lookarounds
    exclude the identifier characters on both sides, which also rules out a
    prefix (`leg_pet` against `leg_petcases`) and a suffix (`petcases`).

    Backticks need no special case: they are not identifier characters, so a
    backtick-quoted name satisfies the same boundary as a bare one.
    """
    if not name:
        return False
    rx = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])')
    return bool(rx.search(text or ''))


def routable_names(entry):
    """(names, source) for one log entry.

    `source` is one of:
      'structured'     -- the entry carries the `routable` list H1 added. Exact.
      'prose-fallback' -- the entry predates that field, so resource-shaped
                          tokens are read out of its `ref`. WEAKER, and the
                          caller is expected to say so in its output rather than
                          present both as the same kind of answer.
      'withheld'       -- `type: no-report`. A deliberate decision not to
                          report, never flagged.
      'none'           -- nothing routable here.
    """
    if (entry.get('type') or '') == 'no-report':
        return [], 'withheld'

    r = entry.get('routable')
    if isinstance(r, list) and r:
        return [str(x).strip() for x in r if str(x).strip()], 'structured'
    if isinstance(r, str) and r.strip():
        return [x.strip() for x in r.split(',') if x.strip()], 'structured'

    # ── THE FALLBACK, AND ITS WEAKNESS IS THE POINT ────────────────────────
    # 681 of 683 entries were written before the field existed. Skipping them
    # would make this tool silent about exactly the period the three missed
    # findings came from. So their `ref` is read for resource-shaped tokens --
    # which is a guess about a free-text field, and every finding derived this
    # way is labelled.
    if (entry.get('type') or '') != 'finding':
        return [], 'none'
    ref = str(entry.get('ref') or '')
    names = [t for t in re.split(r'[,\s;]+', ref) if RESOURCE_RE.match(t)]
    return (names, 'prose-fallback') if names else ([], 'none')


def _parse_ts(ts):
    try:
        return datetime.datetime.strptime(str(ts), '%Y-%m-%dT%H:%M:%SZ')
    except Exception:
        return None


def read_log(path):
    """Rows from the log, or raise CouldNotRead. A zero-row file RAISES."""
    if not os.path.isfile(path):
        raise CouldNotRead('the hover audit log is not at %s. It lives outside '
                           'every clone, in the hover instance\'s own project '
                           'directory, so on this machine it may simply not '
                           'exist -- but ABSENT is not the same answer as NO '
                           'UNROUTED FINDINGS and is not reported as one.' % path)
    rows, bad = [], 0
    try:
        for line in io.open(path, encoding='utf-8', errors='replace'):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                bad += 1
    except OSError as exc:
        raise CouldNotRead('the hover audit log at %s could not be read (%s).'
                           % (path, exc))
    if not rows:
        raise CouldNotRead(
            'the hover audit log at %s yielded NO parseable entry (%d '
            'unparseable line(s)). A reader that returns zero rows is '
            'indistinguishable from a log with nothing in it, so this is the '
            'third state rather than a clean run.' % (path, bad))
    return rows, bad


def gaps(rows, index_text, now=None, stale_hours=STALE_HOURS,
         stale_entries=STALE_ENTRIES):
    """Routable findings that have not landed in the index and are past either
    threshold. One finding per (entry, resource) pair."""
    now_dt = _parse_ts(now) if now else datetime.datetime.utcnow()
    total = len(rows)
    out = []
    for i, e in enumerate(rows):
        names, source = routable_names(e)
        if not names or source in ('withheld', 'none'):
            continue
        behind = total - 1 - i
        age_h = None
        ts = _parse_ts(e.get('ts'))
        if ts is not None and now_dt is not None:
            age_h = (now_dt - ts).total_seconds() / 3600.0
        # EITHER threshold. See the header for why OR and not AND.
        too_old = age_h is not None and age_h > stale_hours
        too_buried = behind > stale_entries
        if not (too_old or too_buried):
            continue
        for name in names:
            if landed_in(name, index_text):
                continue
            out.append({
                'seq': e.get('seq'),
                'ts': e.get('ts'),
                'resource': name,
                'source': source,
                'age_hours': None if age_h is None else round(age_h, 1),
                'entries_behind': behind,
                'target': e.get('target'),
                'threshold_note': THRESHOLD_NOTE,
            })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--log', default=DEFAULT_LOG,
                    help='the hover audit log. Exists so the control can drive '
                         'fixtures instead of the real record.')
    ap.add_argument('--index', default=INDEX)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--now', default=None,
                    help='the instant to measure age against, so the control '
                         'does not race a clock.')
    args = ap.parse_args(argv)

    print('HOVER ROUTING GAP -- a finding nobody routed is a finding nobody has')
    print('  criteria  : %s' % CRITERIA_VERSION)
    print('  log       : %s' % args.log)
    print('  index     : %s' % os.path.relpath(args.index, REPO))
    print('  threshold : REASONED, NOT CALIBRATED -- older than %dh OR more '
          'than %d entries behind.' % (STALE_HOURS, STALE_ENTRIES))
    print('              Neither number is measured. The routing lag has never')
    print('              been recorded, which is the reason this tool exists.')
    print('              OR and not AND: a busy hour buries a finding as well')
    print('              as a quiet day does.')

    try:
        rows, bad = read_log(args.log)
    except CouldNotRead as exc:
        print()
        print('COULD NOT RUN: %s' % exc)
        print('This is the THIRD STATE. It is NOT "no unrouted findings".')
        return EXIT_COULD_NOT_RUN

    if not os.path.isfile(args.index):
        print()
        print('COULD NOT RUN: the open-work index is not at %s, so "has this '
              'landed" has nothing to mean.' % args.index)
        return EXIT_COULD_NOT_RUN
    index_text = io.open(args.index, encoding='utf-8', errors='replace').read()

    structured = sum(1 for e in rows if routable_names(e)[1] == 'structured')
    fallback = sum(1 for e in rows if routable_names(e)[1] == 'prose-fallback')
    withheld = sum(1 for e in rows if routable_names(e)[1] == 'withheld')

    print()
    print('  log entries          : %d (%d unparseable line(s), counted not '
          'hidden)' % (len(rows), bad))
    print('  with STRUCTURED routable : %d -- exact' % structured)
    print('  by PROSE FALLBACK        : %d -- WEAKER, and labelled per finding. '
          'These predate' % fallback)
    print('                             the field; resource-shaped tokens are '
          'read out of `ref`,')
    print('                             which is a guess about free text.')
    print('  deliberately WITHHELD    : %d -- `no-report`, never flagged. '
          'Recording a' % withheld)
    print('                             decision not to report IS the decision.')

    found = gaps(rows, index_text, now=args.now)

    print()
    if found:
        print('UNROUTED (%d) -- in the auditor\'s log, not in the index:' % len(found))
        for f in found:
            print('  ! seq %-5s %-26s %s' % (f['seq'], f['resource'], f['source']))
            print('      age %sh, %d entries behind, target %s'
                  % (f['age_hours'], f['entries_behind'], f['target']))
    else:
        print('No routable finding is past either threshold and missing from the '
              'index.')

    print()
    print('  THIS TOOL ROUTES NOTHING. It does not write an index row, and it')
    print('  deliberately does not go through tools/defect_register.py -- that')
    print('  register is a RETROSPECTIVE record of confirmed defects with a')
    print('  reviewer behind each one, and using it as an intake queue would')
    print('  change the meaning of every density figure computed from it.')

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'log': args.log,
                          'entries': len(rows), 'unparseable': bad,
                          'structured': structured, 'fallback': fallback,
                          'withheld': withheld,
                          'stale_hours': STALE_HOURS,
                          'stale_entries': STALE_ENTRIES,
                          'threshold_calibrated': False,
                          'findings': found}, indent=2))

    return EXIT_FINDING if found else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
