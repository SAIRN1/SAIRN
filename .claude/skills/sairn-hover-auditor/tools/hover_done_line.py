#!/usr/bin/env python
"""hover_done_line.py -- the hover auditor's last step: CODE prints the final chat line
`done b<n> <Drive id of the digest>`, and a Stop hook refuses any other final message.
Built H1 b107. OWN IMPLEMENTATION: it shares no code with tools/sairn_done_line.py (cc's, the
builders'); it follows the same two-half pattern because the rule is the same, and differs where
this role's deliverables differ.

WHY A SEPARATE ONE. The builders' tool requires the deliverables to be committed and on origin/main.
This role's handoff, report and digest are UNTRACKED root files delivered through Drive (the log lives
outside the clone), so the evidence of 'landed' here is Drive, plus the chain, the mirror and git.
Auditor separation also means this role does not run a builder's tool to produce its own sign-off.

  python hover_done_line.py --batch b107 [--wait 180]
      Prints NOT DONE and a reason, exit 2, and NO done line, unless every one of these holds:
        1. SAIRN-handoff-H1-b<n>.md, SAIRN-report-H1-b<n>.txt, SAIRN-digest-H1-b<n>.txt exist, are
           non-empty and contain no angle bracket or ampersand (the Drive upload turns them into
           entities and the byte count drifts: b76);
        2. the digest is 30 lines or fewer and has a line starting with each of STATUS,
           DECISION-NEEDED, CHANGED, EVIDENCE-path, UNVERIFIED, NEXT (checked here, in this file's
           own code; the builders' digest linter is not run);
        3. Drive for desktop's metadata database holds exactly ONE live (not trashed, not tombstoned)
           file of each title in the SAIRN-status folder, with a real cloud id (not local-), and its
           size is the local byte count or that minus one trailing newline;
        4. the Drive mount holds the same BYTES (with or without the trailing newline): a same-size
           different file is caught here and not by (3);
        5. the handoff was uploaded no later than the report ('handoff file before report');
        6. the hash-chained log verifies (hover_log.py --verify) and the TIP-BEACON checkpoint on the
           mount names the log's last entry, i.e. the mirror push came AFTER the last entry;
        7. no claim of this role is still active;
        8. this clone has no commit that origin/main lacks, after a fetch.
      It then records the line in <clone>/.git/hover-done-line and prints it as the LAST line.

  python hover_done_line.py --stop-hook --clone DIR      (Stop-hook entry, payload on stdin)
      If a done line was recorded AFTER the last human message, the turn may end only if the final
      assistant text is that line exactly; anything else exits 2 and quotes the line. A record older
      than the last human message is ignored. After 3 refusals in one turn it lets the stop through
      and says so on stderr (a loop that never ends is worse than one wrong line); the record keeps
      the count.

  python hover_done_line.py --selftest

LIMITS, stated. (3) and (4) prove the files on Drive are the files here; they do not prove the
content is true. The Stop hook needs a line in .claude/settings.local.json, which this role's own
deny hook protects: installing it is Michael's. The snippet is printed by --print-settings.
"""
import datetime
import glob
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time

CRITERIA_VERSION = '2026-10-29.b107.1'
DRIVE_FOLDER_ID = '14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09'
MOUNT_DIR = 'G:/My Drive/SAIRN-status'
BEACON_REL = 'hover-chain-h1/TIP-BEACON.md'
DRIVEFS_GLOB = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'DriveFS', '*', 'metadata_sqlite_db')
LOG_PATH = os.path.expanduser('~/.claude/projects/C--Users-marsh-Documents-SAIRN-hover/hover-audit-log/hover-audit-log.jsonl')
LABELS = ('STATUS', 'DECISION-NEEDED', 'CHANGED', 'EVIDENCE-path', 'UNVERIFIED', 'NEXT')
MAX_DIGEST_LINES = 30
MAX_STOP_REFUSALS = 3
DEFECTS = set()          # selftest only: named checks switched off to prove each arm bites
HERE = os.path.dirname(os.path.abspath(__file__))


class NotDone(Exception):
    pass


def default_clone():
    d = HERE
    while d and not os.path.isdir(os.path.join(d, '.git')):
        up = os.path.dirname(d)
        if up == d:
            raise NotDone('no .git above %s; pass --clone DIR' % HERE)
        d = up
    return d


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def names(batch):
    return ('SAIRN-handoff-H1-%s.md' % batch, 'SAIRN-report-H1-%s.txt' % batch, 'SAIRN-digest-H1-%s.txt' % batch)


def config(clone):
    return {'clone': clone, 'drivefs_glob': DRIVEFS_GLOB, 'folder': DRIVE_FOLDER_ID, 'mount': MOUNT_DIR,
            'beacon': os.path.join(MOUNT_DIR, BEACON_REL), 'log': LOG_PATH,
            'claims': os.path.join(clone, '.claude', 'claims', 'hover.json'),
            'state': os.path.join(clone, '.git', 'hover-done-line'), 'verify': verify_chain, 'wait': 180}


# ---------------------------------------------------------------- checks
def read_local(clone, batch):
    out = {}
    for n in names(batch):
        p = os.path.join(clone, n)
        try:
            b = open(p, 'rb').read()
        except OSError:
            raise NotDone('%s does not exist in the clone' % n)
        if not b.strip():
            raise NotDone('%s is empty' % n)
        if 'no_entities' not in DEFECTS and any(c in b for c in (b'<', b'>', b'&')):
            raise NotDone('%s contains an angle bracket or ampersand; Drive upload would turn it into '
                          'an entity and the byte count would drift' % n)
        out[n] = b
    return out


def check_digest(b, n):
    lines = b.decode('utf-8', 'replace').splitlines()
    if 'digest_lines' not in DEFECTS and len(lines) > MAX_DIGEST_LINES:
        raise NotDone('%s has %d lines; the ceiling is %d' % (n, len(lines), MAX_DIGEST_LINES))
    if 'digest_labels' not in DEFECTS:
        for lab in LABELS:
            if not any(l.startswith(lab) for l in lines):
                raise NotDone('%s has no line starting with %s' % (n, lab))


def drive_items(cfg, title):
    """-> [(id, size, modified_ms)] for live items of this title in the folder."""
    dbs = glob.glob(cfg['drivefs_glob'])
    if len(dbs) != 1:
        raise NotDone('expected one DriveFS metadata database, found %d' % len(dbs))
    try:
        c = sqlite3.connect('file:' + dbs[0].replace(os.sep, '/') + '?mode=ro', uri=True, timeout=10)
        try:
            par = c.execute('select stable_id from items where id=?', (cfg['folder'],)).fetchall()
            if len(par) != 1:
                raise NotDone('the SAIRN-status folder is not in the DriveFS database')
            rows = c.execute(
                'select i.id, i.file_size, i.modified_date from items i join stable_parents p '
                'on p.item_stable_id = i.stable_id where p.parent_stable_id = ? and i.local_title = ? '
                'and i.trashed = 0 and i.is_tombstone = 0', (par[0][0], title)).fetchall()
        finally:
            c.close()
    except sqlite3.Error as e:
        raise NotDone('the DriveFS database could not be read: %s' % e)
    return rows


def sizes_ok(local):
    return {len(local), len(local[:-1]) if local.endswith(b'\n') else len(local)}


def drive_check(cfg, local, batch):
    """-> {title: (id, modified_ms)}; waits (bounded) for sync, raises NotDone otherwise."""
    got = {}
    deadline = time.time() + cfg['wait']
    pending = list(names(batch))
    while pending:
        n = pending[0]
        rows = drive_items(cfg, n)
        live = [r for r in rows if r[0] and not str(r[0]).startswith('local')]
        if len(rows) > 1 and 'one_live' not in DEFECTS:
            raise NotDone('%d live files are titled %s in the folder: %s' % (len(rows), n, [r[0] for r in rows]))
        if not live:
            if time.time() < deadline:
                time.sleep(2)
                continue
            raise NotDone('%s has no cloud id after %ds: Drive has not synced it' % (n, cfg['wait']))
        fid, size, mod = live[0]
        if 'size' not in DEFECTS and size not in sizes_ok(local[n]):
            raise NotDone('%s on Drive is %s bytes; local is %d (or %d without the trailing newline)'
                          % (n, size, len(local[n]), len(local[n]) - (1 if local[n].endswith(b'\n') else 0)))
        if 'bytes' not in DEFECTS:
            mp = os.path.join(cfg['mount'], n)
            try:
                mb = open(mp, 'rb').read()
            except OSError as e:
                raise NotDone('%s cannot be read from the Drive mount, so its bytes are unchecked: %s' % (n, e))
            if mb not in (local[n], local[n][:-1] if local[n].endswith(b'\n') else local[n]):
                raise NotDone('%s on the Drive mount has the same name and a DIFFERENT content' % n)
        got[n] = (fid, mod)
        pending.pop(0)
    return got


def verify_chain():
    r = subprocess.run([sys.executable, os.path.join(HERE, 'hover_log.py'), '--verify'],
                       capture_output=True, text=True, timeout=300)
    return r.returncode == 0 and 'VERIFIED' in r.stdout, (r.stdout or r.stderr).strip()[-120:]


def last_seq(log):
    last = None
    with open(log, encoding='utf-8') as fh:
        for ln in fh:
            if ln.strip():
                last = ln
    return json.loads(last)['seq']


def chain_checks(cfg):
    if 'chain' not in DEFECTS:
        ok, why = cfg['verify']()
        if not ok:
            raise NotDone('the hash-chained log did not verify: %s' % why)
    if 'beacon' not in DEFECTS:
        try:
            txt = open(cfg['beacon'], encoding='utf-8', errors='replace').read()
        except OSError as e:
            raise NotDone('the TIP-BEACON on the mount cannot be read: %s' % e)
        seq = None
        for ln in txt.splitlines():
            if ln.strip().startswith('checkpoint_seq'):
                seq = int(ln.split(':')[1].strip())
        if seq is None:
            raise NotDone('the TIP-BEACON has no checkpoint_seq')
        tip = last_seq(cfg['log'])
        if seq != tip:
            raise NotDone('the mirror beacon names entry %d but the log ends at %d: push the mirror again' % (seq, tip))


def claims_check(cfg):
    if 'claims' in DEFECTS:
        return
    try:
        d = json.load(open(cfg['claims'], encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise NotDone('the claim file cannot be read: %s' % e)
    live = [c.get('id') for c in d.get('claims', []) if c.get('status') != 'released']
    if live:
        raise NotDone('this role still holds claim(s): %s' % live)


def git_check(cfg):
    if 'git' in DEFECTS:
        return
    clone = cfg['clone']
    f = subprocess.run(['git', '-C', clone, 'fetch', '-q', 'origin'], capture_output=True, text=True, timeout=120)
    if f.returncode != 0:
        raise NotDone('git fetch failed, so "landed" cannot be checked: %s' % f.stderr.strip()[:100])
    r = subprocess.run(['git', '-C', clone, 'rev-list', '--count', 'origin/main..HEAD'],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or not r.stdout.strip().isdigit():
        raise NotDone('could not count commits ahead of origin/main')
    if int(r.stdout.strip()) != 0:
        raise NotDone('%s commit(s) are not on origin/main: push first' % r.stdout.strip())


def produce(batch, cfg):
    if not (batch.startswith('b') and batch[1:].isdigit()):
        raise NotDone('--batch must look like b107, got %r' % batch)
    local = read_local(cfg['clone'], batch)
    h, r, d = names(batch)
    check_digest(local[d], d)
    got = drive_check(cfg, local, batch)
    if 'order' not in DEFECTS and got[h][1] > got[r][1]:
        raise NotDone('the report was uploaded before the handoff (handoff file before report)')
    chain_checks(cfg)
    claims_check(cfg)
    cfg.get('git', git_check)(cfg)
    line ='done %s %s' % (batch, got[d][0])
    with io.open(cfg['state'], 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps({'line': line, 'ts': now_utc(), 'refusals': 0, 'criteria': CRITERIA_VERSION}) + '\n')
    return line


# ------------------------------------------------------------- stop hook
def last_turn(path):
    """-> (timestamp of the last HUMAN message or '', the assistant text since the last user entry)."""
    human, final = '', []
    for ln in io.open(path, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(ln)
        except ValueError:
            continue
        msg = o.get('message') or {}
        content = msg.get('content')
        if o.get('type') == 'user':
            final = []
            tool = isinstance(content, list) and any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in content)
            if not tool and not o.get('isMeta'):
                human = o.get('timestamp') or human
        elif o.get('type') == 'assistant' and isinstance(content, list):
            final.extend(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
    return human, '\n'.join(final).strip()


def stop_hook(payload, state):
    """-> (exit code, stderr text)."""
    try:
        rec = json.loads(io.open(state, encoding='utf-8').read())
    except (OSError, ValueError):
        return 0, ''
    tp = (payload or {}).get('transcript_path')
    if not tp or not os.path.isfile(tp):
        return 2, ('hover_done_line Stop hook: a done line is recorded but the transcript cannot be read, '
                   'so the final message cannot be checked. Send exactly:\n%s' % rec['line'])
    human, final = last_turn(tp)
    if (human or '')[:19] + 'Z' > rec['ts'] and human:
        return 0, ''
    if 'stop_compare' not in DEFECTS and final != rec['line']:
        rec['refusals'] = rec.get('refusals', 0) + 1
        io.open(state, 'w', encoding='utf-8', newline='\n').write(json.dumps(rec) + '\n')
        if rec['refusals'] > MAX_STOP_REFUSALS:
            return 0, ('hover_done_line Stop hook: still not the exact line after %d refusals; letting the '
                       'turn end so it cannot loop (recorded in %s)' % (MAX_STOP_REFUSALS, state))
        return 2, ('REFUSED by hover_done_line: the batch is closed and the final message must be EXACTLY '
                   'this line, nothing before or after it:\n%s' % rec['line'])
    return 0, ''


def settings_snippet(clone):
    cmd = 'python "%s" --stop-hook --clone "%s"' % (
        os.path.join(os.path.expanduser('~'), '.claude', 'projects', 'C--Users-marsh-Documents-SAIRN-hover',
                     'hover-audit-log', 'hover_done_line.py').replace('\\', '/'), clone.replace('\\', '/'))
    return json.dumps({'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': cmd}]}]}}, indent=2)


# --------------------------------------------------------------- selftest
def _fixture(root, batch='b9', digest_ok=True, real_git=False):
    """A fake clone with three deliverables, a DriveFS db, a mount, a log, a beacon and a claim file. Only the arms
    that test the git check pay for a real origin and clone; the rest use a bare directory and a no-op git check."""
    g = lambda *a, cwd=None: subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True, text=True)
    origin, clone = os.path.join(root, 'origin.git'), os.path.join(root, 'clone')
    if real_git:
        g('init', '-q', '--bare', '-b', 'main', origin)
        g('clone', '-q', origin, clone)
        open(os.path.join(clone, 'f.txt'), 'w').write('x')
        g('-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '.', cwd=clone)
        g('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'one', cwd=clone)
        g('push', '-q', 'origin', 'HEAD:main', cwd=clone)
        g('fetch', '-q', 'origin', cwd=clone)
    else:
        os.makedirs(os.path.join(clone, '.git'))
    h, r, d = names(batch)
    body = {h: '# handoff\nall good\n', r: 'REPORT\nall good\n',
            d: ('\n'.join(['H1 digest', 'STATUS: ok', 'DECISION-NEEDED: none', 'CHANGED: nothing',
                           'EVIDENCE-path: x', 'UNVERIFIED: y', 'NEXT: z']) if digest_ok else 'STATUS: only') + '\n'}
    mount = os.path.join(root, 'mount')
    os.makedirs(os.path.join(mount, 'hover-chain-h1'))
    for n, t in body.items():
        open(os.path.join(clone, n), 'w', newline='\n').write(t)
        open(os.path.join(mount, n), 'w', newline='\n').write(t[:-1])        # uploaded without the trailing newline
    db_dir = os.path.join(root, 'drivefs', 'acct')
    os.makedirs(db_dir)
    db = os.path.join(db_dir, 'metadata_sqlite_db')
    c = sqlite3.connect(db)
    c.execute('create table items (stable_id integer, id text, trashed int, file_size int, is_tombstone int, '
              'local_title text, modified_date int)')
    c.execute('create table stable_parents (item_stable_id integer, parent_stable_id integer, local_title_hash int)')
    c.execute("insert into items values (1, 'FOLDER', 0, 0, 0, 'SAIRN-status', 0)")
    for i, (n, t) in enumerate(body.items()):
        c.execute("insert into items values (?, ?, 0, ?, 0, ?, ?)", (10 + i, 'id-' + n[6:12], len(t) - 1, n, 1000 + i * 10))
        c.execute('insert into stable_parents values (?, 1, 0)', (10 + i,))
    c.commit()
    c.close()
    log = os.path.join(root, 'log.jsonl')
    open(log, 'w').write(json.dumps({'seq': 1}) + '\n' + json.dumps({'seq': 2}) + '\n')
    open(os.path.join(mount, 'hover-chain-h1', 'TIP-BEACON.md'), 'w').write('x\ncheckpoint_seq   : 2\n')
    os.makedirs(os.path.join(clone, '.claude', 'claims'))
    open(os.path.join(clone, '.claude', 'claims', 'hover.json'), 'w').write(json.dumps({'claims': [{'id': 'c1', 'status': 'released'}]}))
    cfg = {'clone': clone, 'drivefs_glob': os.path.join(root, 'drivefs', '*', 'metadata_sqlite_db'), 'folder': 'FOLDER',
           'mount': mount, 'beacon': os.path.join(mount, 'hover-chain-h1', 'TIP-BEACON.md'), 'log': log,
           'claims': os.path.join(clone, '.claude', 'claims', 'hover.json'),
           'state': os.path.join(clone, '.git', 'hover-done-line'), 'verify': lambda: (True, 'VERIFIED'), 'wait': 0}
    if not real_git:
        cfg['git'] = lambda c: None
    return cfg, db, body


def selftest():
    import shutil
    root = tempfile.mkdtemp(prefix='hover-done-selftest-')
    res = []

    def arm(name, ok):
        res.append((name, bool(ok)))
        print('  %s %s' % ('ok  ' if ok else 'FAIL', name))

    def fresh(**kw):
        d = tempfile.mkdtemp(dir=root)
        return _fixture(d, **kw) + (d,)

    def refuses(fn):
        try:
            fn()
            return False
        except NotDone:
            return True

    def mutate(db, sql, args=()):
        c = sqlite3.connect(db)
        c.execute(sql, args)
        c.commit()
        c.close()

    try:
        def arms():
            res.clear()
            cfg, db, body, d = fresh(real_git=True)
            line = produce('b9', cfg)
            arm('H1 a complete, uploaded, verified batch yields exactly: done b9 <the digest id>', line == 'done b9 id-digest')
            arm('H2 the record is written for the Stop hook', json.load(open(cfg['state']))['line'] == line)
            cfg, db, body, d = fresh()
            os.remove(os.path.join(cfg['clone'], names('b9')[1]))
            arm('H3 a missing report -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh(digest_ok=False)
            arm('H4 a digest missing five of the six labels -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            def resync(cfg, db, name, text):
                # change a deliverable EVERYWHERE (local, mount, Drive size) so only the check under test can refuse it
                open(os.path.join(cfg['clone'], name), 'w', newline='\n').write(text)
                open(os.path.join(cfg['mount'], name), 'w', newline='\n').write(text[:-1])
                mutate(db, 'update items set file_size = ? where local_title = ?', (len(text) - 1, name))
            cfg, db, body, d = fresh()
            resync(cfg, db, names('b9')[2], '\n'.join(['STATUS', 'DECISION-NEEDED', 'CHANGED', 'EVIDENCE-path',
                                                       'UNVERIFIED', 'NEXT'] + ['l%d' % i for i in range(30)]) + '\n')
            arm('H5 a digest over 30 lines, otherwise perfectly uploaded -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            resync(cfg, db, names('b9')[0], '# handoff\na < b\n')
            arm('H6 an angle bracket in a deliverable, otherwise perfectly uploaded -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            mutate(db, "insert into items values (99, 'dup-id', 0, 5, 0, ?, 1)", (names('b9')[2],))
            mutate(db, 'insert into stable_parents values (99, 1, 0)')
            arm('H7 two live files with the digest title -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            mutate(db, "update items set id = 'local-1' where local_title = ?", (names('b9')[2],))
            arm('H8 a local- placeholder id (not synced) -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            mutate(db, "update items set file_size = file_size + 3 where local_title = ?", (names('b9')[1],))
            arm('H9 a Drive size that is neither the local size nor one less -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            mp = os.path.join(cfg['mount'], names('b9')[1])
            t = open(mp).read()
            open(mp, 'w', newline='\n').write('X' + t[1:])
            arm('H10 the mount file has the SAME SIZE and different bytes -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            mutate(db, "update items set modified_date = 5000 where local_title = ?", (names('b9')[0],))
            arm('H11 the report uploaded before the handoff -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            open(cfg['log'], 'a').write(json.dumps({'seq': 3}) + '\n')
            arm('H12 the mirror beacon behind the log tip -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            cfg['verify'] = lambda: (False, 'BROKEN')
            arm('H13 a chain that does not verify -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            open(cfg['claims'], 'w').write(json.dumps({'claims': [{'id': 'c2', 'status': 'active'}]}))
            arm('H14 a claim still active -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh(real_git=True)
            subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'ahead'],
                           cwd=cfg['clone'], capture_output=True)
            arm('H15 a commit origin/main lacks -> NOT DONE', refuses(lambda: produce('b9', cfg)))
            cfg, db, body, d = fresh()
            mutate(db, "insert into items values (98, 'old-id', 1, 5, 0, ?, 1)", (names('b9')[2],))
            mutate(db, 'insert into stable_parents values (98, 1, 0)')
            arm('H16 CONTROL: a TRASHED duplicate title does not block (only live files count)',
                produce('b9', cfg) == 'done b9 id-digest')
            # stop hook
            cfg, db, body, d = fresh()
            line = produce('b9', cfg)
            tp = os.path.join(d, 't.jsonl')

            def tr(*entries):
                open(tp, 'w').write('\n'.join(json.dumps(e) for e in entries) + '\n')
            human = lambda ts: {'type': 'user', 'timestamp': ts, 'message': {'content': 'go'}}
            said = lambda t: {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': t}]}}
            old = '2000-01-01T00:00:00.000Z'
            tr(human(old), said(line))
            arm('S1 final message == the line -> allowed', stop_hook({'transcript_path': tp}, cfg['state'])[0] == 0)
            tr(human(old), said(line + ' done.'))
            code, msg = stop_hook({'transcript_path': tp}, cfg['state'])
            arm('S2 the line plus a sentence -> refused, the refusal quotes the line', code == 2 and line in msg)
            tr(human(old), said('chatter'))
            arm('S3 narration instead of the line -> refused', stop_hook({'transcript_path': tp}, cfg['state'])[0] == 2)
            arm('S4 an unreadable transcript with a record -> refused (never silently allowed)',
                stop_hook({'transcript_path': os.path.join(d, 'absent.jsonl')}, cfg['state'])[0] == 2)
            tr(human('2999-01-01T00:00:00.000Z'), said('next task text'))
            arm('S5 a record older than the last human message is ignored', stop_hook({'transcript_path': tp}, cfg['state'])[0] == 0)
            tr(human(old), said('chatter'))
            rec6 = json.load(open(cfg['state']))
            rec6['refusals'] = 0          # S2 and S3 above already spent refusals on this record
            open(cfg['state'], 'w').write(json.dumps(rec6) + '\n')
            outs = [stop_hook({'transcript_path': tp}, cfg['state'])[0] for _ in range(5)]
            arm('S6 after the 3rd refusal it lets the stop through (no endless loop)', outs[:3] == [2, 2, 2] and outs[-1] == 0)
            cfg2, _, _, d2 = fresh()
            arm('S7 CONTROL: no record at all -> allowed (not a final step)', stop_hook({'transcript_path': tp}, cfg2['state'])[0] == 0)
            return list(res)

        base = arms()
        fails = [n for n, ok in base if not ok]
        print('ARMS: %d, clean run: %d failed' % (len(base), len(fails)))
        rc = 1 if fails else 0
        for flag in ('no_entities', 'digest_lines', 'digest_labels', 'one_live', 'size', 'bytes', 'order',
                     'chain', 'beacon', 'claims', 'git', 'stop_compare'):
            DEFECTS.clear()
            DEFECTS.add(flag)
            red = [n for n, ok in arms() if not ok]
            print('PLANTED %-13s -> %d arm(s) red%s' % (flag, len(red), '' if red else '   <-- UNGUARDED: nothing turned red'))
            if not red:
                rc = 1
        DEFECTS.clear()
    finally:
        DEFECTS.clear()
        shutil.rmtree(root, ignore_errors=True)
    print('SELFTEST', 'PASS' if rc == 0 else 'FAIL')
    return rc


def main(argv):
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default
    if '--selftest' in argv:
        return selftest()
    try:
        clone = opt('--clone') or default_clone()
        if '--print-settings' in argv:
            print(settings_snippet(clone))
            return 0
        if '--stop-hook' in argv:
            raw = sys.stdin.read()
            try:
                payload = json.loads(raw) if raw.strip() else {}
            except ValueError:
                payload = {}
            code, err = stop_hook(payload, config(clone)['state'])
            if err:
                sys.stderr.write(err + '\n')
            return code
        if '--batch' in argv:
            cfg = config(clone)
            cfg['wait'] = int(opt('--wait', 180))
            print(produce(opt('--batch'), cfg))
            return 0
    except NotDone as e:
        print('NOT DONE: %s' % e)
        return 2
    print('usage: --batch b<n> [--wait S] | --stop-hook --clone DIR | --print-settings | --selftest')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
