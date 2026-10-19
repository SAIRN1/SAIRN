#!/usr/bin/env python
# OWNER: cc
# written 2026-10-17, batch b17 item 2 -- TIER 0 #1
"""Does the status registry actually reach the BOARD? Measured, not assumed.

    python tools/status_board_bridge_check.py                 # every agent
    python tools/status_board_bridge_check.py --agent cc
    python tools/status_board_bridge_check.py --nonce <token> --agent cc
    python tools/status_board_bridge_check.py --fixtures      # criteria lock

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── WHAT THIS ANSWERS, AND WHY IT HAD NO ANSWER ─────────────────────────────
`tools/sairn_status.py set` writes a row to ~/SAIRN-SESSION-LOCKS/status and
prints `drive board republished`. `tools/sairn_board_publish.py` renders those
rows into `SAIRN-board.md` and `SAIRN-latest-<agent>.md` on the Drive mount.
Every part of that is tested in isolation. NOTHING COMPARED THE TWO ENDS, so
"the bridge works" was a sentence rather than a measurement -- and the failure
it would have to catch is silent by construction: a board that renders an OLDER
write looks exactly like a board that is up to date, because it is a complete,
well-formed, plausible board either way.

So this reads the LIVE row and the PUBLISHED files and compares:

  STATE      the board's section for the agent renders the row's own state
  STAMP      ...and the row's own `updated` timestamp, which is the only field
             that can tell one write from the next
  TASK       ...and the row's task text, normalised for the board's wrapping
  FRESHNESS  the published file is not OLDER than the row it claims to render
  NONCE      with --nonce, a token written into the row on purpose must appear
             at BOTH ends -- the one check that proves THIS write crossed,
             rather than that some write did at some point

── FAILS CLOSED, PER PR 1.11 ───────────────────────────────────────────────
An unreadable mount, a missing board file and an unreadable registry are each
exit 2 COULD NOT RUN naming what was missing. They are never folded into a
pass: "the board does not disagree with the row" is not a verdict when the
board could not be read at all.

── WHAT IT CANNOT DO ───────────────────────────────────────────────────────
The mount is a SYNC directory. Bytes present there are in the sync set; that is
not proof Google acknowledged them. Only a Drive-side API read closes that, and
only a human or a chat turn can make one -- so this tool prints the board's
Drive file id and says the API read is still owed rather than implying it.
"""
import io
import json
import os
import re
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-17.1'

# How much older than the row the published file may be before it is STALE.
# Not zero: the publisher writes the file a moment after the row, and on this
# mount the two stamps come from different clocks (local file time vs the
# row's own string). Measured spread on this machine is under a second; 90s is
# deliberately loose, because this tool exists to catch a board frozen for
# HOURS, and a tight bound here would make it cry wolf on every normal write.
STALE_TOLERANCE_S = 90


def _epoch(stamp):
    """A naive local ISO stamp -> epoch, or None. Never raises."""
    if not stamp:
        return None
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return time.mktime(time.strptime(str(stamp)[:19], fmt))
        except Exception:                                        # noqa: BLE001
            continue
    return None


def _norm(text):
    """Whitespace-collapsed, because the board wraps and the row does not."""
    return re.sub(r'\s+', ' ', text or '').strip()


def section(board_text, label):
    """The board's `## <label>` section, or '' if it has none."""
    if not board_text:
        return ''
    m = re.search(r'^##\s+%s\s*$' % re.escape(label), board_text,
                  re.MULTILINE)
    if not m:
        return ''
    rest = board_text[m.end():]
    nxt = re.search(r'^##\s+\S', rest, re.MULTILINE)
    return rest[:nxt.start()] if nxt else rest


# ── THE PURE CORE. Everything below the fixtures drives THIS. ───────────────
def classify(row, board_text, latest_text, published_epoch, nonce=None,
             label=None, now=None):
    """-> (findings, notes). Pure: no filesystem, no clock except `now`."""
    findings, notes = [], []
    label = label or (row or {}).get('session') or '?'
    now = float(now if now is not None else time.time())

    if not row:
        findings.append('%s: no registry row at all. That is NOT idle -- it is '
                        'an agent that has never written to the registry, and '
                        'the board says so in its own words.' % label)
        return findings, notes

    sec = section(board_text, label)
    if not sec:
        findings.append('%s: the board has no `## %s` section, so the row is '
                        'not rendered anywhere a reader would look.'
                        % (label, label))
    state = (row.get('state') or '').strip()
    stamp = (row.get('updated') or '').strip()
    task = _norm(row.get('task'))

    for name, text in (('board section', sec), ('latest file', latest_text)):
        if not text:
            continue
        if state and state not in text:
            findings.append('%s: the row says state %r and the %s does not '
                            'carry that word. The published view and the live '
                            'row disagree about the one field every reader '
                            'checks first.' % (label, state, name))
        if stamp and stamp not in text:
            findings.append('%s: the %s does not carry the row\'s own `updated` '
                            'stamp %s. A board rendering an OLDER write is '
                            'well-formed and plausible, which is why this is '
                            'the field that has to match.'
                            % (label, name, stamp))
        if task:
            head = ' '.join(task.split(' ')[:8])
            if head and head not in _norm(text):
                findings.append('%s: the %s does not carry the first words of '
                                'the row\'s task (%r).' % (label, name, head))

    if published_epoch is None:
        notes.append('%s: the published file has no readable timestamp, so '
                     'FRESHNESS was not checked -- said here rather than '
                     'counted as fresh.' % label)
    else:
        row_e = _epoch(stamp)
        if row_e is None:
            notes.append('%s: the row\'s `updated` value %r could not be '
                         'parsed, so FRESHNESS was not checked.'
                         % (label, stamp))
        elif published_epoch < row_e - STALE_TOLERANCE_S:
            findings.append(
                '%s: STALE BRIDGE. The row was written %s and the published '
                'file is %.1f minute(s) OLDER than that. The board is '
                'rendering a write that has been superseded, and nothing in '
                'the board itself can say so.'
                % (label, stamp, (row_e - published_epoch) / 60.0))

    if nonce:
        if nonce not in json.dumps(row, default=str):
            findings.append('%s: the nonce %r is not in the registry row, so '
                            'the WRITE did not land -- this is a finding about '
                            'sairn_status.py, not about the board.'
                            % (label, nonce))
        else:
            for name, text in (('board section', sec),
                               ('latest file', latest_text)):
                if text is None:
                    continue
                if nonce not in text:
                    findings.append(
                        '%s: the nonce %r IS in the registry row and is NOT in '
                        'the %s. The registry accepted this write and the '
                        'bridge did not carry it.' % (label, nonce, name))
    return findings, notes


# ── THE CRITERIA LOCK, IN BOTH DIRECTIONS ──────────────────────────────────
def run_fixtures():
    print('STATUS/BOARD BRIDGE -- criteria lock %s' % CRITERIA_VERSION)
    bad = total = 0

    def check(name, got, want):
        nonlocal bad, total
        total += 1
        ok = (bool(got) == bool(want))
        if not ok:
            bad += 1
        print('  %s %-66s findings=%s'
              % ('ok  ' if ok else 'FAIL', name,
                 len(got) if isinstance(got, list) else got))

    STAMP = '2026-10-17T11:06:02'
    E = _epoch(STAMP)
    ROW = {'session': 'cc', 'state': 'working', 'updated': STAMP,
           'task': 'b17: the bridge, the hint and two index rows'}
    BOARD = ('# SAIRN board\n\n## hank\n\n- **state:** idle\n\n## cc\n\n'
             '- **state:** working (liveness LIVE, row written %s, 0.1h old)\n'
             '- **task:** b17: the bridge, the hint and two index rows\n\n'
             '## cody\n\n- **state:** idle\n' % STAMP)
    LATEST = ('# SAIRN latest -- cc\n\n- **state:** working (liveness LIVE, '
              'row %s)\n- **task:** b17: the bridge, the hint and two index '
              'rows\n' % STAMP)

    f, _n = classify(ROW, BOARD, LATEST, E, now=E + 10)
    check('a row rendered by a fresh board validates', f, False)

    f, _n = classify(None, BOARD, LATEST, E, label='H3', now=E)
    check('NO REGISTRY ROW is a finding, not an idle agent', f, True)

    f, _n = classify(ROW, BOARD.replace('## cc', '## ccx'), LATEST, E, now=E)
    check('a board with no section for the agent is a finding', f, True)

    f, _n = classify(ROW, BOARD.replace('working (liveness', 'idle (liveness'),
                     LATEST, E, now=E)
    check('a STATE the board disagrees with is a finding', f, True)

    old = '2026-10-17T09:00:00'
    f, _n = classify(ROW, BOARD.replace(STAMP, old), LATEST.replace(STAMP, old),
                     _epoch(old), now=E)
    check('a board rendering an OLDER write is a finding -- the whole point, '
          'and it is well-formed either way', f, True)

    f, _n = classify(ROW, BOARD, LATEST, _epoch(old), now=E)
    check('...and a board whose TEXT matches but whose FILE is hours older is '
          'ALSO a finding', f, True)

    f, _n = classify(ROW, BOARD, LATEST, _epoch(STAMP) - STALE_TOLERANCE_S + 5,
                     now=E)
    check('...but a file a few seconds behind the row is NOT -- the publisher '
          'writes after the row and a tight bound would cry wolf', f, False)

    f, _n = classify(ROW, BOARD, LATEST, E,
                     nonce='NONCE-abc123', now=E)
    check('a nonce in NEITHER end is a finding about the WRITE', f, True)
    f, _ = classify(ROW, BOARD, LATEST, E, nonce='NONCE-abc123', now=E)
    check('...and that finding names sairn_status.py rather than the board',
          any('did not land' in x for x in f), True)

    ROWN = dict(ROW, task=ROW['task'] + ' NONCE-abc123')
    f, _n = classify(ROWN, BOARD, LATEST, E, nonce='NONCE-abc123', now=E)
    check('a nonce in the ROW but not in the published files is a finding '
          'about the BRIDGE', f, True)
    f, _ = classify(ROWN, BOARD, LATEST, E, nonce='NONCE-abc123', now=E)
    check('...and that finding says the registry accepted it and the bridge '
          'did not carry it',
          any('bridge did not carry' in x for x in f), True)

    BN = BOARD.replace('two index rows', 'two index rows NONCE-abc123')
    LN = LATEST.replace('two index rows', 'two index rows NONCE-abc123')
    f, _n = classify(ROWN, BN, LN, E, nonce='NONCE-abc123', now=E)
    check('a nonce present at BOTH ends validates -- the positive direction, '
          'without which this passes by refusing everything', f, False)

    f, notes = classify(ROW, BOARD, LATEST, None, now=E)
    check('an unreadable file timestamp is a NOTE, not a pass and not a '
          'finding', notes, True)
    check('...and no finding is invented from it', f, False)

    f, notes = classify(dict(ROW, updated='not a date'), BOARD, LATEST, E,
                        now=E)
    check('an unparseable row stamp is reported rather than treated as fresh',
          notes, True)

    print('  %d/%d fixtures classify correctly' % (total - bad, total))
    return EXIT_FINDING if bad else EXIT_CLEAN


# ── THE LIVE READ ──────────────────────────────────────────────────────────
def live(agents=None, nonce=None):
    try:
        import sairn_status as ST
        import sairn_board_publish as BP
    except Exception as exc:                                     # noqa: BLE001
        print('COULD NOT RUN: %s. This tool compares two other tools and '
              'cannot substitute for either.' % exc)
        return EXIT_COULD_NOT_RUN

    entries, problem = ST.read_all()
    if problem:
        print('COULD NOT RUN: the status registry could not be read (%s). An '
              'unreadable registry is not an empty one.' % problem)
        return EXIT_COULD_NOT_RUN
    rows = {e.get('session'): e for e in (entries or [])}

    ddir = BP.drive_dir() if hasattr(BP, 'drive_dir') else None
    if not ddir:
        try:
            import drive_upload_verify as DUV
            ddir = DUV.DRIVE_DEFAULT
        except Exception:                                        # noqa: BLE001
            ddir = None
    if not ddir or not os.path.isdir(ddir):
        print('COULD NOT RUN: the Drive mount directory (%r) is not readable, '
              'so NOTHING is known about what is published. This is the third '
              'state, not a pass.' % ddir)
        return EXIT_COULD_NOT_RUN

    board_path = os.path.join(ddir, BP.BOARD_NAME)
    try:
        board_text = io.open(board_path, encoding='utf-8',
                             errors='replace').read()
        board_epoch = os.path.getmtime(board_path)
    except OSError as exc:
        print('COULD NOT RUN: %s could not be read (%s).' % (board_path, exc))
        return EXIT_COULD_NOT_RUN

    print('STATUS/BOARD BRIDGE -- criteria %s' % CRITERIA_VERSION)
    print('  registry : %s' % os.path.dirname(
        (list(rows.values()) or [{}])[0].get('path', '') or ''))
    print('  mount    : %s' % ddir)
    print('  board    : %s  (%d bytes, mtime %s)'
          % (BP.BOARD_NAME, len(board_text),
             time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(board_epoch))))
    if getattr(BP, 'BOARD_DRIVE_FILE_ID', ''):
        print('  board Drive id (for an API read, which the mount CANNOT '
              'substitute for): %s' % BP.BOARD_DRIVE_FILE_ID)
    if nonce:
        print('  nonce    : %s' % nonce)
    print('')

    labels = [l for l in BP.BOARD_ORDER
              if not agents or BP.BOARD_TOKEN[l] in agents or l in agents]
    all_f, all_n, checked = [], [], 0
    for label in labels:
        token = BP.BOARD_TOKEN[label]
        row = rows.get(token)
        if row is None:
            for sp in getattr(BP.DUV, 'ALIASES', {}).get(token, ()):
                if sp in rows:
                    row = rows[sp]
                    break
        lp = os.path.join(ddir, BP.LATEST_NAME % label)
        latest_text, latest_epoch = None, None
        try:
            latest_text = io.open(lp, encoding='utf-8', errors='replace').read()
            latest_epoch = os.path.getmtime(lp)
        except OSError:
            all_n.append('%s: %s is not on the mount, so only the board half '
                         'was compared.' % (label, BP.LATEST_NAME % label))
        pub = min(x for x in (board_epoch, latest_epoch) if x is not None)
        f, n = classify(row, board_text, latest_text, pub,
                        nonce=nonce if (agents and token in agents) else None,
                        label=label)
        checked += 1
        state = (row or {}).get('state', 'NO ROW')
        print('  %-5s %-8s %s' % (label, state,
                                  'ok' if not f else '%d FINDING(S)' % len(f)))
        for x in f:
            print('      ! %s' % x)
        for x in n:
            print('      ? %s' % x)
        all_f += f
        all_n += n

        # THE DUPLICATE-COPY NOTE. The sync mount makes `SAIRN-latest-H1
        # (3).md` when two writers race, and a reader who opens one gets a
        # stale board with no sign that it is stale. Reported, not fixed:
        # these are other agents' files.
        dups = [fn for fn in os.listdir(ddir)
                if re.match(r'^%s \(\d+\)\.md$'
                            % re.escape((BP.LATEST_NAME % label)[:-3]), fn)]
        if dups:
            all_n.append('%s: the mount also carries %d numbered COPY(ies) of '
                         'its latest file (%s). A reader who opens one gets a '
                         'board with no sign it is superseded.'
                         % (label, len(dups), ', '.join(sorted(dups)[:3])))
            print('      ? %d numbered duplicate(s) of %s on the mount'
                  % (len(dups), BP.LATEST_NAME % label))

    print('')
    if all_f:
        print('%d FINDING(S) across %d agent(s).' % (len(all_f), checked))
    else:
        print('CLEAN: every row checked is rendered by a board no older than '
              'the row itself%s.' % (', and the nonce crossed both ends'
                                     if nonce else ''))
    if all_n:
        print('%d NOTE(S), not folded into that verdict:' % len(all_n))
        for x in all_n:
            print('  ? %s' % x)
    print('')
    print('LIMIT: the mount proves bytes are in the sync set. A Drive-side API '
          'read of the board file id above is the only thing that proves '
          'Google acknowledged them, and this tool cannot make one.')
    return EXIT_FINDING if all_f else EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv or '--selftest' in argv:
        return run_fixtures()
    # THE LOCK FIRST, as everywhere else in this repo: a comparator whose own
    # criteria are broken reports a clean bridge it never checked.
    if run_fixtures() != EXIT_CLEAN:
        print('')
        print('COULD NOT RUN: the criteria lock failed, so no verdict about '
              'the live bridge is trustworthy.')
        return EXIT_COULD_NOT_RUN
    print('')

    def opt(name):
        return argv[argv.index(name) + 1] if name in argv else None

    one = opt('--agent')
    return live(agents=[one] if one else None, nonce=opt('--nonce'))


if __name__ == '__main__':
    sys.exit(main())
