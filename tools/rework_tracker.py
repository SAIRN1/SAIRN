#!/usr/bin/env python
# OWNER: cody
"""Count REWORK EVENTS over time, in four named shapes, from what was already written.

    python tools/rework_tracker.py
    python tools/rework_tracker.py --json
    python tools/rework_tracker.py --report docs/2026-10-06-rework-report.md
    python tools/rework_tracker.py --known-events      # recall against my own 7
    python tools/rework_tracker.py --fixtures

Exit 0 ran and reported, 1 at least one source COULD NOT BE READ, 2 COULD NOT RUN
at all. Design note: docs/2026-10-06-cody-queue19-design-notes.md section 4.

── THE FOUR SHAPES, AS DEFINED FOR ME RATHER THAN BY ME ────────────────────
  COLLISION       a sandbox or shared-state collision between sessions
  HARNESS_STATUS  a claim cited from a harness "completed (exit code N)"
                  instead of a captured code
  AGENT_SCOPE     a sub-agent or fork given full instructions, or writing
                  shared state
  STALE_FIGURE    a stale or reused figure later corrected

── THE HEADLINE LIMIT, MEASURED AND NOT ARGUED ─────────────────────────────
**It reads what was already written down.** Rework nobody recorded is invisible,
and that is almost certainly the majority.

The second limit is sharper and is the reason `--known-events` exists: **the four
shapes do not span one real batch's rework.** Driven against the seven mistakes
I wrote up in `docs/handoff-cody-2026-10-06b.md` §6, the four tags account for
some of them and NOT the rest -- a tautological arm, a guard in the wrong
function and a shell-eaten verdict are all rework and NONE of them is one of
these four shapes. The number is printed by `--known-events` rather than
asserted here, because a recall figure written into a docstring is the staleness
this platform keeps paying for.

── WHY IT IS NOT A BLAME TOOL ──────────────────────────────────────────────
It counts SHAPES and names the commit. It does not rank sessions, and it does
not weigh severity -- a STALE_FIGURE that cost a minute and one that cost a run
count the same, because weighting them is a judgement no regex has.

── WHAT IT DOES NOT READ ───────────────────────────────────────────────────
**The hover auditors' logs.** They are another role's tamper-evident record and
a build agent does not mine them. The design note listed them as a source; that
was overridden on instruction and the deviation is recorded here rather than
left as a silent difference between the note and the code.
"""

import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CRITERIA_VERSION = '2026-10-06.1'
EXIT_SOURCE_UNREAD = 1
EXIT_COULD_NOT_RUN = 2

GIT_TIMEOUT = 180

# ── STALE_FIGURE is a CONJUNCTION and cannot be written as one regex ───────
# All three of the things the tag's own definition names must be present in one
# window: a digit, a word meaning "this is a figure", and a verb meaning "it
# was corrected". A regex alternation cannot express that without listing every
# ordering; a window scan can, and it is three lines.
_FIG_DIGIT = re.compile(r'(?<![\w.\[-])\d[\d,]*(?![\w.%\]])')
# `of \d+` was in this list for one run and is NOT a figure word -- it is a
# digit, which the digit test already requires, so including it made the
# conjunction a disjunction in disguise.
_FIG_WORD = re.compile(r'\b(?:count|counts|figure|figures|number|numbers|total|'
                       r'totals|tally|reading|census)\b', re.I)
_FIG_VERB = re.compile(r'(?:was wrong|were wrong|is wrong|turned out to be wrong|'
                       r'off by|had gone stale|was stale|went stale|'
                       r're-?measured|re-?counted|re-?derived|corrected|'
                       r'invented|fabricated|overstated|understated)', re.I)
_FIG_WINDOW = 140


def _stale_figure(text):
    """The matched window, or None. A digit AND a figure word AND a correction
    verb, all inside one %d-character window.""" % _FIG_WINDOW
    for m in _FIG_VERB.finditer(text):
        lo = max(0, m.start() - _FIG_WINDOW)
        hi = min(len(text), m.end() + _FIG_WINDOW)
        w = text[lo:hi]
        if _FIG_DIGIT.search(w) and _FIG_WORD.search(w):
            return re.sub(r'\s+', ' ', w).strip()
    return None


# ── THE RULES. Each is (positive, veto) and the veto half is load-bearing ───
# A veto exists for ONE reason: this repo's prose is largely ABOUT these shapes,
# so a bare keyword search counts the documentation of a rule as an instance of
# it. The tracker would then report its own corrective writing as rework, and
# the number would rise fastest in the batches that were most careful.
RULES = [
    ('COLLISION',
     re.compile(r'(?:(?:two|both|another|other)\s+(?:session|clone|runner|probe|worktree)s?\b'
                r'|session\w*\s+and\s+\w*session'
                r'|shared[ -](?:state|config)\b'
                r'|same\s+(?:worktree|sandbox|ledger|file)\b)'
                r'[\s\S]{0,160}?'
                r'(?:collid\w+|collision|clobber\w*|interleav\w+|'
                r'overwr\w+|whole-file conflict|conflict on every|raced?\b|'
                r'restored the (?:first|other))', re.I),
     re.compile(r'(?:must not|cannot be allowed|would be the failure|'
                r'exists to (?:stop|prevent)|the rule is|rule \d+:|'
                r'convention \d+)', re.I)),

    # The harness's own phrasing, verbatim. Anchored on the PARENTHESISED form
    # because that is what a harness notification actually prints -- prose
    # about exit codes ("exit 2 is COULD NOT RUN") does not take this shape.
    ('HARNESS_STATUS',
     re.compile(r'(?:completed|notification|reported|said|told me)'
                r'[\s\S]{0,60}?\(exit code \d+\)'
                r'|\(exit code \d+\)[\s\S]{0,60}?(?:while|but|REAL\b)', re.I),
     re.compile(r'capture_exit|exit_status_attributable', re.I)),

    ('AGENT_SCOPE',
     re.compile(r'(?:sub-?agent|subagent|a fork\b|forked agent|Agent tool|'
                r'sweep-runner|suite-driver)'
                r'[\s\S]{0,200}?'
                r'(?:full instructions|the whole queue|wrote to (?:a )?shared|'
                r'writing shared state|had no Bash|no Bash this session|'
                r'returned in \d+ seconds?|came back in \d+ seconds?|'
                r'reported \d+ seconds)', re.I),
     re.compile(r'(?:must be given|never give|do not dispatch|the rule for '
                r'(?:a )?sub-?agents?|scope rule)', re.I)),

    # ── THE THIRD VERSION, AND THE FIRST TWO ARE KEPT HERE AS THE MEASUREMENT
    # v1  `<any digit> within 80 chars of <a correction verb>`      -> 106 hits
    # v2  v1 plus "or a FIGURE WORD near a correction verb"         -> 280 hits
    # v3  a digit AND a figure word AND a correction verb, all in
    #     one 140-character window                                  -> see --json
    #
    # v2 was written as a tightening and WIDENED THE RULE 2.6x, because adding
    # an alternative to an alternation can only ever add. I measured it instead
    # of reasoning about it, which is the only reason the mistake is in this
    # comment and not in the output. v1's real defect was firing on a digit
    # that merely sat near the word "wrong" -- `list.length-1 ... is wrong`,
    # `0.5 or 1% povidone-iodine ... WHAT WAS WRONG`.
    #
    # v3 requires all THREE things the tag's own definition names. It is a
    # conjunction, not an alternation, so it can only narrow.
    ('STALE_FIGURE', _stale_figure,
     re.compile(r'(?:do not quote (?:either |any )?figure|run it\b|'
                r'count the (?:directories|headings)|'
                r'never (?:quote|trust) a (?:number|count|figure))', re.I)),
]

BATCH_RE = re.compile(r'\b(?:queue|batch)\s*#?\s*(\d{1,3})\b', re.I)


def _fire(pos, text):
    """The matched text, or None. `pos` is a compiled regex or a callable."""
    if callable(pos) and not hasattr(pos, 'search'):
        return pos(text)
    m = pos.search(text)
    return m.group(0) if m else None


def classify(text):
    """[tag, ...] -- every rule whose positive fires and whose veto does not."""
    hits = []
    for tag, pos, veto in RULES:
        if _fire(pos, text) and not veto.search(text):
            hits.append(tag)
    return hits


def _week(iso):
    """'YYYY-Www' from an ISO-ish date string, or None."""
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(iso or ''))
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    try:
        iy, iw, _ = datetime.date(y, mo, d).isocalendar()
    except ValueError:
        return None
    return '%04d-W%02d' % (iy, iw)


def _batch(text):
    m = BATCH_RE.search(text or '')
    return ('batch%s' % m.group(1)) if m else 'unbatched'


# ── THE SOURCES. Each returns (events, unread_reason) and never both. ───────
def _src_git(repo):
    try:
        r = subprocess.run(['git', '-C', repo, 'log', '--no-merges',
                            '--format=%H%x1f%cI%x1f%s%x1e%b%x1e'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as e:
        return ([], 'git log failed: %s: %s' % (type(e).__name__, e))
    if r.returncode != 0:
        return ([], 'git log exited %d: %s' % (r.returncode, (r.stderr or '')[:200]))
    out, events = r.stdout or '', []
    # One record per commit: header\x1fdate\x1fsubject\x1ebody\x1e
    for chunk in out.split('\x1e\x1e'):
        if not chunk.strip():
            continue
        parts = chunk.split('\x1e')
        head = parts[0]
        body = parts[1] if len(parts) > 1 else ''
        bits = head.split('\x1f')
        if len(bits) < 3:
            continue
        sha, when, subject = bits[0].strip(), bits[1].strip(), bits[2]
        text = subject + '\n' + body
        for tag in classify(text):
            events.append({'tag': tag, 'source': 'git', 'ref': sha[:12],
                           'when': when, 'week': _week(when),
                           'batch': _batch(text),
                           'quote': _quote(text, tag)})
    return (events, None)


def _quote(text, tag):
    """The matched sentence, trimmed -- so a reader can judge the hit."""
    for t, pos, _v in RULES:
        if t != tag:
            continue
        m = _fire(pos, text)
        if not m:
            return ''
        return re.sub(r'\s+', ' ', m).strip()[:200]
    return ''


def _src_json_records(repo, rel, fields, when_field):
    path = os.path.join(repo, rel)
    if not os.path.isfile(path):
        return ([], '%s is absent' % rel)
    try:
        d = json.load(io.open(path, encoding='utf-8'))
    except (OSError, ValueError) as e:
        return ([], '%s could not be parsed: %s: %s' % (rel, type(e).__name__, e))
    recs = None
    if isinstance(d, dict):
        for k in ('records', 'reviews', 'suites', 'entries'):
            if isinstance(d.get(k), list):
                recs = d[k]
                break
        if recs is None:
            # A dict-of-entries register. The VALUES are the records.
            recs = [v for v in d.values() if isinstance(v, dict)]
    elif isinstance(d, list):
        recs = d
    if recs is None:
        return ([], '%s has no record list this reader recognises' % rel)
    events = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        text = '\n'.join(str(r.get(f) or '') for f in fields)
        if not text.strip():
            continue
        when = str(r.get(when_field) or '')
        for tag in classify(text):
            events.append({'tag': tag, 'source': rel, 'ref': when or '?',
                           'when': when, 'week': _week(when),
                           'batch': _batch(text), 'quote': _quote(text, tag)})
    return (events, None)


def _src_my_handoffs(repo):
    d = os.path.join(repo, 'docs')
    if not os.path.isdir(d):
        return ([], 'docs/ is absent')
    events, read = [], 0
    for fn in sorted(os.listdir(d)):
        if not re.match(r'handoff-cody-\d{4}-\d{2}-\d{2}\w*\.md$', fn):
            continue
        try:
            text = io.open(os.path.join(d, fn), encoding='utf-8',
                           errors='replace').read()
        except OSError as e:
            return ([], 'docs/%s could not be read: %s' % (fn, e))
        read += 1
        when = re.match(r'handoff-cody-(\d{4}-\d{2}-\d{2})', fn).group(1)
        for para in re.split(r'\n\s*\n', text):
            for tag in classify(para):
                events.append({'tag': tag, 'source': 'docs/' + fn,
                               'ref': fn, 'when': when, 'week': _week(when),
                               'batch': _batch(text), 'quote': _quote(para, tag)})
    if not read:
        return ([], 'no docs/handoff-cody-*.md was found')
    return (events, None)


SOURCES = [
    ('git commit messages', lambda repo: _src_git(repo)),
    ('docs/tier-a-reviews.json', lambda repo: _src_json_records(
        repo, 'docs/tier-a-reviews.json', ('what', 'verdict'), 'opened_at')),
    ('docs/known-red-suites.json', lambda repo: _src_json_records(
        repo, 'docs/known-red-suites.json',
        ('why', 'note', 'reason', 'what', 'diagnosis'), 'since')),
    ('docs/defect-density-register.json', lambda repo: _src_json_records(
        repo, 'docs/defect-density-register.json',
        ('what', 'description', 'note', 'detection_method'), 'found_at')),
    ('my own handoff docs', lambda repo: _src_my_handoffs(repo)),
]


def collect(repo=None):
    repo = repo or REPO
    events, unread = [], []
    for name, fn in SOURCES:
        ev, why = fn(repo)
        if why:
            unread.append((name, why))
        else:
            events.extend(ev)
    return (events, unread)


def buckets(events):
    per_week, per_batch, per_tag = {}, {}, {}
    for e in events:
        per_week.setdefault(e['week'] or 'undated', {}).setdefault(e['tag'], 0)
        per_week[e['week'] or 'undated'][e['tag']] += 1
        per_batch.setdefault(e['batch'], {}).setdefault(e['tag'], 0)
        per_batch[e['batch']][e['tag']] += 1
        per_tag[e['tag']] = per_tag.get(e['tag'], 0) + 1
    return (per_week, per_batch, per_tag)


# ── THE SEVEN KNOWN EVENTS, verbatim from my own handoff, as recall data ────
# Written out here rather than grepped so the arm does not pass because the
# handoff happens to be in the corpus: the question is whether the RULES see
# these shapes, not whether the file is readable.
KNOWN_SEVEN = [
    ('1 shell-substituted verdict + uid leak',
     'A review verdict was passed to tier_a_review_gate.py --discharge as a shell '
     'argument. The shell command-substituted two backticked fragments away and '
     'replaced a third with the output of id, pasting uid=197609(marsh) into the '
     'ledger. Reverted.'),
    ('2 whole-file ledger reformat',
     'The repair rewrote docs/tier-a-reviews.json with json.dumps(indent=1): 5681 '
     'insertions and 5674 deletions on a 235-record ledger that four clones 3-way '
     'merge, where the correct diff was 15 and 8. Every other session would have '
     'taken a whole-file conflict on every record.'),
    ('3 UNBOUNDABLE guard in the wrong function',
     'The UNBOUNDABLE guard sat inside _bare_baseline(), which the WRITER tier '
     'never reaches, so run_all_tests.py still printed "no fixture lock and no '
     'control". Caught by driving the tool, not by reading it.'),
    ('4 two arms matching their own text',
     'L1 matched the fixture inside L1c and L2 matched the retired sentence in the '
     'comment explaining its own fix. My own comments trip my own scanners.'),
    ('5 a fabricated check',
     'My first config-refusal arm was assert.ok(true) with a paragraph explaining '
     'why it could not be tested. It could; a child process has an empty module '
     'cache.'),
    ('6 a wrong aud assertion and a loose SQL regex',
     'A loose SQL regex invented a 27-vs-26 discrepancy against a runbook that was '
     'right, and the figure was corrected to 26 after I re-measured.'),
    ('7 a near-false accusation against the push gate',
     'When a block survived unstaging I concluded three documents were already '
     'stale at HEAD. Then I moved the untracked file out and re-measured: all '
     'three --check runs exit 0. The gate was right and the count I quoted was '
     'wrong.'),
]


def known_events_report():
    """(found, total, rows). Recall of the four shapes over seven real events."""
    rows, found = [], 0
    for label, text in KNOWN_SEVEN:
        tags = classify(text)
        if tags:
            found += 1
        rows.append((label, tags))
    return (found, len(KNOWN_SEVEN), rows)


def _fixtures():
    ok = True
    tally = {'n': 0, 'neg': 0}

    def arm(label, cond, detail=''):
        nonlocal ok
        tally['n'] += 1
        if 'negative' in label.lower() or 'COULD NOT' in label:
            tally['neg'] += 1
        if not cond:
            ok = False
            print('  FAIL %s%s' % (label, (' -- ' + str(detail)) if detail != '' else ''))
        else:
            print('  ok   %s' % label)

    # ── ONE POSITIVE AND ONE NEAR-MISS NEGATIVE PER TAG ────────────────────
    pos = {
        'COLLISION': 'Two probe runs at once; the second restored the first\'s '
                     'mutation and reported byte-identical success.',
        'HARNESS_STATUS': 'The notification said completed (exit code 0) while the '
                          'captured status said 1.',
        'AGENT_SCOPE': 'The sweep-runner subagent returned in 18 seconds for '
                       'harnesses that exceeded 420 seconds.',
        'STALE_FIGURE': 'The count of 23 was wrong; re-measured it is 6 of 50.',
    }
    neg = {
        'COLLISION': 'Convention 12: two sessions must not write the same shared '
                     'state, which is the failure this rule exists to prevent.',
        'HARNESS_STATUS': 'Use tools/capture_exit.py: a backgrounded run reports '
                          '(exit code 0) from the trailing element, so read the '
                          'status file instead.',
        'AGENT_SCOPE': 'The rule for sub-agents is that they must be given one '
                       'scoped task and never the whole queue or shared state.',
        'STALE_FIGURE': 'Re-measured 2026-09-15: 6 of 50, down from 23 of 39. Do '
                        'not quote either figure from here -- run it.',
    }
    for tag in ('COLLISION', 'HARNESS_STATUS', 'AGENT_SCOPE', 'STALE_FIGURE'):
        arm('%-14s fires on its own shape' % tag, tag in classify(pos[tag]),
            classify(pos[tag]))
        arm('%-14s NEGATIVE: does NOT fire on prose ABOUT the rule -- without '
            'this the tracker counts its own documentation' % tag,
            tag not in classify(neg[tag]), classify(neg[tag]))

    # The buckets must sum to the total, or a per-week table is decoration.
    ev = [{'tag': 'COLLISION', 'week': '2026-W40', 'batch': 'batch10'},
          {'tag': 'COLLISION', 'week': '2026-W40', 'batch': 'batch10'},
          {'tag': 'STALE_FIGURE', 'week': '2026-W41', 'batch': 'unbatched'}]
    pw, pb, pt = buckets(ev)
    arm('weekly buckets sum to the total',
        sum(sum(v.values()) for v in pw.values()) == len(ev), pw)
    arm('per-batch buckets sum to the total',
        sum(sum(v.values()) for v in pb.values()) == len(ev), pb)
    arm('per-tag counts sum to the total', sum(pt.values()) == len(ev), pt)

    # A source that cannot be read is NAMED, never a silent zero.
    ev2, why = _src_json_records(REPO, 'docs/no-such-register-xyzzy.json',
                                 ('what',), 'when')
    arm('COULD NOT READ: an absent source is a NAMED reason, never a silent '
        'zero -- the one shape that would report a clean week because nothing '
        'was read', ev2 == [] and why and 'absent' in why, (ev2, why))

    import tempfile
    import shutil
    td = tempfile.mkdtemp(prefix='rework_fx_')
    try:
        bad = os.path.join(td, 'docs')
        os.makedirs(bad)
        io.open(os.path.join(bad, 'known-red-suites.json'), 'w',
                encoding='utf-8', newline='\n').write('{ not json\n')
        ev3, why3 = _src_json_records(td, 'docs/known-red-suites.json',
                                      ('why',), 'since')
        arm('COULD NOT READ: an unparseable source is a NAMED reason too',
            ev3 == [] and why3 and 'could not be parsed' in why3, (ev3, why3))
        ev4, why4 = _src_my_handoffs(td)
        arm('COULD NOT READ: no handoff of mine present is NAMED, not zero '
            'events', ev4 == [] and why4 and 'no docs/handoff-cody' in why4,
            (ev4, why4))
    finally:
        shutil.rmtree(td, ignore_errors=True)

    arm('week derivation is ISO and rejects a non-date',
        _week('2026-10-06T12:00:00Z') == '2026-W41' and _week('nope') is None,
        (_week('2026-10-06T12:00:00Z'), _week('nope')))
    arm('batch derivation reads queue19 and batch 10 and defaults to unbatched',
        _batch('queue19 items') == 'batch19' and _batch('batch 10 item8') == 'batch10'
        and _batch('nothing here') == 'unbatched')

    # THE RECALL ARM. It does not assert a number -- it asserts that the tool
    # REPORTS one, and that the report is not vacuous in either direction.
    found, total, rows = known_events_report()
    arm('the seven known events are driven and the recall is a REPORTED number, '
        'not a claimed one', total == 7 and isinstance(found, int), (found, total))
    arm('NEGATIVE: recall is not 7 of 7 -- the four shapes do NOT span one real '
        'batch, and a tracker claiming they do would be the finding',
        found < total, (found, total))
    arm('...and not 0 of 7 either, so the rules are not simply blind',
        found > 0, (found, total))

    print('  criteria lock: %d arms, %d of them negative (criteria %s)'
          % (tally['n'], tally['neg'], CRITERIA_VERSION))
    return ok


def _render(events, unread, per_week, per_batch, per_tag):
    out = []
    out.append('REWORK TRACKER (criteria %s)' % CRITERIA_VERSION)
    out.append('')
    out.append('  %d event(s) across %d source(s); %d source(s) COULD NOT BE READ'
               % (len(events), len(SOURCES) - len(unread), len(unread)))
    out.append('')
    for tag, _p, _v in RULES:
        out.append('  %-14s %d' % (tag, per_tag.get(tag, 0)))
    out.append('')
    out.append('  PER WEEK')
    for wk in sorted(per_week):
        row = per_week[wk]
        out.append('    %-10s %3d   %s' % (wk, sum(row.values()),
                   ', '.join('%s=%d' % (k, v) for k, v in sorted(row.items()))))
    out.append('')
    out.append('  PER BATCH')
    for b in sorted(per_batch, key=lambda x: (x == 'unbatched', x)):
        row = per_batch[b]
        out.append('    %-12s %3d   %s' % (b, sum(row.values()),
                   ', '.join('%s=%d' % (k, v) for k, v in sorted(row.items()))))
    if unread:
        out.append('')
        out.append('  COULD NOT BE READ -- NOT zero events, and the counts above')
        out.append('  are therefore a FLOOR rather than a total:')
        for name, why in unread:
            out.append('    ? %s: %s' % (name, why))
    found, total, rows = known_events_report()
    out.append('')
    out.append('  RECALL AGAINST SEVEN KNOWN EVENTS: %d of %d' % (found, total))
    for label, tags in rows:
        out.append('    %-46s %s' % (label, ','.join(tags) or 'NONE OF THE FOUR'))
    out.append('')
    out.append('  THE FOUR SHAPES DO NOT SPAN ONE REAL BATCH, and the line above')
    out.append('  is the measurement of that rather than a defect in the corpus.')
    out.append('')
    out.append('  LIMIT: it reads what was already written down. Rework nobody')
    out.append('  recorded is invisible and is probably the majority.')
    out.append('  It does not read the hover auditors\' logs -- another role\'s')
    out.append('  record is not a build agent\'s corpus.')
    return '\n'.join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='count rework events in four named shapes from existing records')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--report', metavar='PATH',
                    help='also write a short report doc at PATH')
    ap.add_argument('--known-events', action='store_true',
                    help='print recall against the seven known events and stop')
    ap.add_argument('--fixtures', action='store_true')
    ap.add_argument('--limit', type=int, default=12,
                    help='how many example events to list per tag (default 12)')
    a = ap.parse_args(argv)

    if a.fixtures:
        print('REWORK TRACKER -- selftest (criteria %s)' % CRITERIA_VERSION)
        return 0 if _fixtures() else 1

    if a.known_events:
        found, total, rows = known_events_report()
        print('RECALL AGAINST SEVEN KNOWN EVENTS: %d of %d (criteria %s)'
              % (found, total, CRITERIA_VERSION))
        for label, tags in rows:
            print('  %-46s %s' % (label, ','.join(tags) or 'NONE OF THE FOUR'))
        print('')
        print('A shape with NO tag is still rework. The four tags were defined')
        print('for this tool and they do not span one real batch.')
        return 0

    if not os.path.isdir(os.path.join(REPO, '.git')) \
            and not os.path.isfile(os.path.join(REPO, '.git')):
        print('COULD NOT RUN: %s is not a git clone, so the largest source is '
              'unavailable.' % REPO, file=sys.stderr)
        return EXIT_COULD_NOT_RUN

    events, unread = collect()
    per_week, per_batch, per_tag = buckets(events)

    if a.json:
        print(json.dumps({'criteria': CRITERIA_VERSION,
                          'events': events, 'unread': unread,
                          'per_week': per_week, 'per_batch': per_batch,
                          'per_tag': per_tag}, indent=1))
    else:
        print(_render(events, unread, per_week, per_batch, per_tag))
        print('')
        print('  EXAMPLES (up to %d per tag, with the matched text)' % a.limit)
        for tag, _p, _v in RULES:
            rows = [e for e in events if e['tag'] == tag]
            print('')
            print('  %s -- %d' % (tag, len(rows)))
            for e in sorted(rows, key=lambda x: x['when'] or '')[-a.limit:]:
                print('    %-12s %-10s %s' % (e['ref'][:12], e['week'] or 'undated',
                                              (e['quote'] or '')[:110]))

    if a.report:
        body = ['# Rework events — four named shapes, derived from existing records',
                '',
                '**Generated by `tools/rework_tracker.py` (criteria %s).** Do not '
                'hand-edit; re-run it.' % CRITERIA_VERSION, '', '```',
                _render(events, unread, per_week, per_batch, per_tag), '```', '']
        io.open(a.report, 'w', encoding='utf-8', newline='\n').write(
            '\n'.join(body))
        print('')
        print('report written: %s' % a.report)

    return EXIT_SOURCE_UNREAD if unread else 0


if __name__ == '__main__':
    sys.exit(main())
