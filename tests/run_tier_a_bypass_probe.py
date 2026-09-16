"""Does tier_a_bypass_check tell a gated handler from an ungated one --
and does it refuse when it cannot look?

    python tests/run_tier_a_bypass_probe.py

The arm that earned its place first: the tool's FIRST version matched raw
source, and both of its findings were prose -- the word "quotes" in
'slabs, quotes and jobs' and "invoices" in a header comment. Two findings, two
false positives. Arm 3 pins the comment stripping that fixed it, and arm 3c
pins the limit it did NOT fix, so nobody reads a later false positive as a
regression.
"""
# REQUIREMENT: tier_a_bypass_check tells a gated handler from an ungated one,
#   strips comments before matching so prose cannot become a finding, and
#   refuses when it cannot look -- its first version's only two findings were
#   both words in prose
#
import contextlib
import io as _io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
os.chdir(REPO)

import tier_a_bypass_check as tab   # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name
          + (('\n        ' + str(detail)[:300]) if (detail and not cond) else ''))


def run(files, tiers_src=None):
    """Run main() over a fake api/ tree. files: {relpath: source}."""
    real_read, real_handlers = tab.read, tab.handlers

    def fake_read(rel):
        if rel == tab.TIERS:
            return real_read(tab.TIERS) if tiers_src is None else tiers_src
        return files.get(rel)
    tab.read = fake_read
    tab.handlers = lambda: sorted(files)
    buf = _io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = tab.main([])
    finally:
        tab.read, tab.handlers = real_read, real_handlers
    return rc, buf.getvalue()


print('--- 1. the Tier A list comes from the register, not from the tool ---')
names = tab.tier_a_resources()
check('1a  the register parses to a non-empty Tier A set', bool(names), names)
check('1b  and it contains resources the document really marks A',
      'sv_controlled' in names and 'sd_invoices' in names,
      sorted(list(names))[:8])

print('\n--- 2. gated vs ungated ---')
GATED = ("const s = await requireSession(req);\n"
         "if (!s) { res.status(401).json({error:'NO_LICENSE'}); return; }\n"
         "await write('sv_controlled', req.body);\n")
OPEN = "await write('sv_controlled', req.body);\n"
rc, out = run({'api/gated.js': GATED})
check('2a  a handler with an identity check AND a refusal is GATED',
      'GATED (1)' in out, out)
rc, out = run({'api/open.js': OPEN})
check('2b  a handler with neither is NO GATE FOUND',
      'NO GATE FOUND (1)' in out, out)
rc, out = run({'api/half.js': "res.status(401).end();\nawait write('sv_controlled',b);\n"})
check('2c  a refusal with no identity is COULD NOT TELL, not GATED',
      'COULD NOT TELL (1)' in out, out)

print('\n--- 3. PROSE IS NOT A REFERENCE (PR 1.2) ---')
rc, out = run({'api/prose.js': "// this file has nothing to do with sv_controlled\nvar x=1;\n"})
check('3a  a Tier A name in a COMMENT does not make a finding',
      'IN CODE: 0' in out, out)
check('3b  and it is reported as dropped rather than vanishing',
      'PROSE ONLY' in out and 'api/prose.js' in out, out)
check('3c  CONTROL: the same name in CODE still counts, so 3a is not passing '
      'because everything is dropped',
      'IN CODE: 1' in run({'api/real.js': OPEN})[1], run({'api/real.js': OPEN})[1])

print('\n--- 4. it refuses rather than reporting a clean platform ---')
rc, out = run({'api/x.js': OPEN}, tiers_src=None if False else '# no table here\n')
check('4a  a tiers document that parses to ZERO resources exits 2 -- an audit '
      'that treats nothing as Tier A reports everything clean', rc == 2, rc)
check('4b  and says zero targets is not a clean sweep',
      'not a clean sweep' in out, out)

real_read = tab.read
tab.read = lambda rel: None if rel == tab.TIERS else 'x'
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = tab.main([])
tab.read = real_read
check('4c  a MISSING tiers document exits 2', rc == 2, rc)

rc, out = run({})
check('4d  zero handlers exits 2 rather than passing', rc == 2, rc)

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
