#!/usr/bin/env python
# OWNER: cc
"""tools/sairn_watchdog.py -- a standalone watchdog over the four build agents.
It FLAGS and writes a findings file. It fixes nothing and decides nothing.

Built by cc in b67 on Michael's instruction: "You build it, you don't operate
it." It is not wired into any hook, gate or schedule.

SCHEDULED (cc b71, Michael's instruction): Windows Task Scheduler task
"SAIRN-watchdog" runs it every 15 minutes through
~/SAIRN-SESSION-LOCKS/watchdog-run.cmd, which passes
--repo "G:\\My Drive\\SAIRN-status". It therefore reads each agent's latest
DRIVE handoff and digest, and takes the landing time from the file mtime
because there is no git there. The task's "Last Result" is THIS tool's exit
code: 1 means findings were written, not that the run failed. Liveness is the
findings file's own generated_utc. It never messages, pauses or touches an
agent.

OPERATOR: hank (Michael's decision, 2026-10-29, cc b69 item 1). hank runs
`python tools/sairn_watchdog.py` at the START of each of its own batches,
before touching shared config. Findings land in the same file every time,
~/SAIRN-SESSION-LOCKS/watchdog-findings.json. cc OWNS the tool and fixes it;
hank OPERATES it and acts on or routes what it flags.

INPUTS, all read at run time and never cached:
  * the shared status registry, ~/SAIRN-SESSION-LOCKS/status/<agent>.json:
    state, task, `updated`, and the `claims` list mirrored there by
    tools/sairn_claim.py. It is outside every clone, so it is current without
    a fetch;
  * each agent's LATEST handoff in the repo root, SAIRN-handoff-<agent>-b<N>.md,
    with the highest N compared as a NUMBER, and the same batch's digest for
    its NEXT line.

FOUR FLAGS, each carrying its evidence:
  OVERLAP      two agents hold ACTIVE claims whose declared FILES intersect,
               either the same path or one a directory prefix of the other.
               Exact and mechanical. A claim that declares no files cannot
               overlap anything, and the agents holding one are LISTED, never
               silently passed: "no files declared" is not "no overlap".
  STALE-CLAIM  the agent's last handoff says its claims were released, or
               that it holds none, but the registry still shows an ACTIVE
               claim made BEFORE that handoff landed. That is the claim/handoff
               mismatch that can be stated without judgement.
  REGISTRY-BEHIND  the row's task names an OLDER batch than the agent's own
               last handoff, at any state (added cc b68 after the first live run
               read two such rows as clean).
  NEXT-DRIFT   the registry row was updated AFTER the handoff and the agent
               is working, yet its task shares no significant word with the
               handoff's stated NEXT step. Or the row was NOT updated since
               the handoff while it still says working. This one is a
               HEURISTIC, and every finding says so in its text. On this
               platform a word-overlap judgement once scored 38%, with five
               false positives out of five (CLAUDE.md, the claim tool's own
               note). It is a prompt for a human to read both, never a
               verdict.

FAILS CLOSED, PR SS1.11. A registry row or handoff that cannot be read is a
COULD-NOT-CHECK entry in the file, exit 2, never a clean pass. An agent with
no handoff at all is COULD-NOT-CHECK for the two flags that need one. Exit:
0 nothing flagged, 1 findings, 2 something could not be checked (findings
still written).

    python tools/sairn_watchdog.py [--out PATH] [--locks DIR] [--repo DIR]
    python tools/sairn_watchdog.py --selftest

Default --out: ~/SAIRN-SESSION-LOCKS/watchdog-findings.json. That is outside
every clone and next to the registry it reads, so all six clones and the
board publisher can read it.
"""
import calendar
import datetime
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

CRITERIA_VERSION = '2026-10-29.b68.1'
EXIT_OK, EXIT_FINDING, EXIT_COULD_NOT = 0, 1, 2
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCKS = os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS')
AUDITOR_RE = re.compile(r'^hover[0-9]*$')
RELEASED_RE = re.compile(r'released with this handoff|claims? held\W{0,6}(?:\*\*)?\s*none|no claims? (?:held|needed)'
                         r'|holds nothing|claims held\s*\|\s*none', re.I)
STOP = set('that this with from into have been will should their there which while would about after before '
           'then than them they what when where also only just each next batch item items done open none'.split())


def utc_epoch(iso):
    """'2026-10-28T23:10:49Z' -> epoch. A registry `updated` has no Z and is
    LOCAL time (tools/sairn_status.py writes it so), read as local."""
    if not iso:
        return None
    s = iso.strip()
    try:
        if s.endswith('Z'):
            return calendar.timegm(time.strptime(s[:19], '%Y-%m-%dT%H:%M:%S'))
        return time.mktime(time.strptime(s[:19], '%Y-%m-%dT%H:%M:%S'))
    except ValueError:
        return None


def words(text):
    return set(w for w in re.findall(r'[a-z][a-z0-9_]{3,}', (text or '').lower()) if w not in STOP)


def agents(locks):
    d = os.path.join(locks, 'status')
    try:
        names = sorted(f[:-5] for f in os.listdir(d) if f.endswith('.json'))
    except OSError as e:
        raise SystemExit('COULD NOT RUN: the status registry %s cannot be listed (%s)' % (d, e))
    return [n for n in names if not AUDITOR_RE.match(n)]


def latest(repo, agent, kind):
    best = None
    for p in glob.glob(os.path.join(repo, 'SAIRN-%s-%s-b*.*' % (kind, agent))):
        m = re.search(r'-b(\d+)\.(?:md|txt)$', p)
        if m and (best is None or int(m.group(1)) > best[0]):
            best = (int(m.group(1)), p)
    return best


def landed_at(repo, path):
    """When the file first landed (git), else its mtime. -> (epoch, source)."""
    try:
        r = subprocess.run(['git', '-C', repo, 'log', '--diff-filter=A', '--format=%ct', '--',
                            os.path.relpath(path, repo)], capture_output=True, text=True, timeout=30)
        ts = [int(x) for x in r.stdout.split()] if r.returncode == 0 else []
        if ts:
            return min(ts), 'git'
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return os.path.getmtime(path), 'mtime'


def next_step(text):
    lines, out, on = text.splitlines(), [], False
    for ln in lines:
        if re.match(r'^NEXT\b', ln):
            on = True
            out.append(ln)
            continue
        if on:
            if re.match(r'^[A-Z][A-Z_-]+[:\s]', ln) and not ln.startswith((' ', '\t')):
                break
            out.append(ln)
    return '\n'.join(out).strip()


def overlap(a, b):
    a, b = a.strip('/'), b.strip('/')
    return a == b or a.startswith(b + '/') or b.startswith(a + '/')


def run(locks=LOCKS, repo=REPO, now=None):
    """-> (findings, could_not, notes)."""
    now = now or time.time()
    findings, could_not, notes, rows, hand = [], [], [], {}, {}
    for a in agents(locks):
        p = os.path.join(locks, 'status', a + '.json')
        try:
            rows[a] = json.loads(io.open(p, encoding='utf-8').read())
        except (OSError, ValueError) as e:
            could_not.append({'agent': a, 'what': 'registry row', 'why': '%s: %s' % (p, e)})
    for a in rows:
        h = latest(repo, a, 'handoff')
        if not h:
            could_not.append({'agent': a, 'what': 'STALE-CLAIM, NEXT-DRIFT', 'why': 'no SAIRN-handoff-%s-b<N> in %s' % (a, repo)})
            continue
        try:
            text = io.open(h[1], encoding='utf-8', errors='replace').read()
        except OSError as e:
            could_not.append({'agent': a, 'what': 'handoff', 'why': str(e)})
            continue
        dg = latest(repo, a, 'digest')
        dtext = ''
        if dg and dg[0] == h[0]:
            try:
                dtext = io.open(dg[1], encoding='utf-8', errors='replace').read()
            except OSError:
                dtext = ''
        at, src = landed_at(repo, h[1])
        hand[a] = {'batch': 'b%d' % h[0], 'path': os.path.basename(h[1]), 'landed': at, 'landed_source': src,
                   'released': bool(RELEASED_RE.search(text)), 'next': next_step(dtext) or next_step(text)}

    def active(a):
        return [c for c in (rows[a].get('claims') or []) if c.get('status') == 'active']

    # OVERLAP
    names = sorted(rows)
    no_files = sorted(set(a for a in names for c in active(a) if not c.get('files')))
    if no_files:
        notes.append('active claim(s) with NO files declared cannot be checked for overlap: %s' % ', '.join(no_files))
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for ca in active(a):
                for cb in active(b):
                    hit = sorted(set(fa for fa in (ca.get('files') or []) for fb in (cb.get('files') or [])
                                     if overlap(fa, fb)))
                    if hit:
                        findings.append({'flag': 'OVERLAP', 'agents': [a, b], 'paths': hit,
                                         'evidence': {a: ca.get('task'), b: cb.get('task')}})
    # STALE-CLAIM and NEXT-DRIFT
    for a in sorted(hand):
        h, row = hand[a], rows[a]
        if h['released']:
            for c in active(a):
                t = utc_epoch(c.get('claimed_at'))
                if t is not None and t < h['landed']:
                    findings.append({'flag': 'STALE-CLAIM', 'agents': [a], 'evidence': {
                        'handoff': h['path'], 'handoff_says': 'claims released / none held',
                        'handoff_landed_utc': datetime.datetime.fromtimestamp(h['landed'], datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'claim_still_active': c.get('task'), 'claimed_at': c.get('claimed_at')}})
        # REGISTRY-BEHIND (cc b68, found on the FIRST live run): the row's task
        # names an older batch than the agent's own last handoff. That is the
        # registry disagreeing with the handoff at ANY state. The first draft
        # only looked at `working` rows, so it read hank (task "b61", handoff
        # b63) and cody (task "b59", handoff b60) as clean.
        named = [int(x) for x in re.findall(r'\bb(\d+)\b', row.get('task') or '')]
        hb = int(h['batch'][1:])
        if named and max(named) < hb:
            findings.append({'flag': 'REGISTRY-BEHIND', 'agents': [a], 'heuristic': False, 'evidence': {
                'registry_task': row.get('task'), 'registry_state': row.get('state'),
                'registry_updated_local': row.get('updated'), 'task_names_batch': 'b%d' % max(named),
                'last_handoff': h['path']}})
        upd = utc_epoch(row.get('updated'))
        state = row.get('state')
        if upd is None:
            could_not.append({'agent': a, 'what': 'NEXT-DRIFT', 'why': 'registry row has no readable `updated`'})
            continue
        if state == 'working' and upd < h['landed']:
            findings.append({'flag': 'NEXT-DRIFT', 'agents': [a], 'heuristic': False, 'evidence': {
                'why': 'registry says working but was not updated since the last handoff landed',
                'registry_task': row.get('task'), 'registry_updated_local': row.get('updated'), 'handoff': h['path']}})
        elif state == 'working' and h['next'] and not (words(row.get('task')) & words(h['next'])):
            findings.append({'flag': 'NEXT-DRIFT', 'agents': [a], 'heuristic': True, 'evidence': {
                'why': 'HEURISTIC, read both: the working task shares no significant word with the stated NEXT',
                'registry_task': row.get('task'), 'stated_next': h['next'][:600], 'handoff': h['path']}})
    return findings, could_not, notes


def write(out, findings, could_not, notes, locks, repo):
    doc = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'criteria': CRITERIA_VERSION, 'inputs': {'registry': os.path.join(locks, 'status'), 'handoffs': repo},
           'findings': findings, 'could_not_check': could_not, 'notes': notes,
           'reads_as': 'FLAGS for a human. OVERLAP and STALE-CLAIM are mechanical; NEXT-DRIFT marked heuristic is a word-overlap '
                       'prompt (38% the last time this platform automated that judgement). Empty findings with a '
                       'non-empty could_not_check is NOT a clean run.'}
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = out + '.tmp'
    io.open(tmp, 'w', encoding='utf-8', newline='\n').write(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    os.replace(tmp, out)


# ── SELFTEST ────────────────────────────────────────────────────────────────
def selftest():
    import shutil
    import tempfile
    bad, n = [], [0]

    def arm(name, ok, got=None):
        n[0] += 1
        print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else '   got %r' % (got,)))
        if not ok:
            bad.append(name)

    t = tempfile.mkdtemp(prefix='watchdog-')
    try:
        locks, repo = os.path.join(t, 'locks'), os.path.join(t, 'repo')
        os.makedirs(os.path.join(locks, 'status'))
        os.makedirs(repo)
        T0 = 1793200000.0                                   # handoffs land here (mtime source)

        def iso(e):
            return datetime.datetime.fromtimestamp(e, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        def local(e):
            return time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(e))

        def row(a, state, task, updated, claims):
            io.open(os.path.join(locks, 'status', a + '.json'), 'w').write(json.dumps(
                {'session': a, 'state': state, 'task': task, 'updated': local(updated), 'claims': claims}))

        def handoff(a, nb, body, digest_next=None):
            p = os.path.join(repo, 'SAIRN-handoff-%s-b%d.md' % (a, nb))
            io.open(p, 'w').write(body)
            os.utime(p, (T0, T0))
            if digest_next is not None:
                io.open(os.path.join(repo, 'SAIRN-digest-%s-b%d.txt' % (a, nb)), 'w').write(
                    'DIGEST\nSTATUS: x\nNEXT: %s\nCONTEXT 1%%\n' % digest_next)

        def claim(task, files, at):
            return {'status': 'active', 'task': task, 'files': files, 'claimed_at': iso(at)}

        # aa and bb collide on a file through a directory prefix; aa's claim predates a "released" handoff.
        row('aa', 'working', 'fix the payroll export rounding', T0 + 600,
            [claim('payroll export', ['tools/payroll/'], T0 - 3600)])
        row('bb', 'working', 'renumber invoices', T0 + 600, [claim('invoices', ['tools/payroll/export.py'], T0 + 60)])
        row('cc', 'working', 'deploy the weather widget', T0 + 600, [claim('widget', None, T0 + 60)])
        row('dd', 'working', 'stale working row', T0 - 600, [])
        row('hover', 'working', 'auditor', T0 + 600, [claim('x', ['tools/payroll/export.py'], T0)])
        handoff('aa', 9, 'Claims held | none\n', digest_next='aa -- payroll export rounding fix')
        handoff('aa', 10, '# handoff aa b10\n| Claims | `payroll` (b10), released with this handoff. |\n',
                digest_next='aa -- payroll export rounding fix')
        handoff('bb', 3, 'Claims held: invoices\n', digest_next='bb -- renumber invoices for the audit')
        handoff('cc', 4, 'Claims held: widget\n', digest_next='cc -- review hank b63 Tier A obligation')
        handoff('dd', 1, 'nothing\n', digest_next='dd -- whatever')
        f, cn, notes = run(locks, repo)
        flags = [(x['flag'], tuple(x['agents'])) for x in f]
        arm('OVERLAP: a directory claim and a file inside it, across two agents, is flagged',
            ('OVERLAP', ('aa', 'bb')) in flags, flags)
        arm('OVERLAP: the AUDITOR row is not a build agent and is never paired', not any('hover' in x['agents'] for x in f), flags)
        arm('the LATEST handoff is taken by NUMBER (b10 over b9)',
            any(x['flag'] == 'STALE-CLAIM' and x['evidence']['handoff'].endswith('b10.md') for x in f), f)
        arm('STALE-CLAIM: "released with this handoff" while a claim made BEFORE it is still active',
            ('STALE-CLAIM', ('aa',)) in flags, flags)
        arm('...and a claim made AFTER the handoff (bb) is not stale', ('STALE-CLAIM', ('bb',)) not in flags, flags)
        arm('NEXT-DRIFT (heuristic): a working task with no word in common with the stated NEXT',
            any(x['flag'] == 'NEXT-DRIFT' and x['agents'] == ['cc'] and x['heuristic'] for x in f), f)
        arm('...and a task that matches its NEXT is not flagged', ('NEXT-DRIFT', ('aa',)) not in flags and ('NEXT-DRIFT', ('bb',)) not in flags, flags)
        arm('NEXT-DRIFT (mechanical): working, but not updated since the handoff landed',
            any(x['flag'] == 'NEXT-DRIFT' and x['agents'] == ['dd'] and not x['heuristic'] for x in f), f)
        arm('REGISTRY-BEHIND is not raised when the task names no batch, or the current one',
            not any(x['flag'] == 'REGISTRY-BEHIND' for x in f), [x for x in f if x['flag'] == 'REGISTRY-BEHIND'])
        row('gg', 'idle', 'b61: push_retry fast retry', T0 + 600, [])
        handoff('gg', 63, 'Claims held: none\n', digest_next='gg -- next')
        f2, _cn2, _n2 = run(locks, repo)
        arm('REGISTRY-BEHIND: an IDLE row whose task names b61 while the last handoff is b63 (the live hank shape)',
            any(x['flag'] == 'REGISTRY-BEHIND' and x['agents'] == ['gg'] for x in f2), f2)
        os.remove(os.path.join(locks, 'status', 'gg.json'))
        arm('a claim with NO files is listed as not checkable, never silently clean',
            any('cc' in s for s in notes), notes)
        # FAIL CLOSED
        io.open(os.path.join(locks, 'status', 'ee.json'), 'w').write('{not json')
        f, cn, notes = run(locks, repo)
        arm('an unreadable registry row is COULD-NOT-CHECK', any(c['agent'] == 'ee' for c in cn), cn)
        os.remove(os.path.join(locks, 'status', 'ee.json'))
        row('ff', 'idle', 'x', T0, [])
        f, cn, notes = run(locks, repo)
        arm('an agent with no handoff is COULD-NOT-CHECK for the handoff flags, not clean',
            any(c['agent'] == 'ff' for c in cn), cn)
        out = os.path.join(t, 'out', 'findings.json')
        write(out, f, cn, notes, locks, repo)
        doc = json.load(io.open(out, encoding='utf-8'))
        arm('the findings file is written, with findings, could-not-check and the reading note',
            doc['findings'] and doc['could_not_check'] and 'heuristic' in doc['reads_as'], sorted(doc))
        rc = main(['--out', out, '--locks', locks, '--repo', repo])
        arm('exit 2 when anything could not be checked (findings or not)', rc == EXIT_COULD_NOT, rc)
        os.remove(os.path.join(locks, 'status', 'ff.json'))
        for a in ('aa', 'bb', 'cc', 'dd'):
            os.remove(os.path.join(locks, 'status', a + '.json'))
        row('aa', 'idle', 'x', T0 + 600, [])
        row('bb', 'idle', 'y', T0 + 600, [])
        rc = main(['--out', out, '--locks', locks, '--repo', repo])
        arm('CONTROL: two idle agents with handoffs and nothing claimed -> exit 0',
            rc == EXIT_OK, (rc, json.load(io.open(out))['findings'], json.load(io.open(out))['could_not_check']))
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print('SAIRN WATCHDOG SELFTEST -- criteria %s -- %d arm(s), %d failed' % (CRITERIA_VERSION, n[0], len(bad)))
    return 1 if bad else 0


def main(argv):
    if '--selftest' in argv:
        return selftest()

    def opt(k, d):
        return argv[argv.index(k) + 1] if k in argv else d
    locks, repo = opt('--locks', LOCKS), opt('--repo', REPO)
    out = opt('--out', os.path.join(LOCKS, 'watchdog-findings.json'))
    findings, could_not, notes = run(locks, repo)
    write(out, findings, could_not, notes, locks, repo)
    print('WATCHDOG -- %d finding(s), %d could-not-check -> %s' % (len(findings), len(could_not), out))
    return EXIT_COULD_NOT if could_not else (EXIT_FINDING if findings else EXIT_OK)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
