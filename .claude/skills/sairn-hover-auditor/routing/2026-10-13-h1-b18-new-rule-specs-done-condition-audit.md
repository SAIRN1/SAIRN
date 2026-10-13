# H1 batch b18 item 4 -- do the 3 new-rule specs each have a checkable done condition?

Written 2026-10-13, batch b18. Re-read all three spec+baseline deliverables
from b16 (items 7-9) end to end, specifically asking: if a build agent
implements this, is there a mechanical, checkable condition for "done" --
not just a description of the gap -- or does it stop at a design judgment
call with nothing to run and compare?

## 1. bld_draws ownership rule -- HAS a checkable done condition

`.claude/skills/sairn-hover-auditor/references/bld-draws-ownership-rule-probe-spec.md`,
section 4's adversarial matrix (rows 1-7, current vs new-rule columns).
Not stated as one "DONE WHEN" sentence, but mechanically checkable once
read as a whole: **row 2 must flip from ALLOW to DENY** (role `pm` denied
on the dedicated `bld_draws` read/write gate), **rows 1, 3, 4, 5 must stay
unchanged** (unauthenticated still denied, `office`/`owner` still allowed,
cross-tenant still denied), and **rows 6-7 are explicitly out of scope**
(no per-job ownership schema exists, so they are not asked to change).
`tools/bld_draws_ownership_rule_probe.py` already extracts the gate and
prints CURRENT vs NEW-RULE side by side -- a future implementer has a
live diff target, not just prose. VERDICT: checkable.

## 2. SAIRNfreedom post-staff gate (5 resources) -- HAS a checkable done
condition, the clearest of the three

`.claude/skills/sairn-hover-auditor/references/sf-post-staff-gate-rule-probe-spec.md`,
section 6 names four concrete steps (add to `SD_SESSION_GATED`, add to
`SD_GATE_APP` in the same edit -- citing the exact prior incident where
skipping this locked out every real caller, confirm the client already
sends `X-SD-Auth` unconditionally, re-run the test) and explicitly names
the test that proves it: `api/sd-data-sf-session-gate.test.js`, which
"asserts the gated set equals the approved set in both directions." This
is the sharpest of the three specs -- a named, already-existing test file
is the done condition, not a new one to invent. VERDICT: checkable, and
the strongest of the three.

## 3. SAIRNfreedom per-resource role matrix (36 resources) -- DOES NOT
have a checkable done condition

`.claude/skills/sairn-hover-auditor/references/sf-role-matrix-adversarial-checklist.md`.
This file is a checklist of OPEN DESIGN DECISIONS, not a spec with a
pass/fail target:

- The "Proposed" columns in the per-resource matrix are stated explicitly
  as "this auditor's own reasoned recommendation only... not as a spec to
  implement as-is" -- there is no authoritative target to diff against,
  only a draft.
- The Monotonicity section is five `- [ ]` checkboxes, and every one is a
  DECISION TO MAKE, not a condition to verify: "confirm the intended
  partial order before writing any test," "decide whether `post.govern`
  and `post.govern.deputy` are equal... pick one and record which," "flag
  the one plausible exception... name this as an open question." No test
  name is given (unlike spec 2's `api/sd-data-sf-session-gate.test.js`);
  the file itself says "control-pair tested" is a future idea, not a
  named file.
- The one item that IS mechanically checkable today --"re-run
  `SD_SESSION_GATED` vs `SF_RESOURCES` agreement... as a precondition" --
  is a precondition check borrowed from elsewhere, not this spec's own
  done condition for the 36-resource matrix itself.

**VERDICT: does NOT have a checkable done condition.** Before this spec
can be implemented and closed the way specs 1 and 2 can, it needs at
least: (a) the partial-order and deputy-equality decisions made and
recorded by whoever owns the product call (not this role), and (b) a
named test file with a stated assertion shape (the way spec 2 names
`api/sd-data-sf-session-gate.test.js`) -- neither exists yet. This is not
a defect in the spec as written (it says plainly it is a checklist, not a
template to implement as-is) -- it is a real, named gap between this one
and its two siblings, worth flagging before anyone tries to mark it
"done" the same way the other two can be.

## Summary

| Spec | Checkable done condition? |
|---|---|
| bld_draws ownership rule | Yes -- adversarial matrix, row 2 flip |
| SAIRNfreedom post-staff gate (5 resources) | Yes -- named test file, clearest of the three |
| SAIRNfreedom role matrix (36 resources) | **No** -- open design decisions, no named test |

Routed to hank (owns all three specs' targets) as a status note, not a
fix -- this role names which spec is implementation-ready and which still
needs a product decision before it can be.
