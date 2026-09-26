"""Does the SAIRNcare compliance loader load the right rules, and refuse the rest?

    python tests/run_compliance_loader_probe.py

THE ARM THAT MATTERS IS THE COVERAGE CAP. Michael capped SAIRNcare's
jurisdiction engine at five states on 2026-09-25 and recorded it inside the
seed as `coverage_cap`. A loader that quietly widened that would be the
decision being re-opened by a tool -- so a rule for a sixth state must be
REFUSED, by name, rather than loaded.

The second is the verification contract. The push gate's own refusal says "a
loader's exit code is not evidence", and this loader answers that by driving
the engine on IDENTICAL inputs before and after and requiring the answer to
have moved. If `answer_changed` ever returned True for two identical replies,
the loader would report success for a load that did nothing -- which is the
2026-08-27 defect the gate exists for, reproduced by the tool written to close
it.

NOTHING HERE TOUCHES THE NETWORK. select_rules, rule_payload, _probe_date and
answer_changed are pure; the credential refusal is driven as a subprocess.
"""
import io
import json
import os
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
print('\n4. a loader\'s exit code is not evidence -- the ANSWER has to move')

check('THE SECOND ARM THAT MATTERS: two identical replies are NOT a change, so '
      'a load that did nothing cannot report success',
      L.answer_changed({'ok': False, 'error': {'code': 'NO_RULE_FOR_STATE'}},
                       {'ok': False, 'error': {'code': 'NO_RULE_FOR_STATE'}}) is False)
check('a refusal becoming a real answer IS a change',
      L.answer_changed({'ok': False, 'error': {'code': 'NO_RULE_FOR_STATE'}},
                       {'ok': True, 'staffing': {'required_staff': 2}}) is True)
check('key ORDER is not a change -- the comparison sorts, so a reserialised '
      'identical reply does not read as a successful load',
      L.answer_changed({'a': 1, 'b': 2}, {'b': 2, 'a': 1}) is False)

check('the probe is READ-ONLY -- it evaluates, and this endpoint has no delete, '
      'which is what a write-probe cost load_deadline_seed.py',
      L.verification_probe('WV', SEED)['action'] == 'evaluate',
      L.verification_probe('WV', SEED))
check('the probe date is DERIVED from the seed, not hardcoded -- a stale '
      'constant would report NO_RULE_FOR_STATE as a load failure',
      L._probe_date('WV', SEED) == max(r['effective_from'] for r in SEED['rules']
                                       if r['state'] == 'WV'))

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
