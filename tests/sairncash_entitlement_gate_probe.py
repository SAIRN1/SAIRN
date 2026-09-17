"""tests/sairncash_entitlement_gate.js must REFUSE a forged entitlement.

Run: python tests/sairncash_entitlement_gate_probe.py

reverifySubscription() IS THE ONLY THING STANDING BETWEEN A TEXT EDITOR AND A
PAID PRODUCT. Its own comment, in the source, says so:

    Re-verifies against the real subscription state once per app load --
    closes the "forged localStorage grants permanent free access" gap a pure
    isSubscribed() check (client-only, no server round-trip) can't close on
    its own.

That is a security claim, and until 2026-09-15 NOTHING DROVE IT: three files
mentioned sairncash.html and none executed the function. The suite exists
because the claim had no evidence.

The suite is the right shape -- it EXTRACTS the functions from the page rather
than reimplementing them, because a reimplementation tests a copy that agrees
with the original exactly until the day it does not. So a mutation to
sairncash.html is a mutation to what ships, and these arms are the only thing
that reads it.

THE MUTATIONS ARE THE WAYS A CLIENT-SIDE ENTITLEMENT GATE STOPS BEING ONE, and
all four of the first are things a person could do while tidying:

  * the missing-subscriptionId branch stops refusing, which is the forgery the
    whole function exists for -- a record with `valid:true` and a far-future
    expiry and NO id;
  * the refused record is left in place rather than removed, so the next load
    re-reads it and isSubscribed() -- which BELIEVES a forged record, and the
    suite asserts that it does -- lets it through;
  * a server that says invalid is treated as valid;
  * the network fallback resurrects an EXPIRED record, turning a documented
    degrade-gracefully path into permanent free access after one offline load;
  * the gate stops calling the server at all and becomes the client-only check
    it was written to replace.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairncash_entitlement_gate.js')
APP = 'sairncash.html'

MUTATIONS = [
    ("1. THE FORGERY THE FUNCTION EXISTS FOR. A stored record with no "
     "subscriptionId stops being refused, so `{valid:true, expiresAt:2099}` "
     "typed into localStorage is permanent free access -- and it never reaches "
     "the server, so nothing else can catch it",
     APP,
     "  if (!s.subscriptionId) {\n    try { localStorage.removeItem('sairncash_sub'); } catch (e) {}\n    return false;\n  }",
     "  if (!s.subscriptionId) {\n    return isSubscribed();\n  }"),

    ("2. the refused record is REFUSED BUT NOT REMOVED. The gate returns false "
     "once and the forged record survives, so every later read -- including "
     "isSubscribed(), which the suite asserts BELIEVES a forgery -- still sees "
     "it. A refusal that leaves the evidence in place is a refusal that has to "
     "win every time",
     APP,
     "  if (!s.subscriptionId) {\n    try { localStorage.removeItem('sairncash_sub'); } catch (e) {}",
     "  if (!s.subscriptionId) {\n    try { /* removed */ } catch (e) {}"),

    ("3. a server answer of INVALID is treated as valid. The round-trip still "
     "happens, the request is in the network tab, and the answer is discarded "
     "-- call-and-ignore on the one call that decides whether the product is "
     "paid for",
     APP,
     "    if (data.valid) { saveSub(data); return true; }",
     "    if (data) { saveSub(data); return true; }"),

    ("4. the NETWORK FALLBACK resurrects an EXPIRED record. Falling back to the "
     "last known real expiry is documented and deliberate -- a customer offline "
     "should not lose the app -- but returning true regardless turns one "
     "offline load into permanent access",
     APP,
     "  } catch(e) {\n    return isSubscribed();\n  }",
     "  } catch(e) {\n    return true;\n  }"),

    ("5. the gate stops asking the server AT ALL and becomes the client-only "
     "check it was written to replace. The function still exists, still returns "
     "a boolean, and its comment still claims the round-trip",
     APP,
     "    const res = await fetch('/api/sairncash/verify', {method:'POST', "
     "headers:{'Content-Type':'application/json'}, body: "
     "JSON.stringify({subscriptionId: s.subscriptionId})});",
     "    const res = { json: async () => ({ valid: true, "
     "expiresAt: s.expiresAt, subscriptionId: s.subscriptionId }) };"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='the SAIRNcash entitlement gate -- the suite must refuse a forged '
              'localStorage grant'))
