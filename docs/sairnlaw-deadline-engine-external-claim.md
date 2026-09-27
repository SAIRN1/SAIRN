# SAIRNlaw deadline engine — approved external-facing claim

**Updated 2026-09-26 (Fourth). The 2026-08-24 version had gone stale in THREE
directions at once, and two of them were overstatements in a document whose
stated purpose is proposals and sales conversations.** The header of that version
opens by recording that the one before it "had gone four phases stale." It
happened again, which is the argument for the measurement block below rather than
for a fourth apology.

**WHAT WAS WRONG, each measured rather than estimated:**

| The 2026-08-24 claim said | Measured 2026-09-26 | Direction |
|---|---|---|
| "eleven jurisdictions … from 119 rules" | **39 jurisdictions, 437 rules** across 47 seed files | UNDERSTATED, 3.7x |
| "Every jurisdiction carries both domains" | **12 of 39** carry both; 27 are civil-litigation only | **OVERSTATED** |
| "a holiday calendar for 2026 through 2031" | **16 of 34** calendar files reach 2031; 15 carry **2026 only** | **OVERSTATED** |

The understatement cost a sale nobody made. **The two overstatements are the
serious ones**: this sentence promised appellate coverage in 27 jurisdictions that
have none and five extra years of holidays that were never emitted — and the
Alabama calendar's own `_readme` says "2027 IS NOT EMITTED" in those words. On a
deadline product a missing holiday year is safe in the ENGINE, which refuses; it
is not safe in the CLAIM, which said it was covered. A firm that relied on the
sentence for appellate work in a civil-litigation-only jurisdiction would find
out from a refusal, not from us.

**RE-DERIVE THE NUMBERS, DO NOT QUOTE THEM FROM HERE.** That is the whole lesson
of three stale versions. The jurisdiction and rule counts come from the seed
files, which are the authority:

```
python - <<'PY'
import json, io, glob, collections
seeds = sorted(glob.glob('sql/sairnlaw_deadline_seed_*.json'))
rules, doms = 0, collections.defaultdict(set)
for p in seeds:
    d = json.load(io.open(p, encoding='utf-8'))
    for r in (d.get('rules') if isinstance(d, dict) else d) or []:
        rules += 1
        if r.get('jurisdiction') and r.get('domain'):
            doms[r['jurisdiction']].add(r['domain'])
print('seed files', len(seeds), '| rules', rules, '| jurisdictions', len(doms))
print('both domains', sum(1 for j in doms if len(doms[j]) >= 2), 'of', len(doms))
PY
```

### The rest of the document swept for the same shape, 2026-09-26

Item 9 found one instance. **The whole file was then swept for other sentences
whose universal word might have outlived its scope.** Three results, and one of
them is the sentence surviving, which is worth as much as the two corrections:

**1. THE PROVENANCE CLAIM IS SOUND ACROSS ALL 437 — measured, not assumed.**
*"every one of them encoded from primary-source rule text read verbatim, with a
full audit trail from the date back to the authority that produced it"* is the
sentence the launch-blocker section below says the entire claim rests on, and it
was the likeliest candidate to have been true of 119 and not of 437. It holds:
**all 437 rules carry an `authority` object with BOTH a `citation` and a `url`,
437 distinct values, zero placeholders** — no `TBD`, no missing field, nothing
under eight characters. The audit-trail half is verifiably complete.

One honest qualification: **no rule stores the verbatim text itself.** "read
verbatim" is a claim about how a human encoded it, not about a stored field, so it
is not falsifiable from the data either way. It is left standing because it is a
true statement about process, but a reader should know the repo cannot prove it —
only the citation and URL can be checked.

```
python - <<'PY'
import json, io, glob, re
n = weak = 0
for p in sorted(glob.glob('sql/sairnlaw_deadline_seed_*.json')):
    d = json.load(io.open(p, encoding='utf-8'))
    for r in (d.get('rules') if isinstance(d, dict) else d) or []:
        n += 1
        a = (r.get('authority') or {})
        if not (isinstance(a, dict) and a.get('citation') and a.get('url')): weak += 1
print('rules', n, '| without a citation+url authority', weak)
PY
```

**2. THE FAILURE-MODE TALLY SAID "six gates" AND THERE ARE NOW SEVEN.** Corrected
below, and the correction is the finding: a numbered list grew and the word
counting it did not move — which is mode 7 happening to the list that describes
mode 7. The instruction is now to count the entries rather than read the word.

**3. "The engine encodes the statutory test IN EVERY CASE"** in §3 of the
demonstrations was the same shape beginning again. True about METHOD — no calendar
here is built from an attendance record — and readable as coverage in a sales
document, when roughly half the calendars stop at 2026. Narrowed to "for every
calendar it carries."

**What the sweep method was, so it can be repeated:** grep the file for `every`,
`all`, `each`, `no`, `none`, `always`, `never`, then for each hit ask the one
question that separates this mode from ordinary staleness — *what set was this
quantifying over when it was written, and has that set grown since?* A sentence
that was never true is an error; a sentence that stopped being true because the
product grew is this mode, and it has no author to blame.

---

This is the sentence to use with anyone outside the team — proposals, sales
conversations, status updates. Do not paraphrase it looser, and do not quote its
figures without re-running the block above.

> The deadline engine computes litigation deadlines across **39 jurisdictions,
> including the federal rules, from 437 rules** — every one of them encoded from
> primary-source rule text read verbatim, with a full audit trail from the date
> back to the authority that produced it. No language model is anywhere in the
> computation. **Coverage is per jurisdiction and is not uniform: 12 of the 39
> carry both civil-litigation and appellate rules, and the remaining 27 carry
> civil litigation only. Holiday calendars likewise vary — roughly half reach
> 2031 and the rest currently carry 2026 alone.** Every calendar is built from
> the statute that defines a legal holiday rather than from a court's published
> closure schedule, because those two lists genuinely differ. The engine refuses
> rather than estimating anything it does not cover — a missing rule, a missing
> holiday year, an ambiguous rule set, or a rule that sets no deadline at all.
> **It computes from the trigger date it is given and does not verify that the
> date means what the rule requires; where a rule runs from a legally computed or
> defined event, the user must supply that event's date, and the engine will not
> detect a wrong one.** Appeal periods in particular are not portable across state
> lines: Michigan allows twenty-one days, Pennsylvania ten in three named subject
> matters, Texas twenty for an accelerated appeal, and the clock starts from a
> different event in five different states.

**"Civil-litigation and appellate" became "litigation", and the per-jurisdiction
sentence carries the detail.** One adjective covering two dimensions is the
failure mode this file's own history names; a blanket "both domains" was that
adjective doing it again.

---

## The positioning this claim USED to rest on, and why it has moved

**Do not lead with jurisdiction scale, and do not present the citator as
something competitors lack.** Both were reasonable positions and both have been
overtaken.

- **Jurisdiction scale.** Clio ships a native court-rules / deadline capability.
  39 jurisdictions is a real engineering fact and a poor differentiator: it is a
  number a funded competitor can match by buying data, and a prospect cannot tell
  two coverage tables apart in a demo.
- **A shipped citator.** Clio's roughly **$1B acquisition of vLex (2025)** —
  reported as the largest private legal-tech transaction to date — gives them a
  real citator with a research corpus behind it. "We have a working citator" is
  no longer a distinguishing sentence; theirs is bigger.

**WHAT THE ABOVE RESTS ON, STATED SO NOBODY OVER-READS IT.** Third-party reports
gathered in `docs/cloud-research/SAIRNlaw-external-competitive-gap-audit-2026-09-25.md`
§6. **No vendor page was fetched in that pass** — Clio's own domain was blocked,
as that document says on its first page. So this is "assume a well-funded
competitor has parity or better", which is the right planning posture, and NOT a
verified feature comparison. It would be a mistake to tell a prospect what Clio
does or does not do on this evidence.

### The two things that are actually still ours to claim

**1. THE US + ENGLAND & WALES COMBINATION, UNDER LICENCES THAT PERMIT IT.** The
citator resolves US authority through CourtListener and England & Wales through
**Find Case Law (The National Archives)** under the Open Justice Licence, which
expressly permits commercial use and incorporation into a product. That
combination is narrow, it is deliberate, and it is durable for a reason that has
nothing to do with engineering: `docs/sairnlaw-international-coverage-scope.md`
records that Australia, Scotland, Northern Ireland and Ireland are excluded by
their sources' own written terms — AustLII names AI uses, BAILII names this
product category — and CanLII has sued an AI legal-research platform over
scraping. **A competitor cannot buy its way past a written prohibition, and one
that routes around it has a different problem than we do.** Say the combination
and say the licence; do not imply broader international coverage.

**2. NATIVE INTEGRATION — ONE APP, NOT AN INTEGRATION.** The deadline engine, the
citator, the matter record, the conflict check and the IOLTA three-way
reconciliation are the same application, so a computed deadline lands on the
matter and a verified citation is checked before it is displayed as authority,
without a connector, a sync window or a second vendor relationship. This is the
claim that a consolidating market makes *stronger* rather than weaker — the
competitive signals in that same audit §6 are acquisitions and partnerships
(vLex, Harvey–LexisNexis, Smokeball–Thomson Reuters), which is integration work
somebody still has to finish.

**Say "native" only where it is true.** SAIRNlaw carries **no payments
integration at all** (same audit, §6) and its trust reconciliation is explicitly
**table stakes rather than a differentiator** — that document's own words, §2.7.
Claiming a unified suite and then being asked about payments is worse than not
claiming it.

### What NOT to say

- Not "the only", "no other platform", "unmatched", or any exclusivity framing.
  Nothing in either audit supports an exclusivity claim, and §4 of the external
  audit labels its one candidate differentiator — the intake conflict check's
  blocking override — a **candidate, not a confirmed one**, pending a follow-up
  pass it asks for and has not had.
- Not a jurisdiction count as a headline.
- Not "we have a citator" as a differentiator; the citator is now support for the
  US+UK claim, not the claim itself.

---

## 🚫 PRE-LAUNCH BLOCKER — SAIRNlaw cannot onboard a paying customer until this is closed

**Named 2026-08-29. Michael's decision, made with the gap in front of him: leave
it open for now, because every licence on these tables today is internal. It
becomes a hard blocker the moment one is not.**

**The gap.** `api/legal-deadlines.js` writes `law_deadline_rules` and
`law_holidays` — the two tables this entire claim rests on — with **no
authenticated write path at all**. The `add_rule` (`:698`) and `add_holidays`
(`:717`) actions require only a valid `Authorization: Bearer <licence key>`. The
endpoint *does* resolve a session at `:542`, but only to fill `verified_by` and
the audit line; **it is never enforced**. A write with no session succeeds and
stores `verified_by: null`.

Proven live 2026-08-29, writing nothing — the probe payload was built to fail
validation so it could not create a row:

```
POST /api/legal-deadlines   Authorization: Bearer LAW-PINNACLE-2026
{"action":"add_rule","rule":{}}
→ 400 {"ok":false,"code":"INVALID_RULE","message":"Missing required field: rule_id"}
```

A **400 from the payload validator, not a 401**, with no session token sent. It
cleared authorisation.

**Why this is a launch blocker and not a backlog item.** Every sentence in the
approved claim above — *"every one of them encoded from primary-source rule text
read verbatim, with a full audit trail from the date back to the authority that
produced it"* — describes provenance. Anything holding the licence key can
overwrite any of those 437 rules, and the column that records who verified it
will say `null`. `tools/sairn_load_state_check.py` would then correctly report
the licence as STALE against the repo **and would not be able to say who changed
it or when**. The audit trail is the product. A customer-held key that can
silently rewrite the authority is not a defect in a feature; it contradicts the
claim.

**What closing it requires — and the tradeoff that is why it is still open.**
Not simply adding `verifySessionToken` to those two actions. `tools/load_deadline_seed.py`
**depends on the bearer-key path**: needing only a licence key is exactly what
lets it run from any clone and gate a pre-push step, and that property was chosen
deliberately over the SQL gate it replaced (see the "WHY THIS ONE" note in
`tools/sairn_load_state_check.py`). So the close needs a real authenticated write
path that does not break loader-from-any-clone — a service-credential or
signed-loader route distinct from a customer's licence key — **not** a session
check bolted onto the existing action.

**Definition of done.** A non-interactive loader identity that is not a customer
licence key; `add_rule`/`add_holidays` refusing an unauthenticated write with 401;
`verified_by` never null on a stored rule; and this section deleted rather than
edited, with the gate re-run per the last section of this file.

**Do not treat "internal licences only" as a durable state.** It is true on
2026-08-29 and is the only reason this is deferred. The first real SAIRNlaw
prospect makes it false, and nothing in the codebase will announce that.

Tracked as a row in `docs/SAIRN-OPEN-WORK-INDEX.md` that points here; this file
is the authority on it.

---

## What this gate found, and the sixth distinct failure mode

**Failure mode six: a claim that is true about the rules and silent about the
inputs.**

The premortem question was *"someone outside the team relied on this engine, got
a wrong date, and pointed at our claim. What did they find?"* The honest answer
was not a coverage gap. It was this:

Every previous version of this claim described how carefully the **rules** were
encoded, and every word of that was true. None of them said anything about the
**trigger date the user supplies**, and the engine does not check it. Five
jurisdictions now start an appeal clock five different ways:

| Jurisdiction | The appeal clock starts on |
|---|---|
| Georgia | **entry** of the appealable decision or judgment |
| Texas | the **signing** of the judgment |
| Florida | **rendition** — a defined term of art, not the signature or mailing date |
| New York | **service** of the judgment **with written notice of its entry** |
| California | service of a notice of entry (two limbs), or 180 days from entry |

Hand the engine an entry date where New York wants service-of-notice-of-entry
and it returns a confident, fully-audited, **wrong** date. Same for New York's
CPLR 320(a) and 3012(c), which run from when *"service is complete"* — a date
CPLR 308 computes and this engine deliberately does not.

That is a real limit, it is the highest-consequence one in the product, and it
had never been in the claim. It is now in the claim, in the sentence itself
rather than in a footnote, because a reader who stops after the first two lines
must still have seen it.

**This is different in kind from failure modes one through five.** Those were all
about coverage — breadth, parity, permanence, one adjective carrying two
dimensions. This one is about the boundary of what the product is responsible
for. Naming it changes what a demo has to show: the trigger vocabulary is part
of the product, not a detail of the input form.

The running tally, none of these obvious without looking. **DO NOT QUOTE THE
COUNT FROM THIS SENTENCE — count the numbered entries.** It read "across six
gates" and a seventh was added on 2026-09-26 without the word being touched,
which is the seventh mode happening to the list that describes the modes:

1. **Phase 4** — a true statement implying more *breadth* than existed.
2. **Phase 5** — a true statement implying more *parity* than existed.
3. **Phase 6** — a previously-approved statement that became *false* because the
   product improved underneath it.
4. **Phase 7** — a statement true on one dimension and misleading on another,
   where one adjective could not carry both.
5. **Phase 8** — a statement describing a *permanent* limit in language that
   implied a *temporary* one.
6. **Batch 2** — a statement true about the *rules* and silent about the
   *inputs*, in a product where a wrong input produces a confident wrong answer.
7. **2026-09-26** — a statement that was **correctly scoped when written and
   became false by GROWTH rather than by editing.** "All eleven carry both
   domains" was true of the eleven it was written about; 28 jurisdictions were
   added, the sentence was not touched, and the approved claim above had already
   generalised it to all of them. **Nobody wrote anything false at any point.**
   This is the only mode on the list that needs no author — it arrives on its own
   if a universal word is left standing over a set that grows, which is why the
   fix was a runnable re-derivation block rather than a corrected number.

## Which frameworks actually applied, and which did not

**Bid/No-Bid: not applicable, and saying so beats a hollow pass.** This is not a
pursuit decision. Nothing is being bid on and no resources are being committed
to an opportunity. Scoring it out of ten would have produced a number that meant
nothing.

**Premortem: this is where the work was.** See above. Also re-run on the
verification method itself, per the standing rule that a clean result is only as
good as what the method could see: *"our own testing said 119 rules, 8,076
computations, zero hard errors — what did that method structurally miss?"* It
misses **whether the date is right**. Every one of those computations proves the
engine did not crash and produced *a* date; only the hand-worked examples in the
per-state tests prove any date is *correct*. Georgia's O.C.G.A. 9-11-36(a)(2)
row is the proof this matters: it passed every automated check and was still
fifteen days wrong, and it was caught by working the arithmetic by hand.

**NIST AI RMF: applies, and the answer is unusual enough to put in the claim.**
There is **no AI in this feature at all** — no model call, no prompt, no
inference, anywhere between the trigger date and the returned deadline. Verified
by reading the code path, not assumed. That matters externally for two reasons.
First, SAIRNlaw does have real AI features elsewhere, so a reader can reasonably
assume these dates come from a model unless told otherwise, and "an LLM produced
your filing deadline" is exactly the sentence that would lose a legal buyer.
Second, it means the Map/Measure/Manage functions have no surface here: there is
no hallucination rate to test and no drift to monitor, because the output is a
deterministic function of stored rule data. **Govern still applies** — someone
owns which rules go in and by what standard — and that is the primary-source
discipline described below, which is the real governance control on this feature.

## What the claim is measured against (live at time of approval)

| Jurisdiction | Rules | Civil | Appellate | Rule families | Notes |
|---|---:|---:|---:|---:|---|
| United States (Federal) | 21 | 18 | 3 | 11 | widest family range: answer, discovery, amendment, service, summary judgment, pretrial disclosures, expert disclosures, subpoena, appeal |
| Michigan | 18 | 14 | 4 | 8 | largest state set; **21-day appeal period** |
| Georgia | 12 | 9 | 3 | 5 | only computable **cross-appeal** in the engine |
| Pennsylvania | 11 | 6 | 5 | 6 | **10-day appeal period in three named subject matters** |
| California | 10 | 7 | 3 | 5 | 60/60/180 earliest-of appeal; per-method service extensions |
| New York | 10 | 8 | 2 | 7 | 20-day discovery periods; service extension **does** reach a notice of appeal |
| Texas | 10 | 6 | 4 | 6 | answer deadline is a **Monday at 10:00 a.m.**, not a day count |
| Florida | 7 | 6 | 1 | 5 | shifted-start counting |
| Indiana | 7 | 5 | 2 | 6 | discovery rules set no deadline |
| Ohio | 7 | 5 | 2 | 6 | discovery rules set no deadline |
| Illinois | 6 | 4 | 2 | 5 | thinnest set |

**119 rules across those eleven; federal 18%. THOSE ELEVEN each carry both
civil-litigation and appellate rules and holiday calendars for 2026–2031.**
Eight backward-counted. Seven designated-period. Two capped. Four multi-trigger.
One terminal-day rule. Periods are counted in calendar days or in months by
anniversary date — nothing in the engine approximates a month as thirty days.

> **THIS TABLE IS A DATED SNAPSHOT OF THE BATCH 2 ELEVEN, NOT CURRENT COVERAGE
> (scoped 2026-09-26).** It was accurate on 2026-08-24 and is kept because the
> per-jurisdiction shape of those eleven is what the demonstrations below are
> built on. The platform is now 39 jurisdictions and 437 rules, and **the
> "each carry both domains and 2026–2031 calendars" property is true of THESE
> ELEVEN and NOT of the 28 added since** — 12 of 39 carry both domains, and
> roughly half the calendars stop at 2026.
>
> The sentence above used to read "All eleven carry both …", and as jurisdictions
> were added a reader could not tell whether "all eleven" meant "all of them" or
> "these eleven". It was the second reading, and the approved claim at the top of
> this file had already generalised it to the first. That is how the
> overstatement got into a sales document: not by anybody writing something
> false, but by a scoped sentence outliving its scope.

## The three things most worth demonstrating

**1. The same words mean different things in different states, and the engine
reads each one.** Three of the four states added in Batch 2 add service-extension
days *"to the prescribed period"* (New York, Texas, Georgia); Florida and the
federal rules add them *"after the period would otherwise expire."* That is a
three-day difference on the same facts, always in the late direction if you
assume the federal order. It was found by a failing test, not by reading, and it
had already shipped wrong in Texas before New York exposed it.

**2. Ohio's and Indiana's discovery rules set no deadline.** All six of them,
across interrogatories, admissions and production, set a floor on a period the
requesting party designates. The engine asks for that period, computes from it,
and **refuses** a request designating less than the minimum rather than quietly
computing the minimum. Any tool returning a flat 28 days for an Ohio
interrogatory request is answering a question the rule does not ask.

**3. A holiday calendar is a statutory question, not an attendance record.**
Pennsylvania's courts commonly close on days no statute makes a holiday;
Georgia's statute freezes the federal list as it stood on 1 January 2022 and
separately tells the Governor to close state offices on thirteen days, which are
not the same set; Texas makes five days legal holidays on which courthouses are
routinely open. The engine encodes the statutory test **for every calendar it
carries** and discloses the divergence, because padding a calendar with observed
closures produces deadlines **later** than the law allows, which is the direction
that misses a filing.

> **"in every case" was the wording here until 2026-09-26, and it was the mode-7
> shape starting again.** It is true about METHOD — no calendar in this repo is
> built from an attendance record — and a reader of a sales document would take
> it as coverage, which is a different claim: roughly half the calendars stop at
> 2026. Narrowed to what is actually universal. The statutory-test method is; the
> calendars are not.

## Claims that are NOT approved

- ❌ *"litigation deadlines across 39 jurisdictions"* used **unqualified** —
  implies parity that does not exist, and the gap is far wider now than when this
  entry was written against eleven. Illinois has 6 rules, federal has 21, and
  **27 of the 39 have no appellate rules at all.** Federal is still the only
  jurisdiction with summary-judgment, expert-disclosure or pretrial-disclosure
  rules. Every count in this bullet needs re-deriving before it is quoted; see the
  block at the top of this file.
- ❌ **Any exclusivity framing** — "the only platform", "no other vendor",
  "unmatched". Added 2026-09-26. Nothing in either competitive audit supports one,
  and the external audit's single candidate differentiator is labelled a candidate
  pending a follow-up pass it has not had.
- ❌ **Jurisdiction count as the headline, or "we have a citator" as a
  differentiator.** Added 2026-09-26 — Clio ships a native rules capability and
  bought vLex. Lead with the US + England & Wales combination under licences that
  permit it, and with native integration. Reasoning in the positioning section
  above, including what that reasoning does and does not rest on.
- ❌ **"A fully integrated suite"** without qualification — SAIRNlaw carries no
  payments integration at all, and its trust reconciliation is table stakes in
  this category rather than an advantage.
- ❌ *"a thirty-day appeal deadline"* stated generally — **false in Michigan**
  (21), in three Pennsylvania subject matters (10), and for a Texas accelerated
  appeal (20). The single most dangerous generalisation in the product.
- ❌ *"computes Ohio's 28-day interrogatory deadline"* — **Ohio has no such
  deadline.** 28 is a floor on a party-designated period. This one sounds
  competent and is wrong.
- ❌ *"we don't cover deposition notice yet"* — implies a roadmap item. Every
  general deposition-notice rule requires only *"reasonable notice"*; there is no
  number and refusing is the final answer, not an interim one.
- ❌ **NEW — ❌ *"give it the date and it gives you the deadline."*** This is the
  Batch 2 failure mode in one sentence. It is true only if the date supplied is
  the event the rule actually names, and in five jurisdictions that event differs
  for the same-sounding act. Never demo the engine without saying which event the
  trigger is.
- ❌ **NEW — ❌ *"every date is verified against primary sources."*** The **rules**
  are, without exception. Three *interpretive* questions rest on secondary
  reading and are documented as such in the seed files: the Texas service-
  extension sequencing (no Texas appellate authority found), *Proctor v. Green*'s
  holding on the Texas Monday rule (full opinion not accessible), and Georgia's
  cascading-rollover reading. Say "every rule," not "every date."
- ❌ **NEW — ❌ *"the engine never returns a date later than the true deadline."***
  Tempting, because that is the design posture nearly everywhere. **Georgia is a
  deliberate exception:** where O.C.G.A. 1-3-1(d)(3) is silent on a Saturday
  whose following Monday is a holiday, the engine cascades to Tuesday, the later
  reading, because the earlier one would fix a deadline on a day the courthouse
  is shut. Documented in the standard's own comment. Do not make a directional
  guarantee.

## Known limits, and what kind of limit each one is

**Permanently uncomputable — refusing is the final answer:** general deposition
notice in every jurisdiction (*"reasonable notice"*); Ind. T.R. 45 motions to
quash (*"promptly"*); Mich. Ct. R. 2.506 objections (*"before the designated time
for appearance"*).

**Unknowable in advance — every jurisdiction has one:** executive-proclamation
and court-closure limbs. Illinois's Governor-proclamation days, Indiana's
office-closed limb, Florida's chief-justice hurricane extension, California's
CCP 12b, Texas's Tex. R. App. P. 4.1(b), New York's presidential and
gubernatorial proclamation days, and Georgia's 1-4-1(a)(2) — which is the
strongest of them, because the statute *requires* the Governor to designate at
least one such day every year.

**A buildable capability gap, currently forcing five refusals:** a "later of two
computed periods" shape. CPLR 5513(c), Tex. R. App. P. 26.1(d), Ohio App.R.
4(B)(1), FRCP 15(a)(3) and Georgia's O.C.G.A. 9-11-36(a)(2) all take the later or
earlier of two limbs that have **different day counts**, where the engine's
existing multi-trigger resolves between two supplied *dates* under one count.
Georgia's is decomposed into two honest rows as a stopgap; the other four refuse.
**This is scoped and buildable — do not describe it as permanent.** That is
precisely the Phase 8 failure mode running in reverse.

**A structural input limit, disclosed above and in the claim itself:** the engine
does not derive a trigger date the law defines or computes, and does not validate
the one it is given.

**A versioning limit:** rule versions are selected by the date the period runs
from. Where an amendment order keys applicability to the date the **case was
filed** — as the Texas Supreme Court's Misc. Docket No. 20-9153 does — the engine
cannot see that and will pick the wrong version for a case filed before the
cutoff whose events fall after it.

**Deliberately out of scope:** statutes of limitation anywhere. Claim-type
specific, often statutory rather than rules-based, and the highest-consequence
error class in the product.

## Why this lives in a document and not in the app

The sentence contains two kinds of fact, and only one is safe to write down.

The **invariant** half — every rule traces to primary-source text, there is a
full audit trail, no model is involved, the engine refuses rather than estimating
— is true independent of what is loaded. That half **is** in the app, in the
coverage card's standing notice.

The **specific** half — which jurisdiction covers what — has now gone stale at
**five consecutive gates**, most recently by four whole phases. That is the
argument for never hardcoding it. The app renders those specifics live from the
loaded rule set.

**So: this document is the point-in-time claim a human makes. The app is the live
one. When they disagree, the app is right and this file is stale.**

## Re-run the gate before changing this

Rewritten at five consecutive gates. The pattern is not going away: any material
coverage change makes the specific half stale, and the failure mode has been
different every single time. Re-run `sairn-decision-gate` and rewrite the sentence
before a new claim goes outside the team.
