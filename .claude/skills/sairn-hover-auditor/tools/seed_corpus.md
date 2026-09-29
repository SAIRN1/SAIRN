# Seed corpus

Designed in SKILL.md (2026-09-17, under the Anthropic-benchmark research),
never built until tonight (2026-09-18), on direct instruction. Anthropic's
breadth-first red-teaming agent uses 255 named seed instructions with tracked
coverage; this is SAIRN's own version, built from real data already on hand
rather than hand-authored from nothing, with the one addition Anthropic's
list structurally cannot contain: SAIRN's own real, recurring bug SHAPES.

**How to use this file.** Before a fast or deep pass with no other target
already chosen, pick a seed below and log which one was tried against which
target (`--ref` on the hover_log entry). A seed already tried against a
given target is not disqualified from being tried again later — code changes
— but tracking the pairing turns "did this role look everywhere" into a
checkable fact instead of an impression, the same payoff 255 named seeds give
the red-teaming agent's own coverage.

**Growth.** This is a first version, not a closed list. Add a numbered entry
under the relevant section whenever a genuinely new angle, technique, or
real recurring shape is confirmed — same discipline as
`sabotage_benchmark/`'s own fixtures growing one per newly-confirmed shape.

---

## A. Real, recurring SAIRN bug shapes (confirmed more than once)

The addition Anthropic's own seed list cannot contain — these are shapes
this platform has actually shipped and re-shipped, not generic categories.

1. **CSV formula injection** — a cell-quoting helper escapes embedded quotes
   but never neutralizes a leading `=`/`+`/`-`/`@`. Confirmed in 13+ files
   platform-wide before the shared fix (`api/_lib/csv-cell.js`, 885fd0b9).
   Seed: grep any NEW CSV/export helper for the same missing guard.
2. **Stale hand-listed test-harness dependency injection** — a lifted
   function's free-variable list is hand-typed in a test harness and drifts
   when the real function grows a dependency, throwing `ReferenceError` at
   run time. Named "found five times" in SKILL.md. Seed: any harness using
   `new Function(name1, name2, ..., src)` — confirm the name list is
   *derived*, not hand-typed, or re-diff it against the real function's free
   vars by hand.
3. **Client-trusted role gating a sensitive action** — a role read from
   `sessionStorage`/`localStorage` with no server-side re-verification at
   the point of use. Confirmed live: sairnscape.html (hover_log #228).
   Seed: grep any `sessionStorage.getItem(...role...)` or
   `localStorage.getItem(...role...)` and confirm a server call sits between
   the read and the sensitive action, not just after page load.
4. **Regex bracket-class silent miss** — a POSIX ERE bracket expression
   (`[:=]`, or a `\s`/`\d`/`\w` shorthand combined with other escapes inside
   `[...]`) compiles cleanly and silently matches nothing. Confirmed 3x in
   one tool build this session (`git_history_secrets_scan.py`). Seed: any
   new `git -G`/`grep -E` pattern with a bracket expression — run it against
   a known-positive fixture before trusting a zero result from it.
5. **Self-referential `--check`** — a generator's own verification mode
   compares its output to a previously-generated file rather than to the
   real source of truth. Named as the eighth cross-domain discipline;
   confirmed a second time at entry 111 (stale NHI-register warning). Seed:
   any `--check`/`--verify` flag — trace what it actually diffs against.
6. **Same bug shape, found and fixed independently more than once** —
   the unescaped-pipe index-row bug (found/fixed twice) and the
   `sairnbiz_ledger_source_id.js`-shaped `ReferenceError` (found 5 times).
   Seed: when a fix lands, grep the rest of the codebase for the identical
   pattern before assuming this was the only instance.
7. **Wholesale-replacement / server-wins / console-only-log composition** —
   named in SKILL.md's benchmarked-tools section as a recurring shape; not
   yet re-confirmed by this role directly. Seed: any sync/merge function —
   confirm it merges additively rather than replacing wholesale on conflict,
   and that a swallowed conflict logs somewhere a human will actually read.
8. **Network-failure-forces-fallback-to-a-client-only-predicate** — named
   in the same section; not yet re-confirmed directly. Seed: any function
   that falls back to a client-computed value on a failed fetch — confirm
   the fallback is disclosed to the user, not presented as equivalent to a
   real server answer.
9. **The `[:=]`-shaped "prose rule never saw a sentence with an apostrophe"
   class** — real, confirmed platform incident (`1a79c8a0`, git log, this
   session): a prose-matching rule with an unstated grammatical assumption.
   Seed: any regex intended to match natural-language prose — test it
   against a sentence containing an apostrophe, an em-dash, and a quoted
   sub-phrase before trusting it.

## B. Named techniques never yet used in a real check (from hover_self_health.py)

Re-run `hover_self_health.py`'s technique tracker before treating this
sub-list as current — it is the live, computed source; this is a snapshot.
As of seq 246: PTES dedicated pass, chaos engineering (hypothesis-first
injection), WADA biological-passport staircase, WCAG-EM sampling, FinOps/
showback, CMMI maturity ladder, bus-factor scanner *by name* (built and run,
but the automated tracker's own name-match missed it — worth noting as a
tracker limit, not a real gap), formal equivalence checking, technical due
diligence (5 pillars), Diátaxis documentation audit, purple teaming, FIA
scrutineering-style spec-vs-artifact diff, GLI two-stage proof.

## C. OWASP Top 10 (2025) — the concrete vulnerability-class lens

Use alongside STRIDE (Section D), never instead of it — see SKILL.md's own
reconciliation. Broken access control; cryptographic failures; injection;
insecure design; security misconfiguration; vulnerable/outdated components;
identification & authentication failures; software/data integrity failures;
security logging & monitoring failures; server-side request forgery.

## D. STRIDE — the property lens OWASP does not cover

Spoofing (Authentication); Tampering (Integrity); **Repudiation**
(Non-repudiation — the property OWASP's list does not name at all, and the
one this platform's own hash-chained self-log and audit checkpoints are a
real mitigation for); Information Disclosure (Confidentiality); Denial of
Service (Availability); Elevation of Privilege (Authorization).

## E. Emerging, currently-forming standards (2026-09-18 WebSearch pass)

Real, dated, not yet checked against this platform at all:
- **ISO/IEC 42001** control areas (risk assessment, data governance,
  transparency, life-cycle oversight) — a real, structured checklist this
  platform has never once compared itself against.
- **NIST AI Agent Interoperability Profile** (Q4 2026 deliverable) — identity/
  authorization, security/risk management, monitoring/logging for
  multi-agent systems — the single most directly-applicable emerging
  framework to this platform's own four-build-agent-plus-hover shape.
- **ISO 26262 / ASIL** confirmation-review independence scaling — compare
  against this role's own Tier A/B/C independence scaling; not yet done.

## F. Cross-domain disciplines already in SKILL.md, reframed as seeds

- Lock a check's criteria against synthetic fixtures BEFORE running it on
  real data (the blind-lock discipline — already standard practice here,
  named as a seed so a fresh session without full SKILL.md context still
  reaches for it).
- Report accuracy and stability as two numbers, never one combined figure.
- Set the alarm tighter than the failure point.
- Run the deep validation with its subject NOT trusted (presumptive doubt).
- Require a structurally different method for independence, not a second
  run of the same tool.
- Byte-identical is not safe-in-context (Ariane 5) — re-qualify scale/input
  range/criticality tier before treating a copied pattern as safe.
- Re-reference a check against its SOURCE on a cadence taken from a measured
  drift rate, not an assumed one.
