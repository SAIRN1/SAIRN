# Hank inventory — batch 8, 2026-10-05

Thirteen items. This file is written as each lands, not at the end, so a
session that dies halfway leaves a true partial record rather than nothing.

---

## 1. `family_mar` had no caller gate at all — H1 #877

**Premise at HEAD: HELD.** `api/sd-data.js`, resource `alf_family_contacts`.
`action === 'read'` at `:11506` resolves `ALF_FAMILY_READ_ROLES` and then the
caller's assigned residents from `alf_clients`, and 403s a resident that is not
theirs. `action === 'family_mar'` at `:11566`, sixty lines below it in the same
handler, did **neither**. It checked `famLib.familyMarView()` — the *contact's*
consent — and shipped the MAR.

**The consent check was standing in for an authorisation check.** That is the
defect in one sentence, and it is why it survived review: there *was* a check
on the path, it was just answering a different question. `familyMarView()`
answers "may this FAMILY CONTACT see anything", which is about the contact.
Nothing asked "may this EMPLOYEE read this resident's MAR", which is about the
session. Any authenticated session on the licence — a `med_aide` or an
`activities` employee with no resident assigned to them at all — could pass any
`contact_id` and receive that resident's full medication administration record.

**The fix, in two halves, because the resident is not knowable up front.**

1. `:11604` — role and assignment scope resolved **before** the contact is
   fetched. A narrow caller with an empty scope is `403 FORBIDDEN` and never
   reaches the query. Lookup-then-authorise was the tempting order and it is
   wrong: it answers "does this contact_id exist on this licence" to a caller
   who may not ask anything at all, which is the existence oracle `read`'s own
   comment already refuses.
2. `:11648` — the stored contact row's `resident_id` checked against that
   scope. `403 FORBIDDEN`, deliberately **distinct from `NO_SUCH_CONTACT`**, so
   the two answers are never collapsed into one oracle. The id comes off the
   stored row, never off the payload — a caller-supplied `resident_id` is a
   parameter somebody edits.

### FLAGGED, NOT FIXED: `ALF_FAMILY_READ_ROLES` includes `billing`

`:11501` — `roleSet({ owner: true, billing: true, nursing: true })`. A
**billing** role is in the broad set that now reaches a **medication
administration record**, with no assignment required. On a clinical record that
is arguable, and I did not narrow it.

**Deliberately not my call in this change.** The whole defect being fixed is a
gate that disagreed with its sibling. Fixing it by introducing a *second*
disagreement — `family_mar` admitting a narrower set than `read` on the same
resource — would leave the handler in the same class of inconsistency one layer
down, and would do it silently, under a commit whose subject is "add the
missing gate". It is a separate decision with a separate owner: whether a
billing role should see clinical detail at all, on this resource and on the
`read` path it already reaches today. Logged here so it is a decision somebody
makes rather than a default nobody noticed.

### Verification

`tests/sd_data_family_mar_gate.js`, new. Drives the **real handler** with auth,
licence and `fetch` mocked — not a reimplementation, which would have passed
against the unfixed code.

    node tests/sd_data_family_mar_gate.js      EXIT=0    10 passed, 0 failed

**Ablation, the number that makes the case.** The same test against
`git show HEAD:api/sd-data.js`, byte-unmodified:

    EXIT=1    4 passed, 6 failed
    FAIL A1  unassigned med_aide got the MAR
    FAIL A2  activities assigned to R2 got R1's MAR   <- the real attack
    FAIL A3  ...and not even as a FORBIDDEN
    FAIL C1/C2/C3  no gate in the source
    ok   B1/B2/B3  the authorised paths — unchanged

The three B arms staying green through the ablation is the half that matters
as much as the six failures: without them the "fix" could be *deny everything*
and every A arm would still pass.

### A false pass I found in my own test, and it was the worse half

C1 failed and C2 passed, and **C2 was the bug**. The source anchor was the bare
string `action === 'family_mar'`, which occurs **twice** — once in the action
allow-list at `:11448` (`action === 'read' || action === 'write' || action ===
'family_mar'`) and once on the branch itself at `:11566`. So `split(...)[1]`
returned the text *between* them, which is **`read`'s body**. C1 failed
honestly — no `marBroad` in `read`. C2 passed on **`read`'s own
`assigned_employee_id` query**: a green arm that never touched the code it
names, in a test written specifically to prove that code exists.

Fixed by anchoring on the branch statement `if (action === 'family_mar')` and
asserting the match count is **exactly 1** (new arm C0, which exits before
C1–C3 run if the anchor is ambiguous). This is the UNIQUENESS guard shape from
`sabotage_control_check` — `count(anchor) != 1` rather than `anchor in src` —
and it is here because the weaker shape had already cost one false pass in this
file's first run.

### Regression

Each exit code read on its own line, immediately after the process, never from
a pipeline's last element:

    tests/sairncare/test-alf-mar.js                 EXIT=0
    tests/sairncare_transport_refusal.js            EXIT=0
    tests/sd_data_unconfirmed_write_review_probe.js EXIT=0
    tests/role_maps_have_no_prototype.js            EXIT=0
    tests/exec_role_gate.js                         EXIT=0
    tools/role_gate_invariants.js                   EXIT=0
    tests/sd_data_dental_provider_scope_probe.py    EXIT=0
    tests/sd_data_food_temp_unevaluated_probe.py    EXIT=0
    tests/sd_data_mech_credentials_probe.py         EXIT=0
    tests/sd_data_numeric_guards_probe.py           EXIT=0
    tests/sd_data_sb_void_role_probe.py             EXIT=0
    tests/active_credential_gate_probe.py           EXIT=0
    tests/alf_append_only_probe.py                  EXIT=0

`node --check api/sd-data.js` EXIT=0 before and after.

### Live verification: COULD NOT TELL, and that is not a pass

Pushed as `8246d8ba` (reseated after two rebases; the register cites that sha).
`tools/sairn_http.py` against the real deployment:

    POST https://sairn.vercel.app/api/sd-data
      {action: family_mar, resource: alf_family_contacts, ...}
    -> 401 {"error":{"code":"NO_LICENSE","message":"Missing bearer license key"}}

**That proves the endpoint is live and refusing. It proves nothing about the
gate**, because the unauthenticated refusal is identical on the old code — it
fires before either branch is reached. Driving the actual gate needs a
sairncare licence key AND an employee session token for a narrow role, which
this session does not hold. So: deployment reachable, fix **NOT live-verified**.
Recorded as a third state rather than folded into the green above.

### Observed, not caused by this change

Every arm of the new test prints:

    sd-data: active-credential re-check DID NOT RUN for app "sairncare"
    (NO_ACTIVE_CHECK) on alf_family_contacts/family_mar. The request was
    allowed on the token alone.

That is the handler's own disclosure firing because the test mocks auth, and it
fires identically on the unfixed code in the ablation. Not a regression and not
in scope here, but it is the right warning in the right place and worth not
mistaking for noise later.

---

## 2. `scp_designs` carried boilerplate while its twin had been read — hover seq 878

**Premise at HEAD: HELD, and re-derived rather than accepted.** The hover
auditor's entry 878 (log `C--Users-marsh-Documents-SAIRN-hover`, severity
moderate) says `scp_designs` still carried the 178-character *"Classified by
the stated B rule rather than individually read"* boilerplate while
`grd_designs` — functionally identical — had been read and moved to **A/B** on
2026-09-23. I re-read both at HEAD before touching the register, because a
routed finding is a claim to verify.

**Verified in the app, not inferred from the finding:**

| | `grd_designs` (sairngrounds) | `scp_designs` (sairnscape) |
|---|---|---|
| send function | `sendDesignToQuote()` `:2500` | `scpSendDesignToQuote()` `:3218` |
| quote gated on approval | `if(!rec\|\|!rec.approved)` refuse | `:3220`, same refusal, same string |
| approval printed on the quote | `lines.push('Design approved by '+…)` | `:3223`, same, plus the Design Walk id |
| prices anything | no — every line `a:0` | no — `:3222`-`:3223`, every line `a:0` |
| target of the write | `grd_quotes` (Tier A) | `scp_quotes` (Tier A) |

Both halves of `grd_designs`'s A verdict — **it gates quote creation** and
**the approval attribution is printed on a customer-facing quote** — are true
of `scp_designs` field for field.

**Applied:** `scp_designs` **B → A on integrity, confidentiality stays B**, with
the evidence written out rather than stamped with a group name. App rollup
`sairnscape` 12 | 2 | 10 → 12 | **3** | 9, `scp_designs` added to the RE-TIERED
list.

**An obligation this creates, written into the row rather than left implied.**
`scp_quotes`'s own cell states the SAIRNscape gating stopping rule as *"Tier A,
not these two names"*. `scp_designs` is now a third Tier A SAIRNscape resource
still authorised by the **licence key alone**. Arming that gate is a handler
change needing its own both-directions suite and its own live verification —
the same shape `invoices` and `scp_quotes` each got — so it is **OPEN and
named**, not quietly absent.

### The headline the promotion broke, which is the guard working

    criticality_tier_check.py   EXIT=1   PROBLEMS:2
      HEADLINE  file says 391/274/117/0, rows say 391/275/116/0
      HEADLINE  "The B tier is 117 rows" -- rows say 116

Both re-derived from the checker's own `RESOURCE_ROWS` / `TIER_A`, not adjusted
by one. **Tenth recorded drift of that sentence, and the first I caught in the
same minute I created it.**

**And the stale figure nothing checks.** The same sentence ended *"That is 64%
Tier A"* — against 274/391, which is **70%**. The two counts beside it are
re-derived on every edit by a guard; the ratio computed from them is not, so it
had drifted furthest and silently. Corrected to 70% with the division written
out. Folded into this edit deliberately rather than split off: it is the same
sentence, and leaving a false ratio inside a line whose whole discipline is
re-derivation would be the defect the line exists to prevent.

### Verification

    python tools/criticality_tier_check.py        EXIT=0   PROBLEMS:0  (TIER_A 275)
    python tools/md_table_check.py CRITICALITY..  EXIT=0   434/434 rows, 0 malformed
    python tools/citation_line_drift_check.py --app sairnscape.html --prefix scp_
                                                  EXIT=0   DRIFTED 0
    python tests/run_criticality_tier_probe.py    EXIT=1 while uncommitted ->
                                                  re-run after commit, below

The probe's failing arm is `this clone's own register is untouched`, a
dirty-tree guard; it is expected to be red while the edit is unstaged.

**One false citation caught by that drift check and removed before it landed.**
My first draft of the row cited the `scp_quotes` row as `` `:544` ``, a
*document* line number. `citation_line_drift_check.py` reads a bare `:NNN` in a
`scp_` row as a line in `sairnscape.html`, so the register would have carried a
citation pointing at an unrelated line of the app. Replaced with a named
cross-reference and the reason written beside it.

### A tool blind spot found while verifying, logged not fixed

`citation_line_drift_check.py` returned **INCONCLUSIVE** for all six
`scp_designs` citations: *"no storage constant declared for it, and no literal
`setItem('scp_designs')` or `st('scp_designs')` write either"*. The write does
exist — `sairnscape.html:2915` is `scpLd('scp_designs',[])` and the saves go
through `scpSt`. The tool looks for `st(` and `setItem(` and does not know about
per-app prefixed accessors like `scpSt`/`scpLd`, so every SAIRNscape row is
unanchorable to it. **INCONCLUSIVE is the honest answer and the tool gives it**
— it is not reporting a pass — but a whole app that can never be anchored is a
coverage hole worth naming. Not fixed here: widening that tool is a change to a
measurer and takes its own fixtures and a before/after count.

---

## 3. The unrouted hover findings — 14, not 10, and now 0

**The dispatched number was stale before I started and I did not adjust it.**
`python tools/hover_routing_gap_check.py` reported **14** unrouted, over
**1439** log entries — the queue said 10 against 1404. Both logs had grown.
Re-measured rather than reconciled.

    BEFORE   EXIT=1   1439 entries, UNROUTED 14
    AFTER    EXIT=0   1449 entries, UNROUTED 0

### The claim question, answered before any write

`docs/SAIRN-OPEN-WORK-INDEX.md` is cc's by convention and the dispatch said to
route around it if held. **It was not held.** `sairn_claim.py check` reported
cc's claim on it **EXPIRED 8.6h ago**, and `sairn_status.py` reported that
session **DEAD** — `CLAUDE_PID 66660 no longer exists`, last row written
2026-10-05T18:14. Expired *and* dead is the platform's own definition of
takeable, so I took it **by name in the claim string** rather than rewording my
task to avoid the matcher. The claim's first publish attempt **failed** (dirty
tree, `git rebase` refuses); the tool said so out loud and said the claim was
therefore invisible to every other clone. Committed, re-ran, published.

### Six FIXED in `docs/CRITICALITY-TIERS.md`

Every citation re-derived at HEAD. **Several of the routed entries' own line
numbers had already drifted**, so nothing was pasted.

| seq | Resource | What was wrong | Outcome |
|---|---|---|---|
| 875 | `leg_facilities` | *“no PII”* — the seed stores `{type:'Staff', name:'Maria Chen', notes:'Funeral Director'}` and bookings key on `facility_id` alone | basis corrected, **B holds** |
| 872 | `sv_examrooms` | *“no PII”* — a named vet beside a named patient, and **not seed-only**: the editor writes both from live inputs | basis corrected, **B holds** |
| H2 538 | `sdn_vendors` | *“no PII”* — `saveVendor()` writes `contact_name`, `phone`, `email` | basis corrected, **B holds** |
| 884 | `sc_specialty_checklists` | never individually read | **confirmed B/B with evidence** + named trigger |
| 884 | `sc_specialty_checks` | never individually read | **confirmed B/B with evidence** + named trigger |
| 708/714 | `sf_bottle_fills`, `sf_documents`, `sf_ceremonial_items` | citations | corrected — see below |

`criticality_tier_check.py` **EXIT=0 PROBLEMS:0**, `TIER_A` **275 before and
after**: nothing moved tier. These are basis corrections, which is the harder
half to notice and the easier half to skip.

### The one worth reading: a function name that was wrong twice

`sf_bottle_fills` has now been re-anchored **three times**.

1. **2026-09-28** cited `sfRecordBottleFill()`. `grep` returns **zero hits**,
   and always did.
2. **2026-09-30** caught that, found the app's own comment names
   `sfBottleFill` — **also not a function; it appears exactly twice and both
   are comments** — and concluded *“the honest citation is a line range and not
   a function name.”*
3. **That conclusion is also wrong, and that is this pass's finding.** The
   write does sit in an anonymous `.then(function(res){…})` inside
   `reader.onload`, so the *innermost* scope has no name. But the enclosing
   named entry point is **`sfEstimateFill()` at `sairnfreedom.html:4834`**,
   called by the button at `:1106`. A durable anchor was available the whole
   time. **Two passes looked at the wrong depth, and the second then wrote the
   absence down as a fact** — which is worse than the original typo, because a
   stated impossibility stops the next reader from looking.

The cell also carried a **spliced-in duplicate fragment** (`…so method is
always 'Automatic, from photograph' writes {productId, …} with method recorded
as…`) and a trailing `RE-ANCHORED 2026-09-28` sentence that contradicted its
own body. Both removed.

**And hover's own proposed replacement text would have been wrong.** Entry 714
supplied paste-ready text naming `sfBottleFill()`. Pasting it would have
swapped one non-existent identifier for another — in a correction whose entire
subject is a non-existent identifier. Caught only because I re-derived instead
of pasting.

### Four ROUTED as index rows, with file:line

- **SAIRNdesign** — the generic `SDN_RESOURCES` write branch stores
  `data: payload` raw, no `storedBlob()`, across all 18 resources; 12 carry
  client identity or money, each named with its own save site. (This is also
  queue item 8; the code half is not done.)
- **StoneDesk** — `sd_pb` / `sd_pb2` / `sd_pb3`, purge-exempt keys with **zero**
  read and write sites, `stonedesk.html:3581`. Re-measured at HEAD. **One fact
  the finding did not have:** the identical `keepKeys` line is copy-pasted into
  four archived apps, so it is a propagated line, not a one-off.
- **Tooling → hover2** — `classify_remote()`'s credential mislabel (seq
  710/722) and the `tools-hover2/` skill-store divergence (seq 723). **Owner
  is hover2 and only hover2**: a build agent must not write into that scope,
  so these are routed and explicitly not fixable from here.
- **Platform** — a ✅ row recording the six cells applied above, so the work is
  visible to the next reader rather than only to `git log`.

### Three findings were ALREADY APPLIED and had simply never been routed

Checked before writing anything, which is why they cost nothing:
`grd_boq_rates` (seq 403 finding 1) is **already Tier A**, re-tiered
2026-09-22 — the same day the finding was logged. `leg_cremations`,
`leg_custodylog` and `leg_deathrecords` (seq 403 finding 2) are **already
A/A**, same date. `sdn_clients` (H1 seq 538) is **already A/A**. All three were
counted as unrouted purely because no index row names them — **the gap was in
the record, not in the work**, which is a different problem from the other
eleven and is worth not conflating with them.

### The insert guard that fired

The row insert anchors on the table header and asserts the match count. It
came back **2**, not 1: the index carries a second table with an identical
header, the frozen *“Added by the handoff-reading pass, 2026-08-24”* one near
the end. A bare first-match would have been right by luck; a bare positional
insert would have been wrong in silence. Asserted explicitly instead, plus a
line-number sanity bound.

    python tools/md_table_check.py docs/SAIRN-OPEN-WORK-INDEX.md
      EXIT=0   831/831 rows, 0 malformed, 0 uncheckable
