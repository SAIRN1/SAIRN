#!/usr/bin/env python
# OWNER: cc
# written 2026-10-17, batch b17 item 2 -- TIER 0 #1
"""Does the status registry actually reach the BOARD? Measured, not assumed.

    python tools/status_board_bridge_check.py                 # every agent
    python tools/status_board_bridge_check.py --agent cc
    python tools/status_board_bridge_check.py --nonce <token> --agent cc
    python tools/status_board_bridge_check.py --api-readback board-from-api.md
    python tools/status_board_bridge_check.py --api-published-at <stamp>
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

IT STILL CANNOT MAKE THE REQUEST, and that limit stays printed. What changed in
b18: the read is no longer compared BY EYE. Save what the API returned and pass
`--api-readback <path>`; the two are compared by sha256, a match is a note
naming the hash, a difference is a finding that says a republish between the
two reads is an ordinary cause and a single mismatch is a could-not-tell about
WHICH rather than a verdict, and no `--api-readback` at all is a note saying
the Drive-side half is still owed. A comparison by eye over a 17KB file was not
a comparison.
"""
import hashlib
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

CRITERIA_VERSION = '2026-10-19.1'

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
def selects(label, token, agents):
    """Is this board row selected by `--agent`? -> bool.

    ONE EXPRESSION, CALLED BY BOTH THE ROW FILTER AND THE NONCE GATE, and
    that is the whole fix. Until 2026-10-19 (b22) the same question was
    answered by two different expressions a hundred lines apart:

        labels = [... if BP.BOARD_TOKEN[l] in agents or l in agents]
        nonce  = nonce if (agents and token in agents) else None

    The first compares the LABEL ('H1') or the token ('h1'); the second
    compares the TOKEN ONLY. So `--agent H1` selected the row and then
    silently dropped the nonce, and the summary still printed `CLEAN ... and
    the nonce crossed both ends` because that sentence was keyed on a nonce
    having been SUPPLIED rather than CHECKED. H1 found it in its b63 and
    reproduced it with a never-written-nonce negative control: uppercase a
    false CLEAN, lowercase the correct FINDING, same registry, same board.

    Case-insensitive on both sides, because the board's own labels are mixed
    case ('H1', 'cc') and nobody typing `--agent H1` means a different agent
    from `--agent h1`.
    """
    if not agents:
        return True
    want = {str(a).strip().lower() for a in agents if str(a).strip()}
    return label.lower() in want or token.lower() in want


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
        elif published_epoch < row_e:
            # ── THE TOLERANCE IS NOT A BLIND SPOT ANY MORE (b18 item 2) ───
            # b17 shipped a 90-second tolerance and said so in its own
            # UNVERIFIED: "a board 30 seconds behind a write would not be
            # reported". That is a gap with a number on it, which is the one
            # kind that quietly widens -- the publisher getting slower, or a
            # mount flush taking longer, moves real staleness INSIDE the
            # window and nothing changes in the output. So the window is now
            # a NOTE rather than silence: inside it is not a finding, and it
            # is not nothing either.
            notes.append(
                '%s: the published file is %.1f second(s) behind the row, '
                'within the %d-second tolerance, so NOT a finding -- the '
                'publisher writes the file after the row. Reported because a '
                'tolerance nobody can see is a gap that widens without '
                'anybody noticing.'
                % (label, row_e - published_epoch, STALE_TOLERANCE_S))

    if nonce:
        if nonce not in json.dumps(row, default=str):
            # ── THIS REASON USED TO BE OVERSTATED (corrected cc b22) ───────
            # It said flatly "the WRITE did not land -- this is a finding
            # about sairn_status.py". MEASURED 2026-10-19 while re-driving
            # H1's b61 nonce through this tool: `H1-NONCE-1792420981` is
            # absent from H1's row AND present on the Drive mount in
            # SAIRN-handoff-H1-b61.md and SAIRN-report-H1-b61.txt. So that
            # write DID land; the row has simply been overwritten three
            # batches since. The verdict (nonce absent) was right and the
            # REASON was wrong, which is worse than a wrong verdict because
            # somebody acts on the reason.
            #
            # A row holds ONE task string, so this check cannot distinguish
            # "never written" from "written and since superseded". That is a
            # could-not-tell about WHICH, so both causes are named and the
            # one piece of evidence that separates them is printed.
            findings.append(
                '%s: the nonce %r is not in the registry row. TWO CAUSES AND '
                'THIS CANNOT TELL THEM APART: the write never landed (a '
                'finding about sairn_status.py), or it landed and the row has '
                'since been overwritten by a later batch -- a row holds one '
                'task string. The row\'s own `updated` stamp is %s; if that '
                'is later than the batch the nonce came from, the second '
                'cause is the ordinary one and this is not evidence against '
                'the original write. Check a nonce from the CURRENT batch to '
                'get an answer about the bridge.'
                % (label, nonce, stamp or 'absent'))
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


# ── CLOSING THE MOUNT-IS-NOT-THE-API GAP MECHANICALLY (b18 item 2) ─────────
# b17 said, correctly, that this tool cannot prove Google acknowledged the
# bytes -- only a Drive-side API read can, and only a chat turn or a human can
# make one. It then left the comparison to a reader's eye: somebody fetches the
# board through the API, looks at it, and says it matches.
#
# A COMPARISON BY EYE OVER A 17KB FILE IS NOT A COMPARISON. So the API read
# becomes a checkable artefact instead: save what the API returned to a file,
# pass --api-readback <path>, and the two are compared by sha256. The tool
# still cannot MAKE the request -- that limit is real and stays printed -- but
# the half a reader was doing badly is now done by the machine.
def compare_readback(mount_bytes, api_bytes, label='SAIRN-board.md'):
    """-> (findings, notes). Pure. Either argument may be None."""
    findings, notes = [], []
    if mount_bytes is None:
        findings.append('%s: the file on the MOUNT could not be read, so the '
                        'API copy has nothing to be compared against. That is '
                        'not a match.' % label)
        return findings, notes
    if api_bytes is None:
        notes.append('%s: no --api-readback given, so the Drive-side half is '
                     'still OWED. The mount proves the bytes are in the sync '
                     'set and nothing more.' % label)
        return findings, notes
    m = hashlib.sha256(mount_bytes).hexdigest()
    a = hashlib.sha256(api_bytes).hexdigest()
    if m == a:
        notes.append('%s: API read-back MATCHES the mount byte for byte, '
                     'sha256 %s. Google has acknowledged these bytes.'
                     % (label, m[:16]))
        return findings, notes
    # A DIFFERENCE IS NOT AUTOMATICALLY A FAILED UPLOAD. The mount's metadata
    # lags a revision, and a republish between the two reads is ordinary with
    # six agents writing. So the finding says what it is and what it is not.
    findings.append(
        '%s: the API copy and the mount copy DIFFER -- mount sha256 %s (%d '
        'bytes), API sha256 %s (%d bytes). Either the upload has not landed, '
        'or the board was republished between the two reads, which is '
        'ordinary with six agents writing. Re-read and compare again before '
        'calling it a failed upload; a single mismatch is a could-not-tell '
        'about WHICH, not a verdict.'
        % (label, m[:16], len(mount_bytes), a[:16], len(api_bytes)))
    return findings, notes


# ── THE SMALL VALUE THAT CROSSES THE CHAT BOUNDARY (b18 item 2) ────────────
# --api-readback wants a FILE, which means a chat turn has to materialise 17KB
# of base64 into the repo before anything can be compared -- so in practice it
# is used by a human with a browser and not by the turn that actually makes the
# API call. The board already carries one field that identifies its revision
# exactly: its own `Published at:` line. That is short enough to read out of an
# API response and paste, which makes it the comparison that will actually get
# made. Both forms exist on purpose; this is the one for the chat turn.
PUBLISHED_RE = re.compile(r'^-\s*\*\*Published at:\*\*\s*(\S+)', re.MULTILINE)


def published_at(board_text):
    """-> the board's own Published-at stamp, or ''."""
    m = PUBLISHED_RE.search(board_text or '')
    return m.group(1) if m else ''


def compare_published_at(mount_text, api_stamp):
    """-> (findings, notes). The API copy's revision against the mount's."""
    findings, notes = [], []
    if not api_stamp:
        return findings, notes
    mine = published_at(mount_text)
    if not mine:
        findings.append('the board on the mount carries no `Published at:` '
                        'line, so the API stamp %r has nothing to be compared '
                        'against. Not a match.' % api_stamp)
        return findings, notes
    if mine.strip() == api_stamp.strip():
        notes.append('API read-back is the SAME REVISION as the mount '
                     '(Published at %s). Google has acknowledged this '
                     'revision.' % mine)
        return findings, notes
    findings.append(
        'the API copy is a DIFFERENT REVISION: the mount says Published at %s '
        'and the API says %s. Drive\'s copy lagging by one revision is '
        'ordinary -- the mount\'s own metadata does too -- and so is another '
        'clone republishing between the two reads. Re-read before calling it '
        'a failed upload.' % (mine, api_stamp))
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
    check('...and that finding names sairn_status.py as ONE of the causes',
          any('finding about sairn_status.py' in x for x in f), True)
    # THE ARM THAT CORRECTS b17's WORDING (cc b22). The old text said flatly
    # "the WRITE did not land", and H1's b61 nonce is absent from the row AND
    # present on the mount in that batch's own handoff and report -- so that
    # write landed and the row was overwritten. A row holds one task string,
    # so this check cannot tell those apart and must not pick one.
    check('...and it ALSO names the overwritten-row cause, because a row '
          'holds ONE task string and this cannot distinguish "never written" '
          'from "written and since superseded"',
          any('since been overwritten' in x for x in f), True)
    check('...and it prints the row\'s own `updated` stamp, which is the one '
          'piece of evidence that separates the two causes',
          any(STAMP in x for x in f), True)
    check('ABLATION: the OLD wording asserted one cause with no evidence for '
          'it -- this arm fails on the pre-b22 text, which contained no '
          'stamp and no second cause',
          any(('since been overwritten' in x and STAMP in x) for x in f), True)

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

    # ── b18 item 2: THE TOLERANCE IS VISIBLE, AND THE API HALF IS CHECKED ──
    f, notes = classify(ROW, BOARD, LATEST, E - 30, now=E)
    check('a file INSIDE the tolerance is a NOTE, not a finding -- b17 left '
          'this silent and said so in its own UNVERIFIED', f, False)
    check('...and the note names the gap in seconds and the tolerance, so a '
          'window that widens is visible',
          any('within the %d-second tolerance' % STALE_TOLERANCE_S in n
              for n in notes), True)
    f, notes = classify(ROW, BOARD, LATEST, E + 30, now=E)
    check('a file NEWER than the row is neither -- the publisher writing after '
          'the row is the normal case and must stay quiet', (f, notes),
          ([], []))

    f, n = compare_readback(b'identical bytes', b'identical bytes')
    check('an API read-back matching the mount is a NOTE naming the sha, not a '
          'silent pass', (f, bool(n)), ([], True))
    f, n = compare_readback(b'the mount copy', b'a different copy')
    check('a DIFFERENT API copy is a finding', f, True)
    check('...and that finding does NOT call it a failed upload, because a '
          'republish between the two reads is ordinary',
          any('ordinary with six agents' in x for x in f), True)
    f, n = compare_readback(None, b'an api copy')
    check('an unreadable MOUNT copy is a finding -- an API copy with nothing '
          'to compare against is not a match', f, True)
    f, n = compare_readback(b'the mount copy', None)
    check('NO --api-readback is a NOTE saying the Drive-side half is still '
          'OWED, never a pass', (f, bool(n)), ([], True))
    check('...and that note says the mount proves only the sync set',
          any('sync set' in x for x in n), True)

    NL = chr(10)
    BOARD_PUB = (
        '# SAIRN board' + NL + NL +
        '- **Published at:** 2026-10-19T08:55:21 (local)' + NL +
        '- **Trigger:** claim change by fourth' + NL)
    check('the board\'s own Published-at stamp is readable',
          published_at(BOARD_PUB), '2026-10-19T08:55:21')
    f, n = compare_published_at(BOARD_PUB, '2026-10-19T08:55:21')
    check('the SAME revision at both ends is a note, not a finding',
          (f, bool(n)), ([], True))
    f, n = compare_published_at(BOARD_PUB, '2026-10-19T07:32:49')
    check('a DIFFERENT revision from the API is a finding', f, True)
    check('...and it names a lagging revision and a concurrent republish as '
          'ordinary causes rather than declaring a failed upload',
          any('ordinary' in x for x in f), True)
    f, n = compare_published_at('a board with no such line', '2026-10-19T08:55:21')
    check('a mount copy with no Published-at line is a finding, not a match',
          f, True)
    f, n = compare_published_at(BOARD_PUB, None)
    check('no --api-published-at is neither a finding nor a note -- the OWED '
          'note comes from the readback half, and saying it twice would read '
          'as two gaps', (f, n), ([], []))

    # ── H1's b63 NEGATIVE CONTROL, MADE PERMANENT (b22) ───────────────────
    # The defect: `--agent H1` selected the row and silently dropped the
    # nonce, so a nonce that was NEVER WRITTEN to the row still produced
    # CLEAN, while `--agent h1` on the same registry and the same board
    # produced the correct FINDING. These arms are that control, with the
    # live registry and the Drive mount replaced by the synthetic row and
    # board above so the control runs on any clone, forever, with no network.
    #
    # The arm that matters is not "uppercase works". It is that uppercase and
    # lowercase give the SAME ANSWER. A fixture asserting only the uppercase
    # verdict would pass again the day the two expressions drift apart in the
    # other direction.
    H1_ROW = {'session': 'h1', 'state': 'idle', 'updated': STAMP,
              'task': 'h1 b61: status-board bridge re-drive'}
    H1_BOARD = ('# SAIRN board\n\n## H1\n\n- **state:** idle (row written %s)\n'
                '- **task:** h1 b61: status-board bridge re-drive\n' % STAMP)
    NEVER_WRITTEN = 'H1-NONCE-NEVER-WRITTEN-b22-CONTROL'

    def _verdict(agents):
        """What live() would decide for the H1 row under this --agent value:
        is it selected, is the nonce actually used, and what does classify
        say. The two `selects` call sites, exercised together."""
        token = 'h1'
        picked = selects('H1', token, agents)
        used = NEVER_WRITTEN if (NEVER_WRITTEN and
                                 selects('H1', token, agents)) else None
        f, _ = classify(H1_ROW, H1_BOARD, None, E, nonce=used, label='H1',
                        now=E + 60)
        return picked, bool(used), len(f)

    up, low = _verdict(['H1']), _verdict(['h1'])
    check('THE b63 CONTROL: a nonce that was NEVER WRITTEN to the row is a '
          'FINDING under UPPERCASE --agent H1 (it was a false CLEAN)',
          up[2] >= 1, True)
    check('...and under lowercase --agent h1, which always worked',
          low[2] >= 1, True)
    check('...AND THE TWO ANSWERS ARE IDENTICAL, which is the arm that '
          'survives the next drift in either direction', up == low, True)
    check('the nonce is actually USED for an uppercase --agent, not dropped '
          'on the floor -- the precise mechanism of the false CLEAN',
          up[1], True)
    check('the row is selected by its board LABEL (H1)',
          selects('H1', 'h1', ['H1']), True)
    check('...and by its registry TOKEN (h1)',
          selects('H1', 'h1', ['h1']), True)
    # EVERY ARM BELOW IS A BOOLEAN, NOT A LIST. `check` compares
    # bool(got) == bool(want), so a non-empty list is True whatever is in it
    # -- `check(name, [False, False], [False, False])` passes vacuously. Two
    # arms were written that way minutes ago and caught before they landed.
    check('...and by either in any case (Cc, FOURTH, h2)',
          all((selects('cc', 'cc', ['Cc']),
               selects('fourth', 'fourth', ['FOURTH']),
               selects('H2', 'h2', ['h2']))), True)
    check('NO --agent selects every row, unchanged',
          all(selects(l, l.lower(), None)
              for l in ('hank', 'cc', 'cody', 'fourth', 'H1', 'H2')), True)
    check('AN UNRELATED --agent STILL SELECTS NOTHING -- case-insensitivity '
          'must not widen the filter into a match-anything',
          selects('H1', 'h1', ['cody']), False)
    check('...and a prefix of a real name is NOT a match either',
          any((selects('H1', 'h1', ['h']), selects('cc', 'cc', ['c']))),
          False)
    check('surrounding whitespace in --agent is tolerated rather than '
          'silently selecting nothing', selects('H1', 'h1', ['  H1 ']), True)
    check('an --agent that is only whitespace selects nothing, so live() '
          'reaches the COULD-NOT-RUN rather than checking every row',
          selects('H1', 'h1', ['   ']), False)

    print('  %d/%d fixtures classify correctly' % (total - bad, total))
    return EXIT_FINDING if bad else EXIT_CLEAN


# ── THE LIVE READ ──────────────────────────────────────────────────────────
def live(agents=None, nonce=None, api_readback=None,
         api_published_at=None):
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
              if selects(l, BP.BOARD_TOKEN[l], agents)]
    # AN --agent THAT MATCHES NOTHING IS NOT A CLEAN BRIDGE. Before b22 this
    # fell through to `0 FINDING(S) across 0 agent(s)` and then printed
    # CLEAN at exit 0 -- a verdict over an empty set, which is the same
    # silent-skip family as the nonce defect above and was found while
    # fixing it.
    if agents and not labels:
        print('COULD NOT RUN: --agent %r matches no board row, so NOTHING was '
              'compared. A verdict over an empty set is not a pass.'
              % (agents[0] if len(agents) == 1 else list(agents)))
        print('  valid names (either form, any case): %s'
              % ', '.join('%s/%s' % (l, BP.BOARD_TOKEN[l])
                          for l in BP.BOARD_ORDER))
        return EXIT_COULD_NOT_RUN
    all_f, all_n, checked = [], [], 0
    nonce_checked = 0
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
        # THE SAME `selects` AS THE ROW FILTER. Two expressions for one
        # question is the b63 defect; see selects().
        use_nonce = nonce if (nonce and selects(label, token, agents)) else None
        if use_nonce:
            nonce_checked += 1
        f, n = classify(row, board_text, latest_text, pub,
                        nonce=use_nonce, label=label)
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

    # ── THE DRIVE-SIDE HALF, COMPARED RATHER THAN EYEBALLED ───────────────
    api_bytes, api_why = None, ''
    if api_readback:
        try:
            api_bytes = io.open(api_readback, 'rb').read()
        except OSError as exc:
            api_why = ('--api-readback %r could not be read (%s), so the '
                       'Drive-side half was NOT checked. That is not a match.'
                       % (api_readback, exc))
    try:
        mount_bytes = io.open(board_path, 'rb').read()
    except OSError:
        mount_bytes = None
    if api_why:
        print('  ! %s' % api_why)
        all_f.append(api_why)
    else:
        rf, rn = compare_readback(mount_bytes, api_bytes, BP.BOARD_NAME)
        for x in rf:
            print('  ! %s' % x)
        all_f += rf
        all_n += rn
    sf, sn = compare_published_at(board_text, api_published_at)
    for x in sf:
        print('  ! %s' % x)
    for x in sn:
        print('  ? %s' % x)
    all_f += sf
    all_n += sn

    print('')
    if all_f:
        print('%d FINDING(S) across %d agent(s).' % (len(all_f), checked))
    else:
        # THE NONCE CLAUSE IS KEYED ON WHETHER ONE WAS CHECKED, NOT ON
        # WHETHER ONE WAS SUPPLIED. That substitution is what made the b63
        # defect READ as a verified pass: `--agent H1 --nonce X` printed the
        # nonce in the header, skipped the check, and then claimed it crossed.
        if nonce and not nonce_checked:
            print('CLEAN on the rows checked -- BUT THE NONCE WAS NOT '
                  'CHECKED ON ANY ROW, so this says nothing about whether '
                  'THIS write crossed. It should be unreachable since b22; '
                  'if you are reading it, the selection and the nonce gate '
                  'have drifted apart again.')
        else:
            print('CLEAN: every row checked is rendered by a board no older '
                  'than the row itself%s.'
                  % (', and the nonce crossed both ends on %d row(s)'
                     % nonce_checked if nonce_checked else ''))
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
    return live(agents=[one] if one else None, nonce=opt('--nonce'),
                api_readback=opt('--api-readback'),
                api_published_at=opt('--api-published-at'))


if __name__ == '__main__':
    sys.exit(main())
