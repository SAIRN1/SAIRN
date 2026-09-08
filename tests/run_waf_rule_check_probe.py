"""tests/run_waf_rule_check_probe.py -- drive tools/waf_rule_check.py against
synthetic live payloads and confirm it goes RED for each failure it claims to
catch.

    python tests/run_waf_rule_check_probe.py

WHY. The standing practice this repo keeps relearning: a suite that has never
been seen to fail is a suite whose behaviour nobody knows. The checker exists
because api/_lib/anon-rate-limit.js LOOKED like protection for a day while
being measured completely inert -- so a checker that would itself pass against
a deleted rule would be the same mistake wearing a different hat.

No network and no mutation of the real firewall: `check()` is a pure function
of (spec, active, found), so every case here is a hand-built payload.
"""
import copy
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import waf_rule_check as W                                    # noqa: E402

passed = failed = 0


def case(name, ok, detail=''):
    global passed, failed
    if ok:
        passed += 1
        print('  ok   ' + name)
    else:
        failed += 1
        print('  FAIL ' + name + ('\n       ' + detail if detail else ''))


def live_from(spec):
    """Build a live payload that EXACTLY matches the spec."""
    rules = []
    for r in spec['rules']:
        rules.append({
            'name': r['name'],
            'active': True,
            'conditionGroup': [{'conditions': [
                {'type': 'path', 'op': 'pre', 'value': r['path_prefix']}]}],
            'action': {'mitigate': {
                'action': r['mitigate_action'],
                'rateLimit': dict(r['rate_limit']),
            }},
        })
    return {'firewallEnabled': True, 'version': '1', 'rules': rules}


def run(spec, active):
    found = {r.get('name'): r for r in active['rules']}
    return W.check(spec, active, found)


def hits(problems, *needles):
    blob = ' '.join(problems).lower()
    return all(n.lower() in blob for n in needles)


SPEC = W.load_spec()

print('--- the baseline must be clean, or every negative below proves nothing ---')
base = live_from(SPEC)
p = run(SPEC, base)
case('an exactly-matching live config produces ZERO problems', not p, repr(p))

print('--- each failure the tool claims to catch ---')

a = copy.deepcopy(base); a['rules'].pop(0)
p = run(SPEC, a)
case('a DELETED rule is caught and named',
     hits(p, SPEC['rules'][0]['name'], 'does not exist'), repr(p))

a = copy.deepcopy(base); a['rules'][0]['active'] = False
p = run(SPEC, a)
case('an EXISTING BUT DISABLED rule is caught -- the headline failure mode',
     hits(p, 'not active'), repr(p))

a = copy.deepcopy(base)
a['rules'][0]['conditionGroup'][0]['conditions'][0]['value'] = '/nothing/'
p = run(SPEC, a)
case('a rule silently scoped to a path we do not care about is caught',
     hits(p, 'no longer matches path prefix'), repr(p))

a = copy.deepcopy(base)
a['rules'][0]['action']['mitigate']['rateLimit']['limit'] = 99999
p = run(SPEC, a)
case('a changed LIMIT is caught', hits(p, 'ratelimit.limit'), repr(p))

a = copy.deepcopy(base)
a['rules'][0]['action']['mitigate']['rateLimit']['window'] = 3600
p = run(SPEC, a)
case('a changed WINDOW is caught', hits(p, 'ratelimit.window'), repr(p))

a = copy.deepcopy(base)
a['rules'][0]['action']['mitigate']['rateLimit']['keys'] = ['ja4']
p = run(SPEC, a)
case('a changed KEY is caught -- it decides who shares a bucket',
     hits(p, 'ratelimit.keys'), repr(p))

a = copy.deepcopy(base); a['firewallEnabled'] = False
p = run(SPEC, a)
case('the FIREWALL ITSELF being disabled is caught, not just the rules',
     hits(p, 'firewall itself is disabled'), repr(p))

a = copy.deepcopy(base)
a['rules'].append({'name': 'someone-elses-rule', 'active': True,
                   'conditionGroup': [], 'action': {'mitigate': {}}})
p = run(SPEC, a)
case('an UNDECLARED live rule is reported rather than ignored',
     hits(p, 'someone-elses-rule', 'not in tools/waf_rules_expected.json'), repr(p))

print('--- the one that must survive a spec edit ---')
# The whole point of OBSERVE_ONLY_ACTIONS living in the tool rather than in the
# spec: somebody flipping the rule to blocking AND editing the spec to agree
# must still trip a loud, separate failure.
sneaky = copy.deepcopy(SPEC)
sneaky['rules'][0]['rate_limit']['action'] = 'deny'
a = live_from(sneaky)
p = run(sneaky, a)
case('a rule flipped to DENY still trips even when the spec was edited to match',
     hits(p, 'blocks or challenges real traffic'), repr(p))
case('...and it is the ONLY problem, proving the per-field comparison was '
     'genuinely satisfied rather than failing for some other reason',
     len(p) == 1, repr(p))

print('--- could-not-tell must not be a pass ---')
try:
    W._extract_json('vercel: command not found')
    case('a non-JSON response raises Unverified', False, 'no exception raised')
except W.Unverified:
    case('a non-JSON response raises Unverified', True)
except Exception as e:
    case('a non-JSON response raises Unverified', False, repr(e))

try:
    W.live_rules({'active': {'somethingElse': 1}})
    case('a response with no active.rules raises Unverified', False, 'no exception')
except W.Unverified:
    case('a response with no active.rules raises Unverified', True)
except Exception as e:
    case('a response with no active.rules raises Unverified', False, repr(e))

# The exit code matters as much as the message: a hook reads the code.
src = io.open(os.path.join(ROOT, 'tools', 'waf_rule_check.py'), encoding='utf-8').read()
case('UNVERIFIED returns exit 2, distinct from both 0 and 1',
     "print(json.dumps({'status': 'unverified'" in src and '        return 2' in src)
case('the spec file is valid JSON and declares at least one rule',
     bool(SPEC.get('rules')))

print('\n' + ('FAILED  ' if failed else 'ok  ') +
      'waf_rule_check probe: %d passed, %d failed' % (passed, failed))
sys.exit(1 if failed else 0)
