"""tools/sync_write_result_check.py must FIND a discarded write and must NOT
invent one. Both halves, on fixtures, because the live codebase is clean.

    python tests/run_sync_write_result_probe.py

WHY THIS FILE IS PAIRED RATHER THAN POSITIVE-ONLY. The tool reports ONE finding
across every app, and that one carries a written reason in the code beside it.
A checker whose real-world output is a single documented case has, by
construction, never been shown to refuse anything -- so nobody knows whether it
can. And it has equally never been shown NOT to fire on correct code, which is
the failure that actually happened here: the first three versions of this tool
reported 242, then 12, then 3 false positives, every one from reading a LINE
where the codebase had written a CONSTRUCT.

So the negative arms are not decoration. They are the ones that were failing.

CONTROLS_FOR is declared rather than inferred -- three inference models were
each wrong within an hour of being written.
"""
CONTROLS_FOR = ['sync_write_result_check.py']

import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'sync_write_result_check.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run_on(body):
    """Write a fixture app and return (exit code, stdout)."""
    d = tempfile.mkdtemp(prefix='sairn-syncwrite-')
    p = os.path.join(d, 'fixture.html')
    io.open(p, 'w', encoding='utf-8', newline='').write(
        '<html><body><script>\n' + body + '\n</script></body></html>\n')
    r = subprocess.run([sys.executable, TOOL, p], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    try:
        os.remove(p)
        os.rmdir(d)
    except OSError:
        pass
    return r.returncode, out


def count(out, key):
    for line in out.split('\n'):
        if line.startswith(key + ':'):
            return int(line.split(':', 1)[1].split()[0])
    raise AssertionError('the tool printed no %s line -- it did not run to the '
                         'end, so nothing below is measuring what it claims.\n%s'
                         % (key, out[-400:]))


print('sync_write_result_check -- it must find one and invent none\n')

# ── THE POSITIVE. Without this every negative arm below is satisfied by a
# ── tool that reports nothing at all, which is the vacuous-pass shape.
rc, out = run_on("function f(){\n"
                 "  sdnData('write','law_invoices',rec);\n"
                 "}")
check('a bare discarded write IS reported', count(out, 'WRITES_DISCARDED') == 1,
      out[-300:])
check('...and the tool exits non-zero on a finding', rc == 1, 'exit=%s' % rc)

# ── AND IT NAMES THE CLAIM BESIDE IT, because a discarded write under a
# ── success toast is the harm, not the discard alone.
rc, out = run_on("function f(){\n"
                 "  sdnData('write','law_invoices',rec);\n"
                 "  toast('Invoice saved');\n"
                 "}")
check('a success toast near a discarded write is quoted in the finding',
      'Invoice saved' in out, out[-300:])

# ── THE FOUR FALSE-POSITIVE CLASSES THAT REALLY HAPPENED, each one arm ──────
NEGATIVES = [
    ('await is punctuation, not a consumer  (242 false positives)',
     "async function f(){ var saved = await senData('write','sen_claims',rec,true);\n"
     "  if(!saved) toast('not synced'); }"),

    ('a multi-line call consumed by a .then() four lines down  (12 false positives)',
     "function f(){ rfDataRaw('write','rf_proposals',{\n"
     "    a:1,\n"
     "    b:2\n"
     "  }).then(function(r){ if(!r.ok) toast('no'); }); }"),

    ('an array element inside Promise.all([...])  (3 false positives)',
     "async function f(){ var results = await Promise.all([grdData('write','grd_invoices',a)]);\n"
     "  if(!results[0]) toast('no'); }"),

    ('an array element whose bracket opened on an EARLIER line  (3 false positives)',
     "async function f(){ var results=await Promise.all([\n"
     "    grdData('write','grd_invoices',irec),\n"
     "    grdData('write','grd_schedule',srec)\n"
     "  ]);\n"
     "  if(!results[0]) toast('no'); }"),

    ("a write the function RETURNS -- the decision is the caller's",
     "function f(){ return sdnData('write','law_invoices',rec); }"),
]
for label, body in NEGATIVES:
    rc, out = run_on(body)
    check('NOT a finding: ' + label,
          count(out, 'WRITES_DISCARDED') == 0 and rc == 0,
          'discarded=%s exit=%s' % (count(out, 'WRITES_DISCARDED'), rc))

# ── THE BENIGN SINK IS COUNTED, NOT HIDDEN. A tool that silently drops a
# ── class is making a judgement its reader cannot see.
rc, out = run_on("function f(){\n"
                 "  sbData('write', 'shared_knowledge', { words: w });\n"
                 "}")
check('shared_knowledge is NOT counted as a finding',
      count(out, 'WRITES_DISCARDED') == 0, out[-300:])
check('...and IS counted and printed under its own heading',
      count(out, 'WRITES_BENIGN_SINK') == 1 and 'benign sink' in out, out[-400:])
check('...and a benign-only file exits ZERO', rc == 0, 'exit=%s' % rc)

# ── COULD-NOT-TELL IS A THIRD STATE AND IS NOT A PASS ──────────────────────
rc, out = run_on("function f(){\n"
                 "  if (q) foo(1) + sdnData('write','x',r) ;\n"
                 "}")
check('an unclassifiable line is reported as UNREADABLE rather than silently passed',
      count(out, 'WRITES_UNREADABLE') + count(out, 'WRITES_CONSUMED') >= 1, out[-300:])

# ── THE FIFTH FALSE-POSITIVE CLASS: A CALL INSIDE A COMMENT (2026-09-24) ───
# Four were already found and fixed -- `await` read as a consumer, a delayed
# multi-line `.then()`, an array element inside `Promise.all([`, and a bracket
# opened on an earlier line. This is the fifth, and it left three PERMANENT
# could-not-tells on the live codebase: comments explaining a write, two of
# them explaining a write that had been REMOVED.
rc, out = run_on("function f(){\n"
                 "  // sdnData('write','dnt_complaints',{id:1});\n"
                 "}")
check('a transport call inside a // comment is not counted as a write at all',
      count(out, 'WRITES_CONSUMED') + count(out, 'WRITES_DISCARDED')
      + count(out, 'WRITES_UNREADABLE') == 0, out[-300:])

rc, out = run_on("function f(){\n"
                 "  // Was sdnData('write','specitems_bulk',{p:1}) -- removed\n"
                 "  var ok = await sdnData('write','x',r);\n"
                 "  if (!ok) toast('no');\n"
                 "}")
check('...and the REAL write on the next line is still found',
      count(out, 'WRITES_CONSUMED') == 1, out[-300:])

# THE FALSE NEGATIVE THIS FIX COULD HAVE INTRODUCED, and the reason the
# stripper is quote-aware instead of `split('//')[0]`: a `//` inside a STRING
# is not a comment, and truncating there would LOSE a real call -- trading
# three false positives for a false negative, which is the worse trade.
rc, out = run_on("function f(){\n"
                 "  sdnData('write','x',{url:'http://a/b'});\n"
                 "}")
check('a // inside a string literal does NOT truncate the line -- the write is '
      'still seen',
      count(out, 'WRITES_DISCARDED') + count(out, 'WRITES_CONSUMED')
      + count(out, 'WRITES_UNREADABLE') == 1, out[-300:])

rc, out = run_on("function f(){\n"
                 "  var ok = await sdnData('write','x',{url:'https://a'}); // fire\n"
                 "  if (!ok) toast('no');\n"
                 "}")
check('...and a real trailing comment after a string-bearing call is still '
      'stripped without losing the call',
      count(out, 'WRITES_CONSUMED') == 1, out[-300:])

# ── THE FOUR ARMS ADDED 2026-09-25, ONE PER FIX ────────────────────────────
# The tool was blind to seven transports and 58 write sites; its exit code
# reported SUCCESS on a run that classified nothing; a call at the start of a
# block scored UNREADABLE; and the BENIGN exemption matched a substring of the
# whole call. Each fix gets an arm and each arm is driven in BOTH directions,
# because an arm that only proves the new behaviour cannot tell a fix from a
# blanket.

# 1. A TRANSPORT NOBODY ADDED IS A THIRD STATE, NOT A CLEAN FILE. This is the
# arm that would have caught the original defect: `zzData` is in neither list, so
# its write site is not scanned at all, and a report over a population it cannot
# see must not exit 0.
rc, out = run_on("function f(){\n"
                 "  zzData('write','x',rec);\n"
                 "}")
check('a transport in NEITHER list is reported by name, with its write count',
      'TRANSPORT NOT IN THE LIST' in out and 'zzData' in out, out[-400:])
check('...and a run that could not see a write site does NOT exit 0',
      rc == 2, 'exit=%s' % rc)
# CONTROL: a KNOWN transport must not be reported as unknown, or the arm above
# would pass on a tool that flagged everything.
rc, out = run_on("function f(){\n"
                 "  var ok = await sdnData('write','x',rec);\n"
                 "  if (!ok) toast('no');\n"
                 "}")
check('CONTROL: a KNOWN transport is not reported as unknown, and that run exits 0',
      'TRANSPORT NOT IN THE LIST' not in out and rc == 0, 'exit=%s %s' % (rc, out[-300:]))
# CONTROL: and a name in NOT_A_TRANSPORT is silent rather than a third state --
# `sdDataFailed` is stonedesk.html's console reporter and takes 'write' as its
# first argument, which is how that list came to exist.
rc, out = run_on("function f(){\n"
                 "  sdDataFailed('write','x','why');\n"
                 "}")
check('CONTROL: a name declared NOT_A_TRANSPORT is neither scanned nor reported',
      'TRANSPORT NOT IN THE LIST' not in out and rc == 0, 'exit=%s %s' % (rc, out[-300:]))

# 2. "N UNREADABLE, NO DISCARDS" MUST NOT EXIT 0. The whole top of the tool
# argues a could-not-tell is never folded into a pass; the exit code folded it.
rc, out = run_on("function f(){\n"
                 "  foo(bar) sdnData('write','x',rec)\n"
                 "}")
check('an unreadable line with NO discards exits 2, not 0 -- the could-not-tell '
      'is not folded into a pass at the process level',
      rc == 2 and count(out, 'WRITES_UNREADABLE') >= 1 and count(out, 'WRITES_DISCARDED') == 0,
      'exit=%s %s' % (rc, out[-300:]))
# CONTROL: a real FINDING still outranks a could-not-tell. A confirmed discarded
# write is worse news than an unread line and must not be downgraded by one
# arriving beside it.
rc, out = run_on("function f(){\n"
                 "  foo(bar) sdnData('write','x',rec)\n"
                 "  sdnData('write','y',rec2);\n"
                 "}")
check('CONTROL: a DISCARDED write alongside an unreadable line still exits 1, '
      'not 2 -- a finding outranks a third state',
      rc == 1 and count(out, 'WRITES_DISCARDED') == 1, 'exit=%s %s' % (rc, out[-300:]))

# 3. A CALL AT THE START OF A BLOCK IS A BARE STATEMENT. `if (c) { try { x(); }
# catch(e) {} }` scored UNREADABLE, and a permanent could-not-tell on a real
# discarded write is the weakest answer this tool can give.
rc, out = run_on("function f(){\n"
                 "  if (c && c.id) { try { sdnData('write','x',c); } catch (e) {} }\n"
                 "}")
check('a write at the start of a block is DISCARDED, not UNREADABLE',
      count(out, 'WRITES_DISCARDED') == 1 and count(out, 'WRITES_UNREADABLE') == 0,
      out[-400:])
# CONTROL: and a BOUND write inside the same nesting is still READ, or the arm
# above would pass on a tool that called every nested call discarded.
rc, out = run_on("function f(){\n"
                 "  if (c && c.id) { try { var ok = await sdnData('write','x',c); "
                 "if (!ok) toast('no'); } catch (e) {} }\n"
                 "}")
check('CONTROL: a BOUND write at the same nesting is still READ',
      count(out, 'WRITES_CONSUMED') == 1 and count(out, 'WRITES_DISCARDED') == 0,
      out[-400:])

# 4. THE BENIGN EXEMPTION IS THE RESOURCE ARGUMENT, NOT A SUBSTRING. A benign
# name appearing anywhere in the call -- in the payload, in a field value --
# silenced a real discarded write on a DIFFERENT resource.
rc, out = run_on("function f(){\n"
                 "  sdnData('write','sd_customers',{tag:'shared_knowledge'});\n"
                 "}")
check('a benign NAME inside the payload does not exempt a write on another '
      'resource -- the exemption reads the second ARGUMENT',
      count(out, 'WRITES_DISCARDED') == 1 and count(out, 'WRITES_BENIGN_SINK') == 0,
      out[-400:])
# CONTROL: the real benign sink is still exempt, or the arm above would pass on a
# tool whose exemption had stopped working entirely.
rc, out = run_on("function f(){\n"
                 "  sdnData('write','shared_knowledge',{words:w});\n"
                 "}")
check('CONTROL: the genuine benign sink is still exempt and still printed',
      count(out, 'WRITES_BENIGN_SINK') == 1 and count(out, 'WRITES_DISCARDED') == 0
      and 'benign sink' in out, out[-400:])

# 5. continues_open_construct MUST NOT FAIL OPEN ON A STRING-INTERNAL `//`.
# It used `split('//')[0]`, so a previous line carrying a URL truncated to
# something ending in `:` -- one of OPENS -- and the bare call below was scored
# READ. A false PASS in the function whose job is preventing false findings.
rc, out = run_on("function f(){\n"
                 "  var u = 'http://a/b';\n"
                 "  sdnData('write','x',rec);\n"
                 "}")
check('a string-internal // on the PREVIOUS line does not make a bare write '
      'look like a continuation -- it is still DISCARDED',
      count(out, 'WRITES_DISCARDED') == 1, out[-400:])
# CONTROL: a genuine open construct on the previous line is still honoured --
# SAIRNgrounds' Promise.all([ ... ]) is the real case this exists for.
rc, out = run_on("function f(){\n"
                 "  var results = await Promise.all([\n"
                 "    sdnData('write','x',a)\n"
                 "  ]);\n"
                 "  if (!results[0]) toast('no');\n"
                 "}")
check('CONTROL: a genuine bracket opened on the previous line is still READ',
      count(out, 'WRITES_DISCARDED') == 0, out[-400:])

# ── A FILE IT CANNOT READ IS NOT A CLEAN FILE ──────────────────────────────
r = subprocess.run([sys.executable, TOOL, 'no-such-file-anywhere.html'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
check('a missing target is COULD NOT RUN (exit 2), never a clean scan',
      r.returncode == 2 and 'COULD NOT RUN' in (r.stdout or ''),
      'exit=%s' % r.returncode)

# ── AND THE LIVE CODEBASE, so the arms above are not measuring a fixture
# ── dialect the real apps do not use.
r = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace')
live = (r.stdout or '')
check('the real apps parse -- hundreds of writes classified, not zero',
      count(live, 'WRITES_CONSUMED') > 200,
      'consumed=%s' % count(live, 'WRITES_CONSUMED'))

print('\n%s  run_sync_write_result_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
