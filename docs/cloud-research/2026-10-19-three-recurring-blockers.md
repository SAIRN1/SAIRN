# The three recurring blockers — one page

**fourth / b33, 2026-10-19.** Four competitive-gap audits have now produced
four non-recommendations. **Not one of them was blocked by the market or by the
regulation.** Each was blocked by a standing SAIRN capability that does not
exist. Three distinct ones, named below, with what would have to be true for
each.

**This page does not decide anything.** Per `sairn-decision-gate`, a new
vertical is expensive to reverse and this is not that gate. It exists so the
condition does not have to be re-derived from four long documents every time
the question comes back.

**Raw material, all landed and all re-readable:**
`docs/cloud-research/childcare-worldwide-competitive-gap-audit-2026-10-16.md`,
`…/behavioral-health-worldwide-competitive-gap-audit-2026-10-17.md`,
`…/trucking-dot-compliance-worldwide-competitive-gap-audit-2026-10-19.md`,
`…/pest-control-worldwide-competitive-gap-audit-2026-10-19.md`,
`…/PARKED-VERTICALS.md`.

---

## THE HEADLINE, STATED FIRST BECAUSE IT IS THE WHOLE POINT

**Two of the three blockers are company decisions nobody can code around. The
third is a build gap SAIRN could simply close — and this batch found it is
already half-built.** See §3, and read it before §1 and §2, because the third
is the only one that moved today.

---

## 1. BLOCKER A — nobody owns a standing 50-state regulatory matrix

**Named by three of four audits:** childcare (§5), behavioral health (§7, and
the PARKED row), pest control (§7 item 3).

**What it is.** Each of those verticals needs a per-state rule table that is
*maintained*, not captured once: childcare's 50 states × age bands × group caps
× subsidy basis; behavioral health's supervision-hour and compact rules;
pest control's applicator licence categories, 1–3-year terms, 4–24 CEUs per
cycle and per-class renewal dates (Tennessee 2026-06-30, Minnesota 2026-03-01,
North Carolina 2026-06-30 commercial / 2026-09-30 private, Ohio 2026-01-15 —
four states, four dates, four rules).

**Why it is not a code problem.** The childcare audit put it exactly: *"a
content obligation, not a code one, and the platform has no precedent for
maintaining one."* The platform has in fact gone the other way on purpose —
SAIRNdental **refused** to bundle a CDT library on copyright grounds and made
the practice enter its own codes. State ratio tables are public, so the
copyright half of that refusal does not transfer; the *staffing* half does.
Somebody has to keep fifty tables current, forever, and that is a cost with no
owner.

**What would have to be true:** one named person or contracted party owns the
matrix as a standing job with a review cadence — not a one-off capture, and not
"we'll keep it updated."

**Who can answer: Michael. Nobody else, and no amount of building changes it.**

---

## 2. BLOCKER B — SAIRN has never sold an administered service

**Named by one audit:** trucking / DOT compliance (§7 items 1 and 2).

**What it is.** Small-carrier DOT compliance is bought as a *service* — a
third-party administrator keeps the driver qualification files, runs the
random-testing consortium and carries the liability. The trucking audit found
the software half is "a file-upload box"; the business is the administration.

**Why it is not a product problem.** Selling it means staffing it and carrying
its liability. The audit says so plainly: *"a company decision, not a product
one."*

**What would have to be true:** SAIRN decides it will sell an administered
service and accepts the staffing and liability, **or** a certified-TPA
partnership is real and costed. Plus one real small-carrier safety director
confirming the file-keeping pain is worth paying for *separately from* the TPA
they already use.

**Who can answer: Michael.**

---

## 3. BLOCKER C — the routing primitive

**Named by one audit:** pest control (§3, §4 item 1, §7 item 1), which measured
**route / stop ordering present in 0 of 17 apps** and called route optimisation
*"the primary purchase reason"* and *"what the customer buys first."*

**That measurement is correct about the seventeen apps and it is not the whole
picture.** b33 re-ran the archaeology b32 was interrupted during, extended it to
`git log -S` over deleted code and to the `archive/` tree, and **read the
output this time.** What it found:

### 3.1 A working route optimiser exists — on a branch nobody builds from

Commit **`35169ea2`** (2026-06-18) added `?action=maps-optimize` to
`api/bridge.js`: a real **nearest-neighbour ordering over Google Route Matrix
drive times**, server-keyed, with an unreachable-pair fallback and a
`savedMinutes` figure. It deliberately avoids Google's `optimizeWaypointOrder`
because that feature needs a manual Support enablement.

**It is not on `main` and never has been.**
`git merge-base --is-ancestor 35169ea2 HEAD` → not an ancestor;
`git branch -a --contains 35169ea2` → `origin/claude/lucid-ptolemy-b73vu0`
alone. `main`'s `api/bridge.js` was built fresh on 2026-07-31 and carries only
`proxy_get` and `push`. The archive tree preserved 167 files from that branch
but not this one.

### 3.2 The client half IS on `main`, and it is calling into the void

`stonedesk.html:12927` (`fmRunOptimize`) and `:12814` (`fmRenderMap`) both POST
to `https://sairn.vercel.app/api/bridge` with `?action=maps-optimize` /
`?action=maps-static`. **Live-verified this batch** via `tools/sairn_http.py`:
both return **HTTP 401**. On `main`, any POST that is not `proxy_get` falls
through to the licence-gated push handler, so the actions are refused before
anything routing-related runs.

**And the failure message blames the wrong thing:** *"Could not optimize route
-- check the Maps API key is configured."* The key is irrelevant — the request
never reaches code that reads it. A person acting on that message would go
check a Vercel environment variable that is not the problem.

### 3.3 So the blocker's character has changed

| | before b33 | after b33 |
|---|---|---|
| routing on the platform | "0 of 17, does not exist, must be invented" | 0 of 17 in the apps — **but a working server implementation exists off-branch and a live client half exists on-branch** |
| StoneDesk Field Map optimise | assumed working | **broken on the live deployment, with a misleading error** |
| size of the build | an unknown first-class build | a **repair plus a shared module**, with one app's client already written against the call shape |

---

## 4. DOES §3's SCOPE DOCUMENT CLOSE THE ROUTING BLOCKER? — **NO. NOT YET.**

**This is the question this page was asked to answer plainly, so it is answered
plainly and in both directions.**

**`docs/2026-10-19-fourth-b33-routing-primitive-scope.md` DOES NOT close
Blocker C.** It is a scope document. **No code was written, no schema was run,
no endpoint exists, nothing was deployed, and nothing was tested.** A design on
disk is not a primitive. Anyone reading this page later and finding Blocker C
marked closed on the strength of that document is reading an error.

**What it DOES close is the unknown inside the blocker**, and that is not
nothing:

* **Does routing code already exist anywhere? — ANSWERED: yes**, and the answer
  was previously recorded as *unknown-because-nothing-was-read* (b32 §6).
* **Is this a greenfield build? — ANSWERED: no.** It is a repair of a live
  broken call plus a shared module, with a reference implementation to read and
  one app's client half already written.
* **Which app first, and why? — ANSWERED: StoneDesk**, because
  `fmRunOptimize()` already builds the address list, already consumes
  `{order, savedMinutes}`, already persists and re-renders, and already splits
  done from not-done. Phase 1 there is three edits, not a feature.
* **What is the schema and the API surface? — SPECIFIED**, including the four
  decisions that are the point: `saved_seconds` NULL ≠ 0, `optimized_at` NULL
  means never optimised, `lat`/`lng` NULL rather than `0,0`, and a `locked`
  flag so the optimiser cannot move a fixed appointment.

**What would close Blocker C**, in order, none of it done:

1. `rt_routes` / `rt_stops` land in `docs/CRITICALITY-TIERS.md` **before** the
   code — expect **A on confidentiality**; an address joined to a named
   assignee and a date is the same class that took `grd_cart_orders` and
   `leg_processions` to A.
2. The shared module lands under `api/_lib/`, dispatched by `api/sd-data.js`
   resource `routes`, with the four actions and the explicit
   `basis: 'unavailable'` third state.
3. StoneDesk's `fmRunOptimize` is repointed at it and **live-verified against
   the deployed URL**, not a clean `git push`.
4. One second app (SAIRNgrounds is the argued choice — it already owns the only
   real `gcdHaversineM()` on the platform and the accuracy-band discipline
   around it) proves the module is shared rather than StoneDesk-shaped.

**Only after 4 is Blocker C closed**, because "the customer buys routing first"
is a claim about a *shared* capability across field apps, not about one app.

---

## 5. THREE REPAIRS THAT ARE DUE WHATEVER IS DECIDED

Independent of any vertical decision. **None is done; each is a routable open
item.**

1. **`api/bridge.js` must refuse an unknown `?action=` rather than falling
   through to a WRITE.** Today the maps calls 401 because they send no
   `Authorization` header — but if a future change gave them the licence header
   the rest of StoneDesk already holds, the fall-through would accept them as a
   push and upsert `data: {addresses:[...]}` over that shop's `bridge_data`
   row, silently, with a `200 ok`. A typo'd action should not reach a write.
2. **StoneDesk's two Field Map error messages must stop blaming
   `GOOGLE_MAPS_API_KEY`.** §3.2. Whatever happens to routing, a message that
   sends a reader to the wrong environment variable is a defect today.
3. **`maps-static` needs a decision, not a scope.** The route *preview image*
   is a separate call with a separate cost. Phase 1 deliberately excludes it.
   Until someone decides whether a map image is wanted, `fmRenderMap` should
   say *"Route preview is not available in this build"* rather than naming a
   key.

---

## 6. THE RECOMMENDATION THE SERIES ALREADY MADE, AND WHERE IT STANDS

b30 (trucking) recommended stopping the audit series until Blockers A and B
were settled: *"Running a fourth before either blocker is resolved would be
measuring the same wall from a new angle."* **The instruction was to continue,
it was continued, and the fourth audit failed for a genuinely new reason** —
pest control is not an underserved market. Three audits found a gap and no
capability; the fourth found capability adjacency and no gap.

**So the standing position is unchanged and now better evidenced: no fifth
vertical audit until one of the three blockers is addressed.** Of the three,
**only Blocker C can be closed by building**, and §3 shows it starts from
further along than anyone thought.

---

## 7. WHAT THIS PAGE DOES NOT ESTABLISH

* **Nothing here is a build decision.** `sairn-decision-gate` owns that.
* **The 401s prove the deployed endpoint refuses those two actions.** They do
  **not** prove `GOOGLE_MAPS_API_KEY` is unset in Vercel — not checked, and a
  different question.
* **The archived implementation was read, not run.** It has never executed in
  this clone, and its `Math.max(0, …)` on `savedMinutes` is a defect the scope
  document corrects rather than inherits.
* **No per-state regulation named in §1 was verified.** Those figures come from
  the audits and are reported-unverified there too.
* **No competitor product was driven and no operator was interviewed**, in any
  of the four audits. Every one of them says so about itself.
* **Blocker C's four closing conditions are a proposal**, not an agreed plan.
