"""tests/claims/run_freshness_probe.py

Run:  python tests/claims/run_freshness_probe.py

Holds the 2026-09-14 fix: `sairn_claim.py` must never state a verdict without
stating how old the evidence under it is.

── THE DEFECT, REPRODUCED BEFORE IT WAS FIXED ────────────────────────────────
`cmd_check` ran `sh(['git','fetch','origin'], check=False)` and threw the
result away. With the remote unreachable the fetch exited 128 with "unable to
access", and the very next line printed was

    CLEAR -- no active overlapping claim from another session.

That verdict came off an `origin/main` ref eighteen minutes stale and nothing
said so. The single existing warning ("falling back to this clone's copy, which
may be stale") could not fire, because nothing had fallen back: a stale
remote-tracking ref is perfectly readable, so `read_origin_claims()` SUCCEEDED
and returned old claims.

"Could not run" folded into "passed" -- CLAUDE.md PR §1.11 -- inside the tool
whose entire premise is that a fetch happened. And disciplines item 8 exactly: a
directional gyro reads perfectly smoothly the whole time it is wrong, and **a
check that cannot say how old its evidence is has not been re-referenced at
all.**

Worth recording why it survived: `tools/sairn_claim_hook.py` ALREADY tracked
this. Its `try_fetch()` returns a bool and `read_claims()` threads a `fresh`
flag so that "a fallback answer is never reported as a current one". The
accounting existed in the copy that runs unattended and was missing from the
copy a human invokes before spending hours -- the same one-copy-fixed asymmetry
this pair recorded on 2026-09-04 over `git checkout origin/main --`, arrow
reversed.

── WHY A REAL GIT REPO AND NOT A MOCK ────────────────────────────────────────
Same reason as run_push_verify_probe.py, and one more specific to this fix. The
question is what git does when a fetch FAILS: whether the remote-tracking ref
survives, whether the origin read still succeeds off it, and whether FETCH_HEAD
is left alone. A stubbed subprocess would assert the code calls the commands it
calls, which is not the question. A real bare remote is built on disk and then
DELETED to break the fetch; no network is involved.

── SECTION I IS THE PART THAT MAKES THE REST WORTH READING ───────────────────
Seven mutations reintroduce the defect in seven different shapes, and each one
FIRST asserts its own sabotage changed the file. Measured on this platform
2026-09-13: 39 probes sabotage a real source file, 23 of them never verify the
sabotage applied -- `str.replace` on an anchor that no longer matches silently
does nothing and the control then runs against an unmodified file, reporting
green for ever. Every mutation here carries that assertion.

**Control 7 is here because this probe caught a real one while being written,
which is the argument for the whole section.** `last_fetch_hours()` first read
`.git/FETCH_HEAD`'s mtime, on the reasoning that git rewrites it on a
successful fetch. Measured instead of reasoned about, both halves were wrong:
`git clone` never writes FETCH_HEAD at all, and a FAILED fetch CREATES and
touches it -- `git fetch` exiting 128 against a dead remote left the file 0.00
hours old. The tool would have reported a five-hour-stale view as one minute
old, immediately after the fetch that failed to refresh it. That is the
`gate_column_check` understatement recommitted by the code written to avoid it,
in the one direction that matters, and nothing but a control that made it fail
on purpose was going to find it.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, 'tools', 'sairn_claim.py')

passed = 0
failed = 0


def check(name, cond, detail=''):
    global passed, failed
    if cond:
        print('  ok   ' + name)
        passed += 1
    else:
        print('  FAIL ' + name + (('\n       ' + detail) if detail else ''))
        failed += 1


def git(cwd, *args, **kw):
    r = subprocess.run(('git',) + args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if kw.get('check', True) and r.returncode != 0:
        raise RuntimeError('git %s failed in %s:\n%s' % (' '.join(args), cwd, r.stderr))
    return r


def run_tool(clone, *args):
    r = subprocess.run([sys.executable, os.path.join(clone, 'tools', 'sairn_claim.py')]
                       + list(args), cwd=clone, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


BANNER = 'THE REMOTE WAS NOT READ ON THIS RUN'
AS_OF = 'AS OF THE LAST SUCCESSFUL FETCH'


def build():
    """A bare origin plus one working clone named SAIRN-probe.

    The directory name matters: session_name() derives the session from it,
    exactly as the four real clones are distinguished.
    """
    tmp = tempfile.mkdtemp(prefix='sairn-fresh-probe-')
    origin = os.path.join(tmp, 'origin.git')
    seed = os.path.join(tmp, 'seed')
    clone = os.path.join(tmp, 'SAIRN-probe')

    git(tmp, 'init', '--bare', '-b', 'main', origin)
    git(tmp, 'init', '-b', 'main', seed)
    for k, v in (('user.email', 'probe@example.invalid'), ('user.name', 'Probe'),
                 ('commit.gpgsign', 'false')):
        git(seed, 'config', k, v)
    os.makedirs(os.path.join(seed, '.claude', 'claims'))
    # Another session holding an ACTIVE claim on origin -- needed by section E,
    # and it must be on the REMOTE rather than in the clone's working tree so
    # the arms read it the way a real session would.
    with open(os.path.join(seed, '.claude', 'claims', 'other.json'), 'w') as f:
        json.dump({'session': 'other', 'claims': [{
            'id': 'other-1', 'session': 'other',
            'subject': 'zzsubject', 'task': 'zztask words',
            'claimed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'claimed_at_epoch': time.time(),
            'status': 'active', 'released_at': None}]}, f)
    git(seed, 'add', '-A')
    git(seed, 'commit', '-q', '-m', 'seed')
    git(seed, 'remote', 'add', 'origin', origin)
    git(seed, 'push', '-q', 'origin', 'main')

    git(tmp, 'clone', '-q', origin, clone)
    for k, v in (('user.email', 'probe@example.invalid'), ('user.name', 'Probe'),
                 ('commit.gpgsign', 'false')):
        git(clone, 'config', k, v)
    os.makedirs(os.path.join(clone, 'tools'), exist_ok=True)
    shutil.copy(TOOL, os.path.join(clone, 'tools', 'sairn_claim.py'))
    return tmp, origin, seed, clone


def kill_remote(clone, tmp):
    """Break the fetch without touching the remote-tracking ref.

    This is the real shape of the defect: origin/main stays readable, so the
    origin read succeeds off stale bytes and no fallback warning fires.
    """
    git(clone, 'remote', 'set-url', 'origin', os.path.join(tmp, 'no-such-remote.git'))


def revive_remote(clone, origin):
    git(clone, 'remote', 'set-url', 'origin', origin)


STAMP = 'sairn-claim-last-fetch'


def set_fetch_age(clone, hours):
    """Backdate the success stamp -- the instrument the age is read from."""
    with open(os.path.join(clone, '.git', STAMP), 'w') as f:
        f.write('%f\n' % (time.time() - hours * 3600))


def clear_fetch_age(clone):
    p = os.path.join(clone, '.git', STAMP)
    if os.path.exists(p):
        os.remove(p)


def mutate(clone, anchor, replacement):
    """Reintroduce the defect, and PROVE the sabotage landed.

    Returns a restore callable. Raises if the anchor no longer matches -- which
    is the failure mode being defended against: `str.replace` on a stale anchor
    does nothing at all and the control then runs against clean code.
    """
    path = os.path.join(clone, 'tools', 'sairn_claim.py')
    with open(path, encoding='utf-8') as f:
        original = f.read()
    if anchor not in original:
        raise RuntimeError('SABOTAGE ANCHOR NO LONGER MATCHES -- this control '
                           'cannot fail and is therefore worthless:\n  %r' % anchor)
    patched = original.replace(anchor, replacement, 1)
    if patched == original:
        raise RuntimeError('SABOTAGE CHANGED NOTHING for anchor %r' % anchor)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)

    def restore():
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(original)
    return restore, len(original) - len(patched)


def main():
    print('sairn_claim.py -- a verdict must carry the age of its evidence\n')
    tmp, origin, seed, clone = build()
    try:
        # ── A. the fresh path is unchanged, and stays quiet ───────────────────
        # A banner that printed on every run is one a reader learns to skip,
        # which would cost exactly the line that matters. Silence on a good
        # fetch is part of the fix, not an omission from it.
        print('A. A GOOD FETCH -- current, and says nothing about age')
        rc, out = run_tool(clone, 'check', 'freshsubject', 'nothing collides')
        check('a fetch that worked exits 0', rc == 0, 'rc=%s out=%s' % (rc, out))
        check('...and still prints CLEAR', 'CLEAR' in out, out)
        check('...and prints NO freshness banner', BANNER not in out, out)

        # ── B. a FAILED fetch -- the exact defect ─────────────────────────────
        print('\nB. A FAILED FETCH -- the reproduction')
        kill_remote(clone, tmp)
        rc, out = run_tool(clone, 'check', 'freshsubject', 'nothing collides')
        check('a failed fetch no longer exits 0', rc != 0, 'rc=%s' % rc)
        check('...it exits the distinct staleness code 4', rc == 4, 'rc=%s' % rc)
        check('...and says the remote was not read', BANNER in out, out)
        check('...and says the fetch FAILED rather than being skipped',
              'the git fetch FAILED' in out, out)
        check('...and says the verdict is as of the last fetch, not now',
              AS_OF in out and 'NOT AS OF NOW' in out, out)
        check('...and names the actual git error rather than a generic line',
              'fetch error:' in out, out)
        check('...and warns before hours are spent on it',
              'before spending hours' in out, out)
        # The verdict itself is still printed. The fix is that it is QUALIFIED,
        # not withheld -- a tool that refuses offline gets routed around, which
        # this file's own header records costing six overrides.
        check('...and the CLEAR verdict is still shown, qualified not withheld',
              'CLEAR' in out, out)

        # ── C. --no-fetch is a different sentence for the same state ─────────
        print('\nC. --no-fetch -- deliberate, and still not current')
        revive_remote(clone, origin)
        rc, out = run_tool(clone, 'check', 'freshsubject', 'nothing collides',
                           '--no-fetch')
        check('--no-fetch exits 4', rc == 4, 'rc=%s' % rc)
        check('...and says --no-fetch was passed, not that anything failed',
              '--no-fetch was passed' in out, out)
        check('...and does not blame a git error it never saw',
              'fetch error:' not in out, out)

        # ── D. list -- where an empty answer reads as permission ─────────────
        print('\nD. list -- an empty list off a stale ref is the worst output')
        kill_remote(clone, tmp)
        rc, out = run_tool(clone, 'list')
        check('list exits 4 on a failed fetch', rc == 4, 'rc=%s out=%s' % (rc, out))
        check('...and carries the banner', BANNER in out, out)
        # Force the no-rows path: an empty roster is the output most likely to
        # be read as "nobody is on anything, go ahead".
        os.rename(os.path.join(clone, '.claude', 'claims'),
                  os.path.join(clone, '.claude', 'claims-hidden'))
        git(clone, 'update-ref', '-d', 'refs/remotes/origin/main')
        rc, out = run_tool(clone, 'list')
        check('"No active claims" off a stale view still carries the banner',
              'No active claims' in out and BANNER in out, 'rc=%s out=%s' % (rc, out))
        os.rename(os.path.join(clone, '.claude', 'claims-hidden'),
                  os.path.join(clone, '.claude', 'claims'))
        revive_remote(clone, origin)
        git(clone, 'fetch', '-q', 'origin')

        # ── E. a BLOCK on stale evidence still blocks, and says it is stale ──
        print('\nE. A BLOCK -- 1 is not displaced, and staleness cuts both ways')
        kill_remote(clone, tmp)
        rc, out = run_tool(clone, 'check', 'zzsubject', 'zztask words')
        check('a block still exits 1, not 4', rc == 1, 'rc=%s out=%s' % (rc, out))
        check('...and still says DO NOT start this', 'DO NOT start this' in out, out)
        check('...and ALSO says the evidence may be stale', BANNER in out, out)
        check('...and says a claim shown active may already be released',
              'already have been released' in out, out)

        # ── F. claim must not ABORT on a stale check ─────────────────────────
        # The publish half does not degrade on stale data -- push_verified()
        # proves the commit reached origin/main or returns 3. Aborting at the
        # check would break the 2026-09-04 contract that an unpushable claim
        # says NOT CLAIMED in those words, so that contract is asserted here
        # and not only in run_push_verify_probe.py.
        print('\nF. claim -- stale warns, it does not abort')
        rc, out = run_tool(clone, 'claim', 'doomedsubject', 'push cannot succeed')
        check('a stale check does not stop the claim attempt',
              'PROCEEDING ANYWAY' in out, out)
        check('...and the unpushable claim still exits non-zero', rc != 0, 'rc=%s' % rc)
        check('...and still says NOT CLAIMED in those words',
              'NOT CLAIMED' in out, out)
        check('...and never prints a bare CLAIMED',
              'CLAIMED.' not in out.replace('NOT CLAIMED', ''), out)
        git(clone, 'reset', '-q', '--hard', 'origin/main')
        revive_remote(clone, origin)
        git(clone, 'fetch', '-q', 'origin')

        # ── G. the age is the FETCH, not a commit date ───────────────────────
        # docs/2026-09-13-claim-provenance-chain-design.md Q1: gate_column_check
        # measured freshness from a git commit date and reported a 43.3-hour
        # capture as 25 hours old -- an 18.7-hour understatement, in the
        # direction that makes stale data look current. These arms discriminate
        # between the two instruments rather than assuming the right one.
        print('\nG. THE AGE IS MEASURED FROM THE FETCH, NOT FROM A COMMIT DATE')
        # Put a very OLD commit on origin and fetch it, so the tip's date and
        # the fetch time are far apart and only one of them is 5 hours.
        old = '2026-09-01T00:00:00'
        env = dict(os.environ, GIT_AUTHOR_DATE=old, GIT_COMMITTER_DATE=old)
        with open(os.path.join(seed, 'stamp.txt'), 'w') as f:
            f.write('old tip\n')
        git(seed, 'add', '-A')
        subprocess.run(('git', 'commit', '-q', '-m', 'an old tip'), cwd=seed,
                       env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        git(seed, 'push', '-q', 'origin', 'main')
        git(clone, 'fetch', '-q', 'origin')
        tip_age_h = ((time.time()
                      - int(git(clone, 'log', '-1', '--format=%ct',
                                'origin/main').stdout.strip())) / 3600.0)
        check('the fixture really does have a tip much older than the fetch',
              tip_age_h > 24, 'tip age %.1fh' % tip_age_h)
        kill_remote(clone, tmp)
        set_fetch_age(clone, 5.0)
        rc, out = run_tool(clone, 'list')
        check('a 5-hour-old fetch is reported as ~5 hours',
              '5.0 hours ago' in out, out)
        check('...and NOT as the age of the tip commit',
              ('%.1f hours ago' % tip_age_h) not in out
              and ('%.1f DAYS ago' % (tip_age_h / 24.0)) not in out, out)
        set_fetch_age(clone, 0.05)
        rc, out = run_tool(clone, 'list')
        check('a 3-minute-old fetch reads in MINUTES, not "0.0 hours"',
              '3 minutes ago' in out, out)
        check('...and "0.0 hours" never appears', '0.0 hours' not in out, out)
        set_fetch_age(clone, 96.0)
        rc, out = run_tool(clone, 'list')
        check('a four-day-old fetch reads in DAYS', '4.0 DAYS ago' in out, out)
        clear_fetch_age(clone)
        rc, out = run_tool(clone, 'list')
        check('an unmeasurable age says so rather than guessing zero',
              'AT A TIME THIS CANNOT MEASURE' in out, out)
        check('...and never renders as a number when it is unknown',
              'minutes ago' not in out and 'hours ago' not in out, out)
        # A clock that moved backwards must not produce a negative age.
        with open(os.path.join(clone, '.git', STAMP), 'w') as f:
            f.write('%f\n' % (time.time() + 7200))
        rc, out = run_tool(clone, 'list')
        check('a stamp in the FUTURE reads as unmeasurable, not negative',
              'AT A TIME THIS CANNOT MEASURE' in out and '-' not in
              [ln for ln in out.split('\n') if AS_OF in ln][0].split(AS_OF)[1],
              out)
        with open(os.path.join(clone, '.git', STAMP), 'w') as f:
            f.write('not a number\n')
        rc, out = run_tool(clone, 'list')
        check('an unparseable stamp reads as unmeasurable, not a crash',
              rc == 4 and 'AT A TIME THIS CANNOT MEASURE' in out,
              'rc=%s out=%s' % (rc, out))

        # ── G2. THE INSTRUMENT ITSELF -- why it is not FETCH_HEAD ────────────
        # Measured, not assumed, because the first implementation DID use
        # FETCH_HEAD and it was wrong in the direction that makes stale data
        # look current. If git ever changes either behaviour these two arms are
        # how anybody finds out.
        print('\nG2. WHY NOT FETCH_HEAD -- the measurement that rejected it')
        fh = os.path.join(clone, '.git', 'FETCH_HEAD')
        if os.path.exists(fh):
            os.remove(fh)
        r = subprocess.run(('git', 'fetch', 'origin'), cwd=clone,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        check('a FAILED fetch still exits non-zero (fixture sane)',
              r.returncode != 0, r.stderr)
        check('...and it CREATES FETCH_HEAD anyway, so its age reads as "now" '
              'on a view the fetch did not refresh', os.path.exists(fh),
              'FETCH_HEAD absent -- git behaviour may have changed; re-read '
              'last_fetch_hours() before trusting either instrument')
        set_fetch_age(clone, 5.0)
        rc, out = run_tool(clone, 'list')
        check('...while the success stamp still reports the real 5 hours',
              '5.0 hours ago' in out, out)

        # ── H. unit rendering, in isolation on hand-built inputs ─────────────
        # Disciplines item 5: the lock runs on hand-built values, in its own
        # pass, calling no git at all.
        print('\nH. fetch_age_str -- hand-built values, no git in the loop')
        sys.path.insert(0, os.path.join(clone, 'tools'))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'freshclaim', os.path.join(clone, 'tools', 'sairn_claim.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for hrs, want in ((None, 'AT A TIME THIS CANNOT MEASURE'),
                          (0.0, '1 minute ago'),
                          (1.0 / 60, '1 minute ago'),
                          (0.5, '30 minutes ago'),
                          (1.0, '1.0 hours ago'),
                          (47.9, '47.9 hours ago'),
                          (72.0, '3.0 DAYS ago')):
            got = mod.fetch_age_str(hrs)
            check('fetch_age_str(%r) -> %r' % (hrs, want), got == want, 'got %r' % got)
        check('a zero-age fetch never renders as "0 minutes"',
              '0 minute' not in mod.fetch_age_str(0.0), mod.fetch_age_str(0.0))
        check('and a good fetch produces no lines at all',
              mod.freshness_lines(True, '', False) == [],
              str(mod.freshness_lines(True, '', False)))
        check('while a bad one produces the banner',
              any(BANNER in ln for ln in mod.freshness_lines(False, '', False)))

        # ── I. THE CONTROLS -- six shapes, each proving its sabotage landed ──
        print('\nI. MUTATION CONTROLS -- reintroduce the defect, seven ways')
        revive_remote(clone, origin)
        git(clone, 'fetch', '-q', 'origin')

        def control(name, anchor, replacement, arm):
            """Patch, assert the patch landed, assert the suite goes RED."""
            try:
                restore, delta = mutate(clone, anchor, replacement)
            except RuntimeError as e:
                check(name + ' -- SABOTAGE APPLIED', False, str(e))
                return
            check(name + ' -- sabotage applied (%+d bytes)' % -delta, True)
            try:
                kill_remote(clone, tmp)
                set_fetch_age(clone, 5.0)
                bites, detail = arm()
                check(name + ' -- and an arm goes RED', bites, detail)
            finally:
                revive_remote(clone, origin)
                restore()

        def arm_check_reports():
            rc, out = run_tool(clone, 'check', 'freshsubject', 'nothing collides')
            return (rc != 4 or BANNER not in out), 'rc=%s out=%s' % (rc, out[:400])

        def arm_list_reports():
            rc, out = run_tool(clone, 'list')
            return (rc != 4 or BANNER not in out), 'rc=%s out=%s' % (rc, out[:400])

        def arm_age_is_fetch():
            rc, out = run_tool(clone, 'list')
            return ('5.0 hours ago' not in out), 'out=%s' % out[:400]

        def arm_claim_proceeds():
            r, out = run_tool(clone, 'claim', 'mutsubject', 'must still attempt')
            git(clone, 'reset', '-q', '--hard', 'HEAD')
            return ('PROCEEDING ANYWAY' not in out
                    or 'NOT CLAIMED' not in out), 'rc=%s out=%s' % (r, out[:400])

        # 1. the original defect verbatim: throw the fetch result away.
        control('1 the fetch result is discarded again',
                '        fetched, ferr = fetch_origin()\n'
                '    subj, task = args.subject',
                '        sh([\'git\', \'fetch\', \'origin\'], check=False)\n'
                '        fetched, ferr = True, \'\'\n'
                '    subj, task = args.subject',
                arm_check_reports)

        # 2. the state is tracked but the exit code folds it back into "passed"
        #    -- PR §1.11's own shape, and the half a script depends on.
        control('2 exit code folds stale back into 0',
                'return 0 if fetched else STALE_RC\n\n\ndef _report_recent_releases',
                'return 0\n\n\ndef _report_recent_releases',
                arm_check_reports)

        # 3. the banner is silenced while everything else stays correct.
        control('3 the banner is silenced',
                "    if fetched:\n        return []\n    age = fetch_age_str",
                "    if True:\n        return []\n    age = fetch_age_str",
                arm_check_reports)

        # 4. the age is read from the tip commit date instead of the fetch --
        #    the gate_column_check 18.7-hour understatement, transplanted.
        control('4 the age comes off a commit date again',
                "    d = sh(['git', 'rev-parse', '--git-dir'], check=False)\n"
                "    if not d:\n        return None",
                "    ct = sh(['git', 'log', '-1', '--format=%ct', 'origin/main'],\n"
                "            check=False)\n"
                "    if ct:\n        return (now() - int(ct)) / 3600.0\n"
                "    d = sh(['git', 'rev-parse', '--git-dir'], check=False)\n"
                "    if not d:\n        return None",
                arm_age_is_fetch)

        # 5. cmd_claim aborts on a stale check -- breaks the 2026-09-04
        #    NOT-CLAIMED contract, which is why F asserts it here too.
        control('5 claim aborts on a stale check',
                '    stale_check = rc == STALE_RC\n    if stale_check:',
                '    stale_check = rc == STALE_RC\n    if stale_check:\n'
                '        return rc\n    if False:',
                arm_claim_proceeds)

        # 6. list goes quiet again -- the copy most likely to be read as a
        #    roster rather than as a verdict.
        # ── THE `\n\n\ndef main` SUFFIX WAS DROPPED FROM THIS ANCHOR ────
        # It went stale the day `cmd_audit` was added: cmd_list stopped being
        # the last function before main(), so the anchor stopped matching and
        # THIS CONTROL STOPPED TESTING ANYTHING. The probe's own count-exactly-
        # once assertion is what surfaced it -- which is the arm working, not
        # failing. Anchoring on position is what rots; the three lines of BODY
        # below are unique on their own (verified: 1 occurrence), and they are
        # the thing the control is actually about.
        control('6 list goes quiet again',
                '    for ln in freshness_lines(fetched, ferr, args.no_fetch):\n'
                '        print(ln)\n    return 0 if fetched else STALE_RC',
                '    return 0',
                arm_list_reports)

        # 7. THE MISTAKE THIS PROBE ACTUALLY CAUGHT, kept as a control so it
        #    cannot come back: read the age off FETCH_HEAD's mtime. A failed
        #    fetch touches that file, so the reported age collapses to "now"
        #    on a view the fetch did not refresh -- understating staleness,
        #    which is the only direction that matters.
        control('7 the age comes off FETCH_HEAD again',
                "    try:\n        with open(os.path.join(d, FETCH_STAMP)) as f:\n"
                "            hrs = (now() - float(f.read().strip())) / 3600.0\n"
                "    except (OSError, ValueError):\n        return None",
                "    try:\n        hrs = (now() - os.path.getmtime(\n"
                "            os.path.join(d, 'FETCH_HEAD'))) / 3600.0\n"
                "    except (OSError, ValueError):\n        return None",
                arm_age_is_fetch)

        # After every control: the tool is byte-identical to the shipped copy.
        with open(os.path.join(clone, 'tools', 'sairn_claim.py'), encoding='utf-8') as f:
            after = f.read()
        with open(TOOL, encoding='utf-8') as f:
            shipped = f.read()
        check('the tool is restored byte-identical after all seven controls',
              after == shipped, 'clone differs from tools/sairn_claim.py')

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n%d passed, %d failed' % (passed, failed))
    if failed:
        return 1
    print('ALL %d ARMS PASS -- a verdict now carries the age of its evidence, '
          'and seven controls bite.' % passed)
    return 0


if __name__ == '__main__':
    sys.exit(main())
