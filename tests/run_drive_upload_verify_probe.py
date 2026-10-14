#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b7, queue item 2
"""Does `tools/drive_upload_verify.py` actually FAIL on the three shapes it exists for?

    python tests/run_drive_upload_verify_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

THE THREE SHAPES, each a real event rather than an invented edge case:

  WRONG-AGENT  `SAIRN-handoff-cc-b6.md` is on the shared Drive, 2,162 bytes,
               and its first line reads `# cody b6 handoff (filename as
               requested)`. The NAME is perfect. A coordinating session reads
               the name, trusts it, and routes cody's state as cc's. Only a
               content check catches this, so the probe proves the content
               check has teeth and is not decoration beside the name check.
  MISSING      cc's b6 report and digest were never uploaded at all and the
               batch was reported closed. An absent deliverable has to be a
               FINDING ABOUT THE BATCH, not a crash and not a skip.
  TRUNCATED    a half-synced file is in the folder listing, carries the right
               name, and has the right first line. Existence and name both
               pass. Only bytes+sha256 against the local copy can tell.

FAILING-FIRST, AND WHAT THAT MEANS HERE. The tool was written before this
probe, so "write the test first" is not available as a sequence -- and a probe
that merely reports exit 1 on bad input cannot distinguish `the check caught
it` from `something else in the run caught it`. So each of the three shapes
carries an ABLATION arm: the one criterion that is supposed to catch it is
replaced with a pass-everything stub, in process, and the SAME bad input is
driven again. If the bad input still fails with the criterion removed, that arm
was never testing that criterion and the ablation arm FAILS. This is convention
12 (ablation over chaos) applied per-criterion rather than per-exit-code.

EVERY ARM RUNS IN TWO THROWAWAY DIRECTORIES -- a fake Drive folder via
SAIRN_DRIVE_DIR and a fake clone via --from. The real shared Drive is NEVER
written by this probe, and the run prints both paths so a pass cannot be
mistaken for a pass about the real mount.

WHAT THIS PROBE CANNOT SEE, said rather than discovered later:
  * whether Google ACKNOWLEDGED an upload. The subject writes to a sync mount
    and says so every run; a temp directory cannot test the sync half at all.
  * whether the real folder's 194 entries are correct. `--audit` is exercised
    against a hand-built folder here; the real run is in the report.
  * a file that syncs correctly and is later changed on the Drive side. Every
    verdict here is as of the run, like every reachability answer in this repo.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'drive_upload_verify.py')

if not os.path.isfile(TOOL):
    print('COULD NOT RUN: %s is absent, so NOTHING WAS TESTED. That is a third '
          'state and it is not a pass.' % TOOL)
    sys.exit(2)

spec = importlib.util.spec_from_file_location('duv_subject', TOOL)
duv = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.join(REPO, 'tools'))
try:
    spec.loader.exec_module(duv)
except Exception as exc:                                         # noqa: BLE001
    print('COULD NOT RUN: %s would not import (%s).' % (TOOL, exc))
    sys.exit(2)

GOOD = {
    'handoff': '# SAIRN handoff -- cc batch b7 -- 2026-10-13\n\nbody line\n',
    'report': 'REPORT cc b7\n\nbody line\nEND-OF-REPORT\n',
    'digest': 'DIGEST cc b7\nSTATUS: fine\n',
}


def run(drive, frm, *args):
    """-> (exit code, combined output). The subject as a real process."""
    env = dict(os.environ)
    env['SAIRN_DRIVE_DIR'] = drive
    p = subprocess.run([sys.executable, TOOL, '--from', frm] + list(args),
                       cwd=REPO, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def clone(tmp, which=('handoff', 'report', 'digest'), bodies=None):
    """A fake clone holding the named deliverables. -> its path."""
    d = tempfile.mkdtemp(prefix='duv-local-', dir=tmp)
    for kind in which:
        text = (bodies or {}).get(kind, GOOD[kind])
        with open(os.path.join(d, duv.expected_name(kind, 'cc', 'b7')), 'w',
                  newline='') as fh:
            fh.write(text)
    return d


arms = []
tmp = tempfile.mkdtemp(prefix='duv-probe-')
print('drive-upload-verify probe')
print('  fake Drive + fake clone under : %s' % tmp)
print('  subject                       : %s' % TOOL)
print('')

try:
    # ── ARM GROUP 0: the clean case, so a later failure means something ──────
    drive = tempfile.mkdtemp(prefix='duv-drive-', dir=tmp)
    local = clone(tmp)
    rc, out = run(drive, local, '--agent', 'cc', '--batch', 'b7')
    arms.append(('CLEAN: three well-formed deliverables upload and verify',
                 (rc, 'PASS: all three' in out), (0, True)))
    arms.append(('...and all three are really in the fake Drive folder',
                 sorted(n for n in os.listdir(drive) if n.startswith('SAIRN')),
                 ['SAIRN-digest-cc-b7.txt', 'SAIRN-handoff-cc-b7.md',
                  'SAIRN-report-cc-b7.txt']))
    arms.append(('...and the sync-mount limit is PRINTED rather than folded '
                 'into the pass',
                 'does NOT prove Google acknowledged' in out, True))
    arms.append(('...and a run against a temp directory SAYS it is not the '
                 'real Drive',
                 'did NOT touch the real shared Drive' in out, True))

    # ── ARM GROUP 1: WRONG-AGENT ────────────────────────────────────────────
    # cody's content, cc's filename. The b6 defect exactly.
    drive = tempfile.mkdtemp(prefix='duv-drive-', dir=tmp)
    local = clone(tmp, bodies={
        'handoff': '# cody b6 handoff (filename as requested) -- 2026-10-13\n'})
    rc, out = run(drive, local, '--agent', 'cc', '--batch', 'b7')
    arms.append(('WRONG-AGENT: a perfect filename over another agent\'s '
                 'content is a FINDING',
                 (rc, 'does not name cc' in out), (1, True)))
    arms.append(('...and the run refuses to call the batch closed',
                 'Do not mark this batch closed' in out, True))
    arms.append(('...and the finding quotes the offending first line, so the '
                 'reader can tell which half is wrong',
                 'cody b6 handoff' in out, True))

    # ABLATION: remove ONLY the first-line identity criterion and drive the
    # SAME bad input. If it still fails, this arm was not testing that check.
    drive_ab = tempfile.mkdtemp(prefix='duv-abl-', dir=tmp)
    keep = duv.names_agent_and_batch
    try:
        duv.names_agent_and_batch = lambda line, agent, batch: (True, 'stub')
        bad = duv.verify_one('handoff', 'cc', 'b7',
                             os.path.join(local, 'SAIRN-handoff-cc-b7.md'),
                             drive_ab, upload=True, out=[])
    finally:
        duv.names_agent_and_batch = keep
    arms.append(('ABLATION wrong-agent: with the first-line check stubbed to '
                 'pass, the SAME cody-content file is accepted -- so the arm '
                 'above is that check and nothing else',
                 bad, []))

    # ── ARM GROUP 2: MISSING ────────────────────────────────────────────────
    drive = tempfile.mkdtemp(prefix='duv-drive-', dir=tmp)
    local = clone(tmp, which=('handoff', 'report'))     # no digest at all
    rc, out = run(drive, local, '--agent', 'cc', '--batch', 'b7')
    arms.append(('MISSING: an absent digest is a FINDING, not a crash',
                 (rc, 'THE DELIVERABLE DOES NOT EXIST' in out), (1, True)))
    arms.append(('...and it is named as a finding about the BATCH rather than '
                 'about the tool',
                 'not about this tool' in out, True))
    arms.append(('...and the two deliverables that ARE present still verify, '
                 'so one absence does not hide the state of the others',
                 out.count('PASS SAIRN-'), 2))
    arms.append(('...and the absent one was not quietly created',
                 os.path.isfile(os.path.join(drive, 'SAIRN-digest-cc-b7.txt')),
                 False))

    # ABLATION: a tool that treated an unreadable local file as empty-and-fine
    # would pass. Stub the read to return bytes and the finding disappears.
    drive_ab = tempfile.mkdtemp(prefix='duv-abl-', dir=tmp)
    keep = duv.read_bytes
    try:
        duv.read_bytes = lambda path: (GOOD['digest'].encode(), '')
        bad = duv.verify_one('digest', 'cc', 'b7',
                             os.path.join(local, 'SAIRN-digest-cc-b7.txt'),
                             drive_ab, upload=True, out=[])
    finally:
        duv.read_bytes = keep
    arms.append(('ABLATION missing: with the local read stubbed to always '
                 'succeed, the absent digest is accepted -- so the arm above '
                 'is the existence check',
                 bad, []))

    # ── ARM GROUP 3: TRUNCATED ──────────────────────────────────────────────
    # Upload clean, then cut the Drive copy short and re-verify. The name is
    # right, the listing has it, the first line still names cc and b7.
    drive = tempfile.mkdtemp(prefix='duv-drive-', dir=tmp)
    local = clone(tmp)
    rc, out = run(drive, local, '--agent', 'cc', '--batch', 'b7')
    arms.append(('TRUNCATED setup: the clean upload passed first',
                 rc, 0))
    dest = os.path.join(drive, 'SAIRN-report-cc-b7.txt')
    whole = open(dest, 'rb').read()
    with open(dest, 'wb') as fh:
        fh.write(whole[:8])                 # 'REPORT c' -- still starts right
    rc, out = run(drive, local, '--agent', 'cc', '--batch', 'b7',
                  '--verify-only')
    arms.append(('TRUNCATED: a short file with the right name IN the listing '
                 'is a FINDING',
                 (rc, 'bytes on the Drive' in out), (1, True)))
    arms.append(('...and the byte difference is stated as a number',
                 'difference of -%d' % (len(whole) - 8) in out, True))
    arms.append(('...and sha256 is reported too, because a same-length '
                 'corruption would pass a length check',
                 'different content' in out or 'sha256' in out, True))

    # ABLATION: stub the read-back so the Drive copy reads as the local bytes.
    # Length and sha are then equal and the truncation is invisible.
    keep = duv.read_bytes
    real_read = keep
    try:
        duv.read_bytes = lambda path: (
            (GOOD['report'].encode(), '') if os.path.dirname(path) == drive
            else real_read(path))
        bad = duv.verify_one('report', 'cc', 'b7',
                             os.path.join(local, 'SAIRN-report-cc-b7.txt'),
                             drive, upload=False, out=[])
    finally:
        duv.read_bytes = keep
    arms.append(('ABLATION truncated: with the read-back stubbed to return the '
                 'local bytes, the truncated Drive copy is accepted -- so the '
                 'arm above is the bytes+sha256 comparison and not the name',
                 bad, []))
    arms.append(('...and the truncated file is STILL truncated on the fake '
                 'Drive, so --verify-only did not repair what it measured',
                 os.path.getsize(dest), 8))

    # ── ARM GROUP 4: the refusal to overwrite another agent's content ───────
    drive = tempfile.mkdtemp(prefix='duv-drive-', dir=tmp)
    local = clone(tmp)
    foreign = '# cody b6 handoff (filename as requested)\nstate cody owns\n'
    with open(os.path.join(drive, 'SAIRN-handoff-cc-b7.md'), 'w',
              newline='') as fh:
        fh.write(foreign)
    rc, out = run(drive, local, '--agent', 'cc', '--batch', 'b7')
    arms.append(('FOREIGN: uploading over a file whose first line names '
                 'another agent is REFUSED',
                 (rc, 'REFUSED TO UPLOAD' in out), (1, True)))
    arms.append(('...and cody\'s bytes are still there, unmodified',
                 open(os.path.join(drive, 'SAIRN-handoff-cc-b7.md')).read(),
                 foreign))
    arms.append(('...and the refusal names the differently-named-file way out',
                 'different name' in out, True))
    rc, out = run(drive, local, '--agent', 'cc', '--batch', 'b7',
                  '--overwrite-foreign')
    arms.append(('...and --overwrite-foreign WITHOUT --why is COULD NOT RUN, '
                 'not a quiet override',
                 (rc, 'requires --why' in out), (2, True)))
    arms.append(('...and that refusal wrote nothing either',
                 open(os.path.join(drive, 'SAIRN-handoff-cc-b7.md')).read(),
                 foreign))

    # ── ARM GROUP 5: fail CLOSED when the mount is absent (PR 1.11) ─────────
    gone = os.path.join(tmp, 'no-such-mount')
    rc, out = run(gone, local, '--agent', 'cc', '--batch', 'b7')
    arms.append(('ABSENT MOUNT: exit 2 COULD NOT RUN -- never 0, and never 1 '
                 'either, because nothing was checked',
                 (rc, 'COULD NOT RUN' in out), (2, True)))
    arms.append(('...and it says NOTHING WAS UPLOADED in those words',
                 'NOTHING WAS UPLOADED AND NOTHING WAS CHECKED' in out, True))

    # ── ARM GROUP 6: --audit ────────────────────────────────────────────────
    drive = tempfile.mkdtemp(prefix='duv-drive-', dir=tmp)
    for name, text in (
            ('SAIRN-handoff-cc-b7.md', GOOD['handoff']),
            ('SAIRN-handoff-cody-b6.md', '# cc b6 handoff\n'),   # disagrees
            ('SAIRN-digest-h1-b5.txt', 'H1 batch U digest\n'),   # wrong batch
            ('notes.txt', 'outside the audit entirely\n')):
        with open(os.path.join(drive, name), 'w', newline='') as fh:
            fh.write(text)
    rc, out = run(drive, local, '--audit')
    arms.append(('AUDIT: a folder file whose name disagrees with its first '
                 'line is reported',
                 (rc, out.count('DISAGREES')), (1, 2)))
    arms.append(('...and the agreeing file is not reported',
                 'DISAGREES       SAIRN-handoff-cc-b7.md' in out, False))
    arms.append(('...and CHECKED / LISTING are two numbers, so an unchecked '
                 'entry cannot read as a passing one',
                 'CHECKED / LISTING : 3 / 4' in out, True))
    arms.append(('...and nothing was renamed',
                 sorted(os.listdir(drive)),
                 ['SAIRN-digest-h1-b5.txt', 'SAIRN-handoff-cc-b7.md',
                  'SAIRN-handoff-cody-b6.md', 'notes.txt']))

    # ── ARM GROUP 7: the criteria lock runs before any verdict ──────────────
    rc, out = run(drive, local, '--fixtures')
    arms.append(('the criteria lock passes on its own fixtures',
                 (rc, 'fixtures classify correctly' in out), (0, True)))
    keep = duv.run_fixtures
    try:
        duv.run_fixtures = lambda: duv.EXIT_FINDING
        rc2 = duv.main(['--agent', 'cc', '--batch', 'b7'])
    finally:
        duv.run_fixtures = keep
    arms.append(('ABLATION lock: a broken lock makes the whole run COULD NOT '
                 'RUN, so no verdict is issued on broken criteria',
                 rc2, 2))

    # ── ARM GROUP 8: the arguments are not guessed ──────────────────────────
    rc, out = run(drive, local, '--batch', 'b7')
    arms.append(('--agent is REQUIRED, not inferred from the folder name',
                 (rc, 'are both' in out), (2, True)))
    rc, out = run(drive, local, '--agent', 'cc', '--batch', '7')
    arms.append(('a batch without the b is COULD NOT RUN',
                 rc, 2))
    rc, out = run(drive, local, '--agent', 'hover', '--batch', 'b7')
    arms.append(('the auditors\' Drive token is h1/h2, and `hover` is refused '
                 'rather than filed under a name nothing reads',
                 (rc, 'h1/h2' in out), (2, True)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

passed = 0
for name, got, want in arms:
    ok = got == want
    passed += ok
    print('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
    if not ok:
        print('       wanted %r' % (want,))
        print('       got    %r' % (got,))
print('drive_upload_verify probe: %d/%d arm(s) pass' % (passed, len(arms)))
sys.exit(0 if passed == len(arms) else 1)
