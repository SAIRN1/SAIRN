# b17 — the six practitioner questions still open, for Michael

**Written 2026-10-16 by hank, batch b17.** Three for a funeral director
(SAIRNlegacy) and three for a practising lawyer or firm administrator
(SAIRNlaw). **Every question below is phrased so it can be read out verbatim**
— that is the point of the file; a question a practitioner has to decode is a
question that comes back with the wrong answer.

**WHAT THESE ARE NOT.** None of them is a bug and none blocks a release that
has not already happened. Each one is a place where the code currently acts on
**my reading of how the trade works**, and where a practitioner's answer would
either confirm it or change a specific named line.

**Every fact in the "what the code does today" lines was re-derived by reading
the file at HEAD on 2026-10-16**, not carried from a handoff.

---

## FUNERAL — SAIRNlegacy

The app's role vocabulary is `owner / director / arranger / prep / office /
apprentice / livery / staff` (`api/_lib/auth.js`, `ROLES_BY_APP.sairnlegacy`).
**Five of those eight names are marked `[CONFIRM]` in the spec and still are**
— a home's own titles win over the spec's — but that is one standing naming
question rather than three, and it is not what these ask.

**Two funeral questions were ANSWERED on 2026-10-15 and are closed:** the
licensed-embalmer tier (recorded as a decision, with an empty
`LEG_PREP_ROOM_RESOURCES` map and a live check, because there is no
preparation-room resource for it to gate yet) and livery's access to dispatches
and the custody log (blocked, with a grant route for personnel above them).
These three are what is left.

### F1 — Does a cremation authorisation need a SECOND named person?

> **"When your home authorises a cremation, does the paperwork need a second
> named, signing person — a second licensed director, a witness, a family
> member — or is one licensed funeral director's signature enough on its own?
> And if a second person is needed, does your state require it, or is it your
> own house rule?"**

**WHY IT MATTERS AND WHAT CHANGES.** A cremation authorisation is the sharpest
irreversible act in the app — there is no undoing it and no amended record that
helps. Today `leg_cremations` is written by `owner` or `director` only and
never by a task role, and **one signature is all the app asks for**
(`api/_lib/leg-roles.js`, the `leg_cremations` row, whose own `why` says the
second-person question "is a state-law question the spec flags and this code
does not answer").

**IF THE ANSWER IS YES**, the change is not a new field — it is a
countersignature lock, and the platform already has one built and shipping:
`api/sv-witness.js` requires a **different** licensed party to countersign
before a controlled-substance entry can be filed. That pattern lifts onto
`leg_cremations` directly.

**WHY I AM ASKING RATHER THAN BUILDING IT.** Whether a second signature is
legally required varies by state and this is a legal reading, not a
preference. Building a lock nobody needs makes the app slower than the paper it
replaces; not building one that is required makes its record useless as
evidence. **Both failures are expensive and only a practitioner can say which
one we are facing.**

### F2 — Is livery invoiced THROUGH the home, or billed direct to the family?

> **"When you use a livery company — drivers, pallbearer staff, the limousine —
> does your home pay them and then bill the family, or do they invoice the
> family directly? And either way, does the livery driver ever need to see a
> price, an invoice or what the family is being charged?"**

**WHY IT MATTERS AND WHAT CHANGES.** `leg_liverybookings` and
`leg_liveryvendors` are currently banded **MONEY** by the vendor-order pattern
(`api/_lib/leg-roles.js`, both rows, whose `why` carries this exact
`[CONFIRM]`). The band decides whether the `livery` role gets any money read at
all.

**IF LIVERY IS BILLED DIRECT**, the `livery` role needs **no MONEY read
whatsoever** and the two rows should be narrowed — a driver who can see what a
grieving family is being charged for a casket is a real problem and nothing in
the app needs it. **IF THE HOME INVOICES AND RE-BILLS**, the band is right as
it stands, because a livery booking IS a purchase order the home owes money on.

**THIS IS ONE WORD IN A TABLE IN EITHER DIRECTION.** I am asking because
guessing wrong in the permissive direction is the kind of mistake nobody
notices until a family does.

### F3 — What can an apprentice NOT sign, and who has to be present?

> **"Your apprentices — interns, resident trainees, whatever your state calls
> them — what are they actually not allowed to sign or do without a licensed
> director present? Give me the list the way the state licensing board gives it
> to you, not the way the office works day to day."**

**WHY IT MATTERS AND WHAT CHANGES.** The spec describes `apprentice` as
"licensed-in-training, works under a director, **cannot sign**", and flags that
"the supervision rule is a **legal** constraint, not a UI one". Today the app
implements the spirit of that — `apprentice` gets READ on the regulated band
and no write (`api/_lib/leg-roles.js`, the regulated band rows) — **but
"cannot sign" is not a rule the code expresses anywhere.** There is no concept
of a supervising director attached to an apprentice's action.

**WHAT WOULD CHANGE DEPENDS ENTIRELY ON THE ANSWER**, which is why the question
asks for the board's wording rather than a summary:

* if it is *"an apprentice may do the work, a director must sign the record"*,
  that is the **same countersignature lock as F1** and the two should be built
  together
* if it is *"an apprentice may not touch these specific records at all"*, it is
  a narrowing of named rows and nothing more
* if it is *"a director must be physically present"*, the app **cannot express
  that at all** and should not pretend to — the honest answer is a disclosure,
  not a gate

**AND I AM DELIBERATELY NOT GUESSING WHICH.** A supervision rule modelled
wrongly is worse than one left unmodelled with a note, because the wrong model
*looks* like compliance. That is the class `sairn-decision-gate` exists for.

---

## COUNSEL — SAIRNlaw

The app's role vocabulary is **three names only**: `owner / attorney /
paralegal` (`api/_lib/auth.js`, `ROLES_BY_APP.sairnlaw`). That is the root of
the first two questions.

### C1 — Who in the firm keeps the books, and are they an employee?

> **"Who enters time, raises invoices and reconciles the operating account at
> your firm — is that a member of staff, or an outside bookkeeper or
> accountant? If they are outside the firm, do they log in to your systems
> themselves, or does somebody inside do it for them?"**

**WHY IT MATTERS AND WHAT CHANGES. THIS IS THE ONE I MOST WANT ANSWERED, and
the reason is a sentence from the spec I think is exactly right:** with three
roles, a firm either gives its bookkeeper an `attorney` token — handing a
non-lawyer every matter document and every client file — **or gives a
`paralegal` token the trust ledger. Both are wrong, and today the app offers no
third answer.**

Today `paralegal` has **read and write on `law_timeentries`** and read on
invoices and the operating account, and is **hard-locked out of the trust
ledger and the trust bank statements** (`api/_lib/law-roles.js`,
`LAW_TRUST_LOCKED` — a separate structure consulted after the table precisely
so no per-firm override can ever open it).

**IF THE ANSWER IS "a member of staff"**, the fix is a fourth role,
`bookkeeper`, with money access and no matter-file access. That is a live
`CHECK`-constraint change on `sairnlaw_employee_auth` plus a table row, and it
is a small, well-understood change.

**IF THE ANSWER IS "an outside bookkeeper who logs in"**, it is a different and
larger thing — a scoped external login rather than an employee row — and I
would want to think about it properly rather than reuse the employee table.
**The two answers do not lead to the same build, which is why the question asks
about employment rather than about job titles.**

### C2 — May a paralegal PREPARE a trust disbursement for an attorney to authorise?

> **"When money goes out of your client trust account — IOLTA — may a paralegal
> prepare the disbursement for an attorney to approve and sign, or must an
> attorney do the whole thing from start to finish? And is that a bar rule
> where you practise, or your firm's own policy?"**

**WHY IT MATTERS AND WHAT CHANGES.** Today a paralegal cannot touch trust
money at all: `law_trusttx` and `law_bankstatements` give `paralegal: ''` AND
are hard-locked (`api/_lib/law-roles.js`, `LAW_TRUST_LOCKED`), and
`law_trust_reconcile` is **owner-only** through its own separate gate. b17
added the arms that prove the lock actually holds rather than merely being
written down (`api/b17-trust-lock-hard.test.js`) — **so this refusal is now a
tested, deliberate position, which is exactly why it is worth asking whether it
is the right one.**

**IF A PARALEGAL MAY PREPARE BUT NOT AUTHORISE**, the shape is a
**two-stage** disbursement — prepared by one role, authorised by a
bar-admitted one — and that is the same countersignature pattern as F1 and C3,
a third time. **IF AN ATTORNEY MUST DO THE WHOLE THING**, the current refusal
is correct and should stay exactly as it is.

**THE SPEC'S OWN SENTENCE ON THIS IS THE REASON IT IS A QUESTION AND NOT A
PREFERENCE:** "Whether a paralegal may PREPARE a trust disbursement for an
attorney to authorise is a **bar-rules question, not a preference**." I am not
qualified to answer it and the app should not quietly imply an answer either
way.

### C3 — Which acts require a bar-admitted person, by name?

> **"Which things in your practice can only be done by an admitted lawyer —
> giving advice, signing a filing, authorising money out of trust, anything
> else? I want the list, because I want the software to refuse the others
> rather than trust whoever is logged in."**

**WHY IT MATTERS AND WHAT CHANGES.** SAIRNvet already encodes exactly this
idea: `PRESCRIBER_ROLES` (`api/sv-auth.js`) is `{ owner, dvm }` and exists
because **a controlled-substance entry is a legal act by a licensed person**,
not because it is sensitive. The equivalent here would be
`{ owner, attorney }` — and **SAIRNlaw has no such constant.** Its access
decisions are per-resource, so "this act needs a licensed person" is currently
expressed only by which rows a paralegal happens to be denied.

**WHY THAT DISTINCTION IS NOT PEDANTRY.** A per-resource denial and a licensure
tier look identical today and diverge the moment a fourth role is added — which
is precisely what C1 may cause. Add `bookkeeper` with no licensure tier in
place and every "attorneys only" decision has to be re-derived from scratch,
one row at a time, by whoever adds it. **Adding the tier BEFORE the role is
cheap; adding it afterwards means re-reading nineteen rows and hoping.**

**AND THIS QUESTION IS ASKED LAST ON PURPOSE.** C1 and C2 are about specific
decisions; this one is about whether the app should carry the CONCEPT at all.
If the answer is short and obvious — advice, signatures, trust disbursements —
it is one constant and three call sites. If it is long or
jurisdiction-dependent, it is a disclosure rather than a gate, and I would
rather know that before building one.

---

## What this document does NOT claim

* **No practitioner has been asked anything.** These are six questions, not six
  findings.
* **Nothing here is a defect.** Every line of code named behaves as designed;
  what is open is whether the design matches the trade.
* **The two answered funeral questions are not re-opened** — the embalmer tier
  and livery's dispatch access were decided 2026-10-15 and are recorded in
  `api/_lib/leg-roles.js` with their reasoning.
* **No state statute, bar rule or licensing-board requirement was read for
  this document.** Every "varies by state" is an admission of what I do not
  know, not a summary of what I checked.
* **The three/three split is a judgment about what is worth a practitioner's
  time**, not a count of every open `[CONFIRM]`. The five SAIRNlegacy role
  NAMES and SAIRNlaw's `staff` title are still marked `[CONFIRM]` in the specs
  and are deliberately left out: they are one naming conversation, and a home
  or firm's own titles win over the spec's whatever we decide here.
