# Full-platform audit, Wave 3 — StoneDesk, SAIRNbiz, SAIRNvet — CLOSED 2026-09-26

**Closed against stated criteria, each verified against the repo rather than
taken from a report.**

**HEADLINE: all three criteria hold, and one of them needs its wording changed to
stay true. StoneDesk's competitive-gap audit is not "8/8 closed" — it is
"8 of 8 gaps with no un-gated work left", and GAP 4's remaining half is a scanner
vendor relationship, not a module.** That distinction is the difference between a
claim that survives a customer asking and one that does not.

Verified at `1be35856`, 2026-09-26.

---

## 0. A NAMING NOTE FIRST, because it cost a search

**There is no "full-platform-audit Wave 1/2/3" structure anywhere in this
repository.** Searched: `Wave 1`, `Wave 2`, `Wave 4`, `full platform audit` and
`FULL PLATFORM AUDIT` across `docs/` and the repo root. The only "Wave 3" artefact
on disk is a **different** wave — `docs/2026-09-23-wave3-click-through-reverification.md`
and `docs/2026-09-25-wave3-clickthrough-rerun.md`, the click-through
re-verification, which closed on 2026-09-23 with 149/149 nav controls driven
signed-in against the deployed apps.

**The two waves share their three apps** — StoneDesk, SAIRNbiz, SAIRNvet — which
is exactly how a reader confuses them. The wave closed here is the **audit**
wave, whose criteria came with the dispatch rather than from a tracked document.
**They are recorded below so this closure can be checked**, which is the thing a
wave with no artefact cannot offer.

---

## 1. StoneDesk — competitive-gap audit

**Criterion as given: "now 8/8 closed." VERIFIED WITH A CORRECTION TO THE
WORDING.**

`docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`,
eight gaps:

| Gap | State | When |
|---|---|---|
| 1, 2, 3 | closed | 2026-09-02 |
| 8 (remnant half) | closed | 2026-09-02 |
| 7 | closed | 2026-09-03 |
| 5 | found already built | 2026-09-15 |
| 6 | a standing decision, never a work item | — |
| **4 — slab-scanner integration** | **step 1 built 2026-09-26; step 2 vendor-gated** | today |

**GAP 4 is the one the criterion rounds off.** The audit's own corrected text says
closing it is **two steps** — accept an image at all, then accept a *calibrated*
one — and that **only the first is un-gated**. Step 1 landed today:
`panel-veinmatch` accepts up to four real slab photos, declared types only,
`media_type` from the file rather than hardcoded, bytes never persisted, and the
saved row records how many were **read** so a failed request logs 0 instead of
crediting photos nobody looked at. 22 arms, four sabotages caught, live-verified
on the deployed URL.

**Step 2 needs a scanner interface — Slabsmith, SideShot, Iride or Mapascan — and
`slabsmith` is still 0 in the file.** That is a commercial relationship, the same
class as SAIRNroofing's B6 EDI transport and SAIRNsenior's A4 clearinghouse.

**So the honest closure sentence is: 8 of 8 gaps have no un-gated work left.**
"8/8 closed" invites *"so Vein Match reads scanner files?"* and the answer is no.
The audit row now carries both halves in writing.

**Also recorded on that row, so it is not rediscovered as a shortcut:** an orphan
`vmAnalyze()`/`vmPreview()` that already did two-photo vein matching was
**deleted rather than wired**, because it parsed a 1–10 score out of the model's
prose and **defaulted to 5 when the regex missed**, rendering it as a coloured
circle headed "Vein Match Score". Wiring it would have put a fabricated figure
back into the one panel whose three quantitative KPIs were zeroed for that exact
reason.

---

## 2. SAIRNbiz — the 1099 threshold

**Criterion as given: "SAIRNbiz's 1099 bug is fixed." VERIFIED, and fixed in the
right shape.**

`sairnbiz.html:3809` carries `sb1099Threshold` — **"$600 before 2026, $2,000 from
2026"**. The threshold is keyed to the **payment date**, not swapped for a new
constant, so 2025 payments stay at $600.

**That shape is what makes this a real close rather than a patch.** OBBBA raised
the Form 1099-NEC/1099-MISC threshold to $2,000 for payments after 2025-12-31 and
**CPI-indexes it from 2027** — so a constant would have gone stale again inside
fifteen months. A date-keyed threshold is exactly what the 2026-09-03 audit's row
A1 asked for: *compliance thresholds must be dated and configurable, never a
constant.*

**Four sibling findings from the same cloud audit remain open and are NOT part of
this wave**, triaged separately in
`docs/2026-09-26-sairnbiz-internal-findings-triage.md`: the Benefits panel's
invented figures (priority 1 there — fabricated-KPI class, shown to every licence,
including a workers'-comp status the app cannot know), weekly-only overtime, the
omitted Additional Medicare Tax, and the "free" wording. **Closing the wave does
not close those**, and saying so is the point of this paragraph.

---

## 3. SAIRNvet — the formulary

**Criterion as given: "SAIRNvet's formulary has been heavily worked." VERIFIED,
and it is the strongest of the three.**

Four commits, and one of them is a real clinical correction rather than a display
fix:

| Commit | What |
|---|---|
| `7bc26782` | **the butorphanol HORSE row was 2–4× the FDA-approved equine dose** — the dog/cat figure had been copied across all five species rows |
| `f3484b3c` | **284 dosing rows displayed a green "Verified" tick and nothing in the app had ever verified them** |
| `2cec9c09` | four more unearned "verified" claims, in a panel the same morning's sweep never looked at |
| `980a9d2c` | **315 species-copied doses now warn on the screen AND in the prompt**, derived from the table rather than listed |

**Why this one is unambiguous.** The other two criteria are about a feature and a
constant. This is a drug dose for a horse that was wrong by a factor of two to
four, in an app a veterinarian would read — and the same pass removed 284 false
assurances that the numbers had been checked. **The species-copy warning being
derived from the table rather than hand-listed is the part that will still be true
next month**, which is the test a "heavily worked" claim should have to pass.

**What is NOT closed:** the sourcing pass itself. `cc-queue12` carries *"SAIRNvet
formulary sourcing pass continued (281 unsourced rows)"*, and `source_url` is
**0** in the file. **The formulary is now honest about what it has not verified;
it is not yet sourced.** Those are different states and the wave closes on the
first.

---

## 4. Wave 3 — CLOSED

| App | Criterion | Verdict | Evidence |
|---|---|---|---|
| StoneDesk | competitive-gap audit 8/8 | **CLOSED, wording corrected** — 8 of 8 with no un-gated work left; GAP 4 step 2 is scanner-vendor-gated | the audit doc's own GAP 4 row, updated today |
| SAIRNbiz | 1099 bug fixed | **CLOSED** | `sairnbiz.html:3809`, date-keyed |
| SAIRNvet | formulary heavily worked | **CLOSED** | four commits, one a real dosing correction |

**What "closed" means here, stated so it cannot be over-read:** the three named
criteria are true at `1be35856`. It does **not** mean these three apps have no open
findings — SAIRNbiz has four live ones triaged today, SAIRNvet has 281 unsourced
rows with cc, and StoneDesk has a vendor-gated half-gap and eight dormant chat
hooks now disclosed rather than silent.

**And this closure is itself a claim with a date on it.** Every row above is a
read at one commit against files three other sessions are editing. **Re-verify
before quoting the wave as closed** — SAIRNbiz's F1 moved from open to fixed
inside the same afternoon this was written.

## 5. What this closeout did NOT do

- **It did not find or create a Wave 1/2/4.** The criteria came with the dispatch;
  there is no tracked wave document to update, and none was invented.
- **It did not touch `sairnbiz.html` or `sairnvet.html`.** `cc-queue12` holds
  both.
- **It did not re-derive the seven already-closed StoneDesk gaps.** Their closures
  are inherited from the dated entries on the audit row, which is the weaker half
  of this verification and is stated rather than glossed.
- **It did not verify any external fact.** OBBBA, the FDA-approved equine
  butorphanol dose, and the CPI-indexing date are all inherited.
