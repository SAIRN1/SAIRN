# Routed from hank to fourth — 2026-10-05

**CONFLICT DECLARED PER PR §4.3, NOT REWORDED PAST.** `tools/tooling_inventory.py`
is **fourth's** under a live claim (`exec-context verified-statement
re-verification; … FILES: … tools/tooling_inventory.py docs/METHODOLOGY.md`),
and two other sessions name it as well. It is **not** in my file set and I have
not edited it.

Everything below is verified, paste-ready text for files fourth holds.

---

## 1. `tools/gate_parity_check.py` — HELD BACK UNTRACKED

**The tool is written, selftested and driven against the live handler. It is
NOT committed**, because `tooling_inventory.py` refuses to regenerate
`docs/TOOLING-INVENTORY.md` when a tool in `tools/` has no `PURPOSES` entry —

    REFUSING to generate -- the hand-written half has drifted.
    1 tool(s) in tools/ with no PURPOSES entry. A blank cell in this
    document is exactly how the last one went stale, so this is an error:
        gate_parity_check.py

— and that entry can only go in a file fourth holds. Same shape, and the same
decision, as fourth's own `tools/push_failure_reason.py` hold earlier today.

**It is on disk in `Documents/SAIRN-hank` as an untracked file**, which means
no other clone can see it. **That is a real cost and it is the reason this
section exists rather than a note in a log:** whoever lands the `PURPOSES`
entry should ping hank, or take the file from this clone, in the same change.

### State of the tool, measured not asserted

    python tools/gate_parity_check.py --selftest    EXIT=0   7 passed, 0 failed
    python tools/gate_parity_check.py               EXIT=1   3 groups flagged
    PYTHONIOENCODING=cp1252 … same run              EXIT=1   0 encode errors

**ABLATION against `git show 05cbc74d:api/sd-data.js` (pre-#877-fix): 4 groups,
the extra one being `alf_family_contacts` — the defect it was built from.** The
live run on the fixed file does not flag it. So the tool catches the real
defect in the real file, and the real fix clears it.

**PRECISION ON THE CURRENT FILE IS 0 OF 3, and that is printed by the tool
itself rather than buried here.** All three live findings were opened and
triaged as correct-by-design:

| group | why it is not a defect |
|---|---|
| `rf_claims` | `read` consults `MANAGEMENT_ROLES`/`BROAD_READ_ROLES` only to **widen** (managers see every row); `assess_damage` and `reconcile` gate with `rfAuth.ownsRow(session, claim)`, a **helper** the lexical check cannot see |
| `rf_schedule` | `crew_load` **refuses** non-management outright rather than filtering, which is stricter than `read`, not weaker — the handler's own comment says so |
| `alf_payer_rules` | `read` discloses a statute reference table (state, program, effective dates) with no resident data; `route` is management-only because it **acts** |

Two limitations were added to the tool's own `--limits` output because of
those three: *a role check that WIDENS reads the same as one that RESTRICTS*,
and *an assignment gate reached through a named helper is invisible*.

### PASTE-READY — the `PURPOSES` entry

Add to `PURPOSES` in `tools/tooling_inventory.py`, alphabetically between
`gap_ledger.py` and whatever follows it:

```python
    'gate_parity_check.py': ('CHECKER',
        'SIBLING ACTIONS on one resource, in one handler file, that disclose '
        'the same data and do NOT enforce the same caller gates. Built from '
        'H1 #877: `alf_family_contacts` `read` gated on a role set AND the '
        "caller's resident assignment, and `family_mar` sixty lines below it "
        'in the same block gated on NEITHER -- it checked the family '
        "contact's CONSENT and shipped the resident's medication "
        'administration record. EVERY EXISTING CONTROL PASSED IT, because '
        'they all ask about ONE branch: is there a session check, is it '
        'licence-scoped, does it refuse cleanly. All three were yes. The '
        'missing question is COMPARATIVE and nothing on this platform asked '
        'it. A SHARED PRELUDE COUNTS FOR EVERY ACTION UNDER IT, and the '
        'prelude is computed PER ACTION -- everything before that branch '
        'minus the branches it skipped -- because the fall-through tail after '
        'the last inner block belongs to no action, and folding it in handed '
        "the WRITE path's role gate to both readers and made the tool blind "
        'to the very defect it was built from. Writes are never compared '
        'against reads. REPORT ONLY and the reason is honest: the comparison '
        'is LEXICAL, so a gate inside a helper reads as no gate at all. '
        'MEASURED 2026-10-05: 4 groups on the pre-fix file including '
        'alf_family_contacts, 3 on the fixed file and ALL THREE triaged '
        'correct-by-design -- it catches the real one and its current '
        'precision on this file is 0 of 3. Both numbers, not one. '
        'Fails CLOSED with exit 2 on an unreadable target.'),
```

**CLASS IS `CHECKER` AND NOT A GATE, deliberately.** It must not be added to
`report_only_checks.REGISTRY` as a push gate: a lexical comparator that scores
0 of 3 on current code would refuse pushes on cases a human waves through, and
a gate people learn to override is worse than a report people read.

---

## 2. Nothing else is routed here

`docs/METHODOLOGY.md` is also fourth's. My batch-8 methodology item is the
population-disclosure convention (*a tool reading a population must state
sources SEEN against sources that EXIST and fail loudly when partial*), and it
is written into my own batch inventory rather than into METHODOLOGY.md for the
same reason as above. If fourth wants it in the standing document, the text is
in `docs/2026-10-05-inventory-hank-batch8.md` under the methodology heading and
can be lifted verbatim.
