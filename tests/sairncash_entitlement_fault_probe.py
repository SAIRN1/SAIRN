"""SAIRNcash's entitlement gate must DENY -- gate 4 on the paywall.

Run: python tests/sairncash_entitlement_fault_probe.py

── WHY THIS EXISTS, AND WHY IT COULD NOT EXIST THIS MORNING ────────────────
`docs/MASTER-PLAN.md` gate 4: a guard is known to DENY, not merely to pass.
SAIRNcash read fault 0, and the reason recorded earlier today was specific
rather than an omission: `sairncash.html`'s entitlement gate had NO SUITE AT
ALL, and a mutation probe against an unwitnessed function proves nothing --
every mutation "passes" because nothing was ever watching.

`tests/sairncash_entitlement_gate.js` closed that precondition (14 arms,
written RED against a live bypass). This asks the next question: would that
suite actually go red.

── THE INDEPENDENCE PROBLEM, STATED RATHER THAN IGNORED ───────────────────
I wrote that suite. A probe by the same author shares the author's blind spot,
which is the entire premise of the independent-review rule this platform runs
on, so this file cannot claim the independence a second session would bring.

What it does instead is DERIVE THE MUTATIONS FROM THE SUBJECT, not from the
suite's arm list -- every anchor below was taken by reading
`reverifySubscription()` and `reverifyTrial()` line by line and asking what
each line is load-bearing for, WITHOUT looking at which arms exist. Two of the
five are properties no arm was written for on purpose, which is the only
evidence available here that the derivation was genuinely independent of the
suite: if it had been read off the arm list, those two would not be here.

A second session re-deriving this list would still be worth more than this is.

── EVERY ARM IS A PROPERTY THE PAYWALL RESTS ON ───────────────────────────
Not a mutation chosen because it is easy to make. The gate is
`justPaid || await reverifySubscription() || hasTrial`, so anything that makes
any of those three answer true without a server saying so opens the paid
product to a text editor.

── EVERY ARM RUNS IN A THROWAWAY WORKTREE, never this clone ───────────────
── EVERY ANCHOR IS COUNTED AND EVERY SABOTAGE VERIFIES ITSELF ─────────────
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True,
                      encoding='utf-8', errors='replace').stdout.strip()

HTML = 'sairncash.html'
SUITE = os.path.join('tests', 'sairncash_entitlement_gate.js')
SUBJECTS = (HTML, SUITE)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(wt, suite):
    r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('sairncash -- the entitlement gate must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-cash-ent-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    for _rel in SUBJECTS:
        shutil.copyfile(os.path.join(REPO, _rel), os.path.join(wt, _rel))

    ORIG = {HTML: io.open(os.path.join(wt, HTML), encoding='utf-8', newline='').read()}

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

    def arm(label, edits):
        try:
            for rel, old, new in edits:
                text = ORIG[rel].replace(once(rel, old), new, 1)
                assert text != ORIG[rel], 'sabotage did not apply for arm %r' % label
                write(rel, text)
            for rel, _o, _n in edits:
                on_disk = io.open(os.path.join(wt, rel), encoding='utf-8',
                                  newline='').read()
                assert on_disk != ORIG[rel], 'sabotage did not reach disk for %r' % label
            rc, out = run(wt, SUITE)
            check(label, rc != 0,
                  'the suite still PASSED against the mutation\n' + out[-300:])
        finally:
            restore()

    # ── ARM 0: THE CONTROL ─────────────────────────────────────────────────
    rc, out = run(wt, SUITE)
    check('the shipped tree passes the entitlement suite', rc == 0, out[-400:])

    # ── 1. THE BYPASS COMES BACK ───────────────────────────────────────────
    # The exact defect fixed today: a record with no subscriptionId falling
    # through to the pure client-side check. This is the only arm here that
    # reproduces a shipped bug rather than proposing one.
    arm('the no-identity path falling back to isSubscribed() is caught',
        [(HTML, """  if (!s.subscriptionId) {
    try { localStorage.removeItem('sairncash_sub'); } catch (e) {}
    return false;
  }""",
          """  if (!s.subscriptionId) {
    return isSubscribed();
  }""")])

    # ── 2. THE REFUSED RECORD IS LEFT ON DISK ──────────────────────────────
    # A PROPERTY NO ARM WAS WRITTEN FOR, and one of the two that make this
    # derivation independent of the suite.
    #
    # AND MY FIRST REASON FOR IT WAS WRONG, WHICH IS RECORDED RATHER THAN
    # QUIETLY REPLACED. I wrote that leaving the record meant the next OFFLINE
    # load would believe it again. Traced: it does not. This branch returns
    # false on every load regardless, because the catch that falls back to
    # isSubscribed() is only reachable AFTER a fetch, and a fetch only happens
    # when subscriptionId exists. Removing the record changes no verdict here.
    #
    # THE REAL CONSEQUENCE is that getSub() is read by initFirebase() (:457)
    # and showAccount() (:655) as well as by this gate, so a record the gate
    # has already rejected keeps being returned to them -- an account panel
    # rendering a subscription the paywall just refused. The app holds two
    # contradictory answers about the same fact. Same arm, correct reason.
    arm('a refused record left in localStorage is caught',
        [(HTML, "    try { localStorage.removeItem('sairncash_sub'); } catch (e) {}\n    return false;",
          "    return false;")])

    # ── 3. A SERVER REJECTION STOPS CLEARING THE RECORD ────────────────────
    # Same shape one branch down: the server said no, and the local copy stays
    # to be believed by the next offline load.
    arm('a server rejection that no longer clears the record is caught',
        [(HTML, "    localStorage.removeItem('sairncash_sub');\n    return false;",
          "    return false;")])

    # ── 4. THE NETWORK FALLBACK STOPS CHECKING EXPIRY ──────────────────────
    # The documented offline behaviour is "fall back to the last known REAL
    # expiry" -- a paying customer on a bad connection must not be locked out.
    # Returning true instead turns one failed fetch into permanent access, and
    # a forged record with a real-looking subscriptionId gets it by going
    # offline. The second property no arm was written for.
    arm('an offline fallback that grants access unconditionally is caught',
        [(HTML, "  } catch(e) {\n    return isSubscribed();\n  }\n}\n\n// MANAGE BILLING IS A REAL ACTION NOW",
          "  } catch(e) {\n    return true;\n  }\n}\n\n// MANAGE BILLING IS A REAL ACTION NOW")])

    # ── 5. THE TRIAL SIBLING LOOSENS TO MATCH THE OLD BUG ──────────────────
    # reverifyTrial() is the function that got this right, and it is the
    # comparison the fix rests on. If it drifts to the shape reverifySubscription
    # used to have, the same bypass exists on the trial path instead -- and
    # nothing about the subscription path would show it.
    arm('the trial path falling back to a client-only check is caught',
        [(HTML, "  if (!t || !t.trialToken) return false;",
          "  if (!t || !t.trialToken) return isTrialActive();")])

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    ok_all = all(io.open(os.path.join(wt, rel), encoding='utf-8',
                         newline='').read() == ORIG[rel] for rel in ORIG)
    check('the subject file is byte-identical to the working tree after every arm',
          ok_all, 'a restore did not land -- later arms tested a mutated file')
    rc, out = run(wt, SUITE)
    check('...and the suite is green again on it', rc == 0, out[-300:])
finally:
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)
    print('\n  the throwaway worktree is gone: %s' % (not os.path.isdir(wt)))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
