"""Control for tools/batch_manifest.py and the push gate's item-4 additions.

    python tests/run_batch_manifest_probe.py

The manifest's job is to make a SKIPPED or RENUMBERED item impossible to
report around, so the arms are about the id lock and about evidence that
cannot be re-run. The gate's two additions -- scoping a finding to the pushing
agent's own files, and capping retries at 2 -- are driven here too, because
cody's live b6 claim holds tests/push_gate/ and those files are not this
session's to touch.
"""
CONTROLS_FOR = ['batch_manifest.py', 'sairn_push_gate_hook.py']

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'batch_manifest.py')
GATE = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
NL = chr(10)

for _p in (TOOL, GATE):
    if not os.path.isfile(_p):
        print('COULD NOT RUN -- %s is absent.' % _p)
        sys.exit(2)

_spec = importlib.util.spec_from_file_location('bm_probe', TOOL)
BM = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BM)

passed, fails = 0, []


def ok(cond, label, detail=''):
    global passed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        fails.append(label)
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:400])


print('1. the shipped criteria lock')
r = subprocess.run([sys.executable, TOOL, '--fixtures'], capture_output=True,
                   text=True, encoding='utf-8', errors='replace')
ok(r.returncode == 0, 'it passes', (r.returncode, (r.stdout or '')[-300:]))
ok('21/21' in (r.stdout or ''), '...and every fixture ran',
   (r.stdout or '')[-160:])

print('')
print('2. the id lock catches each of the four ways ids drift')
base = BM.new('cc', 'probe', [1, 2, 3, 4])
ok(not BM.validate(base), 'a fresh manifest validates')

def mutate(fn):
    d = json.loads(json.dumps(base))
    fn(d)
    return BM.validate(d)

def _renumber(d):
    d['items'][3]['id'] = 9

def _duplicate(d):
    d['items'][3]['id'] = 2

def _add(d):
    d['items'].append({'id': 5, 'status': 'open', 'evidence': ''})

def _remove(d):
    d['items'].pop()

def _swap(d):
    d['items'][0]['id'], d['items'][1]['id'] = (d['items'][1]['id'],
                                                d['items'][0]['id'])

ok(mutate(_renumber), 'RENUMBERED is caught')
ok(mutate(_duplicate), 'DUPLICATED is caught')
ok(mutate(_add), 'an ADDED id is caught -- the agent does not write ids')
ok(mutate(_remove), 'a REMOVED id is caught')
ok(mutate(_swap), 'a SWAPPED PAIR is caught, which a count would miss -- and '
   'is the reason the lock hashes the ORDERED list')
ok(any('IDS HAVE CHANGED' in f for f in mutate(_renumber)),
   '...and the renumber finding names the lock mismatch rather than just '
   'saying no', mutate(_renumber))

print('')
print('3. evidence has to be a pointer, not an adjective')
def with_ev(status, ev):
    d = json.loads(json.dumps(base))
    d['items'][0]['status'] = status
    d['items'][0]['evidence'] = ev
    return BM.validate(d)

ok(with_ev('done', ''), 'done with NO evidence is a finding')
for word in ('verified', 'works', 'tested', 'complete', 'yes', 'n/a', 'done'):
    ok(with_ev('done', word), 'done with %r is a finding' % word)
ok(with_ev('done', 'it went fine'), 'done with prose carrying no pointer is a '
   'finding')
ok(not with_ev('done', 'tools/gate_skip.py, 14/14 fixtures'),
   'a path plus a count validates')
ok(not with_ev('done', 'landed at 0f531a66'), 'a sha validates')
ok(not with_ev('done', 'python tools/batch_cleanup.py --fixtures'),
   'a command validates')
ok(with_ev('blocked', ''), 'blocked with no reason is a finding -- "not done" '
   'needs a reason for the same reason "done" needs a pointer')
ok(not with_ev('blocked', 'hank holds docs/tier-a-reviews.json in his b5 FILES'),
   'blocked WITH a reason validates')

print('')
print('4. --set refuses to invent an id')
tmp = tempfile.mkdtemp(prefix='bmp_')
_docs = BM.DOCS
try:
    BM.DOCS = tmp
    BM.save(BM.new('cc', 'probe', [1, 2]))
    rc = BM.cmd_set('cc', 'probe', '7', 'done', 'x.py')
    ok(rc == 1, '--set on an id that does not exist is REFUSED, not created -- '
       'that is the renumbering the manifest exists to prevent', rc)
    doc, _ = BM.load('cc', 'probe')
    ok(len(doc['items']) == 2, '...and nothing was added', len(doc['items']))
    rc = BM.cmd_set('cc', 'probe', '1', 'done', 'verified')
    ok(rc == 1, '--set with unusable evidence is REFUSED before writing', rc)
    doc, _ = BM.load('cc', 'probe')
    ok(doc['items'][0]['status'] == 'open',
       '...and the status did NOT move, so a refused set leaves no half-state',
       doc['items'][0])
    rc = BM.cmd_set('cc', 'probe', '1', 'done', 'tools/x.py 3/3')
    ok(rc == 0, 'a real set with a real pointer succeeds', rc)
finally:
    BM.DOCS = _docs
    shutil.rmtree(tmp, ignore_errors=True)

print('')
print('5. the real b6 manifest validates')
r = subprocess.run([sys.executable, TOOL, '--check'], capture_output=True,
                   text=True, encoding='utf-8', errors='replace')
ok(r.returncode == 0, 'docs/batch-manifest-cc-b6.json is clean',
   (r.returncode, (r.stdout or '')[-300:]))
ok('batch-manifest-cc-b6.json' in (r.stdout or ''),
   '...and it really looked at it rather than finding nothing',
   (r.stdout or '')[-200:])

print('')
print('6. the push gate: a finding is SCOPED to the pushing agent, not dropped')
_gspec = importlib.util.spec_from_file_location('gate_probe', GATE)
G = importlib.util.module_from_spec(_gspec)
try:
    sys.argv = ['gate_probe']
    _gspec.loader.exec_module(G)
    _loaded = True
except SystemExit:
    _loaded = False
ok(_loaded, 'the gate module imports without running its main()')

if _loaded:
    _real = G.outgoing_files
    try:
        G.outgoing_files = lambda repo, base=None, tip='HEAD': [
            'tools/gate_skip.py', 'docs/batch-manifest-cc-b6.json']
        mine, theirs = G.scope_to_mine(
            ['tools/gate_skip.py', 'G:/My Drive/SAIRN-status/handoff-hank.md',
             'docs/batch-manifest-cc-b6.json', 'api/sd-data.js'], REPO)
        ok(sorted(mine) == ['docs/batch-manifest-cc-b6.json',
                            'tools/gate_skip.py'],
           'paths THIS PUSH touched are mine', mine)
        ok(sorted(theirs) == ['G:/My Drive/SAIRN-status/handoff-hank.md',
                              'api/sd-data.js'],
           'paths it did not touch are THEIRS -- reported, never blocking',
           theirs)
        ok(len(mine) + len(theirs) == 4,
           'NOTHING IS DROPPED by the split -- every path lands in exactly '
           'one bucket')
        mine, theirs = G.scope_to_mine([], REPO)
        ok(mine == [] and theirs == [],
           'an empty finding list splits to two empty lists rather than '
           'raising')
    finally:
        G.outgoing_files = _real

    print('')
    print('7. the push gate: retries capped at 2, then escalate with the text')
    _rd = G.RETRY_DIR
    tmp2 = tempfile.mkdtemp(prefix='rtp_')
    try:
        G.RETRY_DIR = tmp2
        ok(G.RETRY_CAP == 2, 'the cap is 2 -- attempt 1 finds the refusal, '
           'attempt 2 proves the fix worked, a third is a loop', G.RETRY_CAP)
        n1 = G.retry_count('abc123def456', bump=True)
        n2 = G.retry_count('abc123def456', bump=True)
        n3 = G.retry_count('abc123def456', bump=True)
        ok((n1, n2, n3) == (1, 2, 3), 'the count rises per refusal for one tip',
           (n1, n2, n3))
        ok(G.retry_count('different0tip', bump=False) == 0,
           'a DIFFERENT tip starts at zero -- a rebase renames the tip and a '
           'new tip is a new push, not a retry')
        lines = G.escalation_lines(3, 'abc123def456', ['the real error text'])
        ok(any('ESCALATING' in l for l in lines), 'the escalation says so')
        ok(any('the real error text' in l for l in lines),
           '...and carries the FULL error text rather than a summary of it')
        ok(any('Take it to chat' in l for l in lines),
           '...and says to escalate rather than retry')
    finally:
        G.RETRY_DIR = _rd
        shutil.rmtree(tmp2, ignore_errors=True)

print('')
print('%d passed, %d failed' % (passed, len(fails)))
for f in fails:
    print('  FAILED: %s' % f)
sys.exit(1 if fails else 0)
