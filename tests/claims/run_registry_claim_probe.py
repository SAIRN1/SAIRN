"""Control for the LIVE-REGISTRY half of tools/sairn_claim.py.

    python tests/claims/run_registry_claim_probe.py

Exit 0  a claim that exists only in the registry blocks, and every way the
        registry can be unavailable leaves the tool exactly as it was
Exit 1  one of those did not hold

── THE SIX SECONDS THIS EXISTS TO CLOSE ────────────────────────────────────
MEASURED, from the claim records, not constructed:

    cody  criticality-tiers  claimed 22:12:27Z  FILES: docs/CRITICALITY-TIERS.md
    hank  tier-batch         claimed 22:12:33Z  FILES: docs/CRITICALITY-TIERS.md

Six seconds apart, both DECLARING THE SAME FILE, and both proceeded. Seven
rows of that file were then re-tiered twice, independently, to the same
verdict. THE MATCHER WAS NOT AT FAULT: it decides on the declared file set and
would have refused instantly. It could not see cody's claim, because a claim
is published by committing and PUSHING it and hank's check read a fetch taken
before cody's push landed.

So sairn_claim now mirrors its active claims into tools/sairn_status.py's
registry -- outside git, written locally, read with no fetch -- and reads the
other sessions' at check time.

── WHAT THE ARMS ARE ACTUALLY ABOUT ────────────────────────────────────────
Two things, and the second is the larger risk:

  1 a claim visible ONLY in the registry must block, and the refusal must SAY
    it came from there, because "not pushed yet" changes what to do about it;
  2 EVERY way the registry can be unavailable must leave the tool behaving
    exactly as it did before this change. Three clones are using it right now.
    A new dependency that can refuse work when a file is missing would be a
    worse defect than the collision it prevents, and this is the platform's
    own fail-CLOSED rule running the other way: a gate must fail closed, an
    ADVISORY EARLY WARNING must fail open, and the difference is that this one
    adds evidence rather than being the evidence.

Every fixture is synthetic, in a temp directory, with SAIRN_STATUS_DIR pointed
at it. The real registry is never read or written by this probe.
"""
CONTROLS_FOR = ['sairn_claim.py', 'sairn_status.py']

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, 'tools', 'sairn_claim.py')
FAILS = []


def ok(label, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        FAILS.append(label)


# ── ASSERTED ON THE OUTPUT, NOT THE EXIT CODE, AND THE FIRST VERSION GOT
# ── THIS WRONG IN THE FLATTERING DIRECTION ─────────────────────────────────
# Every arm below runs with `--no-fetch`, and `check` returns STALE_RC = 4 for
# that -- correctly: it is saying "this verdict did not reach the remote". The
# first version asserted `rc == 0` for the eight NON-blocking arms, so all
# eight failed against a tool that was behaving perfectly, and the one arm
# asserting `rc != 0` PASSED for the wrong reason: 4 is not 0 whether or not
# anything blocked. A blocking arm that cannot tell a block from a stale fetch
# is the shape this whole file is about.
def run(regdir, *args):
    env = dict(os.environ)
    if regdir is None:
        env.pop('SAIRN_STATUS_DIR', None)
    else:
        env['SAIRN_STATUS_DIR'] = regdir
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=300, env=env)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def write_row(regdir, session, files, subject='their-batch',
              task=None, status='active', age_h=0.0):
    task = task or ('their work FILES: ' + ' '.join(files))
    row = {
        'session': session, 'state': 'working', 'task': subject,
        'updated': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'claims': [{
            'subject': subject, 'task': task,
            'claimed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'claimed_at_epoch': time.time() - age_h * 3600,
            'files': list(files), 'status': status,
        }],
    }
    with io.open(os.path.join(regdir, session + '.json'), 'w',
                 encoding='utf-8') as fh:
        fh.write(json.dumps(row, indent=1))


tmp = tempfile.mkdtemp(prefix='regclaim-probe-')
MINE = 'my work FILES: docs/CRITICALITY-TIERS.md'
try:
    # ── 1. THE DEFECT ITSELF. A claim that is in NO git repository anywhere
    # ── blocks, because the other session wrote it locally six seconds ago.
    reg = os.path.join(tmp, 'live')
    os.makedirs(reg)
    write_row(reg, 'hank', ['docs/CRITICALITY-TIERS.md'])
    rc, out = run(reg, 'check', 'tooling', MINE, '--no-fetch')
    ok('a claim visible ONLY in the registry BLOCKS', 'BLOCKED' in out, out[:300])
    ok('...naming the session that holds it', 'hank' in out, out[:300])
    ok('...and the declared file they collide on',
       'docs/CRITICALITY-TIERS.md' in out, out[:300])
    ok('...and SAYING it is not on origin/main, because that changes what to '
       'do about it', 'LIVE STATUS REGISTRY' in out and 'not been pushed' in out,
       out[:400])

    # ── 2. IT STILL DISCRIMINATES. A blocker that blocks everything is not a
    # ── blocker, and this is the arm a match-everything regression fails.
    rc, out = run(reg, 'check', 'tooling', 'unrelated FILES: tools/zz_nothing.py',
                  '--no-fetch')
    ok('a registry claim on DISJOINT files does not block', 'BLOCKED' not in out, out[:300])

    # ── 3. EXPIRY IS THE REGISTRY'S TOO. A row nobody cleaned up must not
    # ── block work for ever -- that is the four-hour rule with the rule
    # ── removed, which is worse than no row.
    old = os.path.join(tmp, 'stale')
    os.makedirs(old)
    write_row(old, 'hank', ['docs/CRITICALITY-TIERS.md'], age_h=9.0)
    rc, out = run(old, 'check', 'tooling', MINE, '--no-fetch')
    ok('a registry claim older than the expiry does not block', 'BLOCKED' not in out, out[:300])

    # ── 4. A RELEASED CLAIM IS NOT A CLAIM, even in the fast path.
    rel = os.path.join(tmp, 'released')
    os.makedirs(rel)
    write_row(rel, 'hank', ['docs/CRITICALITY-TIERS.md'], status='released')
    rc, out = run(rel, 'check', 'tooling', MINE, '--no-fetch')
    ok('a RELEASED registry claim does not block', 'BLOCKED' not in out, out[:300])

    # ── 5. FAIL OPEN, FIVE WAYS. Each is a real state a clone can be in
    # ── during a rollout, and none may refuse work.
    rc, out = run(os.path.join(tmp, 'does-not-exist'), 'check', 'tooling', MINE,
                  '--no-fetch')
    ok('an ABSENT registry directory leaves the tool as it was', 'BLOCKED' not in out, out[:200])

    empty = os.path.join(tmp, 'empty')
    os.makedirs(empty)
    rc, out = run(empty, 'check', 'tooling', MINE, '--no-fetch')
    ok('an EMPTY registry leaves the tool as it was', 'BLOCKED' not in out, out[:200])

    bad = os.path.join(tmp, 'corrupt')
    os.makedirs(bad)
    with io.open(os.path.join(bad, 'hank.json'), 'w', encoding='utf-8') as fh:
        fh.write('{not json at all')
    rc, out = run(bad, 'check', 'tooling', MINE, '--no-fetch')
    ok('a CORRUPT registry row leaves the tool as it was', 'BLOCKED' not in out, out[:200])
    ok('...and does not spill a traceback at the operator',
       'Traceback' not in out, out[-300:])

    noclaims = os.path.join(tmp, 'noclaims')
    os.makedirs(noclaims)
    with io.open(os.path.join(noclaims, 'hank.json'), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps({'session': 'hank', 'state': 'working',
                             'task': 'on an older build'}))
    rc, out = run(noclaims, 'check', 'tooling', MINE, '--no-fetch')
    ok('a row with NO claims key -- a clone on the older build -- is not an '
       'error', 'BLOCKED' not in out, out[:200])

    wrongshape = os.path.join(tmp, 'wrongshape')
    os.makedirs(wrongshape)
    with io.open(os.path.join(wrongshape, 'hank.json'), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps({'session': 'hank', 'claims': ['not', 'dicts']}))
    rc, out = run(wrongshape, 'check', 'tooling', MINE, '--no-fetch')
    ok('a row whose claims are the WRONG SHAPE is skipped, not fatal',
       'BLOCKED' not in out and 'Traceback' not in out, out[:200])

    # ── 6. THE MIRROR IS WRITTEN, AND ONLY THIS SESSION'S ROW IS TOUCHED.
    # ── Ownership-per-key is the property that makes the registry safe to
    # ── write without locking; a tool that wrote another session's row would
    # ── destroy it.
    mirror = os.path.join(tmp, 'mirror')
    os.makedirs(mirror)
    write_row(mirror, 'hank', ['docs/UNRELATED.md'], subject='hank-keeps-this')
    before = io.open(os.path.join(mirror, 'hank.json'), encoding='utf-8').read()
    rc, out = run(mirror, 'check', 'tooling', 'anything at all', '--no-fetch')
    after = io.open(os.path.join(mirror, 'hank.json'), encoding='utf-8').read()
    ok("another session's row is byte-identical after a check", after == before)
    # ── ASKED, NOT RE-DERIVED, AND THE BASELINE CAUGHT THE FIRST VERSION ──
    # This was `os.path.basename(ROOT)` with the SAIRN- prefix stripped, which
    # is exactly the rule 527b31bf ABANDONED when it moved identity into a
    # marker in the git dir. In this clone the two agree, so it passed; inside
    # the sabotage harness's worktree the directory is `sairn-sab-XXXX` and the
    # marker still says `cc`, and the arm failed against a tool doing the right
    # thing. A probe that re-implements the rule its subject stopped using is
    # asserting against a copy, so it asks the same module the tool asks.
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import sairn_session_identity as _ident
    me = _ident.session_name()
    mine_path = os.path.join(mirror, me + '.json')
    ok('this session wrote its OWN row', os.path.isfile(mine_path), mirror)
    if os.path.isfile(mine_path):
        row = json.load(io.open(mine_path, encoding='utf-8'))
        ok('...with a claims key', isinstance(row.get('claims'), list), row.keys())
        ok('...stamped so a reader can tell how fresh the mirror is',
           bool(row.get('claims_updated')), row.get('claims_updated'))
        ok('...and every mirrored claim carries its declared file set',
           all('files' in c for c in row.get('claims') or []),
           row.get('claims'))

        ok('...and the row still says it belongs to THIS session -- a mirror '
           'that mislabels its owner corrupts the one key the registry is '
           'partitioned by', row.get('session') == me, row.get('session'))

    # ── 6b. THE INNER GUARD GETS ITS OWN ARM, because the outer one hides it.
    # sairn_claim.registry_claims() wraps the whole read in its own try/except,
    # so read_claims() could raise on every call and the claim tool would still
    # fail open -- real defence in depth, and it meant the five fail-open arms
    # above were all testing the OUTER guard. A control planting a raise inside
    # read_claims() ran SILENT against them, which is how this was found.
    # Asserted directly so both layers are held, not just the one that happens
    # to be outermost.
    # STATUS_DIR IS SET ON THE MODULE, NOT THROUGH THE ENVIRONMENT. The first
    # version set the env var and called importlib.reload(), and the arm came
    # back holding THIS CLONE'S REAL cc row -- so it had read the live registry
    # while claiming to read a corrupt fixture. A probe that silently reaches
    # the real registry is the one thing this file's header promises it never
    # does, and it was one assertion away from passing.
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import sairn_status as _st
    _real_dir = _st.STATUS_DIR
    try:
        # FRESH FIXTURES, NOT THE ONES THE ARMS ABOVE USED, and the reason is
        # a side effect of the very change under test: `check` now MIRRORS
        # this session's own claims into whatever SAIRN_STATUS_DIR it is
        # given, so `bad/` is no longer corrupt-only -- it has a perfectly
        # valid cc.json in it that an earlier arm caused the tool to write.
        # Reusing it made read_claims() correctly return that row and the arm
        # read it as a failure to fail open. A probe whose fixtures are
        # mutated by its own subject has to stop sharing them.
        inner_bad = os.path.join(tmp, 'inner-corrupt')
        os.makedirs(inner_bad)
        with io.open(os.path.join(inner_bad, 'hank.json'), 'w',
                     encoding='utf-8') as fh:
            fh.write('{not json at all')
        for label, d in (('a corrupt row', inner_bad),
                         ('a directory that is not there',
                          os.path.join(tmp, 'inner-does-not-exist'))):
            _st.STATUS_DIR = d
            ok('read_claims() itself returns [] on %s rather than raising, so '
               'the INNER guard is held too' % label,
               _st.read_claims(exclude='nobody') == [], d)
    except Exception as e:                                       # noqa: BLE001
        ok('read_claims() itself fails open', False,
           '%s: %s' % (type(e).__name__, e))
    finally:
        _st.STATUS_DIR = _real_dir

    # ── 6c. THE HEARTBEAT: STALENESS BY LIVENESS, NOT BY A FIXED TIMEOUT ──
    # MEASURED on the session that built this: a claim taken for 9.96 hours of
    # continuous work read as ABANDONED to every other clone for about six of
    # them, because the only rule was four hours from the moment it was taken.
    # The same number fails the other way -- a session that crashes at minute
    # two holds its claim for the remaining three hours and fifty-eight.
    #
    # THE CONTRACT IS THE THREE-VALUED `_alive`, so it is asserted directly:
    # a process answer beats age in BOTH directions, and unknown falls back to
    # the heartbeat rather than to the claim time.
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import sairn_claim as _C
    ten_h = _C.now() - 10 * 3600
    base = {'status': 'active', 'claimed_at_epoch': ten_h}
    ok('a TEN-HOUR-OLD claim whose session is still RUNNING is still held -- '
       'the case that read as abandoned for six hours tonight',
       _C.is_active(dict(base, _alive=True)) is True)
    ok('a ONE-MINUTE-OLD claim whose session is GONE is released NOW, not in '
       'three hours and fifty-nine minutes',
       _C.is_active({'status': 'active',
                     'claimed_at_epoch': _C.now() - 60,
                     '_alive': False}) is False)
    ok('with liveness UNKNOWN a RECENT HEARTBEAT keeps an old claim held',
       _C.is_active(dict(base, _alive=None,
                         _heartbeat=_C.now() - 60)) is True)
    ok('...and a STALE heartbeat does not, so an abandoned row still expires',
       _C.is_active(dict(base, _alive=None,
                         _heartbeat=ten_h)) is False)
    ok('a claim with NO liveness and NO heartbeat falls back to the claim '
       'time exactly as before, so a git claim is unaffected',
       _C.is_active(dict(base)) is False
       and _C.is_active({'status': 'active',
                         'claimed_at_epoch': _C.now() - 60}) is True)
    ok('and a RELEASED claim is still released whatever liveness says -- a '
       'running process must not resurrect finished work',
       _C.is_active({'status': 'released', 'claimed_at_epoch': _C.now(),
                     '_alive': True}) is False)

    # END TO END: a row whose owning process is GONE must stop blocking, and
    # the pid is one nothing on this machine can be running.
    dead = os.path.join(tmp, 'dead')
    os.makedirs(dead)
    write_row(dead, 'hank', ['docs/CRITICALITY-TIERS.md'])
    _p = os.path.join(dead, 'hank.json')
    _row = json.load(io.open(_p, encoding='utf-8'))
    _row['claude_pid'] = 999999
    _row['claude_start'] = 1
    with io.open(_p, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(_row, indent=1))
    rc, out = run(dead, 'check', 'tooling', MINE, '--no-fetch')
    ok('end to end: a registry claim whose PROCESS IS GONE does not block, '
       'however recently it was taken', 'BLOCKED' not in out, out[:300])

    # And the heartbeat is actually written by the tool, not just read.
    beat = os.path.join(tmp, 'beat')
    os.makedirs(beat)
    rc, out = run(beat, 'check', 'tooling', 'anything', '--no-fetch')
    _mine = os.path.join(beat, me + '.json')
    if os.path.isfile(_mine):
        _r = json.load(io.open(_mine, encoding='utf-8'))
        ok('the tool STAMPS a heartbeat, so "still working" is evidence '
           'rather than an assumption', bool(_r.get('claims_heartbeat')),
           sorted(_r.keys()))
    else:
        ok('the tool STAMPS a heartbeat', False, 'no row written at ' + _mine)

    # ── 7. A FILE INTERSECTION IS AN OVERLAP IN ITS OWN RIGHT. Before this
    # ── change the loop skipped on `if not shared: continue` BEFORE reaching
    # ── the file check, which worked only because a path tokenises into the
    # ── task string. Asserted directly so a future FILES: syntax that stores
    # ── paths outside the prose cannot remove the accident silently.
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import sairn_claim as C
    hit = C.overlaps({'subject': 'zzz', 'task': 'FILES: docs/CRITICALITY-TIERS.md'},
                     'qqq', 'FILES: docs/CRITICALITY-TIERS.md')
    ok('overlaps() reports the shared FILE explicitly, not only its word '
       'fragments', any(str(h).startswith('FILE:') for h in hit), sorted(hit))

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('\n%d failure(s)' % len(FAILS))
for f in FAILS:
    print('  - ' + f)
sys.exit(1 if FAILS else 0)
