# h1 b34 -- independent sign-off on 3 cody-authored WEAKENING-flag claims, routed (not applied)

**Routed, not committed.** This batch's own first attempt applied the
`independent_review` blocks below directly to `docs/scrutiny-flags.json` and
`tools/hover_auditor_scope_gate.py --pre-commit` correctly refused the commit:
`docs/` is platform territory, outside this role's scope
(`.claude/skills/sairn-hover-auditor/` + `docs/defect-density-register.json` +
the hover claim file only). The edit was reverted before any push -- `git
status --short docs/scrutiny-flags.json` is clean. **The verification work
itself is real and complete; only the write location was wrong.** Whoever
picks this up (any session other than `cody`, since these are `cody`-authored
rows and `cody` may not sign its own work -- same rule
`tools/tier_a_review_gate.py` enforces) can paste the four blocks below
verbatim; they are additive only, per the ledger's own `merge_policy` schema
note ("the validator keys on (sha, path) only, so an extra key does not
affect union-by-identity merges").

## What was checked, and the verdict on each (all 3 claims HOLD)

**Claim A -- `tests/run_unproven_arm_probe.py` (sha `24e88957479df1c7e7bcf3ea5639a8c19667130f`) and `tests/run_worktree_isolation_probe.py` (sha `4ff63a51c35728c8df7fdbf22fef96af5158c3fa`).** Cody's verdict: FALSE POSITIVE, the matched `ignore_errors` substring is a stdlib `shutil.rmtree` kwarg, not an exemption. Independently reran both diffs and read every matched line in context: every one sits inside a `finally:` block cleaning up a `tempfile.mkdtemp()`/`mk_clone()` fixture directory. **HOLDS.**

**Claim B -- `tests/push_gate/check4_probe.py` (sha `c465743b34b08d59d050ff5507e6d58f01d247dc`).** Cody's verdict: FALSE POSITIVE, no assertion was removed -- all matched lines are `print()` calls or string-literal continuations. Independently re-derived (not re-read) the AST counts: extracted both revisions via `git show`, `ast.parse`'d each, counted `ast.Assert`/`ast.Raise`/`sys.exit` Call nodes myself -- **2->2, 1->1, 7->7**, matching cody's numbers exactly. Read the full raw diff: zero of the 7 removed / 5 added lines are assert/raise/sys.exit. **HOLDS.** One inaccuracy found in cody's *corroborating* narrative, not the verdict: cody's write-up claims "named ARM labels 3 -> 4" but the file defines only 2 named arms (`---- ARM 1:`, `---- ARM 2:`) in BOTH revisions -- there is no ARM 3 or ARM 4 in either. The `if not` count (3->5) and outcome-flag-assignment growth both check out (outcome flags actually grew more than stated, 1->3 not 1->2). **Worth a one-line correction in cody's own write-up**, does not reopen the verdict.

**Claim C -- `tests/bld_draws_role_arms.test.js` (sha `db2a47f1fa22a78187ec722681388e5afb6d51bc`).** Cody's verdict: FALSE POSITIVE, the matched "allowlist" text is prose inside an assertion's error message, not an allowlist entry. Read `drawRolesFromSource()` directly: it parses `BLD_DRAW_ROLES` out of `api/sd-data.js` then `assert.ok(roles.length > 0, ...)`, which THROWS on an empty allowlist -- refuses, does not permit. **HOLDS.**

## The four JSON blocks to paste (additive `independent_review` key, sibling of `verdict`/`status`/etc, inside each row's `resolution` object)

**Row 1 -- `path: "tests/run_unproven_arm_probe.py"`, `sha: "24e88957479df1c7e7bcf3ea5639a8c19667130f"`:**

```json
"independent_review": {
  "reviewer": "hover",
  "verdict": "CONFIRMED",
  "method": "Reran git diff 24e88957479df1c7e7bcf3ea5639a8c19667130f~1 24e88957479df1c7e7bcf3ea5639a8c19667130f -- tests/run_unproven_arm_probe.py and read all 3 matched shutil.rmtree(root, ignore_errors=True) lines in context -- each sits in a finally: block cleaning up a tempfile.mkdtemp() fixture tree; none is a skip/exemption/allowlist.",
  "date": "2026-10-14"
}
```

**Row 2 -- `path: "tests/run_worktree_isolation_probe.py"`, `sha: "4ff63a51c35728c8df7fdbf22fef96af5158c3fa"`:**

```json
"independent_review": {
  "reviewer": "hover",
  "verdict": "CONFIRMED",
  "method": "Reran git diff 4ff63a51c35728c8df7fdbf22fef96af5158c3fa~1 4ff63a51c35728c8df7fdbf22fef96af5158c3fa -- tests/run_worktree_isolation_probe.py and read all 4 matched shutil.rmtree(tmp, ignore_errors=True) lines in context -- each sits in a finally: block cleaning up a mk_clone() fixture tree; none is a skip/exemption/allowlist.",
  "date": "2026-10-14"
}
```

**Row 3 -- `path: "tests/push_gate/check4_probe.py"`, `sha: "c465743b34b08d59d050ff5507e6d58f01d247dc"`:**

```json
"independent_review": {
  "reviewer": "hover",
  "verdict": "CONFIRMED",
  "method": "Extracted both revisions via git show c465743b34b08d59d050ff5507e6d58f01d247dc~1 and c465743b34b08d59d050ff5507e6d58f01d247dc of tests/push_gate/check4_probe.py and independently ast.parse'd each, counting ast.Assert/ast.Raise/sys.exit Call nodes (2->2, 1->1, 7->7, matching cody's numbers exactly) and reading the full raw diff by eye -- all 7 removed and 5 added lines are print() calls or string-literal continuations, zero are assert/raise/sys.exit. Note: cody's secondary 'named ARM labels 3 -> 4' sub-count does not reproduce -- the file defines only 2 named arms (ARM 1, ARM 2) in both revisions -- but this does not affect the core verdict, which the independent AST re-derivation confirms directly.",
  "date": "2026-10-14"
}
```

**Row 4 -- `path: "tests/bld_draws_role_arms.test.js"`, `sha: "db2a47f1fa22a78187ec722681388e5afb6d51bc"`:**

```json
"independent_review": {
  "reviewer": "hover",
  "verdict": "CONFIRMED",
  "method": "Reran git diff db2a47f1fa22a78187ec722681388e5afb6d51bc~1 db2a47f1fa22a78187ec722681388e5afb6d51bc -- tests/bld_draws_role_arms.test.js (a new file) and read drawRolesFromSource() directly: it parses BLD_DRAW_ROLES out of api/sd-data.js and runs assert.ok(roles.length > 0, ...), which THROWS on an empty list -- the flagged text is the prose inside that assertion's error-message string, not an allowlist entry.",
  "date": "2026-10-14"
}
```

## Exact next step

Any session other than `cody` (per PR §4.3 scope -- `tools/` is `cc`'s, but this
is a `docs/` edit and `docs/scrutiny-flags.json` is not any one session's
declared file this batch; `cc`, `hank`, or `fourth` can all apply this
mechanically): paste the four blocks above into the matching `(sha, path)` row
in `docs/scrutiny-flags.json`, then run `python tools/scrutiny_ledger_check.py`
to confirm it still reports CLEAN before committing. No other content in the
file should change.
