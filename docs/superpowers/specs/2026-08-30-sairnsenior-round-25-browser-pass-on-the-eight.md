# SAIRNsenior — round 25: a fresh-angle pass at the eight diagnosed states

2026-08-30. **Research only.** Thirty-eighth document in the series.

Depth, not breadth: the eight states with a diagnosis and no answer. **One
genuinely moved** — South Dakota's browser route works and its home-health
chapter is now identified. **The browser is not a universal key**, which is
itself the useful result.

---

## 1. South Dakota — the browser route works, and the chapter is found

**`get_page_text` in Chrome renders the Vue SPA fully.** Two pages retrieved at
~50 KB each:

- **`/Statutes/34`** — the full Title 34 chapter list.
- **`/Statutes/34-12`** — *Regulation of Hospitals and Related Institutions*, in
  full.

**The chapter I had been probing for eleven rounds was the wrong one.**
SDCL **34-12** licenses *institutions* — its own list runs to hospitals, birth
centers, ambulatory surgery centers, chemical dependency treatment facilities,
nursing facilities, **assisted living centers**, rural primary care hospitals,
**adult foster care homes**, inpatient hospice, **residential hospice**,
freestanding emergency care facilities and more. **Home health is not among
them.**

**Title 34's chapter list gives the right answer: ch. 34-03A, "Home Health
Services."** *(Between 03 "County and District Full-Time Health Departments" and
03B "County and Municipal Drug Education Programs".)*

> **Eleven endpoint forms were excluded across rounds 21–23, and every one of
> them was for chapter 34-12** — a chapter that does not regulate home health.
> **The route and the citation were both wrong, and only the route was being
> debugged.** The same compound failure as North Dakota, where the `.pdf`
> extension fixed the route and delivered a repealed chapter about cooperative
> agreements.

**Ch. 34-03A itself would not render.** `/Statutes/34-03A` and `/Statutes/34-3A`
both hang — `document_idle` never fires, and a screenshot times out, across four
attempts with waits up to eight seconds. **Title 34 and chapter 34-12 render
fine on the same host in the same session**, so this is specific to that chapter
page, not to South Dakota.

**Net position:** route proven, correct citation identified, **content still
unread**. That is three steps forward from "SPA, blocked".

---

## 2. Alaska — the browser is not the answer either

`akleg.gov/basis/aac.asp#7` loaded in Chrome and then **never reached
`document_idle`**; `find` timed out after 45 seconds.

> **The same failure mode as Arizona's PDF viewer and South Dakota's 34-03A.**
> Three states now where Chrome renders something and the automation cannot read
> it. **"Use the browser" is a fresh angle, not a master key** — worth recording
> plainly, because the temptation after South Dakota's success is to assume it
> generalises.

---

## 3. The other six — angles tried this round

Each was given one fresh, non-repeating angle rather than a retry of what already
failed.

| State | Fresh angle | Result |
|---|---|---|
| **Utah** | the SPA's own API path — `adminrules.utah.gov/public/api/rule/R432-700` | **200, 2,224 bytes — the same shell.** The API path returns the app, not data. |
| **Kansas** | direct year/title PDF — `sos.ks.gov/publications/kar/2024/28.pdf` | **200 but `text/html`, 4,990 bytes** — a soft-200 HTML page where a PDF was requested. |
| **Connecticut** | bypass the regs portal for a DPH-published PDF on `portal.ct.gov/-/media/...` | **200 but `text/html`, 7,417 bytes** — another soft-200. |
| **Alabama** | the SPA's API — `admincode.legislature.state.al.us/api/agencies` | **404, 136 bytes** — a real 404, not the shell. Different answer, wrong path. |
| **Mississippi** | a different admin-search entry point — `sos.ms.gov/adminsearch/ACProposed.aspx` | **404** |
| **Idaho** | *(not retried — closed as a state-declared outage)* | — |

**Two of those are worth separating from the rest.** Kansas and Connecticut both
returned **HTML with a 200 where a PDF was requested** — the soft-200 shape
again, now seen in five states (Alabama, Connecticut, Rhode Island's statute
host, Kansas, and Connecticut's portal). **Alabama's 404 on its API path is
progress of the same kind as South Dakota's `mylrc` 404**: a different answer
means the host is real and the path is wrong.

---

## 4. Where the eight now stand

| State | Before this round | After |
|---|---|---|
| **South Dakota** | SPA, 11 endpoints excluded | **Route proven (browser); correct chapter identified (34-03A); content unread** |
| **Alaska** | index server-side, content client-side | **Confirmed: browser does not resolve it either** |
| **Alabama** | LexisNexis-gated | API path returns a real 404 — host real, path unknown |
| **Mississippi** | LexisNexis-gated | second entry point 404s |
| **Utah** | publisher SPA | its own API path serves the app, not data |
| **Kansas** | index is chrome only | direct PDF path is a soft-200 |
| **Connecticut** | soft-200 on the regs portal | second publisher also soft-200 |
| **Idaho** | state-declared outage | unchanged, deliberately not retried |

**One moved materially, one was definitively closed off, six advanced by
elimination.**

---

## 5. Tier 2

| Item | Status |
|---|---|
| **SDCL ch. 34-03A content** | **IDENTIFIED, UNREAD** — the chapter page hangs in Chrome while its siblings render. |
| SD reclassification check | **NOT RUN** — no chapter text yet. |
| Alaska 7 AAC 12 / AS 47.32 | **NO ROUTE** — curl and browser both fail. |
| AL, MS, UT, KS, CT | **NO ROUTE** — one fresh angle each excluded this round. |
| ID | **CLOSED** |
| IN | **ON HOLD** — credential decision. |

## 6. Method notes

- **Debugging the route while the citation is wrong wastes the whole effort.**
  Eleven South Dakota endpoint forms were tested against a chapter that does not
  regulate home health. **Confirm the citation from the index *before* investing
  in the transport.** North Dakota taught this once; South Dakota is the second
  and more expensive instance.
- **A success does not generalise.** The browser opened South Dakota's title list
  and one chapter, and failed on Alaska, on South Dakota's own 34-03A, and
  previously on Arizona. Three of four.
- **A 404 is better news than a 200.** Alabama's API 404 and South Dakota's
  `mylrc` 404 both mean a real host and a wrong path. The 200s — Utah's shell,
  Kansas's and Connecticut's HTML-for-PDF — say nothing at all.
