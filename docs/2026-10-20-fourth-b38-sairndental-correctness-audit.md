# SAIRNdental correctness audit — GFE, denials, credentialing

**fourth / ted, batch b38, 2026-10-20.** These three panels were *read from the
registry* in b36's competitive-gap audit and never audited. b36 said so:
*"existing and being right are different claims."* This closes that.

**THE CRITERION FOR EACH PANEL WAS WRITTEN DOWN BEFORE ITS CODE WAS READ**, so
it could not be bent to whatever the code turned out to do:

| panel | what *correct* means, in one line |
|---|---|
| **GFE** | the estimate handed to the patient is derived from the same fee/coverage data the practice will actually bill, and is dated and scoped so **"this estimate is still valid" can never be shown for one outside its statutory window** |
| **Denials** | a denial's reason and its appeal deadline come from the payer's **own adjudication and the right start date**, so an expired appeal window can never render as still-appealable |
| **Credentialing** | a provider reads as able to bill a payer only when **every requirement that payer actually imposes is on file AND unexpired**, with an expiry making them non-billable rather than merely flagged |

**RESULT: THREE FINDINGS, ALL THE SAME CLASS, AND DENIALS IS CLEAN.** Two
panels have a summary that cannot distinguish *nothing is wrong* from *the
question was never answered* — and in both cases **the data needed to tell them
apart is already on the record.**

**These panels are better built than the audit expected.** The findings are in
the summary layer, not the law: the CFR citations are real and paragraph-level,
the two overlapping limbs of 149.610(b)(1)(vi) are disclosed rather than
resolved, federal holidays are computed rather than tabled, and the
credentialing board refuses to guess a CE requirement for a state whose rules
are not loaded. **Nothing below is a fabricated-KPI finding.**

**NOT FIXED. The dispatch said AUDIT.** Each finding carries a pasteable fix;
applying them is one decision away and would open a Tier A review obligation.

---

## 1. GFE — **MARKING AN ESTIMATE "ISSUED" ERASES THE EVIDENCE IT WAS LATE**

**Severity: real.** The whole obligation in 45 CFR 149.610(b)(1)(vi) is a
*date*. This panel tracks whether the estimate was eventually issued and drops
whether it was issued in time — using a field it already stores.

**`issueGfe()` (`sairndental.html:5131`) DOES record the date:**

```js
rec.status='Issued'; rec.issued_at=dntLocalToday();
```

**And nothing anywhere compares `issued_at` to `dueDate`.** Three places drop
it, all in `rGfe()`:

```js
// :5241  overdue is only computed for records that are NOT issued
if(d.applies && g.status!=='Issued'){ ... if(due<=today){dueCount++;overdue=true;} }

// :5252  an Issued row's due-date badge is neutral no matter when it went out
'<span class="badge '+(g.status==='Issued'?'bx':(overdue?'br':'bw'))+'">'

// :5268  the KPI and the nav badge count only un-issued records
if($('k-gfe-due'))$('k-gfe-due').textContent=dueCount;
```

**So a practice that issued every estimate three weeks past its due date shows
a clean panel, a zero "Due" tile and no nav badge.** The lateness is not
mis-stated — it is *absent*, which is the harder kind to notice. The record
knows; the screen does not.

**PASTEABLE FIX** — one derived value, no schema change, no new field:

```js
// Was this estimate issued INSIDE its window? `issued_at` has been recorded
// since the panel shipped and nothing has ever read it.
var lateBy = null;
if (d.applies && g.status === 'Issued' && g.issued_at) {
  lateBy = Math.round((new Date(g.issued_at + 'T00:00:00') -
                       d.dueDate) / 86400000);
}
// badge: issued-on-time -> 'bg', issued late -> 'br' with "+N d late",
// issued with no date on file -> 'bw' "issued, timing not on file".
```

**AND A SECOND, SMALLER DEFECT ON THE SAME LINE.** `if(due<=today)` treats an
estimate **due today** as overdue. It is not — the day is not over. This
over-counts `dueCount` by one day per record, and `dueCount` drives the nav
badge. It fails *safe* (over-alarming, not under-alarming) and is still wrong:
`due < today`.

**WHAT I CHECKED AND FOUND CORRECT in the same panel**, so the finding is not
mistaken for a verdict on the whole thing:

* **Charges come from the real fee data** — `addGfeLine()` defaults
  `expected_charge` to `p.default_fee` from `procedureTypes()`, the same store
  the practice bills from, and allows an explicit override. My criterion's
  first half holds.
* **The deadline is RECOMPUTED at render from the stored dates**, never frozen
  at save, so it cannot go stale.
* **`gfeMissing()` cites paragraphs, not "incomplete"**, and `issueGfe()`
  **REFUSES** rather than warning when an element is missing — the comment
  gives the reason, and it is the right one.
* **`practice_address` is a real key**, written by Booking Settings at `:3714`
  and read at `:5002`/`:5211`. No cross-panel key mismatch — this was checked
  because a wrong key name here would report a missing address forever.
* **`gfeEligibility()` gets the hard part right**: an insured patient who is
  not submitting a claim *is* owed an estimate under (a)(2)(xiii), and the
  panel says **ASK** rather than deciding.
* **Business-day arithmetic is weekday-only and holidays are reported, never
  applied silently**, with the reason stated. The eleven 5 U.S.C. 6103
  holidays are **computed with observance shifts**, not a table that goes stale.

---

## 2. DENIALS — **CLEAN AGAINST THE CRITERION. No finding.**

`dnAppealWindow()` (`:3954`) does exactly what the criterion asks:

* the window starts at **`d.denied_on`** — the payer's adjudication date, not a
  created-at;
* its length comes from the **per-payer contracted term**, and when there is
  none it returns `known:false` with *"Appeal deadlines come from your contract
  and differ between payers, so none is assumed"*. **An unknown window is a
  third state and is never rendered as timely.**
* no denial date → `known:false` with *"the window cannot be counted from
  anywhere."*

**Two robustness points checked rather than assumed:**

* **`dnPayerTermFor()` matches trim + lowercase** (`:3934`), so `"Delta Dental "`
  and `"delta dental"` resolve to the same term. An exact-match lookup here
  would have lost a payer's window on a whitespace difference, silently.
* **Date math is local-midnight** (`dnAddDays`, `dnDaysUntil`), so there is no
  UTC off-by-one on the deadline.

**And the panel is unusually honest in two places that are easy to get wrong:**
a closed window renders **`closed N d ago` and the row is still listed** — with
the reason given, *"an appeal that can no longer be filed is a figure the
practice should see, not one the software quietly drops"* — and `abandoned` is
excluded from **both halves** of the success rate rather than counted as a loss.

---

## 3. CREDENTIALING — **FOUR ZEROS RENDER WHEN NOTHING HAS BEEN CHECKED**

**Severity: real, and the failure is permanent rather than transient whenever
the evaluation cannot run.**

The four KPI tiles are hardcoded `0` in the markup (`:523-526`):

    Expired 0 | Expiring Soon 0 | CE Behind Pace 0 | MATE Outstanding 0

`nav('credentials')` calls **`rCredentials(null)` first** (`:2041`) and then
starts the async board. On the `null` path `rCredentials` **returns at `:3075`
before touching any KPI**, so the four zeros stand.

**That is correct and harmless for the second before the board arrives. It is
not harmless when the board never arrives — and `sdnEvaluateCredentials()`
(`:2908`) returns `null` on FOUR separate failures, every one of them silent to
the user:**

| | condition | line |
|---|---|---|
| 1 | **no licence key on this install** | `:2910` |
| 2 | any non-ok HTTP status | `:2919` |
| 3 | an ok status with a non-ok body | `:2919` |
| 4 | **any network error** | `:2921` |

All four `console.warn` and return `null`. **So on a workstation with no
licence, or with the server unreachable, or with `dnt_credentials` not
provisioned, the Credentialing panel shows four zeros — the strongest possible
all-clear — above a table whose every row reads "Not checked yet".**

**THE TABLE IS HONEST AND THE SUMMARY IS NOT, AND THE SUMMARY IS WHAT GETS
READ.** The nav badge is hidden on the same path, which is indistinguishable
from "nothing to action".

**PASTEABLE FIX** — the `null` branch must assert the third state rather than
leaving a stale zero:

```js
if(!board){
  // ... existing local table render ...
  ['k-cred-expired','k-cred-expiring','k-cred-ce','k-cred-mate']
    .forEach(function(id){ var el=$(id); if(el){el.textContent='--';
      el.title='Not evaluated: the credential board could not be reached.';} });
  // and the nav badge must say COULD-NOT-CHECK, not nothing:
  var b=$('credentials-badge');
  if(b){ b.textContent='?'; b.style.display=''; }
  return;
}
```

**`--` and `?`, not `0`.** *Could not run* is a third state and must never be
folded into *passed* — which is **PR §1.11** applied to a KPI tile instead of a
gate.

**WHAT IS GENUINELY WELL BUILT HERE, and it is most of the panel:**

* **An enrolment row carries TWO statuses and shows both** (`:3094`), and the
  comment names the exact hazard my criterion was written for: *"Showing only
  the first would let a terminated enrolment read as 'OK' because its
  revalidation date is far off."* That is the criterion, already understood.
* **No CE requirement is guessed.** With no rules loaded, `rCredRules()` says
  so and says CE cycles must carry their own hours — *"this app will not guess
  a number for your state."*
* **Uncovered states are named** — *"Nothing is claimed about those states."*
* **MATE attestation** is surfaced as its own badge, and only on
  `dea_registration` where it belongs.
* **The local (`!board`) table says "Not checked yet" per row** rather than
  rendering a status it has not computed. The *rows* get this right; only the
  summary does not.

---

## 4. THE PATTERN ACROSS ALL THREE, WHICH IS THE REAL RESULT

**Both findings are the same defect in two places: a compliance summary that
collapses three states into two.**

| | the three states | what is rendered |
|---|---|---|
| GFE | issued on time / issued late / not issued | **on time == late** |
| Credentialing | nothing wrong / nothing known / something wrong | **nothing wrong == nothing known** |

**Neither is a wrong number and neither would be caught by a fabrication
check** — every figure traces to a real function. They are
`sairn-silent-failure-sweep` findings: *real functions reporting a state they
never established*. And in both cases **the missing information is already on
the record** (`issued_at`; the four `null` conditions), so both fixes are a
render change and nothing deeper.

**Denials is the control that makes this a finding rather than a style
preference.** The same codebase, the same author, the same week — and it keeps
all three states apart deliberately, says so in prose, and explains why it
refuses to assume. The capability is present in the file; it just was not
applied to the other two summaries.

---

## 5. WHAT THIS AUDIT DID NOT ESTABLISH

* **Nothing was driven.** This is a source read. No GFE was issued, no board
  evaluation was forced to fail, no denial was aged past its window. **The
  credentialing finding in particular would be settled in a minute by blanking
  the licence key and opening the panel**, and that was not done.
* **The server half of credentialing was not audited.** `action:'evaluate'` on
  `dnt_credentials` in `api/sd-data.js` computes the whole board, and that file
  is **cody's** — the audit stops at the client boundary and makes no claim
  about the evaluation itself.
* **The three panels' SQL and write paths were not audited**, only the render
  and the helpers each panel computes from.
* **No legal review.** The CFR paragraph citations were read as *present and
  specific*, and spot-checked for internal consistency. **I did not verify
  against the regulation that each cited paragraph says what the code says it
  says** — that is a different and stronger check, and the GFE panel's own
  handling of the overlapping (A)/(B) limbs suggests whoever wrote it read the
  text more carefully than this audit did.
* **The other 20 panels were not audited.** Three were named; three were done.
