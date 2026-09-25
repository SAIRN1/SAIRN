# Item 47 — First Article Inspection, grounded in what the trade actually does

**2026-09-25 (Fourth).** Item 47 borrowed manufacturing's *First Article
Inspection* for its name and its core idea — measure article one against every
dimension, not a sample — and then implemented a generic two-list checklist.
This closes the gap between the name and the practice, and it starts with a
correction about where the grounding came from.

---

## 0. THE NAMED SOURCE DOES NOT EXIST — stated first, because it changes what this document is

The brief said to use `sairn-trade-vertical-expert`'s domain knowledge as the
source. **That skill is not installed** — not in the user store
(`~/.claude/skills/`, 62 skills, checked by listing) and not in the repo mirror
(`.claude/skills/`). It has no SKILL.md anywhere.

So this document does **not** claim to relay that skill's knowledge. Inventing
trade detail and attributing it to a skill that does not exist would be the
fabrication class this platform spends most of its effort on. The grounding
below comes from two sources that can be named and checked:

1. **Published aerospace and automotive FAI practice** — AS9102 (the aerospace
   first-article standard) and PPAP (the automotive production-part approval
   process). These are external standards; nothing here quotes a clause number
   or a form revision, because I have not read the documents in this session
   and a cited clause I cannot verify would be worse than the shape I can
   describe honestly.
2. **This platform's own trade verticals**, which are checkable in the repo.

**If the skill is installed later, this document should be re-read against it
rather than assumed compatible.**

---

## 1. What the trade does that item 47 was not doing

A real FAI report is **not two lists handed to an inspector.** The structural
feature is:

> Every characteristic on the drawing gets a **balloon number**. The report has
> **one numbered row per balloon**, carrying the requirement, the measured
> result, and the **method** used to measure it. The rule that makes it work is
> **design characteristic accountability**: every ballooned characteristic must
> appear on the form, so an unmeasured one is a **visible empty row** rather
> than an absence.

That last sentence is the whole gap. Item 47's worksheet printed:

```
CLAIMS IN ITS OWN HEADER (7):
  - ...
ARMS IN ITS SUITE (4):
  * ...
MAP THEM BY HAND.
```

Two bare lists. **A claim nobody had considered and a claim somebody had
considered and dismissed look identical in that output** — both are just a line
with nothing beside them. An inspector cannot tell how far through the job they
are, cannot hand it over half-finished, and cannot be held to finishing it.

## 2. What changed, and what deliberately did not

**CHANGED — the worksheet is a ballooned form.** Each claim gets `C-n` and a
`[      ]` verdict column. An empty verdict is now a row somebody still owes.

**CHANGED — accountability arithmetic.** The form prints ballooned-claim count,
arms available, and rows outstanding. When there are **fewer arms than claims**
it says so and names the floor: *at least N rows cannot be filled even if every
arm maps to a different claim.* That is arithmetic about the form, not a
mapping, which is why it is safe to print where a coverage percentage is not.

**NOT CHANGED — the refusal to match.** Pairing a prose claim to a prose arm by
word overlap returned **38% accuracy with five false positives out of five** on
this platform, and `docs/2026-09-14-first-article-inspection.md` says the two
lists *"must not be"* matched automatically. A fixture arm in the tool asserts
it never does. Ballooning gives the human a form to fill; it does not fill it.

**NOT CHANGED — the exit code.** Still 0/1/2 on the mechanical half only
(does a suite exist at all). Verified identical to baseline by stashing.

**STATED IN THE CODE so nobody cites one later:** balloon numbers are
**positional and stable only within a run**. Edit the header and everything
below renumbers. They make the worksheet completable in one sitting; they are
not identifiers.

## 3. The trade-specific half this platform can actually use

FAI's other transferable idea is that **the drawing's tolerance comes from the
part's function**, and the verticals here have real, checkable analogues
already encoded in the apps:

| Vertical | The "drawing dimension" already in the code | Why its tolerance is not generic |
|---|---|---|
| StoneDesk | waste allowance (`proj.comp >= 1.20 ? 1.20 : 1.15`), THH benchmarks, edge-profile LF rates | A waste factor wrong by 5 points is a slab short on a job; the quote and the public calculator must share the expression, which a test arm now pins |
| SAIRNvet | the DEA controlled-substance register and its dosing trail | An inspector asks for completeness, so "the server copy is not capped" had to become a claim verified against a count rather than asserted |
| SAIRNmechanical | 40 CFR 84.106 refrigerant scope from `hfc_gwp_over_53`, leak dates | The engine was complete and the endpoint selected none of the three fields — a seam that would have reported `unknown_substance` for every asset forever |
| SAIRNlaw | IOLTA three-way reconciliation | The one figure a bar association audits; float comparison there refuses correct values |

**The transferable rule:** an artefact serving a regulated vertical should be
FAI'd against the claims its *regulator* would read, not only the claims its
header happens to make. Item 47's own stated limit — *"it cannot see a
requirement the header does not state"* — is exactly where a vertical's
external spec belongs, and no tool on this platform reads one today.

## 4. What this still does not do

- **No external spec is ingested.** The drawing is still the artefact's own
  header. The table in §3 is a pointer for a human, not something the tool
  reads.
- **Arm quality is still unjudged.** An arm asserting `True` fills a row as
  well as a real one. That is mutation testing's job.
- **The method column is absent.** AS9102's form records *how* a characteristic
  was measured; the worksheet records only that an arm exists. Adding it would
  mean classifying arms (driven / source-shape / fixture), which is a real
  piece of work and is named here rather than half-built.
