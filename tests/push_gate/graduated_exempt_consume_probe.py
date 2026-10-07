"""Only the mode that can actually let a push through may SPEND the exemption.

One `git push` from a Bash tool call runs tools/sairn_push_gate_hook.py TWICE:
once as a PreToolUse hook reading the command text, once as the real
.githooks/pre-push. Both read ONE store file under
~/SAIRN-SESSION-LOCKS/gate-exemptions/, and until 2026-10-07 both DELETED the
pending record on a match. The half that cannot push anything was eating the
token, so the observed sequence was:

    push 1   pretooluse: no record -> soft capture, writes, DENIES
             (prepush never runs -- the command itself was refused)
    push 2   pretooluse: record matches -> CONSUMES, allows
             prepush:    store now empty -> soft capture, writes, DENIES
    push 3   identical to push 2, forever

SAIRN_GATE_EXEMPT=seed was therefore ungrantable from the ordinary context, and
nothing in the output said so: every attempt printed SOFT CAPTURE, which reads
as "you have not pushed twice yet". The only way to reach the feature was from
a context where the PreToolUse half does not run, which is not a property
anybody could infer from the message.

THE FIX IS AUTHORITY, NOT A SECOND STORE FILE. `prepush` is the mode git will
not push without, so it is the only one that deletes. `pretooluse` reads the
same record, grants on a match, and leaves it to be spent. Two store files
would have worked for this sequence and been wrong the moment a third mode
existed; and it would have let a pretooluse grant and a prepush grant come
from two independent tokens, which is two exemptions wearing one flag.

ARM 1 IS THE ABLATION AND IT IS THE POINT. It forces consume=True in both
halves -- the pre-fix behaviour -- and asserts that prepush DENIES. An arm that
only ever sees the fixed code cannot tell you the fix did anything.

WHAT THIS PROBE DOES NOT COVER, stated rather than discovered later:
  * the real two-process sequence. Both modes are driven in ONE python process
    by setting MODE, so a defect that depends on process boundaries (file
    locking, a partial write) is invisible here.
  * the 15-minute TTL. The window is read from EXEMPT_TTL_SECONDS and not
    exercised; an arm that waits is an arm nobody runs.
  * whether every OTHER check still ran on the granted push. That is the
    hook's own report and is not observable from this function.

NOTHING IN THE REPO IS MUTATED. EXEMPT_DIR is redirected to a temp directory
for the whole run, so no arm can touch the live exemption store -- which
matters more here than usual, because the live store is what a concurrent
session's push depends on.

Run: python tests/push_gate/graduated_exempt_consume_probe.py
Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOK = os.path.join(ROOT, 'tools', 'sairn_push_gate_hook.py')

if not os.path.isfile(HOOK):
    print('COULD NOT RUN -- %s is absent. This probe is about that file and '
          'reports nothing without it.' % HOOK)
    sys.exit(2)


def _git(*a):
    r = subprocess.run(['git'] + list(a), cwd=ROOT, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.stdout.strip() if r.returncode == 0 else ''


TIP = _git('rev-parse', 'HEAD')
OTHER = _git('rev-parse', 'HEAD~1')
if len(TIP) != 40 or len(OTHER) != 40:
    print('COULD NOT RUN -- need two resolvable commits; got %r and %r. A '
          'shallow clone or an unborn branch is a could-not-run, not a pass.'
          % (TIP, OTHER))
    sys.exit(2)

# The hook reads sys.argv at import time; 'prepush' is selected by a flag and
# this probe sets MODE directly instead, so argv must stay inert.
_argv = sys.argv
sys.argv = ['graduated_exempt_consume_probe']
try:
    _spec = importlib.util.spec_from_file_location('gate_under_probe', HOOK)
    G = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(G)
finally:
    sys.argv = _argv

TMP = tempfile.mkdtemp(prefix='graduated-exempt-probe-')
G.EXEMPT_DIR = TMP
STORE = G._exempt_path('seed')
if os.path.commonprefix([os.path.abspath(STORE), os.path.abspath(TMP)]) != os.path.abspath(TMP):
    print('COULD NOT RUN -- the store path %r is not inside the temp dir. '
          'Refusing rather than risk writing the live exemption store.' % STORE)
    sys.exit(2)


def clear():
    for f in os.listdir(TMP):
        os.remove(os.path.join(TMP, f))


arms = []

# ── ARM 1: THE ABLATION. The pre-fix behaviour, and it must DENY. ──────────
clear()
G.MODE = 'pretooluse'
a1 = G.graduated_exempt('seed', TIP, consume=True)      # soft capture
a2 = G.graduated_exempt('seed', TIP, consume=True)      # CONSUMES
G.MODE = 'prepush'
a3 = G.graduated_exempt('seed', TIP, consume=True)      # nothing left
arms.append(('ABLATION: when pretooluse consumes, prepush is never granted',
             (a1, a2, a3), (False, True, False)))

# ── ARM 2: the fixed sequence, defaults taken from MODE. ───────────────────
clear()
G.MODE = 'pretooluse'
b1 = G.graduated_exempt('seed', TIP)                    # soft capture, denies
b2 = G.graduated_exempt('seed', TIP)                    # grants, does NOT spend
G.MODE = 'prepush'
b3 = G.graduated_exempt('seed', TIP)                    # grants AND spends
arms.append(('the confirming push reaches prepush and IS granted',
             (b1, b2, b3), (False, True, True)))
arms.append(('the token is spent exactly once -- the store is gone after prepush',
             os.path.isfile(STORE), False))

# ── ARM 3: spent is spent. ─────────────────────────────────────────────────
G.MODE = 'prepush'
arms.append(('a spent token does not grant a second push',
             G.graduated_exempt('seed', TIP), False))

# ── ARM 4: the pin still binds, which is the whole safety property. ───────
clear()
G.MODE = 'pretooluse'
G.graduated_exempt('seed', TIP)
G.MODE = 'prepush'
arms.append(('a DIFFERENT tip is not granted by this pin',
             G.graduated_exempt('seed', OTHER), False))

# ── ARM 5: a different CHECK name does not share the token. ────────────────
clear()
G.MODE = 'pretooluse'
G.graduated_exempt('seed', TIP)
G.MODE = 'prepush'
arms.append(('another check name does not spend seed\'s token',
             G.graduated_exempt('tier-a', TIP), False))

# ── ARM 6: an unresolvable tip can never be granted (fail closed). ────────
clear()
G.MODE = 'prepush'
arms.append(('an unresolvable tip is refused rather than pinned to nothing',
             G.graduated_exempt('seed', 'no-such-ref-at-all'), False))

shutil.rmtree(TMP, ignore_errors=True)

passed = 0
for name, got, want in arms:
    ok = got == want
    passed += ok
    print('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
    if not ok:
        print('       wanted %r, got %r' % (want, got))
print('graduated_exempt consume probe: %d/%d arm(s) pass' % (passed, len(arms)))
sys.exit(0 if passed == len(arms) else 1)
