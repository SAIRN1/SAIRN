# The tooling inventory — what exists, what it catches, and what actually runs

**Built 2026-09-09 (Cody).** First real inventory of `tools/`. Every number
below is **derived** from the repo at commit time — `.claude/settings.json`,
`.githooks/pre-push`, `tools/sairn_push_gate_hook.py`, and `git ls-files` —
not read off any prior document. The derivation scripts are throwaway; the
method is written out under *How to re-derive this* so the next session can
redo it in one pass rather than trusting this file.

**Why it exists.** A large amount of standalone tooling was written across the
last two weeks — one checker per incident, each correct, each committed, none
of it collected anywhere. Nothing says which of them run, which block a push,
and which have never been executed since the day they were written. That is
the same shape as every other claim-in-two-places failure this repo records,
applied to the safety net itself.

---

## The headline

**77 files in `tools/`.** By what actually invokes them:

| Status | Count | Meaning |
|---|---:|---|
| **BLOCKING** | 10 | Can refuse a push or a tool call |
| **REPORT-ONLY** | 3 | Run automatically, never block |
| **ADVISORY** | 2 | Session-start / prompt hooks, informational |
| **UNWIRED** | 33 | Nothing runs these. 28 are checkers/sweeps; 4 are live network probes, correctly manual; 1 is a harness bundled with its checker |
| **LIBRARY / GENERATOR** | 29 | Not checkers — parsers, fetchers, seed builders |

**The finding worth acting on: 28 working checkers are run by nobody.** That is
nearly twice the 15 that are wired at all, and almost three times the 10 that
can actually refuse anything. Several were written *in response to
a real production incident*, proved on that incident, committed, and have not
looked at the codebase since.

**And a sharper sub-case: nine of those 28 have a probe under `tests/` that
`run_all_tests.py` executes on every push.** So the suite proves the checker
*works* — on fixtures — while nothing ever points it at the real code. A green
probe on an unwired checker is the most convincing possible form of "we are
covered," and it is coverage of the tool, not of the codebase.

---

## BLOCKING (10)

Two entry points, and they are not the same one.

**`.claude/settings.json` PreToolUse — fires on a Claude Code tool call:**

| Tool | Catches |
|---|---|
| `git_push_master_guard.py` | a push aimed at `master`, which is stale |
| `sairn_push_gate_hook.py` | the seven checks below |
| `redaction_check.py` | secrets in what an agent is about to Write/Edit |

**`.githooks/pre-push` — fires on the GIT OPERATION**, so a push from a Python
subprocess (`sairn_claim.py`) cannot spell its way around it. This is the
stronger of the two and exists because the PreToolUse regex missed exactly
that case on 2026-09-01. **Per-clone install:** `python tools/install_git_hooks.py`
— `.git/` is not versioned, so a clone that never ran it has no pre-push hook
and gets only the weaker Claude-Code-shaped gate.

**The seven push-gate checks. Every one has a deny path — all seven block:**

| # | Tool | Catches |
|---|---|---|
| 1 | `sairn_load_state_check.py`, `load_deadline_seed.py` | a seed file changed in the repo but never loaded live |
| 2 | `employee_auth_guard_check.py` | SQL that would leave a licence with no active provisioner — unrecoverable through the API |
| 3 | `sairn_sql_preflight.py` | SQL checked against a live schema snapshot; **fail-closed** if it cannot tell |
| 4 | `sairn_seam_check.py` | an endpoint that does not forward every input its engine reads (SAIRNlaw ran Florida five days late this way) |
| 5 | `sairn_reachability_check.py` | a feature nothing can reach — squatted id, hidden container, unwired entry point |
| 6 | `redaction_check.py` | secrets in the ADDED LINES of the outgoing range — covers what an agent did *not* write |
| 7 | `preauth_oracle_check.py` | a refusal an endpoint gives before it knows who is asking |

`SAIRN_SEED_GATE=off` at the FRONT of the push command overrides the gate. Say
so out loud when you use it.

**Two membership notes, so the count of 10 is checkable.** `load_deadline_seed.py`
appears in check 1 and is *also* listed under LIBRARY/GENERATOR below — it is a
seed reader the check calls, not a checker, and it is counted once, as a
library. `sairn_claim.py` is named in the gate's own header as the caller that
motivated the pre-push hook; it is a workflow tool, not a check. The ten are:
the three PreToolUse entries above plus `sairn_load_state_check.py`,
`employee_auth_guard_check.py`, `sairn_sql_preflight.py`, `sairn_seam_check.py`,
`sairn_reachability_check.py` and `preauth_oracle_check.py` — `redaction_check.py`
is in both lists and counted once.

---

## REPORT-ONLY (3)

| Tool | When | Catches |
|---|---|---|
| `run_all_tests.py` | PostToolUse, async, after a push | every test file, including the ~58% no session ever ran |
| `deploy_verify_notify.py` | PostToolUse, async, after a push | live site still not matching `HEAD` after a deploy |
| `html_script_check.py` | PostToolUse on Write/Edit | a broken script block in an app file |

**Corrected today, and it matters for reading this table:** both Bash hooks
carried `"if": "Bash(git push*)"` in config. **A hook entry has no `if` field**
— its only gate is `matcher`, which matches the tool NAME — so the unknown key
was ignored in silence and the full mutating suite ran after **every Bash tool
call**. Fixed by Hank in `4cbbcf23`; both now gate on the command text in code.
The symptom was ten concurrent suite copies in one clone in four minutes, which
is what published a `PROBE` fixture commit to `origin/main` and what stripped
`sairnvet.html`'s corrupt-store guard repeatedly overnight.

## ADVISORY (2)

`sairn_claim_hook.py` (SessionStart — surfaces other sessions' active claims)
and `session_lock_check.py` (SessionStart + UserPromptSubmit).

---

## UNWIRED — the 28 checkers nobody runs (of 33 unwired files)

**Group A — has a purpose-built probe in `tests/`, so the SUITE proves the tool
works, but nothing runs the tool against the codebase.** These are the ones to
promote first: they are already known-good, so wiring them is a decision about
noise, not about correctness.

| Tool | Catches | Probe that watches it |
|---|---|---|
| `fail_open_check.py` | a read that turns "I could not ask" into "there is none" | `tests/fail_open_browser_probe.py` |
| `write_without_readback_check.py` | a resource written to the server and never read back | `tests/write_readback_probe.py` |
| `local_only_collection_check.py` | a business collection that never reaches a server at all | `tests/local_only_probe.py` |
| `discarded_verdict_check.py` | a refusal that is computed and thrown away | `tests/discarded_verdict_check.test.js` |
| `discarded_verdict_crossfile.py` | the cross-module half of the same | `tests/run_discarded_verdict_crossfile_probe.py` |
| `waf_rule_check.py` | a firewall rule that is supposed to be protecting something and is not | `tests/run_waf_rule_check_probe.py` |
| `md_table_check.py` | a markdown row whose prose pipes broke its own columns | `tests/run_md_table_check_probe.py` |
| `key_collision_check.py` | a localStorage key written by more than one feature | asserted in `tests/sairndental_settings_patch.js` |
| `licence_recoverability_check.py` | a licence sitting in the unrecoverable-credential state right now | only its HTTP path, in `tests/sairn_http_challenge.py` |

`sairn_app_map_check.py` sits here too, with the same partial coverage as the
last row: `tests/sairn_http_challenge.py` asserts it fetches through
`sairn_http.py`, which is a claim about how it reaches the network and not
about what it finds.

**Group B — no probe and no invoker. Written, proven once by hand, never run
again** (18): `div_balance_check.py`, `duplicate_global_check.py`,
`literal_drift_check.py`, `missing_dom_target_check.py`, `nav_panel_check.py`,
`orphan_register_check.py`, `panel_nesting_check.py`, `sairn_ai_fact_scan.py`,
`sairn_dead_button_audit.py`, `sairn_dead_function_sweep.py`,
`sairn_reachability_probe.py`, `sairn_stale_snapshot_scan.py`,
`sairn_strict_args_check.py` (+ `strict_args_harness.js`),
`sairnlaw_citation_audit.py`, `va_rule_currency.py`, `vercel_config_check.py`,
`verify_review_gates.py`, `posthook.cjs`.

**Three in Group B are named as REQUIRED by a skill or by `CLAUDE.md` and are
still not wired — the gap between a documented rule and a mechanism:**

- `sairn_dead_button_audit.py` — Guardian v2 check 27 says run it "against
  every app file before declaring it done."
- `nav_panel_check.py` — Guardian checks 16–18, and the safe-editing rules say
  to run it **after every single edit**.
- `vercel_config_check.py` — Guardian's own note says a `buildCommand` over
  Vercel's 256-char limit "takes the whole production site down while looking
  like nothing happened," and it is unwired.

`div_balance_check.py` is in the same sentence of the safe-editing rules as
`nav_panel_check.py`. Four rules that depend on remembering, in a file whose
recurring lesson is that rules depending on remembering are the failure mode.

**Not a recommendation to wire all 28.** Several are one-off audits
(`sairnlaw_citation_audit.py`, `va_rule_currency.py`, `reclassification_sweep.py`)
and several are live probes that need a network and a real licence
(`rf_claim_gate_live_probe.py`, `rf_roundtrip_probe.py`,
`probe_public_book_guardian.py`) — those are correctly manual. The decision each
one needs is *blocking / report-only / deliberately manual*, recorded once, not
left unanswered by default.

---

## LIBRARY / GENERATOR (29) — not checkers, do not wire

Parsers and helpers (`jscomments.py`, `js_code_only_diff.py`,
`extract_scripts.py`, `extract_panels.py`, `outline.py`, `checkblocks.py`,
`sairn_dom_snapshot.js`), network and source fetchers (`sairn_http.py` —
the one place that knows how to get past Vercel's bot mitigation —
`sairn_source_fetch.py`, `fetch_blocked_doc.sh`, `gh_push.py`, `gh_verify.py`),
the installer (`install_git_hooks.py`), the seed loader
(`load_deadline_seed.py`), the superseded `sairn_build_load_gates.py`, and
**16 SAIRNlaw calendar/seed generators** (`gen_*_calendar.py`, `gen_*_seed.py`)
which are run once per state and produce a committed artefact.

---

## The skill-list audit — RE-DERIVED 2026-09-09, and it is still accurate

`CLAUDE.md`'s skills section carries a re-count dated 2026-09-03 (Hank). Every
claim in it was re-measured today against the real directories. **All of them
hold:**

| Claim | Measured 2026-09-09 |
|---|---|
| 60 skills on disk | **60** in `~/.claude/skills/` |
| 32 SAIRN, mirrored in this repo | **32** SAIRN-prefixed; `.claude/skills/` holds exactly those 32 |
| 28 general and user-level only | **28** |
| mirrors verified content-identical | **0 real content differences** |
| twelve mirrors differ by CRLF only | **exactly 12**, and 20 byte-identical |
| `grill-me` present but model-invisible by design | present, `disable-model-invocation: true` |
| `security-auditor` removed, do not reinstate | absent from both stores |
| `sairn-code-guardian` not in any skill store | absent from both stores |

The canonical store `C:/SAIRN/skills/sairn/` also holds 32, and nothing is in
the repo mirror that is not in the user store. **The twelve CRLF-only diffs are
not drift** — a bare `diff` reports them as changed and that remains a false
alarm; normalise with `tr -d '\r'` before believing any byte comparison.

**One wording correction, not a factual one.** `CLAUDE.md` says the audit found
"52 skills on disk" (2026-08-30) and then re-counts to 60 (2026-09-03), telling
the reader to re-count rather than trust either. That instruction is right and
this section does not replace it — 60 is what today measures, and it will be
wrong the next time a skill is added.

---

## How to re-derive this

Do not trust the counts above; they are a fact about 2026-09-09.

1. **The set:** `ls tools/` minus `__pycache__`.
2. **Hook wiring:** read `.claude/settings.json` `hooks` and match
   `tools/<name>.py` in each `command`. `PreToolUse` = can block;
   `PostToolUse` = cannot. **A hook entry has only `matcher`** — any other
   gating key is ignored in silence (this cost a night on 2026-09-09), so
   confirm the gate is in the tool's own code.
3. **Push-gate membership:** the checks are `# ── CHECK n:` blocks in
   `tools/sairn_push_gate_hook.py`; a check blocks if its block contains a
   `deny(` path.
4. **Pre-push installed in THIS clone:** `git config --get core.hooksPath`
   must print `.githooks`. It is per-clone and not automatic.
5. **Probe coverage:** walk `tests/` for the tool's filename, then **read the
   hit** — several are provenance comments or assertions about an unrelated
   property, not probes of what the checker catches.
6. **Skills:** count `SKILL.md` files in `~/.claude/skills/` and
   `.claude/skills/`, and compare after `tr -d '\r'`.
