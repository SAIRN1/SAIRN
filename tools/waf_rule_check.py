"""tools/waf_rule_check.py -- is the firewall rule that is supposed to be
protecting us actually there, active, and configured the way git says?

    python tools/waf_rule_check.py
    python tools/waf_rule_check.py --json      # machine-readable

WHY THIS EXISTS (2026-09-05). A Vercel WAF rule lives in Vercel's dashboard,
not in this repository. It is invisible to `git log`, to every reviewer, and to
every other gate here. Somebody can disable it and nothing would ever say so.

THAT IS NOT HYPOTHETICAL, and the precedent is one layer down.
api/_lib/anon-rate-limit.js shipped ENFORCING and was measured completely inert
in production -- 40 concurrent junk-token requests returned 40 x 401 and not one
429 -- because horizontal scale-out defeats a per-instance counter. It looked
like protection for a day. The scoping document's premortem named the same
failure repeating one layer up: a rule somebody switched off that nobody
notices until the week it is needed.

So the rule and its checker ship in the SAME pass. Not afterwards.

── WHAT IT CHECKS ────────────────────────────────────────────────────────
tools/waf_rules_expected.json is the declared intent. This compares the LIVE
config against it, field by field:

  * the rule EXISTS, by name
  * it is ACTIVE -- an existing-but-disabled rule is the whole failure mode
  * its path condition still matches what we think it matches
  * limit, window, keys, algo and the on-exceed action all agree
  * `firewallEnabled` is true at the project level, because every rule in the
    world is inert underneath a disabled firewall
  * and, separately from all of the above, that no rule has been flipped to
    BLOCK while the open-work row still says observe-only. Editing the spec
    file to say `deny` does not get you past this one -- it is checked against
    a constant in this file, not against the spec.

── COULD-NOT-TELL IS NOT A PASS ──────────────────────────────────────────
No credentials, network failure, unparseable response: exit code 2 and a loud
line. It is deliberately NOT exit 0. The standing lesson this repo keeps
relearning is that the expensive part of a false success is never the error --
it is the confident line printed after it. The seed gate's "allowed with a loud
note" was written down as explicitly not a pass, and this follows it.

Exit codes:  0 = live matches the spec
             1 = DRIFT -- live and spec disagree, or a rule blocks in observe mode
             2 = UNVERIFIED -- could not read the live config. Not a pass.

── HOW IT AUTHENTICATES ──────────────────────────────────────────────────
VERCEL_TOKEN if set (works unattended, in a hook or CI); otherwise the `vercel`
CLI's own session, which is what a developer machine has. If neither works you
get exit 2, never a silent green.
"""
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_PATH = os.path.join(ROOT, 'tools', 'waf_rules_expected.json')

# Checked against THIS constant, never against the spec file, so that editing
# the spec to allow blocking does not quietly satisfy the check. Flipping to
# enforce is a real decision and has to change this line and the open-work row.
OBSERVE_ONLY_ACTIONS = ('log',)


class Unverified(Exception):
    """Could not read the live config. Distinct from 'the config is wrong'."""


def load_spec():
    with io.open(SPEC_PATH, encoding='utf-8') as fh:
        return json.load(fh)


def _extract_json(text):
    """The CLI prints a banner before the body; find the first JSON object."""
    i = text.find('{')
    if i < 0:
        raise Unverified('no JSON in the response: ' + text.strip()[:200])
    try:
        return json.loads(text[i:])
    except ValueError as err:
        raise Unverified('unparseable response: %s' % err)


def fetch_live(spec):
    path = ('/v1/security/firewall/config?projectId=%s&teamId=%s'
            % (spec['projectId'], spec['teamId']))
    token = os.environ.get('VERCEL_TOKEN')
    if token:
        try:
            import urllib.request
            req = urllib.request.Request(
                'https://api.vercel.com' + path,
                headers={'Authorization': 'Bearer ' + token})
            with urllib.request.urlopen(req, timeout=30) as r:
                return _extract_json(r.read().decode('utf-8', 'replace'))
        except Unverified:
            raise
        except Exception as err:
            raise Unverified('VERCEL_TOKEN request failed: %s: %s'
                             % (type(err).__name__, err))
    # QUOTED, and shell=True, because of Windows. `vercel` is a .cmd shim, so
    # shell=False often cannot find it; and the path carries `?` and `&`, which
    # an unquoted shell command splits -- the first version did exactly that and
    # vercel read the fragment as a deploy target. It failed loudly rather than
    # passing, which is the one thing that went right about it.
    cmd = 'vercel api "%s"' % path
    try:
        p = subprocess.run(cmd, cwd=ROOT, shell=True,
                           capture_output=True, text=True, timeout=90)
    except Exception as err:
        raise Unverified('could not run the vercel CLI: %s: %s'
                         % (type(err).__name__, err))
    if p.returncode != 0:
        raise Unverified('vercel CLI exited %d: %s'
                         % (p.returncode, (p.stderr or p.stdout).strip()[:200]))
    return _extract_json(p.stdout)


def live_rules(payload):
    active = payload.get('active') or payload
    if not isinstance(active, dict) or 'rules' not in active:
        raise Unverified('response has no active.rules -- shape changed?')
    return active, {r.get('name'): r for r in (active.get('rules') or [])}


def path_prefixes(rule):
    out = []
    for group in rule.get('conditionGroup') or []:
        for c in group.get('conditions') or []:
            if c.get('type') == 'path' and c.get('op') == 'pre':
                out.append(c.get('value'))
    return out


def check(spec, active, found):
    problems = []

    if active.get('firewallEnabled') is not True:
        problems.append('THE FIREWALL ITSELF IS DISABLED at the project level, '
                        'so every rule below it is inert regardless of how it '
                        'reads. This is the failure this tool exists for.')

    for want in spec['rules']:
        name = want['name']
        got = found.get(name)
        if got is None:
            problems.append('rule "%s" DOES NOT EXIST in the live config. It was '
                            'deleted, or was never published (a staged rule is '
                            'not a live one -- `vercel firewall publish`).' % name)
            continue
        if got.get('active') is not True:
            problems.append('rule "%s" exists but is NOT ACTIVE. An existing but '
                            'disabled rule is exactly the shape this tool was '
                            'written to catch.' % name)

        prefixes = path_prefixes(got)
        if want['path_prefix'] not in prefixes:
            problems.append('rule "%s" no longer matches path prefix %r -- live '
                            'prefixes are %r. It may still be enabled while '
                            'covering nothing we care about.'
                            % (name, want['path_prefix'], prefixes))

        mit = ((got.get('action') or {}).get('mitigate') or {})
        if mit.get('action') != want['mitigate_action']:
            problems.append('rule "%s" mitigate action is %r, spec says %r'
                            % (name, mit.get('action'), want['mitigate_action']))

        rl = mit.get('rateLimit') or {}
        wrl = want['rate_limit']
        for field in ('limit', 'window', 'algo', 'action'):
            if rl.get(field) != wrl[field]:
                problems.append('rule "%s" rateLimit.%s is %r, spec says %r'
                                % (name, field, rl.get(field), wrl[field]))
        if list(rl.get('keys') or []) != list(wrl['keys']):
            problems.append('rule "%s" rateLimit.keys is %r, spec says %r -- the '
                            'key decides WHO shares a bucket, so this is not a '
                            'cosmetic difference'
                            % (name, rl.get('keys'), wrl['keys']))

        # Separate from the comparison above, and deliberately against a
        # constant in this file rather than against the spec.
        if rl.get('action') not in OBSERVE_ONLY_ACTIONS:
            problems.append('rule "%s" is set to %r on exceed, which BLOCKS OR '
                            'CHALLENGES REAL TRAFFIC. The platform is still in '
                            'the observation week: flipping to enforce is a '
                            'decision that must change OBSERVE_ONLY_ACTIONS in '
                            'tools/waf_rule_check.py and the open-work row, not '
                            'just the rule.' % (name, rl.get('action')))

    unexpected = [n for n in found if n not in {r['name'] for r in spec['rules']}]
    for n in unexpected:
        problems.append('live rule "%s" is not in tools/waf_rules_expected.json. '
                        'Reported rather than ignored: a rule nobody declared is '
                        'a rule nobody reviewed.' % n)
    return problems


def main(argv):
    as_json = '--json' in argv
    spec = load_spec()
    try:
        payload = fetch_live(spec)
        active, found = live_rules(payload)
    except Unverified as err:
        msg = ('WAF CHECK UNVERIFIED -- %s\n'
               'THIS IS NOT A PASS. The live firewall config was not read, so '
               'nothing is known about it. Set VERCEL_TOKEN or run `vercel '
               'login`, then run this again and report the real result.' % err)
        print(json.dumps({'status': 'unverified', 'reason': str(err)})
              if as_json else msg)
        return 2

    problems = check(spec, active, found)
    if as_json:
        print(json.dumps({'status': 'drift' if problems else 'ok',
                          'version': active.get('version'),
                          'problems': problems}, indent=2))
    elif problems:
        print('WAF CHECK FAILED -- %d problem(s):' % len(problems))
        for p in problems:
            print('  * ' + p)
    else:
        print('WAF CHECK OK -- %d rule(s) live and matching the spec, firewall '
              'enabled, all on-exceed actions still observe-only.'
              % len(spec['rules']))
        print('NOTE: this proves the rule is CONFIGURED as declared. It does not '
              'prove it fires. That needs the concurrency probe -- see the '
              'scoping document.')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
