"""Prove --live discriminates, using handler names OBSERVED on the deployed app.

A checker that has only returned clean is unproven, and a --live mode that
clears nothing is indistinguishable from one that is not running. This exercises
all four outcomes with fixtures, plus records the real live observation that
motivated the mode.

REAL OBSERVATION, 2026-09-01, https://sairn.vercel.app/stonedesk:
  All seven static R3 findings on stonedesk.html were checked against the
  RENDERED DOM. Every one: defined_on_window true, wired_in_live_dom FALSE, and
  -- the important part -- mentioned_anywhere TRUE. That last flag is exactly
  what a source grep sees, and it is exactly why grep cannot answer this
  question. The static findings were right; live turns them from "needs a read
  before you believe it" into confirmed.

  It also separated two names a grep conflates: `safetyExport` IS wired in the
  live DOM, `sdSafetyExport` is not. They are different functions.
"""
import json
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'sairn_reachability_check.py')
TARGET = 'stonedesk.html'

# Names genuinely present in live on*= handlers on the deployed page.
OBSERVED_WIRED = [
    'safetyExport', 'safetyLogIncident', 'saWipeAppData', 'openCamera',
    'sairnFQAnalyze', 'renderCustomers', 'posCompleteSale',
]
# The seven static R3 findings, confirmed NOT wired in the live DOM.
CONFIRMED_ORPHANS = [
    'crPostGL', 'crSave', 'openFQ', 'saDebounce',
    'sairnOpenFQ', 'sairnOpenPricing', 'sdSafetyExport',
]


def snap(**kw):
    base = dict(_generated_at='fixture', url='fixture',
                handler_names=list(OBSERVED_WIRED),
                panels_total=62, panels_with_handlers=62,
                panels_with_rendered_rows=9, gated=False)
    base.update(kw)
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        json.dump(base, fh)
    return path


def run(*extra):
    r = subprocess.run([sys.executable, TOOL] + list(extra) + [TARGET],
                       cwd=REPO, capture_output=True, text=True)
    return r.returncode, r.stdout


R = {}

rc, out = run()
R['static_only_still_reports'] = (rc == 1 and all(n in out for n in CONFIRMED_ORPHANS))

# 1. A good snapshot must NOT clear the seven, because they really are unwired.
p = snap()
rc, out = run('--live', p)
R['real_orphans_survive_live'] = (rc == 1 and all(n in out for n in CONFIRMED_ORPHANS))
R['nothing_falsely_cleared'] = ('cleared by the live DOM' not in out)
os.remove(p)

# 2. If one of them WERE wired at runtime, live must clear it. This is the
#    false-positive class the mode exists for -- a handler written by JS.
p = snap(handler_names=OBSERVED_WIRED + ['sdSafetyExport'])
rc, out = run('--live', p)
R['wired_at_runtime_is_cleared'] = ('sdSafetyExport' in out and 'wired at RUNTIME' in out)
R['others_still_reported'] = all(n in out for n in CONFIRMED_ORPHANS if n != 'sdSafetyExport')
os.remove(p)

# 3. A snapshot of the licence gate describes the gate. It must clear nothing.
p = snap(gated=True, handler_names=OBSERVED_WIRED + ['sdSafetyExport'])
rc, out = run('--live', p)
R['gate_snapshot_clears_nothing'] = ('LICENCE GATE' in out and 'sdSafetyExport' in out
                                     and 'wired at RUNTIME' not in out)
os.remove(p)

# 4. An under-covered snapshot is a could-not-tell, not a pass.
p = snap(panels_with_handlers=3, handler_names=OBSERVED_WIRED + ['sdSafetyExport'])
rc, out = run('--live', p)
R['low_coverage_clears_nothing'] = ('below the' in out and 'wired at RUNTIME' not in out)
os.remove(p)

# 5. --require-live with no snapshot must fail closed with exit 2.
rc, out = run('--require-live')
R['require_live_fails_closed'] = (rc == 2 and 'not a pass' in out)

for k, v in R.items():
    print('%-32s %s' % (k, v))
print()
ok = all(R.values())
print('LIVE MODE VERIFIED:', ok)
sys.exit(0 if ok else 1)
