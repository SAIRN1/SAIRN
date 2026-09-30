#!/usr/bin/env python
"""The control for tools/schema_provisioning_check.py -- and it had none.

    python tests/run_schema_provisioning_probe.py

Exit 0 all arms pass, 1 any arm fails.

── THE TWO DEFECTS THIS PINS, BOTH MEASURED ────────────────────────────────
1. IT COMPARED TABLE NAMES TO RESOURCE NAMES. SAIRNgrounds and SAIRNscape map
   one to the other on purpose -- resource `properties` reaches table
   `grd_properties`, `customers` reaches `scp_customers` -- so the tool saw
   seven live tables missing from the registry and reported that "no code can
   ask for them". Code asks for them on every page load.

2. ITS REGISTRY READER KNEW ONE SPELLING. `re.search(r'resources\\s*:\\s*\\[')`
   returns None against `const RESOURCES = [...]` plus
   `module.exports = { resources: RESOURCES }`, which is SAIRNcode's shape. The
   reader returned an EMPTY SET and the tool printed

       registered      : 0 checkable
       NOT REGISTERED  : 15 (the schema builds these and no code can ask for them)

   for an app with TWENTY-EIGHT registered resources. The two halves of that
   output contradict each other and neither is flagged: "0 checkable" is a
   could-not-read printed as a measurement, and the 15-table finding was DERIVED
   FROM IT. An empty parse produced a confident finding.

THE THIRD ARM IS THE ONE THAT MATTERS: an unreadable registry must be COULD NOT
RUN, never zero. Reading nothing and reporting a finding about what you read is
the defect this whole family of tools exists to catch, and it was inside one.
"""
import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'schema_provisioning_check.py')
CONTROLS_FOR = ['schema_provisioning_check.py']

import schema_provisioning_check as S                            # noqa: E402

_pass, _fail = 0, 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


def section(t):
    print('\n' + t)


def tmp_registry(body):
    d = tempfile.mkdtemp(prefix='spc-')
    p = os.path.join(d, 'zzapp.js')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    return p


print('SCHEMA PROVISIONING -- the control it did not have')

# ── A. THE REGISTRY READER, BOTH SPELLINGS ─────────────────────────────────
section('A. it reads both registry spellings, and refuses when it reads neither')

OBJ = ("module.exports = {\n  app: 'zzapp',\n  resources: [\n"
       "    'zz_one',\n    'zz_two',\n  ],\n};\n")
check('A1. the OBJECT-LITERAL spelling is read -- the one it always handled',
      S.registered_from_source(OBJ) == {'zz_one', 'zz_two'},
      S.registered_from_source(OBJ))

CONST = ("const RESOURCES = [\n  'zz_one',\n  'zz_two',\n];\n"
         "module.exports = { app: 'zzapp', resources: RESOURCES };\n")
check('A2. KNOWN-BAD: the CONST plus module.exports spelling is read too. This '
      'is SAIRNcode, and the old reader returned an empty set for it and then '
      'derived a 15-table finding from that emptiness',
      S.registered_from_source(CONST) == {'zz_one', 'zz_two'},
      S.registered_from_source(CONST))

check('A3. ...and a file with NO resource list at all returns None, not an '
      'empty set. THIS IS THE ARM THAT MATTERS: None is a could-not-read and '
      'empty would be a measurement, and the tool derived a finding from the '
      'difference',
      S.registered_from_source("module.exports = { app: 'zzapp' };\n") is None,
      S.registered_from_source("module.exports = { app: 'zzapp' };\n"))

check('A4. ...and an EMPTY declared list is an empty set, not None -- a registry '
      'that really admits nothing is a different fact from one that cannot be '
      'read, and folding them would make A3 unfalsifiable',
      S.registered_from_source(
          "module.exports = { app: 'zzapp', resources: [] };\n") == set(),
      S.registered_from_source(
          "module.exports = { app: 'zzapp', resources: [] };\n"))

# ── B. PREFIXED TABLE vs BARE RESOURCE ─────────────────────────────────────
section('B. a prefixed table resolves to its bare resource name')

check('B1. KNOWN-BAD: table `grd_properties` is reachable through resource '
      '`properties`. The old comparison called seven live tables unreachable',
      S.resolves('grd_properties', {'properties', 'jobs'}),
      'the prefix mapping is not applied')
check('B2. ...and `scp_customers` through `customers`',
      S.resolves('scp_customers', {'customers'}), '')
check('B3. ...and an exact name still resolves exactly',
      S.resolves('sc_claims', {'sc_claims'}), '')
check('B4. THE SILENT HALF: a table with NO matching resource under either '
      'spelling still does NOT resolve, or the fix clears every table and the '
      'NOT-REGISTERED finding stops existing',
      not S.resolves('zz_orphan_table', {'properties', 'customers'}),
      'everything now resolves, so the finding can never fire again')
check('B5. ...and a prefix strip must not match a DIFFERENT resource by '
      'accident: `grd_jobs` resolves to `jobs`, but `grd_jobs` must not resolve '
      'against a registry holding only `golf_zones`',
      not S.resolves('grd_jobs', {'golf_zones'}), '')

# ── C. THE REAL FILES, read through the tool ───────────────────────────────
section('C. the three registries the defect was found on')

for app, want in (('sairncode', 15), ('sairngrounds', 4), ('sairnscape', 3)):
    got = S.registered(app)
    check('C. %s registry reads NON-EMPTY (%s names). It read empty for '
          'sairncode before the fix, which is how 15 live tables became a '
          'finding' % (app, 'some' if got else 'ZERO'),
          got is not None and len(got) > 0, len(got or []))

check('C4. and every one of the 22 tables the tool called unreachable now '
      'RESOLVES, which is the measured outcome of both fixes together',
      all(S.resolves(t, S.registered(a)) for a, ts in (
          ('sairngrounds', ['grd_properties', 'grd_jobs', 'grd_quotes',
                            'grd_golf_zones']),
          ('sairnscape', ['scp_customers', 'scp_schedule', 'scp_invoices']),
          ('sairncode', ['sc_anesthesia', 'sc_ar', 'sc_auth', 'sc_compliance',
                         'sc_denial', 'sc_drg', 'sc_encoder', 'sc_fraud',
                         'sc_hcc', 'sc_prebill', 'sc_providers', 'sc_query',
                         'sc_rac', 'sc_revenue', 'sc_telehealth'])
      ) for t in ts),
      [(a, t) for a, ts in (
          ('sairngrounds', ['grd_properties', 'grd_jobs', 'grd_quotes',
                            'grd_golf_zones']),
          ('sairnscape', ['scp_customers', 'scp_schedule', 'scp_invoices']),
      ) for t in ts if not S.resolves(t, S.registered(a))])

# ── D. THE REFUSAL IS DRIVEN THROUGH THE CLI ───────────────────────────────
section('D. an unreadable registry exits COULD NOT RUN through the real CLI')

_r = subprocess.run(
    [sys.executable, TOOL, '--app', 'zz-no-such-app',
     '--schema', 'sql/stonedesk_data_schema.sql', '--key', 'ZZ-NONE'],
    cwd=REPO, capture_output=True, text=True, encoding='utf-8',
    errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
check('D1. an app with no registry file at all is refused and says the absence '
      'is itself a finding',
      _r.returncode != 0 and 'unregistered app' in (_r.stdout + _r.stderr),
      (_r.returncode, (_r.stdout + _r.stderr)[-200:]))

check('D2. ANCHOR: registered_from_source and resolves are still the names this '
      'control calls. If either is renamed every arm above stops testing the '
      'tool and passes against nothing',
      hasattr(S, 'registered_from_source') and hasattr(S, 'resolves'),
      'a function was renamed')

_src = io.open(TOOL, encoding='utf-8').read()
check('D3. the tool declares this file as its control, so '
      'checker_control_check can find the pair from either end',
      'run_schema_provisioning_probe.py' in _src, 'CONTROLLED_BY is missing')

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
