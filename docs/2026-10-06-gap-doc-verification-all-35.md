# Every gap document checked against HEAD — 35 of 35, mechanically

**2026-10-06 (Fourth).** Batch 9 verified 5 documents by hand and left 30
unchecked. This pass covers **all 35**, by a different method, and the
difference in method is the point: a hand pass reads verdicts, this one
re-derives the **checkable claims underneath them**.

---

## What was checked, and what was not

Three claim shapes, and only three:

| shape | example | how it is checked |
|---|---|---|
| **file citation** | `` `api/_lib/roofing-gl-export.js` `` | does the path exist at HEAD |
| **count claim** | `` `retainage` × 22 `` | re-count the token in the app the document is about |
| **line citation** | `` `IPL_KINDS` at `:3352` `` | is that identifier within ±3 lines of that line |

**Everything else is NOT covered and must not be read as verified.** No
competitor claim, no market size, no severity judgement, no verdict was
re-derived here. A document reported as "every checkable claim still holds"
has had its *arithmetic* checked, not its *argument*.

Run: `python scratchpad/gapverify.py <every gap doc>` — 35 documents,
199 lines of output.

---

## Result

| | |
|---|---|
| documents checked | **35 of 35** |
| clean on all three shapes | **23** |
| carrying at least one finding | **12** |
| of those, FALSE POSITIVES of this sweep | **5** — named below, because a finding list with unnamed noise in it is read as noise |
| real and corrected in this batch | **3** |
| real and ROUTED | **4** |

---

## The five FALSE POSITIVES, named

A sweep that does not publish its own wrong answers trains people to ignore
its right ones.

| doc | reported | why it is wrong |
|---|---|---|
| `2026-08-30-ar-measure-iphone-gap.md` | `api/XRSystem.json` does not exist | It is the **WebXR browser API** `XRSystem`, in backticks beside a MIME-ish name. Not a repo path. My file regex matched `api/...` and has no way to know |
| `superpowers/specs/2026-08-27-sairnmechanical-...md` | 6 line citations past end of file; `subcontractor` 47 → 0 | **My app inference is wrong for this document.** It is named `sairnmechanical` and its §5 cites **stonedesk.html** and **sairnbuild.html**. Lines 34734 / 34078 / 6229 are real in stonedesk.html (3,549-line sairnmechanical.html cannot hold them). The classification rule was mine and it was wrong — convention 14, on my own tool |
| `superpowers/specs/2026-09-02-stonedesk-worldwide-...md` | `sdVeinAnalyze` at `:33536`, found at 33669 | Real drift of **133 lines**, but the document is a 2026-09-02 audit superseded for status by `2026-09-02-competitive-gap-status-rederived.md`. Recorded, not corrected — correcting a superseded audit's line numbers makes it look current |
| `cloud-research/sairngrounds-...-2026-09-27.md` | `msbEnsureSaleHoursSeeded` at `:0` | `:0` is not a citation. My regex matched a `:0` from adjacent prose |
| `2026-09-17-sairndental-competitive-gap-rederived.md` | `rollup` 0 → 41, `roll-up` 0 → 9, `panel-rollup` 0 → 1 | **Already corrected on 2026-10-06**, in that document, with the new counts beside the old ones. The old figures survive inside `~~strikethrough~~` and a text scanner cannot see a strikethrough. **This is a real limitation of the sweep and is stated as one** |

---

## The three corrected in this batch

| doc | finding | what was done |
|---|---|---|
| `2026-09-17-sairnroofing-competitive-gap-rederived.md` | 7 marker counts drifted, all upward — `crew` 39→55, `retainage` 22→46, `WIP` 10→28, `JHA` 36→58, `supplier` 26→41, `COI` 14→16, `EMR` 5→7 | Dated re-count appended. **No verdict moves**: they rest on *non-zero and hand-read*, not on the number. The counts that would matter are the ZEROES and this document has none left |
| `competitive-gap-audit-sairncode.md` | 5 counts drifted and **one went DOWN to zero**: `site-of-service` 3 → 0 | Dated re-count appended, with the open question stated: a token present 3 times and now absent is either a removed feature or a rename, and **a token count cannot tell those apart** |
| `cloud-research/sairnlegacy-competitive-gap-audit-2026-10-05.md` | `leg_merch_catalog` cited at `:1948` (now 2017), `IPL_KINDS` at `:3352` (now 3446) | **Drift I caused**, by the declinability work of 2026-10-06 in the same file. Both corrected in place with the old numbers struck |

---

## The four ROUTED

| doc | finding | owner, and why |
|---|---|---|
| `cloud-research/sairnfreedom-...-2026-09-27.md` | **Three ZEROES became non-zero** — `HB 96` 0→3, `raffle` 0→4, `Casino Control` 0→1 — and `bond` 2→54 | **hank**, holds `sairnfreedom.html` under a live claim and is editing it. A zero becoming non-zero is a capability ARRIVING, which is the one direction that changes a gap verdict, so this is the most consequential row in the sweep |
| `2026-09-17-caller-level-gap-check-senior-stonedesk.md` | 6 counts drifted; `DXF` 38→115 and `QBO` 9→17 are the large ones | stonedesk/senior. `DXF` tripling is the GAP 2 closure the 09-02 file already records; `QBO` nearly doubling against a row held open on Michael's decision is worth a read by whoever owns that decision |
| `SAIRNlaw-competitive-gap-audit-2026-09-24.md` | `split_fees` cited at `:647`, now at `:3900` — a **3,253-line** drift | sairnlaw. Not corrected here: a drift that large usually means the citation was to a different artefact, not that the line moved, and guessing which would be worse than leaving it named |
| `cloud-research/sairnvet-external-...-pricing-cds-2026-09-26.md` | Cites a **companion document that is not on `main`**: `cloud-research/sairnvet-external-competitive-gap-audit-2026-09-26.md` | The companion was written on a PR branch and never landed. A document whose "see the companion" pointer resolves to nothing is the branch-only-audit problem this platform has recorded before |

---

## What this sweep cannot do, stated rather than discovered later

* **It cannot see a correction written as strikethrough.** The sairndental row
  above proves it: three figures already corrected, all three reported as
  stale. Any future use of this tool has to read the surrounding text.
* **It infers which app a document is about from the document's FILENAME**,
  and that was wrong for the SAIRNmechanical research, which cites two other
  apps. A cross-app document gets a wrong denominator and every count claim in
  it becomes noise.
* **It checks arithmetic, never argument.** 23 documents came back clean and
  not one of them has had a verdict re-derived by this pass.
* **A count is not a capability.** `site-of-service` 3 → 0 might be a removal
  or a rename, and nothing here distinguishes them.

---

# BATCH 11 RE-DERIVATION — the inference removed, and then the AMBIGUITY removed

**Run:** `python <scratchpad>/gapverify2.py $(cat gapdocs.txt)` at HEAD
`762b084b`, 2026-10-06. **PROGRAM_EXIT=0** read from the program's own
invocation. Run **three times** against this SHA — once before the ambiguity
state, once after, once after the misattribution state — and the first run
returned the same file-citation and count-claim totals as the last, which is
why the citation column is the only one that moves below.

**The denominator is 36, not 35.** The population was re-enumerated at HEAD and
one document (`2026-10-06-gap-doc-verification-all-35.md` — this file) is part
of it. The title's "35" is the batch-10 count and is left as written rather
than rewritten over.

## 36 of 36 documents verified

| measure | result at `762b084b` |
|---|---|
| documents NAMED / READ / ABSENT | 36 / 36 / 0 |
| file citations | 321, of which **4 missing** |
| count claims | 47 hold, **17 broke**, 173 COULD NOT CHECK (no file named), 4 COULD NOT CHECK (several files named) |
| line citations | 6 hold, **5 broke**, 21 COULD NOT CHECK (no file named), 1 COULD NOT CHECK (several files named), **15 MISATTRIBUTED BY THIS TOOL** |

## THE SECOND LIMIT IN THE SECTION ABOVE IS NOW FIXED, AND IT WAS STILL WRONG AFTER THE FIRST FIX

The limit this file already states — *"it infers which app a document is about
from the document's FILENAME"* — was removed in batch 11 by judging each claim
against **the file the document itself names nearest above it**, with a
`COULD NOT CHECK (no file named)` third state.

**That was not enough, and the residual produced 15 false findings.** The
replacement rule reported:

    CITE  `rf_warranty_tiers` at sairndental.html:4737 -- found at NOWHERE
    CITE  `dnt_gfe`           at sairnroofing.html:1802 -- found at NOWHERE

Ten roofing `rf_*` identifiers judged against the dental app, five dental
`dnt_*`/`cdt_*`/`payer_enrollment` identifiers judged against the roofing app —
all from `superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md`,
which interleaves three verticals. Each "NOWHERE" was *true of the file the
tool chose*. There was a third state for ZERO candidates in the lookback
window and none for TWO, so absence refused and ambiguity resolved silently.

Two states were added and the finding count moved 21 → 5:

* **AMBIGUOUS** — more than one distinct app named in the window; the claim is
  COULD NOT CHECK, counted on its own line (4 counts, 1 citation).
* **MISATTRIBUTED BY THIS TOOL** — the identifier is absent from the file
  proximity picked but present in exactly one *other* app the same document
  names. That is the tool's denominator, not the document's defect, and it now
  prints saying so (15 citations).

Promoted to `docs/2026-09-13-cross-domain-disciplines.md` **item 17**.

**And the same run, invoked with no arguments, printed `TOTALS over 0
document(s)` with every counter at zero and exited 0** — a run that read
nothing, in the same shape and with the same exit code as a run that read all
36. It now exits **2 COULD NOT RUN**, and the totals line states NAMED / READ /
ABSENT separately because one number cannot carry all three.

## The 5 line citations that are REALLY broken

| identifier | cited at | actually at |
|---|---|---|
| `split_fees` | `sairnfreedom.html:647` | **NOWHERE in sairnfreedom.html** — and note the routed row above has the same identifier drifting inside `sairnlaw`; two documents cite one name against two apps |
| `IPL_KINDS` | `sairnlegacy.html:3352` | 3446, 3468 |
| `current_backlog_pct` | `sairnbuild.html:2455` | 3367–3370 |
| `insurance_expiry` | `sairnbuild.html:2571` | 3483, 7251, 7266, 7276 |
| `subComplianceIssue` | `sairnbuild.html:6229` | 6242, 7533, 7568, 7624 |

## What is still NOT done, named rather than left to look finished

* **The 17 broken count claims are measured, not triaged.** `applicant` 46 → 0
  in stonedesk.html and `public catalog` 17 → 0 in sairnsenior.html are
  capabilities going the *wrong* way and are the two worth reading first; the
  `IIF` 0 → 39 and `rollup` 0 → 41 rows are capabilities arriving.
* **No verdict in any of the 36 documents has been re-derived.** This pass
  still checks arithmetic, never argument — unchanged from the limit above.
* **173 count claims and 21 line citations name no file at all** and are
  unreachable by any version of this tool. That is 60% of the count claims in
  the corpus and it is the real ceiling here, not a tuning problem.
