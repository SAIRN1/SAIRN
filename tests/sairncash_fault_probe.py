"""SAIRNcash's webhook signature, its ordering guard and its trial retry must DENY.

Run: python tests/sairncash_fault_probe.py

── GATE 4, ON THE LAST VERTICAL IN THE SEAM WITH SUITES ────────────────────
`docs/MASTER-PLAN.md` gate 4: the guards are known to DENY, not merely to pass.
SAIRNcash read **0 resources, 2 attributed suites, 0 traced, 0 fault probes**.

The `0 resources` is accurate and the `2 suites` is not: SAIRNcash owns no entry
in `api/_resources/`, because it is not a licence-gated data app at all -- it is
the consumer subscription product, and its surface is five bespoke endpoints
under `api/sairncash/`. There are FIVE suites, not two; the attribution counts
by path and does not reach them. Every one is green.

── WHY THIS APP IS DIFFERENT FROM EVERY OTHER ONE IN THE SEAM ──────────────
The others hold a customer's records. This one takes a customer's MONEY, and
two of its guards are the only thing between a stranger and a paid plan:

  * THE WEBHOOK SIGNATURE. `stripe.webhooks.constructEvent` is what makes the
    request body trustworthy. Without it, anybody who knows the URL can POST a
    `customer.subscription.updated` saying they are active and the mirror
    believes it. There is no other authentication on that endpoint -- by
    design, because Stripe cannot present one.
  * THE ORDERING GUARD. Stripe does not guarantee delivery order, so a RETRIED
    OLD event arriving after a newer one rolls the mirror backwards: a
    cancelled customer shown as active, or a real dunning flag cleared. It
    fails in both directions and neither shows on a screen.
  * THE TRIAL RETRY. A 409 means the row exists. Only a caller who can produce
    the SAME idempotency key gets the token back -- that distinction IS the
    security argument for a key rather than an email lookup, and losing it
    hands somebody else's trial credential to anybody who knows their address.

── EVERY ARM IS A GUARD WITH A WRITTEN REASON AT ITS SITE ──────────────────
Each mutation below inverts a property the source states in a comment beside
itself. None is a failure mode invented to have something to mutate.

── EVERY ARM RUNS IN A THROWAWAY WORKTREE, never this clone ────────────────
── EVERY ANCHOR IS COUNTED AND EVERY SABOTAGE VERIFIES ITSELF ──────────────
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()

WEBHOOK = os.path.join('api', 'sairncash', 'stripe-webhook.js')
VERIFY = os.path.join('api', 'sairncash', 'verify.js')
TRIAL = os.path.join('api', 'sairncash', 'trial-start.js')

WH_SUITE = os.path.join('api', 'sairncash', 'stripe-webhook.test.js')
V_SUITE = os.path.join('api', 'sairncash', 'verify.test.js')
T_SUITE = os.path.join('api', 'sairncash', 'trial-start.test.js')
SUITES = (WH_SUITE, V_SUITE, T_SUITE)
SUBJECTS = (WEBHOOK, VERIFY, TRIAL) + SUITES

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(wt, suite):
    r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('sairncash -- the webhook signature, the ordering guard and the trial '
      'retry must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-cash-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    for _rel in SUBJECTS:
        shutil.copyfile(os.path.join(REPO, _rel), os.path.join(wt, _rel))

    ORIG = {}
    for rel in (WEBHOOK, VERIFY, TRIAL):
        ORIG[rel] = io.open(os.path.join(wt, rel), encoding='utf-8', newline='').read()

    def write(rel, text):
        io.open(os.path.join(wt, rel), 'w', encoding='utf-8', newline='').write(text)

    def restore():
        for rel, txt in ORIG.items():
            write(rel, txt)

    def once(rel, needle):
        n = ORIG[rel].count(needle)
        assert n == 1, ('fixture invalid: %r matches %d places in %s, not 1'
                        % (needle[:60], n, rel))
        return needle

    def arm(label, suite, edits):
        try:
            for rel, old, new in edits:
                text = ORIG[rel].replace(once(rel, old), new, 1)
                assert text != ORIG[rel], 'sabotage did not apply for arm %r' % label
                write(rel, text)
            for rel, _o, _n in edits:
                on_disk = io.open(os.path.join(wt, rel), encoding='utf-8',
                                  newline='').read()
                assert on_disk != ORIG[rel], 'sabotage did not reach disk for arm %r' % label
            rc, out = run(wt, suite)
            check(label + '  [' + os.path.basename(suite) + ']', rc != 0,
                  'the suite still PASSED against the mutation\n' + out[-300:])
        finally:
            restore()

    # ── ARM 0: THE CONTROLS, FIRST ─────────────────────────────────────────
    for suite in SUITES:
        rc, out = run(wt, suite)
        check('the shipped tree passes %s' % os.path.basename(suite), rc == 0,
              out[-400:])

    # ═══ DIRECTION 1: ANYBODY WHO KNOWS THE URL GETS A PAID PLAN ═══════════
    #
    # 1. THE SIGNATURE CHECK STOPS CHECKING. constructEvent is replaced by a
    #    bare parse of the body. The endpoint still works perfectly for real
    #    Stripe traffic -- which is exactly why nobody would notice.
    arm('a webhook that parses the body instead of verifying it is caught',
        WH_SUITE,
        [(WEBHOOK, "    event = stripe.webhooks.constructEvent(rawBody, req.headers['stripe-signature'], secret);",
          "    event = JSON.parse(rawBody);")])

    # ═══ DIRECTION 2: THE MIRROR ROLLS BACKWARDS ═══════════════════════════
    #
    # 2. THE ORDERING GUARD NEVER FIRES. A retried old event overwrites newer
    #    state: a cancelled customer shown as active, or a dunning flag
    #    cleared on somebody who is genuinely behind.
    arm('a stale event allowed to overwrite newer state is caught', WH_SUITE,
        [(WEBHOOK, "  if (typeof existingAt === 'number' && typeof m.patch.lastEventAt === 'number' && m.patch.lastEventAt < existingAt) {",
          "  if (false) {")])

    # 3. ...AND THE OTHER DIRECTION, which is not the same bug. A guard that
    #    skips EVERYTHING freezes the mirror at whatever it first recorded --
    #    no error, no write, and a customer whose subscription changes months
    #    ago is still shown on the old plan.
    arm('an ordering guard that skips every write is caught too', WH_SUITE,
        [(WEBHOOK, "  if (typeof existingAt === 'number' && typeof m.patch.lastEventAt === 'number' && m.patch.lastEventAt < existingAt) {",
          "  if (true) {")])

    # 4. THE DUNNING FLAG STOPS BEING SET. past_due and unpaid both mean
    #    Stripe is still retrying the card. Losing the flag means nothing in
    #    the product ever says a payment failed.
    arm('a dunning state that never raises paymentFailed is caught', WH_SUITE,
        [(WEBHOOK, "    patch.paymentFailed = (o.status === 'past_due' || o.status === 'unpaid');",
          "    patch.paymentFailed = false;")])

    # ═══ DIRECTION 3: A LAPSED SUBSCRIPTION READS AS PAID ══════════════════
    #
    # 5. EVERY STATUS BECOMES ACTIVE. `past_due`, `canceled` and `unpaid` all
    #    start returning valid:true, so the app keeps opening for somebody
    #    whose card stopped working.
    arm('a verify that treats every subscription status as active is caught',
        V_SUITE,
        [(VERIFY, "    const active = sub.status === 'active' || sub.status === 'trialing';",
          "    const active = true;")])

    # 6. ...and the inverse: nobody is ever valid. A broken product rather than
    #    a breach, and a suite that only caught the permissive direction would
    #    let it ship to every paying customer at once.
    arm('a verify that treats NO subscription as active is caught too', V_SUITE,
        [(VERIFY, "    const active = sub.status === 'active' || sub.status === 'trialing';",
          "    const active = false;")])

    # ═══ DIRECTION 4: SOMEBODY ELSE'S TRIAL TOKEN ══════════════════════════
    #
    # 7. THE LOOKUP STOPS FILTERING ON THE KEY. Query by EMAIL ALONE and the
    #    trial token goes back to anybody who knows the address. The source
    #    calls that distinction "the whole security argument for a key rather
    #    than an email lookup"; this deletes exactly that.
    #
    #    A FIRST VERSION OF THIS ARM WAS NOT A DEFECT, AND WHICH KIND OF NULL
    #    RESULT IT WAS IS RECORDED RATHER THAN QUIETLY DROPPED. It flipped
    #    `if (idemHash)` to `if (true)`, expecting a keyless caller to reach
    #    the lookup. They do -- and the URL then carries
    #    `idempotency_key_hash=eq.null`, which matches no row, so the caller
    #    still gets ALREADY_EXISTS. The property is defended twice and removing
    #    one layer changes no outcome, so trial-start.test.js was RIGHT to stay
    #    green. A control that fails to break its subject tests nothing, and
    #    the difference between "a coverage gap" and "a bad arm" is exactly
    #    this question, asked before the suite is blamed.
    arm('a trial retry that looks up by EMAIL ALONE is caught', T_SUITE,
        [(TRIAL, "          + '&idempotency_key_hash=eq.' + encodeURIComponent(idemHash)\n", "")])

    # 8. THE KEY-SHAPE REFUSAL GOES AWAY. A short or guessable key is refused
    #    rather than ignored, because a guessable key is a lookup anybody can
    #    perform. Accepting one is the same exposure by a slower route.
    arm('a trial that accepts a short or guessable idempotency key is caught',
        T_SUITE,
        [(TRIAL, "  const idemRaw = req.body && req.body.idempotency_key;",
          "  const idemRaw = (req.body && req.body.idempotency_key) ? String(req.body.idempotency_key).padEnd(24, 'x') : undefined;")])

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    ok_all = all(io.open(os.path.join(wt, rel), encoding='utf-8',
                         newline='').read() == ORIG[rel] for rel in ORIG)
    check('all three subject files are byte-identical to the working tree after '
          'every arm', ok_all,
          'a restore did not land -- later arms tested a mutated file')
    for suite in SUITES:
        rc, out = run(wt, suite)
        check('...and %s is green again on it' % os.path.basename(suite),
              rc == 0, out[-300:])
finally:
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)
    print('\n  the throwaway worktree is gone: %s' % (not os.path.isdir(wt)))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
