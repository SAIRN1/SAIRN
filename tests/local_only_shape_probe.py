"""Probe the two shapes tools/local_only_collection_check.py learned 2026-09-10.

WHY. Three live apps sat permanently in the checker's
"WROTE STORAGE, RESOLVED NO COLLECTIONS -- could not read these, NOT a pass"
bucket: sairncash, sairncode and sairnroofing. All three call
localStorage.setItem directly instead of through a named wrapper, so
find_setter() came back empty and NOTHING was ever classified. A standing
unknown on a medical-coding product holding claims, denials, providers and A/R.

TWO SHAPES, AND THE SECOND WAS FOUND BY THE FIRST.

  1. BARE setItem. The same listish-variable heuristic the wrapper loop already
     used, applied to `localStorage.setItem('k', JSON.stringify(list))`, which
     is what those three apps actually write. sairncode goes from 0 resolved
     collections to 27.

  2. `\\w*Data(` WAS TOO NARROW, and widening (1) is what exposed it. With
     collections finally visible, stonedesk-hr.html was reported as 2 of 2 kept
     on the device -- FALSE. It sends both to the server through
     hrCall('write', 'sd_hr_employees', ...), a wrapper that does not end in
     `Data`, so neither name was harvested. Its localStorage write is an
     explicit CACHE, commented as one, sitting beside a real server write.
     The platform convention is ACTION-FIRST -- f('write'|'read', '<lit>', ...)
     -- so that is what is matched now, widening which FUNCTION counts rather
     than what a server call looks like.

SIX ARMS. Arms 3 and 4 are the negative controls, and each proves the TRAP
before proving the fix: a fixture that passes under the old and new logic alike
tests nothing.

Run: python tests/local_only_shape_probe.py
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import local_only_collection_check as L  # noqa: E402

TOOL = os.path.join(REPO, 'tools', 'local_only_collection_check.py')
results = {}


def run():
    p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True, cwd=REPO)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def row(out, app):
    """(colls, covered, local_only, cannot_tell, unclassified) for one app.

    READ OFF THE END, NOT BY COLUMN INDEX. The setter column holds the literal
    `(bare setItem)` for exactly the three apps this probe is about, and it
    contains a space -- so a positional split shifts every number by one and
    the arms that matter fail while the rest pass. Which is what happened on
    the first run of this probe.
    """
    for ln in out.splitlines():
        if ln.startswith(app + ' '):
            nums = [t for t in ln.split() if t.isdigit()]
            return tuple(nums[-5:]) if len(nums) >= 5 else ()
    return ()


code, out = run()

# ── ARM 1: the three apps that could not be read now are ────────────────────
# sairncode is the one that matters: 27 collections resolved, all covered.
sc = row(out, 'sairncode.html')
results['arm1_sairncode_resolved'] = len(sc) == 5 and sc[0] == '27'
results['arm1_sairncode_all_covered'] = len(sc) == 5 and sc[0] == sc[1] and sc[2] == '0'
# sairnroofing and sairncash keep NOTHING locally, and that is now a measured
# zero rather than an unknown -- 5 and 4 storage writes respectively, every one
# licence, session or subscription state.
for app in ('sairnroofing.html', 'sairncash.html'):
    r = row(out, app)
    results['arm1_%s_zero_collections' % app.split('.')[0]] = len(r) == 5 and r[0] == '0'

# ── ARM 2: the false accusation on a companion page is gone ─────────────────
hr = row(out, 'stonedesk-hr.html')
results['arm2_hr_covered_not_local_only'] = hr[:3] == ('2', '2', '0')

# ── ARM 3 (CONTROL): a non-list write is STILL not a collection ─────────────
# The widening must not turn every bare setItem into a record collection.
FIXTURE_SCALAR = """
localStorage.setItem('zz_token', JSON.stringify(token));
localStorage.setItem('zz_flag', JSON.stringify(enabled));
"""
FIXTURE_LIST = """
localStorage.setItem('zz_widgets', JSON.stringify(list));
"""
scalar_keys, _ = L.collection_keys(FIXTURE_SCALAR, [])
list_keys, _ = L.collection_keys(FIXTURE_LIST, [])
results['arm3_scalar_not_a_collection'] = not set(scalar_keys)
results['arm3_list_is_a_collection'] = 'zz_widgets' in list_keys

# ── ARM 4 (CONTROL): the widened harvest still needs a REAL call ────────────
# It must match a server call, not merely the resource name appearing anywhere.
OLD_WRITE_RE = re.compile(r"\w*Data\(\s*'write'\s*,\s*'(\w+)'")
CALL = "hrCall('write', 'zz_res', rec);"
MENTION = "var label = 'zz_res'; // just a string, no call"
results['arm4_trap_is_real'] = not OLD_WRITE_RE.findall(CALL)      # the old regex missed it
results['arm4_real_call_is_seen'] = L.WRITE_LIT_RE.findall(CALL) == ['zz_res']
results['arm4_bare_mention_is_not'] = not L.WRITE_LIT_RE.findall(MENTION)

# ── ARM 5: every other app is untouched ────────────────────────────────────
# Measured immediately before and after the change; identical. Anchors the fix
# to the files whose shape it was about.
# RE-MEASURED 2026-09-10, TWICE, and both moves were real work rather than
# drift -- so the numbers are restated with what changed rather than relaxed:
#   sairndental 22/18/4 -> 22/22/0   the four vendor collections were backed up
#   sairnbiz    11/10/1 -> 11/11/0   sb_incidents gained a real writer (Hank)
#   sairnlaw    20/19/1 -> 20/19/0   law_billingcodes is now DECLARED not-synced
#   sairnbuild  34/34/0 -> 34/31/0   three keys stopped being falsely cleared
#                                    and are now declared
#   sairnvet    42/42/0 -> 42/41/0   sv_examrooms_turnover likewise
#   stonedesk   37/34/3 -> 37/30/0   six declared; the three that were already
#                                    reported are among them
# The local-only column is now 0 everywhere except SAIRNmechanical, which is
# the one app with genuinely undeclared local collections.
BASELINE = {
    'sairnbiz.html': ('11', '11', '0'), 'sairnbuild.html': ('34', '31', '0'),
    'sairncare.html': ('6', '6', '0'), 'sairndental.html': ('22', '22', '0'),
    'sairndesign.html': ('18', '18', '0'), 'sairnfreedom.html': ('35', '35', '0'),
    'sairngrounds.html': ('30', '30', '0'), 'sairnlaw.html': ('20', '19', '0'),
    'sairnlegacy.html': ('36', '36', '0'), 'sairnmechanical.html': ('5', '0', '5'),
    'sairnscape.html': ('12', '12', '0'), 'sairnsenior.html': ('14', '14', '0'),
    'sairnvet.html': ('42', '41', '0'), 'stonedesk.html': ('37', '30', '0'),
}
drift = []
for app, want in sorted(BASELINE.items()):
    got = row(out, app)
    if got[:3] != want:
        drift.append('%s want %s got %s' % (app, want, got[:3]))
results['arm5_other_apps_unchanged'] = not drift
if drift:
    results['arm5_drift'] = '; '.join(drift)

# ── ARM 6: the genuinely local-only findings survive ───────────────────────
# A resolver can always be "fixed" by making everything look covered.
# THE KEYS CHECKED HERE MOVED, and saying which is the point. sb_incidents,
# law_billingcodes, dnt_supplies_list and sd_market_history have all since been
# BACKED UP or DECLARED -- so asserting they still appear as findings would be
# asserting that real work did not happen. SAIRNmechanical's five are the ones
# that remain genuinely local and declared by nobody, and they are what this arm
# guards: a resolver can always be "fixed" by making everything look covered.
for key in ('sairnmechanical_quotes', 'sairnmechanical_takeoffs',
            'sairnmechanical_checks', 'sairnmechanical_docs',
            'sairnmechanical_memory'):
    results['arm6_still_reports_%s' % key] = key in out
# ...and the ones that moved are accounted for rather than dropped: each is now
# either covered or declared, never silently absent.
for key in ('sb_incidents', 'dnt_supplies_list'):
    results['arm6_%s_no_longer_a_finding' % key] = (
        key not in out.split('KEPT ON THE DEVICE AND SENT NOWHERE ===')[1]
        .split('=== DECLARED')[0])
for key in ('law_billingcodes', 'sd_market_history'):
    results['arm6_%s_is_declared' % key] = (
        key in out.split('=== DECLARED NOT SYNCED')[1].split('=== COULD NOT TELL')[0])

print('--- results ---')
bad = 0
for k in sorted(results):
    v = results[k]
    print('  %-38s %s' % (k, v))
    if isinstance(v, bool) and not v:
        bad += 1

print('')
print('%d ARM(S) FAILED' % bad if bad else 'ALL ARMS PASS')
sys.exit(1 if bad else 0)
