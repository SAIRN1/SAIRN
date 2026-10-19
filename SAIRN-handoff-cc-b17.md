# SAIRN handoff — cc batch b17 — 2026-10-19

**Written at a point where nothing is half-finished.** All four items are
closed, every code change is on `origin/main`, the tree is clean apart from
this file and the two artefacts that follow it, and no edit is mid-flight. The
batch spans two days — claimed 2026-10-17T15:05:26Z, finished 2026-10-19 —
because the dispatch arrived in one session and the date rolled during it; it
is **one session, one transcript**, unlike b16.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\4d4f63b1-1aa9-48c9-b832-ddd1c2674580.jsonl`
— 2,403,915 bytes, **367,417 tokens (36.7% of the 1M window)**, measured by
`tools/sairn_status_line.used_tokens()` against the transcript itself. **This
transcript also contains b16's wrap**, so the figure covers both.

---

## Committed / pushed state

| sha | what |
|---|---|
| `d8be810a` | hint+lock(gate skip) — the documented scoped form was TWO commands and said it was one, and a crashed criteria lock exited 0 |
| `92b46df1` | bridge(tier 0 #1) — the status registry reaching the board was a sentence, and now it is a measurement |
| `1d97c4b9` | fix(index check) — the rows hank reported as malformed were already repaired, and the real defect was in the tool reading them |
| `f116ae83` | record(defects) — the index-check naive split, with the one row it made invisible |
| `9a8ba078`, `d653b3bd` | chore(scrutiny) — the ledger rows the push gate wrote |
| `3f579205`, `92471db7` | reseat(register) — two rebases moved the fix and the citation followed each time |
| `e18d72b9` | chore(claims) — the claim, and later the published addendum |

`HEAD == origin/main`, **0 ahead / 0 behind**, zero stashes.

**Files:** `tools/gate_skip.py`, `tools/sairn_push_gate_hook.py`,
`tools/index_duplicate_check.py`, `tools/tooling_inventory.py` +
`docs/TOOLING-INVENTORY.md`, new `tools/status_board_bridge_check.py`, new
`docs/2026-10-17-cc-b17-locked-entry-crash-injection.py`, new
`docs/2026-10-19-cc-b17-status-board-bridge-live-evidence.md`, new
`docs/2026-10-19-cc-b17-routed.md`, `docs/defect-density-register.json`,
`docs/scrutiny-flags.json`, `docs/batch-manifest-cc-b17.json`,
`SAIRN-ACTIVE-WORK-cc.md`. **No `api/`, no `sql/`, no app HTML, no `tests/`
file** — hank b18 holds `api/sd-data.js` and that conflict was declared and
not overridden.

**Overrides: NONE, in any form.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no
`SAIRN_SEED_GATE`, and **no row was added to `docs/BYPASS-LOG.jsonl` by this
batch** — which is an audit rather than an assertion, because the gate records
an override *attempt* before deciding whether to honour it. No `--force` in any
spelling. No hook added or restored; `settings.json` never committed. No
auditor clone entered or written.

---

## The four items

**1. The gate's refusal hint now names the real two-step.** Michael's decision:
keep the two-step, **no auto-grant-from-environment path**, because the grant
being its own act — validated once, written once, logged once — is what makes
it auditable. Measured before editing: with both variables set and nothing
else run, `active()` is None, `_scoped_skip()` is False, no record exists, the
gate denies; the push path has **zero** calls to `grant()` and **zero** to
`requested()`. Fixed in **all three** places a reader meets it — the hook's
`OVERRIDE_HINT`, `gate_skip.BLANKET_REFUSAL` (which the hook prints) and
gate_skip's module docstring. 56/56 arms; ABLATION 3 shows the b16 text passing
every pre-existing arm and failing all three new ones.

**2. TIER 0 #1 — the bridge is measured, not re-claimed.** New
`tools/status_board_bridge_check.py`, 15/15 fixtures, fails closed. A nonce
written into cc's row at `2026-10-19T07:32:48` was read back **through the
Drive API** at `07:32:49` in the board's own `## cc` section, Drive id
`19GSUTWQLddPwZiLEUNfssAjrMxK4vVE1`. All six agent rows bridge correctly.
H1/H2 can re-derive it with their own nonce — steps in
`docs/2026-10-19-cc-b17-status-board-bridge-live-evidence.md`.

**3. Methodology — a lock that crashes is not a lock that passed.** The push
gate's `--selftest` was dispatched inside `except Exception: sys.exit(0)`. A
NameError in one of this batch's own arms printed 23 of 50 arms, no summary,
and **exited 0**. End-to-end on a copy with a crash injected: **pre-fix exit 0
with zero bytes of stdout, post-fix exit 2** naming COULD NOT RUN.

**4. The index rows were already repaired, and the recommended repair would
have been a regression.** All 855 main-table rows carry 8 unescaped pipes.
hank's premise about the backslash rendering is measured false in two renderer
presets. The real defect was in `index_duplicate_check`'s naive split: **one
row of the index was invisible to the check and nothing said so.** 836 rows
compared before, 837 after.

---

## Claims held

**One**, `cc`, with a published **addendum**: `tools/index_duplicate_check.py`
is cc's by the owner map and was **not** in the batch's FILES list when it
opened — the index rows turned out to be already repaired and the real defect
was in the tool. Declared rather than edited quietly. Released at the end of
the wrap.

**Conflict declared and NOT overridden:** hank b18 holds `api/sd-data.js`, so
cody's SAIRNscape `customers` gating fix is **not** in this batch and stays
routed.

---

## Open items — each with why it is open and the exact next step

1. **cody's SAIRNscape finding is still the highest-value open item and is
   BLOCKED on a file hank holds.** `customers` carries name, phone, email and
   street address and is reachable on the licence key alone for read and write,
   proven live with a control. The root cause is the register letter, not the
   gate: `customers` is carried B/B while its confidentiality cell already says
   the row holds PII. **Next step:** two lines in `SD_SESSION_GATED` and
   `SD_GATE_APP` in **one** edit, plus the B→A retier, when hank releases
   `api/sd-data.js`. **The assertion that matters after: the WRITE path must go
   400 → 403, not just the read.** Full account:
   `docs/2026-10-05-sairnscape-customers-licence-key-alone.md`.
2. **H1/H2: 19 stale numbered copies of the auditors' latest files on the Drive
   mount** (H1 6, H2 13). A reader who opens one gets a complete, plausible
   board four days old. **Not deleted by cc** — a build agent removing files
   from an auditor's published set is the separation boundary running the wrong
   way. **Next step:** delete them, or name the one that is load-bearing.
3. **hank: three undeclared near-duplicate index pairs**, pre-existing, two of
   them his (lines 144/145 SAIRNgrounds at 0.988, 255/257 Tooling at 1.000).
   **Next step:** merge, or declare the pair in `ACCEPTED` with a reason — that
   dictionary exists for this and is empty.
4. **Everyone: the fail-open-over-a-lock shape.** A lock entry point reached
   from inside a handler that returns 0 on any exception. cc's sweep of
   `tools/` found **one false positive and zero real instances**, and that
   sweep's first version found nothing *including in the file it was written to
   detect* — so the shape is worth a read of your own `__main__`, not a trust
   in cc's count.
5. **hank or cc: two CONTEXT cells on the board render report prose** rather
   than a figure. Either one `set --context` from hank, or a parse in
   `sairn_board_publish.py` that stops at the first whitespace — cc's file,
   deliberately not changed mid-batch without saying so first. **Say which.**
6. **Three b12 test-file-floor layers remain unarmed**, carried from b14, b15
   and b16 unchanged. `tracked-intersection` is the urgent one. `tests/` is
   cody's.

---

## Two things that will cost the next session time if nobody says them

1. **A backslash in a CLI body is mangled exactly like a backtick.** A heredoc
   lost one from a regex twice in this batch — `(?<!\\)\|` arrived as
   `(?<!\)\|` and died on an unterminated subpattern. Same fix as for
   backticks: **write the program to a file and run the file.**
2. **A line number in a routed note ages out within a batch.** hank's rows
   "355 and 356" were lines 479 and 480 four days later, because the index
   grows at the top. Search for the quoted *content*, never the number — and
   if you route a row, quote a span from it.
