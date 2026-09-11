"""The control-character check must catch what it exists to catch.

    python tests/run_control_char_probe.py

A checker that has only ever returned CLEAN is not evidence. This drives the
real `tools/control_char_check.py` against throwaway fixture repos in a temp
directory -- never against this repo -- covering:

  * a raw NUL in a string literal, the shape that made `api/sd-data.js`
    unsearchable by grep for as long as it was there;
  * a raw NUL in a COMMENT, which has no runtime meaning at all and is
    therefore the easiest version to dismiss;
  * a literal BACKSPACE where `\\b` was meant -- the shape that left a database
    privilege assertion unable to fail;
  * the ESCAPE SEQUENCE for the same byte, which must be CLEAN, or the fix the
    tool recommends would trip the tool;
  * tab / newline / CR, which must be CLEAN, or every file in the repo is a
    finding;
  * a genuine binary file, which must be SKIPPED and must be NAMED -- a
    category quietly dropped is how a real file hides;
  * an UNTRACKED file with a NUL, which must NOT be reported: the tool derives
    its file list from `git ls-files`, and a scratch file is not source.

The last three arms are the ones worth having. Anyone would write the first.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'control_char_check.py')

NUL = bytes([0])
BS = bytes([8])
fails = 0


def check(label, actual, expected):
    global fails
    if actual == expected:
        print('  ok    %s' % label)
        return True
    fails += 1
    print('FAIL  %s\n        expected %r\n        actual   %r'
          % (label, expected, actual))
    return False


def build(tmp, files, untracked=None):
    """A throwaway repo with a copy of the tool and the given files."""
    os.makedirs(os.path.join(tmp, 'tools'), exist_ok=True)
    shutil.copy(TOOL, os.path.join(tmp, 'tools', 'control_char_check.py'))
    for name, body in files.items():
        full = os.path.join(tmp, name)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with io.open(full, 'wb') as fh:
            fh.write(body)
    subprocess.run(['git', 'init', '-q'], cwd=tmp, capture_output=True)
    subprocess.run(['git', 'add', '-A'], cwd=tmp, capture_output=True)
    # Written AFTER `git add`, so it is genuinely untracked.
    for name, body in (untracked or {}).items():
        with io.open(os.path.join(tmp, name), 'wb') as fh:
            fh.write(body)


def run(tmp):
    r = subprocess.run([sys.executable,
                        os.path.join(tmp, 'tools', 'control_char_check.py')],
                       cwd=tmp, capture_output=True, text=True)
    return r.returncode, r.stdout


tmp = tempfile.mkdtemp(prefix='ctrlchar-')
n = [0]


def case(name, files, untracked=None):
    n[0] += 1
    d = os.path.join(tmp, '%02d-%s' % (n[0], name))
    os.makedirs(d)
    build(d, files, untracked)
    return run(d)

# ── the control: ordinary source with tab, newline and CR is CLEAN ────────
rc, out = case('clean', {
    'a.js': b"const x = 1;\r\n\tconst y = 2;\n",
    'b.py': b"def f():\n\treturn '\\x00'\n",
})
check('tab, newline and CR are CLEAN', rc, 0)
check('and it says so', 'CLEAN' in out, True)
check('and an ESCAPE SEQUENCE is not a finding -- the recommended fix must pass',
      '\\x00' in out.replace('write \\x00', ''), False)

# ── a raw NUL in a string literal ─────────────────────────────────────────
rc, out = case('nul-string', {'a.js': b"const k = id + '" + NUL + b"' + res;\n"})
check('a raw NUL in a string literal FAILS', rc, 1)
check('and the byte is named', '0x00' in out, True)
check('and the file and line are named', 'a.js:1' in out, True)

# ── a raw NUL in a COMMENT: no runtime meaning, still a finding ────────────
rc, out = case('nul-comment', {'a.js': b"// key: employee " + NUL + b" date\n"})
check('a raw NUL in a COMMENT still FAILS', rc, 1)

# ── a literal BACKSPACE where \b was meant ────────────────────────────────
rc, out = case('backspace', {
    't.js': b"assert.ok(!/grant[^;]*" + BS + b"delete" + BS + b"/i.test(sql));\n"})
check('a literal BACKSPACE FAILS', rc, 1)
check('and the message points at the \\b mistake specifically',
      'word boundary' in out, True)
check('and BOTH occurrences on the line are reported',
      out.count('t.js:1') , 2)

# ── the line number must be right on a multi-line file ────────────────────
rc, out = case('lineno', {
    'a.js': b"one\ntwo\nthree\nconst k = '" + NUL + b"';\nfive\n"})
check('the line number is the line the byte is on', 'a.js:4' in out, True)

# ── a real binary file is SKIPPED, and NAMED ──────────────────────────────
rc, out = case('binary', {
    'a.js': b"const x = 1;\n",
    'assets/logo.png': b'\x89PNG\r\n\x1a\n' + NUL * 20,
})
check('a binary file does not make the run FAIL', rc, 0)
check('and the skip is PRINTED, not silent', 'skipped as binary' in out, True)
check('and the skipped file is NAMED', 'logo.png' in out, True)

# ── an UNTRACKED file is not source ───────────────────────────────────────
rc, out = case('untracked', {'a.js': b"const x = 1;\n"},
               untracked={'scratch.bin': b'x' + NUL + b'y'})
check('an UNTRACKED file with a NUL is NOT reported', (rc, 'scratch' in out),
      (0, False))

# ── 0x7f DEL is a hit too ─────────────────────────────────────────────────
rc, out = case('del', {'a.js': b"const x = '\x7f';\n"})
check('0x7f DEL FAILS', rc, 1)

# ── and the REAL repo is clean, since that is what it is for ──────────────
r = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                   text=True)
check('the real SAIRN tree is currently clean', r.returncode, 0)

print()
if fails:
    print('%d FAILED' % fails)
    sys.exit(1)
print('ALL PASS -- an escape sequence typed as its literal control character '
      'cannot reach the tree unnoticed again.')
