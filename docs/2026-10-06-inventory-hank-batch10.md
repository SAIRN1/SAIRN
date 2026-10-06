# Hank inventory — batch 10, 2026-10-06

Written as each item landed. Twelve dispatched items; the mapping is stated
rather than left to be inferred. **This batch resumed after a context
compaction, so every premise below was re-derived from HEAD rather than carried
forward — which changed the answer on three of the twelve.**

| dispatch | here | verdict |
|---|---|---|
| 1 establish state | §1 | three items were ALREADY LANDED before this session resumed |
| 2 #894 single-response + test | §2 | landed `16b2cc70`, verified, mutation-checked |
| 3 `gate_parity_check.py` | §3 | landed `e7adad94`, verified, 24 of 125 tables compared |
| 4 `tooling_inventory.py` duplicate key | §4 | **FIXED AND PUSHED** `19c872e0` |
| 5 `sc_anesthesia_base_units` citations | §5 | **already correct at HEAD** — 12 of 12 re-derived |
| 6 three probes, clone identity | §6 | **the conversion was done and the FALLBACK was still wrong** `6a4ee580` |
| 7 panel-auditor + agents README | §7 | landed `104ab3ff` |
| 8 the six platform-work items | §8 | file+line for each |
| 9 two methodology rules | §9 | routed, not promoted |
| 10 review obligations | §10 | listed; one discharged, the rest BLOCKED and flagged back |
| 11 pull / status discipline | §11 | — |
| 12 handoff | `docs/handoff-hank-2026-10-06b.md` | — |

---

## 1. State, established before anything was touched

At resume, `git log origin/main..HEAD` showed **one** unpushed commit (item 7's)
and **one** commit behind. The screen's recollection that "items 1–3 were
pushed" was correct but incomplete — re-deriving from the log showed that items
**5 and 6 had also already landed**, in `c586d0e3`, and that item 4's *probe*
had landed in `9ac085e2` while its *fix* had not.

**That is the whole argument for re-deriving rather than resuming from a
summary:** two of the twelve items were finished and one was half-finished, and
no amount of care about the dispatch text would have revealed which.

Per-item landed state as measured, not as remembered:

| item | at resume | now |
|---|---|---|
| 2 (#894) | **landed** `16b2cc70` | unchanged |
| 3 (gate parity) | **landed** `e7adad94` | unchanged |
| 4 (duplicate key) | probe landed, **fix did not exist** | **landed** `19c872e0` |
| 7 (panel-auditor) | **committed, UNPUSHED** | **landed** `104ab3ff` |

---

## 2. #894 — exactly one response per path, and the suite has been seen red

**ONE `res.status(200)` IN THE BRANCH, and it is the `scoped_to_self` one.**
Enumerated mechanically rather than by eye: every response site between
`api/sd-data.js:11948` and `:12122` is listed below, and every one but the last
is a `return`ed refusal.

    :11950  401 NO_SESSION                 :12011  400 ANNUAL_WINDOW_UNKNOWN
    :11952  400 (state/requirement_type)   :12025  503 NOT_PROVISIONED (roster)
    :11957  503 NOT_PROVISIONED (rules)    :12029  return upstream()
    :11961  return upstream()              :12036  503 NOT_PROVISIONED (creds)
    :11978  400 STAFF_NOT_CALLER_SUPPLIED  :12040  return upstream()
    :12119  200 — the ONLY one, carrying scoped_to_self

The second `res.status(200).json` the pre-compaction screen showed is **gone**.

**`tests/sd_data_alf_compliance_staff_scope.js`: 16 arms, 3 runs at the tree
containing `16b2cc70`, EXIT 0 every run, first run 16 passed / 0 failed.**

**MUTATION-CHECKED, which is what makes it a guard rather than decoration.**
Against `16b2cc70^`'s `api/sd-data.js` with the current suite: **3 passed, 13
failed, EXIT 1** — every B arm (the three narrow roles), C1, all three D arms,
E1, F1 and G1. `api/sd-data.js` restored and `git status` confirmed clean
afterwards.

**It drives the REAL path.** The handler is required, not reimplemented; the
auth module is NOT stubbed, so `signSessionToken` mints and the handler's own
`verifySessionToken` checks signature, `typ`, role-in-app, expiry and the licence
binding; tokens are signed against the same `license_hash` the stubbed licence
returns, which is the trap `sairn-api-tester` §2 records. `fetch` and
`validateLicenseKey` are mocked. **The live round trip is NOT run** and this file
is a substitute for it, not a replacement.

---

## 3. `gate_parity_check.py` — compiles, 9/9 selftest, and the grouping measured

**The `CRITERIA_VERSION` lines are clean.** `py_compile` exits 0; every `\n` in
the file is a Python newline escape inside a string literal, not a literal
backslash-n in the text. Byte-inspected at lines 88–100, 575–585 and 700–715.

**Selftest: 9 arms, 3 runs, EXIT 0 every run, first run 9 passed / 0 failed.**
X1 flags the pre-fix #894 shape on a fixture; X2 proves the post-fix shape is
NOT flagged, without which X1 would pass on a checker that flagged everything.

**AND ON THE REAL FILE, which is the part a fixture cannot say.** Running
`--json` at HEAD and against `16b2cc70^`'s `api/sd-data.js`:

    flagged PRE, clean at HEAD :  alf_staff_credentials   <- #894, closed
    flagged at HEAD, clean PRE :  alf_staff               <- NEW, caused by the fix

So the real #894 table is clean at HEAD. **The tool still exits 1 on
`api/sd-data.js`** — 12 cross-resource tables and 4 same-resource groups — and
that is report-only by design, not a failure.

**X OF Y, the figure asked for.** The cross-resource pass groups by the TABLE a
branch reads. Of **125 distinct tables** seen in 288 disclosure units, **24 are
read by more than one resource** and are therefore the comparable set; the other
101 have a single reader and nothing to compare against. Those 24 tables span
**40 of the 143 resources** with a disclosure unit. **12 of the 24 are flagged.**

**THE NEW FLAG IS NOT NOISE AND IS NOT FIXED HERE.** `alf_staff` is flagged
because `alf_compliance_rules`/`evaluate` now consults a role set and
`alf_staff`/`read` (`:10144`) consults nothing — the fix made the sibling
asymmetry visible in the other direction. That is already tracked as its own row
(§8) and is a product decision about which role set belongs on `alf_staff`, not
a repair.

---

## 4. The duplicate `PURPOSES` key — the fix, and the bug report became the regression

**THE ASYMMETRY, measured by driving the real generator:**

    MISSING entry   -> exit 2, "REFUSING to generate", NAMES the tool
    DUPLICATE key   -> exit 0, silent, for ever

**THE FIX GOES TO THE SOURCE BECAUSE THE IMPORTED DICT CANNOT ANSWER THE
QUESTION.** `duplicate_purposes_keys()` reads the module's own file,
`ast.parse`s it, and finds the module-level `PURPOSES = {...}` by `tree.body`
rather than `ast.walk` — a literal nested inside a function would not be the one
the import evaluated. By the time `PURPOSES` is a dict the duplicate is gone.

**IT CARRIES THE THIRD STATE RATHER THAN FOLDING IT IN.** An unreadable or
unparseable source, or one where the literal is not found, refuses with **COULD
NOT CHECK**, worded separately from "no duplicates" — PR §1.11. A non-string or
computed key refuses too, rather than being skipped quietly.

**DRIVEN, NOT READ.** Injected duplicate → **EXIT 2**, same banner as the
missing half, naming the key and both line numbers:

    fail_open_scan.py -- written at line 86, SILENTLY DISCARDED;
    the copy Python kept is at line 87

Source restored and **compared byte-for-byte: identical**.

**THE PROBE BECAME THE REGRESSION AND NOT ONE LINE OF THE TWO ARMS CHANGED.**
`tests/run_purposes_duplicate_key_probe.py` was written as a routed bug report
because `tools/tooling_inventory.py` looked like cody's. Re-derived at HEAD:
cody's claim text **flags the file back** ("hank holds `tools/tooling_inventory.py`
... item 7 is FLAGGED BACK unlanded") and does not list it among its own FILES;
hank's claim does. The arms were written to go green on the fix, so the file
that accused the generator now guards it. **5 arms, 3 runs, EXIT 0 every run,
first run 5 passed / 0 failed.** One arm added — B1, requiring the KEY ITSELF in
the output, because "there is a duplicate somewhere" satisfies arm B and is not
actionable on a literal this size.

**NOT COVERED:** the COULD NOT CHECK state is not driven — that needs an
unreadable source, a different arm.

---

## 5. `sc_anesthesia_base_units` — the three impossible citations are gone, measured

**ALL TWELVE LINE CITATIONS IN THE ROW RE-DERIVED AT HEAD. Twelve of twelve
correct.**

| cite | at HEAD |
|---|---|
| `sairncode.html:5022` | `async function addAsaBaseUnit(){` |
| `:5041` | `function anLookupBaseUnits(){` |
| `:5047` | `document.getElementById('an-add-base').value = match.units;` |
| `:5049` | `note.textContent = 'Base units filled from your reference table…` |
| `:5052` | `note.textContent = 'No reference entry for this CPT code yet…` |
| `:4914` | `function renderAnesthesia(){` |
| `:4922` | `var totalUnits = a.base + timeUnits;` |
| `:4937` | `var dollarAmount = resolvedCf != null ? (totalUnits * resolvedCf) : null;` |
| `:4939`–`:4940` | the per-row currency cell |
| `:4957` | the **Billed Amount** KPI |

The three IMPOSSIBLE cites — `4904`, `4905`, `4906`, lines **inside** a function
the same sentence said started at `:4914` — **no longer appear as citations**.
They survive only inside the row's own account of the error, which is where a
corrected mistake belongs. The same is true of `:5014`: it appears once, in the
sentence explaining that it used to be cited and resolves to
`async function removeAsaBaseUnit(id)`, a DELETE function.

**The 21 SHA citations in `docs/CRITICALITY-TIERS.md` were checked too: 0 of 21
unreachable from HEAD.**

**NOTHING WAS CHANGED FOR ITEM 5.** The work had already landed in `264d8c3f`
and `c586d0e3`; this was verification, and verification that finds nothing is
reported as nothing rather than dressed up as a repair.

### The sweep I ran and am NOT reporting as findings

To answer *"for real"* rather than *"for this row"*, I swept all 408 register
rows for the impossible shape — a cite whose real enclosing function is not one
the row names. **It flagged 113 and it is not usable.** The one case I can
adjudicate, `doc line 264 … :5014`, is a **false positive**: it is the row's own
narration of a corrected error, and the sweep cannot tell a mention from a
claim. That is scrubber item 24 exactly, so the sweep stays in the scratchpad and
**none of its 113 flags is routed to anybody**. Reporting them would hand three
sessions a day of triage against a classifier I already know is wrong.

---

## 6. The three probes — the conversion was done, and it was the FALLBACK that was wrong

All three already called `git rev-parse --show-toplevel`, anchored with
`-C <this file's own directory>` and checked that git's answer contains this
file. `c586d0e3` did that correctly. **The safety net underneath was not checked
at all:**

    fallback = os.path.dirname(here)        # here = dirname(abspath(__file__))
    ...
    return fallback                          # unchecked

Put a copy under the home directory and `here` is that directory, so
`dirname(here)` is **`C:\Users\marsh` — the home repository**, which is the exact
wrong answer the anchoring exists to avoid. The anchored git call refused it,
printed the warning, and the fallback returned it anyway.

**DRIVEN, NOT REASONED.** `tests/run_worktree_root_home_repo_probe.py` extracts
each subject's own `_repo_root()` and EXECUTES it with `__file__` pointed at a
copy sitting under the home repo — the real situation, not a simulation.

    FIRST RUN, pre-fix :  16 passed,  3 failed, EXIT 1
                          arm B returned C:\Users\marsh from ALL THREE
    AFTER THE FIX      :  22 passed,  0 failed, EXIT 0, three runs

**A WARNING ON stderr IS NOT A REFUSAL, and that is the correction.** Arm B1
(*"the fallback is announced"*) **PASSED on the broken code**. The announcement
was there, beside a usable string, and nothing downstream reads stderr. An
unverifiable root now **exits 2 naming both candidates** — PR §1.11.

**ARM D IS WHY ARM B MEANS ANYTHING:** a naive `git rev-parse --show-toplevel`
from the same sandbox is asserted to DO answer `C:/Users/marsh`. Without it, B
would pass on a machine where git was unavailable, or where the home directory
had quietly stopped being a repository, and the probe would report the anchoring
as working while testing nothing.

**NOT COVERED:** the probes themselves are not run — two make live requests
against an audit licence. This is the ROOT DERIVATION only. And on a machine
whose home directory is not a repository the hazard does not exist; the probe
reports **COULD NOT RUN** there rather than a pass.

**`tools/worktree_root.py` named in the claim's FILES was never created** and is
not needed: the derivation is eight lines and a shared helper would have to be
imported, which is the thing that cannot be done before the root is known.

---

## 7. panel-auditor and the agents README — landed

`104ab3ff`. Recorded in `.claude/agents/README.md` and repeated here because it
bounds what the next session can assume:

- **`disallowedTools` / `isolation` frontmatter is NOT CONFIRMED ENFORCED.** A
  live test was run and did not establish enforcement. The allowlist (`tools:`)
  is what panel-auditor now relies on, not a denial list.
- **Subagents had NO Bash session-wide.** Not a scoping choice — the capability
  was absent.
- **`suite-driver` and `sweep-runner` are UNUSABLE this session.** Both are
  defined with Bash and Bash was not available to them, so anything needing a
  real exit code had to run in the main loop.

---

## 8. The six platform-work items — file and line

All six are rows in **`docs/SAIRN-OPEN-WORK-INDEX.md`**, line numbers at
`78324f56`. The anchors are stable; the line numbers are not, which is why both
are given.

| # | line | anchor | area | state |
|---|---|---|---|---|
| 1 | `:76` | `HOVER-H1-892-894-913-ROUTED-HANK-2026-10-06` | SAIRNcare | **FIXED** `16b2cc70` — `alf_compliance_rules`/`evaluate` shipped the roster |
| 2 | `:77` | `HOVER-H2-551-556-564-ROUTED-HANK-2026-10-06` | Platform | ROUTED, not fixed — `employee_id` case-sensitivity defeats deactivation in 14 verticals |
| 3 | `:78` | `HOVER-H2-557-ROUTED-HANK-2026-10-06` | Platform | ROUTED, not fixed — three more of the same class on other columns |
| 4 | `:79` | `HOVER-H1-906-909-ROUTED-HANK-2026-10-06` | Tooling | ROUTED **to cody by name** — `dead_rule_sweep` finds 35 dead rules where the claim said 2 |
| 5 | `:80` | `HOVER-H1-905-910-ROUTED-HANK-2026-10-06` | Platform | ROUTED **to fourth by name** — the CTO accounting statement contradicts `exec-context.js:185` |
| 6 | `:81` | `HOVER-H1-915-ROUTED-HANK-2026-10-06` | SAIRNvet | ROUTED, not fixed — `PROVISIONING_ROLES` checked in one of four actions |

**Two more rows were added by THIS batch** and are not part of the six:
`:63` `WORKTREE-ROOT-FALLBACK-HANK-2026-10-06` and `:64`
`ALF-STAFF-READ-UNGATED-HANK-2026-10-06`.

---

## 9. Two methodology rules — routed, not promoted

`docs/METHODOLOGY.md` is in my own claim's FILES, so writing them there would be
self-promotion into a document I hold. Both go to fourth in
**`docs/2026-10-06-hank-routed-to-fourth.md` §5**:

- **RULE A** — a check that refuses one direction of a drift has a MIRROR, and
  the mirror is the quiet half. Paid for by the duplicate-key asymmetry.
- **RULE B** — the arm that catches a wrongly-named assertion key is the
  ALLOWED-SIDE arm. Paid for by my own first run of the #894 suite, where
  asserting `staff` instead of `staff_findings` would have passed every narrow
  arm and only arm D failed loudly.

---

## 10. Review obligations — listed, one discharged, the rest BLOCKED

`python tools/tier_a_review_gate.py --list` exits 1 (overdue present): **31 open
obligations, 235 records.** Computed from the file: **23 are eligible to hank**
(not authored by hank). The most overdue eligible is **cody's
`2026-09-27T02:06:03Z`, 234h** — `mech_credentials, mech_site_assets, sc_claims,
sc_drg, sc_eligibility, sc_fraud, sc_hcc, sc_pctc, sc_prebill`.

**ONE WAS DISCHARGED THIS BATCH**, before cody's claim was visible: fourth's
`2026-09-26T19:12:42Z` (237h at the time, the most overdue then), reviewed at
`2026-10-06T16:44:25Z`, verdict **SOUND ON ALL THREE SUBSTANTIVE CLAIMS**,
through the only sanctioned path, `--discharge --takeover`.

**NO FURTHER DISCHARGE, AND THIS IS FLAGGED BACK RATHER THAN REWORDED PAST.**
`docs/tier-a-reviews.json` is CODY'S under a live claim whose task text is
*"Tier A discharge most-overdue-first"* — the same phrase, verbatim. cc and
fourth both declined on exactly this ground in the same cycle (cc listed 25 and
took none; fourth routed 9). Taking the 234h record would be three sessions
discharging the same queue from three clones.

**WHAT THE LIST ALSO SAYS, and it is not mine to fix:** 4 of the 31 are
**COULD-NOT-TELL** — their recorded `opened_at_sha` does not resolve in this
clone, rebased away without a re-seat. That is cc's root-cause item.

---

## 11. Pull and status discipline

Every HEAD-dependent check was re-run after a pull. The push raced **four
separate times** against other sessions; each time the sequence was pull-rebase,
**re-run both generators**, commit the post-rewrite re-seat, push. `git status`
was read after every tool this session did not build.

**THE RE-SEAT RAN THREE TIMES ON ONE RECORD** — `c5e65e9e` → `34d79353` →
`19c872e0` — because each rebase rewrote the commit the register cites. That is
`.githooks/post-rewrite` working, not a correction. **Verified by REACHABILITY,
not existence:** `git cat-file -t` says `commit` for an unreachable object, so a
presence check would have reported every stale citation as sound. All **458**
register records resolve to a commit reachable from HEAD.

---

## 12. One finding this batch created and closed in the same breath

`docs/SAIRN-OPEN-WORK-INDEX.md:75` cited `03d03cf7` for the #894 fix — a commit
that **exists in this clone's object database and in no other**, because a rebase
rewrote it. Re-seated to `16b2cc70`, confirmed three ways: same subject,
reachable, and `git log -S"ALF_CRED_READ_ROLES[session.role]"` names it as where
the content entered.

**AND THE REST ARE MEASURED RATHER THAN WAVED AT.** Re-measured at `78324f56`
after the fix: of **385** distinct sha-shaped citations in that file, **51 do
not resolve to a commit reachable from HEAD** — **10** are real objects
unreachable from HEAD (the rebase-orphan class) and **41** are not objects in
this clone at all, which is a **different** problem: an unfetched commit from
another clone and a typo are indistinguishable from here and must not be folded
together. Not fixed, not claimed clean, and cc holds the root cause.

The figures moved while this batch ran — 383/52 before the fix, 385/51 after,
because two citations were added and two were re-seated. **Re-measure; do not
quote these.** The command is six lines and is in `docs/handoff-hank-2026-10-06b.md`.
