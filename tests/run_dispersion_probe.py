"""The control for the dispersion test in tools/defect_dispersion.py.

Run: python tests/run_dispersion_probe.py

A concentration index (Gini, top-20 share) is high for ANY sparse count over a
large population, including a perfectly random one. The dispersion test was added
to tell those apart, so the only thing that makes it worth having is that it
answers DIFFERENTLY on the two shapes -- and the only way to know that is to
feed it both.

BOTH DIRECTIONS ON EVERY ARM. A test that answered OVER-DISPERSED
unconditionally would pass every "it found the cluster" arm, and one that
answered INDISTINGUISHABLE unconditionally would pass every "it stayed quiet"
arm. The pairs are the whole content.

FIXTURES ARE GENERATED FROM A FIXED SEED, not sampled live: a probe whose
verdict changes run to run cannot say whether the tool changed or the dice did.
"""
import os
import random
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import defect_dispersion as D                                  # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def counts(vals):
    """{unit: n} from a list of per-unit counts, zeros omitted as the register
    omits them -- which is exactly the shape the real data arrives in."""
    return {('u%d' % i): v for i, v in enumerate(vals) if v > 0}


# ── 1. A POISSON SAMPLE MUST NOT READ AS CLUSTERED ─────────────────────────
# The failure this arm exists for: the real register shows Gini 0.97 on commits.
# If the dispersion test also said OVER-DISPERSED on pure chance at the same
# rate, it would be a second copy of the Gini and would have added nothing.
rng = random.Random(20260915)
N = 1232
LAM = 77.0 / N          # the real platform rate


def poisson(rng, lam):
    """Knuth. lam here is ~0.0625, so this terminates in one or two steps."""
    import math
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


pois = [poisson(rng, LAM) for _ in range(N)]
idx, k, verdict, why = D.dispersion(counts(pois), N)
check('a POISSON sample at the platform rate is NOT called clustered',
      verdict == 'INDISTINGUISHABLE FROM POISSON',
      'verdict=%s index=%s why=%s' % (verdict, idx, why))
check('...and its GINI is high anyway, which is the whole point',
      D.gini(pois) > 0.9,
      'gini=%.3f -- if this is low the fixture is not sparse and the arm above '
      'proves nothing' % D.gini(pois))
check('...and no NB k is produced for it, rather than a clamped one',
      k is None or k > 5,
      'k=%s -- a small k on a Poisson sample would be a fabricated '
      'superspreading figure' % k)

# ── 2. A CLUSTERED SAMPLE MUST READ AS CLUSTERED ───────────────────────────
# Same total, same population, all of it in a few units.
clustered = [0] * N
for i in range(5):
    clustered[i] = 15          # 75 of 77 in five units
clustered[5] = 2
idx2, k2, verdict2, why2 = D.dispersion(counts(clustered), N)
check('a heavily CLUSTERED sample at the same total IS called over-dispersed',
      verdict2 == 'OVER-DISPERSED', 'verdict=%s index=%s' % (verdict2, idx2))
check('...and its index is far above the Poisson one',
      idx2 > (idx or 0) * 5, 'clustered=%.2f poisson=%.2f' % (idx2, idx or 0))
check('...and NB k is small, which is what "superspreading" means',
      k2 is not None and k2 < 1, 'k=%s' % k2)
check('...while its GINI is barely different from the Poisson sample\'s',
      abs(D.gini(clustered) - D.gini(pois)) < 0.12,
      'clustered gini=%.3f poisson gini=%.3f -- if these differ a lot then '
      'Gini WOULD have separated the shapes and the dispersion test is less '
      'necessary than claimed' % (D.gini(clustered), D.gini(pois)))

# ── 3. THE REFUSALS, AND THEY ARE NOT "INDISTINGUISHABLE" ──────────────────
idx3, k3, verdict3, _w = D.dispersion({'a': 1, 'b': 2}, None)
check('an unknown population is NOT TESTED, not a verdict', verdict3 == 'NOT TESTED',
      verdict3)
check('...and produces no index at all', idx3 is None, idx3)

idx4, k4, verdict4, why4 = D.dispersion({'a': 40, 'b': 20, 'c': 17}, 3)
check('THREE units is NOT TESTED -- UNDERPOWERED, not "indistinguishable"',
      verdict4.startswith('NOT TESTED'), verdict4)
check('...and says the band is wider than the value it tests against',
      'wider than the value' in (why4 or ''), why4)

idx5, k5, verdict5, _w = D.dispersion({}, 100)
check('no defects at all is NOT TESTED, not a clean bill of health',
      verdict5 == 'NOT TESTED', verdict5)

# ── 4. BACKWARD TRACING ────────────────────────────────────────────────────
# A cluster with a genuinely shared, UNUSUAL attribute must be reported as
# informative; a cluster sharing the platform's most common value must not.
recs_common = ([{'commit': 'C1', 'app': 'stonedesk', 'layer': 'product',
                 'detection_method': 'code-review', 'injection_phase': 'design',
                 'severity': 'moderate', 'files': ['a.js'], 'date': '2026-09-01',
                 'subject': 's', 'summary': 'x'}] * 2
               + [{'commit': 'C%d' % i, 'app': 'stonedesk', 'layer': 'product',
                   'detection_method': 'code-review', 'injection_phase': 'design',
                   'severity': 'moderate', 'files': ['b.js'], 'date': '2026-09-01',
                   'subject': 's', 'summary': 'x'} for i in range(2, 20)])
cl = D.backward_trace(recs_common)
check('a cluster IS found when a commit carries more than one defect',
      len(cl) == 1 and cl[0]['size'] == 2, cl)
if cl:
    inf = [x for x in cl[0]['shared'] if x['informative']]
    check('...and an attribute shared by MOST of the register is NOT called '
          'informative', inf == [],
          'these were called informative: %r' % inf)

recs_rare = ([{'commit': 'R1', 'app': 'sairnlaw', 'layer': 'product',
               'detection_method': 'probe', 'injection_phase': 'design',
               'severity': 'high', 'files': ['law.js', 'shared.js'],
               'date': '2026-09-02', 'subject': 's', 'summary': 'x'}] * 3
              + [{'commit': 'R%d' % i, 'app': 'stonedesk', 'layer': 'product',
                  'detection_method': 'code-review', 'injection_phase': 'design',
                  'severity': 'moderate', 'files': ['b.js'], 'date': '2026-09-01',
                  'subject': 's', 'summary': 'x'} for i in range(2, 30)])
cl2 = D.backward_trace(recs_rare)
check('a cluster sharing a RARE attribute has it reported as informative',
      cl2 and any(x['field'] == 'app' and x['informative'] for x in cl2[0]['shared']),
      cl2[0]['shared'] if cl2 else None)
check('...and the files common to EVERY member are named',
      cl2 and set(cl2[0]['common_files']) == {'law.js', 'shared.js'},
      cl2[0]['common_files'] if cl2 else None)

no_cluster = [{'commit': 'X%d' % i, 'app': 'a', 'layer': 'product',
               'detection_method': 'm', 'injection_phase': 'design',
               'severity': 's', 'files': [], 'date': '2026-09-01',
               'subject': 's', 'summary': 'x'} for i in range(10)]
check('NO cluster is invented when every commit carries exactly one defect',
      D.backward_trace(no_cluster) == [], D.backward_trace(no_cluster))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
