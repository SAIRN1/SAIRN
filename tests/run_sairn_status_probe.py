"""The status registry must not lose a write, and the design claim must be earned.

    python tests/run_sairn_status_probe.py

`tools/sairn_status.py` makes ONE architectural claim and everything else rests
on it: *one file per agent, so two agents' writes cannot interact at the
filesystem level at all -- no window to narrow, by construction.*

AN ARM THAT ONLY DRIVES THE CHOSEN DESIGN CANNOT TEST THAT CLAIM. "N concurrent
writers all survived" passes on any design that happens not to race during one
run, and a concurrency bug that does not reproduce on the run you watched is
the whole reason this class of defect ships. So section 2 implements the
REJECTED design -- one shared file, read-modify-write, one section each -- and
drives the SAME concurrency at it. If that loses writes and this does not, the
claim is measured rather than asserted.

── WHAT SECTION 2 IS AND IS NOT ────────────────────────────────────────────
It inserts a small sleep between the read and the write. That WIDENS a real
window; it does not invent one. The window exists in any read-modify-write
against a shared file and its size depends on disk, load and file size -- which
is exactly why "it worked when I ran it" is not evidence about it. The arm
asserts the shared design loses writes, and says in its own output that the
sleep is what makes the loss reproducible rather than occasional.

Every arm points `SAIRN_STATUS_DIR` at a temp directory. NOTHING here can touch
`~/SAIRN-SESSION-LOCKS/status`, and section 0 proves that redirection works
before any other arm trusts it -- a control pointed at the wrong target is the
vacuous-control shape this platform polices hardest, and it was found twice in
one session on 2026-09-16 in two different tools.
"""
CONTROLS_FOR = ['sairn_status.py']

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'sairn_status.py')

FAILS, PASSES = [], [0]


# ONE SIGNATURE, AND IT TAKES A BOOLEAN. This file's first draft passed LISTS
# as `cond` in nine arms -- `ok('...', bad_parse, [])` -- reading as
# (actual, expected) because a sibling suite's helper has that shape. An empty
# list is falsy, so the arms that should have passed reported FAIL, and a
# NON-EMPTY list is truthy, so `ok('...', torn[:3], [])` PASSED precisely when
# the reader had observed torn files. That is the third time in one session on
# this platform that an arm has reported a check it never performed, and the
# only reason it surfaced is that four of the nine failed loudly.
def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('  ok   %s' % label)
    else:
        FAILS.append(label)
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:500])


def env(status_dir):
    return dict(os.environ, SAIRN_STATUS_DIR=status_dir,
                PYTHONIOENCODING='utf-8', PYTHONUTF8='1')


def run(status_dir, *args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=env(status_dir))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


tmproot = tempfile.mkdtemp(prefix='sairnstatus-')

# ── 0. THE REDIRECTION WORKS, asserted before anything relies on it ─────────
print('\n0. the probe is pointed at a fixture, not at the real registry')
REAL = os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS', 'status')
_real_before = sorted(os.listdir(REAL)) if os.path.isdir(REAL) else None
d0 = os.path.join(tmproot, 'redirect')
rc, out = run(d0, 'set', '--state', 'working', '--task', 'redirect probe',
              '--session', 'probe0')
ok('0a a write lands in the FIXTURE directory',
   os.path.exists(os.path.join(d0, 'probe0.json')), out[:300])
ok('0b ...and the tool says so in its own output', d0 in out, out[:300])
_real_after = sorted(os.listdir(REAL)) if os.path.isdir(REAL) else None
ok('0c and the REAL registry was not touched', _real_after == _real_before,
   (_real_before, _real_after))

# ── 1. THE REQUIREMENT: concurrent writers to their OWN sections ────────────
# Six agents, ten rounds each, all started before any finishes. Every write
# must survive and every file must end holding its own agent's last value.
print('\n1. six agents writing their own sections concurrently, ten rounds each')
AGENTS = ['alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot']
ROUNDS = 10
d1 = os.path.join(tmproot, 'concurrent')
os.makedirs(d1)

WRITER = '''
import os, subprocess, sys
tool, name, rounds, d = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
e = dict(os.environ, SAIRN_STATUS_DIR=d, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
for i in range(rounds):
    subprocess.run([sys.executable, tool, "set", "--session", name,
                    "--state", "working", "--task", "%s round %d" % (name, i)],
                   capture_output=True, env=e)
'''
wpath = os.path.join(tmproot, '_writer.py')
io.open(wpath, 'w', encoding='utf-8', newline='\n').write(WRITER)

procs = [subprocess.Popen([sys.executable, wpath, TOOL, a, str(ROUNDS), d1],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
         for a in AGENTS]
for p in procs:
    p.wait()

files = sorted(f for f in os.listdir(d1) if f.endswith('.json'))
ok('1a every agent has a file -- NOT ONE WRITE WAS LOST',
   files == [a + '.json' for a in AGENTS], files)
bad_parse, bad_value, wrong_owner = [], [], []
for a in AGENTS:
    try:
        with io.open(os.path.join(d1, a + '.json'), encoding='utf-8') as fh:
            body = json.load(fh)
    except Exception as e:                                       # noqa: BLE001
        bad_parse.append((a, str(e)[:80]))
        continue
    if body.get('session') != a:
        wrong_owner.append((a, body.get('session')))
    if body.get('task') != '%s round %d' % (a, ROUNDS - 1):
        bad_value.append((a, body.get('task')))
ok('1b every file parses -- no torn write survived anywhere',
   not bad_parse, bad_parse)
ok('1c every file holds its OWN agent, never a neighbour\'s',
   not wrong_owner, wrong_owner)
ok('1d every file holds that agent\'s LAST round, so no write was overwritten '
   'by a stale one', not bad_value, bad_value)
_leftover1 = [f for f in os.listdir(d1) if '.tmp-' in f]
ok('1e no temp file was left behind', not _leftover1, _leftover1)

# ── 2. THE CONTROL. The rejected design, same concurrency, and it LOSES ─────
print('\n2. CONTROL: the shared-file design, driven the same way')
print('   Without this, section 1 passes on any design that happens not to')
print('   race during one run. This shows the window is real.')
SHARED_WRITER = '''
import json, os, sys, time
path, name, rounds = sys.argv[1], sys.argv[2], int(sys.argv[3])
for i in range(rounds):
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    # THE WINDOW. Every read-modify-write against a shared file has one; the
    # sleep WIDENS it so the loss is reproducible rather than occasional. It
    # does not create a defect that is otherwise absent.
    time.sleep(0.01)
    d[name] = {"task": "%s round %d" % (name, i)}
    tmp = path + ".tmp-" + name
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.replace(tmp, path)
'''
spath = os.path.join(tmproot, '_shared_writer.py')
io.open(spath, 'w', encoding='utf-8', newline='\n').write(SHARED_WRITER)
shared = os.path.join(tmproot, 'shared.json')
io.open(shared, 'w', encoding='utf-8', newline='\n').write('{}')

procs = [subprocess.Popen([sys.executable, spath, shared, a, str(ROUNDS)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
         for a in AGENTS]
for p in procs:
    p.wait()
with io.open(shared, encoding='utf-8') as fh:
    final = json.load(fh)
missing = [a for a in AGENTS if a not in final]
stale = [a for a in AGENTS
         if a in final
         and final[a].get('task') != '%s round %d' % (a, ROUNDS - 1)]
lost = len(missing) + len(stale)
ok('2a the SHARED-FILE design loses writes under the same concurrency',
   lost > 0,
   'it did not lose any this run -- the window is timing-dependent, which is '
   'the point, but this arm cannot then be evidence. missing=%r stale=%r'
   % (missing, stale))
print('       measured: %d of %d agents ended with a lost or stale section '
      '(%d absent entirely, %d showing an old round)'
      % (lost, len(AGENTS), len(missing), len(stale)))
ok('2b ...while the per-agent design lost NONE, on the same machine, in the '
   'same run', not (bad_parse or bad_value or wrong_owner),
   (bad_parse, bad_value, wrong_owner))

# ── 3. TWO WRITERS ON THE SAME SECTION -- the one shared path there is ──────
# An agent running two processes at once is the degenerate case. Last write
# wins is acceptable; a torn or unparseable file never is.
print('\n3. the degenerate case: two processes writing the SAME section')
d3 = os.path.join(tmproot, 'samesection')
os.makedirs(d3)
procs = [subprocess.Popen([sys.executable, wpath, TOOL, 'solo', '8', d3],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
         for _ in range(4)]
for p in procs:
    p.wait()
try:
    with io.open(os.path.join(d3, 'solo.json'), encoding='utf-8') as fh:
        body = json.load(fh)
    parsed, err = True, ''
except Exception as e:                                           # noqa: BLE001
    parsed, err, body = False, str(e)[:120], {}
ok('3a the file still parses after four processes raced on it', parsed, err)
ok('3b ...and holds a WHOLE, valid record rather than a merge of two',
   parsed and body.get('session') == 'solo' and 'updated' in body, body)
_leftover3 = [f for f in os.listdir(d3) if '.tmp-' in f]
ok('3c no temp file was left behind', not _leftover3, _leftover3)

# ── 4. READING WHILE THE REGISTRY IS BEING WRITTEN ─────────────────────────
#
# Section 1 reads only AFTER every writer has finished, so it cannot say
# anything about a reader that overlaps a write. This does, and it separates
# two failures that look identical from the outside and are not:
#
#   TORN   -- a reader sees half a file. This is what os.replace() prevents,
#             and it did: zero partial or unparseable reads, ever.
#   ACCESS -- a reader is momentarily refused the file because a rename is
#             landing on it. MEASURED on Windows, a handful per few thousand.
#             The file is not damaged; it is unopenable for an instant.
#
# THE SECOND ONE WOULD HAVE BEEN A FALSE ALARM IN PRODUCTION. The tool's first
# version treated any exception as `unreadable`, so a perfectly healthy agent
# would have been reported UNREADABLE -- and the whole run pushed to exit 2 --
# at random, roughly twice per thousand reads. A registry that cries wolf twice
# a day is one nobody reads. read_one() retries an OPEN failure and reports
# only a file that still will not open, or one that opens and does not parse.
print('\n4. reading while the registry is being written')
import importlib.util                                            # noqa: E402
_spec = importlib.util.spec_from_file_location('sairn_status_probe_copy', TOOL)
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

d4 = os.path.join(tmproot, 'reader')
os.makedirs(d4)
procs = [subprocess.Popen([sys.executable, wpath, TOOL, a, '6', d4],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
         for a in AGENTS[:4]]
naive_torn, naive_access, reads = [], [], 0
tool_failed = []
while any(p.poll() is None for p in procs):
    for f in os.listdir(d4):
        if not f.endswith('.json'):
            continue
        full = os.path.join(d4, f)
        # (a) the NAIVE reader -- one open, no retry. This is what the tool
        #     used to do, and it is what makes the retry earn its place.
        try:
            with io.open(full, encoding='utf-8') as fh:
                json.load(fh)
            reads += 1
        except ValueError as e:
            naive_torn.append((f, str(e)[:70]))
        except OSError as e:
            naive_access.append((f, str(e)[:70]))
        # (b) the TOOL's reader, on the same file at the same moment.
        _d, _err = S.read_one(full)
        if _err:
            tool_failed.append((f, _err[:90]))
for p in procs:
    p.wait()
ok('4a the reader really got to read DURING the writes, so nothing below is '
   'passing on zero attempts', reads > 20, reads)
ok('4b NOT ONE read was torn or half-written -- which is what os.replace() '
   'buys and the only thing it buys',
   not naive_torn, '%d torn: %r' % (len(naive_torn), naive_torn[:3]))
# This arm asserts the PROBLEM exists. If it ever stops firing the retry below
# is no longer evidence of anything, and that is worth knowing too.
if naive_access:
    ok('4c MEASURED: a naive one-shot reader IS refused mid-rename -- %d of '
       '%d reads' % (len(naive_access), reads + len(naive_access)), True)
else:
    ok('4c MEASURED: a naive one-shot reader was NOT refused on this run, so '
       '4d is not evidence today -- declared rather than passed quietly', True,
       'the access race is timing-dependent; on the run that found it, 5 of '
       '2867 reads were refused')
ok('4d and the TOOL never once reported a healthy file as unreadable',
   not tool_failed, '%d false UNREADABLE: %r' % (len(tool_failed),
                                                 tool_failed[:3]))

# ── 5. ONE CORRUPT FILE MUST NOT HIDE THE OTHERS ───────────────────────────
print('\n5. a corrupt entry is NAMED, never dropped')
d5 = os.path.join(tmproot, 'corrupt')
os.makedirs(d5)
run(d5, 'set', '--session', 'good', '--state', 'working', '--task', 'real work')
io.open(os.path.join(d5, 'broken.json'), 'w', encoding='utf-8').write('{ nope')
rc, out = run(d5)
ok('5a the corrupt entry is reported UNREADABLE and named',
   'broken' in out and 'UNREADABLE' in out, out[:400])
ok('5b the healthy entry is STILL reported beside it',
   'real work' in out, out[:400])
ok('5c and the run is COULD NOT TELL (2), not a clean registry',
   rc == 2, 'exit %d' % rc)
# The other direction, so 5c is not satisfied by a tool that always exits 2.
rc_ok, _ = run(d1)
ok('5d CONTROL: a registry with no corrupt entry exits 0', rc_ok == 0,
   'exit %d' % rc_ok)

# ── 6. THE THIRD STATE, IN BOTH OF ITS SHAPES ──────────────────────────────
print('\n6. absent and empty are both COULD NOT RUN, not "nobody is working"')
rc, out = run(os.path.join(tmproot, 'never-created'))
ok('6a an ABSENT registry is exit 2', rc == 2, 'exit %d' % rc)
ok('6b ...and says it checked nothing', 'did NOT check anything' in out, out[:300])
d6 = os.path.join(tmproot, 'empty')
os.makedirs(d6)
rc, out = run(d6)
ok('6c an EMPTY registry is exit 2, NOT a clean all-clear', rc == 2,
   'exit %d' % rc)
ok('6d ...and says explicitly that this is not "nobody is working"',
   'NOT "nobody is working"' in out, out[:400])

# ── 7. A WRITE IN FLIGHT IS NOT AN ENTRY ───────────────────────────────────
print('\n7. a .tmp- file mid-write is never read as a session')
d7 = os.path.join(tmproot, 'tmpfile')
os.makedirs(d7)
run(d7, 'set', '--session', 'real', '--state', 'working', '--task', 'x')
io.open(os.path.join(d7, 'ghost.json.tmp-deadbeef'), 'w',
        encoding='utf-8').write('{"session": "ghost"}')
rc, out = run(d7)
ok('7a the temp file is not reported as a session', 'ghost' not in out, out[:300])
ok('7b ...and the real one still is', 'real' in out, out[:300])

# ── 8. A BLOCKED ROW THAT NAMES NO BLOCKER IS REFUSED ──────────────────────
print('\n8. blocked without a blocker is a silence wearing a status')
d8 = os.path.join(tmproot, 'blocked')
os.makedirs(d8)
rc, out = run(d8, 'set', '--session', 'x', '--state', 'blocked', '--task', 't')
ok('8a it is REFUSED with exit 2', rc == 2, 'exit %d\n%s' % (rc, out[:300]))
ok('8b ...and nothing was written',
   not os.path.exists(os.path.join(d8, 'x.json')))
rc, out = run(d8, 'set', '--session', 'x', '--state', 'blocked', '--task', 't',
              '--blocked-on', 'Michael: run the migration')
ok('8c and WITH a blocker it is accepted and the blocker is shown',
   rc == 0 and 'run the migration' in out, 'exit %d\n%s' % (rc, out[:300]))
rc, out = run(d8, 'set', '--session', 'x', '--state', 'nonsense')
ok('8d an unknown state is refused rather than stored', rc == 2, 'exit %d' % rc)

# ── 9. THE BLIND LOCK. The overlap rule is fixture-checked BEFORE it runs ───
print('\n9. teeth -- a broken overlap rule must refuse, not report a quiet '
      'platform')
d9 = os.path.join(tmproot, 'teeth')
os.makedirs(d9)
run(d9, 'set', '--session', 'a', '--state', 'working', '--task', 'alpha work')
broken = os.path.join(tmproot, 'broken_tool.py')
src = io.open(TOOL, encoding='utf-8').read()
ANCHOR = 'def words(text):\n'
ok('9a the teeth anchor is present', src.count(ANCHOR) == 1,
   'anchor stale -- the arm below tests NOTHING')
io.open(broken, 'w', encoding='utf-8', newline='\n').write(
    src.replace(ANCHOR, ANCHOR + '    return set()\n', 1))
p = subprocess.run([sys.executable, broken], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace',
                   env=dict(env(d9), PYTHONPATH=os.path.join(REPO, 'tools')))
ok('9b an overlap rule that finds NOTHING exits COULD NOT RUN (2), not 0',
   p.returncode == 2, 'exit %d\n%s' % (p.returncode, (p.stdout or '')[:300]))
ok('9c ...and names the rule rather than printing a report',
   'overlap rule failed its own fixtures' in (p.stdout or ''),
   (p.stdout or '')[:300])

# ── 10. THE JOIN ITSELF, in both directions ────────────────────────────────
print('\n10. overlap candidates are surfaced, and unrelated work is not')
d10 = os.path.join(tmproot, 'overlap')
os.makedirs(d10)
run(d10, 'set', '--session', 'one', '--state', 'working',
    '--task', 'removal path baseline burn-down')
run(d10, 'set', '--session', 'two', '--state', 'working',
    '--task', 'the removal path fixture arm')
run(d10, 'set', '--session', 'three', '--state', 'working',
    '--task', 'sairnvet dosing audit local time')
rc, out = run(d10)
ok('10a two agents on the same subject are named as candidates',
   'one <-> two' in out and 'removal' in out, out[-700:])
ok('10b an unrelated third is NOT paired with either',
   'three' not in out.split('OVERLAP CANDIDATES')[-1].split('THIS DOES NOT')[0],
   out[-700:])
ok('10c and the report refuses to call a candidate a verdict',
   'DOES NOT DECIDE ANYTHING' in out, out[-400:])
# An IDLE agent is not competing for work and must not raise a candidate.
run(d10, 'set', '--session', 'two', '--state', 'idle')
rc, out = run(d10)
ok('10d an IDLE agent raises no overlap candidate',
   'one <-> two' not in out, out[-500:])

# ── 11. LIVENESS: a dead writer is not reported as working ─────────────────
print('\n11. a status whose owner is gone is not a live agent')
d11 = os.path.join(tmproot, 'liveness')
os.makedirs(d11)
# A pid that cannot be running, with a start signature that cannot match.
io.open(os.path.join(d11, 'ghostagent.json'), 'w', encoding='utf-8',
        newline='\n').write(json.dumps({
            'session': 'ghostagent', 'state': 'working', 'task': 'long gone',
            'updated': '2020-01-01T00:00:00', 'claude_pid': 999999999,
            'claude_start': '0'}))
rc, out = run(d11)
ok('11a a status from a process that does not exist is NOT reported LIVE',
   'ghostagent' in out and ' LIVE' not in out.split('ghostagent')[1][:60],
   out[:500])
ok('11b ...and the row is still shown, with the reason',
   'long gone' in out, out[:500])

# ── 12. THE SessionStart HOOK FAILS OPEN, ALWAYS ───────────────────────────
#
# This is the mechanism that makes "every agent reads the registry at session
# start" true rather than remembered. It is also the one piece of this that can
# hurt: a hook that errors, blocks or emits malformed JSON degrades every
# session on the platform, including sessions that have nothing to do with the
# registry.
#
# SO IT FAILS OPEN, AND THAT IS THE OPPOSITE OF THE RULE THIS REPO APPLIES TO
# CHECKS -- deliberately. A check that cannot run must not report a pass; an
# advisory that cannot run must not stop the work. Failing open is not failing
# silent: every could-not-read path still emits the sentence saying the answer
# is UNKNOWN, because emitting nothing reads as "nobody is working".
print('\n12. the SessionStart hook never blocks a session')


def hook(status_dir):
    p = subprocess.run([sys.executable, TOOL, '--hook'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=env(status_dir))
    return p.returncode, (p.stdout or '')


for label, d in (('a populated registry', d1),
                 ('an ABSENT registry', os.path.join(tmproot, 'nope-never')),
                 ('an EMPTY registry', d6),
                 ('a registry with a CORRUPT entry', d5)):
    rc, out = hook(d)
    ok('12 %s: the hook exits 0' % label, rc == 0, 'exit %d' % rc)
    try:
        body = json.loads(out)
        ctx = body['hookSpecificOutput']['additionalContext']
        valid = body['hookSpecificOutput']['hookEventName'] == 'SessionStart'
    except Exception as e:                                       # noqa: BLE001
        ctx, valid = '', False
        ok('12 %s: emits parseable hook JSON' % label, False, '%s: %r'
           % (e, out[:200]))
    else:
        ok('12 %s: emits parseable hook JSON' % label, valid, out[:200])
    ok('12 %s: says something rather than nothing' % label,
       len(ctx.strip()) > 40, repr(ctx[:120]))

# THE TWO SILENT-CLEAN DIRECTIONS, named explicitly.
_rc, _out = hook(os.path.join(tmproot, 'nope-never'))
_ctx = json.loads(_out)['hookSpecificOutput']['additionalContext']
ok('12 an ABSENT registry says UNKNOWN, never "nobody else is working"',
   'not as "nobody else is working"' in _ctx, _ctx[:200])
_rc, _out = hook(d6)
_ctx = json.loads(_out)['hookSpecificOutput']['additionalContext']
ok('12 an EMPTY registry says so is not evidence nobody is working',
   'not evidence that nobody is working' in _ctx, _ctx[:200])

# AND IT STILL EXITS 0 WHEN THE REGISTRY PATH IS SOMETHING IT CANNOT READ AT
# ALL -- a file where a directory should be. A session must start regardless.
_notadir = os.path.join(tmproot, 'notadir')
io.open(_notadir, 'w', encoding='utf-8').write('x')
rc, out = hook(_notadir)
ok('12 a registry path that is a FILE, not a directory, still exits 0',
   rc == 0, 'exit %d' % rc)

shutil.rmtree(tmproot, ignore_errors=True)
print('\n' + '=' * 68)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
