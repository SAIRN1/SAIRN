# SAIRNsenior — Guardian pass, the PDF unblock, and what CMS's guidance actually says

2026-08-30. **Guardian v2 full pass, one tooling fix, two primary documents read,
and a real code change** — the last of which is *not* comment-only, unlike the
2026-08-29 change it follows. Fourth document in the series.

---

## 1. Guardian v2 — full pass on `api/_lib/sen-evv-readiness.js`

Run because the previous session declared the file's diff comment-and-string-only
and **asserted** it rather than proving it. Check count re-read from the skill's
own `## The 30 Checks` heading, not from CLAUDE.md.

### The assertion, now proven — and the method is the reusable part

A grep filter for "changed lines that are neither comments nor strings" is not
proof: it is a regex guessing at JS tokenisation. Replaced with a **tokeniser**
that strips comments and replaces every string/template literal with an empty
literal of the same kind, then compares.

**The self-test is what makes it evidence rather than another assertion:** the
stripped output must still pass `node --check`. A tokeniser that mis-reads a
regex literal or a string boundary produces a syntax error almost every time, so
a clean parse on the stripped file is real evidence the strip was correct.

    before.stripped.js   PARSES
    after.stripped.js    PARSES
    code-only sha256 (before) f3a570decaa94a8f6d7515904b6b1ab1c0454de925e7b90b01adf8409a8c8994
    code-only sha256 (after)  f3a570decaa94a8f6d7515904b6b1ab1c0454de925e7b90b01adf8409a8c8994
    IDENTICAL

**The 2026-08-29 diff was comment-and-string-only. Confirmed, not claimed.**
Tool kept at `scratchpad/gv/strip.py`; it is generic and worth promoting to
`tools/` if this comes up again.

### Results — 30 checks plus Check 0

**Check 0a — syntax.** `node --check` PASS. Single script, no HTML extraction
needed.

**Check 0b — fabricated values.** PASS. Every numeric literal in code is a
citation or a genuine count: `42`, `1396`(b), `1903`, `114`/`255`, `12006`,
`2016`, `2026`, `403`, `5`, `6`, `0`, `1`. No KPI is emitted without a function
behind it — `summarize` counts real rows, and the existing test
*"summarize counts REAL rows and never invents a denominator"* asserts it.

**Check 0c — multi-codebase drift.** N/A, settled platform-wide.

**Check 0d — dormant code.** PASS, and checked rather than assumed. Callers:
`api/sd-data.js:40` (`require`), `sairnsenior.html:1165` (the panel that renders
it), `tests/sairnsenior/test-evv-readiness.js`. Not dormant.

**Check 0e — pre-build duplication.** PASS. `grep -rln "checkVisit\|FEDERAL_ELEMENTS" api/` returns this file only.

| # | Check | Result |
|---|---|---|
| 1 | Proxy rule | **PASS** — 0 hits for `api.anthropic.com` |
| 2 | Bridge rule | **PASS** — 0 hits; no cross-app data path |
| 3 | `app_id` present | **N/A** — pure function library, issues no fetch |
| 4 | `is_demo` flag | **N/A** — same |
| 5 | No service_role key | **PASS** — 0 hits |
| 6 | Unicode box chars | **PASS** — 5 hits (lines 10, 24, 72, 149, 294), **all in `//` comments**; 0 survive comment+string stripping, so none is in a string literal. Exactly the false positive the check's own warning describes |
| 7 | Regex newlines escaped | **N/A** — no regex literals |
| 8 | No duplicate IDs | **N/A** — no HTML |
| 9 | No undefined handlers | **N/A** — no DOM |
| 10 | No const/let redeclaration | **PASS** — 3 top-level declarations, 0 duplicates |
| 11 | No `APP_ID` redeclaration | **PASS** — no `APP_ID` |
| 12–15 | Design (dark bg, colour, print, tints) | **N/A** — no markup or CSS |
| 16 | Inline `display:none` | **N/A** |
| 16–18 | Navigation (panels, `sbNav`, section map) | **N/A** |
| 19 | localStorage namespacing | **PASS** — 0 `localStorage` |
| 20 | `sdLoad`/`sdStore` try/catch | **N/A** |
| 21 | `JSON.parse` guarded | **PASS** — 0 `JSON.parse` |
| 22 | No API keys | **PASS** — 0 hits for key-shaped literals |
| 23 | `SAIRN_INTERNAL_KEY` | **RETIRED** — not run, per the skill |
| 24 | No `console.log` | **PASS** — 0 |
| 25 | `escHtml` on user content | **PASS** — module touches no DOM; its consumer at `sairnsenior.html:1204` maps every gap through `H()` |
| 26 | AI output escaped | **N/A** — no AI output |
| 27 | Dead-button audit | **N/A** — no buttons |
| 28 | Cross-app identifier collision | **PASS** — 0 hits for `verifySessionToken`, `expectedApp`, `MANAGEMENT_ROLES`, `'owner'`, `license_hash`. The module takes no identity input; its caller `api/sd-data.js` owns that gate |
| 29 | Storage-validator change needs a real write | **PASS** — 0 hits for `INVALID_`, `insert`, `update`, `upsert`, `supabase`, `fetch(`. `api/sd-data.js:2282` records that this path **writes nothing** |
| 30 | Env-var name drift | **PASS** — 0 `process.env` reads; `RESEND_FROM_ADDRESS` absent |

**Verdict: clean.** No blocking check failed; no check failed at all.

**Coverage disclosure, per 0b-coverage.** This is a 300-line pure-function module
with one caller and a 30-assertion test file, so the sweeps above are close to
exhaustive rather than pattern-sampled — a materially easier target than a
2 MB app file, and the clean result should be read with that in mind.

---

## 2. The PDF blocker — solved, and my own diagnosis of it was wrong

The last document called this "the single highest-leverage tooling gap" and said
mass.gov was a *request-fingerprint* block because "curl with a browser
user-agent also gets 403."

**That was wrong, and wrong in the expensive direction.** It is a **header-set**
check. A bare curl fails; a curl sending only `User-Agent` fails; a curl sending
the full browser header set **succeeds**:

    Accept, Accept-Language, Accept-Encoding, sec-ch-ua, sec-ch-ua-mobile,
    sec-ch-ua-platform, Sec-Fetch-Dest/Mode/Site/User,
    Upgrade-Insecure-Requests, Referer

    mass.gov 105 CMR 155 PDF      -> 200  118,257 bytes  application/pdf
    medicaid.gov CIB  2018-05-16  -> 200  168,538 bytes  application/pdf
    medicaid.gov FAQ  2018-05-16  -> 200  200,988 bytes  application/pdf

**"Request fingerprint" implies TLS-stack or IP reputation and sends the next
reader to browser automation. "Header check" is four extra headers.** I had
tested one hypothesis (UA) and named a different, larger one. PowerShell
`Invoke-WebRequest` with a UA still 403s, which is consistent — it is missing the
same headers, not blessed by a different TLS stack.

Text extraction is then just `pypdf`, already installed. **No browser needed at
all**, and the canvas-viewer problem that consumed five attempts across two
sessions was never on the critical path.

Reusable: `scratchpad/gv/fetchpdf.sh`. Worth promoting to `tools/`.

---

## 3. Massachusetts — 105 CMR 155 CLOSED

**Tier 1, primary, read from the regulation PDF.**

**Scope, § 155.002.** Applies to long-term care facilities licensed under
M.G.L. c. 111 § 71, hospice programs under § 57D or § 51, **and home health
agencies and homemaker agencies**. §§ 155.004–155.012 bind *all individuals
working in or employed by* those entities; §§ 155.013–155.015 bind **only nurse
aides, home health aides and homemakers**.

**§ 155.010(E)(3) — the registry check, and it is a pre-hire duty:**

> "All home health agencies, homemaker agencies, and hospice programs shall
> contact the Registry prior to hiring an individual who will provide direct care
> to patients or have access to patients or their property to ascertain if there
> is any sanction, finding or adjudicated finding of patient or resident abuse,
> neglect, mistreatment or misappropriation of patient or resident property…"

**§ 155.010(E)(4)** then prohibits hiring or employing anyone listed with such a
finding (subject to § 155.014(A)(2)), or during any imposed sanction period.

**§ 155.010(G)(3) — CORI**, as a preventive-policy duty: obtain all available
criminal offender record information "on an applicant **under final
consideration** for a position that involves the provision of direct personal
care or treatment."

**§ 155.016 — the Registry.** DPH maintains it; it carries documented and
adjudicated findings against **nurse aides, home health aides and homemakers**,
the accused's own dispute statement if offered, suspension/probation dates, and
known court findings. Note **§ 155.015**: a sanctioned individual may petition
for removal **after one year**, and DPH must find no pattern and that the
original neglect was a single occurrence.

**Where this lands in the pathways model.** Massachusetts adds a **fourth axis**
the other states did not force: not a training pathway, not a criminal check, but
a **state-run adverse-findings registry with a pre-hire query duty and a hiring
prohibition**. A model with only "training route" and "background check" fields
cannot represent it. **The registry query is an event with a date and an outcome,
and it must precede the hire.**

---

## 4. CMS EVV guidance — 2 of 10 documents read

**Tier 1, primary.** CMCS Informational Bulletin and FAQ, both **2018-05-16**.

**The scope carve-out nobody would infer from the statute (FAQ Q3, Q5).** CMS
*"interprets the reference in the statute to an 'in-home visit' to exclude PCS
provided in congregate residential settings where 24 hour service is
available"* — group homes, assisted living — reasoning that a congregate
employee serves multiple individuals across a shift and is typically reimbursed
per diem rather than per visit. **PACE is also out.** A visit is not in EVV scope
merely because it is a Medicaid personal care visit.

**There is no federal GPS requirement (FAQ Q15).** *"The Cures Act does not
require states to capture each location as the individual is moving throughout
the community"*; capturing where service **starts and stops** is *"sufficient for
meeting the minimum requirements."* CMS names **Interactive Voice Response** as a
common alternative. States may require more.

**No uniform system (FAQ Q8, Q13; CIB "EVV Models").** § 12006(c)(2) bars
construing § 1903(l) to require a particular or uniform system — and CMS reads
that as binding **on CMS**, not as barring a state from choosing one. Five models
are described: **Provider Choice, MCP Choice, State Mandated In-house, State
Mandated External Vendor, Open Vendor.** The CIB names twelve states plus DC on
the state-mandated-external-vendor model: **Arizona, Connecticut, Florida,
Illinois, Kansas, Mississippi, Montana, Ohio, South Carolina, Washington, West
Virginia, District of Columbia.**

**The good-faith-effort relief is narrower than the landing page implies (CIB,
Background).** It is *"a limited exception for the first year of the
requirement"*, against an FMAP reduction phased across the first five years
reaching 1 percent.

**Territories are in (FAQ Q2)** — DC, Puerto Rico, the Virgin Islands, Guam, the
Northern Mariana Islands, American Samoa.

**Still unread:** the August 2019 "Additional EVV Guidance" CIB, the December
2022 good-faith-effort exemption guidance, the May 2022 1915(c) documentation
note, and five presentation decks.

---

## 5. The code change — and it is NOT comment-only

`api/_lib/sen-evv-readiness.js` gained **two new `residual_gaps` entries**: the
congregate-setting scope carve-out and the no-federal-GPS-requirement point. The
tokeniser reports **CODE CHANGED**, correctly — array element count is structure,
not prose. Said plainly because the previous change was comment-only and it would
be easy to carry that description forward by habit.

**Three tests failed immediately**, all asserting `residual_gaps.length === 2`.
That is the tests working: the payload really did change, and
`sairnsenior.html:1204` renders every gap as a list item, so the screen gains two
bullets.

**The assertions were made stronger, not looser.** An exact count turns *"we
disclosed more"* into a failure — pressure in exactly the wrong direction for a
module whose entire purpose is honest disclosure. Replaced with `length >= 4`
plus a **named assertion for each of the four gaps**: the CMS-guidance gap, that
the guidance is only *partly* read, the statutory-silence inference, the
congregate carve-out, and the GPS point. **Adding a fifth gap now passes;
deleting any existing one fails.** The count assertion could not catch a
deletion-plus-addition; this can. In the roll-up test the count was replaced by a
comparison against the per-visit result, since that test's real subject is object
identity and a literal there only restated what `assertEq(s.federal_source,
r.federal_source)` already proved.

**Verified after:** `node --check` on both files, **30 passed / 0 failed**.

**The scope carve-out is disclosed, not implemented, and the disclosure says so.**
This module is handed a visit and cannot know the setting, so it cannot apply
FAQ Q3 itself. A caller feeding it congregate-setting visits gets well-formed
answers about visits CMS does not require EVV for. Naming that in
`residual_gaps` is the honest move; silently filtering on a field the module does
not receive would be worse.

---

## 6. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| 8 of 10 CMS EVV documents | **UNREAD** | Now purely a reading task — the fetch method works on all of them. |
| Which EVV model each state uses **today** | **STALE AT BEST** | The twelve-state list is from a **2018** bulletin. Do not present it as current; medicaid.gov has per-state compliance-status pages that supersede it. |
| MA c. 151 § 1A hospital/nursing-home exemption wording | **SUMMARISED, NOT QUOTED** | Carried unchanged. Now cheap to close with the working fetch. |
| NY 40/75 hour figures | **STILL UNVERIFIED** | Needs 18 NYCRR 505.14. |
| TX unlicensed personal assistant requirements | **UNRETRIEVED** | Appian portal still unusable. |
| NJ, municipal ordinances, ~35 states | **NOT ATTEMPTED** | Next. |

## 7. Method notes

- **Prove a diff-shape claim with a tokeniser whose output still parses.** A grep
  filter is a guess; a stripped file that passes `node --check` and hashes
  identically is evidence.
- **Test the hypothesis you name.** "UA alone fails" does not license "request
  fingerprint". Naming a bigger blocker than you tested sends the next reader to
  a harder tool.
- **An exact-count assertion on a disclosure list is a trap.** It makes telling
  the caller more into a test failure. Assert each item by name.
- **The five-attempt browser workaround was never needed.** Before escalating to
  automation, re-test the cheap client with *complete* inputs.
