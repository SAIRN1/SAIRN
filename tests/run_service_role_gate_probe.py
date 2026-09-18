CONTROLS_FOR = ['tools/service_role_tier_a_gate_check.py']
#!/usr/bin/env python
"""tests/run_service_role_gate_probe.py -- controls for
tools/service_role_tier_a_gate_check.py.

THE SUBJECT REPORTS CLEAN TODAY, WHICH IS EXACTLY WHEN A CHECKER IS WORTH THE
LEAST. Three of its eight fixtures exist because the classifier was wrong on a
REAL file and the wrongness was only caught by asking why a module had appeared
-- or vanished -- between two runs:

  bridge.js      `invoices` in header prose and in `body.invoices`, reported as
                 an ungated Tier A write. It writes to `bridge_data`.
  sv-witness.js  killed by the over-correction that fixed bridge.js. Its only
                 reference is `LOCKED_RESOURCES = { sv_controlled: true }` -- a
                 genuine reference, and suppressing it to silence one false
                 alarm on the DEA-relevant witnessing lock was a bad trade.
  send-reminder  writes in helpers ABOVE the handler, CRON_SECRET first INSIDE
                 it. A whole-file offset comparison called that ungated.

Exit 0 all arms passed, 1 otherwise.
"""

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
SUBJECT = os.path.join(REPO, 'tools', 'service_role_tier_a_gate_check.py')

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('    ok   %s' % label)
    else:
        FAILS.append(label)
        print('    FAIL %s' % label)
        if detail:
            print('         %s' % str(detail)[:400])


import service_role_tier_a_gate_check as S   # noqa: E402


print('\nA. every verdict, on its own')
bad = S.self_check(verbose=False)
ok('all fixtures classify as declared', not bad, bad)
# ── THIS ARM PINNED A COPY OF THE VERDICT LIST AND THE COPY WENT STALE ──────
# It read `== {'GATED', 'UNGATED', 'PUBLIC_BY_DESIGN', 'NO_WRITE', None}` and
# went red the day v4 added a FIFTH verdict, COULD_NOT_TELL, with a fixture for
# it. The arm was doing its job -- a verdict list is exactly the thing that
# should not change silently -- but it was doing it against a hardcoded copy in
# a different file from the returns it describes, which is the pinned-list
# drift shape `tools/pinned_list_drift_check.py` exists for.
#
# The list now lives in the subject as S.VERDICTS, and this arm asserts THREE
# things instead of one, each derived differently:
#   a) the declared tuple matches what the module's `return '<X>'` sites
#      actually produce -- a lexical scan of the source, not the tuple itself,
#      so a verdict added and not declared is caught;
#   b) the fixtures cover every declared verdict -- so a verdict declared and
#      not exercised is caught;
#   c) None is still in the fixture set, which is the not-a-service-role-file
#      case and is not a verdict.
# A constant classifier still fails (b), which is what the original arm was for.
returned = set(re.findall(r"return '([A-Z_]+)'", io.open(SUBJECT, encoding='utf-8').read()))
ok('every verdict the CODE returns is declared in VERDICTS',
   returned == set(S.VERDICTS), sorted(returned ^ set(S.VERDICTS)))
ok('the fixture set reaches every declared verdict plus None -- a constant '
   'would pass a one-sided test',
   set(w for _l, _s, w in S.FIXTURES) == set(S.VERDICTS) | {None},
   sorted(str(w) for _l, _s, w in S.FIXTURES))


print('\nB. it is built THROUGH checker_kit (item 28), not around it')
src = io.open(SUBJECT, encoding='utf-8').read()
ok('it imports the kit rather than re-deriving the contract',
   'from checker_kit import' in src)
for name in ('strip_comments', 'finish', 'tracked', 'EXIT_COULD_NOT_RUN'):
    ok('...and uses %s from it' % name, name in src)
ok('it does NOT hand-roll a comment stripper', 'def strip_comments' not in src)


print('\nC. the three real false positives, pinned')
S.TIER_A = {'sv_controlled', 'dnt_patients', 'invoices'}
v, _d = S.classify('bridge.js',
                   "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
                   "// Body: { invoices? } -- the shape this forwards\n"
                   "const d={ invoices: body.invoices || null };\n"
                   "fetch(rest('bridge_data?on_conflict=shop_id'),{method:'POST'});")
ok('a jsonb KEY whose write targets another table is NOT reported', v is None, v)

v2, d2 = S.classify('sv-witness.js',
                    "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
                    "const LOCKED_RESOURCES = { sv_controlled: true };\n"
                    "verifySessionToken(t);\n"
                    "fetch(rest('sv_controlled?x=1'),{method:'POST'});")
ok('a POLICY REGISTRY key IS still seen when the same resource is written',
   v2 == 'GATED', (v2, d2))

v3, d3 = S.classify('send-reminder.js',
                    "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
                    "async function h(){ return fetch(rest('dnt_patients?x=1'),"
                    "{method:'POST'}); }\n"
                    "module.exports=async(req,res)=>{ "
                    "if(!process.env.CRON_SECRET) return; await h(); };")
ok('a gate inside the handler beats a write in a helper defined above it',
   v3 == 'GATED', (v3, d3))


print('\nD. the direction that must never be softened')
v4, _ = S.classify('x.js', "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
                           "fetch(rest('sv_controlled?x=1'),{method:'POST'});")
ok('no gate anywhere -> UNGATED', v4 == 'UNGATED', v4)
v5, _ = S.classify('y.js', "// Genuinely public, unauthenticated endpoint\n"
                           "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
                           "fetch(rest('dnt_patients?x=1'),{method:'POST'});")
ok('DECLARED public with NO limiter is still UNGATED -- the note is intent, '
   'the limiter is the mechanism', v5 == 'UNGATED', v5)
v6, _ = S.classify('z.js', "// Genuinely public, unauthenticated endpoint\n"
                           "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
                           "rate_limit();\n"
                           "fetch(rest('dnt_patients?x=1'),{method:'POST'});")
ok('...and WITH one it is PUBLIC_BY_DESIGN, not a finding', v6 == 'PUBLIC_BY_DESIGN', v6)


print('\nE. against the real tree')
r = subprocess.run([sys.executable, SUBJECT], capture_output=True, text=True,
                   encoding='utf-8', errors='replace', cwd=REPO)
ok('it runs', r.returncode in (0, 1, 2), r.stderr[-300:])
ok('it prints the population before any verdict',
   'read SUPABASE_SERVICE_ROLE_KEY' in r.stdout, r.stdout[:200])
ok('it states that GATED is an order PROXY and not a proof',
   'order proxy' in r.stdout.lower() or 'ORDER PROXY' in r.stdout, r.stdout[-400:])
ok('it prints its exclusions rather than dropping them silently',
   'excluded:' in r.stdout, r.stdout[-300:])
# A CLEAN run is the weakest signal a checker produces, so the population it
# looked at is asserted -- a scan that silently stopped finding modules would
# otherwise read identically.
ok('it still finds the three known Tier A write paths',
   r.stdout.count('PUBLIC_BY_DESIGN') >= 2 and 'api/sd-data.js' in r.stdout,
   r.stdout[:600])


print('\nF. teeth -- a classifier that can never say UNGATED must not report clean')
TMP = tempfile.mkdtemp(prefix='srg_')
ENV = dict(os.environ, PYTHONPATH=os.path.join(REPO, 'tools'))
try:
    ANCHOR = "    return 'UNGATED', d\n"
    ok('the teeth anchor is present', src.count(ANCHOR) >= 1,
       'anchor stale -- section F tests NOTHING')
    broken = src.replace(ANCHOR, "    return 'GATED', d\n")
    ok('the neutering changed the source', broken != src)
    bp = os.path.join(TMP, 'broken.py')
    io.open(bp, 'w', encoding='utf-8').write(broken)
    rb = subprocess.run([sys.executable, bp], capture_output=True, text=True,
                        encoding='utf-8', errors='replace', cwd=REPO, env=ENV)
    ok('the broken copy runs at all', rb.returncode in (0, 1, 2), rb.stderr[-300:])
    ok('TEETH: it exits COULD NOT RUN (2), never CLEAN (0)', rb.returncode == 2,
       'exit %s\n%s' % (rb.returncode, rb.stdout[-400:]))
    ok('...and says the blind lock failed rather than printing a clean sweep',
       'blind lock failed' in rb.stdout, rb.stdout[:300])
    rg = subprocess.run([sys.executable, SUBJECT, '--self-check'],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', cwd=REPO)
    ok('CONTROL: the real subject passes its own blind lock', rg.returncode == 0,
       rg.stdout[-300:])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the scratch directory is gone', not os.path.isdir(TMP))


print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
