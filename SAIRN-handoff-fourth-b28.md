# HANDOFF — fourth / ted, batch b28, 2026-10-16

**READ THIS FILE ONLY.** It is the whole state.

**FOUR OF SIX ITEMS DONE AND NOTHING IS HALF-FINISHED AT THIS LINE.** Items 5
(this file) and 6 (the push) are what remains, and §7 says exactly what is left
in them. Every other item is either closed with driven evidence or has its
remaining step named with an owner.

**Context at this line: 44.0% of 1000k** (439,525 tokens, max `usage` sum over
this session's transcript).

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FIVE THINGS TO READ FIRST:**

1. **TWO DISPATCH PREMISES WERE WRONG AND BOTH CORRECTIONS CHANGED WHAT GOT
   BUILT.** Item 3's described defects do not exist and two real ones did;
   item 4's "four existing audit docs" are four of twenty. §2, §5.
2. **A WRITE-AND-NEVER-READ ON MONEY.** SAIRNdental has stamped the CDT code
   and edition onto every charge since 2026-09-17 and **both readers ignored
   the stamp**. §2.
3. **THE TIER A LEDGER IS NOW APPEND-ONLY PER-AGENT, AND THE bld_bids
   DISCHARGE LANDED THROUGH IT WHILE hank STILL HELD THE OLD FILE.** That is
   the fix working on its first real use. §3, §4.
4. **cody's CHECK (4) IS A CONFIRMED HIGH FINDING, DRIVEN.** The unrepaired
   predecessor defect sits **twelve lines above** the arm b27 repaired, on the
   same Tier A resource. §4.
5. **THE CHILDCARE SUBSIDY BILLING BASIS FLIPPED TWICE IN 26 MONTHS** and the
   rescission takes effect **2026-07-13**. §5.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\ed5b1771-4b30-429a-98d0-aa98a2a7e664.jsonl`

**Working files (this session's scratchpad):**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\ed5b1771-4b30-429a-98d0-aa98a2a7e664\scratchpad\`
b28: `b28_dental_drive.js` + `.log`, `b28_check4_ablation.py` + `.log`,
`b28_check2_ablation.log`.
**b27-resume's files are in the SAME directory** (`b27r_*`), because this is the
same session; b27's own first-session files are under `990beb38…` and are not.

---

## 1. COMMITTED / PUSHED STATE, AS OF THIS LINE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **14 BEHIND, 0 ahead** — five sessions are pushing; nothing of mine is committed yet | `git rev-list --left-right --count origin/main...HEAD` |
| claim | **HELD**, published on `origin/main` | `sairn_claim.py own` |
| status row | `working` | `sairn_status.py` |
| uncommitted | `sairndental.html` (M); new: `tools/tier_a_reviews_store.py`, `docs/tier-a-reviews/`, the two new docs, the manifest | `git status --porcelain` |
| `git stash` | **0** | `git stash list` |
| `SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` | **none used, any form** | — |
| `.claude/settings.json` | **not edited, not committed** | — |
| hooks | **untouched and never re-added** | — |
| files written under `api/` `sql/` `tests/` | **0** | `git status --porcelain` |
| `docs/tier-a-reviews.json` | **BYTE-UNTOUCHED** — `git status --porcelain` on it is EMPTY | — |
| `tools/tier_a_review_gate.py` | **not edited** — cc's, and held LIVE all batch | — |
| auditor clones | **not entered** | — |
| b28 batch manifest | **opened FIRST**, `--new fourth b28 --items 6`, `id_lock=906816e5cf0d24f9`; **4 done, 2 open** | `batch_manifest.py --check --agent fourth --batch b28` |

**NOTHING IS PUSHED YET.** §7 item 6 is the push and it is the only reason this
table does not say 0/0. **Do not read this file as a post-push state** — the
report and digest carry that.

---

## 2. ITEM 3 — SAIRNdental: THE DESCRIBED DEFECTS DO NOT EXIST AND TWO REAL ONES DID

**Measured before anything was changed.** The dispatch said to "repair the
orphaned tbody, wire up the unfinished JS, verify no HTML corruption remains":

* **`html.parser` over the file with script/style bodies blanked (line numbers
  preserved): ZERO findings, ZERO unclosed tags.**
* **All FOUR script blocks pass `node --check` individually.**
* Every `<tbody id>` has a JS writer; every `getElementById` id exists in the
  markup; no inline handler names an undefined function.

**So there is no orphaned tbody and no HTML corruption.** A `grep -c '<tr'`
count *did* look unbalanced (84 open / 85 close) and that was the regex
counting `<tr>` inside JS string literals — which is exactly why the project
rule says parse, don't grep.

### F1 (HIGH) — the charge's CDT stamp was written and never read

`addChargeEntry()` has stamped `cdt_code` and `cdt_version` onto every charge
since 2026-09-17, and its own comment states the guarantee: *"the code and the
edition are STAMPED AT POSTING"*, so a catalogue edit cannot restate history.
**That guarantee did not hold.** Both places that show a charge's code looked it
up **LIVE** from the mutable procedure-type row:

* the patient ledger's charges table, and
* the `charges` export's `Procedure` column — **nine lines below its own comment
  stating the rule it then broke**: *"a deleted patient still has charges, and a
  name-only export would make those rows unattributable."* A deleted **procedure
  type** has charges too.

**The write half shipped, the read half did not, and nothing could tell**: the
stamp and the lookup agree on every row until the day the catalogue is edited,
which is the one day the stamp exists for.

**FIXED** — `dntChargeCode()` reads the stamp; falls back to the live row only
when there is no stamp and **labels that** (*"as the catalogue reads today — not
stamped at posting"*); says *"not recorded"* when neither exists rather than
guessing. Three new export columns: `CDT code as billed`, `CDT edition as
billed`, `Code source`.

### F2 — the versioning had no way in

The form was **ADD-ONLY** and the table's only action was **Remove**. So every
procedure type predating the feature reported **"Not verifiable" permanently
with no path to a checked state** — the exact population the feature was built
for — and applying a new CDT edition meant Remove-and-re-Add, which mints a new
row id and orphans every historical charge. **The 2026-09-17 stamping fix was
written for an edit path that did not exist**, which is also why its missing
read half was never noticed.

**FIXED** — `startProcedureRevise()` / `cancelProcedureRevise()` plus
update-or-insert in `addProcedureType()`: **same row id** so posted charges stay
attributable, replaced values **appended to `revisions[]`** rather than
overwritten, only **changed** fields recorded, and refusals for no-change,
vanished-target and inverted-window.

### Driven, not read

`<scratch>/b28_dental_drive.js` extracts the four functions out of the 430KB
file **by name** and runs them against stubs. **ALL 22 CHECKS PASS, exit 0** —
including the discriminating case (catalogue revised after posting, so stamp and
lookup disagree) and five refusal directions.

**ONE HARNESS DEFECT DISCLOSED:** the first draft's `newId()` minted `'PC-1'`,
colliding with the fixture's own id, and the ADD arm failed **on the harness and
not on the app**. The stub now prefixes `NEW`. A stub that can accidentally
satisfy or break an assertion is the same defect class as the rest of this
batch.

---

## 3. ITEM 1 — THE TIER A LEDGER IS APPEND-ONLY PER-AGENT

**Michael's decision. The design argument is the part worth keeping**, because
it rules out the obvious implementation:

The ledger **already** declares itself *"append-only across four clones"* in its
own `merge_policy`, and `tools/sairn_rebase_resolve.py` **already** 3-way merges
it by identity. **So git was never the contention.** `tools/sairn_claim.py`
decides on the **DECLARED FILE SET**, so two sessions naming the same path block
each other whatever the merge semantics are — and **a single shared append-only
JSONL is still ONE PATH.** Only per-agent shards put the writes on disjoint
paths.

`docs/tier-a-reviews/<session>.jsonl`, one JSON object per line. A session
appends only to its own shard and never rewrites it.

* **Identity is `(author_session, opened_at)`, taken VERBATIM from the legacy
  file's own `merge_policy.identity`**, not invented. `--validate` reports
  `IDENTITY DRIFT` if they ever disagree, because a discharge keyed on the wrong
  fields opens a *second* obligation instead of closing one.
* **The reader unions legacy-base + shards, last layer wins FIELD-BY-FIELD, not
  whole-record.** A discharge line names the verdict and reviewer without
  restating `resources`/`files`/`rules`; a whole-record replace would erase them
  by omission. **That is a fixture, in the direction that would have been
  wrong.**
* **MIGRATED:** 265 records → `cc=66 cody=71 fourth=48 hank=76 hover2=4`, **zero
  unknown authors**. **Round trip proved LOSSLESS, not assumed:** 0 identities
  only in legacy, 0 only in the union, **0 records differing**, 265 → 265.
  `--migrate --apply` is **idempotent** and leaves the legacy file
  **byte-identical** — both fixtures.
* **22 fixtures, both directions, `--selftest` exit 0**, and every other mode
  runs them first and exits **2 COULD NOT RUN** rather than reporting with a
  caveat. Fail-closed on an unreadable legacy layer (returns `None`, never
  `[]`); per-line reporting of a bad shard line with the read marked
  **DEGRADED**; refusal of an unknown session, of a record with no identity, and
  of a non-object; and append-after-missing-final-newline not concatenating two
  records.

**THE LEGACY FILE IS NOT DELETED, EMPTIED OR REWRITTEN.** It is the base layer,
so every existing reader keeps working — **and it was held live by hank all
batch, so rewriting it would have been the defect this fix exists to prevent,
committed by the fix for it.**

**ONE DEFECT IN MY OWN TOOL, FOUND AND FIXED:** `--read` first reported all 265
migrated records as *"superseded by an appended line"* when every one was a
byte-identical mirror of itself — a count reading as 265 edits when there were
none, **the fabrication shape inside the tool built to stop one.** It now
separates *layered* from *CHANGED* and reports 0 changed.

**ROUTED, NOT EDITED:**
`docs/2026-10-16-fourth-b28-tier-a-shards-routed-to-cc.md` carries the full
replacement bodies for `load_reviews()` and `save_reviews()` — **TWO FUNCTION
BODIES, not 18 call sites**, because the gate already funnels 11 loads and 7
saves through them — plus the one fixture only cc can write, and a **named
non-patch** for `review_ledger_reseat.py` with the reason.

**STATE: shards are ADDITIVE AND NOT AUTHORITATIVE until cc lands that**, and
the store prints that sentence on every `--read` rather than leaving it to be
remembered.

---

## 4. ITEM 2 — THE bld_bids DISCHARGE, AND cody's CHECK (4) IS A HIGH FINDING

**Discharged by APPENDING to `docs/tier-a-reviews/fourth.jsonl` while hank still
held the legacy file.** `cody 2026-10-15T15:12:47Z` / `bld_bids`: `open` →
`reviewed`, `reviewer_session: fourth` (author `cody`, so **not self-signed**).

**Verified by reading it back through the union:** 265 records still 265 with no
duplication, not-reviewed **11 → 10**, exactly **1** record differs from its
legacy value, provenance `['legacy','cody.jsonl:70','fourth.jsonl:49']`, and the
field-level merge **kept** `resources`, both `files` and all 1,701 characters of
cody's own `what` text. **`git status --porcelain docs/tier-a-reviews.json` is
EMPTY and the legacy file still reads `status: open`.**

**All four of cody's named checks answered BY ABLATION, and two are HIGH:**

| check | answer |
|---|---|
| **(1)** can a comment or string literal satisfy the new regex? | **YES, AND IT DID, TWICE.** Four of five mutations accepted on the shipped repair; then the repair itself opened M6 — `'write'` → `'read'` **accepted at 25 passed, 0 failed**. Both closed; 10/10 refused on the named arm. |
| **(2)** is the planted defect still right, given `bld_draws` joined the map? | **The defect is right and `bld_draws` HAS NO ARM.** Flipping `bld_draws: false` **alone** is **ACCEPTED at 25/0**, while the `bld_bids` control is REFUSED on the named arm. **Same shape as b26's `law_bankstatements` finding.** |
| **(3)** is arm 6 CAUGHT for a verified reason? | **YES.** M1 *is* arm 6's mutation and returns exit 1 with the red arm named; the harness reads the red arm's own stdout line so no other arm can be credited. |
| **(4)** does the sibling `BLD_PENDING_TRACKED` assertion have the same substring-proxy shape? | ***YES. HIGH. IT IS THE UNREPAIRED PREDECESSOR DEFECT, TWELVE LINES ABOVE THE ARM THIS RECORD REPAIRED.*** |

**Check (4) in full**, because it is the batch's sharpest finding.
`tests/sairnbuild_server_wins.js:408` is
`html.indexOf("BLD_PENDING_TRACKED['bld_bids'] = true;") !== -1` **over the
WHOLE FILE with NO comment stripping whatsoever**, and `:418` is a raw
`body.indexOf('BLD_PENDING_TRACKED[key]')`. Driven **with working controls**:

```
N2 CONTROL  declaration DELETED outright ............ exit 1  REFUSED
N3 CONTROL  declaration flipped to `= false` ........ exit 1  REFUSED
N1          declaration replaced by a LINE COMMENT
            carrying it ............................. exit 0  ACCEPTED, 25/0
N4          the :2522 guard broken, a BLOCK COMMENT
            carries a satisfying one ................ exit 0  ACCEPTED, 25/0
```

**So `bld_bids` can lose its pending tracking entirely and the suite stays
green.** N2/N3 refusing is what makes N1/N4 mean something.

**I did NOT edit `tests/` for findings (2) and (4).** `tests/` is cody's, and a
reviewer who fixes what he reviews is the self-signed review this ledger exists
to prevent.

**STATED LIMITATION, NOT FOLDED INTO THE PASS:** the push gate still reads the
legacy file, so this discharge is **durable and recorded but NOT YET
AUTHORITATIVE** until cc lands the two routed bodies. The record's own `note`
field says so.

---

## 5. ITEM 4 — THE CHILDCARE AUDIT, AND THE PREMISE CORRECTION

`docs/cloud-research/childcare-worldwide-competitive-gap-audit-2026-10-16.md`.

**The dispatch named four existing audit docs. There are twenty**, and
`docs/2026-09-29-competitive-gap-doc-inventory.md` — which derives its universe
with `git ls-files '*.html'` rather than trusting a list — records that **all
eighteen real products already have one**, the last three closed 2026-10-05. So
"the next vertical not covered" cannot be a SAIRN app, and the only
non-vacuous reading is **a vertical SAIRN has not built for**. Read the other
way, the work would have been a 21st audit of an audited app. **That correction
is §0 of the document, not a silent reinterpretation.**

**THE CENTRAL FINDING:** brightwheel holds **45.92%** of the install base
(6sense technographic, 2,456 customers) and is reported to have **no proactive
ratio alerts at any tier, no real-time staff-to-child ratio monitoring**, and to
trail on licensing-compliance reporting and complex subsidy billing — while
**Procare at 27.07%** sells exactly ratio alerts, **background-check expiration
tracking** and state licensing reports as its differentiator. **The largest
share of the market runs without the compliance layer a licensing inspector asks
about.**

**THE REGULATORY FINDING, dated:** the 2024-03-01 CCDF final rule mandated
prospective payment and payment on authorised **enrolment**; ***Restoring
Flexibility in the CCDF*, FINAL RULE 2026-05-12, 91 FR No. 91, doc 2026-09382,
RESCINDS all four of those requirements EFFECTIVE 2026-07-13** and makes each a
per-state option. **The billing basis flipped twice in 26 months.** No product
can hold one answer — it must hold the rule per state, with an effective window,
evaluated against the **service period**. That is the same shape SAIRNdental
solved for CDT editions and that item 3 finished in this batch.

**Platform fit verified, not asserted** (`grep -ciE` over the root app files): a
credential-expiry primitive ships in **14 of 18** products; an `effective_from`
date-of-service primitive in **4** (`sairncare`, `sairndental`, `sairnlaw`,
`sairnsenior`).

**AND THE HONEST OTHER HALF, which is §4 of the document:** ratio-AND-group-size
is **not** a primitive in any app and is the largest build item; CCDF subsidy
depth is beyond any billing path shipped; the check-in burst load shape has no
precedent here; **the criticality tier would be high and is NOT assessed.**

**Every limit named rather than buried:** no competitor account was provisioned
and no feature driven, so the central claim rests on **secondary and partly
competitor-authored** sources; the market denominator's three sources **disagree**
(92,786 / 83,176+53,653 over 29 states / 82,162 Census establishments) and a
fourth is an order of magnitude out and is **excluded as UNRECONCILED rather
than averaged**; the share table **omits Lillio**, which other sources call a
leader; and a redirect blocked the direct Federal Register fetch, so the
rescission is cited by document number with an instruction to re-derive before
customer-facing use. **The document states it is NOT a build recommendation.**

---

## 6. WHAT IS OPEN, BY OWNER

### cc — `tools/`

1. **LAND THE TWO FUNCTION BODIES** from
   `docs/2026-10-16-fourth-b28-tier-a-shards-routed-to-cc.md`. **Until then the
   bld_bids discharge in §4 is recorded but not seen by the push gate**, and
   `docs/tier-a-reviews.json` keeps being the contention it has been for three
   batches. Add the one fixture only you can write: open an obligation,
   discharge it from a different session with the legacy file read-only, assert
   `--list` sees it.
2. **`review_ledger_reseat.py`** — named non-patch, not an oversight. Reseating
   an append-only log means appending a correction line, and which fields may be
   corrected that way is a semantics decision.
3. **INSTALL THE BRANCH CENSUS** from the b27 routing doc —
   `docs/2026-10-16-fourth-b27-branch-census-routed-to-cc.md`, seven rules, 26
   fixtures. `tools/branch_census.py` **still does not exist**; sixth batch,
   sixth scratchpad.
4. **`batch_manifest.py --check` should RESOLVE the paths inside evidence
   strings** and report COULD NOT RESOLVE per path (b27 §1 — one `re.findall`,
   one `os.path.isfile`). Still open, and **this batch hit the adjacent
   problem**: a manifest evidence string written through Bash had two
   backtick-quoted field names eaten by command substitution, which I found and
   repaired by hand. A `--set` that refused a backtick, or took evidence from a
   file, would close that.
5. Still open from b26/b27: `tier_a_review_gate.py --amend`; wire **ONE**
   anchor-rot tool into a gate; R3's 48 citation ranges; and the
   convention-numbering check routed in
   `docs/2026-10-12-fourth-b5-routing.md:585-615`, which b25–b28 have all moved
   a prose denominator by hand instead of.

### cody — `tests/`

1. **CHECK (4), HIGH, from §4 — `tests/sairnbuild_server_wins.js:408` and
   `:418`.** Match over a comment-and-string-stripped copy and require the
   **guard** rather than the substring. **Then re-run N1 and N4 and confirm BOTH
   go RED** — an arm does not count until it has been made to fail. The same fix
   already exists twelve lines down, in the arm b27 repaired.
2. **An arm for `bld_draws`**, from check (2) — one that goes red when
   `bld_draws` alone loses its session flag.
3. Unchanged from b27: arm Z's `else` branch then **re-run the ablation**;
   `known-red-suites.json` blob-scope row and the control arm's hardcoded *"ten
   failures above"*; b24 F1's re-anchoring with an arm that fails when the
   anchor stops matching; a failing-first arm driving a `23514` through one of
   the 22 and a `42703` through one of the 151.
4. **I edited two of your files in b27-resume** under a declared claim while
   yours was expired. The arm now carries **two** assertions and the probe carries
   arms **6, 14 and 15**. If you re-shape it, the property to keep is **both**
   copies: strings collapsed proves it is code, strings intact proves it is the
   `'write'`.

### hank — `api/`

Unchanged and **carried from b26 without re-verification this batch, which is
why it is not restated in detail**: H3 first (the append-only closings resource
and the named refusal of `payroll_closed_periods` at the generic `sen_settings`
path — **until it exists a paid period can be unfrozen by a billing session with
one POST**), then H2, then H1 with the 2×2 re-run confirming ARM A goes RED;
then Q4's `partially_closed`, Q(b)2's EVV basis, Q(c)'s two purity headers; then
b24 F3 and F4. **Read b26's handoff for those, not this paragraph.**

**AND ONE THING b28 ADDS FOR hank:** `docs/tier-a-reviews.json` is now a
**read-only base layer**. Keep reading it; **stop rewriting it** once cc lands
the routed change, and append to `docs/tier-a-reviews/hank.jsonl` instead —
`python tools/tier_a_reviews_store.py --append hank --record '<json>'`.

### Michael

**Nothing blocking from b28.** Item 1's decision was yours and is implemented as
far as another session's live claim allows; the remaining step is cc's and is
one routed change.

**TWO THINGS FOR YOU, both named rather than acted on:**

1. **The childcare vertical is NOT recommended by §5** of that document, which
   lists what would have to be true first — a driven trial account on
   brightwheel and Procare, one real centre director interviewed, and an owner
   for a 50-state rule matrix that nobody currently has. Per
   `sairn-decision-gate` a new vertical is expensive to reverse and that audit
   is explicitly not the gate.
2. Carried, unchanged: the one-person-agency self-approval question; whether any
   real visit was underpaid before today is **not establishable from the repo**;
   and **no agency has a `payroll_closed_periods` row, so the freeze has never
   run on real data by anyone.**

---

## 7. WHAT IS STILL AHEAD OF THIS FILE

**Nothing is half-finished at this line.** These are whole steps, in order:

1. **Commit everything in §1's uncommitted list and push without force**,
   rebasing onto the 14 commits ahead of me, then **confirm it landed by reading
   the files back off `origin/main`** — a clean exit from `git push` is not
   proof. Manifest item 6.
2. **The register-feed gate will deny** on item 3's commit, as it did in
   b27-resume: a `fix(...)` touching shipped behaviour needs a
   `docs/defect-density-register.json` record or a `no-defect-record:` note.
   **Write the record** — F1 is a real write-and-never-read on money and
   deserves one.
3. The report, the digest and `SAIRN-latest-fourth-b28.md`; upload all four
   deliverables to Drive folder `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` and
   **verify each THROUGH THE DRIVE API**, not off the mount — the mount proves
   the bytes are in the sync set, not that Google acknowledged them.
4. Close the manifest, **release the claim LAST**, then set the status row to
   `idle`.

---

## 8. WHAT b28 PROVED vs LEFT UNPROVEN

**PROVED, driven or measured:** that SAIRNdental's HTML and all four script
blocks are clean and that the dispatch's described defects do not exist; that
the charge CDT stamp was written and read nowhere, and that the fix reads it,
labels its fallback and refuses to guess (22/22 driven); that a procedure type
can now be revised in place keeping its row identity, with history appended and
four refusal directions; that the Tier A migration is lossless (265→265, 0
differing) and idempotent and leaves the legacy file byte-identical; that a
reviewer can discharge another session's obligation by appending one line while
a third session holds the old file; that `bld_draws` has no arm; and that the
sibling `BLD_PENDING_TRACKED` assertion accepts both a line comment and a block
comment with valid controls on either side.

**LEFT UNPROVEN, and none of it is recorded as checked:**

* **NO LIVE VERIFICATION.** Nothing ran against a real Supabase. **No
  production row read, no table touched, no deployment fetched.**
* **The shards are not authoritative** and the push gate has never read one.
  Until cc lands the routed change, **the only thing proved is that the store
  works**, not that the platform uses it.
* **`sairndental.html` was never rendered.** The two fixes were driven through
  extracted functions against stubs, not through a browser, and no panel was
  screenshotted. `sairn-visual-review` did not run.
* **The childcare audit drove no competitor product** and interviewed nobody;
  its central claim rests on secondary, partly competitor-authored sources and
  its §6 says so.
* **`tests/` findings (2) and (4) are reported and NOT fixed**, by design — they
  are cody's.
* **Everything in §6 attributed to hank is carried from b26 and was not
  re-verified this batch.**
