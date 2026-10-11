# OWNER: hank
"""run_status_doc_secret_probe.py -- A MISSING SECRET MUST NEVER OVERWRITE A
GOOD RECORD.

    python tests/run_status_doc_secret_probe.py

EXIT 0 every subject behaves, 1 at least one does not, 2 COULD NOT RUN.

── THE DEFECT THIS LOCKS, MEASURED 2026-10-07 ───────────────────────────────
A bare run of `tools/cron_liveness_check.py` in a clone with no `CRON_SECRET`
**REPLACED** `docs/CRON-LIVENESS-STATUS.md` -- a real **OK**, four jobs, all ok,
measured 09:18:44Z -- with **COULD NOT TELL**. The record was destroyed by a
session that had no way to check it, and nothing anywhere recorded that an OK had
ever existed. `tools/audit_checkpoint_status.py` did the same to
`docs/AUDIT-CHECKPOINT-STATUS.md`.

── WHY THE ORIGINAL REASONING WAS SOUND AND STILL WRONG HERE ────────────────
"Say so rather than keep a stale OK" is RIGHT when the tool **asked** and could
not get an answer: a 401, a timeout, an unparseable body. Those are facts about
the subject. **A MISSING ENVIRONMENT VARIABLE IS NOT A FACT ABOUT THE SUBJECT.**
It is a fact about the clone the tool happens to be running in -- and five of the
six clones on this box do not carry the secret, so every sweep that drove every
tool bare erased the record again.

So the missing-secret path writes NOTHING and exits **3**. Every other
could-not-tell path is unchanged and still records COULD NOT TELL, because those
ran.

── HOW IT IS DRIVEN, AND WHY NOT IN A WORKTREE ──────────────────────────────
Each subject is copied into a **SYNTHETIC SANDBOX** -- a bare directory holding
`tools/<subject>.py`, `tools/sairn_http.py` and a `docs/` carrying a PLANTED GOOD
RECORD. The subjects derive their repo root from `__file__`, so the sandbox is a
complete world and nothing shared is reachable from it.

NOT A LINKED WORKTREE, on purpose. Batch 18 found that a worktree shares
`.git/config` with the clone that owns it, so a tool driven inside one corrupted
the real clone (`core.bare = true`). RULE G, in
`docs/2026-10-07-hank-routed.md`: test infrastructure must not mutate the clone
or shared state it runs in.

── THE SABOTAGE HALF, WHICH IS WHAT MAKES THE ARMS EVIDENCE ─────────────────
For each subject the probe also builds a sandbox carrying the **OLD BEHAVIOUR**
-- the missing-secret path restored to `write_status(...)` + exit 2 -- and
asserts the arms would have FAILED on it: exit 2 not 3, and the planted record
**gone**. An arm that cannot be made to fail has not been tested.
"""
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRITERIA_VERSION = '2026-10-08.1'

# (tool, status document basename, a word the GOOD record contains)
SUBJECTS = [
    ('cron_liveness_check.py', 'CRON-LIVENESS-STATUS.md'),
    ('audit_checkpoint_status.py', 'AUDIT-CHECKPOINT-STATUS.md'),
]

GOOD = (
    '# PLANTED GOOD RECORD\n'
    '\n'
    'This file stands in for a real OK verdict written by a run that COULD ask.\n'
    'If a subject overwrites it when no secret is set, that is the defect.\n'
    '\n'
    'SENTINEL-DO-NOT-OVERWRITE-7f31a9\n')

npass = nfail = 0


def ck(label, cond, extra=''):
    global npass, nfail
    if cond:
        npass += 1
        print('  ok   ' + label)
    else:
        nfail += 1
        print('  FAIL ' + label)
        if extra:
            print('       ' + str(extra)[:400])


def sha(path):
    return hashlib.sha256(io.open(path, 'rb').read()).hexdigest()


def sandbox(base, tool, docname, sabotage=False):
    """A complete little world: tools/ + docs/, nothing shared reachable."""
    root = tempfile.mkdtemp(prefix='statusdoc_', dir=base)
    os.makedirs(os.path.join(root, 'tools'))
    os.makedirs(os.path.join(root, 'docs'))
    src = io.open(os.path.join(REPO, 'tools', tool), encoding='utf-8').read()
    if sabotage:
        # RESTORE THE OLD BEHAVIOUR: make the missing-secret path write the
        # COULD NOT TELL document and return the could-not-run code, which is
        # exactly what it did before 2026-10-08.
        src, n = re.subn(
            r'(\n    if not secret:\n)(.*?)(\n        return EXIT_NO_SECRET\n)',
            r'\1        write_status("COULD NOT TELL", ["sabotage: the old '
            r'behaviour, which overwrote this file"])\n'
            r'        return EXIT_COULD_NOT_RUN\n',
            src, count=1, flags=re.S)
        if n != 1:
            return None, 'could not plant the sabotage in %s' % tool
    io.open(os.path.join(root, 'tools', tool), 'w', encoding='utf-8',
            newline='\n').write(src)
    shutil.copy(os.path.join(REPO, 'tools', 'sairn_http.py'),
                os.path.join(root, 'tools', 'sairn_http.py'))
    io.open(os.path.join(root, 'docs', docname), 'w', encoding='utf-8',
            newline='\n').write(GOOD)
    return root, None


def drive(root, tool):
    env = dict(os.environ)
    env.pop('CRON_SECRET', None)          # THE WHOLE POINT: no secret
    env['PYTHONIOENCODING'] = 'utf-8'
    p = subprocess.run([sys.executable, '-u', os.path.join('tools', tool)],
                       cwd=root, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, env=env, timeout=120)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def main():
    print('STATUS DOC vs MISSING SECRET -- criteria %s' % CRITERIA_VERSION)
    print('  subjects: %s' % ', '.join(t for t, _ in SUBJECTS))
    print('  CRON_SECRET is removed from the environment of every run below.')
    print('')

    missing = [t for t, _ in SUBJECTS
               if not os.path.isfile(os.path.join(REPO, 'tools', t))]
    if missing:
        print('COULD NOT RUN: not on disk: %s' % ', '.join(missing))
        print('Nothing was driven. This is NOT "both subjects behave".')
        return 2

    base = tempfile.mkdtemp(prefix='statusdoc_base_')
    try:
        for tool, docname in SUBJECTS:
            print('%s' % tool)
            root, why = sandbox(base, tool, docname)
            if root is None:
                ck('A. %s sandbox could be built' % tool, False, why)
                continue
            doc = os.path.join(root, 'docs', docname)
            before = sha(doc)
            code, out = drive(root, tool)
            after = sha(doc) if os.path.isfile(doc) else None

            ck('A. %-28s with NO secret exits 3, not 2. Exit 2 means '
               'COULD NOT RUN and is used by the paths that DID ask; a '
               'credential this clone never had is a different state'
               % tool, code == 3,
               'exit=%s  %s' % (code, out.strip().split('\n')[0][:160]))
            ck('B. %-28s ...and the status document is BYTE-IDENTICAL '
               'afterwards. This is the arm that matters: the defect was not a '
               'wrong exit code, it was a destroyed record'
               % tool, after == before,
               'before=%s after=%s' % (before[:12],
                                       (after or 'FILE GONE')[:12]))
            ck('C. %-28s ...and it SAYS nothing was written, so a reader of '
               'the output is not left guessing whether the file moved'
               % tool, 'NOTHING WAS WRITTEN' in out, out[:200])
            ck('D. %-28s ...and the planted sentinel survives, which proves B '
               'compared a real file rather than two absences'
               % tool,
               os.path.isfile(doc)
               and 'SENTINEL-DO-NOT-OVERWRITE-7f31a9'
               in io.open(doc, encoding='utf-8').read(),
               'doc exists=%s' % os.path.isfile(doc))

            # ── THE SABOTAGE HALF ──────────────────────────────────────────
            sroot, swhy = sandbox(base, tool, docname, sabotage=True)
            if sroot is None:
                ck('S. %-28s SABOTAGE could be planted -- without this the '
                   'arms above are unfalsified' % tool, False, swhy)
                continue
            sdoc = os.path.join(sroot, 'docs', docname)
            sbefore = sha(sdoc)
            scode, sout = drive(sroot, tool)
            safter = sha(sdoc) if os.path.isfile(sdoc) else None
            ck('S1. %-27s SABOTAGE (old behaviour restored) exits 2, so arm A '
               'WOULD have failed on it' % tool, scode == 2,
               'exit=%s %s' % (scode, sout.strip()[-160:]))
            ck('S2. %-27s SABOTAGE OVERWRITES the planted record, so arm B '
               'WOULD have failed on it. An arm that cannot be made to fail '
               'has not been tested' % tool, safter != sbefore,
               'before=%s after=%s' % (sbefore[:12],
                                       (safter or 'GONE')[:12]))
            ck('S3. %-27s ...and the sentinel is GONE from the sabotaged run, '
               'which is the destroyed record stated as a fact rather than as '
               'a hash difference' % tool,
               os.path.isfile(sdoc)
               and 'SENTINEL-DO-NOT-OVERWRITE-7f31a9'
               not in io.open(sdoc, encoding='utf-8').read(),
               'sentinel still present')
            print('')
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print('%d passed, %d failed' % (npass, nfail))
    print('')
    print('WHAT THIS DOES NOT COVER, said rather than left to be assumed:')
    print('  * the OTHER could-not-tell paths -- a 401, a timeout, an')
    print('    unparseable body -- STILL write COULD NOT TELL, deliberately.')
    print('    Those ran and the result is a fact about the subject.')
    print('  * a run WITH a real secret is not driven here. No credential was')
    print('    manufactured, so the happy path is untested by this file.')
    return 1 if nfail else 0


if __name__ == '__main__':
    sys.exit(main())
