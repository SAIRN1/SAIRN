"""The SOUP register check must catch what it exists to catch.

    python tests/run_soup_register_probe.py

A checker that has only ever returned CLEAN is not evidence. This drives the
real `tools/soup_register_check.py` against throwaway fixtures in a temp
directory -- never against the repo -- covering the drift that actually happens
to a register:

  * a new npm dependency nobody added to it;
  * a new CDN script nobody added to it, which is the half an npm audit cannot
    see and the half this platform's two weakest components live in;
  * a VERSION that moved under an entry written against the old one -- a
    register entry describing software nobody is running;
  * an entry for something that has been REMOVED, because a register that only
    grows starts lying about what is running;
  * missing Subresource Integrity, which now FAILS. It was a report-only note
    until 2026-09-10, correctly, while every CDN script lacked SRI and the
    register owned that with an open-work row -- a check that is red on a
    recorded, owned state teaches people to ignore it. All four are hashed now,
    so a missing integrity attribute is a regression, and the arm below asserts
    the new behaviour rather than the old;
  * a CDN script INJECTED FROM JS rather than written as a `<script src>` tag.
    This is the arm that exists because the tool shipped without it: it reported
    `CLEAN -- every running component is in the register` while `tesseract.js@5`
    ran unregistered on a floating major in `sairnlaw.html`, invisible to
    Semgrep's `missing-integrity`, StoneDesk's Layer 12, and this checker, all
    for the same reason;
  * a FLOATING major, which is a version in the URL and still not a pin;
  * a prose table INSIDE an entry, whose rows must not be read as components.
    The scoping fix for that was itself caught by running the tool against the
    real register, not by reasoning about it.

The later arms are the ones worth having. Anyone would write the first.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'soup_register_check.py')

fails = 0


def check(label, actual, expected):
    global fails
    if actual == expected:
        print('  ok    %s' % label)
        return True
    fails += 1
    print('FAIL  %s\n        expected %r\n        actual   %r' % (label, expected, actual))
    return False


def build(tmp, deps, lockversions, html, register):
    """A throwaway repo just real enough for the tool: git, package files, apps."""
    os.makedirs(os.path.join(tmp, 'docs'), exist_ok=True)
    os.makedirs(os.path.join(tmp, 'tools'), exist_ok=True)
    shutil.copy(TOOL, os.path.join(tmp, 'tools', 'soup_register_check.py'))
    io.open(os.path.join(tmp, 'package.json'), 'w', encoding='utf-8').write(
        json.dumps({'name': 'fixture', 'dependencies': deps}))
    io.open(os.path.join(tmp, 'package-lock.json'), 'w', encoding='utf-8').write(
        json.dumps({'lockfileVersion': 3, 'packages': dict(
            [('', {'dependencies': deps})] +
            [('node_modules/' + k, {'version': v}) for k, v in lockversions.items()])}))
    for name, body in html.items():
        io.open(os.path.join(tmp, name), 'w', encoding='utf-8').write(body)
    io.open(os.path.join(tmp, 'docs', 'SOUP-REGISTER.md'), 'w', encoding='utf-8').write(register)
    subprocess.run(['git', 'init', '-q'], cwd=tmp, capture_output=True)
    subprocess.run(['git', 'add', '-A'], cwd=tmp, capture_output=True)


def run(tmp):
    r = subprocess.run([sys.executable, os.path.join(tmp, 'tools', 'soup_register_check.py')],
                       cwd=tmp, capture_output=True, text=True)
    return r.returncode, r.stdout


BASE_DEPS = {'stripe': '^17.0.0'}
BASE_LOCK = {'stripe': '17.7.0'}
# The control now carries integrity, because missing SRI is a failure rather
# than a note -- a control that trips the check is not a control.
BASE_HTML = {'app.html': '<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/q.js" '
                         'integrity="sha384-x" crossorigin="anonymous"></script>'}
BASE_REG = ('## Server-side\n\n| Component | Version |\n|---|---|\n'
            '| `stripe` | 17.7.0 |\n\n'
            '## Browser-side\n\n| Component | Version |\n|---|---|\n'
            '| `qrcodejs` | 1.0.0 |\n')

INJECTED = ("<script>\n"
            "var s=document.createElement('script');\n"
            "s.src='https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/t.min.js';\n"
            "%s"
            "document.head.appendChild(s);\n"
            "</script>\n")
INJ_SRI = "s.integrity='sha384-y';s.crossOrigin='anonymous';\n"

tmp = tempfile.mkdtemp(prefix='soup-')

# ── the control: a register that matches reality passes ───────────────────
d = os.path.join(tmp, 'clean')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK, BASE_HTML, BASE_REG)
rc, out = run(d)
check('a register matching reality is CLEAN', rc, 0)
check('and it says so', 'CLEAN' in out, True)

# ── an undeclared npm dependency ──────────────────────────────────────────
d = os.path.join(tmp, 'newdep')
os.makedirs(d)
build(d, dict(BASE_DEPS, **{'left-pad': '^1.0.0'}),
      dict(BASE_LOCK, **{'left-pad': '1.3.0'}), BASE_HTML, BASE_REG)
rc, out = run(d)
check('a new npm dependency missing from the register FAILS', rc, 1)
check('and it is named', 'left-pad' in out, True)

# ── an undeclared CDN script: the half npm audit cannot see ───────────────
d = os.path.join(tmp, 'newcdn')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK,
      {'app.html': BASE_HTML['app.html'] +
       '\n<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>'},
      BASE_REG)
rc, out = run(d)
check('a new CDN script missing from the register FAILS', rc, 1)
check('and it names the component, not the URL', '@supabase/supabase-js' in out, True)
check('and it names the app that loads it', 'app.html' in out, True)

# ── a version that moved under an entry ───────────────────────────────────
d = os.path.join(tmp, 'moved')
os.makedirs(d)
build(d, BASE_DEPS, {'stripe': '18.0.1', 'qrcodejs': '1.0.0'}, BASE_HTML, BASE_REG)
rc, out = run(d)
check('an installed version the register does not name FAILS', rc, 1)
check('and it says what is actually installed', '18.0.1' in out, True)

# ── an entry for something that is gone ───────────────────────────────────
d = os.path.join(tmp, 'stale')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK, BASE_HTML,
      BASE_REG + '| `firebase-admin` | 12.7.0 |\n')
rc, out = run(d)
check('an entry for a REMOVED component FAILS', rc, 1)
check('and it names the stale entry', 'firebase-admin' in out, True)

# ── missing SRI now FAILS, and used to be a note ──────────────────────────
d = os.path.join(tmp, 'sri')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK,
      {'app.html': '<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/q.js"></script>'},
      BASE_REG)
rc, out = run(d)
check('a static script with NO integrity FAILS', rc, 1)
check('and the finding names Subresource Integrity', 'Subresource Integrity' in out, True)

# ── the arm the tool shipped without: a script injected from JS ───────────
# Registered and hashed -- must be clean, or the new detection is just noise.
d = os.path.join(tmp, 'inj-ok')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK,
      {'app.html': BASE_HTML['app.html'] + (INJECTED % INJ_SRI)},
      BASE_REG + '| `tesseract.js` | 5.1.1 |\n')
rc, out = run(d)
check('a registered, hashed, pinned INJECTED script is CLEAN', (rc, 'CLEAN' in out), (0, True))

# Unregistered -- the exact live miss.
d = os.path.join(tmp, 'inj-missing')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK,
      {'app.html': BASE_HTML['app.html'] + (INJECTED % INJ_SRI)}, BASE_REG)
rc, out = run(d)
check('an INJECTED script missing from the register FAILS', rc, 1)
check('and it names the component', 'tesseract.js' in out, True)

# Injected and unhashed -- invisible to every static-tag check there is.
d = os.path.join(tmp, 'inj-nosri')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK,
      {'app.html': BASE_HTML['app.html'] + (INJECTED % '')},
      BASE_REG + '| `tesseract.js` | 5.1.1 |\n')
rc, out = run(d)
check('an INJECTED script with no integrity FAILS', rc, 1)
check('and the finding is about SRI, not about registration',
      ('Subresource Integrity' in out, 'NOT in the register' in out), (True, False))

# ── a floating major is a version in the URL and still not a pin ──────────
d = os.path.join(tmp, 'floating')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK,
      {'app.html': '<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1/q.js" '
                   'integrity="sha384-x" crossorigin="anonymous"></script>'},
      BASE_REG)
rc, out = run(d)
check('a FLOATING major FAILS even with an integrity hash', rc, 1)
check('and the finding says floating', 'FLOATING' in out, True)

# ── an entry's own prose table is not a list of components ────────────────
# The scoping bug this asserts against was real: the sub-resource breakdown in
# the tesseract entry was read as a stale component entry.
d = os.path.join(tmp, 'prose')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK, BASE_HTML,
      BASE_REG + '\n### `qrcodejs` — why it is trusted\n\n'
                 '| Fetched | From | Hashed? |\n|---|---|---|\n'
                 '| `worker.min.js` | a CDN | no |\n')
rc, out = run(d)
check('a prose table inside an entry is not read as a component', rc, 0)
check('and worker.min.js is not reported as a stale entry',
      'worker.min.js' in out, False)

# ── a missing register is a hard fail, not a clean run ────────────────────
d = os.path.join(tmp, 'noreg')
os.makedirs(d)
build(d, BASE_DEPS, BASE_LOCK, BASE_HTML, BASE_REG)
os.remove(os.path.join(d, 'docs', 'SOUP-REGISTER.md'))
rc, out = run(d)
check('a missing register exits 2 rather than passing', rc, 2)

# ── and the REAL repo is clean, since that is what it is for ──────────────
r = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True, text=True)
check('the real SAIRN register is currently clean', r.returncode, 0)

print()
if fails:
    print('%d FAILED' % fails)
    sys.exit(1)
print('ALL PASS -- the register cannot drift from what is actually running.')
