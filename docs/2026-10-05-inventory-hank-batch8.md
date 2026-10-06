# Hank inventory — batch 8, 2026-10-05

Written as each item lands, not at the end, so a session that dies halfway
leaves a true partial record rather than nothing.

**The dispatch listed fifteen numbered items; this file has eleven sections,
and the mapping is stated rather than left to be inferred.** Three of the
dispatch's items were the resume instruction, the inventory itself, and the
methodology entry, and two more collapsed into sections written for other
items — `leg_facilities` (dispatch item 7) is inside section 3 because the
same hover entry routed it, and `sdn_vendors`'s register half (part of
dispatch item 8) is there for the same reason. **Nothing was dropped; the
section numbers are not the dispatch numbers.**

| dispatch | here |
|---|---|
| 1 `family_mar` gate | §1 |
| 2 `scp_designs` (#878) | §2 |
| 3 route the unrouted hover findings | §3 |
| 4 `leg_facilities` basis | §3 (same hover entry) |
| 5 `sdn_vendors` / SDN `storedBlob` | §3 register half, §4 code half |
| 6 `sen_settings` accessor | §5 |
| 7 drift backlog, 10+ rows | §6 |
| 8 cp1252 sweep | §9 |
| 9 plan literals + paywall affordance | §8 |
| 10 gate-parity check | §7 |
| 11 population methodology | §10 |
| 12 inventory | §11 |

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

---

## 4. The SDN generic write branch stored the payload raw — hover H2 seq 529/538

**Premise at HEAD: HELD.** `api/sd-data.js`, the single generic
`SDN_RESOURCES` write branch, built its upsert body as **`data: payload`** —
the caller's entire object, with no `storedBlob()` call. Any key the caller
invented was persisted verbatim into the jsonb column, **including a forged
`license_hash`, `app_id` or `p_license_hash`**, and echoed back on read beside
the real columns that contradict it.

**One branch, eighteen resources — which is what makes it worth a commit.**
That branch is a parametrised pair covering all 18 SAIRNdesign resources, and
that design is right: one fix is one fix. The same property makes one omission
eighteen omissions, twelve of them on rows carrying client identity or money.

**LATENT, NOT LIVE, and that is stated rather than used as a downgrade.** Every
read path resolves tenancy from the real `license_hash` **column**, which
always wins, so no cross-tenant read was ever reachable. What the defect
produced is a **stored falsehood** waiting for the next reader that trusts a
field inside `data`. `api/_lib/blob.js`'s own header already records two
instances of exactly that found in one 2026-09-24 review.

### The near-miss that the test exists to catch

The obvious fix is `storedBlob(payload, ['id'])` — what **every** sibling call
site in the file passes. **It would have been wrong here.** Those branches
re-attach the id from its column on read; this one returns `x.data` verbatim.
Passing `['id']` would have been a correct-looking scope fix that **silently
emptied the id off every record in all eighteen resources**, and it would have
passed every arm that only checks the forged keys are gone.

So the call is `storedBlob(payload, [])` with the reason written at the call
site, and **arm B1 exists specifically to fail that near-miss.**

### Verification

    node tests/sd_data_sdn_blob_scope.js            EXIT=0   10 passed, 0 failed
    ABLATION vs byte-unmodified HEAD                EXIT=1    4 passed, 6 failed
      FAIL A1/A2/A3  forged license_hash, app_id, p_license_hash all stored
      FAIL C1        the ungated resources too
      FAIL D1/D2     no storedBlob in the branch
      ok   A0/A4/B1/B2  the preservation arms — so not "strip everything"

**It asserts on the BODY POSTED UPSTREAM, not the response**, because the
response is not where the defect lived. **Arm C1 drives an UNGATED resource**
(`sdn_moodboards`, licence-key only) so a fix written into the session-gated
path rather than the shared branch would be caught.

    node --check api/sd-data.js                           EXIT=0
    api/sd-data-sdn-session-gate.test.js                  EXIT=0
    api/sd-data-bespoke-branch-isolation.test.js          EXIT=0
    api/sd-data-cross-tenant-isolation.test.js            EXIT=0
    api/sd-data-unconfirmed-write-sweep.test.js           EXIT=0
    tests/sd_data_family_mar_gate.js                      EXIT=0
    tools/role_gate_invariants.js                         EXIT=0
    tools/md_table_check.py SAIRN-OPEN-WORK-INDEX.md      EXIT=0  831/831
    tools/hover_routing_gap_check.py                      EXIT=0

### Two defects in my own test, both found by running it

1. **Every arm 403'd** with `CREDENTIAL_INACTIVE`. The active-credential
   pre-gate runs above every branch and asks the app's employee-auth table; my
   mock answered `[]`, which is a correct deactivation verdict on an empty
   answer. Mocked honestly instead — had I "fixed" it by weakening the gate's
   mock to pass unconditionally, I would have disabled a real control to make
   a test about something else go green.
2. **Arm D2 cut its source block at the string `SAIRNLEGACY`** — which exists
   only in a **comment**, and the arm strips comments two lines earlier. So
   the "block" ran to end-of-file and matched `data: payload` in unrelated
   branches. Same class as the family_mar false pass in item 1, in the same
   session, found the same way: by reading what the arm actually measured
   rather than what its name says.

### The index row was rewritten, not left

It had been added hours earlier in item 3 as **ROUTED, NOT FIXED HERE**. That
sentence stopped being true, so the row now reads FIXED with the sha, the
ablation numbers and the register record — and carries **what is still open**:
no sweep has been done for remaining raw `data: payload` branches elsewhere in
the file, and the twelve save-site line numbers in that row are hover's and
were **not** re-derived at HEAD. Only the handler branch was.

Register record `57017e71eb4e`. `--injection-unknown` rather than a commit:
the branch has carried `data: payload` since it was written, and
`api/_lib/blob.js` came much later — it was written before the rule it
violates existed, so naming the feature commit would misdate the
discovery-lag figure by months and blame a commit that broke nothing.

---

## 5. `sen_settings` has no local accessor — EXEMPT, and the reason is now in the app

**Premise at HEAD: HELD, and the dispatch's two options are not symmetric.**
`tools/citation_line_drift_check.py` reports every `sen_settings` citation
**INCONCLUSIVE** — *"no storage constant declared for it, and no literal
`setItem('sen_settings')` or `st('sen_settings')` write either"*.

**The verdict is correct and the resource must stay that way.** `sen_settings`
is server-authoritative by a decision recorded in the app's own comment on
2026-08-27, which fixed a real defect: a federally-mandated **EVV
configuration** that lived only in `localStorage` did not survive a
browser-data clear, did not follow the user to a second machine, and was
invisible to the rest of the agency — *while the panel reported it as saved*.
The legacy `sen_agency` / `sen_evv_config` keys are kept **read-only** as a
migration source and are never written again.

**So "add the accessor so it can reach SOUND" would make the checker say SOUND
by re-creating the bug.** Exempted, with the reason written at
`sairnsenior.html` immediately above `SEN_AGENCY_DEFAULT` — at the exact place
somebody would otherwise helpfully add the accessor, rather than in a document
they would not be reading at that moment.

    python tools/checkblocks.py sairnsenior.html    EXIT=0   3 blocks, 0 failed

**And the exemption note immediately caused a drift it also caught.** Adding
15 lines above `saveEvvConfig()` moved it, so the `sen_settings` tier cell's
citation went stale in the same edit — corrected in that edit. Re-deriving the
other two cites in that cell then found **drift +456** on both
`api/sd-data.js` citations, **already there and never reported**: an
INCONCLUSIVE verdict cannot catch a drift, so a resource exempt from the
checker is also invisible to it. That is the real cost of the exemption and it
is now written down.

---

## 6. The drift backlog — 13 rows, 42 citations verified at HEAD

**The dispatched figure was 135 DRIFTED. Re-measured: 170**, across 18
app/prefix pairs. Not reconciled — re-run.

    BEFORE   DRIFTED 170   ANCHORED 156   SOUND 101   INCONCLUSIVE 58
    AFTER    DRIFTED 158   ANCHORED 182   SOUND 103   INCONCLUSIVE 58

**13 rows, well past the 10 asked for:** `sen_settings`, `alf_activities`,
`alf_staff`, `bld_comm_log`, `bld_deliveries`, `bld_equipment`,
`bld_toolbox_talks`, `bld_warranty`, `dnt_vendor_contacts`, `grd_irr_zones`,
`grd_rounds`, `law_picases`, `law_timeentries`.

**42 citations read against the source at HEAD. 28 had genuinely drifted and
are corrected. 14 were already right** — and **five of those fourteen were
being reported DRIFTED by the tool.**

### The result that matters more than the 28: the verdict is a PROXY

`citation_line_drift_check.py` answers *"is this cited line near the nearest
LOCAL WRITE SITE for this resource"*. That is a proxy for *"does this line
support the sentence citing it"*, and on these rows it is wrong in both
directions:

- `law_timeentries:1977` — flagged DRIFTED +128. **Correct at HEAD.** It cites
  a *comment recording a prior defect*, not a write.
- `law_picases:4646`, `grd_rounds:3004` and `:3046`, `grd_irr_zones:3694` —
  all flagged, all **correct at HEAD**.
- `alf_staff:4393` and `:4441` cite `alf_staff_credentials`, a **different
  resource**, so they are far from `alf_staff`'s write site by construction.
- `sen_settings:6355`/`:6359` are in `api/sd-data.js` and are compared against
  `sairnsenior.html`'s write site.

**The tool's own header already records this class** — *"a checker that ranks
a correct citation below an incorrect one is worse than no ranking, because it
rewards the wrong edit"* — and `ANCHORED-VIA` was added to fix it. The
backlog figure still carries the old proxy's false positives, and **a backlog
count is not a defect count.**

### A citation that still looks plausible is the hardest kind

`bld_warranty` cited `fmt(w.cost)` at line `2182`. At HEAD **`2182` is the
definition of the `fmt()` helper** — a line any reader opening it would accept.
The real render is `:6904`. A number that lands on nothing gets fixed; a
number that lands on a right-sounding function survives.

### And one quotation that could not be found at all

`bld_toolbox_talks` quoted `bld_incidents`'s corrective action as *"…
TOOLBOX TALK CONDUCTED SAME DAY"*. The source says *"; toolbox talk conducted
same day"* — lower case, no ellipsis. `grep` for the quoted text returned
**nothing**. Capitals read as emphasis and make a cell unsearchable against
its own source; **a quotation that cannot be found is the same failure as a
line number that points nowhere.** Replaced with the verbatim text.

### Recording the OLD number re-injects it as a citation

Writing *"was `:3227`, now `:3376`"* contributes **both** numbers to
`CITE_RE`, so each corrected cell gained a permanently-dead citation and the
first re-measure came back **worse** (170 → 177). The convention of recording
the superseded number is right — it is how a reader tells a re-derivation from
an arithmetic adjustment — so the number stays and only the **form** changed:
`` line `3227` ``, no colon, which the regex does not match. 18 occurrences
converted. That is the difference between 177 and 158.

    python tools/criticality_tier_check.py   EXIT=0  PROBLEMS:0  TIER_A 275
    python tools/md_table_check.py …          EXIT=0  434/434 rows

---

## 7. Gate parity — the check that would have caught #877, built and ablated

`tools/gate_parity_check.py`. Flags a (file, resource) group where **two or
more actions DISCLOSE the resource and disagree** on whether a role gate or an
assignment gate is enforced.

**Why nothing existing saw #877.** Every control on this platform asks about
ONE branch — is there a session check, is it licence-scoped, does it refuse
cleanly. All three answered **yes** for `family_mar`, because a check *was*
present; it was answering a different question. The missing question is
**comparative**, and nothing compared two branches to each other.

### The ablation, which is the only claim worth making about a new checker

    pre-fix file (git show 05cbc74d:api/sd-data.js)   EXIT=1   4 groups
                                                      ... including alf_family_contacts
    HEAD (fixed)                                      EXIT=1   3 groups
                                                      ... alf_family_contacts gone
    --selftest                                        EXIT=0   7 passed, 0 failed
    under forced PYTHONIOENCODING=cp1252              EXIT=1   0 encode errors

**It catches the real defect in the real file, and the real fix clears it.**

### THREE TIMES THE FIXTURES PASSED WHILE THE TOOL WAS WRONG

This is the part worth keeping, and all three were caught by running against
the real file rather than by adding another fixture.

1. **Writes were being compared against reads** — the docstring said they were
   not. An upsert here carries `Prefer: return=representation` and answers
   `{ ok: true, data: rows[0].data }`, so the disclosure test matched almost
   every write branch. First live run: **36 groups**, mostly "the write
   refuses more than the read", which is the design. Fixture B2's write
   answered a bare `{ ok: true }` — **a fixture cleaner than production tests
   a handler that does not exist.** B2 now returns a representation.
2. **`roleSet(` counted as a role gate.** On the real pre-fix handler the set
   is *declared* in the shared prelude (`:11501`) and *consulted* inside
   `read` only — so the prelude lit up, both siblings inherited `role=True`,
   and **the ablation did not flag #877 at all**. A declaration is not a gate.
   Fixture A1 put the declaration inside the gated branch, which no handler in
   this file does; **fixture A3 is now the production shape.**
3. **The prelude was one shared string.** It must be **per action** —
   everything before that branch, minus the branches it skipped — because the
   tail after the last inner block is the **fall-through**, belonging to no
   action. `api/sd-data.js:11671` is the write path's
   `if (!ALF_MANAGEMENT_ROLES[session.role])`, sitting after the `family_mar`
   block; folding it in handed the write's role gate to both readers and hid
   the asymmetry a second way.

And a fourth, from the same family as item 1's: **comments contaminated every
signal.** `:11485` is a comment reading *"alf_clients.assigned_employee_id,
which is the same source"*, inside the prelude — so every action under that
block reported an assignment gate it did not have. Whole-line comments are now
stripped before any signal is read.

### Precision, reported as its own number

**3 groups flagged on HEAD and all three triaged correct-by-design** — so
**0 of 3**, printed by the tool itself rather than left in a document:

| group | why it is not a defect |
|---|---|
| `rf_claims` | `read` consults the role sets only to **widen** (managers see every row); the siblings gate with `rfAuth.ownsRow()`, a **helper** a lexical check cannot see |
| `rf_schedule` | `crew_load` **refuses** non-management outright — stricter than `read`'s filter, not weaker; the handler says so in its own comment |
| `alf_payer_rules` | `read` discloses a statute reference table with no resident data; `route` is management-only because it **acts** |

Both patterns are now in the tool's printed limits. **Report-only, and not a
push gate:** a lexical comparator at 0-of-3 precision would refuse pushes on
cases a human waves through, and a gate people learn to override is worse than
a report people read.

### NOT COMMITTED — conflict declared per PR §4.3

`tools/tooling_inventory.py` **refuses** to regenerate `TOOLING-INVENTORY.md`
while a tool in `tools/` has no `PURPOSES` entry, and that file is **fourth's**
under a live claim (cody and cc name it too). The tool is **held back
untracked** in this clone and the `PURPOSES` entry is delivered as paste-ready
text in `docs/2026-10-05-hank-routed-to-fourth.md`. Same decision, same day,
as fourth's own hold on `tools/push_failure_reason.py`.

**The cost is real and is stated there rather than implied:** an untracked file
is invisible to every other clone.

---

## 8. Plan literals and the paywall contradiction

### `stonedesk.html` — `Plan: Demo` was a hardcoded literal wearing a variable

`var plan=localStorage.getItem('sd_plan')||'Demo';` — **`sd_plan` has ZERO
write sites anywhere on the platform.** The only two references are that read
and the purge allowlist in `itaClearData()` that preserves it. So the fallback
was not a fallback, **it was the value**: a licensed customer saw *"Plan:
Demo"* for ever on the IT-admin panel.

**Harder to notice than the sairncash case it matches.** A literal in markup is
visible; a dead `localStorage` key reads as real state. Fixed to say what is
known — *"not recorded in this browser"* — rather than inventing a label from
the licence key's presence, which would be the same defect one step along.

### `sairnscape.html` — the pricing header contradicted its own first card

    :187  "Simple. Honest. No per-user games."
    :188  "Flat monthly fee. Unlimited users. Cancel anytime."
    :201  Starter, $99 ........................ "Up to 3 users"

A blanket *unlimited users* claim over the pricing grid, withdrawn **thirteen
lines below** by the entry tier — and Starter is the card a first-time reader
prices against, so the claim has already done its work by the time the
contradiction arrives. Same class as the *"QuickBooks integration"* line
removed from this file on 2026-09-02.

**What is true is kept:** the fee is flat, there is no per-seat billing, and
users are unlimited on Professional and Business. The sentence now says that
instead of more.

    python tools/checkblocks.py stonedesk.html    EXIT=0   131 blocks, 0 failed
    python tools/checkblocks.py sairnscape.html   EXIT=0     7 blocks, 0 failed

### Swept and found clean, stated so the silence is not read as coverage

- `sairncash.html:323` — the Plan row is derived via `scPlanLabel()` (batch 7).
  `:241` *"Pro"* is a **paywall card naming the plan on offer**, not a claim
  about the reader's plan. `:1059` is a comment quoting the old defect.
- The *"unlock unlimited access"* trial-expiry banner appears in **13 apps**
  with identical wording. Not a contradiction: it describes the licensed state,
  and `sairncash.html:1024-1039` already records that the platform deliberately
  does **not** meter AI because the paywall promises it. Consistent, not
  conflicting.
- `sairncode`, `sairndental`, `sairnmechanical`, `sairnsenior`, `sairnvet`,
  `stonedesk:37637` — every other `Plan` hit is a **table column header or a
  form label**, not an assertion about an entitlement.

### LOGGED, NOT FIXED — out of this item's scope and a product decision

`sairnscape.html:258-261`, the Business tier ($299) advertises **"API access"**,
**"Custom AI training on your business"** and an **"SLA and uptime guarantee"**.
These are purchase-influencing claims of the same class as the removed
QuickBooks line, and I did not verify any of the three. Removing or keeping
them is a decision about what is sold, not a literal-sweep fix.

---

## 9. The cp1252 sweep, with its own uncertainty stated

**DRIVEN 296. CRASHED 1. COULD NOT TELL 1.**

    pass 1   296 tools, 25s timeout, 8 workers
             CRASHED  1   accepted_risk_expiry_audit.py
             TIMEOUT 27   NOT a crash, and NOT a pass either
    pass 2   the same 27, serial, 600s timeout
             CRASHED  0
             STILL TIMEOUT 1   run_all_tests.py

So **295 of 296 answered**, and the one that did not is named. `run_all_tests.py`
drives the whole suite, so >10 minutes is expected rather than suspicious — but
it is **not** counted as clean, because a tool that was never observed to finish
has not been observed to encode anything.

**Run in a scratch copy** (`git archive HEAD` into the scratchpad), because a
meaningful fraction of these tools write when run and a sweep must not mutate
its own subject.

### The harness violated a standing convention and was rewritten mid-task

The first version buffered every row and wrote the report at the end. It was
killed at the ten-minute mark and produced **an empty file** — a long run whose
first check is at the end, which is the tenth standing convention, broken by
the tool written to check an unrelated one. Rewritten to flush each row as it
completes, so a kill leaves a true partial answer.

### The one crash, and why its shape matters more than its count

`tools/accepted_risk_expiry_audit.py` printed its per-verdict section headers
with box-drawing rules. Under cp1252 that is `UnicodeEncodeError` — **at the
REPORTING stage, after the whole audit had run.** The process exits 1, and
**exit 1 is also this tool's finding status**, so a caller reading the status
alone cannot tell a crash from a result. It computed the right answer and
could not say it.

Fixed by reconfiguring the **stream**, not the text: ASCII-ing this file would
fix one file and leave the pattern in the other ~295. That is the same fix and
the same reasoning `tools/register_feed_gate.py` already carries, where this
class was recorded as its **fifth instance in one day** — one of which died
*mid-sweep* and recorded an entire app as `SOUND=0 DRIFTED=0 INCONCLUSIVE=0`
over 51 citations. **A crash read as a clean file.**

---

## 10. Methodology — a population must state what it SAW against what EXISTS

**Written here and routed, not into `docs/METHODOLOGY.md`:** that file is
**fourth's** under a live claim. The text is lift-and-paste ready and is named
in `docs/2026-10-05-hank-routed-to-fourth.md`.

### The convention

> **A tool that reads a POPULATION must report the sources it SAW against the
> sources that EXIST, and must fail loudly when the two differ.** A count
> computed over part of a population is not a smaller true answer — it is a
> different question, answered confidently.

**Paid for by `hover_routing_gap_check.py`.** Its default read **876** log
entries and reported **8** unrouted. There were **1404** entries across two
auditor instances and **10** unrouted. **528 entries and two findings were
invisible, and the tool never said a second instance existed.** A
routing-gap checker blind to one auditor's log is the exact shape it was built
to catch.

### What the convention requires, concretely

1. **Enumerate the universe from something that cannot be forgotten** — a
   glob, a `git ls-files`, a registry — never a hardcoded list. A list is a
   snapshot and goes stale silently; the fifth clone on this machine was
   pushing commits for weeks while `CLAUDE.md` said there were four.
2. **Print SEEN / EXIST on every run**, not on request. `876 of 1404` is a
   finding; `876` is a result.
3. **A partial read is a THIRD STATE and is never folded into the pass.** Two
   runs in this batch depend on it: the cp1252 sweep reports
   `run_all_tests.py` as COULD-NOT-TELL rather than counting it clean, and
   `gate_parity_check.py` prints its file list on every run **because a silent
   universe reports clean for a file it never opened.**
4. **Name the exclusions out loud.** A tool that caps at top-N, skips
   retries or samples must `log()` what it dropped — silent truncation reads
   as "covered everything".

### Where it already holds, and where it does not

| | |
|---|---|
| `tooling_inventory.py` | **holds** — 7 declared sources, each with its count and its origin, and it **REFUSES** rather than emitting a blank cell |
| `criticality_tier_check.py` | **holds** — `RESOURCES_REGISTERED` against `RESOURCE_ROWS`, and a disagreement is a PROBLEM |
| `citation_line_drift_check.py` | **partly** — it reports INCONCLUSIVE honestly, but has no SEEN/EXIST line for apps; every SAIRNscape row is unanchorable to it and nothing says so |
| the cp1252 sweep here | **holds, after a rewrite** — see item 9 |
| `gate_parity_check.py` | **holds by construction** — the file list prints every run |

**The third row is the live gap and it is not closed by this entry.**

---

## 11. Inventory — what landed, what did not, and what I got wrong

### Landed, with shas

| What | Sha | Verified by |
|---|---|---|
| `family_mar` caller gate (H1 #877) | `8246d8ba` | `tests/sd_data_family_mar_gate.js` **10/0**; ablation 6 arms fail on unmodified HEAD, 3 allowed arms stay green |
| `scp_designs` B&rarr;A on integrity | `5faa4f1a` | `criticality_tier_check` PROBLEMS:0, TIER_A 275 |
| 14 unrouted hover findings &rarr; 0 | `8783093f` | `hover_routing_gap_check` **EXIT=0**; `md_table_check` 831/831 |
| Six tier cells corrected from the backlog | `7bd72e4d` | PROBLEMS:0; every citation re-derived at HEAD |
| SDN generic write branch `storedBlob()` | `607f4f03` | `tests/sd_data_sdn_blob_scope.js` **10/0**; ablation 6 fail / 4 green |
| 13 rows off the drift backlog | `f9898241` | DRIFTED 170&rarr;158, ANCHORED 156&rarr;182 |
| `sen_settings` accessor exemption | `f9898241` | `checkblocks` 3/0 |
| cp1252 crash; `sd_plan`; pricing header | `53168bb5` | 296 driven, 1 crash fixed; `checkblocks` 131/0 and 7/0 |

### NOT landed, and why

- **`tools/gate_parity_check.py`** — written, 7/0 selftest, ablated against the
  real pre-fix file. **Held back untracked**: `tooling_inventory.py` refuses a
  tool with no `PURPOSES` entry and that file is fourth's. Routed with
  paste-ready text. **An untracked file is invisible to every other clone** and
  that is the cost of the hold, not a detail.
- **The `billing` role in `ALF_FAMILY_READ_ROLES`** — flagged, deliberately not
  narrowed. See item 1.
- **The SAIRNscape Business-tier feature claims** — logged with file:line, not
  verified, not removed. A decision about what is sold.
- **The `sdn_` save-site line numbers** in the routed index row are hover's and
  were **not** re-derived at HEAD. Only the handler branch was.

### What I got wrong, and what caught it

**Five of my own defects this batch, none caught by review and all five caught
by running the thing against real input.**

1. **A false PASS in my own `family_mar` test.** The anchor
   `action === 'family_mar'` matches **twice**, so arm C2 was grading `read`'s
   body — a green arm in a test written specifically to prove that code
   exists. Fixed with a `count == 1` uniqueness guard (arm C0).
2. **The SDN test's arm D2** cut its source block at the string `SAIRNLEGACY`,
   which exists only in a **comment**, and the arm strips comments two lines
   earlier. The block ran to end-of-file.
3. **`gate_parity_check` compared writes against reads** after its own
   docstring said it would not — because fixture B2's write was cleaner than
   any real write branch in the file.
4. **`gate_parity_check` treated a role-set DECLARATION as a gate**, so the
   ablation against the pre-fix file **did not flag #877 at all**. The tool
   built to catch that defect could not see it, and the fixtures all passed.
5. **Recording a superseded line number re-injected it as a citation**, so the
   first drift re-measure came back **worse** (170 &rarr; 177) after thirteen
   correct repointings.

**The pattern is one pattern:** every fixture I wrote was tidier than the code
it stood for, and every one of those defects was found by pointing the tool at
production instead of at the fixture. Three of the five are *the tool failing
to see the exact defect it was written for*.

### Two hover findings whose proposed FIX was wrong

- **seq 714** supplied paste-ready text naming `sfBottleFill()`. That function
  **does not exist** — it appears twice, both in comments. Pasting it would
  have swapped one non-existent identifier for another, in a correction whose
  whole subject is a non-existent identifier. The real anchor is
  `sfEstimateFill()` at `:4834`.
- **seq 403 and the second half of 538** were **already applied** —
  `grd_boq_rates`, the three `leg_` vital-records rows and `sdn_clients` are
  all at their corrected tiers already. The gap was in the **record**, not the
  work.

### Open, named rather than left implied

- The SAIRNscape **Tier A gating** obligation created by the `scp_designs`
  promotion — a third Tier A resource still on the licence key alone.
- The **dead-storage-key** class: keys READ but never WRITTEN. `sd_plan` is
  fixed; `sd_pb`/`sd_pb2`/`sd_pb3` are routed; nothing sweeps for the rest.
- A sweep for remaining raw **`data: payload`** write branches in
  `api/sd-data.js`.
- `citation_line_drift_check.py` cannot anchor **any** SAIRNscape row — it does
  not know the `scpSt`/`scpLd` accessor idiom — and reports INCONCLUSIVE
  without a SEEN/EXIST line.
- **31 Tier A review obligations are past their 24h deadline** platform-wide,
  three of them opened by me today.

---

## 12. Addendum — the unrouted count re-measured at the end of the batch

**It is 19, not 0, and saying "0" would be true only of a moment that has
passed.**

    at the time of the routing pass (§3)   1449 entries   UNROUTED  0   EXIT=0
    at the end of the batch                1492 entries   UNROUTED 19   EXIT=1

**All nineteen were logged DURING this session, after the pass.** Ages run
**0.0h to 1.9h**; the sequence numbers are 551, 556, 557 and 905–913, and the
targets are `fourth` (2), `cody` (1), `platform` (1), `self` (1) and a cluster
of 14 `*_employee_auth` resources carried on ten entries from one finding.
**None of them is one I failed to route** — the pass closed everything that
existed when it ran, and two live auditors added 43 entries while the rest of
the batch was being done.

**Recorded because a zero quoted from a stale measurement is the exact defect
this platform keeps paying for.** §3's number is correct *as of* `8783093f`
and is now stale, which is a property of a count over a live log rather than a
mistake in the pass. The queue did not stay closed and nobody should read it
as closed.

**Not routed here, deliberately:** these are minutes old, most belong to other
sessions by their own `target` field, and a backlog that refills faster than
one session can drain it is not drained by one session trying harder. The
right read is the **rate**, not the instantaneous count, and nothing measures
that yet.
