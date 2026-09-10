"""Probe the false CLEAN in local_only_collection_check.py's sibling-sync route,
and the declaration that keeps the corrected output readable.

THE BUG. The route excuses a local write when a server call NEARBY is made with
the SAME VARIABLE -- `st('sb_emps', emps)` beside `syncEmps(emps)`. Its own
header says a route that over-covers produces a FALSE CLEAN, "the one direction
this must not fail in". It was failing in that direction.

TWO CAUSES, ONE VISIBLE ONLY AFTER THE OTHER:

  1. st() JOINED THE SERVER-CALLING SET. SAIRNvet, SAIRNfreedom and StoneDesk
     now push from inside their storage setter, so the one-hop rule put st()
     itself in `reaches` -- and then every `st('key', list)` line matched as
     "a server-calling function called with the same variable". The LOCAL WRITE
     was matching as its own server call.

  2. A ONE-LINE WRAPPER CLEARED ITSELF ON ITS OWN SIGNATURE, which is the
     deeper half and is independent of any hook. _body() includes the
     declaration line, so for

         function saveExamRoomTurnoverLog(list){ return st('sv_...', list); }

     the window contains `saveExamRoomTurnoverLog(list)` -- the PARAMETER LIST
     -- and the shares test matched the function's own header. Any wrapper in
     `reaches` excused every key it wrote, by existing.

WHAT THE FIX SURFACED, AND WHY A SECOND CHANGE WAS NEEDED. Correcting it turned
up nine keys at once across four apps -- and every one is a decision already
written down in prose in the app's registry ("bld_ai_chat -- an unbounded
conversation transcript, not a business record"). Prose is not machine-readable,
so the checker could not tell a decision from an oversight and reported both as
findings. A checker that lists nine deliberate choices is one people stop
reading, which is how the tenth -- a real one -- gets missed. The decisions are
now a `notSynced` declaration the tool reads, reported in their own section.

SEVEN ARMS. Arms 3 and 4 are the controls: the trap is reproduced against the
OLD logic before the fix is asserted, and a declaration must not be able to
launder a key that really is covered by nothing and declared by nobody.

Run: python tests/local_only_self_evidence_probe.py
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


code, out = run()

# ── ARM 1: the key that started it is no longer falsely cleared ─────────────
# sv_examrooms_turnover is excluded from SV_SYNCED, pushed by nothing, and a
# live 400 from the deployed allowlist proves it is not backed up.
results['arm1_not_in_covered_section'] = (
    'same data as a server call in saveExamRoomTurnoverLog()' not in out)
results['arm1_reported_as_declared'] = re.search(
    r'sairnvet\.html -- \d+ declared:[^\n]*sv_examrooms_turnover', out) is not None

# ── ARM 2: a real finding still survives -- ON A FIXTURE ───────────────────
# A resolver can always be "fixed" into silence, so this arm has to prove one
# still gets through. It named SAIRNmechanical's five until 2026-09-10, when
# they were backed up and the platform reached ZERO local-only findings. A
# control pinned to a live defect dies with the defect; this one cannot.
FIXTURE_LOCAL = """
function st(k,v){localStorage.setItem(k,JSON.stringify(v));return true;}
function saveZzRecords(list){ return st('zz_records', list); }
"""
_k, _u = L.collection_keys(FIXTURE_LOCAL, ['st'])
_c, _s2 = L.covered_keys(FIXTURE_LOCAL, set(_k), set(), ['st'])
results['arm2_a_local_collection_is_seen'] = 'zz_records' in _k
results['arm2_and_is_not_cleared'] = 'zz_records' not in _c
# The live run's own exit code still has to be non-zero for a real reason --
# stonedesk's sd_intake could-not-tell -- rather than because nothing ran.
results['arm2_exit_nonzero'] = code != 0
results['arm2_reason_is_a_could_not_tell'] = 'sd_intake' in out

# ── ARM 3 (CONTROL): reproduce the self-signature trap, then refute it ─────
# The fixture is the exact shape: a one-line wrapper whose parameter list looks
# like a call, inside an app whose setter reaches a server.
FIXTURE = """
function zzData(action, resource, payload){ return fetch('/api/x'); }
function st(key, data){
  localStorage.setItem(key, JSON.stringify(data));
  zzSync(key, data);
  return true;
}
function zzSync(key, rows){ return zzData('write', key, rows); }
function saveZzThing(list){
  return st('zz_things', list);
}
"""
_reaches, _bodies = L._server_calling_functions(FIXTURE)
results['arm3_trap_is_real_setter_reaches'] = 'st' in _reaches
results['arm3_trap_is_real_wrapper_reaches'] = 'saveZzThing' in _reaches
# The old logic would have matched `saveZzThing(list)` -- its own header -- and
# `st('zz_things', list)`. Asserted explicitly so the control cannot rot into a
# fixture that passes either way.
_body = _bodies['saveZzThing']
results['arm3_own_signature_is_in_the_body'] = 'saveZzThing(list)' in _body
_covered, _unsure = L.covered_keys(FIXTURE, {'zz_things'}, set(), ['st'])
results['arm3_no_longer_self_cleared'] = 'zz_things' not in _covered

# ── ARM 4 (CONTROL): a genuine sibling sync must STILL be cleared ──────────
# The fix must not be a blanket silencing of the route. Here a real, separate
# server-calling function is invoked with the same variable.
FIXTURE_OK = FIXTURE.replace(
    "function saveZzThing(list){\n  return st('zz_things', list);\n}",
    "function saveZzThing(list){\n  st('zz_things', list);\n  zzSync('zz_things', list);\n}")
_cov2, _uns2 = L.covered_keys(FIXTURE_OK, {'zz_things'}, set(), ['st'])
results['arm4_real_sibling_sync_still_covered'] = 'zz_things' in _cov2

# ── ARM 5: the declaration is read, and only from the resources registry ──
declared_vet = L.declared_not_synced(os.path.join(REPO, 'sairnvet.html'))
results['arm5_declaration_is_read'] = 'sv_examrooms_turnover' in declared_vet
# An app with no declaration gets an empty set -- absent means UNDECIDED.
results['arm5_absent_declaration_is_empty'] = L.declared_not_synced(
    os.path.join(REPO, 'sairnscape.html')) == set()

# ── ARM 6 (CONTROL): a declaration cannot launder an undeclared key ────────
# SAIRNmechanical has no registry declaration, so its five must stay findings
# no matter what any other app declares.
# CORRECTED 2026-09-10: SAIRNmechanical's four are now BACKED UP and its fifth
# is DECLARED, so "still in findings" would assert that real work did not
# happen. What this arm is actually for -- a declaration must not launder a key
# nothing covers -- is proven directly instead, on a key no registry mentions.
results['arm6_undeclared_key_is_not_laundered'] = 'zz_records' not in L.declared_not_synced(
    os.path.join(REPO, 'sairnmechanical.html'))
results['arm6_declaration_is_narrow'] = L.declared_not_synced(
    os.path.join(REPO, 'sairnmechanical.html')) == {
        'sairnmechanical_memory', 'sairnmechanical_crnum', 'sairnmechanical_pricing'}

# ── ARM 7: every app's covered count is unchanged except the four fixed ────
# Measured immediately before and after. Only the apps whose setter pushes --
# and StoneDesk's and SAIRNbuild's self-clearing wrappers -- move.
BASELINE = {
    'sairnbiz.html': '11', 'sairncare.html': '6', 'sairncode.html': '27',
    'sairndental.html': '22', 'sairndesign.html': '18', 'sairnfreedom.html': '35',
    'sairngrounds.html': '30', 'sairnlegacy.html': '36', 'sairnmechanical.html': '4',
    'sairnscape.html': '12', 'sairnsenior.html': '14', 'stonedesk-hr.html': '2',
}
drift = []
for app, want in sorted(BASELINE.items()):
    for ln in out.splitlines():
        if ln.startswith(app + ' '):
            nums = [t for t in ln.split() if t.isdigit()]
            if len(nums) < 5 or nums[-4] != want:
                drift.append('%s want covered=%s got %s' % (app, want, nums[-5:] if nums else ln))
            break
results['arm7_untouched_apps_unchanged'] = not drift
if drift:
    results['arm7_drift'] = '; '.join(drift)

print('--- results ---')
bad = 0
for k in sorted(results):
    v = results[k]
    print('  %-44s %s' % (k, v))
    if isinstance(v, bool) and not v:
        bad += 1

print('')
print('%d ARM(S) FAILED' % bad if bad else 'ALL ARMS PASS')
sys.exit(1 if bad else 0)
