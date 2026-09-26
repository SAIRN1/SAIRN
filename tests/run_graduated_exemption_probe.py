"""Item 101 on the push gate: does the scoped exemption really scope, and does
the first push really get refused?

    python tests/run_graduated_exemption_probe.py

THE TWO ARMS THAT MATTER ARE THE REFUSALS, not the grant.

A graduated override whose SOFT CAPTURE phase silently succeeds is the blanket
flag with extra steps, and it would look identical in the bypass log on the
confirming push. So the first-push-is-refused arm is driven directly, and so is
the one that decides whether this design is worth anything at all: an exemption
pinned to a tip sha must STOP APPLYING when the sha moves. If it survives an
amend, the "settling" phase is decoration.

The third is the fail-safe direction. Everything else in sairn_push_gate_hook.py
fails OPEN -- a gate that crashes closed gets disabled and then protects
nothing. The exemption store must fail CLOSED, because a store that cannot be
read granting an exemption would be a gate that disables itself by breaking.

NOTHING HERE PUSHES ANYTHING. The graduated logic is pure enough to drive
directly: exempt_requested() takes a command string, graduated_exempt() takes a
check name and a sha. The store is redirected at a temporary directory for the
duration.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_push_gate_hook as g                                  # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:300]))
    if not cond:
        fails.append(name)


print('item 101 -- graduated exemption: soft capture, settling, hard capture')

# ── 1. WHAT THE COMMAND ASKS FOR ────────────────────────────────────────────
print('\n1. the request is read from the command, and only for a named check')

check('a scoped request at the front of the command is read',
      g.exempt_requested('SAIRN_GATE_EXEMPT=seed git push origin main') == 'seed')
check('...and after a separator too',
      g.exempt_requested('git add -A && SAIRN_GATE_EXEMPT=seed git push') == 'seed')
check('a check this hook does not offer an exemption for is REFUSED, not '
      'honoured -- a wildcard would be the blanket flag under a better name',
      g.exempt_requested('SAIRN_GATE_EXEMPT=tier-a-review git push') is None)
check('SAIRN_GATE_EXEMPT=all is not a thing',
      g.exempt_requested('SAIRN_GATE_EXEMPT=all git push') is None)
check('no request is None, not a default',
      g.exempt_requested('git push origin main') is None)

# THE QUOTED-MENTION ARM. This repo's commit messages and this very file quote
# the variable name in prose, and a commit message must not disable a check.
check('A QUOTED MENTION DOES NOT COUNT -- a commit message naming the variable '
      'cannot grant an exemption',
      g.exempt_requested('git commit -m "used SAIRN_GATE_EXEMPT=seed" && git push') is None,
      g.exempt_requested('git commit -m "used SAIRN_GATE_EXEMPT=seed" && git push'))
check('...and the same rule the blanket override already keeps still holds for it',
      g.override_in_command('git commit -m "SAIRN_SEED_GATE=off" && git push') is False)

# ── 2. SOFT CAPTURE, SETTLING, HARD CAPTURE ─────────────────────────────────
print('\n2. three phases, and the first one REFUSES')

tmp = tempfile.mkdtemp(prefix='gate-exempt-probe-')
real_dir, real_ttl = g.EXEMPT_DIR, g.EXEMPT_TTL_SECONDS
try:
    g.EXEMPT_DIR = tmp
    TIP = 'a' * 40

    first = g.graduated_exempt('seed', TIP)
    check('SOFT CAPTURE: the FIRST push is REFUSED -- contact, not commitment',
          first is False)
    check('...and the request is recorded, pinned to the tip',
          os.path.isfile(g._exempt_path('seed')))
    rec = json.load(io.open(g._exempt_path('seed'), encoding='utf-8'))
    check('...with the check name and the sha it is bound to',
          rec['check'] == 'seed' and rec['tip'] == TIP, rec)

    second = g.graduated_exempt('seed', TIP)
    check('HARD CAPTURE: the SECOND push, same sha, is granted',
          second is True)
    check('...and the exemption is CONSUMED -- single use, so a third push '
          'starts the cycle over rather than riding the same grant',
          not os.path.isfile(g._exempt_path('seed')))
    third = g.graduated_exempt('seed', TIP)
    check('...proven: the third push is refused again', third is False)

    # ── THE ARM THAT DECIDES WHETHER SETTLING MEANS ANYTHING ────────────────
    os.remove(g._exempt_path('seed'))
    g.graduated_exempt('seed', TIP)                       # soft capture on TIP
    moved = g.graduated_exempt('seed', 'b' * 40)          # ...then amend
    check('SETTLING IS REAL: an exemption taken on one sha does NOT apply after '
          'an amend or a rebase -- the push must stop moving before it is let '
          'through', moved is False, moved)

    # Expiry.
    os.remove(g._exempt_path('seed'))
    g.graduated_exempt('seed', TIP)
    rec = json.load(io.open(g._exempt_path('seed'), encoding='utf-8'))
    rec['at'] = time.time() - (g.EXEMPT_TTL_SECONDS + 60)
    io.open(g._exempt_path('seed'), 'w', encoding='utf-8').write(json.dumps(rec))
    check('an exemption older than the window is not honoured -- it is a '
          'confirmation, not a standing grant',
          g.graduated_exempt('seed', TIP) is False)

    # ── 3. FAIL CLOSED, WHICH IS THE OPPOSITE OF THE REST OF THIS HOOK ──────
    print('\n3. the store fails CLOSED -- more checking, never less')
    io.open(g._exempt_path('seed'), 'w', encoding='utf-8').write('{not json')
    check('a MALFORMED record grants nothing',
          g.graduated_exempt('seed', TIP) is False)
    os.remove(g._exempt_path('seed'))
    io.open(g._exempt_path('seed'), 'w', encoding='utf-8').write(
        json.dumps({'check': 'seed', 'at': time.time()}))
    check('a record with NO tip grants nothing -- an unpinned exemption is a '
          'standing one', g.graduated_exempt('seed', TIP) is False)

    g.EXEMPT_DIR = os.path.join(tmp, 'nonexistent', '\0bad')
    check('a store that cannot be read OR written grants nothing and does not '
          'raise -- a hook that crashed here would block a legitimate push',
          g.graduated_exempt('seed', TIP) is False)
finally:
    g.EXEMPT_DIR, g.EXEMPT_TTL_SECONDS = real_dir, real_ttl
    shutil.rmtree(tmp, ignore_errors=True)

# ── 4. THE BLANKET FORM IS STILL THERE, AND STILL SAYS WHAT IT IS ───────────
print('\n4. the blanket form is not removed, and the scoped one is offered first')

src = io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
              encoding='utf-8').read()
code = '\n'.join(l for l in src.split('\n') if not l.lstrip().startswith('#'))
check('the blanket override still exists -- removing the only escape hatch '
      'mid-incident is its own failure mode',
      'OVERRIDE_RE' in code and 'override_in_command' in code)
check('the seed refusal offers the SCOPED form before the blanket one',
      code.index('SCOPED, GRADUATED EXEMPTION') < code.index('BLANKET, STILL AVAILABLE'))
check('the blanket form is logged as ALL and says so in its own reason text',
      "_record_bypass('ALL'" in code)
check('the scoped grant is logged against the NAMED check, not ALL',
      "_record_bypass('seed-gate'" in code)
check('the exemption directory is OUTSIDE every clone, so a pending grant '
      'cannot be committed and shared',
      'SAIRN-SESSION-LOCKS' in code and 'EXEMPT_DIR' in code)

# CONTROL on the comment-stripping, so the arms above are judging code.
check('CONTROL: the stripping left the code behind',
      'def graduated_exempt' in code and len(code) > 20000)

print('')
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('ALL ARMS PASS')
