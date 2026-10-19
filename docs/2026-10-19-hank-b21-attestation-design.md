# The IOLTA reconciliation attestation — design note, b21

**DESIGN NOTE ONLY. No code this batch, deliberately.** b20 recorded Michael's
decision that `paralegal` comes off `LAW_RECONCILE_ROLES` *until the attestation
step exists*, and named the mechanism without building it. This is the design
for that mechanism and nothing in this batch implements it.

**Author:** hank, batch b21, 2026-10-19.
**Precondition it rests on:** `LAW_RECONCILE_ATTESTATION` in
`api/_lib/law-roles.js` already carries `required_by_rule: true`,
`implemented: false`, the rule basis, the gap and the candidate. This note is
that `candidate` field expanded into a design, not a new idea.

---

## THE ONE-LINE CONCEPT

> **A completed three-way reconciliation becomes an ATTESTED record only when a
> bar-admitted person signs a hash of the exact comparison that was run — so
> "the three legs agree" and "a lawyer has attested that they agree" are two
> different stored facts, and the app can never present the first as the
> second.**

Everything below follows from that sentence, and the sentence is the thing to
attack first if the design is wrong.

---

## 1. GOALS

1. **Make the attestation a RECORD, not a claim.** The output must be a row
   that names *who* attested, *when*, and *to what exact figures* — recoverable
   years later by a bar auditor without re-running anything.
2. **Bind the signature to the CONTENT, not to the event.** The thing signed is
   a hash of the reconciliation's own result — the three leg balances, their
   as-of dates, the client-subledger sum, the verdict and the negative-balance
   list. A signature bound only to "a reconciliation happened" can be presented
   against a different reconciliation, which is the same defect class the C2
   lock's `contentHash(resource, payload)` already closes for disbursements.
3. **Re-open the delegation that b20 withdrew.** Once an attestation exists,
   `paralegal` goes back onto a *prepare*-shaped grant: a paralegal RUNS the
   reconciliation, a bar-admitted person ATTESTS the result. That is what Rule
   5.3 supports and what Rule 1.15 requires, and it is the arrangement real
   firms actually run.
4. **Make the UNATTESTED state visible and named.** The Trust Accounting panel
   must distinguish *reconciled* from *reconciled and attested* on screen. A
   reconciliation with no attestation is a legitimate intermediate state, not
   an error — and it must not render as completion.
5. **Reuse the one mechanism rather than growing a second.**
   `api/_lib/countersign.js` + `api/_lib/countersign-endpoint.js` already
   implement prepare / countersign / status / open, token hashing, content
   hashing, single-use, expiry, the self-signature refusal and the
   computed-stage ladder. A third copy of that is a third thing that can drift.

## 2. NON-GOALS

1. **NOT a correctness checker.** An attestation records that a qualified
   person *looked and signed*. It does not and must not imply the figures are
   right. `api/_lib/countersign.js`'s header already carries the argument: a
   witness attests that somebody looked, not that they were right — and the
   research behind the lock is explicit that even independent double-review has
   a measured, non-zero failure rate. **The UI copy must say this.** Building
   an attestation that reads as a correctness guarantee would be the
   wrong-model-that-looks-like-compliance failure F3 names.
2. **NOT a periodicity enforcer.** Several state bars mandate reconciliation
   *monthly* or *quarterly*. This design does not decide, schedule or nag about
   cadence. Cadence is per-state, it is the same per-state-config problem F3
   answered with a config, and folding it in here would make one mechanism
   answer two unrelated questions.
3. **NOT a new credential.** No new header, no new token type, no new auth
   path. It runs on the existing licence + `X-SD-Auth` session and
   `LAW_BAR_ADMITTED_ROLES`.
4. **NOT a block on reconciling.** A paralegal must still be able to RUN the
   comparison without an attorney present. Gating the arithmetic behind a
   signature would make the feature unusable in exactly the firms that delegate
   it, and the duty the rules impose is on the REVIEW, not on the arithmetic.
5. **NOT a retroactive backfill.** Reconciliations run before this ships have
   no attestation and must never be shown as attested. They are
   `attested: false` forever, and that is the honest answer.
6. **NOT an amendment path.** An attestation is never edited or deleted. A
   corrected reconciliation is a NEW comparison with a NEW attestation, the
   same append-only discipline `law_trusttx` already enforces.

---

## 3. ALTERNATIVES CONSIDERED

### Alternative A — REUSE the countersignature lock, with a new profile (RECOMMENDED)

Add a third `api/*-countersign.js`-style profile — or a new locked resource on
the existing `api/law-countersign.js` profile — for a `law_trust_attestation`
record, in `MODE_ALWAYS`:

* **prepare** — the person who ran the reconciliation (owner, attorney, *or*
  paralegal once re-granted) stages the attestation. The `payload` is the
  reconciliation RESULT, so `contentHash('law_trust_attestation', payload)`
  binds the token to those exact figures.
* **countersign** — a DIFFERENT, bar-admitted employee signs. The existing
  `sairnlaw_countersign_not_self` CHECK makes a self-attestation
  unrepresentable in the database, and `..._complete` makes a half-written
  signature unrepresentable.
* **the write** — `requireCountersignature()` recomputes the content hash and
  refuses if it differs by a byte, then the attestation row lands.

**Why this wins.** Every property the goals ask for already exists and is
already tested: content binding, single-use, expiry, self-signature refusal in
three places, and a server-computed stage so a panel cannot render "signed" for
a spent-and-expired record. `api/b18-countersign-lock.test.js` (59 arms) and
`api/b20-countersign-open.test.js` (15 arms) already hold that machinery, and
b20's `open` action means the attorney's "needs your authorisation" queue
serves this for free.

**MODE_ALWAYS and not MODE_PREPARED_ONLY, and this is the sharpest decision in
the note.** C2's lock lets a bar-admitted person write `law_trusttx` directly
with no token, because C2 asked only whether a paralegal may prepare. **Here the
asymmetry would defeat the purpose**: the point of the record is that a
bar-admitted person reviewed a reconciliation *somebody produced*, and under
`MODE_PREPARED_ONLY` an attorney who ran it themselves would attest their own
work with no second party and no token — which is exactly the shape b20
withdrew a grant to avoid. SAIRNlegacy's F1 lock is `MODE_ALWAYS` for the same
reason and its schema says it in as many words: *a rule the owner is exempt
from is not "the paperwork needs a second named person"*.

**The cost, stated:** a one-attorney firm cannot produce two bar-admitted
signers, so under `MODE_ALWAYS` a solo practitioner cannot attest at all. **That
is a real blocker and it is the one open question this note cannot close** — see
§6.

### Alternative B — a self-attestation flag on the reconciliation row

Add `attested_by` / `attested_at` / `attested_role` columns to a reconciliation
record and let a bar-admitted caller set them in the same request that runs the
comparison.

**Rejected, and the reason is not effort.** It makes the attestation an
assertion by the *saver* rather than a signature by a *reviewer*: one request,
one party, no binding to the figures, nothing that cannot be re-sent against a
later comparison. It would satisfy a checkbox audit and satisfy nothing a bar
association actually asks. It also reproduces, one layer up, the pre-2026-09-17
`bridge_data` defect — a row keyed on what the caller said rather than on what
was proved. **It does, however, solve the solo-practitioner problem
completely**, which is why it is recorded rather than dismissed: if §6 is
answered "a solo attorney may attest their own reconciliation", Alternative B
becomes the honest shape for that case and the design becomes a hybrid.

### Alternative C — an append-only attestation LOG with no lock

Write every attestation to an append-only audit table
(`sairnlaw_audit_log_schema.sql` already exists) and enforce nothing.

**Rejected as the primary mechanism, kept as a companion.** A log records what
happened; it does not stop the thing the rules care about (an unreviewed
reconciliation presented as complete). But Alternative A **should** write to
that log as well — the token table is the control and the audit log is the
history, and they answer different questions. This is the one alternative that
is additive rather than exclusive.

### Alternative D — do nothing and keep the disclosure

`LAW_RECONCILE_ATTESTATION` already carries the gap honestly, and the app
refuses the delegation rather than faking the control.

**Recorded because it is the current state and it is defensible.** The cost is
that SAIRNlaw cannot support the ordinary division of labour in a law firm, and
that is a product gap rather than a compliance one. **It is the right answer
until §6 is decided**, which is precisely why b20 shipped it.

---

## 4. CROSS-CUTTING CONCERNS

### 4.1 Security

* **The signer's standing is read from the ROW, not from whoever saves it.**
  `countersign_role` exists so the write path re-derives qualification from the
  column rather than from the caller — the property `api/_lib/countersign.js`
  already documents. An attestation must claim the SIGNER's standing, never the
  saver's.
* **The role must be re-checked against `LAW_BAR_ADMITTED_ROLES` at attest
  time, not at prepare time.** A session outlives a demotion by up to its TTL,
  and `countersign-endpoint.js`'s `activeCaller()` already reads the role from
  the employee row for exactly this reason.
* **The attestation token is a bearer credential and must never be listed.**
  b20's `open` action returns no token and no token hash, on the argument both
  SQL schemas make in their own words: *a readable table of live tokens is a
  table of signatures waiting to be borrowed*. The same must hold here.
* **`verifySessionToken(token, license_hash, 'sairnlaw')` with the third
  argument.** Guardian check 28 and the Semgrep rule exist because `owner` is a
  valid role in several apps' vocabularies; a two-argument call here would let
  a genuine session from another SAIRN app attest a law firm's trust
  reconciliation.
* **Fail CLOSED.** If the attestation store cannot be read, the answer is
  "could not tell", never "attested". `isMissingTable()` already maps that to
  503 NOT_PROVISIONED rather than to a pass.
* **The reconciliation endpoint stays OWNER-ONLY until cody applies the routed
  derive.** This design assumes `api/sd-data.js:18804` reads
  `lawRoles.LAW_RECONCILE_ROLES` instead of its hand-written
  `roleSet({ owner: true })`. **It does not today** (re-measured against origin
  in b21), so building this against the current gate would produce an
  attestation mechanism only the firm owner could ever reach.

### 4.2 Data

* **One new table, `sairnlaw_trust_attestations`**, keyed on `license_hash` +
  an attestation id, carrying: the content hash of the reconciliation, the three
  leg balances as INTEGER CENTS, their as-of dates, the verdict
  (`AGREES`/`DISAGREES`/`PARTIAL`/`CANNOT_RECONCILE`), the negative-balance
  list, `prepared_by`/`prepared_role`, `attested_by`/`attested_role`/
  `attested_at`, and `created_at`.
* **INTEGER CENTS, never floats.** `api/_lib/law-trust-reconcile.js` already
  computes in cents and `sairnlaw.html` already sends `client_total_cents`, so a
  rounding difference here could manufacture the discrepancy the record exists
  to settle.
* **The figures are STORED, not re-derived.** An attestation that points at a
  live query attests to whatever that query returns *today*. The row must carry
  the numbers as they were when signed, or it is not a record of anything.
* **GRANTS: `revoke all` first, then `select, insert` — NO UPDATE, NO DELETE.**
  Stronger than the countersign token tables, which need UPDATE to mark a token
  spent. An attestation is never amended; a correction is a new row. And the
  leading `revoke all` matters for the reason
  `sairnlegacy_settings_schema.sql`'s own grants section argues: without it the
  table inherits TRUNCATE from the platform default ACL, and TRUNCATE here
  would erase every attestation a firm has ever recorded, silently, in one
  statement.
* **RLS `for all using (false) with check (false)`**, service-role only, same as
  every other tenant-scoped table.
* **A CHECK that the attester is not the preparer**, in the database as well as
  the application — the third place, for the same reason the countersign tables
  carry it: the two application checks live in one process and a future write
  path that forgot them would leave no trace.

### 4.3 Test plan

Written as the plan the build must satisfy, not as a list of things that would
be nice:

1. **Module arms, no transport.** `LAW_RECONCILE_ATTESTATION.implemented` flips
   to `true` and an arm asserts it — so "we know and have not built it" cannot
   decay into "it is fine" in the other direction either. An arm asserts
   `paralegal` is back on `LAW_RECONCILE_ROLES` **and** that the attestation
   profile is `MODE_ALWAYS`.
2. **Handler arms through the real dispatcher**, recorded PostgREST stand-in,
   the `api/b18-countersign-lock.test.js` shape:
   * a paralegal may PREPARE an attestation and the row is pending;
   * a paralegal may NOT attest — 403 naming the bar-admitted route;
   * the SAME attorney who prepared it may not attest it (SAME_PERSON);
   * a token spent once cannot be spent again (ALREADY_SPENT);
   * an expired token is refused (EXPIRED), and the stage reads `expired` even
     when `countersign_employee_id` is set — the signed-then-expired row that
     is the whole reason the stage is computed server-side;
   * a content hash that differs **by one cent** is refused. This is the arm the
     mechanism exists for: the same attestation must not be spendable against a
     different comparison.
3. **THREE NEGATIVE CONTROLS, because a green suite is not evidence:**
   * **ABLATION** — delete the `MODE_ALWAYS` branch and confirm the
     self-attestation arm goes RED. Per ARM, not per exit code.
   * **ABLATION** — delete the content-hash recomputation and confirm the
     one-cent arm goes RED while the others stay green, so one layer was
     removed and not the floor.
   * **CONTROL** — with nothing ablated, the happy path still attests. An
     ablation that breaks the file proves nothing.
4. **SQL negative inserts, in the file, with the expected error code**: a
   self-attestation must violate the CHECK; a half-written attestation must
   violate the CHECK; and a POSITIVE control insert must SUCCEED, because two
   erroring inserts are equally consistent with "the constraints work" and
   "the table rejects everything".
5. **A LIVE probe that exits 2 COULD NOT RUN without credentials**, naming the
   licence it needs — the `tools/alf_facility_role_gate_live_probe.py` shape.
   Every arm above is against a mock, and the deployed gate is UNVERIFIED until
   something drives the real URL. "Could not run" is a third state and is never
   folded into "passed".
6. **A rendered pass on the panel.** The distinction between *reconciled* and
   *reconciled and attested* is a visual property; no static check can see it.

---

## 5. WHAT THIS CHANGES IN THE APP

* `api/_lib/law-roles.js` — `paralegal` returns to `LAW_RECONCILE_ROLES`;
  `LAW_RECONCILE_ATTESTATION.implemented` becomes `true`; the b20 comment block
  recording the withdrawal stays, with the date it was reversed.
* `api/law-countersign.js` — `lockedResources` gains
  `law_trust_attestation: cs.MODE_ALWAYS`. Arm E3 of
  `api/b18-countersign-lock.test.js` asserts that list against
  `LAW_TRUST_TWO_STAGE`, so **that arm will go red and must be re-aimed with
  the new expected answer written down** — not deleted to go green.
* `sql/sairnlaw_trust_attestations.sql` — new.
* `api/sd-data.js` — the `law_trust_reconcile` branch returns the attestation
  stage alongside the verdict. **cody's file.**
* `sairnlaw.html` — the Trust panel shows the attestation stage and the
  not-a-correctness-guarantee sentence.

---

## 6. THE ONE QUESTION THIS NOTE CANNOT ANSWER

**Can a solo practitioner attest their own reconciliation?**

Under Alternative A (`MODE_ALWAYS`) they cannot, because there is no second
bar-admitted employee to sign. That is not an edge case — a large share of real
law firms are one attorney plus staff, and for them the mechanism would make
attestation *impossible* rather than *required*, which is worse than the current
state where it is merely absent.

**The three answers, and they are not equivalent:**

1. **`MODE_ALWAYS` always.** Cleanest control, and it locks out solo firms.
2. **A per-firm setting**, the shape `sairnvet_witness_policy.require_two_person`
   already uses — a firm that can staff a second signer turns it on. **But
   SAIRNlaw's own countersign schema explicitly refused a policy table once
   already**, on the grounds that a legal requirement is not something a
   licensee turns off in Settings. Re-opening that is a decision, not a
   convenience.
3. **A named single-signer mode** where a solo attorney's own attestation is
   recorded AS a single-signer attestation — Alternative B's shape, scoped —
   so the record never claims two parties looked when one did.

**(3) is where the honesty is**, because it changes what the record CLAIMS
rather than weakening what it requires. It is still Michael's call, and it is
the thing to decide before any of this is built.

---

## 7. WHAT THIS DESIGN DELIBERATELY LEAVES ALONE

* **b18's F1/C2 `MODE_*` asymmetry.** Still attack point (a) of the Tier A
  obligation and not re-decided here.
* **Reconciliation cadence.** Non-goal 2.
* **The inert `reconcile` verb.** b21 recorded the decision that it stays
  undeclared and `law_trust_reconcile` + `read` is the only route; this design
  assumes that and does not reopen it.
