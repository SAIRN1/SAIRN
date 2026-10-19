# SAIRN handoff — cc, batch b21, 2026-10-19

**Subject:** wire the measured context figure into the digest-writing step as a
push gate; independently drive the WCAG contrast gate; scope a coordination-health
monitor. Written before the report, per instruction. Nothing half-finished.

---

## 1. Committed / pushed state

| | |
|---|---|
| Branch | `main` |
| Start of batch | `8aa71479` → pulled to `56d2031a`, clean 0/0, zero stashes |
| Claim commit | `f2b17f74` — `chore(claims): cc claims cc` |
| Work commit | **`c2436a95`** — `feat(context): the digest CONTEXT line stops being typed`. Rebased twice while the remote moved, so the sha ran `60e6a3a5` → `162681f9` → `c2436a95`; only the last one exists on origin. |
| Gate bookkeeping | `7766774b` — the row `docs/scrutiny-flags.json` gained, written by the gate itself, not by hand |
| Handoff / report / digest commit | appended after this file (see §6) |
| Push | **LANDED.** `HEAD == origin/main`, 0 ahead / 0 behind, clean, zero stashes. Verified by reading the files back OUT OF ORIGIN: `origin/main:tools/context_verify.py` is 49,592 bytes at `CRITERIA_VERSION 2026-10-19.2` and its lock classifies 56/56 when driven from that extracted copy; `origin/main:tools/sairn_push_gate_hook.py` carries CHECK 5c. A second push carries this handoff, the report and the digest. |
| Overrides used | **none.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`. `docs/BYPASS-LOG.jsonl` gains no row from this batch. |

Files changed by `c2436a95`:

```
tools/context_verify.py          +686 / -13   --digest-line, --check-digest,
                                              --provision-window, session-keyed
                                              declared window, 56/56 fixtures
tools/sairn_push_gate_hook.py    +125         CHECK 5c, gate id context-digest
tools/gate_skip.py                 +2         context-digest registered
docs/TOOLING-INVENTORY.md         +9 / -10    regenerated (BLOCKING 21 -> 22)
docs/2026-10-19-cc-b21-context-in-digest.md        new  items 2 and 3 in full
docs/2026-10-19-coordination-health-monitor-scope.md new  item 4, SCOPE ONLY
```

**`tools/wcag_contrast_check.py`, `docs/wcag-contrast-baseline.json`,
`api/sd-data.js` and every `.html` file were NOT touched.** Item 3 was
verification only.

## 2. What is CLOSED

**Item 1 — orientation.** Pulled, clean 0/0 before anything was touched.
Registry read, all four build agents plus both hover instances present. Claim
checked then taken; the one lexical match (fourth b32) is disjoint by declared
file set and was read before proceeding.

**Item 2 — the measured figure wired at the source. CLOSED.**
`context_verify.py --digest-line` emits the line; CHECK 5c in the push gate
re-derives it and denies when it is not a measurement. Driven in five
directions (fabricated count → `NOT_MEASURED`; no line → `MISSING`; real count
with edited percentage → `INCONSISTENT`; the tool's own output → `OK`; a hover
digest → `COULD_NOT_TELL` by the separation boundary), and the whole pre-push
hook was driven on the fabricated one and refused. Criteria lock 56/56, hook
selftest 56/56.

**Item 3 — is the contrast gate really wired. VERIFIED, with one gap found.**
Driven, not read: a planted below-AA rule in `stonedesk-catalog.html` is
refused naming the finding at 2.54:1; the same rule at an AA-passing colour
passes the whole gate. **The gap:** `--static --all` derives its product list
by excluding any root HTML stem containing a hyphen, so the five sub-apps are
outside `docs/wcag-contrast-baseline.json` while being inside the gate — and
two of them carry debt. See §4.

**Item 4 — coordination-health monitor. SCOPE ONLY, as asked.**
`docs/2026-10-19-coordination-health-monitor-scope.md`. Nothing in `tools/`
was added for it.

**Item 5 — methodology.** Each of items 2, 3 and 4 states its one-line concept
before its implementation, in the doc and in §3 of the report.

## 3. What is OPEN, and why

**(a) `tests/run_push_gate_preflight_probe.py` is RED, 3 of 13 arms, and it is
NOT mine.** Diagnosed, not fixed, deliberately — fixing somebody's suite to
make it pass is the shape this platform warns about, and it is an orthogonal
change to this batch.

*Pre-existing:* driven on an isolated worktree at `HEAD` **before** any b21
change — identical 3 failures (E1, E2, E3), all `RAISED SyntaxError`.

*Root cause, confirmed:* the probe does
`source.replace("if __name__ == '__main__':", inject, 1)`. That anchor now
occurs **twice** in `tools/sairn_push_gate_hook.py` and the **first** is inside
a double-quoted string on a real code line — `_src.rindex("if __name__ ==
'__main__':")`, at char 278145, part of the hook's own WIRING selftest arm. The
multi-line injection lands inside that string literal, leaves it unterminated,
and `compile()` raises. The hook's own selftest already uses `rindex` for
exactly this reason.

*The fix is one line:* anchor on the LAST occurrence
(`source.rindex(anchor)` + slice, or `replace` after splitting at `rindex`),
not the first. **Nobody has a row for this suite in
`docs/known-red-suites.json` either — that file is cody's and was not touched.**

**(b) The contrast baseline's universe is narrower than the gate's universe.**
Routed to fourth — both `tools/wcag_contrast_check.py` and
`docs/wcag-contrast-baseline.json` are in fourth's b32 declared file set. §4
has the measurement.

**(c) hank's two routed items to cc are NOT started and are not in this
batch's claim.** From the registry, hank's append of 2026-10-19T14:14:24:
*"no gate driver references either new b18 suite (`grep -rlE
'b18-(countersign|passkey)' tools/` returns nothing), and FMEA drafts are owed
for eight new/changed files."* Neither was claimed and neither was touched.

**(d) NOT MINE, left flagged on instruction:** cody's SAIRNscape `customers`
PII fix needs `api/sd-data.js`, which is hank's boundary. Not touched, not
fixed, still flagged. *(Note for the next reader: cody's own b25 commit
`899597b5` already appears to have landed a SAIRNscape retier and a write
400→403 — re-read it before repeating the work.)*

## 4. The contrast gap, measured

`product_files()` in `tools/wcag_contrast_check.py` keeps a root `*.html` only
when its stem is `stonedesk` or starts with `sairn` **and contains no hyphen**.
The gate runs on every changed `.html`. Measured with
`--gate <file> --baseline`, exit codes read directly rather than through a
pipe:

| file | new findings vs baseline | today's gate verdict |
|---|---:|---|
| `sairndental-book.html` | 6 | **deny** |
| `sairndental-complaint.html` | 2 | **deny** |
| `stonedesk-catalog.html` | 0 | pass |
| `stonedesk-hr.html` | 0 | pass |
| `stonedesk-intake.html` | 0 | pass |

The baseline holds **3** findings today, all `sairnroofing.html`. So any push
touching either dental sub-app is denied on **8 findings of pre-existing debt**
with no route but a skip. b29–b31 took the platform from 153 to 3 across the 17
root products and never saw these files, because `--all` could not.

Two defensible fixes and the choice is not mine: widen `product_files()` and
re-record the baseline, or fix the 8 findings.

## 5. Exact next step, per item

| item | next step |
|---|---|
| 2 | **Each of hank, cody and fourth runs `python tools/context_verify.py --provision-window <tokens>` once per session, then `--digest-line`, and pastes the output.** Until a session declares, the row is AMBIGUOUS and `--digest-line` refuses — by design. cc's own session is declared (1,000,000). Nothing else is owed on this item. |
| 3 | fourth: pick one of the two fixes in §4. The measurement is done; no re-derivation needed beyond re-running the five `--gate` commands. |
| 4 | Before ANY code: collect **one week** of per-agent registry write intervals. §3 of the scope doc says why a threshold from today's single snapshot would fire on hank. C1+C2 are the cheap third and land first; C3 stays report-only until a real lost batch gives it a threshold. |
| (a) | whoever owns `tests/`: the one-line `rindex` fix above, then re-drive — expect 13/13. Separately, cody: a row in `docs/known-red-suites.json`. |
| (c) | hank's two routed items need a claim first; they are unclaimed as of this writing. |

## 6. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\c44c9acc-c450-453e-8559-c42a7fd16504.jsonl
```

Evidence captured out of band, in this session's scratch:

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\c44c9acc-c450-453e-8559-c42a7fd16504\scratchpad\
  hook_plant.txt   the pre-push hook refusing the planted contrast finding
  hook_abl.txt     the same push passing with the AA-fixed colour
  ctx_fab.txt      the pre-push hook refusing a fabricated CONTEXT line
  ctx_ok.txt       the tool's own line verifying OK
  a.txt b.txt c.txt   MISSING / INCONSISTENT / hover-boundary arms
  g_sairndental-book.html.txt, g_sairndental-complaint.html.txt
```

**A scratch directory is session-local and is not a durable record.** Every
figure quoted in the report and the digest is re-derivable by the commands
named beside it, which is the record that survives.

## 7. Context at the time of writing

Measured, not estimated — `python tools/context_verify.py --digest-line`. The
figure is in the digest's CONTEXT line and in the report. The window is
**declared** for this session, not inferred, which is the b21 change; before
that change this tool would have reported this session at roughly five times
its real percentage.
