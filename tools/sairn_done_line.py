#!/usr/bin/env python
# OWNER: cc
"""tools/sairn_done_line.py -- a builder's last step. Code produces the
`done b<n> <Drive id>` line, and a Stop hook refuses any other final message.

THE RULE IT ENFORCES (CLAUDE.md, "Batch deliverables"): the final chat message
is exactly `done b<n> <Drive file id of the digest>`, with nothing else on the
line. A rule kept by remembering it fails the way every other one has: an id
typed from memory, a filename in place of the id, or a paragraph after the
line. Two halves:

  python tools/sairn_done_line.py --batch b66
      The batch's last command. It REFUSES, printing NOT DONE and no done line
      (exit 2), unless ALL of the following hold:
        * this clone's identity marker names the agent;
        * SAIRN-handoff-<agent>-<b>.md, SAIRN-report-<agent>-<b>.txt and
          SAIRN-digest-<agent>-<b>.txt exist;
        * each of the three is on origin/main byte for byte, after a fetch:
          committed AND landed, not only written;
        * the handoff landed no later than the report ("handoff file before
          report"). Both are compared by the commit that first carried them;
        * tools/digest_lint.py passes the digest;
        * tools/drive_upload_verify.py uploads and verifies all three;
        * Drive for desktop's own metadata database names exactly one live
          file of that title in the SAIRN-status folder, with a real cloud id
          (not a local- placeholder). The wait for sync is bounded.
      It then records the line in <clone>/.git/sairn-done-line and prints it
      as the LAST line of its output.

  python <clone>/.git/sairn-hooks/sairn_done_line.py --stop-hook
      Wired as a Stop hook by tools/builder_hook_presence.py --install. When a
      done line was recorded AFTER the last human message, the turn may end
      only if the final assistant text is that line exactly. Any other text,
      including the line followed by a sentence, is refused (exit 2), and the
      refusal quotes the line to send. A record older than the last human
      message belongs to an earlier turn and is ignored. After 3 refusals in
      one turn it lets the stop through and says so on stderr, because a loop
      that never ends is worse than one wrong final line. The record says
      that happened.

WHY THE DRIVE ID COMES FROM THE DATABASE. The mount gives bytes, not ids. The
id is the Drive API's, and the only local holder of it is DriveFS's
metadata_sqlite_db (items.id, joined through stable_parents to the folder
DRIVE_FOLDER_ID). It is opened read-only. Checked against the API for cc b65:
1mxo9oBlTOvMz-BsmOLqtoxcXwweHiSyI on both sides.

    python tools/sairn_done_line.py --batch b<n> [--wait 180]
    python tools/sairn_done_line.py --stop-hook          # Stop-hook entry, payload on stdin
    python tools/sairn_done_line.py --selftest
"""
import datetime
import glob
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

CRITERIA_VERSION = '2026-10-29.cody-b66.1'   # + the unrecorded done-line refusal
DRIVE_FOLDER_ID = '14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09'     # = drive_upload_verify.DRIVE_FOLDER_ID
DRIVEFS_DB_GLOB = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'DriveFS', '*',
                               'metadata_sqlite_db')
MAX_STOP_REFUSALS = 3


def clone_root():
    here = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
    parts = here.split('/')
    return '/'.join(parts[:parts.index('.git')]) if '.git' in parts else os.path.dirname(here)


REPO = clone_root()
STATE = os.path.join(REPO, '.git', 'sairn-done-line')


class NotDone(Exception):
    pass


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def git(*args):
    return subprocess.run(['git', '-C', REPO] + list(args), capture_output=True, timeout=120)


def agent():
    try:
        return io.open(os.path.join(REPO, '.git', 'sairn-session'), encoding='utf-8').read().strip()
    except OSError as e:
        raise NotDone('this clone has no identity marker (.git/sairn-session): %s' % e)


def names(a, b):
    return ('SAIRN-handoff-%s-%s.md' % (a, b), 'SAIRN-report-%s-%s.txt' % (a, b),
            'SAIRN-digest-%s-%s.txt' % (a, b))


def landed(names_):
    """Every file is on origin/main byte for byte; the handoff landed no later
    than the report."""
    if git('fetch', '-q', 'origin').returncode != 0:
        raise NotDone('git fetch failed, so "landed" cannot be checked')
    first = {}
    for n in names_:
        try:
            local = io.open(os.path.join(REPO, n), 'rb').read()
        except OSError:
            raise NotDone('%s does not exist' % n)
        r = git('show', 'origin/main:%s' % n)
        if r.returncode != 0:
            raise NotDone('%s is not on origin/main -- commit and push it first' % n)
        if r.stdout.replace(b'\r\n', b'\n') != local.replace(b'\r\n', b'\n'):
            raise NotDone('%s on origin/main differs from the local file -- push the final version' % n)
        r = git('log', '--diff-filter=A', '--format=%ct', 'origin/main', '--', n)
        ts = [int(x) for x in r.stdout.split()]
        first[n] = min(ts) if ts else None
    h, rep = first[names_[0]], first[names_[1]]
    if h is None or rep is None or h > rep:
        raise NotDone('the handoff did not land before (or with) the report: handoff %s, report %s' % (h, rep))


def run_tool(args, what):
    r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', args[0])] + args[1:],
                       capture_output=True, text=True, cwd=REPO, timeout=600)
    if r.returncode != 0:
        tail = '\n'.join((r.stdout + r.stderr).strip().splitlines()[-6:])
        raise NotDone('%s exited %d:\n%s' % (what, r.returncode, tail))


def drive_id(title, db_glob=DRIVEFS_DB_GLOB, folder=DRIVE_FOLDER_ID):
    """-> the one live cloud id for `title` in the folder, or None while it is
    not synced yet. Raises NotDone for ambiguity or an unreadable database."""
    dbs = glob.glob(db_glob)
    if len(dbs) != 1:
        raise NotDone('expected one DriveFS metadata database, found %d (%s)' % (len(dbs), db_glob))
    try:
        c = sqlite3.connect('file:' + dbs[0].replace(os.sep, '/') + '?mode=ro', uri=True, timeout=10)
        try:
            par = c.execute('select stable_id from items where id=?', (folder,)).fetchall()
            if len(par) != 1:
                raise NotDone('the SAIRN-status folder %s is not in the DriveFS database' % folder)
            rows = c.execute(
                'select i.id from items i join stable_parents p on p.item_stable_id = i.stable_id '
                'where p.parent_stable_id = ? and i.local_title = ? and i.trashed = 0 '
                'and i.is_tombstone = 0', (par[0][0], title)).fetchall()
        finally:
            c.close()
    except sqlite3.Error as e:
        raise NotDone('the DriveFS database could not be read: %s' % e)
    live = [r[0] for r in rows if r[0] and not r[0].startswith('local')]
    if len(live) > 1:
        raise NotDone('%d live files are titled %s in the folder: %s' % (len(live), title, live))
    return live[0] if live else None


def produce(batch, wait):
    if not (batch.startswith('b') and batch[1:].isdigit()):
        raise NotDone('--batch must look like b66, got %r' % batch)
    a = agent()
    ns = names(a, batch)
    landed(ns)
    run_tool(['digest_lint.py', ns[2]], 'digest_lint')
    run_tool(['drive_upload_verify.py', '--agent', a, '--batch', batch], 'drive_upload_verify')
    deadline = time.time() + wait
    fid = drive_id(ns[2])
    while fid is None and time.time() < deadline:
        time.sleep(5)
        fid = drive_id(ns[2])
    if fid is None:
        raise NotDone('%s has no cloud id after %ds: Drive has not synced it yet. Re-run.' % (ns[2], wait))
    line = 'done %s %s' % (batch, fid)
    with io.open(STATE, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps({'line': line, 'ts': now_utc(), 'agent': a, 'refusals': 0}) + '\n')
    return line


# ── STOP HOOK ───────────────────────────────────────────────────────────────
def last_turn(transcript_path):
    """-> (ts of the last HUMAN message or '', final assistant text). Final text
    is every assistant text block after the last user entry of any kind."""
    human_ts, final = '', []
    for ln in io.open(transcript_path, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(ln)
        except ValueError:
            continue
        typ, msg = o.get('type'), o.get('message') or {}
        content = msg.get('content')
        if typ == 'user':
            final = []
            is_tool = isinstance(content, list) and any(
                isinstance(b, dict) and b.get('type') == 'tool_result' for b in content)
            if not is_tool and not o.get('isMeta'):
                human_ts = o.get('timestamp') or human_ts
        elif typ == 'assistant' and isinstance(content, list):
            final.extend(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
    return human_ts, '\n'.join(final).strip()


def iso_to_z(ts):
    """Transcript timestamps carry milliseconds ('...T22:14:48.123Z'); the
    record does not. Compare on the second."""
    return (ts or '')[:19] + 'Z' if ts else ''


DONE_SHAPE = re.compile(r'^done\s+(b\d+)\s+\S+\s*$')


def unrecorded(payload, ts_key, batch):
    """A done-shaped final message that this tool did not produce this turn
    (cody b66): refused, capped like the recorded case so it cannot loop. The
    counter is keyed to the turn's human timestamp, so a new turn starts at 0."""
    side = STATE + '.unrecorded'
    try:
        seen = json.loads(io.open(side, encoding='utf-8').read())
    except (OSError, ValueError):
        seen = {}
    if seen.get('turn') != ts_key:
        seen = {'turn': ts_key, 'refusals': 0}
    seen['refusals'] += 1
    io.open(side, 'w', encoding='utf-8', newline='\n').write(json.dumps(seen) + '\n')
    if seen['refusals'] > MAX_STOP_REFUSALS:
        return 0, ('sairn_done_line Stop hook: an unrecorded done line was refused %d times; letting the '
                   'turn end so it cannot loop. Recorded in %s.' % (MAX_STOP_REFUSALS, side))
    return 2, ('REFUSED by sairn_done_line: the final message is shaped like a done line, but this tool '
               'did not produce one this turn, so its id was never checked against Drive. Run:\n'
               '  python tools/sairn_done_line.py --batch %s\nand send the line it prints.' % batch)


def stop_hook(payload):
    """-> (exit code, stderr text)."""
    tp = (payload or {}).get('transcript_path')
    try:
        rec = json.loads(io.open(STATE, encoding='utf-8').read())
    except (OSError, ValueError):
        rec = None
    if rec is None:
        if not tp or not os.path.isfile(tp):
            return 0, ''                                # no record and nothing to read: not a final step
        human_ts, final = last_turn(tp)
        m = DONE_SHAPE.match(final)
        return unrecorded(payload, human_ts, m.group(1)) if m else (0, '')
    if not tp or not os.path.isfile(tp):
        return 2, ('sairn_done_line Stop hook: a done line is recorded but the transcript could not '
                   'be read, so the final message cannot be checked. Send exactly:\n%s' % rec['line'])
    human_ts, final = last_turn(tp)
    if iso_to_z(human_ts) > rec['ts']:
        m = DONE_SHAPE.match(final)                     # recorded in an earlier turn
        return unrecorded(payload, human_ts, m.group(1)) if m else (0, '')
    if final == rec['line']:
        return 0, ''
    rec['refusals'] = rec.get('refusals', 0) + 1
    io.open(STATE, 'w', encoding='utf-8', newline='\n').write(json.dumps(rec) + '\n')
    if rec['refusals'] > MAX_STOP_REFUSALS:
        return 0, ('sairn_done_line Stop hook: final message still differs after %d refusals; letting '
                   'the turn end so it cannot loop. Recorded in %s.' % (MAX_STOP_REFUSALS, STATE))
    return 2, ('REFUSED by sairn_done_line: the batch is closed and the final message must be '
               'EXACTLY this line, with nothing before or after it:\n%s' % rec['line'])


# ── SELFTEST ────────────────────────────────────────────────────────────────
def selftest():
    import shutil
    import tempfile
    global STATE
    bad, n = [], [0]

    def arm(name, ok, got=None):
        n[0] += 1
        print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else '   got %r' % (got,)))
        if not ok:
            bad.append(name)

    t = tempfile.mkdtemp(prefix='done-line-')
    real_state = STATE
    try:
        STATE = os.path.join(t, 'sairn-done-line')
        tp = os.path.join(t, 'transcript.jsonl')

        def transcript(*entries):
            with io.open(tp, 'w', encoding='utf-8') as fh:
                for e in entries:
                    fh.write(json.dumps(e) + '\n')

        def human(ts, text='go'):
            return {'type': 'user', 'timestamp': ts, 'message': {'content': text}}

        def tool_result(ts):
            return {'type': 'user', 'timestamp': ts, 'message': {'content': [{'type': 'tool_result', 'content': 'x'}]}}

        def said(text):
            return {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': text}]}}

        def tool_use():
            return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {}}]}}

        line = 'done b66 1AbCdEf'
        pl = {'transcript_path': tp}
        arm('no record -> the stop is not this hook\'s business', stop_hook(pl)[0] == 0)
        io.open(STATE, 'w').write(json.dumps({'line': line, 'ts': '2026-10-28T22:30:00Z', 'refusals': 0}))
        transcript(human('2026-10-28T22:00:00.000Z'), tool_use(), tool_result('2026-10-28T22:30:01.000Z'), said(line))
        arm('final text EXACTLY the line -> stop allowed', stop_hook(pl)[0] == 0, stop_hook(pl))
        transcript(human('2026-10-28T22:00:00.000Z'), tool_use(), tool_result('2026-10-28T22:30:01.000Z'),
                   said(line + '\nAll six items closed.'))
        rc, msg = stop_hook(pl)
        arm('the line PLUS a sentence -> refused, and the refusal quotes the line', rc == 2 and line in msg, (rc, msg))
        transcript(human('2026-10-28T22:00:00.000Z'), tool_use(), tool_result('2026-10-28T22:30:01.000Z'),
                   said('Batch closed.'), said(line))
        arm('a sentence BEFORE the line in the same turn -> refused', stop_hook(pl)[0] == 2)
        transcript(human('2026-10-28T22:00:00.000Z'), tool_use(), tool_result('2026-10-28T22:30:01.000Z'),
                   said('done b66 1AbCdEf.'))
        arm('a trailing period -> refused (exact means exact)', stop_hook(pl)[0] == 2)
        transcript(human('2026-10-28T22:00:00.000Z'), said('Narration.'), tool_use(),
                   tool_result('2026-10-28T22:30:01.000Z'), said(line))
        arm('text BEFORE the last tool call is not the final message -> allowed', stop_hook(pl)[0] == 0, stop_hook(pl))
        transcript(human('2026-10-28T22:00:00.000Z'), said(line), human('2026-10-28T22:45:00.000Z', 'next task'),
                   said('Working on it.'))
        arm('a record from an EARLIER turn is ignored -> allowed', stop_hook(pl)[0] == 0)
        io.open(STATE, 'w').write(json.dumps({'line': line, 'ts': '2026-10-28T22:30:00Z', 'refusals': 0}))
        transcript(human('2026-10-28T22:00:00.000Z'), said('chatter'))
        codes = [stop_hook(pl)[0] for _ in range(MAX_STOP_REFUSALS + 1)]
        arm('refused %d times, then let through so it cannot loop' % MAX_STOP_REFUSALS,
            codes == [2] * MAX_STOP_REFUSALS + [0], codes)
        arm('an unreadable transcript with a record -> refused, never silently allowed',
            stop_hook({'transcript_path': os.path.join(t, 'absent.jsonl')})[0] == 2)
        # A HAND-TYPED done line (cody b66). With no record this turn, a final
        # message shaped like a done line was waved through: an id written from
        # memory, or one copied from an earlier batch, ended the session as if
        # the tool had checked it.
        os.remove(STATE)
        transcript(human('2026-10-28T23:00:00.000Z'), said('done b67 1FromMemory'))
        rc, msg = stop_hook(pl)
        arm('a done-shaped final message with NO record -> refused, and the refusal names the tool',
            rc == 2 and 'sairn_done_line.py --batch b67' in msg, (rc, msg))
        io.open(STATE, 'w').write(json.dumps({'line': line, 'ts': '2026-10-28T22:30:00Z', 'refusals': 0}))
        transcript(human('2026-10-28T22:00:00.000Z'), said(line), human('2026-10-28T23:00:00.000Z', 'next batch'),
                   said('done b67 1FromMemory'))
        arm('a done-shaped final message whose only record is from an EARLIER turn -> refused',
            stop_hook(pl)[0] == 2, stop_hook(pl))
        os.remove(STATE)
        transcript(human('2026-10-28T23:00:00.000Z'), said('Done with the review; b67 is next.'))
        arm('ordinary prose that merely starts with "Done" -> not this hook\'s business', stop_hook(pl)[0] == 0)
        transcript(human('2026-10-28T23:10:00.000Z'), said('done b67 1FromMemory'))
        codes = [stop_hook(pl)[0] for _ in range(MAX_STOP_REFUSALS + 1)]
        arm('the unrecorded refusal is capped too, so it cannot loop', codes == [2] * MAX_STOP_REFUSALS + [0], codes)
        if os.path.exists(STATE + '.unrecorded'):
            os.remove(STATE + '.unrecorded')
        # DRIVE ID, against a database built to DriveFS's own column names
        db = os.path.join(t, 'acct', 'metadata_sqlite_db')
        os.makedirs(os.path.dirname(db))
        c = sqlite3.connect(db)
        c.execute('create table items (stable_id integer, id text, local_title text, trashed int, is_tombstone int)')
        c.execute('create table stable_parents (item_stable_id integer, parent_stable_id integer)')
        c.executemany('insert into items values (?,?,?,?,?)', [
            (1, 'FOLDER', 'SAIRN-status', 0, 0), (2, '1realId', 'SAIRN-digest-cc-b66.txt', 0, 0),
            (3, 'local-123', 'SAIRN-digest-cc-b67.txt', 0, 0), (4, '1old', 'SAIRN-digest-cc-b68.txt', 1, 0),
            (5, '1a', 'SAIRN-digest-cc-b69.txt', 0, 0), (6, '1b', 'SAIRN-digest-cc-b69.txt', 0, 0),
            (7, '1elsewhere', 'SAIRN-digest-cc-b70.txt', 0, 0)])
        c.executemany('insert into stable_parents values (?,?)', [(2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 99)])
        c.commit()
        c.close()
        g = os.path.join(t, '*', 'metadata_sqlite_db')
        arm('a synced file resolves to its cloud id', drive_id('SAIRN-digest-cc-b66.txt', g, 'FOLDER') == '1realId')
        arm('a local- placeholder is NOT an id (not synced yet -> None)', drive_id('SAIRN-digest-cc-b67.txt', g, 'FOLDER') is None)
        arm('a trashed file is not an id', drive_id('SAIRN-digest-cc-b68.txt', g, 'FOLDER') is None)
        try:
            drive_id('SAIRN-digest-cc-b69.txt', g, 'FOLDER')
            arm('two live files of one title -> NOT DONE, never a guess', False, 'returned')
        except NotDone:
            arm('two live files of one title -> NOT DONE, never a guess', True)
        arm('a same-title file in ANOTHER folder is not this one', drive_id('SAIRN-digest-cc-b70.txt', g, 'FOLDER') is None)
        try:
            drive_id('x', os.path.join(t, 'nowhere', '*'), 'FOLDER')
            arm('no DriveFS database -> NOT DONE', False, 'returned')
        except NotDone:
            arm('no DriveFS database -> NOT DONE', True)
        try:
            produce('66', 0)
            arm('a malformed --batch -> NOT DONE', False, 'produced')
        except NotDone:
            arm('a malformed --batch -> NOT DONE', True)
    finally:
        STATE = real_state
        shutil.rmtree(t, ignore_errors=True)
    print('SAIRN DONE LINE SELFTEST -- criteria %s -- %d arm(s), %d failed' % (CRITERIA_VERSION, n[0], len(bad)))
    return 1 if bad else 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    if '--stop-hook' in argv:
        try:
            payload = json.loads(sys.stdin.read() or '{}')
        except ValueError:
            payload = {}
        rc, msg = stop_hook(payload)
        if msg:
            sys.stderr.write(msg + '\n')
        return rc
    if '--batch' not in argv:
        print(__doc__)
        return 2
    wait = int(argv[argv.index('--wait') + 1]) if '--wait' in argv else 180
    try:
        if os.path.exists(STATE):
            os.remove(STATE)                            # a stale line must never be re-printed
        line = produce(argv[argv.index('--batch') + 1], wait)
    except NotDone as e:
        print('NOT DONE -- %s' % e)
        print('No done line was produced. Fix the above and re-run.')
        return 2
    print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
