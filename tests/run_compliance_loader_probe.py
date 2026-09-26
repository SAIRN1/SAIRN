"""Does the SAIRNcare compliance loader load the right rules, and refuse the rest?

    python tests/run_compliance_loader_probe.py

THE ARM THAT MATTERS IS THE COVERAGE CAP. Michael capped SAIRNcare's
jurisdiction engine at five states on 2026-09-25 and recorded it inside the
seed as `coverage_cap`. A loader that quietly widened that would be the
decision being re-opened by a tool -- so a rule for a sixth state must be
REFUSED, by name, rather than loaded.

The second is the verification contract. The push gate's own refusal says "a
loader's exit code is not evidence", and this loader answers that by driving
the engine on IDENTICAL inputs before and after. If `answer_changed` ever
returned True for two identical replies, the loader would report success for a
load that did nothing -- which is the 2026-08-27 defect the gate exists for,
reproduced by the tool written to close it.

AND SECTION 4 USED TO PASS WHILE THAT VERIFICATION HAD NEVER RUN (2026-09-26).
It tested the loader's pure helpers against themselves and never tested the
probe's PAYLOAD against what the endpoint requires, so a probe sending `check`
instead of `requirement_type` earned a 400 on every run -- before and after --
and two identical 400s compare equal. The loader reported UNCHANGED every time
it has ever run, including the run where all three West Virginia rules loaded
correctly. Section 4 now reads the endpoint's required-field list OUT OF
api/sd-data.js, which is the only arm that could have caught it.

NOTHING HERE TOUCHES THE NETWORK. select_rules, rule_payload,
verification_probe, answer_changed and probe_verdict are pure; the credential
refusal is driven as a subprocess.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import load_compliance_seed as L                                  # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:300]))
    if not cond:
        fails.append(name)


SEED = L.load_seed()

print('SAIRNcare compliance loader -- what it loads, and what it refuses')

# ── 1. THE COVERAGE CAP ─────────────────────────────────────────────────────
print('\n1. the cap is a decision, and the loader does not widen one')

to_load, refused = L.select_rules(SEED)
check('every rule in the seed is selected, because every seeded state is '
      'inside the cap today',
      len(to_load) == len(SEED['rules']) and not refused,
      (len(to_load), len(SEED['rules']), refused))

sixth = json.loads(json.dumps(SEED))
sixth['rules'].append({
    'rule_id': 'KY-STAFFING-TEST', 'state': 'KY', 'requirement_type': 'staffing',
    'effective_from': '2026-01-01',
    'data': {'authority': {'citation': 'x', 'url': 'https://example.invalid/x'}}})
tl, rf = L.select_rules(sixth)
check('THE ARM THAT MATTERS: a rule for a state OUTSIDE the cap is REFUSED by '
      'name, not loaded',
      len(tl) == len(SEED['rules']) and len(rf) == 1
      and rf[0][0] == 'KY-STAFFING-TEST', (len(tl), rf))
check('...and the refusal says the cap is a decision rather than a backlog',
      'decision' in rf[0][1], rf[0][1])

check('--state narrows to one state and selects only its rules',
      len(L.select_rules(SEED, 'WV')[0]) == 3
      and {r['state'] for r in L.select_rules(SEED, 'WV')[0]} == {'WV'})
check('--state is case-insensitive, because a state code gets typed by hand',
      len(L.select_rules(SEED, 'wv')[0]) == 3)

# ── 2. PROVENANCE IS REQUIRED BEFORE THE NETWORK IS TOUCHED ─────────────────
print('\n2. an unsourced rule is stopped here, not halfway through a load')

noauth = json.loads(json.dumps(SEED))
noauth['rules'] = [json.loads(json.dumps(SEED['rules'][0]))]
noauth['rules'][0]['data']['authority'] = {'citation': 'something'}
tl2, rf2 = L.select_rules(noauth)
check('a rule with a citation but NO resolvable URL is refused before any '
      'POST -- the endpoint refuses it too, and stopping early means no '
      'partial load', not tl2 and len(rf2) == 1, (tl2, rf2))

noauth2 = json.loads(json.dumps(SEED))
noauth2['rules'] = [json.loads(json.dumps(SEED['rules'][0]))]
noauth2['rules'][0]['data']['authority'] = {'url': 'https://example.invalid/x'}
check('...and a URL with no citation is refused too',
      not L.select_rules(noauth2)[0])

# ── 3. THE PAYLOAD IS THE ENDPOINT'S SHAPE ──────────────────────────────────
print('\n3. the payload carries what the endpoint requires')

wv = [r for r in SEED['rules'] if r['state'] == 'WV'][0]
p = L.rule_payload(wv)
for field in ('rule_id', 'state', 'requirement_type', 'effective_from', 'data'):
    check('the payload carries %s, which the endpoint refuses without' % field,
          p.get(field) is not None, p)
check('status defaults to active rather than being omitted',
      L.rule_payload({'rule_id': 'x', 'state': 'WV',
                      'requirement_type': 'staffing',
                      'effective_from': '2026-01-01'})['status'] == 'active')
check('a null facility_class survives as null -- it means "every class in this '
      'state" and must not become a string',
      L.rule_payload({'rule_id': 'x', 'state': 'WV',
                      'requirement_type': 'staffing',
                      'effective_from': '2026-01-01'})['facility_class'] is None)

# ── 4. THE VERIFICATION CONTRACT ────────────────────────────────────────────
# ── REWRITTEN 2026-09-26, AND THE OLD SECTION 4 IS THE LESSON ───────────────
# This section used to pass while the verification it tests HAD NEVER RUN. It
# checked `answer_changed` (pure, and correct) and that the probe's `action` was
# 'evaluate' -- and never once checked the probe's PAYLOAD against what the
# endpoint requires. The probe sent `check` where api/sd-data.js requires
# `requirement_type`, so every probe answered 400 both before and after; two
# identical 400s compare equal, and the loader reported
# "*** UNCHANGED -- nothing this app can use was loaded ***" on every run it has
# ever done, including the one where all three WV rules landed correctly.
#
# A probe that verifies a tool against ITSELF rather than against the interface
# it has to satisfy is the shape here: every arm was green, the tool's own header
# promised "the only evidence that counts", and the evidence was a string
# comparison between two copies of the same refusal. The fix is the arm below
# that reads the required-field list OUT OF api/sd-data.js.
print('\n4. a loader\'s exit code is not evidence -- and the PROBE has to reach '
      'the engine at all')

check('two identical replies are NOT a change, so a load that did nothing '
      'cannot report a move',
      L.answer_changed({'ok': False, 'error': {'code': 'NO_RULE_FOR_STATE'}},
                       {'ok': False, 'error': {'code': 'NO_RULE_FOR_STATE'}}) is False)
check('a refusal becoming a real answer IS a change',
      L.answer_changed({'ok': False, 'error': {'code': 'NO_RULE_FOR_STATE'}},
                       {'ok': True, 'staffing': {'required_staff': 2}}) is True)
check('key ORDER is not a change -- the comparison sorts, so a reserialised '
      'identical reply does not read as a successful load',
      L.answer_changed({'a': 1, 'b': 2}, {'b': 2, 'a': 1}) is False)

WV_STAFF = [r for r in SEED['rules']
            if r['state'] == 'WV' and r['requirement_type'] == 'staffing'][0]
MI_LIC = [r for r in SEED['rules']
          if r['state'] == 'MI' and r['requirement_type'] == 'licensure'][0]

check('the probe is READ-ONLY -- it evaluates, and this endpoint has no delete, '
      'which is what a write-probe cost load_deadline_seed.py',
      L.verification_probe(WV_STAFF)['action'] == 'evaluate',
      L.verification_probe(WV_STAFF))

# THE ARM THE OLD SECTION 4 DID NOT HAVE, and the only one that could have
# caught the defect: the required-field list is READ OUT OF THE ENDPOINT. A
# hand-typed copy here would have gone stale in exactly the same direction as
# the probe it is checking.
API = io.open(os.path.join(REPO, 'api', 'sd-data.js'), encoding='utf-8').read()
EVAL_BRANCH = API[API.index("if (resource === 'alf_compliance_rules' && action === 'evaluate')"):][:1400]
required = sorted(set(re.findall(r'!payload\.(\w+)', EVAL_BRANCH)))
check('the endpoint\'s evaluate branch names its required payload fields, and '
      'this arm read them rather than re-typing them',
      required == ['requirement_type', 'state'], required)
probe_payload = L.verification_probe(WV_STAFF)['payload']
check('THE ARM THAT MATTERS NOW: the probe payload carries EVERY field the '
      'endpoint requires -- the missing one earned a 400 on every run and made '
      'the whole verification a comparison of two identical refusals',
      all(probe_payload.get(f) for f in required), (probe_payload, required))
check('...and it does NOT send the obsolete `check` key the endpoint ignores',
      'check' not in probe_payload, probe_payload)

check('facility_class is sent when the rule carries one -- the engine refuses to '
      'apply one class\'s figures to another and answers NO_RULE_FOR_CLASS',
      probe_payload.get('facility_class') == WV_STAFF['facility_class'],
      probe_payload)
check('...and OMITTED when the rule carries none, because null would not mean '
      '"every class in this state" to the engine',
      'facility_class' not in L.verification_probe(MI_LIC)['payload'],
      L.verification_probe(MI_LIC)['payload'])
check('the probe date is the RULE\'s own effective_from, not a constant -- a '
      'hardcoded date would report a rule not yet in force as a load failure',
      probe_payload['on_date'] == WV_STAFF['effective_from'], probe_payload)

# ── 4b. THREE STATES, NEVER TWO. Locked against synthetic fixtures in BOTH
# directions before the tool is trusted on real data, per
# docs/2026-09-13-cross-domain-disciplines.md item 1.
print('\n4b. the verdict has three states, and an idempotent re-run is a PASS')

REFUSAL = {'ok': False, 'error': {'code': 'NO_RULE_FOR_STATE'}}
SERVED = {'ok': True, 'rule_id': WV_STAFF['rule_id'], 'evaluated': False,
          'missing': ['shift']}

check('a refusal becoming this rule is LOADED',
      L.probe_verdict(WV_STAFF, REFUSAL, SERVED)[0] == 'loaded',
      L.probe_verdict(WV_STAFF, REFUSAL, SERVED))
check('THE ARM THE OLD CRITERION GOT BACKWARDS: unchanged AND the engine serves '
      'this rule is ALREADY IN FORCE -- a pass. The endpoint upserts, so a '
      're-run is idempotent BY DESIGN and the old "must have CHANGED" test '
      'called that a failure',
      L.probe_verdict(WV_STAFF, SERVED, SERVED)[0] == 'in_force',
      L.probe_verdict(WV_STAFF, SERVED, SERVED))
check('still refusing afterwards is NOT IN FORCE, and the detail carries the '
      'engine\'s own code rather than a paraphrase',
      L.probe_verdict(WV_STAFF, REFUSAL, REFUSAL) ==
      ('not_in_force', 'NO_RULE_FOR_STATE'),
      L.probe_verdict(WV_STAFF, REFUSAL, REFUSAL))
check('NO_RULE_FOR_CLASS is NOT IN FORCE too -- the rule is stored and the '
      'engine cannot reach it, which is the exact state WV was in while the '
      'probe sent no facility_class',
      L.probe_verdict(WV_STAFF, REFUSAL,
                      {'ok': False, 'error': {'code': 'NO_RULE_FOR_CLASS'}})[0]
      == 'not_in_force')
check('ok:true for a DIFFERENT rule_id is NOT IN FORCE -- ok alone would pass a '
      'load that silently did nothing while another rule answered the query',
      L.probe_verdict(WV_STAFF, REFUSAL,
                      {'ok': True, 'rule_id': 'PA-STAFFING-ALR-2010'})[0]
      == 'not_in_force')
check('evaluated:false is NOT a failure -- the probe supplies no census, so the '
      'engine describes the rule and names what it would still need',
      L.probe_verdict(WV_STAFF, REFUSAL, SERVED)[0] == 'loaded')
check('a non-dict answer (a challenge page, a None) is NOT IN FORCE rather '
      'than a crash',
      L.probe_verdict(WV_STAFF, REFUSAL, None)[0] == 'not_in_force')

# ── 5. IT FAILS CLOSED WITHOUT CREDENTIALS ──────────────────────────────────
print('\n5. no credentials is COULD NOT RUN, and it loads nothing')

env = dict(os.environ)
for k in ('SAIRNCARE_LICENSE_KEY', 'SAIRNCARE_EMP', 'SAIRNCARE_PIN'):
    env.pop(k, None)
r = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'load_compliance_seed.py'),
                    '--state', 'WV'],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', env=env)
check('exit 2 COULD NOT RUN, never 0 and never 1',
      r.returncode == 2, (r.returncode, (r.stderr or '')[:200]))
check('...and it says an unloaded seed is INERT rather than absent',
      'INERT' in (r.stderr or ''), (r.stderr or '')[:300])

r2 = subprocess.run([sys.executable,
                     os.path.join(REPO, 'tools', 'load_compliance_seed.py'),
                     '--dry-run'],
                    capture_output=True, text=True, encoding='utf-8',
                    errors='replace', env=env)
check('a DRY RUN needs no credentials and sends nothing',
      r2.returncode == 0 and 'nothing was sent' in (r2.stdout or ''),
      (r2.returncode, (r2.stdout or '')[-200:]))

# ── 6. NO DELETE, ANYWHERE ──────────────────────────────────────────────────
src = io.open(os.path.join(REPO, 'tools', 'load_compliance_seed.py'),
              encoding='utf-8').read()
code = '\n'.join(l for l in src.split('\n') if not l.lstrip().startswith('#'))
code = code.replace(src[src.index('"""'):src.index('"""', src.index('"""') + 3) + 3], '')
check('the loader never deletes -- a rule removed from the seed stays on the '
      'licence, and that is stated rather than assumed',
      "'delete'" not in code and '"delete"' not in code, code.count('delete'))

print('')
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('ALL ARMS PASS')
