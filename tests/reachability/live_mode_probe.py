"""Prove --live discriminates, on FIXTURES rather than on names in a live file.

A checker that has only returned clean is unproven, and a --live mode that
clears nothing is indistinguishable from one that is not running. This
exercises all four outcomes, plus the two fail-closed paths.

── WHY THIS WAS REWRITTEN, 2026-09-08 ──────────────────────────────────────
The first version anchored every arm to SEVEN REAL R3 FINDINGS observed on
the deployed stonedesk.html on 2026-09-01: crPostGL, crSave, openFQ,
saDebounce, sairnOpenFQ, sairnOpenPricing, sdSafetyExport. It asserted the
static pass still reported them, that a good snapshot did not clear them, and
that planting one in a snapshot cleared exactly that one.

ALL SEVEN WERE REMOVED FROM stonedesk.html ON 2026-09-02 -- the day after this
probe was written. The file carries their headstones (`// sdSafetyExport
REMOVED 2026-09-02 -- superseded, not lost`). So the checker became correct
and the probe became wrong, together, and five of its eight arms went red.

IT WENT RED FOR SIX DAYS AND NOTHING SAID SO, because no runner executes
tests/**/*.py -- the same reason tests/fail_open_browser_probe.py sat with two
dead arms until 2026-09-08. Both are the same shape: A PROBE PINNED TO A REAL,
CURRENT DEFECT ROTS THE MOMENT THAT DEFECT IS FIXED. Succeeding at the work
breaks the test that watched it.

So the arms below use SYNTHETIC fixtures written to a temp file: one function
that is genuinely an orphan by construction, one that is genuinely wired in
markup. They cannot be fixed out from under the probe, and they do not depend
on what any real app happens to contain this week.

THE REAL OBSERVATION IS KEPT, because it is why the mode exists:
  2026-09-01, https://sairn.vercel.app/stonedesk -- all seven static R3
  findings were checked against the RENDERED DOM. Every one: defined_on_window
  true, wired_in_live_dom FALSE, and mentioned_anywhere TRUE. That last flag is
  exactly what a source grep sees, and exactly why grep cannot answer this.
  It also separated two names a grep conflates: `safetyExport` IS wired live,
  `sdSafetyExport` was not. Different functions.
"""
import json
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'sairn_reachability_check.py')

# One orphan and one wired handler, by construction. `zzWired` is called from
# an onclick in the markup, so the static pass must never report it; `zzOrphan`
# is defined on window and referenced nowhere, so it must always be reported
# unless a live snapshot says otherwise.
FIXTURE = """<!doctype html>
<div class="panel" id="panel-zz">
  <button onclick="zzWired()">Wired</button>
</div>
<script>
window.zzWired = function () { return 1; };
window.zzOrphan = function () { return 2; };
</script>
"""

ORPHAN = 'zzOrphan'
WIRED = 'zzWired'


def fixture_file():
    path = os.path.join(REPO, 'zz_reach_fixture.html')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(FIXTURE)
    return path


def snap(**kw):
    base = dict(_generated_at='fixture', url='fixture',
                handler_names=[WIRED],
                panels_total=1, panels_with_handlers=1,
                panels_with_rendered_rows=1, gated=False)
    base.update(kw)
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        json.dump(base, fh)
    return path


def run(target, *extra):
    r = subprocess.run([sys.executable, TOOL] + list(extra) + [target],
                       cwd=REPO, capture_output=True, text=True)
    return r.returncode, r.stdout


R = {}
target = fixture_file()
try:
    rel = os.path.basename(target)

    # 0. The static pass finds the orphan and leaves the wired one alone.
    #    Without this arm every other result could come from a scan that found
    #    nothing at all -- which is exactly how the previous version died.
    rc, out = run(rel)
    R['static_reports_the_orphan'] = (rc == 1 and ORPHAN in out)
    R['static_leaves_the_wired_one_alone'] = (WIRED not in out)

    # 1. A good snapshot that does NOT contain the orphan must not clear it.
    p = snap()
    rc, out = run(rel, '--live', p)
    R['real_orphan_survives_live'] = (rc == 1 and ORPHAN in out)
    R['nothing_falsely_cleared'] = ('cleared by the live DOM' not in out)
    os.remove(p)

    # 2. If the orphan IS wired at runtime, live must clear it. This is the
    #    false-positive class the mode exists for -- a handler written by JS.
    p = snap(handler_names=[WIRED, ORPHAN])
    rc, out = run(rel, '--live', p)
    R['wired_at_runtime_is_cleared'] = (ORPHAN in out and 'wired at RUNTIME' in out)
    os.remove(p)

    # 3. A snapshot of the licence gate describes the gate. It must clear nothing.
    p = snap(gated=True, handler_names=[WIRED, ORPHAN])
    rc, out = run(rel, '--live', p)
    R['gate_snapshot_clears_nothing'] = ('LICENCE GATE' in out and ORPHAN in out
                                         and 'wired at RUNTIME' not in out)
    os.remove(p)

    # 4. An under-covered snapshot is a could-not-tell, not a pass.
    p = snap(panels_total=10, panels_with_handlers=1, handler_names=[WIRED, ORPHAN])
    rc, out = run(rel, '--live', p)
    R['low_coverage_clears_nothing'] = ('below the' in out and 'wired at RUNTIME' not in out)
    os.remove(p)

    # 5. --require-live with no snapshot must fail closed with exit 2.
    rc, out = run(rel, '--require-live')
    R['require_live_fails_closed'] = (rc == 2 and 'not a pass' in out)

    # 6. A TARGETED RUN MUST NOT REPORT ANOTHER FILE'S EXEMPTIONS AS STALE.
    #    A file that was never scanned cannot match anything, so comparing
    #    every exemption against a one-file run declares live entries dead.
    #    That happened on 2026-09-08: a run of one unrelated file printed both
    #    of stonedesk.html's exemptions under "should be deleted", and acting
    #    on it un-suppressed two real R1 findings. The sibling checker
    #    fail_open_check.py had already been fixed for exactly this; this one
    #    had not.
    #
    # DRIVEN IN BOTH DIRECTIONS with a genuinely dead exemption injected into
    # the real file, because suppressing the message everywhere would trade a
    # false alarm for a silent one -- and that is the easy mistake here.
    EX = os.path.join(REPO, 'tools', 'reachability_exemptions.json')
    original = open(EX, encoding='utf-8').read()
    try:
        doc = json.loads(original)
        doc['exemptions'].append({'file': 'zz_no_such_file.html', 'code': 'R3',
                                  'name': 'zzDefinitelyNotAFinding',
                                  'added': 'probe', 'reason': 'probe fixture'})
        with open(EX, 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, indent=2)

        rc, out = run(rel)
        R['targeted_run_reports_no_staleness'] = ('STALE EXEMPTIONS' not in out)

        r_full = subprocess.run([sys.executable, TOOL], cwd=REPO,
                                capture_output=True, text=True)
        R['full_run_still_reports_a_dead_exemption'] = (
            'STALE EXEMPTIONS' in (r_full.stdout or '')
            and 'zzDefinitelyNotAFinding' in (r_full.stdout or ''))
    finally:
        with open(EX, 'w', encoding='utf-8') as fh:
            fh.write(original)
finally:
    os.remove(target)

for k, v in R.items():
    print('%-34s %s' % (k, v))
print()
ok = all(R.values())
print('LIVE MODE VERIFIED:', ok)
sys.exit(0 if ok else 1)
