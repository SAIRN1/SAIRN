"""Probe tools/write_without_readback_check.py against real history.

A checker that has only ever returned clean is a checker whose behaviour nobody
knows. This drives it against the two commits that motivated it and against
synthetic files for each shape it claims to resolve.

THE LOAD-BEARING ARM IS THE HISTORICAL ONE. sairnlaw.html at 3d869e1c^ is the
real file, as it really was, writing nineteen resources and reading none of
them back. If the checker does not go red on that, it would not have caught the
defect it exists for.

THE SECOND HISTORICAL ARM IS THE HONEST ONE. sairnbiz.html at 48c122df^ is the
other case this tool's header cites -- and the checker says NOTHING about it,
correctly by its own rules and uselessly in practice, because SAIRNbiz was not
writing to a server at all. That arm is asserted so the limitation stays true
and visible rather than being quietly forgotten.
"""
import os
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(ROOT, 'tools', 'write_without_readback_check.py')

FAIL = []


def check(name, got, want):
    if got == want:
        print('  ok   ' + name)
    else:
        print('  FAIL ' + name + '\n         got:  ' + repr(got) + '\n         want: ' + repr(want))
        FAIL.append(name)


def run(paths):
    p = subprocess.run([sys.executable, TOOL] + paths, capture_output=True, text=True, cwd=ROOT)
    return p.returncode, p.stdout


def at(commit, path, dest):
    p = subprocess.run(['git', 'show', commit + ':' + path], capture_output=True, cwd=ROOT)
    if p.returncode != 0:
        return None
    with open(dest, 'wb') as f:
        f.write(p.stdout)
    return dest


def write(dest, body):
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(body)
    return dest


def main():
    tmp = tempfile.mkdtemp(prefix='wrb_probe_')
    print('write_without_readback_check probe')

    # ── history ─────────────────────────────────────────────────────────────
    print('--- against the commits that motivated it ---')
    law = at('3d869e1c^', 'sairnlaw.html', os.path.join(tmp, 'sairnlaw.html'))
    if not law:
        print('  SKIP the pre-fix SAIRNlaw commit is not in this clone')
    else:
        rc, out = run([law])
        check('pre-fix SAIRNlaw exits non-zero', rc != 0, True)
        check('...and names law_trusttx among the unread', 'law_trusttx' in out, True)
        check('...and law_timeentries', 'law_timeentries' in out, True)
        n = out.count('\n      law_')
        check('...nineteen resources named, not a sample', n >= 19, True)

    rc, out = run([os.path.join(ROOT, 'sairnlaw.html')])
    check('the CURRENT SAIRNlaw is clean -- the fix is what changed the answer', rc, 0)

    biz = at('48c122df^', 'sairnbiz.html', os.path.join(tmp, 'sairnbiz.html'))
    if not biz:
        print('  SKIP the pre-fix SAIRNbiz commit is not in this clone')
    else:
        rc, out = run([biz])
        # ASSERTED AS A LIMITATION, NOT AS A PASS. SAIRNbiz was writing to
        # localStorage and stopping, so there is no server write for this to
        # see. Keeping the arm means the header's claim stays honest.
        check('pre-fix SAIRNbiz is SILENT -- a different defect this cannot see', rc, 0)
        check('...and it reports no writes for that file at all', 'sairnbiz' not in out, True)

    # ── the shapes it claims to resolve ─────────────────────────────────────
    print('--- the loop shapes ---')
    flat = write(os.path.join(tmp, 'flat.html'), """
      var X_SYNC=['ap_one','ap_two','ap_three'];
      function go(){ X_SYNC.map(function(k){ return apData('read',k); }); }
      function w(){ apData('write','ap_one',{}); apData('write','ap_two',{}); apData('write','ap_three',{}); }
    """)
    rc, out = run([flat])
    check('a flat array of names counts as reading all of them', rc, 0)

    pairs = write(os.path.join(tmp, 'pairs.html'), """
      var X_SYNC=[['ap_one','ap_one_list'],['ap_two','ap_two_list']];
      function go(){ for(var i=0;i<X_SYNC.length;i++){ apData('read',X_SYNC[i][0]); } }
      function w(){ apData('write','ap_one',{}); apData('write','ap_two',{}); }
    """)
    rc, out = run([pairs])
    check('an array of PAIRS resolves on the first element', rc, 0)

    lower = write(os.path.join(tmp, 'lower.html'), """
      function go(){ var resources=[['ap_one','k1'],['ap_two','k2']];
        for(var i=0;i<resources.length;i++){ apData('read',resources[i][0]); } }
      function w(){ apData('write','ap_one',{}); apData('write','ap_two',{}); }
    """)
    rc, out = run([lower])
    check('a lowercase LOCAL list resolves -- the SAIRNgrounds false positive', rc, 0)

    obj = write(os.path.join(tmp, 'obj.html'), """
      var KEYS={ap_one:'k1',ap_two:'k2'};
      function go(){ var resources=Object.keys(KEYS); resources.map(function(r){ return apData('read',r); }); }
      function w(){ apData('write','ap_one',{}); apData('write','ap_two',{}); }
    """)
    rc, out = run([obj])
    check('Object.keys(<object literal>) resolves', rc, 0)

    # ── the object-literal call shape ───────────────────────────────────────
    print('--- the object-literal call shape ---')
    obj_call = write(os.path.join(tmp, 'objcall.html'), """
      function go(){ apPostRaw({action:'read',resource:'ap_one',app_id:'x',payload:{}});
                     apPostRaw({action:'read',resource:'ap_two',app_id:'x',payload:{}}); }
      function w(){ apData('write','ap_one',{}); apData('write','ap_two',{}); }
    """)
    rc, out = run([obj_call])
    check('a read posted as an object literal counts -- the SAIRNcare false positive', rc, 0)

    obj_write = write(os.path.join(tmp, 'objwrite.html'), """
      function w(){ apPostRaw({action:'write',resource:'ap_solo',app_id:'x',payload:{}}); }
    """)
    rc, out = run([obj_write])
    check('a WRITE posted as an object literal is seen too', rc != 0, True)
    check('...and named', 'ap_solo' in out, True)

    care = os.path.join(ROOT, 'sairncare.html')
    if os.path.exists(care):
        rc, out = run([care])
        # The real file that produced the false positive. alf_op_audits and
        # alf_staff_credentials are read through alfPostRaw({action:'read'...}).
        check('the REAL SAIRNcare file is clean', rc, 0)
        check('...and neither previously-flagged name is reported',
              'alf_op_audits' not in out and 'alf_staff_credentials' not in out, True)

    # ── the cases it must still catch ───────────────────────────────────────
    print('--- what it must still catch ---')
    gap = write(os.path.join(tmp, 'gap.html'), """
      var X_SYNC=['ap_one','ap_two'];
      function go(){ X_SYNC.map(function(k){ return apData('read',k); }); }
      function w(){ apData('write','ap_one',{}); apData('write','ap_two',{}); apData('write','ap_three',{}); }
    """)
    rc, out = run([gap])
    check('a resource left OUT of the sync list is caught', rc != 0, True)
    check('...and named', 'ap_three' in out, True)

    none = write(os.path.join(tmp, 'none.html'), """
      function w(){ apData('write','ap_one',{}); apData('write','ap_two',{}); }
    """)
    rc, out = run([none])
    check('writes with no read at all are caught', rc != 0, True)

    unsure = write(os.path.join(tmp, 'unsure.html'), """
      function go(){ apData('read', somethingUnresolvable); }
      function w(){ apData('write','ap_one',{}); apData('write','ap_two',{}); }
    """)
    rc, out = run([unsure])
    check('an UNRESOLVABLE read loop is could-not-tell, not a pass', rc != 0, True)
    check('...and says so under its own heading', 'COULD NOT TELL' in out, True)

    plat = write(os.path.join(tmp, 'plat.html'), """
      function w(){ apData('write','shared_knowledge',{}); }
    """)
    rc, out = run([plat])
    check('a platform resource alone does not make a finding', rc, 0)

    print('\n' + str(len(FAIL)) + ' failure(s)')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
