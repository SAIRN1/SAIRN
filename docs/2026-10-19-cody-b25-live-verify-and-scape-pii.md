« b25 — the live check b24 was missing, the SAIRNscape PII retier that was owed since 2026-10-05, and one standing document that had gone stale in the direction that costs a session

**cody, b25, 2026-10-19.** Four items. Items 2, 3 and 4 write new logic or a
standing rule, and each carries its one-line concept **above** the thing it
produced. Item 5 (the B6-class check) is **not started, by instruction**.

---

## 0. Methodology, since it is item 1

**Every item below that writes new logic states its concept in one line before
the code exists, and the concept lives in the file it governs rather than only
here.** Two of this batch's three findings were only findable because the
concept was written first: an arm that sends a *valid* payload cannot see an
ordering defect, and that is visible the moment you write down what the arm is
supposed to establish.

---

## 1. ITEM 2 — the live verification. CLOSED, and the controls are what made it mean anything

### The concept

> **A change to a response shape is not done until the destination is queried
> back, so read `rf_locations` through the real endpoint with a real session
> and assert `is_default` on the rows that actually come out of it.**

### Result: the shape IS on the deployed endpoint

```
C1 provisioned:true ............................................. ok
C2 at least one row came back ................................... ok
C3 default_location_id present (pre-dates b24, so a deploy tell) . ok
A1 EVERY row carries is_default ................................. ok
A2 ...and every one is a BOOLEAN ................................. ok
A3 is_default agrees with default_location_id -- COMPUTED, not
   stamped to a constant ........................................ ok
6 checks run, 0 failed      EXIT=0
```

`docs/b25-logs/live_verify_rf_locations_is_default.py`, re-runnable.

**THIS IS THE CHECK b24's OWN REPORT NAMED AS ITS GAP**, and the reason it
mattered is not bureaucratic: every b24 arm reads `api/sd-data.js` and
`sairnroofing.html` **off disk**. This repo has a recorded incident where a
Vercel deploy failed, production kept serving the **last successful build**, and
several pushes reported clean while the live site stayed on old code. A
source-level suite is green against a tree nobody is serving and cannot tell.

### THREE THINGS THE CONTROLS CAUGHT, AND WITHOUT THEM THIS WOULD HAVE BEEN A FALSE PASS OR A FALSE FINDING

**(a) THE REGISTRY WAS EMPTY.** The first run came back `provisioned: true` with
**zero rows**, so arm C2 went red and **refused to let the A-arms be read at
all**. "`is_default` was not found" over an empty list is satisfied for ever and
says nothing about the response shape. The platform's Verification Discipline
names the method for exactly this state: a lookup returning *"nothing here"* is
**ambiguous**, and neither answer may be reported without seeding one real
record and re-running.

> **THE SEED CONCEPT:** an empty registry makes an absence unattributable, so
> the verifier seeds ONE synthetic location through the real write path, reads
> it back through the real read path, asserts the flag, and then **deactivates
> it** — leaving a named inactive row rather than silently mutating demo data.

**WHAT IS LEFT BEHIND IS NAMED, NOT HIDDEN:** one row on the demo/audit licence
`RF-AUDIT-2026`, id **`LOC-B25-VERIFY`**, name *"b25 live verification — safe to
delete"*, **deactivated** at the end of the run and **queried back** to confirm
`active=False` rather than trusting the write's exit code. SAIRNroofing has no
delete path for a location — that is a fact about the app, not a choice made
here, which is why it is deactivated rather than removed.

**(b) A SECOND CONTROL SEPARATES "THE CHANGE IS BROKEN" FROM "THE DEPLOY IS
OLD".** `default_location_id` has been on this response since **2026-09-16**,
long before b24. If it were present while `is_default` was absent, the deployed
build simply predates b24 — a **deploy** question, not a code one. Reporting
those two as the same thing is what C3 prevents, and no amount of re-reading the
source could have distinguished them.

**(c) THE is_default:TRUE CASE WAS NOT EXERCISED LIVE, and the verifier says so
in its own output.** No row in that registry carries the sentinel id, and
creating one would change what the demo tenant renders as *"Main"*. The TRUE
branch is covered at source level by `api/_lib/location-scope.test.js` arm E and
`tests/sairnroofing_default_location_from_server.js` arms B1/C1. **Stated rather
than implied**, because "6 of 6 green" over a one-row registry is a weaker claim
than it looks.

### AND A STANDING DOCUMENT HAD GONE STALE IN THE DIRECTION THAT COSTS A SESSION

`docs/2026-09-03-demo-credentials.md` says, under *"One licence does not
exist"*:

> `RF-AUDIT-2026` returns `401 INVALID_LICENSE`, which means
> `sql/sairnroofing_audit_license_seed.sql` was written and **never run**.

**Measured today: it returns 200 with a session token.** The seed has since been
run. That sentence would have stopped this item before it started — *"there is
no usable SAIRNroofing licence, so the live check cannot be done"* — and the
only reason it did not is that the verifier tried the login anyway and read the
answer instead of the document.

**CORRECTED IN THAT FILE, with both the old claim and the new measurement kept.**
`RF-PINNACLE-2026` was tried in the same run and still answers **401
INVALID_CREDENTIALS**, so the section is not emptied: one of its two licences is
genuinely still unusable and the other is not.

---

## 2. ITEM 3 — the SAIRNscape `customers` PII retier, and the ordering arm that was missing

### 2.1 The retier: B → A on both axes, and it had been owed for two weeks

`docs/CRITICALITY-TIERS.md` line 535 now carries `customers` at **A / A**.

**IT WAS CORRECTLY NOT TAKEN IN 2026-10-05 AND THAT IS WORTH KEEPING.**
`api/sd-data.js`'s `SD_SESSION_GATED` entry says in terms: *"THE RETIER IS OWED
AND IT IS NOT MINE TO MAKE: hank holds docs/CRITICALITY-TIERS.md under a live
claim."* The gate was deliberately shipped **ahead of** the register with that
comment as the explanation — the right call, and the thing a reader needs in
order to trust the next one. **That paragraph is struck through rather than
deleted**, because it is the record of why the two disagreed for two weeks.

**The axes, stated separately because they move independently.**
Confidentiality **B → A**: the row's own basis cell already read *"A CUSTOMER's
NAME, PHONE, EMAIL AND STREET ADDRESS"* — the **basis was corrected on
2026-09-30 and the LETTER was not**, and the letter is what the 2026-10-05 gate
sweep read when it stopped at Tier A. **Integrity is untouched and is still
genuinely B.** The **tier follows to A** because this register takes the worse
axis, which is how `sd_sms_log` is already carried in that file.

**AND IT BREAKS A STATED CLASS DECISION, WHICH IS A FINDING AND NOT
BOOKKEEPING.** The struck-through cell held this row at B **on a CLASS** shared
with `bld_suppliers`, `sf_vendors`, `leg_clergy` and `dnt_vendor_contacts`.
**Those four are NOT retiered here.** Each needs its own individual read, and
retiering four rows off one row's decision is precisely the class-default
reasoning this register keeps correcting. **They now disagree with `customers`,
and that is open work — §4 below routes it.**

**The row was rebuilt WHOLE**, never split on a pipe: 663 → 663 lines, pipe
count **7 → 7**, the row one physical line, and **every other line in the file
asserted byte-identical** afterwards by the inserter rather than checked by eye.

### 2.2 Both lists carry it, measured rather than assumed

```
api/sd-data.js:1505   SD_SESSION_GATED  'customers': ['read', 'write']
api/sd-data.js:1842   SD_GATE_APP       'customers': 'sairnscape'
```

**The pair is the point.** A resource added to `SD_SESSION_GATED` without an
`SD_GATE_APP` entry resolves to `'stonedesk'`, and then **every correctly
signed-in SAIRNscape crew lead is refused FORBIDDEN** — the failure mode that
pair of lists exists to prevent, and it is already documented at both sites.

### 2.3 The write path: 403 is already live, and the arm that would notice if it stopped being

**THE CONCEPT:**

> **An unauthenticated write to a session-gated resource must be refused by the
> GATE before the handler body reads the payload, so it answers 403 and not the
> handler's own 400 — a 400 proves the gate did not fire and discloses the
> validation rules to a caller who has not signed in.**

**MEASURED LIVE, on `SCP-DEMO-2026` with no session token:**

```
customers    read   -> 403 FORBIDDEN
customers    write  (id-less payload)  -> 403 FORBIDDEN     <- the 2026-10-05 defect, gone
customers    write  (valid payload)    -> 403 FORBIDDEN
invoices     read / write              -> 403 FORBIDDEN     <- control
scp_quotes   write                     -> 403 FORBIDDEN     <- control
```

So the **400 the 2026-10-05 note records is gone** and the gate fires before the
body. The controls are what make that a measurement rather than a coincidence.

**BUT NOTHING WOULD HAVE NOTICED IF IT CAME BACK, AND THAT IS THE REAL FINDING.**
The existing suite's write arm sends `{id: 'X-1', customer_id: 'C-1'}` — a
**valid** payload — so it answers 403 whether the gate runs before or after
validation. **The ordering is only observable with a payload the body would
refuse.** `api/sd-data-scp-session-gate.test.js` now carries one arm per gated
resource sending `{}`, asserting **403 and `code: FORBIDDEN`**. 80 → **92 arms**.

**The payload is deliberately EMPTY** because every gated resource validates
*something* — an id, a `customer_id`, a date — so `{}` is refused by all twelve
handler bodies and one arm covers the list without encoding each validator's
rules.

### 2.4 Ablated, both legs, and the discriminating mutation is the whole claim

`docs/b25-logs/ablate_b25_gate_order.py`:

```
                                                  PRE-REPAIR      POST-REPAIR
G3 CONTROL, unmutated copy                        exit 0          exit 0
G1 a payload check for customers placed
   BEFORE the gate                                ACCEPTED        REFUSED, and ONLY by
                                                  (unprotected)   the empty-payload arm
G2 CONTROL, customers removed from
   SD_SESSION_GATED                               valid arm only  BOTH write arms red
```

**G1 IS THE CASE THAT SEPARATES THE NEW ARM FROM THE OLD ONE.** Under a body
check placed before the gate, the **pre-existing** write arm stays **GREEN** —
it sends a valid payload and gets its 403 either way. Only the empty-payload arm
goes red. Removing the gate entirely (G2) turns both red and therefore proves
the new arm *runs*, not that it was *needed*; G1 proves it was needed.

**THE CONTROL REFUSED TWICE BEFORE IT PASSED, AND BOTH REFUSALS WERE REAL.** The
temp tree lacked `tests/lib/fn_span.js` and then `sairnscape.html`, both of which
the suite reads. Each time the harness reported **CONTROL FAILED — nothing below
is attributable** and stopped. Without the control, two rounds of "REFUSED"
verdicts would have come from a copy that **never executed a single arm** —
which is b23's and b24's experience with a different missing dependency each
time, and the argument for the control running first every time.

**AND THE HARNESS'S OWN LABELLING WAS WRONG ON THE FIRST PRE RUN.** It applied
the POST expectation to both legs, so the PRE leg printed G1 and G2 as *"NOT AS
EXPECTED"* when both were behaving exactly as a pre-repair suite must.
Expectations are per leg now. **A harness that calls the correct pre-repair
result a failure is reporting on its own expectations rather than on the
subject** — the same class as b24's silent clobber, in the labelling instead of
the setup, and the fourth such defect in three batches.

---

## 3. ITEM 4 — the scrutiny-flags deadlock: the rule existed and stated only half of itself

**THE CONCEPT:**

> **A file the GATE ITSELF wrote during a refused push is bookkeeping this
> session owns and must be COMMITTED on every round; only a file another
> session has declared may be stashed — because stashing the gate's own write
> leaves the tree dirty against the very rebase the gate's refusal asks for.**

**`docs/SAIRN-PROCESS-RULES.md` §3.5 ALREADY PRESCRIBED THE LOOP and already
said what to do when the hook-written file belongs to somebody else: stash it,
do not commit it.** What it did not say is the **complement** — the more common
case, where nobody else declares it. A reader carried the correct **no** across
to their own file, and that is how b24 spent four rounds inside the loop §3.5
itself names.

**MEASURED, b24:** `git pull --rebase origin main` exited **128** —
*"cannot pull with rebase: Your index contains uncommitted changes"* — on a tree
whose **only** modification was the gate's own `scrutiny-flags.json` write, and
the refusal that produced that write had asked for exactly that rebase.

**AND A STASH IS WORSE THAN DIRTY, WHICH IS THE PART THAT IS NOT OBVIOUS.** Those
rows are keyed **per COMMIT**. A stash held across a rebase keys them to shas
that no longer exist — a ledger entry pointing at nothing. b24 took one stash to
break the loop, found its rows superseded, and dropped it: the right sequence,
two rounds later than committing would have been.

**THE TEST, IN ONE QUESTION:** *is this file in anybody else's declared FILES
list?* Check `sairn_claim.py list` rather than assuming. **No → commit it every
round. Yes → stash it and name it in the handoff. The file is not what decides;
the claim is.** Landed as an addition to §3.5 rather than a new section, because
a second rule saying nearly the same thing is the duplication this platform
penalises.

**AND IT WAS FOLLOWED THIS BATCH**, not only written down — see the report's
STATUS for the round-by-round account.

---

## 4. Open work this batch created or carried

### 4.1 → FOUR TIER ROWS NOW DISAGREE WITH `customers`, AND IT IS A READ EACH

`bld_suppliers`, `sf_vendors`, `leg_clergy`, `dnt_vendor_contacts`. All four sat
in the same class the `customers` row was held at B on, and that class reading is
now struck through for one member and standing for the other four.

**THE EXACT NEXT STEP, and it is deliberately not a retier:** read each one's
columns out of its own `sql/` schema and its own write site — **not** out of this
register and **not** out of the `customers` decision — and record a tier per row
with the columns quoted. **Retiering four rows off one row's decision would
recreate the class-default reasoning that produced the original error.** Two of
the four may well be genuinely B: a supplier's company contact is not the same
population as a residential landscaping customer's home address.

### 4.2 → `LOC-B25-VERIFY` is an INACTIVE row on `RF-AUDIT-2026`

Left deliberately, named here and in the verifier's own output, deactivated and
queried back. SAIRNroofing has no delete path for a location. **Anybody with
database access may delete the row; nothing depends on it.**

### 4.3 → THE is_default:TRUE CASE IS STILL UNEXERCISED LIVE

Covered at source level in two suites. Exercising it live means creating a
registry row carrying the sentinel id on a demo tenant, which changes what that
tenant renders as *"Main"*. **Not done, and the reason is recorded rather than
the omission being silent.**

### 4.4 → ITEM 5, THE B6-CLASS CHECK: NOT STARTED, BY INSTRUCTION

Still blocked on a real precision number from a sample rather than more design.
The scope stands at §3 of `docs/2026-10-19-cody-b24-sweep-continued.md`.

---

## 5. What is NOT done

- **No B6-class check**, by instruction.
- **No sweep continuation this batch** — b24's 85 non-cody candidates are still
  unread and still not counted as clean.
- **`sairnscape.html` was NOT touched.** fourth holds it under a live claim for
  a contrast pass. Nothing in item 3 needed a client change: `customers` is read
  in `scpSyncFromServer()`'s resource loop post-login and written once
  post-login, both already carrying the session.
- **No live render of anything.** Items 2 and 3 are live **endpoint** checks,
  which is a different and narrower thing than a rendered-page check.
