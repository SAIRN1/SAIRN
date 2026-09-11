"""Probe the WRITE-SET resolver, after its first run against the real codebase.

`tools/write_without_readback_check.py` was written 2026-09-05, proved on a
fixture and on one historical commit, committed, and then run by NOBODY --
one of the 28 unwired checkers in docs/2026-09-09-tooling-inventory.md. The
first run against the whole codebase reported FIFTY "written to the server and
never read back" findings on stonedesk.html, the largest app on the platform.

ALL FIFTY WERE FALSE, against the resolver's own docstring promise that it
"can only ever produce a COULD NOT TELL or a false clean on the READ side --
never a false accusation." Two independent defects, and they masked each other:

  SHAPE B took a 4,000-CHARACTER SLICE instead of a function body. With
  comments stripped, `function st(key,data)` sits 1,708 characters from its
  NEIGHBOUR `sdSyncCollection(key,...)`, which really does contain
  `sdData('write',key,r)`. Both parameters are named `key`, so st() was
  accepted as a generic writer and all 68 of its `st('literal',...)` call sites
  -- every localStorage write in the app -- became "server writes". stRaw() was
  swallowed the same way at 1,257 characters, and stRaw() is
  `localStorage.setItem` and nothing else: it has no server path at all.

  SHAPE A required a NEGATIVE gate (`!MAP[`). StoneDesk gates positively --
  `var synced = ... && SD_SYNCED_ON[key];` -- so SD_SYNCED, the app's real
  21-name server-write set, was skipped, and two of those names appear nowhere
  else in the file.

The first defect invented 50 writes; the second hid 21 real ones. The totals
looked plausible the whole time, which is why only pointing the tool at real
code could find it.

SIX ARMS. Arms 3 and 4 are the negative controls, and each one first proves the
TRAP still exists before proving the fix avoids it -- a fixture that passes
under both the old and new logic tests nothing.

Run: python tests/write_readback_shape_probe.py
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import write_without_readback_check as W  # noqa: E402

# ── RUN THIS, DO NOT IMPORT IT (2026-09-11) ────────────────────────────────
# This probe MUTATES A TRACKED SOURCE FILE in place and restores it at the end.
# It has no `if __name__ == "__main__"` guard, so an import runs the whole
# thing -- and an import that is interrupted leaves the mutation on disk.
#
# THAT IS NOT HYPOTHETICAL. On 2026-09-11 a read-only checker walked
# tests/**/*_probe.py and imported each one to read its MUTATIONS list. It hung,
# was killed mid-probe, and left api/_lib/dental-guardian.js modified with an
# injected `if (r.zz_probe_field) return "probe";`. Found by `git status`,
# restored by hand, and the checker rewritten to PARSE rather than import.
#
# The cheap half of the fix is this: refuse the import loudly instead of
# mutating a live file silently. Three lines, no restructuring, and it turns the
# dangerous failure into an obvious one.
if __name__ != '__main__':
    raise RuntimeError(
        __file__ + ' mutates a tracked source file in place. Run it as a script; '
        'do not import it. To read its structure, parse it with ast -- see '
        'tools/mutation_anchor_check.py.')



TOOL = os.path.join(REPO, 'tools', 'write_without_readback_check.py')
results = {}


def run(*paths):
    p = subprocess.run([sys.executable, TOOL] + list(paths),
                       capture_output=True, text=True, cwd=REPO)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def row(out, app):
    for ln in out.splitlines():
        if ln.startswith(app + ' ') or ln.startswith(app + '\t'):
            return ln.split()
    return []


def old_shape_b(src):
    """The 4,000-character-window resolver, kept so the control can prove the
    trap is real rather than assuming it."""
    resolved = set()
    for fm in re.finditer(r'\b(?:async\s+)?function\s+(\w+)\s*\(\s*(\w+)\s*,', src):
        fn, param = fm.group(1), fm.group(2)
        tail = src[fm.end():fm.end() + 4000]
        if not re.search(r"\w*Data\(\s*'write'\s*,\s*" + re.escape(param) + r'\s*,', tail):
            continue
        for cm in re.finditer(r'(?<![\w$.])' + re.escape(fn) + r"\(\s*'(\w+)'\s*,", src):
            resolved.add(cm.group(1))
    return resolved


# ── ARM 1: the historical defect is STILL caught ─────────────────────────────
# Narrowing a resolver can always be "fixed" by making it see nothing. The
# commit before sairnlaw.html's hydrate landed is the case this tool was built
# on; it must still name all nineteen.
tmp = os.path.join(os.environ.get('TEMP', '/tmp'), 'wr_shape_probe')
os.makedirs(tmp, exist_ok=True)
law = os.path.join(tmp, 'sairnlaw.html')
blob = subprocess.run(['git', '-C', REPO, 'show', '3d869e1c~1:sairnlaw.html'],
                      capture_output=True)
results['arm1_fixture_read'] = blob.returncode == 0 and len(blob.stdout) > 100000
io.open(law, 'wb').write(blob.stdout)
c1, o1 = run(law)
results['arm1_historical_still_red'] = c1 == 1
results['arm1_all_19_named'] = len([l for l in o1.splitlines()
                                    if l.strip().startswith('law_')]) == 19

# ── ARM 2: stonedesk.html, the file that exposed both defects ────────────────
c2, o2 = run()
sd = row(o2, 'stonedesk.html')
results['arm2_writes_33_not_81'] = len(sd) >= 3 and sd[1] == '33'
results['arm2_reads_match_writes'] = len(sd) >= 3 and sd[1] == sd[2]
results['arm2_no_findings_at_all'] = c2 == 0 and 'WRITTEN AND NEVER READ BACK' in o2 \
    and o2.split('WRITTEN AND NEVER READ BACK ===')[1].strip().startswith('none')

src_sd = W.strip_comments(io.open(os.path.join(REPO, 'stonedesk.html'),
                                  encoding='utf-8', errors='replace').read())
resolved_sd = W.resolve_generic_writes(src_sd)
# stRaw() touches no server. Its six call-site literals must not be write names.
STRAW = {'quoteCounter', 'sairn_privacy_accepted', 'sd_demo_cleared',
         'sd_exec_role', 'stonedesk_license_key', 'stonedesk_net_intel_ts'}
results['arm2_straw_literals_gone'] = not (STRAW & resolved_sd)
# ...and the Shape-A half: SD_SYNCED is now resolved, including the two names
# that appear nowhere else, so the fix did not simply delete the write set.
results['arm2_sd_synced_resolved'] = {'sd_email_threats', 'sd_templates'} <= resolved_sd

# ── ARM 3 (CONTROL): a neighbouring function must not leak ───────────────────
# `outer` writes only to localStorage. `inner`, defined right after it, writes
# to a server through a parameter of the SAME NAME. Under a fixed window the
# slice runs from outer's parameter list into inner's body and outer's call
# sites are stolen; under a brace-matched body they are not.
FIXTURE_B = """
function outer(key, value) {
  localStorage.setItem(key, value);
  return true;
}
function inner(key, rec) {
  return xData('write', key, rec);
}
outer('zz_local_only', 1);
inner('zz_real_resource', 2);
"""
leak = old_shape_b(FIXTURE_B)
results['arm3_trap_is_real'] = 'zz_local_only' in leak          # the control bites
fixed = W.resolve_generic_writes(FIXTURE_B)
results['arm3_neighbour_not_stolen'] = 'zz_local_only' not in fixed
results['arm3_real_writer_still_seen'] = 'zz_real_resource' in fixed

# ── ARM 4 (CONTROL): a map nothing consults is still not a write set ─────────
# Widening Shape A from `!MAP[` to "the map is read at all" must not widen it
# to "the map exists". The first fixture builds a map and never looks at it.
FIXTURE_A_DEAD = """
var ZZ_LIST = ['zz_a', 'zz_b'];
var ZZ_ON = {};
ZZ_LIST.forEach(function(k){ ZZ_ON[k] = true; });
"""
FIXTURE_A_POS = FIXTURE_A_DEAD + """
function zzSt(key, data) {
  var synced = ZZ_ON[key];
  if (synced) { zzSyncOne(key, data); }
}
"""
FIXTURE_A_NEG = FIXTURE_A_DEAD + """
function zzSt(key, data) {
  if (!ZZ_ON[key]) { return; }
  zzSyncOne(key, data);
}
"""
results['arm4_dead_map_skipped'] = not (W.resolve_generic_writes(FIXTURE_A_DEAD)
                                        & {'zz_a', 'zz_b'})
results['arm4_positive_gate_resolved'] = {'zz_a', 'zz_b'} <= W.resolve_generic_writes(FIXTURE_A_POS)
results['arm4_negative_gate_still_works'] = {'zz_a', 'zz_b'} <= W.resolve_generic_writes(FIXTURE_A_NEG)

# ── ARM 5: every other app is untouched ──────────────────────────────────────
# Measured before and after the change; identical. Anchors the fix to the one
# file whose shape it was about.
# RE-MEASURED 2026-09-10. Two apps moved and BOTH moves are real work, so the
# numbers are restated with what changed rather than the arm being loosened:
#   sairnbiz    9 -> 10   sb_incidents gained a real writer (Hank's OSHA log)
#   sairndental 16 -> 20  the four vendor/supply resources were registered
# Every app is still N writes / N read back, which is what this arm is for.
BASELINE = {
    'sairnbiz.html': ('10', '10'), 'sairnbuild.html': ('32', '32'),
    'sairncare.html': ('9', '9'), 'sairncode.html': ('28', '28'),
    'sairndental.html': ('20', '20'), 'sairndesign.html': ('18', '18'),
    'sairngrounds.html': ('30', '30'), 'sairnlaw.html': ('19', '19'),
    'sairnlegacy.html': ('36', '36'), 'sairnmechanical.html': ('2', '2'),
    'sairnscape.html': ('12', '12'), 'sairnsenior.html': ('15', '15'),
}
drift = []
for app, (w, r) in sorted(BASELINE.items()):
    got = row(o2, app)
    if len(got) < 3 or (got[1], got[2]) != (w, r):
        drift.append('%s want %s/%s got %s' % (app, w, r, got[1:3] if len(got) > 2 else got))
results['arm5_other_apps_unchanged'] = not drift
if drift:
    results['arm5_drift'] = '; '.join(drift)

# ── ARM 6: a real planted defect on the real file is still caught ────────────
# Arm 2 says stonedesk.html is clean. A clean result from a tool that has just
# been narrowed needs a live control on the SAME file, not only on a fixture.
SD = os.path.join(REPO, 'stonedesk.html')
orig = io.open(SD, 'rb').read()
try:
    anchor = b"function sdData("
    # EXACTLY ONCE, NOT MERELY PRESENT (2026-09-10) -- see the note on
    # anchor_once() in tests/push_gate/check7_probe.py. `in` catches an anchor
    # that has GONE and misses one that has become AMBIGUOUS; .replace(..., 1)
    # would then plant the fixture in whichever came first, in a 2MB file where
    # nobody would notice which. An anchor is a string match against code
    # somebody else keeps editing, so going ambiguous is how it ages.
    _n = orig.count(anchor)
    assert _n == 1, ('probe fixture invalid -- the sdData() anchor matches %d places '
                     'in stonedesk.html, not 1; widen it rather than letting the '
                     'probe pick' % _n)
    io.open(SD, 'wb').write(orig.replace(
        anchor, b"function zzProbeWrite(r){return sdData('write','zz_probe_res',r);}\n"
                b"zzProbeWrite(1);\nsdData('write','zz_probe_res2',{});\n" + anchor, 1))
    c6, o6 = run()
    results['arm6_planted_write_is_caught'] = c6 == 1 and 'zz_probe_res2' in o6
finally:
    io.open(SD, 'wb').write(orig)
results['arm6_source_restored'] = io.open(SD, 'rb').read() == orig

print('--- results ---')
bad = 0
for k in sorted(results):
    v = results[k]
    print('  %-32s %s' % (k, v))
    if isinstance(v, bool) and not v:
        bad += 1

print('')
print('%d ARM(S) FAILED' % bad if bad else 'ALL ARMS PASS')
sys.exit(1 if bad else 0)
