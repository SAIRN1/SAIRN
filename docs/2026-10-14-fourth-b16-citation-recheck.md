# METHODOLOGY — every `file:line` in my b15 documents, re-derived at this HEAD — 2026-10-14, fourth b16

**THE RULE THIS ADDS:** a `file:line` citation is **re-derived against HEAD
before the batch that contains it closes, and again by the next batch that
touches the document.** A citation is not checked by confirming the line
exists; **it is checked by reading the text now at that line.**

```
CMD git -C <repo> pull --rebase origin main        (platform repo pulled first)
CMD python scratchpad/cite_recheck_b16.py          ->  exit 0
    45 citation(s) across 9 document(s); 0 unresolvable
```

**45 citations, 44 correct, ONE WRONG — and the wrong one proves the method,
because nothing else would have caught it.**

---

## 1. THE ONE THAT MOVED

**`docs/2026-10-14-fourth-b15-sairnvet-role-matrix.md` cited
`api/_lib/auth.js:277` twice for the claim that a practice manager is
"explicitly NOT a clinician".**

```
CMD awk 'NR>=274 && NR<=278 {printf "%d: %s\n", NR, $0}' api/_lib/auth.js
    274:   //   tech       -- Veterinary Technician (CVT/RVT/LVT depending on state).
    275:   //   assistant  -- Veterinary Assistant.
    276:   //   manager    -- Practice Manager. Runs the office; NOT a clinician.
    277:   //   frontdesk  -- Front Desk / reception.
```

**The claim is at `:276`. `:277` is the `frontdesk` line.** Off by one, in a
document whose entire subject is who may read a clinical record, on the one
line a reviewer would check first.

**FIXED IN PLACE, with the correction visible rather than silent:** the
document now reads `api/_lib/auth.js:276` and says in the same breath that it
was cited as `:277` when written and corrected the same day by re-deriving it.
**A corrected citation that hides having been wrong teaches nobody anything.**

**It did NOT move. It was never right** — and that distinction matters for the
tool request in §3: a drift checker that only compares against a stored
baseline would have called this clean, because the line number was wrong from
the first commit. **What catches it is reading the line, not diffing it.**

---

## 2. THE 44 THAT ARE CORRECT, and what "correct" was taken to mean

Each was checked by reading the text now at the cited line and comparing it to
what the citing sentence claims. Spot examples:

| citation | text now at that line | claim it supports |
|---|---|---|
| `api/sv-auth.js:118` | `const PRESCRIBER_ROLES = roleSet({ owner: true, dvm: true });` | the one role gate SAIRNvet has |
| `api/sd-data.js:16882` | `const LAW_RECONCILE_ROLES = roleSet({ owner: true });` | the one role gate SAIRNlaw has |
| `api/_lib/auth.js:177` | `sairnlegacy: ['owner', 'director', 'staff'],` | three roles, which is the SAIRNlegacy finding |
| `api/_lib/auth.js:138` | `sairnlaw: ['owner', 'attorney', 'paralegal'],` | three roles, two jobs missing |
| `api/_lib/auth.js:238` | `sairncare: ['owner','nursing','med_aide','caregiver','billing','activities'],` | the precedent |
| `sql/sairnfreedom_employee_auth_schema.sql:73-85` | `role text not null check (role in (` … `)),` | the second precedent |
| `tools/batch_manifest.py:386` | `print('  | %s' % line)` | the `--close` crash |
| `tools/text_gate_literal_sweep.py:80` | `MASKS = re.compile(` | why prose about masking can credit a tool that does none |
| `tools/text_gate_literal_sweep.py:115` | `def classify():` | the function the fixture must lock |
| `api/sd-data.js:14007` / `:14706` | `const SV_RESOURCES = {` / `const LAW_RESOURCES = {` | where each gate goes |

**TWO SEALED ARTEFACTS WERE CHECKED AND NOT EDITED.**
`SAIRN-handoff-fourth-b15.md` and `SAIRN-report-fourth-b15.txt` carry 12 of the
45 citations between them; **all 12 are correct**, and the wrong one does not
appear in either. **Had it appeared, the correction would go in a new dated
document and not into a sealed report** — a report carries a SHA256 over its
own body and is a record of what was said at the time, not a living page.

---

## 3. THE TOOL REQUEST — routed to cc

**`tools/citation_line_drift_check.py` already exists** and is the right place;
this asks for one mode rather than a new tool.

```
python tools/citation_line_drift_check.py --read-the-line <doc>...
```

| requirement | why |
|---|---|
| extract `path:line` and `path:line-line` from a document, where `path` is a real repo path with a code/data extension | the b16 prototype's pattern is in `scratchpad/cite_recheck_b16.py`; it found 45 in 9 documents |
| for each, print **the text now at that line**, truncated | **this is the whole feature.** A verdict of "the line exists" is what let `:277` stand |
| exit **1** if a cited file is absent or a cited line is out of range | the cheap half, and the only half that can be fully automatic |
| exit **2** if no citation parses at all | a document whose citations stopped matching the pattern reports zero drift and zero coverage, and those must not look alike |
| **report, never rewrite** | a tool that silently renumbers a citation is a tool that can move a claim onto a different line. **The b16 fix was made by hand, visibly, and that is the right shape** |
| `--fixtures` with a BAD INPUT arm | a document citing `:9999` of a 10-line file must exit 1; **and the control: a document whose citations are all correct must exit 0** |
| an arm for the off-by-one case | a citation one line away from its claim **cannot be caught mechanically** — the tool prints the line and a human reads it. **Say that in the banner** rather than implying the check is complete |

**WHAT THE TOOL CANNOT DO, and must say so:** decide whether the line supports
the sentence. That is the judgement `:277` needed. **The tool's job is to put
the current text in front of a reader cheaply enough that they do it every
time.**

---

## 4. WHAT THIS RE-DERIVATION DOES NOT CLAIM

* **It does not cover documents older than b15.** b12, b13 and b14 carry their
  own citations and were not re-derived here. **Unmeasured, not clean.**
* **It does not check prose claims without a line number** — "the push gate
  refuses on drift" has nothing to re-derive against.
* **It does not check the two sealed artefacts' figures**, only their
  citations. A SHA256 over a body proves the body is unchanged, not that it was
  right.
* **One in forty-five is a rate from one sample.** It is not a measured error
  rate for my citations generally, and quoting it as one would be the
  fabricated-figure defect this platform keeps a register for.
