"""The pre-auth exemption list is anchored to the REFUSAL, not to its line.

Until 2026-09-09 tools/preauth_oracle_accepted.json was keyed on (file, line),
and that is wrong in both directions. This probe holds both.

  DRIFT DOWN (noisy, and how it was found). Adding one import line near the top
  of api/sd-data.js moved its 429 rate limiter from line 388 to 389. The
  exemption keyed at 388 stopped matching and the tool reported a fresh ORACLE
  against code nobody had touched. A gate that cries wolf on an ordinary edit is
  one somebody switches off.

  DRIFT ACROSS (silent, and worse). The same shift runs the other way: a
  DIFFERENT refusal moving INTO an exempted line inherits an exemption written
  for something else. tools/sairn_push_gate_hook.py check 7 BLOCKS on the
  DISCLOSURE tier, so that is a blocking gate quietly ceasing to block.

NOTHING IN THE REPO IS MUTATED. Every arm works on a copy under a temp dir --
deliberately, because this repo has just spent a session establishing that a
probe which edits tracked files is indistinguishable from residue when it dies.

Run: python tests/push_gate/preauth_exemption_anchor_probe.py
"""
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location(
    'preauth', os.path.join(ROOT, 'tools', 'preauth_oracle_check.py'))
PC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PC)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


print('pre-auth exemption anchoring -- an exemption must survive a line shift '
      'and must NOT survive a change of refusal\n')

# ── 0. THE SHIPPED TREE IS THE BASELINE ──────────────────────────────────────
# If this is not clean, every arm below is measuring something else.
accepted = PC.load_accepted()
check('the accepted file loads and is non-empty', len(accepted) > 0, str(len(accepted)))
check('every entry carries a `match`', all(e.get('match') for e in accepted))
check('no entry is keyed on a bare `line`',
      not any('line' in e and 'lines_when_written' not in e
              for e in json.load(io.open(
                  os.path.join(ROOT, 'tools', 'preauth_oracle_accepted.json'),
                  encoding='utf-8'))))

# ── 1. PICK A REAL EXEMPTED REFUSAL, from the shipped tree ───────────────────
TARGET = 'api/sd-data.js'
src_path = os.path.join(ROOT, TARGET)
rel, boundary, found = PC.scan(src_path)
check('the target file has an auth boundary at all', boundary is not None)

hit = None
for line, tier, code, text in (found or []):
    e = PC.accepted_entry(accepted, TARGET, code, text)
    if e is not None:
        hit = (line, tier, code, text, e)
        break
check('at least one refusal in %s is currently exempt' % TARGET, hit is not None)
if hit is None:
    print('\nFAILED  preauth_exemption_anchor_probe: no exempt refusal to test against')
    sys.exit(1)
line, tier, code, text, entry = hit
print('       anchoring on %s:%d [%s] %s' % (TARGET, line, code, entry['match']))

tmp = tempfile.mkdtemp(prefix='sairn-preauth-anchor-')
try:
    # ── 2. DRIFT DOWN: the refusal moves, the exemption must follow ──────────
    # Twenty blank lines at the top of the file. Nothing about the refusal
    # changes; only its line number does.
    raw = io.open(src_path, encoding='utf-8', errors='replace').read()
    shifted = os.path.join(tmp, 'shifted.js')
    io.open(shifted, 'w', encoding='utf-8', newline='').write(('\n' * 20) + raw)
    _r, _b, shifted_found = PC.scan(shifted)
    moved = [f for f in shifted_found if f[3] == text]
    check('the same refusal is still found after the shift', len(moved) >= 1)
    if moved:
        new_line = moved[0][0]
        check('...and it really did move', new_line != line,
              'still at %d' % new_line)
        check('...and it is STILL EXEMPT, keyed on the refusal',
              PC.accepted_entry(accepted, TARGET, moved[0][2], moved[0][3]) is not None)
        # THE CONTROL. The old rule is reproduced here rather than described, so
        # this arm proves the regression was real and not argued.
        old_key = {(e['file'], ln) for e in accepted for ln in e['lines_when_written']}
        check('CONTROL: the OLD line key would have LOST this exemption',
              (TARGET, new_line) not in old_key,
              'the old key still matched -- this arm proves nothing')

    # ── 3. DRIFT ACROSS: a different refusal must NOT inherit the pass ───────
    # The dangerous direction. The exempted refusal is replaced, in place, by a
    # different one carrying a different error code. Its LINE is unchanged, so
    # the old key would have exempted it.
    swapped_text = ("{ error: { code: 'ZZ_PROBE_DIFFERENT', "
                    "message: 'A different refusal entirely.' } }")
    assert text != swapped_text
    body = io.open(src_path, encoding='utf-8', errors='replace').read()
    stripped = PC.strip_comments(body)
    m = PC.REFUSAL_RE.search(stripped, max(0, sum(len(x) + 1 for x in
                                                  body.split('\n')[:line - 1])))
    check('the refusal was located in the raw source for the swap', m is not None)
    if m is not None:
        swapped_src = body[:m.start(2)] + swapped_text + body[m.end(2):]
        swapped = os.path.join(tmp, 'swapped.js')
        io.open(swapped, 'w', encoding='utf-8', newline='').write(swapped_src)
        _r2, _b2, swapped_found = PC.scan(swapped)
        planted = [f for f in swapped_found if 'ZZ_PROBE_DIFFERENT' in f[3]]
        check('the planted refusal is detected at all', len(planted) == 1,
              str([f[:3] for f in swapped_found][:5]))
        if planted:
            p_line, p_tier, p_code, p_text = planted[0]
            check('...and it is NOT exempt -- a different refusal cannot inherit '
                  'somebody else\'s pass',
                  PC.accepted_entry(accepted, TARGET, p_code, p_text) is None)
            old_key = {(e['file'], ln) for e in accepted
                       for ln in e['lines_when_written']}
            check('CONTROL: the OLD line key WOULD have exempted it -- this is the '
                  'silent hole the change closes',
                  (TARGET, p_line) in old_key,
                  'planted at %d; exempted lines for this file: %s'
                  % (p_line, sorted(ln for f, ln in old_key if f == TARGET)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ── 4. THE FILE ITSELF IS AUDITED, not just consulted ────────────────────────
# An exemption that matches nothing is a suppression that outlived what it
# suppressed. It must be reported, and it must not change the verdict.
import subprocess  # noqa: E402  (used only for the end-to-end run below)
out = subprocess.run([sys.executable,
                      os.path.join(ROOT, 'tools', 'preauth_oracle_check.py')],
                     capture_output=True, text=True, cwd=ROOT).stdout
check('the end-to-end run reports a stale-exemption count at all',
      'STALE_EXEMPTIONS:' in out)
check('...and the shipped tree has ZERO stale exemptions',
      'STALE_EXEMPTIONS:0' in out,
      re.sub(r'\s+', ' ', out)[-300:])
check('...and still reports zero disclosures', 'PREAUTH_DISCLOSURES:0' in out)
check('...and zero oracles', 'PREAUTH_ORACLES:0' in out)

print('\n%s  preauth_exemption_anchor_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
