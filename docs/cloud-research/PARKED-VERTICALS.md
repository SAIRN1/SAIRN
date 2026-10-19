# PARKED VERTICALS — audited, decided against, and not built

**What this file is.** The competitive-gap series audits verticals SAIRN has
**not** built for. An audit is not a decision and the decision is Michael's.
This is where a decided-against vertical goes so the next session does not
re-audit it, re-propose it, or quietly start building it.

**What this file is NOT.** It is not a backlog and it is not a maybe-later
list. A row here means **a decision was made to not build**, with the date and
the reason. Reopening one is a new decision, not a resumption.

**The rule that makes this worth keeping:** a row stays until somebody decides
otherwise, and **the conditions that would change the answer are written down**,
because "no, because X is unknown" becomes a different answer the day X is
known — and nobody will remember what X was.

---

## Outpatient behavioral health — PARKED 2026-10-19

**Audit:** `behavioral-health-worldwide-competitive-gap-audit-2026-10-17.md`
(fourth b29). **Decision: Michael, 2026-10-19 — no new vertical, log as a
parked idea only, nothing built.**

**Nothing was built and nothing is in flight.** No schema, no app file, no
API route, no panel. The audit document is the whole artefact.

**Why it was a candidate at all**, kept because it is the part that would be
expensive to re-derive: outpatient mental health bills on a code set
republished annually (CPT) against a **date of service**, under rules that vary
**by state and by payer** with an effective window — structurally the same
problem `sairndental` already solves for CDT editions. The gap found was not
the EHR but **the supervision layer**: whether a pre-licensed associate
clinician's session is billable at all. Supervision-hour tracking is not a
standard EHR feature, incident-to is narrow and being withdrawn by some
commercial payers, and Headway does not support it at all.

**Why the answer was no.** The audit's own §7 said it was not a
recommendation, and none of its preconditions were met:

* no driven trial account on SimplePractice or TherapyNotes, so the central
  claim rests on secondary, partly vendor-authored sources;
* no clinician, supervisor or practice owner interviewed;
* **no owner for a 50-state supervision and compact rule matrix** — and
  childcare's audit named the same missing role a day earlier. **Two audits,
  one missing role. That is the finding about SAIRN rather than about either
  market.**

**What would change the answer** — write the date next to any that becomes
true rather than re-arguing from scratch:

1. Somebody owns a 50-state rule matrix as a standing job, not a one-off.
2. A real group-practice owner employing associates has been interviewed and
   confirms the supervision/billing-basis pain first-hand.
3. A driven trial on both incumbents shows the supervision gap is real in the
   product rather than in the buyer guides.
4. The DEA special-registration final rule publishes (it was still at OIRA on
   2026-09-21, and the fourth extension lapses **2026-12-31**), so a
   prescribing-authority model could be built against a rule that exists.

**Perishable facts in that audit, stated so a stale read is obvious:** the
42 CFR Part 2 compliance date (2026-02-16) has passed; the DEA extension
expires 2026-12-31; the Counseling Compact state count was already
unreconciled at 7 vs 9 when it was written. **Re-derive all three before
quoting them**, via the Federal Register API through `tools/sairn_http.py` —
`WebFetch` is blocked by a redirect and that is a standing fact, not a one-day
outage.

---

## Childcare — AUDITED, NOT DECIDED (2026-10-16)

**Audit:** `childcare-worldwide-competitive-gap-audit-2026-10-16.md` (fourth
b28). **No decision has been recorded.** It is listed here only so the pair is
visible in one place; it is **not** parked and must not be read as decided.
Its §5 carries the same three unmet preconditions, including the same missing
50-state-matrix owner.
