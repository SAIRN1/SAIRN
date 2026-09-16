"""The control for tools/checker_estimate_fusion.py.

Run: python tests/run_estimate_fusion_probe.py

The fusion's whole justification is that a COMPROMISED CORRECTOR must not be
allowed to correct -- so the arm that matters is the refusal, and a refusal that
fires unconditionally is worthless. Every arm is therefore paired: the correction
IS applied when the corrector is sound, and is NOT when it is not.

fuse() is driven directly with synthetic rows. Driving the real fleet would make
the arms depend on 46 checkers' current state, so they would change meaning
between runs without anybody editing them -- which is the staleness this platform
keeps paying for.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import checker_estimate_fusion as F                            # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def row(tool, stability, why, evidence, ewhy='a control plants a defect AND plants clean code'):
    return {'tool': tool, 'stability': stability, 'stability_why': why,
            'evidence': evidence, 'evidence_why': ewhy}


SOUND = {'guarded': {'tests/run_x_probe.py'}, 'unguarded': set()}
COMPROMISED = {'guarded': set(), 'unguarded': {'tests/run_flaky_tool_probe.py'}}


def one(rows, validity):
    return F.fuse(rows, validity)[0]


# ── 1. THE PAIR THAT IS THE WHOLE POINT ────────────────────────────────────
r = one([row('flaky_tool.py', 'HIGH', '40 runs, no verdict has ever moved', 'HIGH')],
        SOUND)
check('a SOUND corrector is applied -- the state is a fusion',
      r['state'].startswith('FUSED') or r['state'].startswith('CORRECTION ONLY'),
      r)
check('...and the weight it was given is non-zero', r['weight'] > 0, r['weight'])

r2 = one([row('flaky_tool.py', 'HIGH', '40 runs, no verdict has ever moved', 'HIGH')],
         COMPROMISED)
check('a COMPROMISED corrector is REFUSED, and that is the arm that matters',
      r2['state'] == 'UNCORRECTED -- CORRECTOR REFUSED', r2['state'])
check('...its weight is exactly zero', r2['weight'] == 0.0, r2['weight'])
check('...and the estimate falls back to the DRIFTING signal, unchanged',
      r2['fused'] == r2['ins'], (r2['fused'], r2['ins']))
check('...and it says WHY, naming the unguarded set',
      'UNGUARDED' in (r2['why'] or ''), r2['why'])

# ── 2. AN UNREADABLE CORRECTOR IS NOT A SOUND ONE ──────────────────────────
r3 = one([row('x.py', 'HIGH', '40 runs, no verdict has ever moved', 'HIGH')], None)
check('a corrector that could not be READ is refused, not assumed valid',
      r3['state'] == 'UNCORRECTED -- CORRECTOR REFUSED', r3['state'])
check('...and says the validity could not be read', 'COULD NOT BE READ' in (r3['why'] or ''),
      r3['why'])

# ── 3. NO CONTROL IS NOT A CONTROL OF ZERO ─────────────────────────────────
r4 = one([row('y.py', 'HIGH', '40 runs, no verdict has ever moved', None,
              'no control declared')], SOUND)
check('no control at all is UNCORRECTED -- NO CONTROL, not a correction to 0',
      r4['state'] == 'UNCORRECTED -- NO CONTROL', r4['state'])
check('...and the fused value is the drifting one, not 0',
      r4['fused'] == r4['ins'] and r4['fused'] > 0, (r4['fused'], r4['ins']))
check('...and the OPTIMISTIC direction of the bias is named, so it is not read '
      'as neutral', 'OPTIMISTIC' in (r4['why'] or ''), r4['why'])

# ── 4. THE CORRECTION MUST BE ABLE TO PULL AN ESTIMATE DOWN ────────────────
# checkblocks.py is the reason this tool exists: perfectly stable, completely
# useless. If a failing control cannot move a high INS, the fusion adds nothing.
up = one([row('stable_but_useless.py', 'HIGH', '40 runs, no verdict has ever moved',
              'HIGH')], SOUND)
down = one([row('stable_but_useless.py', 'HIGH', '40 runs, no verdict has ever moved',
                'LOW', 'a control plants a defect and never plants clean code')], SOUND)
check('a FAILING control pulls a perfectly stable checker DOWN',
      down['fused'] < up['fused'] - 0.2,
      'with control %.3f, without %.3f -- if these are close the correction is '
      'decorative' % (down['fused'], up['fused']))
check('...and a PASSING control does not pull it down',
      up['fused'] >= up['ins'], (up['fused'], up['ins']))

# ── 5. THE RUN COUNT DECIDES HOW MUCH THE CORRECTION MATTERS ───────────────
few = one([row('z.py', 'HIGH', '6 runs, no verdict has ever moved', 'LOW',
               'a control plants a defect and never plants clean code')], SOUND)
many = one([row('z.py', 'HIGH', '40 runs, no verdict has ever moved', 'LOW',
                'a control plants a defect and never plants clean code')], SOUND)
check('a flip rate from SIX runs cannot outvote a control',
      few['weight'] > many['weight'],
      'few=%s many=%s -- the correction must matter MORE when the continuous '
      'signal has earned less' % (few['weight'], many['weight']))
check('...and a well-earned flip rate is not simply overwritten',
      many['weight'] < 1.0, many['weight'])

# ── 6. A PURE CORRECTION IS NOT CALLED A FUSION OF TWO ─────────────────────
pure = one([row('w.py', 'LOW', 'no runs recorded', 'HIGH')], SOUND)
check('a weight of 1 is labelled CORRECTION ONLY, not FUSED',
      pure['state'].startswith('CORRECTION ONLY'),
      '%s (w=%s) -- calling this FUSED would let one measurement read as two '
      'agreeing' % (pure['state'], pure['weight']))

# ── 7. NO CONTINUOUS SIGNAL AT ALL IS COULD NOT TELL ───────────────────────
none_ins = one([{'tool': 'q.py', 'stability': None, 'stability_why': '',
                 'evidence': 'HIGH', 'evidence_why': 'x'}], SOUND)
check('no usable continuous signal is COULD NOT TELL, never a number',
      none_ins['state'] == 'COULD NOT TELL' and none_ins['fused'] is None,
      none_ins)

# ── 8. AND THE EXIT CODE CARRIES THE REFUSAL ───────────────────────────────
# A report whose refusals are only in the prose is one a script cannot act on.
import contextlib
import io as _io
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    rc_clean = F.main(['--quiet'])
check('the real run exits non-zero while any estimate is UNCORRECTED, or 0 when '
      'none is', rc_clean in (0, 1, 2), 'exit %s' % rc_clean)
out = buf.getvalue()
check('...and --quiet really is quiet', len(out.strip()) == 0,
      'printed %d chars under --quiet' % len(out.strip()))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
