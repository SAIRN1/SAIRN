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
# ── THE STATE THIS ARM ASSERTS CHANGED ON 2026-09-15, AND SO DID THE ARM ────
# Until the item 97 fix it asserted the DEFECT -- seven hard-deletable Tier A
# resources, all in sairncode. That was the right assertion for the day it was
# written and it is the wrong one now: the fix made the count zero, and an arm
# still demanding seven would report the repaired platform as broken.
# Section 3's registry mutation is what keeps THIS arm from being vacuous, by
# putting the seven back and requiring the number to move.
check('NO Tier A resource on the platform can be hard-deleted -- 0, and the '
      'names if not: %s' % (sorted(hard) or 'none'),
      hard == [], hard)
check('...and the Tier A set is not empty, so the zero above is a measurement '
      'and not an absence of rows',
      data.get('tier_a', 0) >= 70, data.get('tier_a'))
check('the seven SAIRNcode records are soft-delete-only now',
      set(['sc_ar', 'sc_claims', 'sc_compliance', 'sc_credential_scope',
           'sc_denial', 'sc_denial_events', 'sc_revenue'])
      <= set(data.get('soft_delete_only', [])),
      sorted(data.get('soft_delete_only', [])))

print('\n2. the three buckets partition the Tier A set')
tot = (len(data.get('hard_delete', [])) + len(data.get('soft_delete_only', []))
       + len(data.get('no_delete_verb', [])))
check('hard + soft-only + none == the Tier A count',
      tot == data.get('tier_a'), '%s vs %s' % (tot, data.get('tier_a')))
check('no resource is in two buckets',
      not (set(hard) & set(data.get('soft_delete_only', []))), 'overlap')

print('\n3a. MUTATION on the REGISTER -- demote a Tier A row and the total moves')
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
        check('demoting sc_compliance drops the Tier A total by exactly one',
              d2.get('tier_a') == data.get('tier_a') - 1,
              '%s vs %s' % (d2.get('tier_a'), data.get('tier_a')))
        check('...and it leaves the soft-delete-only set one shorter',
              len(d2.get('soft_delete_only', [])) ==
              len(data.get('soft_delete_only', [])) - 1,
              '%s vs %s' % (len(d2.get('soft_delete_only', [])),
                            len(data.get('soft_delete_only', []))))
        mutated_ok = True
    finally:
        io.open(REGISTER, 'w', encoding='utf-8', newline='').write(src)
check('the register is restored BYTE FOR BYTE', sha(REGISTER) == before_sha,
      'docs/CRITICALITY-TIERS.md was left modified -- restore it by hand')
check('the mutation actually applied (not a vacuous pass)', mutated_ok,
      'the arm above never ran, so it proved nothing')

print('\n3b. MUTATION on the REGISTRY -- put the seven destroy verbs back')
# THE ARM THAT KEEPS SECTION 1 HONEST. Section 1 now asserts ZERO hard-deletable
# Tier A resources, and a tool that had simply stopped detecting them would pass
# it just as well as the fix does. So the defect is RECREATED: the per-resource
# test in api/_resources/sairncode.js is defeated, restoring the uniform grant
# item 97 found, and the count must come back as exactly the seven.
#
# SINGLE-LINE ANCHOR ON PURPOSE -- that file is CRLF in this working tree while
# api/sd-data.js is LF, and a multi-line anchor written with \n reported
# ANCHOR-0 against it the first time this was tried.
REGISTRY = os.path.join(REPO, 'api', '_resources', 'sairncode.js')
reg_sha = sha(REGISTRY)
rsrc = io.open(REGISTRY, encoding='utf-8', newline='').read()
RANCHOR = '    map[name] = SC_TIER_A_SOFT_DELETE_ONLY.indexOf(name) === -1'
rhits = rsrc.count(RANCHOR)
check('the registry anchor matches EXACTLY once (ANCHOR-%d)' % rhits, rhits == 1,
      'the grant is no longer built by a per-resource test -- re-anchor this arm')
reg_mutated_ok = False
if rhits == 1:
    try:
        io.open(REGISTRY, 'w', encoding='utf-8', newline='').write(
            rsrc.replace(RANCHOR, '    map[name] = [].indexOf(name) === -1', 1))
        code3, out3, _ = run_json()
        d3 = json.loads(out3) if code3 == 0 else {}
        h3 = sorted(h[0] for h in d3.get('hard_delete', []))
        check('defeating the per-resource test makes all seven hard-deletable '
              'again -- the tool DOES detect this, it is not blind',
              h3 == ['sc_ar', 'sc_claims', 'sc_compliance', 'sc_credential_scope',
                     'sc_denial', 'sc_denial_events', 'sc_revenue'], h3)
        reg_mutated_ok = True
    finally:
        io.open(REGISTRY, 'w', encoding='utf-8', newline='').write(rsrc)
check('api/_resources/sairncode.js is restored BYTE FOR BYTE',
      sha(REGISTRY) == reg_sha,
      'the registry was left modified -- restore it by hand before pushing')
check('the registry mutation actually applied (not a vacuous pass)',
      reg_mutated_ok, 'the arm above never ran, so it proved nothing')

print('\n3c. THE UNDER-ASSIGNMENT SIGNALS -- and the one that shipped DEAD')
# ── POSITIVE CONTROLS, AND THEY EARNED THEIR KEEP IMMEDIATELY ───────────────
# The ATTESTATION pattern shipped with a LITERAL BACKSPACE where a word boundary
# was intended -- the byte 0x08 -- so `ATTEST.search('signer:signer')` was False
# and the signal reported ZERO hits across the whole platform. A clean result
# from a dead pattern. CLAUDE.md already names this exact defect as one of the
# three that made the cross-domain disciplines necessary: "a regex that shipped
# with a literal backspace and could never match."
#
# IT WAS FOUND BY ASSERTING THE SIGNAL FIRES ON A KNOWN CASE, not by reading the
# line, which looks correct at every size of font. So every signal below has a
# positive control and a negative one, and the tool now refuses to IMPORT if the
# attestation pattern cannot match its own reference case.
check('ATTEST matches a real signature write', bool(t.ATTEST.search(
    "list.push({ signer:signer, typed:typed, hash:doc.hash })")))
check('ATTEST matches a server-stamped sign-off',
      bool(t.ATTEST.search("payload.signedOffBy = arCaller.employee_id;")))
check('CONTROL: ATTEST does NOT match a word that merely contains one',
      not t.ATTEST.search("var designer = 1;"),
      'it matches inside `designer` -- the substring trap this platform has '
      'already been bitten by once')
check('ATTEST carries NO control bytes -- the defect that made it dead',
      not any(ord(c) < 32 for c in t.ATTEST.pattern), repr(t.ATTEST.pattern))
check('SHAPE matches a log name', bool(t.SHAPE.search('sd_sms_log')))
check('SHAPE matches an audit name', bool(t.SHAPE.search('sv_audit_log')))
check('CONTROL: SHAPE does NOT match a name that merely contains one',
      not t.SHAPE.search('sc_dialogue'), 'substring match')
check('the attestation reader sees through a CONSTANT alias -- sairnfreedom '
      'binds K_SIGNATURES and every writer uses the constant',
      t.attestation_writers('sf_signatures') == ['sairnfreedom.html'],
      t.attestation_writers('sf_signatures'))
check('...and it finds the SAIRNlaw e-signature record, which is Tier B today',
      t.attestation_writers('law_portalesign') == ['sairnlaw.html'],
      t.attestation_writers('law_portalesign'))

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
