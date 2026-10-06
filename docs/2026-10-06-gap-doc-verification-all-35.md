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
