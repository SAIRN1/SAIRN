#!/usr/bin/env python
"""Does the rule-discovery scan find rules, and refuse the things that are not?

    python tests/run_coding_rule_discovery_probe.py

Exit 0 every arm holds, 1 an arm failed, 2 COULD NOT RUN.

── THE CRITERIA ARE LOCKED AGAINST SYNTHETIC FIXTURES FIRST ───────────────────
docs/2026-09-13-cross-domain-disciplines.md, discipline one. Every fixture below
is a string handed to discover_text(), written to no file, and each is ONE
property short of -- or one property past -- a real rule. A detector that says
yes to everything is worth less than none, and the S2 signal is exactly the
shape that widens quietly: it reached 70 candidates on sairncode.html before the
wired-handler narrowing, most of them dragged in by a single generic helper.

── AND THEN AGAINST THE REAL FILE, WHICH IS THE OTHER HALF ────────────────────
Fixtures prove the criteria; the real file proves they still match how this
codebase actually writes rules. Both, or neither means anything.
"""

import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

try:
    import coding_rule_discovery as d                             # noqa: E402
except Exception as e:                                            # noqa: BLE001
    sys.stderr.write('COULD NOT RUN: coding_rule_discovery did not import: %s\n' % e)
    sys.exit(2)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


# The smallest text carrying BOTH conventions this codebase uses, so a fixture
# can subtract one property at a time and see what happens.
HEAD = (
    'var XX_SOURCES = { a: "CMS says so" };\n'
    'function xxFinding(sev, rule, detail, key){ return {sev:sev}; }\n'
)
WIRED = '<button onclick="runXx()">go</button>\n'


def names(text):
    _, _, hits = d.discover_text(text)
    return set(hits)


print('\n1. the fixtures are real -- the scan sees the conventions at all')
base = HEAD + 'function xxRule(a){ return xxFinding("block","r","d","a"); }\n'
check('S1: a function calling a finding builder is a candidate',
      'xxRule' in names(base), sorted(names(base)))
check('CONTROL: the BUILDER itself is not a candidate -- it emits nothing, it '
      'is what emitting looks like', 'xxFinding' not in names(base),
      sorted(names(base)))

print('\n2. S1 needs the CALL, not the name')
near = HEAD + 'function xxRule(a){ return { sev: "block" }; }\n'
check('a function that merely returns a block-shaped object is NOT a candidate',
      'xxRule' not in names(near), sorted(names(near)))

print('\n3. S2 -- pure, called from a WIRED handler that cites a source')
s2 = (HEAD + WIRED
      + 'function xxPure(a){ return a > 1; }\n'
      + 'function runXx(){ var r = xxPure(2); box(r, XX_SOURCES.a); }\n')
check('the pure callee is a candidate', 'xxPure' in names(s2), sorted(names(s2)))

print('\n4. THE NARROWING THAT MATTERED -- an unwired citing function')
# scCsvCell is the real instance: it cites a source map and calls a dozen
# helpers, none of which is a rule. Removing the onclick is the whole fixture.
s4 = (HEAD
      + 'function xxPure(a){ return a > 1; }\n'
      + 'function helper(){ var r = xxPure(2); box(r, XX_SOURCES.a); }\n')
check('a citing function NOT wired from markup drags nothing in',
      'xxPure' not in names(s4), sorted(names(s4)))

print('\n5. THE PURITY TEST -- a renderer is not a rule')
s5 = (HEAD + WIRED
      + 'function xxBox(r){ document.getElementById("x").innerHTML = r; }\n'
      + 'function runXx(){ xxBox(1); box(1, XX_SOURCES.a); }\n')
check('a callee touching document/innerHTML is refused', 'xxBox' not in names(s5),
      sorted(names(s5)))
for impure, label in (('localStorage.getItem("k");', 'localStorage'),
                      ('fetch("/x");', 'fetch'),
                      ('showToast("x");', 'showToast')):
    s = (HEAD + WIRED
         + 'function xxSide(){ %s }\n' % impure
         + 'function runXx(){ xxSide(); box(1, XX_SOURCES.a); }\n')
    check('...and so is one that calls %s' % label, 'xxSide' not in names(s),
          sorted(names(s)))

print('\n6. no conventions at all -> no candidates, not "everything"')
s6 = ('function plain(a){ return a + 1; }\n'
      '<button onclick="plain()">go</button>\n')
check('a file with no SOURCES map and no finding builder yields nothing',
      not names(s6), sorted(names(s6)))

print('\n7. a callee that is not defined locally is not invented')
s7 = (HEAD + WIRED
      + 'function runXx(){ var r = somethingElsewhere(2); box(r, XX_SOURCES.a); }\n')
check('an undefined callee produces no candidate', not names(s7), sorted(names(s7)))

print('\n8. the REAL file -- the criteria still match how rules are written here')
try:
    maps, builders, hits = d.discover('sairncode.html')
except Exception as e:                                            # noqa: BLE001
    check('sairncode.html scanned', False, e)
    maps, builders, hits = [], [], {}
check('it finds the citation convention (%d source map(s))' % len(maps),
      len(maps) >= 5, maps)
check('it finds the finding convention (%d builder(s))' % len(builders),
      len(builders) >= 5, builders)
check('it finds candidates (%d)' % len(hits), len(hits) >= 10, sorted(hits))
# THE TWO ALREADY REGISTERED MUST BE AMONG THEM. If the scan cannot see the
# rules somebody has already decided ARE rules, it is measuring something else.
for known in ('scValidatePtSession', 'dmeValidateSwo'):
    check('...including %s, which is already registered' % known, known in hits,
          sorted(hits)[:12])
# ...AND THE NOISE FLOOR IS MEASURED RATHER THAN HOPED. A helper that exists
# only to render is the population this tool must keep out.
for noise in ('scCsvCell', 'isMobileNav', 'showPanel'):
    check('CONTROL: %s is not reported as a rule' % noise, noise not in hits,
          sorted(hits)[:12])

print('\n9. an unreadable registry is COULD NOT RUN, never an empty answer')
real = d.REGISTRY
d.REGISTRY = os.path.join(REPO, 'tools', '__probe_no_registry.json')
try:
    rc = 'did not exit'
    try:
        d.registered()
    except SystemExit as e:
        rc = e.code
    check('registered() exits 2 when the registry cannot be read', rc == 2, rc)
finally:
    d.REGISTRY = real
check('the registry path is restored', d.REGISTRY == real, d.REGISTRY)

print('')
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('ALL ARMS PASS')
sys.exit(0)
