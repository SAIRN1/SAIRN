# Vet report — the nine-skill SAIRN pack

Run 2026-08-30 with `sairn-skill-vetter`, because the pack README names this as
the pre-ship gate and a stated intention is not a result.

---

## VERDICT — split, because the answer differs by destination

    ADMIT                    for internal use, today, as installed
    ADMIT WITH CHANGES       for shipping to anyone outside the team

**Safety:** clean. No exfiltration, no instruction-override, no destructive
operations. Every grep hit was either `sairn-skill-vetter` quoting its own
detection patterns, or a documented example with a placeholder
(`Authorization: Bearer <KEY>`).

**Truth:** no versioned external standard is cited anywhere in the nine — which
is a **pass, not a gap**, and is recorded so a later vet does not flag it. These
skills are incident-sourced, not standard-sourced; there is no OWASP/WCAG-style
revision to go stale. That is precisely the failure that killed
`security-auditor`, and this pack is structurally immune to it.

**Overlap:** precedence was undeclared in four of nine. Two fixed (mine); two
outstanding.

**Unreadable / not verified — mandatory line:** see the section at the end. It
is the largest finding in this report.

---

## Findings

### 1. `allowed-tools` undeclared on all nine — and one is a regression

Gate 1.4. **Zero of nine declared `allowed-tools`.** They inherit everything.

Worse, `sairn-differential-review` **dropped a declaration its third-party
original had** — `differential-review` ships `allowed-tools: Read Write Grep
Glob Bash`; the SAIRN rebuild declares nothing. A rebuild that removes a safety
declaration the incumbent had is a regression, however good the content is.

**Fixed for the three I own**, declared narrowly since all three read and reason
rather than write:

    sairn-rbac            Read Grep Glob Bash
    sairn-skill-author    Read Grep Glob
    sairn-context-budget  Read Grep Glob Bash

**Outstanding on CC's six.** Not my files to edit mid-flight.

### 2. Five of nine had no honest-scope section

Gate 3.3 — *"Every SAIRN skill that has held up over time has a 'what this does
not do' section."* Missing from `sairn-rbac`, `sairn-context-budget`,
`sairn-differential-review`, `sairn-memory-curator`, `sairn-minimalism`.

**Two of the five were mine.** Both fixed, with a real scope statement rather
than a formality — `sairn-rbac` now says it does not cover any app's role
vocabulary (deliberately, because a list here would go stale), authentication
itself, Postgres RLS, or non-SAIRN authorisation models.

**Three outstanding on CC's six.**

### 3. Precedence undeclared in four of nine

Gate 3.5 — a buyer must know when to use this instead of the incumbent.
Missing from `sairn-rbac`, `sairn-context-budget`, `sairn-api-tester`,
`sairn-skill-vetter`. **Two fixed (mine), two outstanding.**

### 4. SHIPPING BLOCKER — live licence keys and a real name in the files

Gate 3.4. The nine contain **six licence-key strings and one real first name**:

    LAW-PINNACLE-2026   RF-PINNACLE-2026   SD-PINNACLE-2026
    SD-AUDIT-2026       SD-PARTNER-2026    DNT-TEST
    "Michael"  (sairn-context-budget, quoting the SQL-client incident)

**These are live keys, not illustrations.** `SD-PINNACLE-2026` returned HTTP 200
against the production endpoint earlier tonight, and it carries real employee
credentials including a named person's account.

**This is not a problem internally** — every one of these is already public in a
committed `sql/*_license_seed.sql` file, and inside the team the keys *are* the
evidence that makes each incident checkable. **It is a problem for a shipped
pack**, which is a different distribution surface: it hands a customer a live
tenant identifier and an invitation to probe it.

**Deliberately NOT stripped now.** Removing them would destroy the verifiability
that is the pack's entire moat, to solve a problem that does not exist yet.

**Required pre-ship step, as packaging rather than content:** redact the six keys
to shapes (`<APP>-PINNACLE-<YEAR>`) and the name to a role, in the *build* that
goes out — not in the working copies. Add it to whatever produces
`dist/skills-public/`.

---

## Unreadable / not verified

**I did not read CC's six skills line by line.** Gate 1.1 says read every line
before installing, and they were already installed by another session before I
saw them. What I actually did was run every mechanical gate across all nine —
exfiltration, override, destructive, secrets, tools, scope, precedence, version
currency — and read every line those greps surfaced. That is a real check and it
is **not** the same as Gate 1.1.

**I did not machine-verify CC's six for factual accuracy.** The 31/31
verification covers `sairn-rbac`, `sairn-skill-author` and `sairn-context-budget`
only. CC's six assert their own incidents; I have not checked one of them
against the codebase. Given the pack's entire claim is *"every rule traces to a
real failure"*, **that is the gap that matters most before anything ships.**

**Not checked:** whether any of the nine teaches a practice this platform found
harmful (Gate 2.9) beyond what pattern-matching would catch. That needs the
line-by-line read above.

---

## What has to happen before this ships

1. Line-by-line read of CC's six — by CC, or by whoever ships it.
2. Machine-verify CC's six factual claims, to the 31/31 standard the other three
   met.
3. `allowed-tools` on CC's six, and restore the one `sairn-differential-review`
   dropped.
4. Honest-scope sections on the remaining three.
5. Precedence on the remaining two.
6. Redaction step in the distribution build (finding 4).

**Until 1 and 2 are done, the pack is fit for internal use and not for sale** —
and the reason is exactly the standard it sets for itself.
