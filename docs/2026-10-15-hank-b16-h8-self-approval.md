# H8 — RESOLVED 2026-10-15 (b17). The owner may approve their own.

> **MICHAEL'S RESOLUTION, and it is NOT the exception this document was written
> to hold open:** *"A one-person agency is just the owner with full access; the
> owner may approve their own visit."*
>
> **So there is no one-person-agency exception at all, and that is the point.**
> This document spent b16 describing a dead end that needed a special case.
> The answer was that it needed a **role**, not a special case: an owner is an
> owner at any headcount, the owner's authority includes approving a
> correction, and nothing anywhere has to know the agency is one person.
>
> **BUILT IN b17**, in `api/_lib/sen-evv-clock.js`'s `approveCorrection()`
> which now takes `approverRole`. §3 below listed the two constraints any
> design would have to satisfy; **both are met** — see §5, added b17.
> Driven by `api/b17-one-person-agency.test.js`, 11 arms, including the
> end-to-end arm O5 that takes the stranded visit from §2 all the way to
> **240 minutes / 8000 cents paid and no EVV time-span gap**.

**THE HISTORY BELOW IS LEFT AS IT WAS WRITTEN, deliberately.** §1–§4 describe
the state at b16 and the reasoning that led to the question being asked — which
is the part worth keeping. The headline and this box are the correction.
**Reading §1–§4 as current state would be wrong**; every one of them is marked.

---

**Written 2026-10-15 by hank, batch b16.** ~~This is a **record for the
home-care practitioner question H8**, per Michael's standing instruction that
the one-person-agency self-approval exception **stays unbuilt**.~~ **SUPERSEDED
b17 — the question was answered.** It was written down because the consequence
is a real workflow dead end and it would otherwise be re-found as a defect by
whoever reads `approveCorrection` next; that reasoning held, and the answer
arrived one batch later.

---

## 1. The rule, where it lives, and what it refuses  — **AS AT b16; §5 is current**

`api/_lib/sen-evv-clock.js:333` — `approveCorrection()`:

```
if (String(entry.proposed_by) === String(approver)) {
  return refuse('SELF_APPROVAL_REFUSED', ...);
}
```

Decided by Michael on 2026-10-15. b13 had **marked** the case
(`self_approved: true`) and allowed it, on the argument that a one-person agency
has nobody else and refusing would strand them. Michael decided the other way:
**an approval by the submitter is not an approval**, so it is refused rather
than flagged. The module's own note states the trade in its own words and does
not hide it.

**It is in the module and not only in the handler**, deliberately — a rule
enforced in one branch of one endpoint is a rule the next caller does not get.
The handler maps the refusal to 403.

## 2. The dead end, stated exactly  — **CLOSED IN b17; kept because O5 drives this exact scenario**

In a one-person agency the owner **is** the assigned caregiver. So:

1. The caregiver forgets to clock out. The visit has no end time.
2. They file a correction. `proposeCorrection` writes it `status: 'pending'`,
   `approved_by: null`.
3. They are the only employee, so they are the only possible approver.
4. `approveCorrection` refuses: `SELF_APPROVAL_REFUSED`.
5. **The correction can never become effective.** As of b15 and b16 that means:
   * `api/_lib/sen-payroll.js` pays the visit **nothing** (no clock-out → the
     `no_clock_out` exclusion), and
   * `api/_lib/sen-evv-readiness.js` reports the visit as **not EVV-ready**
     ("No clock-out time recorded"), so it cannot be submitted either.

**Both halves of b16 make this sharper rather than softer.** Before b16 the EVV
side read the raw clock and would have reported the gap anyway; now the two
sides agree, which means they agree on *stranded*. The visit is unpayable and
unsubmittable and the only person who can fix it is forbidden from doing so.

## 3. Why it is NOT built, and what building it would have to look like  — **SUPERSEDED b17; the two constraints it names were MET, see §5**

**It is not built because Michael decided it stays unbuilt.** This section
exists so the shape of the answer is on record and nobody improvises one in a
handler.

If it is ever granted, the b15 handoff's condition stands and b16 adds a second:

* **It must be a licence-level setting with an audit trail, not a fallback in
  the handler.** A code path that silently permits self-approval "when there is
  only one employee" would be the rule deleting itself based on a row count
  that changes the moment somebody is hired.
* **AND it must carry an `approved_at_server`.** b16's freeze compares that
  instant to a period's `paid_at` to decide whether a correction was in the
  as-paid basis. A self-approval route that minted an entry without one would
  land in the **undatable** bucket — applied on the as-paid basis and counted as
  unverifiable — which for a one-person agency would be *every* correction it
  ever makes. The freeze would then be unverifiable for exactly the agencies
  using the exception.

## 4. What this document does not claim  — **AS AT b16**

* **Not** that the refusal is wrong. It is a decided trade and the argument for
  it — an edited EVV time with no second party cannot be told from a fabricated
  one — is the stronger one on a federally audited record.
* **Not** that any real agency has hit this. No live data was examined; the
  dead end is derived from the code paths, not from a report.
* **Not** a design. §3 lists two constraints any design would have to satisfy,
  not a design.

---

## 5. HOW IT WAS BUILT (b17, 2026-10-15) — this section is the current state

**`api/_lib/sen-evv-clock.js`'s `approveCorrection(entry, approver, atISO,
approverRole)`.** Self-approval is permitted when, and only when,
`approverRole === 'owner'`.

**A ROLE AND NOT A HEADCOUNT.** The design NOT taken was "permit self-approval
when the agency has one employee", and it is worse in three measurable ways: it
is a rule that deletes itself the moment somebody is hired; it needs a roster
COUNT at approval time, on a path that currently needs no extra query; and a
miscounted roster would silently re-open self-approval for a ten-person agency.

**§3's TWO CONSTRAINTS, BOTH MET:**

| §3 said | b17 |
|---|---|
| "a licence-level setting with an audit trail, not a fallback in the handler" | **Better than asked: no setting at all.** There is nothing to configure, so there is nothing to misconfigure and no per-licence state to drift. The rule is in the MODULE every caller goes through, not in the handler — `api/sd-data.js` passes `session.role` from the VERIFIED session, never the payload. The trail is on the entry: `self_approved: true`, `self_approval_basis: 'owner'`. |
| "must carry an `approved_at_server`, or the freeze is unverifiable for exactly the agencies using the exception" | **Met.** `approved_at_server` is set on BOTH paths. Arm O1 asserts it. Without it every correction a one-person agency ever made would land in b16's `undatable_corrections` bucket. |

**THE MARK IDENTIFIES ENTRIES WITH NO SECOND PARTY, NOT ENTRIES AN OWNER
HANDLED.** Arm O3 drives an owner approving somebody *else's* correction and
requires `self_approved` to be **absent**. b13 marked self-approval and allowed
it for everyone, which was the right half of the wrong answer; allowing the
owner without the mark would lose the one fact an auditor needs.

**BACKWARD COMPATIBLE.** `approverRole` undefined behaves exactly as b16 did —
refused. `api/b14-clock-approval-two-person.test.js` arm S11 uses the
three-argument form and still passes unchanged; arm O4 drives the same call.

**WHAT §5 DOES NOT CLAIM:** no live verification. The approve action answers
401 before the dispatcher without a licence key, so O5 drives the real handler
with a stubbed upstream, not the deployed endpoint.
