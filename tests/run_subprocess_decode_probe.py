"""Does the decode sweep find the real defect, and can its "clean" ever be false?

    python tests/run_subprocess_decode_probe.py

THE ARM THAT MATTERS IS SECTION 1, and my own open-work row demanded it before
the sweep was written: "a real pass needs a control that FAILS on the unfixed
version, driven with a diff that actually contains the bytes -- a sweep verified
by reading the diff of itself proves nothing."

So section 1 does not describe the defect. It REPRODUCES it, with a real
tracked file, in a real subprocess, and requires the bare call to differ from
the explicit one. If that ever stops reproducing, the 358-site fix is a change
nobody has evidence for.

SECTION 3 EXISTS BECAUSE VERSION TWO OF THE TOOL EDITED ITS OWN DOCSTRING. The
prose in that file contains a literal `subprocess.run(..., text=True)` as an
example, a regex-based scanner matched it, and --fix rewrote the paragraph
explaining the bug. That is CLAUDE.md's standing rule 1.2 -- grep cannot tell
code from text that describes code -- reproduced inside a tool written to close
a different fail-open. The tool walks the AST now and section 3 pins that.
"""
import ast
import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import subprocess_decode_check as d                              # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


print('\n1. THE DEFECT, REPRODUCED -- not described')
# A tracked file whose bytes cp1252 CANNOT decode. Found by measurement, not
# assumed: four exist, including SAIRN-ACTIVE-WORK-cc.md, which is in diffs
# constantly.
undecodable = None
listing = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True,
                         text=True, encoding='utf-8', errors='replace').stdout
for rel in listing.split('\n'):
    rel = rel.strip()
    if not rel.endswith(('.md', '.py', '.js', '.html')):
        continue
    try:
        raw = io.open(os.path.join(REPO, rel), 'rb').read()
    except OSError:
        continue
    try:
        raw.decode('cp1252')
    except UnicodeDecodeError:
        undecodable = rel
        break
check('at least one TRACKED file cannot be decoded as cp1252, so the arms '
      'below are not hypothetical -- %s' % undecodable, undecodable is not None,
      'no such file; the reproduction cannot run and this section proves nothing')

if undecodable:
    args = ['git', 'show', 'HEAD:' + undecodable]
    # ── THE UNFIXED CALL IS BUILT FROM A DICT, ON PURPOSE ────────────────────
    # This probe has to MAKE the defective call in order to reproduce the
    # defect, and the sweep would otherwise report its own reproduction as a
    # finding. The fix is NOT an exclusion list -- an exclusion is how a gate
    # quietly stops covering things. The kwargs are splatted instead, which is a
    # DOCUMENTED blind spot of the tool, and section 2 asserts that blind spot
    # directly: if the tool ever learns to see splatted kwargs, that arm fails
    # and this section has to be rewritten, which is the right order.
    UNFIXED = {'capture_output': True, 'text': True}
    bare = subprocess.run(args, cwd=REPO, **UNFIXED)
    good = subprocess.run(args, cwd=REPO, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')
    check('the EXPLICIT call returns the file', len(good.stdout or '') > 0,
          'the control itself is broken')
    # The bare call either raises in the reader thread (partial output) or
    # decodes to something that is not what the child wrote. EITHER IS THE
    # DEFECT; asserting one specific mode would make this arm fail on a
    # platform where the other one happens.
    check('the BARE call does NOT return what the child wrote -- mojibake or a '
          'raising reader thread, and either is the defect',
          (bare.stdout or '') != (good.stdout or ''),
          'bare and explicit agreed; this platform may not be cp1252, in which '
          'case this arm cannot test anything and should say so rather than pass')
    print('         bare=%d chars, explicit=%d chars'
          % (len(bare.stdout or ''), len(good.stdout or '')))

print('\n2. the sweep reports ZERO on the real tree, and CAN report more')
rows, unparsed = d.scan()
check('zero text-mode subprocess calls without an explicit encoding', not rows,
      [r['file'] + ':' + str(r['line']) for r in rows[:6]])
check('...and no file failed to parse, so the zero is over the whole tree',
      not unparsed, unparsed[:4])
# WITHOUT THIS THE ARM ABOVE WOULD PASS ON A DETECTOR THAT FINDS NOTHING.
BROKEN = "import subprocess\nsubprocess.run(['git', 'status'], text=True)\n"
check('CONTROL: the detector FINDS the unfixed shape in a fixture',
      len(d.findings_in(BROKEN)) == 1, d.findings_in(BROKEN))
FIXED = ("import subprocess\nsubprocess.run(['git'], text=True, "
         "encoding='utf-8', errors='replace')\n")
check('CONTROL: and does NOT find the fixed shape', not d.findings_in(FIXED))
check('CONTROL: text=False is not text mode and is not a finding',
      not d.findings_in("import subprocess\nsubprocess.run(['x'], text=False)\n"))
check('universal_newlines=True is caught too -- the older spelling',
      len(d.findings_in("import subprocess\nsubprocess.run(['x'], "
                        "universal_newlines=True)\n")) == 1)
check('CONTROL: a call on some OTHER module is not a subprocess call',
      not d.findings_in("import x\nx.run(['a'], text=True)\n"))
# THE DOCUMENTED BLIND SPOT, ASSERTED RATHER THAN DESCRIBED. Section 1 relies on
# it to make the defective call without the sweep flagging its own reproduction,
# so if the tool ever learns to see splatted kwargs this arm fails and section 1
# has to be rewritten -- which is the correct order for that to happen in.
check('KNOWN BLIND SPOT: splatted kwargs are invisible to it, which is what '
      'lets section 1 reproduce the defect without an exclusion list',
      not d.findings_in("import subprocess\nK={'text':True}\n"
                        "subprocess.run(['x'], **K)\n"),
      'the tool now sees splatted kwargs -- section 1 needs rewriting')

print('\n3. IT WALKS THE AST -- prose about subprocess is prose')
# Version two used a regex and its --fix rewrote this tool's OWN docstring,
# which contains a subprocess example. Rule 1.2, inside a tool written to fix a
# different fail-open.
DOCSTRING = ('"""Explains the bug:\n'
             "    subprocess.run(cmd, text=True)   # <- an EXAMPLE, not a call\n"
             '"""\nimport subprocess\n')
check('an example inside a docstring is NOT a finding',
      not d.findings_in(DOCSTRING), d.findings_in(DOCSTRING))
COMMENT = "import subprocess\n# subprocess.run(cmd, text=True) is the bug\n"
check('...and neither is one in a comment', not d.findings_in(COMMENT))
src = io.open(os.path.join(REPO, 'tools', 'subprocess_decode_check.py'),
              encoding='utf-8').read()
check('the tool\'s own file is clean under its own rule -- it does not exempt '
      'itself', not d.findings_in(src), d.findings_in(src))

print('\n4. --fix refuses to write a file it broke')
tmp = tempfile.mkdtemp(prefix='decode-fix-probe-')
try:
    p = os.path.join(tmp, 'sample.py')
    io.open(p, 'w', encoding='utf-8', newline='').write(
        "import subprocess\n"
        "r = subprocess.run(\n"
        "    ['git', 'log'],\n"
        "    capture_output=True,\n"
        "    text=True)\n")
    n = d.fix_file(p)
    after = io.open(p, encoding='utf-8').read()
    check('it fixes a MULTI-LINE call -- the shape the first two versions '
          'could not see at all', n == 1 and 'errors=' in after, after)
    try:
        ast.parse(after)
        ok, err = True, None
    except SyntaxError as e:
        ok, err = False, e
    check('...and the result parses', ok, err)
    check('...and re-running it is a no-op, so the sweep is idempotent',
          d.fix_file(p) == 0)
finally:
    try:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)
    except OSError:
        pass

print('\n5. the gates this defect actually reached still run')
# sairn_push_gate_hook.py and sairn_claim.py were the two highest-consequence
# files in the sweep. A change to 137 files is exactly where a broken import
# would be found by somebody else's push rather than here.
for mod in ('sairn_push_gate_hook', 'sairn_claim', 'tier_a_review_gate',
            'tooling_inventory', 'traceability_matrix', 'master_plan'):
    r = subprocess.run([sys.executable, '-c',
                        'import sys; sys.path.insert(0, %r); import %s'
                        % (os.path.join(REPO, 'tools'), mod)],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=120)
    check('tools/%s.py imports' % mod, r.returncode == 0, (r.stderr or '')[:200])


# -- THE MODULE BINDING IS READ, NOT ASSUMED (2026-09-16) -------------------
# is_subprocess_call() required the receiver to be the literal Name
# `subprocess`, so a file that aliased the import was invisible to this
# checker -- not reported clean, not reported at all.
#
# MEASURED: tests/seam_check/run_probe.py line 17 used `import subprocess as
# _sp` and called `_sp.run(..., text=True)` with no encoding. That is the exact
# defect the 358-call sweep was written to eliminate, in a file whose very next
# function already calls subprocess.run WITH the fix. The sweep said "all of
# them"; this call was never in the population it swept.
#
# Third confirmed instance of one class on this platform: a detector that knows
# ONE SPELLING reports every other spelling as ABSENT, and absent reads as
# clean. The other two: the hover auditor's hardcoded guard vocabulary, and
# tests/run_tool_selftest_probe.py seeing `'--selftest' in argv` but not
# argparse.
print(chr(10) + 'the subprocess module binding is read from the imports')

check('an ALIASED module is seen: import subprocess as _sp',
      len(d.findings_in("import subprocess as _sp\n"
                        "_sp.run(['x'], text=True)\n")) == 1)
check('...and the real shape from run_probe.py line 17',
      len(d.findings_in(
          "import subprocess as _sp\n"
          "REPO = _sp.run(['git','rev-parse'],capture_output=True,"
          "text=True).stdout.strip()\n")) == 1)
check('a FROM-import is seen: from subprocess import run',
      len(d.findings_in("from subprocess import run\n"
                        "run(['x'], text=True)\n")) == 1)
check('...and an aliased from-import: from subprocess import run as r',
      len(d.findings_in("from subprocess import run as r\n"
                        "r(['x'], text=True)\n")) == 1)

# BOTH DIRECTIONS. Widening a detector is how it starts firing on things that
# are not its subject, and this checker REWRITES SOURCE -- a false positive
# here edits the wrong line of somebody's file.
check('CONTROL: a local helper named run is NOT subprocess.run',
      not d.findings_in("def run(*a, **k):\n    pass\nrun(['x'], text=True)\n"))
check('CONTROL: an unrelated module aliased to _sp is not matched',
      not d.findings_in("import shutil as _sp\n_sp.run(['x'], text=True)\n"))
check('CONTROL: from-importing a DIFFERENT name does not bind run',
      not d.findings_in("from subprocess import PIPE\nrun(['x'], text=True)\n"))
check('CONTROL: an aliased module WITH an encoding is still clean',
      not d.findings_in("import subprocess as _sp\n"
                        "_sp.run(['x'], text=True, encoding='utf-8')\n"))


print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
