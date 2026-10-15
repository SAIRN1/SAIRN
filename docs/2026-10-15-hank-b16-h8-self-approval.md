# H8 — the one-person agency has no route to make a clock correction effective. RECORDED, NOT BUILT.

**Written 2026-10-15 by hank, batch b16.** This is a **record for the home-care
practitioner question H8**, per Michael's standing instruction that the
one-person-agency self-approval exception **stays unbuilt**. Nothing in b16
built it and nothing here asks for it to be built. It is written down because
the consequence is a real workflow dead end and it would otherwise be re-found
as a defect by whoever reads `approveCorrection` next.

---

## 1. The rule, where it lives, and what it refuses

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

## 2. The dead end, stated exactly

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

## 3. Why it is NOT built, and what building it would have to look like

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

## 4. What this document does not claim

* **Not** that the refusal is wrong. It is a decided trade and the argument for
  it — an edited EVV time with no second party cannot be told from a fabricated
  one — is the stronger one on a federally audited record.
* **Not** that any real agency has hit this. No live data was examined; the
  dead end is derived from the code paths, not from a report.
* **Not** a design. §3 lists two constraints any design would have to satisfy,
  not a design.
