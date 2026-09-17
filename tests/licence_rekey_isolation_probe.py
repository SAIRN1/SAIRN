"""tests/licence_rekey_isolation.js must REFUSE -- this code DELETES CUSTOMER DATA.

Run: python tests/licence_rekey_isolation_probe.py

THE MOST DANGEROUS GUARD ON THE PLATFORM, by its own suite's account, and
NEITHER of its two failure modes throws:

  1. IT WIPES TOO MUCH. Every SAIRN app is served from the same origin and
     shares one localStorage -- a real browser checked in August held 201 keys
     across eight apps. A prefix of `sd` rather than `sd_` matches `sdn_clients`
     and deletes a design studio's client list from inside StoneDesk.
     stonedesk.html's own Layer 27 comment records that as the reason its scoped
     wipe exists at all, so it is not hypothetical.
  2. IT WIPES TOO LITTLE, OR NOT AT ALL, and the next licence to open the app on
     that device sees the previous customer's records as its own.

Thirteen apps carry the guard. The suite lifts it out of each real app file
rather than reimplementing it, which is the right call and means a mutation to
ONE app's constants is a mutation to what is actually shipped.

AND THE SUITE'S OWN HEADER RECORDS A NEAR-MISS WORTH MORE THAN ANY ARM IT
CONTAINS: its first harness used a Proxy, whose ownKeys trap must report the
target's own non-configurable properties, so it threw, the guard's try/catch
swallowed it, EVERY WIPE SILENTLY BECAME A NO-OP, and the "nothing was deleted"
assertions all passed. The first version of that harness made the code under
test look SAFER THAN IT IS. A suite that can do that once can do it again, which
is the argument for measuring it rather than trusting it.

FIVE MUTATIONS, and the probe threw two of its own candidates away:

  * the underscore leaves the prefix -- driven on SAIRNcode's `sc_`, which
    collides with SAIRNscape's `scp_jobs`. Aimed there AFTER planting it on
    sairnlaw first and finding `law_` -> `law` collides with nothing in the
    shipped key space: an EQUIVALENT MUTANT, discovered by planting rather than
    by reasoning;
  * the fingerprint key stops being excluded, so the wipe deletes the key that
    identifies the licence and every later open looks like a first run;
  * the ownership test inverts, wiping all twelve other apps and sparing its
    own -- the widest blast radius available;
  * the live scope assertion is disarmed;
  * the guard stops being CALLED while remaining defined.

AND ONE MORE WAS WITHDRAWN, in the list below with its reason: making the
SHARED PLATFORM KEYS app-owned changes nothing, because every shared key begins
`sairn_` or `s_` and no app prefix is a prefix of those, so the trailing
`indexOf(prefix) === 0` already rejects them.

THE DISARMED TRIPWIRE WAS SILENT AND IS NOW FIXED. The suite asserted the scope
assertion's VALUE, and a disarmed tripwire is still `true`. It now asserts the
CONTENT: that the expression drives the app's own ownership test over at least
one FOREIGN key expected false and one OWN key expected true. Structural, not
keyword-based -- keys are classified by the app's real prefix.

"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'licence_rekey_isolation.js')
APP = 'sairnlaw.html'
CODE = 'sairncode.html'

MUTATIONS = [
    ("1. THE UNDERSCORE LEAVES THE PREFIX, on the pair that actually collides. "
     "SAIRNcode's 'sc_' becomes 'sc', which claims SAIRNscape's `scp_jobs` -- "
     "sc_/scp_ is one of the two pairs the underscore exists to separate, and a "
     "widened prefix is how StoneDesk ate a design studio's client list. Aimed "
     "at sairncode rather than sairnlaw deliberately: 'law_' -> 'law' collides "
     "with nothing in the shipped key space and is an EQUIVALENT MUTANT, which "
     "this probe found out by planting it",
     CODE,
     "var SC_OWN_PREFIX = 'sc_';",
     "var SC_OWN_PREFIX = 'sc';"),

    ("2. the FINGERPRINT KEY stops being excluded from ownership, so the wipe "
     "deletes the very key that identifies which licence owns this device. "
     "Every subsequent open then looks like a first run and adopts silently -- "
     "the guard disabling itself, permanently, on its first use",
     APP,
     "  if (k === LAW_LIC_FP) return false;",
     "  if (false) return false;"),

    # ── MUTATION 3 WAS WITHDRAWN, AND IT IS A SMALL FINDING IN ITSELF ──────
    # "the SHARED PLATFORM KEYS become app-owned" is an EQUIVALENT MUTANT.
    # Removing `if (LAW_SHARED_KEYS.indexOf(k) !== -1) return false;` changes
    # nothing, because every shared key begins `sairn_` or `s_` and no app
    # prefix is a prefix of those -- so the trailing `indexOf(prefix) === 0`
    # already rejects them. The exclusion is defence in depth against a prefix
    # nobody has, and it is currently unreachable.
    #
    # That is worth writing down rather than fixing: it is correct code, it
    # costs nothing, and it becomes load-bearing the day an app takes a prefix
    # like `s_`. Counting it as a caught mutation would have been a fabricated
    # arm; counting it as a GAP would have been a fabricated finding against a
    # suite that is right.

    ("4. the ownership test INVERTS -- it now claims every key that does NOT "
     "start with the prefix. A re-key wipes all twelve other apps and leaves "
     "its own data untouched: the widest blast radius available, and only the "
     "arms asserting what was NOT deleted can see it",
     APP,
     "  return String(k).indexOf(LAW_OWN_PREFIX) === 0;",
     "  return String(k).indexOf(LAW_OWN_PREFIX) !== 0;"),

    ("5. the LIVE SCOPE ASSERTION is disarmed. It exists so a future widening "
     "refuses at load rather than quietly eating somebody else's records -- the "
     "guard's own tripwire -- and a disarmed tripwire is indistinguishable from "
     "one that never fired",
     APP,
     "var LAW_SCOPE_OK = ['sd_jobs', 'leg_cases'].every(function (k) { return lawIsOwnKey(k) === false; })",
     "var LAW_SCOPE_OK = true && ['sd_jobs'].every(function (k) { return true; })"),

    ("6. the guard stops being CALLED at the activation path while remaining "
     "defined. The dormant-code failure exactly: the exposure is untouched, the "
     "function is right there in the file, and anything grepping for it finds "
     "it",
     APP,
     "  if(!lawLicenceGuard(k)){",
     "  if(false){"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='the licence re-key guard -- the suite must refuse a wipe that '
              'takes too much, too little, or the wrong app'))
