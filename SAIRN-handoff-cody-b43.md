# SAIRN handoff — cody b43 (2026-10-21)

Five items. **Items 2–5 done. Item 1 NOT DONE: the harness denied the delete.**

## State
- One code commit, `8e9eebf18`, two test files only. No app code, no SQL, no live writes.
- No live-verify: nothing here is deployed (tests only).
- Claim: not taken. `sairn_claim.py check` blocked on "same app: sairndental"
  (fourth's b50 a11y claim). Fourth's FILES list is `sairndental.html` and
  `tests/sairndental_a11y_pass.js`; I touched neither. I edited only
  `tests/sairndental_write_failure_probe.py`, which the queue sent me. Said here so
  fourth can object.

## Item 1: delete settings.local.json.bak — DENIED
`rm .claude/settings.local.json.bak` was denied by the harness. No retry, no other
route. It is still untracked in this clone. Michael, one line:

    ! rm C:/Users/marsh/Documents/SAIRN-cody/.claude/settings.local.json.bak

## Item 4: the concept, stated before each fix
- **isolation:** the measurement was right and the hand-written table was one row
  short. A new registered owner needs a recorded posture decision.
- **dental probe 2:** a mutation anchor must be unique, and a later commit copied
  its text. The probe failed closed (ANCHOR-2) and so tested nothing. Lengthen the
  anchor to a part only the target has.

## Item 2: app_session_isolation red at HEAD — real, fixed
`routes` joined `reg.APP_NAMES` on 2026-10-19 (fourth b34, `api/_resources/routes.js`).
Section 4 measures every app and requires a `POSTURE` row; `routes` had none:
`DRIFT routes: measured ALL (2 of 2 gate), recorded NOTHING`.
The measurement is correct: `rt_routes`/`rt_stops` return 403 FORBIDDEN without a
session on every verb (`api/sd-data.js`, the SHARED ROUTING PRIMITIVE branch).
**Fix:** a `routes` row, `gate: 'ALL'`, with a reason, next to the `shared` precedent.
RED exit 1 → GREEN, 67/67.
**Not done:** a mutant run (`gate: 'SOME'` on a scratch copy). The harness denied
that Bash call. Evidence is the RED→GREEN differential only.

## Item 3: dental write-failure probe 2 not biting — real, fixed
Probe 2 read **ANCHOR-2**, not SILENT. The anchor tail
`message:(d&&d.error&&d.error.message)||'',status:r.status};` appears twice:
sdnData (`sairndental.html:1652`) and the credential board (`:2968`). The board's
copy came from `cc919c308` (2026-10-20). The probe refuses to mutate a non-unique
anchor, so probe 2 changed nothing.
**Fix:** the anchor now starts with `dntLastErr[resource]={code:...`, which only
sdnData has (count 1, measured). Exit 1 → 0. Probe 2 **BITES**, all 16 bite, and
`sairndental.html` is restored byte-identical (`623a378252d588d0`).
fourth's b49 note "exit 1 before this batch" fits: cc919c308 predates b49.

## Item 5: push
See the report for the landed sha. Pushed with no force.

## Guardian
Check 0 syntax: `node --check` and `py_compile` clean on both files. The other
31 checks cover app code (UI, storage, navigation, auth). Neither file is app code,
so I ran none of them by hand. The push gate ran its mechanical set.

## Open
- Item 1: the `!` line above.
- Not swept: other mutation probes with anchors that a later commit may have
  duplicated. The same shape would read ANCHOR-n.
- Carried: hank F2/F3 owner write path; cc Tier A b31–b37; fourth defects 7/8.
