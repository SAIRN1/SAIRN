# SAIRNsenior — round 26: the "render-but-unreadable" shape was a stale tab

2026-08-30. **Research only.** Fortieth document in the series.

**Round 25's conclusion was wrong, and the correction is the most useful
operational finding of the night.** *"The browser is a fresh angle, not a master
key — three of four Chrome attempts fail"* rested on a defect in **my tab**, not
in three states' websites.

**Opening a new tab fixed South Dakota and Alaska in one attempt each.**

---

## 1. The diagnosis, and how it was found

South Dakota's `/Statutes/34-03A` hung across four attempts with waits to eight
seconds, while `/Statutes/34` and `/Statutes/34-12` had rendered fine **in the
same tab minutes earlier**. `document_idle` never fired; screenshots timed out.

**The tell:** when a new tab was created, the *old* tab's title had updated to
**"Codified Law 34-3A-1 | South Dakota Legislature"** — **the page had loaded all
along.** Only the automation's readiness check was stuck.

**A fresh tab loaded the same URL and returned full text in four seconds.**

> **After roughly a dozen navigations, a tab stops reaching `document_idle` on
> these sites and never recovers — while continuing to load pages normally.**
> Every symptom I attributed to three separate publishers was one client-side
> defect:
>
> - **South Dakota 34-03A** — "specific to that chapter page" (round 25). **Wrong.**
> - **Alaska `aac.asp`** — "confirmed: browser does not resolve it either"
>   (round 25). **Wrong.**
> - **Arizona's PDF viewer** (round 5) — **genuinely different**; that was a
>   canvas-rendered PDF with no text layer, and remains unresolved.
>
> **So the real number is one of three, not three of four**, and the rule is:
> **when `document_idle` times out, create a new tab before concluding anything
> about the site.**

---

## 2. South Dakota — read, and it is not a licensure chapter

**SDCL ch. 34-3A, "Home Health Services"** — six sections, in full:

> **34-3A-1** Special revenue funds authorized · **34-3A-2** Fees paid into
> special revenue fund · **34-3A-3** Fees receivable by counties and
> municipalities · **34-3A-4** Expenditures from special revenue fund ·
> **34-3A-5** Health service contracts with public or private agencies ·
> **34-3A-6** Appropriations from general funds for contract purposes.

> "The counties and municipalities are hereby authorized to establish a **home
> health agency services special revenue fund**." (§ 34-3A-1, SL 1968 ch 26)
>
> "Fees collected … for services to patients in their homes by **public health
> nurses, home health aides, physical therapists, and other specialized health
> personnel who are employees of counties and municipalities** shall be receipted
> into said fund." (§ 34-3A-2)

**This is a county and municipal finance chapter.** It authorises local
governments to run a fund for home health services they themselves provide, to
receive fees from patients, Social Security home health benefits, the Department
of Social Services, insurers and other agencies, and to contract for health
services with public or private agencies.

> **Third chapter whose *name* promised licensure and delivered something else**,
> after West Virginia art. 2C (public provision) and North Dakota 23-17.5
> (repealed cooperative agreements). **"Home Health Services" as a chapter title
> means nothing until the sections are read.**

**And SDCL 34-12 does not license home health either** — round 25 established its
institution list stops at hospitals, nursing facilities, assisted living, hospice
and adult foster care. **So no home health agency licensure has been found in
South Dakota's statutes at all.** *(Whether ARSD — the administrative rules —
carries one was not checked. **Do not read this as "South Dakota does not license
home health."**)*

**Reclassification check on ch. 34-3A: no relevant language** — the chapter
concerns county employees and public/private service contracts.

---

## 3. Alaska — title 7 opens

`akleg.gov/basis/aac.asp#7` returned **Alaska Administrative Code Title 7,
Health and Social Services**, beginning at Part 1, Chapter 05 (Vital Records) and
continuing. **The route is open.**

**Chapters identified in Title 7 so far:** 05 Vital Records · 07 **Certificate of
Need** · 09 **Design and Construction of Health Facilities** · 10 **Licensing,
Certification, and Approvals** — the last also covering **barrier crimes and
background checks**, which is Alaska's centralised-licensing machinery under
AS 47.32.

**No home health or home care provisions appear in the portion loaded.** Two
possibilities, neither established: the relevant chapter sits further down a very
long single-document title (the extraction is capped at ~50 KB and returned only
chapter 05's text), or Alaska handles home health through **7 AAC 10**'s
centralised licensing rather than a dedicated chapter. **Not concluded.**

---

## 4. Tier 2

| Item | Status |
|---|---|
| Alaska 7 AAC 10 (Licensing, Certification, Approvals) full text | **ROUTE OPEN, NOT READ** — the single-document title exceeds one extraction. |
| Whether Alaska licenses home health/home care at all, and where | **NOT ESTABLISHED** |
| South Dakota ARSD (administrative rules) | **NOT CHECKED** — the remaining place a licensure regime could sit. |
| **Arizona AAC 9-10** | **STILL GENUINELY BLOCKED** — canvas PDF, no text layer; the stale-tab fix does not apply. |
| AL, MS, UT, KS, CT | **NO ROUTE** — unchanged; **all five deserve a retry in a fresh tab before being re-diagnosed**, since round 25's browser conclusions are now suspect. |
| ID | **CLOSED** — state outage. |
| IN | **ON HOLD** |

## 5. Method notes

- **A stale tab produces symptoms indistinguishable from a hostile site.** Hangs,
  timeouts, screenshot failures — all of which I attributed to publishers.
  **Create a fresh tab before diagnosing a site.**
- **The tab's own title was the evidence.** It had updated to the page I thought
  had failed to load. The signal was there and I read past it for four attempts.
- **Round 25's "three of four" was arithmetic on a bad premise.** Two of those
  three failures were mine. **The honest number is one genuine browser failure
  (Arizona's canvas PDF) out of four**, and I have corrected it here rather than
  leaving the more cautious-sounding claim standing because it flattered the
  write-up.
- **Reopen the closed ones.** Alabama, Mississippi, Utah, Kansas and Connecticut
  were all judged partly on browser behaviour. That judgement now needs redoing.
