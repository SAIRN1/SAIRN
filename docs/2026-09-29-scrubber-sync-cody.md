# The skill mirror has diverged in two places, both with the repo ahead

**2026-09-29 (Cody).** `CLAUDE.md` says the repo mirrors the SAIRN skills from
the user store. **Two of the 34 mirrored skills currently differ**, and in both
cases the repo carries content the user store does not — so the store copy, which
is the one a session actually loads, is the stale side.

**Compared after `tr -d '\r'`.** The user store is CRLF and the repo is LF; a
bare `diff` reports content-identical files as changed and has produced four
false alarms in a single session before. Every figure below is from the
normalised comparison.

## The measurement

    34 mirrored skill directories in .claude/skills/
    62 directories in the user store (the other 28 are third-party, not mirrored)
     0 skills present in the repo and absent from the store
     2 skills whose SKILL.md differs after CRLF normalisation

| skill | repo lines | store lines | differing lines | direction |
|---|---|---|---|---|
| `sairn-code-scrubber` | 500 | 430 | 70 | **repo ahead**, 70 repo-only, 0 store-only |
| `sairn-hover-auditor` | — | — | 243 | **repo ahead**, 241 repo-only, 2 store-only |

The other 32 are byte-identical after normalisation.

---

## 1. `sairn-code-scrubber` — one whole section is missing from the store

The repo copy has **27** numbered sections and the store copy has **26**. The
difference is exactly one block, repo lines 431–500:

> `## 27. A cap on a ratio that turns an OVERRUN into COMPLETION`

That section is **cc's**, written 2026-09-27 from SAIRNbuild's WIP schedule,
where `Math.min(1, costToDate / estTotal)` made a job that had spent 130% of its
estimated cost report 100% complete — so `earned` became the whole contract and
over/under billing swung to its most under-billed reading, on the one report a
surety underwriter and a bank read specifically to find profit fade. The cap did
not round an overrun off; it inverted the finding.

**IT IS NOT REWRITTEN BY HAND HERE, and that is deliberate.** Michael's direction
was that this file is not overwritten by hand, and the section is another
session's work with its own detection tool (`tools/overrun_inversion_scan.py`)
and its own three-part criterion. Re-typing another session's analysis into a
second copy is how two divergent versions of one rule get created — which is the
problem this document is about, one level up.

**The sync is a copy, not an edit.** The repo copy is the superset; nothing in
the store copy is missing from the repo. So:

    # from a clone, after confirming the diff is still one-directional:
    diff <(tr -d '\r' < .claude/skills/sairn-code-scrubber/SKILL.md) \
         <(tr -d '\r' < ~/.claude/skills/sairn-code-scrubber/SKILL.md)
    # every line should be `<` and none `>` -- if any `>` appears, the store has
    # content of its own and a straight copy would DESTROY it. Stop and read.
    cp .claude/skills/sairn-code-scrubber/SKILL.md \
       ~/.claude/skills/sairn-code-scrubber/SKILL.md

**Re-run the direction check immediately before the copy, not from this
document.** This file records the state at the time it was written; the store is
outside every clone and can change without a commit, which is the same staleness
this document exists to report.

## 2. `sairn-hover-auditor` — 243 lines, and a build agent must not touch it

The hover auditor's skill is **out of scope for every build agent**, including
for a sync. `docs/2026-09-15-hover-auditor-separation-enforcement.md` records
why, `tools/hover_auditor_scope_gate.py` prevents it and
`tools/hover_separation_audit.py` detects it. A build agent reaching into that
clone to "just fix the mirror" is the same boundary problem the gates exist for,
running the other way.

**So it is reported, not acted on.** The divergence is **241 repo-only lines and
2 store-only lines** — note that it is *not* one-directional, unlike the
scrubber, so a straight copy in either direction would destroy content. The
largest repo-only block is:

> `## Four further standing rules, 2026-09-28 (Michael's direct instruction,
> sourced separately from the build-agent registry)`

and the store-only lines are a two-line paraphrase of the same rules
("Four further anti-predictability rules, against the rotation itself becoming
a pattern a build agent could learn and route around"). **That is two versions of
one instruction, which is worse than a missing one**: whichever copy a session
loads, it will not know the other exists.

**Owner: the hover auditor.** Routed here rather than fixed.

---

## What this is really about

A mirror with no checker is a mirror that diverges silently, and both halves of
that sentence have already happened here. The mirror is not in
`docs/TOOLING-INVENTORY.md` as a checked artefact, nothing compares the two
trees on a cadence, and the only reason this was found is that a task named one
of the two files.

**The remedy, named rather than done:** a report-only checker that walks
`.claude/skills/*/SKILL.md`, normalises line endings, compares against the user
store, and reports per skill **the direction** of the divergence — repo-ahead,
store-ahead, or both — because the direction is what decides whether a copy is
safe and a checker that only reports "differs" would have said the same thing
about both rows above while one is a safe copy and the other is a data loss. It
must fail COULD NOT RUN when the user store is absent rather than reporting every
skill as diverged, and it cannot be a push gate: the store is outside the repo,
so its state is not a property of any commit.

---

## LANDED 2026-09-29 — the scrubber half only

**`sairn-code-scrubber` is synced.** The direction check was re-run immediately
before the copy, exactly as this document said it must be: **70 repo-only lines,
0 store-only**, so the copy could not destroy anything. After:

    repo-only 0, store-only 0
    sections repo/store: 27 / 27

Section 27 — cc's ratio cap that turned a 130% cost overrun into 100% complete
and inverted over/under billing on the report a surety underwriter reads — is now
in the copy a session actually loads. **It was not retyped**: the repo file was
copied whole, which is the only form of this fix that cannot create a second
divergent version of one rule.

The previous store copy is kept as a backup in this session's scratchpad. The
repo file is unchanged — it was already the superset.

**A full re-check of all 34 mirrored skills after the copy leaves exactly one
divergence:**

    sairn-hover-auditor: repo-only 241, store-only 2

**Still routed, still not touched.** It is out of scope for every build agent,
its divergence is NOT one-directional, and a copy either way would destroy
content. Owner: the hover auditor.

**This is a config file outside every clone, so nothing here is in the diff.**
Re-run the direction check rather than trusting this section:

    diff <(tr -d '\r' < .claude/skills/sairn-code-scrubber/SKILL.md) \
         <(tr -d '\r' < ~/.claude/skills/sairn-code-scrubber/SKILL.md)
