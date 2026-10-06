# OWNER: hank
"""run_purposes_duplicate_key_probe.py -- a MISSING PURPOSES entry and a
DUPLICATE one must both refuse. This is the REGRESSION that proves it, by
driving the real generator rather than reading it.

    python tests/run_purposes_duplicate_key_probe.py
    python tests/run_purposes_duplicate_key_probe.py --selftest

── WHAT THIS WAS, AND WHAT IT IS NOW ─────────────────────────────────────────
It was a BUG REPORT. Written 2026-10-06 while `tools/tooling_inventory.py`
appeared to be another session's under a live claim, so the finding could not be
fixed by the session that found it; the standing rule is that a finding routed
to another agent carries a REPRODUCING ARTIFACT rather than prose, and this file
was that artifact. It exited 1 and arm B was the accusation.

IT IS NOW A REGRESSION. Re-derived at HEAD 2026-10-06: cody's claim text FLAGGED
THE FILE BACK ("hank holds tools/tooling_inventory.py ... item 7 is FLAGGED BACK
unlanded") and does not list it among its own FILES, and hank's live claim does.
So the fix was hank's to make and was made in the same change as this edit. Not
one line of the two arms changed -- only the prose and the exit contract. THAT IS
THE POINT: the arms were written to go green on the fix, so the file that
accused the generator is the file that now guards it, with no rewrite to make it
agree with the code.

── THE ASYMMETRY IT WAS BUILT FROM ───────────────────────────────────────────
MISSING entry  -> the generator REFUSED to run, exit 2, naming the file:
    "REFUSING to generate -- the hand-written half has drifted.
     1 tool(s) in tools/ with no PURPOSES entry."
DUPLICATE key  -> nothing. Python keeps the LAST of two identical dict keys and
discards the first silently; the generator never looked, so the document
regenerated cleanly and the dead entry was invisible for ever.

THE SECOND IS THE MIRROR OF THE FIRST AND IT WAS THE QUIETER FAILURE. A missing
entry announces itself at the next push. A duplicate is a cell somebody WROTE,
believing it landed, which is never read -- and the author had no way to find
out. This happened for real on 2026-10-06: a `gate_parity_check.py` entry was
written into PURPOSES while another session had already added one, Python kept
theirs, and the duplicate was dead text nobody could have noticed.

── WHY DUPLICATE REFUSES AT LEAST AS LOUDLY ──────────────────────────────────
The generator's own stated reason for refusing a MISSING entry is that "a blank
cell is how the last inventory went stale". A duplicate is worse than a blank
cell: a blank cell is visible in the rendered document, and a discarded entry is
visible nowhere at all. The fix is `duplicate_purposes_keys()`, which parses the
generator's own SOURCE with `ast` -- the imported dict cannot answer the
question, because by then Python has already thrown the duplicate away.

── WHAT THIS PROBE DOES NOT CLAIM ────────────────────────────────────────────
It does not say the duplicate ever produced a WRONG cell -- on 2026-10-06 the
surviving entry was the better of the two. It says the mechanism could not tell
anybody, which was a different and more durable problem than one bad row.

It also does not cover the THIRD STATE the fix added: a generator that cannot
read or parse its own source refuses with "COULD NOT CHECK" rather than
reporting no duplicates. Driving that needs an unreadable source, which is a
different arm and is NOT RUN here. Stated so a green run is not read as covering
it.

EXIT: 0 both halves refuse (the regression holds), 1 the asymmetry is BACK,
2 COULD NOT RUN.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join('tools', 'tooling_inventory.py')
#   .1 the asymmetry as a bug report (arm B expected to FAIL).
#   .2 the same two arms as a REGRESSION (arm B expected to PASS). The arms are
#      byte-identical; only the contract around them moved, so a past report
#      stamped .1 and a run stamped .2 are not comparing different criteria.
CRITERIA_VERSION = '2026-10-06.2'


def scratch_tree():
    """A copy of the COMMITTED tree, under the system temp dir.

    The generator WRITES docs/TOOLING-INVENTORY.md, so this probe must never run
    it in the live clone -- and it has to mutate PURPOSES to drive the two arms,
    which is a second reason. `git -C` anchors the archive so it cannot answer
    about the home-directory repository, which on this machine is a real one.
    """
    d = tempfile.mkdtemp(prefix='purposes-probe-')
    tar = os.path.join(d, 'tree.tar')
    with io.open(tar, 'wb') as fh:
        p = subprocess.run(['git', '-C', REPO, 'archive', 'HEAD'],
                           stdout=fh, stderr=subprocess.PIPE)
    if p.returncode != 0:
        return None, 'git archive HEAD failed: %s' % p.stderr.decode('utf-8', 'replace')[:160]
    root = os.path.join(d, 'tree')
    os.makedirs(root)
    p = subprocess.run(['tar', '-x', '-f', tar, '-C', root],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        return None, 'tar extract failed: %s' % p.stderr.decode('utf-8', 'replace')[:160]
    if not os.path.isfile(os.path.join(root, GEN)):
        return None, '%s is not in the committed tree' % GEN
    # ── THE COPY HAS TO BE A REAL GIT REPO, AND THE BASELINE ARM IS WHAT
    # TAUGHT ME THAT. The generator derives its universe from
    # `git ls-files tools/`; in a bare extraction that returns NOTHING, so it
    # refused with "3 empty source(s)" -- correctly, fail-closed, on an empty
    # population. Without the baseline arm both the missing and the duplicate
    # arms would have seen exit 2 and the probe would have reported the
    # asymmetry as ALREADY FIXED.
    for cmd in (['git', 'init', '-q'],
                ['git', '-c', 'user.email=probe@local',
                 '-c', 'user.name=probe', 'add', '-A'],
                ['git', '-c', 'user.email=probe@local',
                 '-c', 'user.name=probe', 'commit', '-q', '-m', 'probe base']):
        p = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
        if p.returncode != 0:
            return None, ('the scratch copy could not be made into a git repo '
                          '(%s): %s' % (' '.join(cmd),
                                        p.stdout.decode('utf-8', 'replace')[:160]))
    return root, None


def run_gen(root):
    p = subprocess.run([sys.executable, GEN], cwd=root, timeout=300,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def first_purposes_key(src):
    """The first `'name.py': (` key inside the PURPOSES literal, and its span."""
    i = src.index('PURPOSES = {')
    m = re.search(r"\n(\s*)'([a-z0-9_]+\.py)':\s*\(", src[i:])
    if not m:
        return None, None, None
    return m.group(2), i + m.start(), m.group(1)


def main(argv):
    if '--selftest' in argv:
        # The selftest IS the probe here: both arms drive the real generator in
        # a scratch tree, so there is no separate fixture layer to keep honest.
        return main([a for a in argv if a != '--selftest'])

    print('PURPOSES DUPLICATE-KEY ASYMMETRY -- criteria %s' % CRITERIA_VERSION)
    root, why = scratch_tree()
    if root is None:
        print('COULD NOT RUN: no scratch copy -- %s' % why)
        print('This is NOT "no asymmetry". Nothing was driven.')
        return 2
    base = os.path.dirname(root)
    try:
        gen_path = os.path.join(root, GEN)
        original = io.open(gen_path, encoding='utf-8').read()
        key, at, indent = first_purposes_key(original)
        if key is None:
            print('COULD NOT RUN: no PURPOSES entry found to duplicate.')
            return 2
        print('  subject   : %s' % GEN)
        print('  scratch   : %s' % root)
        print('  key used  : %s (the first entry in PURPOSES)' % key)
        print('')

        npass = nfail = 0

        def ck(label, cond, extra=''):
            nonlocal npass, nfail
            if cond:
                npass += 1
                print('  ok   ' + label)
            else:
                nfail += 1
                print('  FAIL ' + label)
                if extra:
                    print('       ' + str(extra)[:300])

        # ── BASELINE. Without this the two arms below could both be measuring
        #    a generator that refuses everything.
        rc, out = run_gen(root)
        ck('BASELINE. the UNMODIFIED generator runs clean (exit 0). Without '
           'this arm a generator that refused everything would satisfy both '
           'arms below and look like the fix', rc == 0, 'exit=%d %s' % (rc, out[-200:]))

        # ── ARM A, THE CONTROL: a MISSING entry must refuse loudly.
        missing = original[:at] + re.sub(
            r"^\s*'%s':\s*\(.*?\n(?=\s*'[a-z0-9_]+\.py':)" % re.escape(key),
            '', original[at:], count=1, flags=re.S)
        io.open(gen_path, 'w', encoding='utf-8', newline='\n').write(missing)
        rc_missing, out_missing = run_gen(root)
        loud_missing = (rc_missing == 2 and 'REFUSING' in out_missing
                        and key in out_missing)
        ck('A. a MISSING entry REFUSES, exit 2, and NAMES the tool. This is '
           'the control and the standard the other half is measured against',
           loud_missing, 'exit=%d; names key=%s' % (rc_missing, key in out_missing))

        # ── ARM B, THE SUBJECT: a DUPLICATE key must refuse at least as loudly.
        dup_line = "%s'%s': ('CHECKER', 'zz duplicate injected by the probe'),\n" % (indent, key)
        dupd = original[:at + 1] + dup_line + original[at + 1:]
        io.open(gen_path, 'w', encoding='utf-8', newline='\n').write(dupd)
        rc_dup, out_dup = run_gen(root)
        # It really is a duplicate in the literal, not a near-miss.
        occurrences = len(re.findall(r"\n\s*'%s':\s*\(" % re.escape(key), dupd))
        ck('B0. the injected source really does carry the key TWICE -- without '
           'this the arm below could be reporting on a file it failed to '
           'modify', occurrences >= 2, 'occurrences=%d' % occurrences)

        loud_dup = rc_dup != 0 and ('duplicate' in out_dup.lower()
                                    or 'DUPLICATE' in out_dup)
        ck('B. a DUPLICATE key refuses at least as loudly as a missing one. '
           'THE DEFECT IF THIS FAILS: Python keeps the LAST of two identical '
           'dict keys and discards the first silently, the generator never '
           'looks, and the discarded entry is invisible in the rendered '
           'document AND in the source', loud_dup,
           'exit=%d, and the output does not mention a duplicate' % rc_dup)
        # B1 is NOT redundant with B. Arm B is satisfied by any non-zero exit
        # mentioning a duplicate, so a refusal that said "a duplicate exists
        # somewhere" would pass it -- and that is not actionable: the author
        # cannot find a key they cannot see. This arm requires the KEY ITSELF in
        # the output, which is the standard arm A holds the missing half to.
        ck('B1. ...and NAMES THE KEY, the way the missing-entry refusal names '
           'the tool. "There is a duplicate somewhere" is not actionable on a '
           'literal of this size', key in out_dup,
           'exit=%d; the output never mentions %s' % (rc_dup, key))

        print('')
        print('  MEASURED: missing -> exit %d%s | duplicate -> exit %d%s'
              % (rc_missing, ' (REFUSING)' if 'REFUSING' in out_missing else '',
                 rc_dup, ' (silent)' if rc_dup == 0 else ''))
        print('')
        print('%d passed, %d failed' % (npass, nfail))
        if nfail:
            print('')
            print('THE ASYMMETRY IS BACK. This arm went green on 2026-10-06 when '
                  'tools/tooling_inventory.py grew duplicate_purposes_keys(), '
                  'which parses the generator\'s own SOURCE with ast -- the '
                  'imported dict cannot answer the question, because Python has '
                  'already discarded the duplicate by then. If arm B is failing, '
                  'check that function is still CALLED from build() and still in '
                  'the `if absent or untracked or gone or dup or dupkeys or '
                  'dupwhy:` condition; a check that is present but no longer '
                  'consulted is the shape this probe exists to catch.')
        return 1 if nfail else 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
