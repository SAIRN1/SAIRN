"""The control for tools/entitlement_freshness_check.py -- both directions.

Run: python tests/entitlement_freshness_control.py

WHY THIS EXISTS, AND IT IS NOT A FORMALITY
-------------------------------------------
The tool it checks shipped with a silent undercount ALREADY IN IT. Its first
version scanned `api/**/*.js`. Git pathspecs match with FNM_PATHNAME, so `**`
requires at least one directory level and **`api/sd-data.js` did not match**. It
reported 4 readers where there are 34 and 1 presence-gate where there are 3 --
no error, no warning, a clean-looking run with a quarter of the answer. That is
the exact failure this platform keeps paying for: a checker that reports a pass
it never performed.

Arm 1 below is that defect, asserted directly. If anyone "tidies" the pathspec
back into a glob, this goes red.

EVERY ARM IS TWO-DIRECTIONAL, because one direction proves nothing:
  * a check that ALWAYS reports passes every "it caught the defect" arm;
  * a check that NEVER reports passes every "it stayed quiet" arm.
So the suite carries both, plus one arm that the tool can reach exit 0 at all
and one that it REFUSES (exit 2) rather than reporting zero when its own
assumption breaks.

Every arm runs in a throwaway git worktree, never this clone.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
TOOL = os.path.join('tools', 'entitlement_freshness_check.py')
LIC = os.path.join('api', '_lib', 'license.js')
DATA = os.path.join('api', 'sd-data.js')
STORE = os.path.join('api', '_lib', 'sd-store.js')
RENDER = os.path.join('api', 'sd-render.js')
COPY = (TOOL, LIC, DATA, STORE, RENDER)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:500]))
    if not cond:
        fails.append(name)


def run(wt):
    r = subprocess.run([sys.executable, os.path.join(wt, TOOL)], cwd=wt,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def presence_count(out):
    for line in out.splitlines():
        if 'PRESENCE-GATED ENTITLEMENT' in line:
            return int(line.split('--')[1].strip().split()[0])
    return 0


def sql_count(out):
    for line in out.splitlines():
        if 'hand-run SQL that writes it' in line:
            return int(line.split(':')[1].strip().split()[0])
    return -1


print('entitlement_freshness_check -- does it report, and does it stay quiet?\n')

wt = tempfile.mkdtemp(prefix='sairn-ent-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    for rel in COPY:
        shutil.copyfile(os.path.join(REPO, rel), os.path.join(wt, rel))

    ORIG = {rel: io.open(os.path.join(wt, rel), encoding='utf-8',
                         newline='').read() for rel in COPY}

    def write(rel, text):
        io.open(os.path.join(wt, rel), 'w', encoding='utf-8',
                newline='').write(text)

    def restore():
        for rel, txt in ORIG.items():
            write(rel, txt)
        for extra in ('sql/_control_writer.sql', 'api/_control_writer.js'):
            p = os.path.join(wt, extra)
            if os.path.isfile(p):
                os.remove(p)

    def once(rel, needle):
        n = ORIG[rel].count(needle)
        assert n == 1, ('fixture invalid: %r matches %d places in %s, not 1'
                        % (needle[:60], n, rel))
        return needle

    # ── ARM 0: THE BASELINE ────────────────────────────────────────────────
    # Without this, an arm that "caught" something cannot be told from a tool
    # that was already reporting everything.
    rc, out = run(wt)
    base_presence = presence_count(out)
    base_sql = sql_count(out)
    check('the shipped tree reports findings (exit 1)', rc == 1, out[-400:])
    # 3 -> 0 on 2026-09-15: the defect this tool was written to find was FIXED
    # at all three sites, so the clean state is the baseline now. That moves the
    # burden onto arm 1, which is the only remaining proof the rule can fire.
    check('...and finds ZERO presence-gated entitlements (the fix landed)',
          base_presence == 0, 'found %d\n%s' % (base_presence, out[-300:]))
    check('...and finds the hand-run SQL writers (>0, not counted as writers)',
          base_sql > 0, 'found %d' % base_sql)

    # ── ARM 1: THE PATHSPEC REGRESSION, ASSERTED DIRECTLY ──────────────────
    # A presence-gate planted in a TOP-LEVEL api/*.js file. Under the original
    # `api/**/*.js` pathspec this file was invisible, so the count stayed put
    # and the tool looked fine.
    #
    # THIS ARM BECAME LOAD-BEARING ON 2026-09-15. The baseline used to carry
    # three real presence-gates, so the rule was known to fire from the
    # baseline alone. They were FIXED, the baseline is 0, and this is now the
    # only thing proving the rule can fire at all -- a check with nothing left
    # to find is indistinguishable from a check that no longer works.
    try:
        write(DATA, ORIG[DATA].replace(
            once(DATA, '  const everSubscribed = !!lic.stripe_subscription_id;'),
            '  const everSubscribed = !!lic.stripe_subscription_id;\n'
            '  const isPaid = !!lic.stripe_customer_id;', 1))
        rc, out = run(wt)
        n = presence_count(out)
        check('a presence-gate planted in a TOP-LEVEL api/*.js is seen (the '
              'pathspec regression)', n == 1,
              'found %d, expected 1 -- if this is 0, the scan is skipping '
              'top-level api files again' % n)
    finally:
        restore()

    # ── ARM 2: THE SQL SPELLING THE SEEDS ACTUALLY USE ─────────────────────
    # `public.license_keys`, which the first regex could not match.
    try:
        write('sql/_control_writer.sql',
              '-- control fixture\nINSERT INTO public.license_keys (key) '
              "VALUES ('X') ON CONFLICT DO NOTHING;\n")
        subprocess.run(['git', '-C', wt, 'add', '-f', 'sql/_control_writer.sql'],
                       capture_output=True)
        rc, out = run(wt)
        n = sql_count(out)
        check('a schema-qualified `public.license_keys` write is counted',
              n == base_sql + 1,
              'sql writers %d, expected %d' % (n, base_sql + 1))
    finally:
        subprocess.run(['git', '-C', wt, 'rm', '-q', '-f', '--cached',
                        'sql/_control_writer.sql'], capture_output=True)
        restore()

    # ── ARM 3: THE TOOL CAN REACH EXIT 0 ───────────────────────────────────
    # A checker that can never say "ok" is a checker nobody can act on. Give it
    # a real in-repo writer AND remove the three presence-gates; it must go
    # green. This is the arm that proves the findings are not unconditional.
    try:
        write('api/_control_writer.js',
              "// control fixture -- a real in-repo writer for license_keys\n"
              "module.exports = async () => fetch(process.env.SUPABASE_URL +\n"
              "  '/rest/v1/license_keys?key=eq.X',\n"
              "  { method: 'PATCH', body: JSON.stringify({ status: 'cancelled' }) });\n")
        subprocess.run(['git', '-C', wt, 'add', '-f', 'api/_control_writer.js'],
                       capture_output=True)
        for rel in (DATA, STORE, RENDER):
            write(rel, ORIG[rel].replace(
                'const isPaid = !!lic.stripe_subscription_id;',
                "const isPaid = lic.subscription_state === 'active';", 1))
        rc, out = run(wt)
        check('a real in-repo writer + no presence-gates -> exit 0', rc == 0,
              'exit %d\n%s' % (rc, out[-500:]))
    finally:
        subprocess.run(['git', '-C', wt, 'rm', '-q', '-f', '--cached',
                        'api/_control_writer.js'], capture_output=True)
        restore()

    # ── ARM 4: A REAL STATE CHECK IS NOT A PRESENCE GATE ───────────────────
    # The false-positive direction on its own. `=== 'active'` asks the mirror a
    # question; `!!id` does not. A rule that flagged both would be noise, and
    # noise is how a real finding gets skimmed past.
    try:
        write(DATA, ORIG[DATA].replace(
            once(DATA, '  const everSubscribed = !!lic.stripe_subscription_id;'),
            "  const everSubscribed = !!lic.stripe_subscription_id;\n"
            "  const isPaid = lic.subscription_status === 'active';", 1))
        rc, out = run(wt)
        n = presence_count(out)
        check('a real STATE check is NOT flagged as a presence gate', n == 0,
              'found %d presence-gates where there should be none' % n)
    finally:
        restore()

    # ── THE TWO FALSE POSITIVES THE FIX ITSELF PRODUCED ────────────────────
    # Both appeared the moment the defect was repaired, which is the worst
    # possible time for a checker to start lying: the count went UP from 3 to 6
    # on a tree that had just been made clean.
    try:
        write(DATA, ORIG[DATA].replace(
            once(DATA, '  const everSubscribed = !!lic.stripe_subscription_id;'),
            '  // a comment that QUOTES the defect: '
            'const isPaid = !!lic.stripe_subscription_id;\n'
            '  const everSubscribed = !!lic.stripe_subscription_id;', 1))
        rc, out = run(wt)
        n = presence_count(out)
        check('a COMMENT quoting the defective expression is not a finding',
              n == 0, 'found %d -- the rule cannot tell code from prose about '
                      'code, which is the esign/design trap' % n)
    finally:
        restore()

    try:
        # `everSubscribed` is the HONEST name for `!!id` and must not be
        # flagged; `isSubscribed` claims a CURRENT state from a fact about the
        # past and must be. The tense is the bug, and this pair is what stops
        # the `ever` exclusion quietly gutting the rule.
        write(DATA, ORIG[DATA].replace(
            once(DATA, '  const everSubscribed = !!lic.stripe_subscription_id;'),
            '  const isSubscribed = !!lic.stripe_subscription_id;\n'
            '  const everSubscribed = !!lic.stripe_subscription_id;', 1))
        rc, out = run(wt)
        n = presence_count(out)
        check('`isSubscribed` IS still caught -- the `ever` exclusion is narrow',
              n == 1, 'found %d, expected 1' % n)
    finally:
        restore()

    # ── ARM 5: IT REFUSES RATHER THAN REPORTING ZERO ───────────────────────
    # Break the assumption the whole tool rests on -- the `out.x = row.y`
    # mapping block. The wrong answer here is exit 0 ("no findings"), which is
    # indistinguishable from a clean repo. Exit 2 is the only honest outcome.
    try:
        write(LIC, ORIG[LIC].replace('out.', 'renamed_out_object.'))
        rc, out = run(wt)
        check('a broken mapping block is exit 2 (COULD NOT RUN), never 0',
              rc == 2, 'exit %d -- "could not check" was folded into an '
                       'answer\n%s' % (rc, out[-400:]))
    finally:
        restore()

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    ok_all = all(io.open(os.path.join(wt, rel), encoding='utf-8',
                         newline='').read() == ORIG[rel] for rel in ORIG)
    check('every subject file is byte-identical after each arm', ok_all,
          'a restore did not land -- later arms tested a mutated file')
    rc, out = run(wt)
    check('...and the tool reports the clean baseline again (0 presence-gates, '
          'exit 1 for the still-open unrevokable fields)',
          rc == 1 and presence_count(out) == 0, out[-300:])
finally:
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)
    print('\n  the throwaway worktree is gone: %s' % (not os.path.isdir(wt)))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
