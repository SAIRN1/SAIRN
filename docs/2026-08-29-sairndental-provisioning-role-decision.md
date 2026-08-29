# SAIRNdental: should more than one role be able to provision credentials?

**A decision document, 2026-08-29 (Hank). Nothing is built and nothing is
recommended as settled — this lays out what is actually true, what the options
cost, and what I would choose and why.** The call itself is an authorisation
change and should go through `sairn-decision-gate` before anyone writes code.

---

## 1. Why SAIRNdental and not the other three

Four apps have a single provisioning role. SAIRNdental is the worst-placed of
them, and the reason is not the count.

| app | `PROVISIONING_ROLES` | `MANAGEMENT_ROLES` | full role vocabulary |
|---|---|---|---|
| SAIRNdental | `['owner']` | `{owner}` | `owner, frontdesk, provider` |
| SAIRNmechanical | `['owner']` | `{owner, admin}` | `owner, admin, sales, tech` |
| SAIRNroofing | `['owner']` | `{owner, admin}` | `owner, admin, estimator, foreman, crew` |
| SAIRNcode | `['admin']` | *(none)* | `admin, coder, biller, auditor` |
| StoneDesk | `['owner','admin']` | *(none)* | `owner, admin, sales, install` |

**SAIRNdental is the only app with no second office-level role in its vocabulary
at all.** Mechanical and roofing each already have an `admin` who runs the shop
without minting identities; widening to them is a one-word change to an existing
role. SAIRNdental's other two roles are `frontdesk` and `provider` — a
receptionist and a clinician. Neither is an obvious deputy principal.

### A code comment that describes a role this app does not have

`api/dnt-auth.js:146-149` reads:

> *Only 'owner' provisions or changes credentials. `'admin'` runs the office but
> does not mint identities — deliberately narrower than StoneDesk, where both
> owner and admin can, because a 20-100 person shop has one principal and the
> blast radius of a mistaken deactivation is the whole company.*

**SAIRNdental has no `admin` role.** `ROLES_BY_APP.sairndental` is
`['owner','frontdesk','provider']`. The reasoning was carried over from an app
that does have one, and it makes the current design look like a deliberate
narrowing from two roles to one when it was never two. **This should be
corrected regardless of which option below is chosen** — it is the kind of
comment that makes a future reader "restore" a role that never existed.

### Live state, read 2026-08-29

`DNT-PINNACLE-2026`: 2 credential rows, **1 active provisioner**. Mechanical and
SAIRNcode are the same shape (2 rows, 1 active). StoneDesk's three licences carry
3/3, 4/2 and 1/1. So three of the five apps are currently one row away from
having no provisioner — not through the API, which refuses, but through any SQL
that touches those rows.

---

## 2. What the exposure actually is, stated narrowly

The failure state is **credential rows exist AND zero of them are both `active`
and hold a provisioning role**. Then `bootstrap` refuses 409 (its existence probe
does not filter on `active`), and `setup` and `set_active` both require an active
provisioner. All three exits shut.

**The API cannot produce this state.** `set_active` requires an active
provisioning caller, re-reads the roster to confirm the caller's own row is still
active, refuses self-deactivation, and refuses to deactivate the last active
provisioner. The count cannot cross 1 → 0 through any API path.

**So widening the role pool is not a fix for the lockout.** It is a fix for a
different, real problem: *what happens operationally when the single owner is
unavailable* — on leave, ill, departed, or simply not at the practice that week.
Today nobody else can add a hygienist, deactivate a departed employee's PIN, or
restore an account. That is an availability and offboarding problem, and it is
worth deciding on its own merits rather than being smuggled in as a safety patch.

The lockout itself is addressed by two things already shipped on 2026-08-29:
`tools/employee_auth_guard_check.py` (no new SQL file can create the state) and
`api/provisioner-health.js` + `tools/licence_recoverability_check.py` (a licence
already in it is reported rather than discovered).

---

## 3. The options

### Option A — leave it. One provisioning role, `owner`.

**For.** It is a genuine security position, not an oversight: in a 20-100 person
practice there is one principal, and the blast radius of a mistaken deactivation
is the whole company. Fewer identity-minting accounts is strictly less attack
surface, and a dental practice holds PHI. Nothing is required: the lockout is now
guarded and detected.

**Against.** The offboarding problem stays. A practice whose owner is away cannot
revoke a departed employee's access — which for PHI is its own compliance
exposure, pointing the opposite way to the argument for A. It also makes the
owner's PIN a single point of failure that the app offers no recovery for.

**Cost to reverse.** None; this is the status quo.

### Option B — add `frontdesk` to `PROVISIONING_ROLES`.

**For.** One-line change, no new role, no schema change, no UI. Front desk is
usually the person who actually onboards and offboards staff in a practice, so it
matches how the office really runs.

**Against.** `frontdesk` is the *least* trusted role in the app and typically the
highest-turnover seat. Giving it the power to mint an owner-equivalent account is
a large jump. It is also not reversible in practice: once practices have granted
it, narrowing it later breaks their workflow, and the accounts it created remain.

**Cost to reverse.** High. Authorisation grants are far easier to widen than to
narrow.

### Option C — add `provider` to `PROVISIONING_ROLES`.

**For.** A provider (dentist) is often a partner in the practice and plausibly a
second principal.

**Against.** Also often *not* — associates and locums are providers too, and the
app cannot tell a partner from a contractor. This grants identity-minting to a
clinical role on the basis of an assumption about practice ownership that varies
per customer. Of the three options that widen, this is the one most likely to be
wrong for a specific practice while looking right in general.

**Cost to reverse.** High, same as B.

### Option D — introduce a new `manager` role, provisioning-capable.

**For.** Says exactly what it means; matches mechanical's and roofing's `admin`,
so the platform converges rather than diverging further. Each practice chooses
whether to use it, so the default posture stays exactly as strict as today and
Option A remains available per customer. The `LAST_OWNER` guard becomes genuinely
reachable rather than quarantined, which means it starts being exercised.

**Against.** The most work: a role added to `ROLES_BY_APP`, the UI role picker,
any `DNT_RESOURCES` gate that enumerates roles, plus tests. It widens the pool
without solving the case a practice never creates one — which, for a small
practice that does not want a second principal, will be most of them.

**Cost to reverse.** Moderate. A role in the vocabulary is hard to remove once
any customer has assigned it, though it can be left unused.

### Option E — a break-glass recovery path instead of widening.

**For.** Targets the actual failure — no way back in — without granting anyone
new day-to-day power. Keeps Option A's security posture intact.

**Against.** **It cannot be built safely with what the app has today**, and this
is the important finding of this section. A licence key is shared with every
employee and is not a secret, so any recovery gated on the licence key alone lets
anyone holding it seize a tenant. Break-glass needs a factor the key-holder does
not have — an email round-trip to the licence's registered `customer_email`, or a
support-operated path. SAIRNdental has no verified-email flow. This is therefore a
larger project than it looks, and pretending otherwise is how it would get built
badly.

**Cost to reverse.** N/A — the cost is in building it correctly.

---

## 4. What I would do

**Option A for now, plus the comment correction — and treat Option D as the
thing to build when a customer actually asks for a second provisioner.**

Reasoning, in order of weight:

1. **The lockout is already addressed**, by the guard and the detector shipped
   the same day. Widening the pool was proposed as a lockout mitigation; it is
   not one, because the API could never reach that state anyway. Making an
   authorisation change for a reason that does not hold is the wrong basis for a
   decision that is hard to reverse.
2. **The real problem — owner unavailable — has not been reported by a customer.**
   SAIRNdental has one demo licence and no production practices. Deciding a
   permissions model now means guessing at how real practices delegate, and B and
   C are both guesses about that.
3. **B and C are cheap to do and expensive to undo.** D is the opposite, and D is
   the one that matches the platform's existing shape.
4. **The comment is wrong today regardless.** `api/dnt-auth.js:146` describes an
   `admin` role that does not exist in this app, and that costs nothing to fix
   and prevents a plausible future mistake.

**What would change my answer:** a real practice reporting that they cannot
offboard someone while the owner is away. That is Option D, immediately — and it
is the scenario worth asking the first SAIRNdental customer about directly rather
than waiting for it to surface as a complaint.

## 5. Explicitly out of scope here

- The other three single-role apps. Mechanical and roofing already have an
  `admin` in the vocabulary, so their version of this decision is materially
  cheaper and should be taken separately, not bundled.
- Any change to `bootstrap`. Softening its existence probe is a different
  proposal and is rejected on its own grounds in
  `docs/2026-08-29-single-provisioning-role-trapdoor-analysis.md` §3.
- The `LAST_OWNER` guard, which is correct and needs no change under any option
  above.
