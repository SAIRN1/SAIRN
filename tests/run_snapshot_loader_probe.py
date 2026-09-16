"""tests/run_snapshot_loader_probe.py -- the loader refuses what it claims to refuse.

    python tests/run_snapshot_loader_probe.py

tools/load_schema_snapshot.py is a gate on the one file every schema checker
reasons from. A gate that cannot be shown to refuse is indistinguishable from
one that always passes, so every refusal is planted here on a throwaway fixture
and demanded.

THE ARM THAT MATTERS IS THE CONTROL. A "gate" that returned REFUSED for
everything would satisfy every other arm in this file. Section 5 builds a
genuinely good capture -- newer stamp, one table gained, none lost -- and
demands exit 0.

The shapes are not hypothetical. Each is something that actually happened, or
is the quiet twin of something that did:
  * EMPTY -- the chat relay produced this twice on 2026-09-12/13, an
    instruction with nothing after the colon;
  * MALFORMED -- a transfer cut off mid-JSON. Loud, and therefore the safe one;
  * SHORT BUT VALID -- the dangerous twin. Nothing downstream can tell it from
    a database that really lost those tables, and
    tools/schema_snapshot_freshness.py turns an absence into "this migration
    was never run";
  * NOT NEWER -- the wrong file, or a paste of the one already committed.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'load_schema_snapshot.py')
CURRENT = os.path.join(REPO, 'db', 'schema_snapshot.json')

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


def run(path, *extra):
    p = subprocess.run([sys.executable, TOOL, path] + list(extra),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=REPO)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


tmp = tempfile.mkdtemp(prefix='snaploader-')
base = json.load(io.open(CURRENT, encoding='utf-8'))
NEWER = '2026-12-25 00:00:00.000000+00'


def fixture(name, obj_or_text):
    p = os.path.join(tmp, name)
    text = obj_or_text if isinstance(obj_or_text, str) else json.dumps(obj_or_text)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(text)
    return p


print('1. an EMPTY payload -- the shape the chat relay produced twice')
rc, out = run(fixture('empty.json', ''))
check('1a  refused', rc == 2, 'exit %d' % rc)
check('1b  and it says EMPTY rather than a parse error', 'EMPTY' in out)
check('1c  nothing was written', 'Nothing was written' in out or 'REFUSED' in out)

print('2. MALFORMED json -- a transfer cut off mid-stream')
rc, out = run(fixture('cut.json', '{"a": [1,2'))
check('2a  refused', rc == 2, 'exit %d' % rc)
check('2b  and it names the loud/quiet distinction', 'LOUD' in out)

print('3. SHORT BUT VALID -- the dangerous twin, which still parses')
short = dict(base)
short['_generated_at'] = NEWER
dropped = [k for k in short if not k.startswith('_')][:5]
for k in dropped:
    del short[k]
rc, out = run(fixture('short.json', short))
check('3a  refused even though it is newer and parses fine', rc == 1, 'exit %d' % rc)
check('3b  and every lost table is NAMED, not just counted',
      all(d in out for d in dropped), dropped)
check('3c  it says why a shrink is indistinguishable from a real drop',
      'indistinguishable' in out)

print('4. NOT NEWER -- the wrong file, or a paste of the one already here')
rc, out = run(fixture('same.json', base))
check('4a  refused', rc == 1, 'exit %d' % rc)
check('4b  and it says so in those terms', 'NOT NEWER' in out)
nostamp = dict(base)
del nostamp['_generated_at']
rc, out = run(fixture('nostamp.json', nostamp))
check('4c  a capture with no _generated_at is refused, not defaulted', rc == 1)

print('5. CONTROL -- a genuinely good capture must PASS')
good = dict(base)
good['_generated_at'] = NEWER
good['zz_probe_only_table'] = ['id']
rc, out = run(fixture('good.json', good))
check('5a  a newer capture that gains a table is ACCEPTED', rc == 0, 'exit %d' % rc)
check('5b  the gained table is reported', 'zz_probe_only_table' in out)
check('5c  WITHOUT --write it writes nothing -- the check is not the install',
      'Nothing written' in out)

print('6. the shrink override is a DECISION, not a flag')
rc, out = run(fixture('short2.json', short), '--allow-shrink')
check('6a  --allow-shrink with no reason is refused', rc == 2, 'exit %d' % rc)
check('6b  and it says why an unstated override is dangerous',
      'hollowed out' in out)
rc, out = run(fixture('short3.json', short), '--allow-shrink', 'dropped on purpose')
check('6c  with a reason it proceeds', rc == 0, 'exit %d' % rc)
check('6d  and the reason is ECHOED so it reaches the commit message',
      'dropped on purpose' in out)

# ── SECTION 7 CORRECTED 2026-09-16, AND THE FIXTURE WAS THE THING THAT WAS
# ── WRONG, NOT THE TOOL'S OUTPUT. SAYING WHICH, BECAUSE THAT IS THE RULE.
# This section used to add `_probe_metadata_key: ['not', 'a', 'table']` and
# assert it was NOT counted as a table. That fixture encoded the loader's
# leading-underscore name rule, and the name rule is what was wrong: TWO REAL
# TABLES IN `public` BEGIN WITH AN UNDERSCORE AND HAVE BEEN IN THE CAPTURE
# SINCE 2026-08-26 -- `_anon_grant_baseline_2026_08_26` and
# `_anon_nontable_baseline_2026_08_26`, created by
# sql/anon_authenticated_grant_revoke_2026-08-26.sql, and the hardening handoff
# says in terms that they must stay. Their values are lists of column names,
# structurally identical to the old fixture, so the fixture was asserting the
# exact classification that made those two invisible to the shrink guard.
#
# The loader now classifies by the VALUE's shape. Both directions are demanded
# here, because the name rule passed one of them and the point is that it could
# not pass both.
print('7. metadata is told from a table by SHAPE, not by a leading underscore')
meta = dict(base)
meta['_generated_at'] = NEWER
meta['_constraints'] = {'some_table': {'ck': 'CHECK (true)'}}
rc, out = run(fixture('meta.json', meta))
check('7a  a real metadata key (an object) is not reported as a gained table',
      rc == 0)
check('7b  and it does not appear in the gained list', '_constraints' not in out)

under = dict(base)
under['_generated_at'] = NEWER
under['_anon_probe_baseline_2026_08_26'] = ['table_name', 'grantee']
rc, out = run(fixture('underscore-table.json', under))
check('7c  an underscore-named key holding a COLUMN LIST is a table', rc == 0)
check('7d  and it IS reported as gained -- the two real baseline tables were '
      'invisible here until 2026-09-16',
      '_anon_probe_baseline_2026_08_26' in out, out.strip().splitlines()[-1][:70])

# AND THE ARM THE WHOLE CORRECTION IS FOR, driven against the REAL committed
# capture rather than a synthetic base: dropping one of the two baseline tables
# must REFUSE. Under the name rule this was accepted in silence.
BASELINE = '_anon_grant_baseline_2026_08_26'
if BASELINE not in base:
    check('7e  COULD NOT TEST -- %s is no longer in the committed capture, so '
          'the arm that proves underscore-named tables are guarded has nothing '
          'to drop. That is a finding about the capture, not a pass' % BASELINE,
          False)
else:
    gone = dict(base)
    gone['_generated_at'] = NEWER
    gone.pop(BASELINE)
    check('7e  the fixture really drops the baseline', BASELINE not in gone)
    rc, out = run(fixture('lost-baseline.json', gone))
    check('7f  losing an underscore-named REAL table is REFUSED', rc == 1,
          'exit %d' % rc)
    check('7g  and it is named in the refusal', BASELINE in out)

print('8. THE FILE IS NEVER TOUCHED BY A CHECK RUN')
before = io.open(CURRENT, encoding='utf-8').read()
run(fixture('good2.json', good))
run(fixture('short4.json', short))
check('8a  db/schema_snapshot.json is byte-identical after two runs',
      io.open(CURRENT, encoding='utf-8').read() == before,
      'a read-only-sounding tool that mutates is its own section of the process rules')

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
