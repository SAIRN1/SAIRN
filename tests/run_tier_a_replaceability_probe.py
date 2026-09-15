"""Does tier_a_replaceability_check measure the register, or just print?

    python tests/run_tier_a_replaceability_probe.py

THE ARM THAT MATTERS IS SECTION 3. A checker that prints "7" is worth nothing
until something has watched the 7 move. So this probe EDITS the real register
-- demoting one of the seven hard-deletable Tier A resources to B -- and
requires the count to fall to 6, then restores the file and verifies the
restore by sha256 rather than by having meant to.

AND SECTION 4 IS THE ONE THIS REPO KEEPS PAYING FOR. The tool reads the live
registry by RUNNING it, because SAIRNcode builds its grants with a reduce() and
a regex over the source would miss precisely the case the tool exists to
report. Section 4 proves that claim instead of asserting it: it checks that
`'delete'` appears nowhere as a literal beside any sc_* resource name in
api/_resources/sairncode.js, so a source-scraping implementation would have
found zero and reported the platform clean.

SECTION 5 IS A CONTROL ON THE WEAK MEASUREMENT. The recoverability figure reads
LANGUAGE, and a regex that had stopped matching anything would report every
Tier A row as silent and look like a dramatic finding. It is required to match
a fixture that plainly states recoverability and to not match one that plainly
does not, so the number cannot be manufactured by a dead pattern.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import tier_a_replaceability_check as t                          # noqa: E402

REGISTER = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
TOOL = os.path.join(REPO, 'tools', 'tier_a_replaceability_check.py')
SAIRNCODE = os.path.join(REPO, 'api', '_resources', 'sairncode.js')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run_json():
    r = subprocess.run([sys.executable, TOOL, '--json'], cwd=REPO,
                       capture_output=True, text=True, timeout=180)
    return r.returncode, r.stdout, r.stderr


def sha(path):
    return hashlib.sha256(io.open(path, 'rb').read()).hexdigest()


print('\n1. it reports the register as it stands')
code, out, err = run_json()
check('exits 0 on a clean repo', code == 0, err)
data = json.loads(out) if code == 0 else {}
check('it finds Tier A rows at all', data.get('tier_a', 0) > 0, data)
hard = [h[0] for h in data.get('hard_delete', [])]
apps = set(h[1] for h in data.get('hard_delete', []))
check('every hard-deletable Tier A resource is in ONE app',
      len(apps) == 1, apps)
check('...and that app is sairncode', apps == {'sairncode'}, apps)
check('the seven are the sc_* money and regulated resources',
      sorted(hard) == ['sc_ar', 'sc_claims', 'sc_compliance',
                       'sc_credential_scope', 'sc_denial', 'sc_denial_events',
                       'sc_revenue'], hard)

print('\n2. the three buckets partition the Tier A set')
tot = (len(data.get('hard_delete', [])) + len(data.get('soft_delete_only', []))
       + len(data.get('no_delete_verb', [])))
check('hard + soft-only + none == the Tier A count',
      tot == data.get('tier_a'), '%s vs %s' % (tot, data.get('tier_a')))
check('no resource is in two buckets',
      not (set(hard) & set(data.get('soft_delete_only', []))), 'overlap')

print('\n3. MUTATION -- demote one of the seven and the count must move')
before_sha = sha(REGISTER)
src = io.open(REGISTER, encoding='utf-8', newline='').read()
# The row is matched by its resource name at the start of a cell, so this does
# not depend on the evidence text, which changes.
pat = re.compile(r'(\|\s*`sc_compliance`\s*\|\s*)\*\*A\*\*(\s*\|)')
hits = len(pat.findall(src))
check('the mutation anchor matches EXACTLY once (ANCHOR-%d)' % hits, hits == 1,
      'a stale or ambiguous anchor means the arm below proves nothing')
mutated_ok = False
if hits == 1:
    try:
        io.open(REGISTER, 'w', encoding='utf-8', newline='').write(
            pat.sub(r'\1**B**\2', src))
        code2, out2, _ = run_json()
        d2 = json.loads(out2) if code2 == 0 else {}
        h2 = [h[0] for h in d2.get('hard_delete', [])]
        check('demoting sc_compliance to B drops the count to 6',
              len(h2) == 6 and 'sc_compliance' not in h2, h2)
        check('...and the Tier A total falls by exactly one',
              d2.get('tier_a') == data.get('tier_a') - 1,
              '%s vs %s' % (d2.get('tier_a'), data.get('tier_a')))
        mutated_ok = True
    finally:
        io.open(REGISTER, 'w', encoding='utf-8', newline='').write(src)
check('the register is restored BYTE FOR BYTE', sha(REGISTER) == before_sha,
      'docs/CRITICALITY-TIERS.md was left modified -- restore it by hand')
check('the mutation actually applied (not a vacuous pass)', mutated_ok,
      'the arm above never ran, so it proved nothing')

print('\n4. the live-registry read is load-bearing, not a style choice')
js = io.open(SAIRNCODE, encoding='utf-8').read()
code_only = '\n'.join(re.sub(r'^\s*//.*$', '', ln) for ln in js.split('\n'))
literal = re.findall(r"'sc_[a-z_]+'\s*:\s*\[[^\]]*'delete'", code_only)
check('sairncode grants delete via reduce(), never as a literal per resource',
      not literal,
      'found literal grants, so the reduce() claim in the tool header is stale: '
      + str(literal[:3]))
check('...and the file does build its grants with a reduce',
      'reduce(' in code_only, 'the header says reduce(); the file no longer does')

print('\n5. CONTROL on the language measurement -- the regex is alive')
check('a cell stating recoverability MATCHES',
      bool(t.RECOVERABILITY.search(
          'Money. In the 21-resource backup and carries `soft_delete`')))
check('a cell stating only consequence DOES NOT match',
      not t.RECOVERABILITY.search('Money'))
check('the real register has at least one matching row, so the silent count '
      'is not an artefact of a dead pattern',
      len(data.get('evidence_silent_on_recoverability', [])) < data.get('tier_a', 0),
      'every row reported silent -- suspect the pattern before the register')

print('\n6. it REFUSES rather than measuring a subset it cannot explain')
rows = t.tier_rows('| `nope_not_real` | **A** | x | y |\n')
check('tier_rows reads a tier cell wrapped in asterisks',
      rows == [('nope_not_real', 'A', 'y')], rows)
check('tier_rows ignores a row with no tier',
      t.tier_rows('| a | b | c | d |\n') == [], 'non-tier row was read as one')

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
