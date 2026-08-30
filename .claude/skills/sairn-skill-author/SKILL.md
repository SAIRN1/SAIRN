---
name: sairn-skill-author
description: Write and maintain a SAIRN skill so it stays true after the thing it describes changes. Covers what earns a skill at all, how to source a rule from a real incident, and the maintenance conventions that keep a skill from quietly becoming a lie — dated in-place corrections, numbering that never renumbers, retiring rather than deleting, and never trusting a count. Trigger before creating any skill, before editing an existing one, when the same correction is made twice, and whenever a skill turns out to have been wrong. Distinct from sairn-skill-vetter, which gates skills arriving from OUTSIDE; this one is about authoring our own. Every convention here exists because a SAIRN skill went stale and cost real time.
allowed-tools: Read Grep Glob
---

# SAIRN Skill Author

**Installed 2026-08-30.** Rebuilt as a SAIRN original from the settled
list in `docs/2026-08-30-skill-rebuild-classification.md`. Every factual claim
machine-verified against this codebase before install.

The generic version of this skill teaches you to *create* a skill. That is the
easy half and it is not where SAIRN's skills went wrong. **Every failure worth
encoding here was a maintenance failure** — a skill that was correct when
written, described something that changed, and then confidently said the wrong
thing for weeks.

`sairn-guardian-v2` alone carries **eight dated self-corrections** between
2026-07-26 and 2026-08-27. That is not a sign of a bad skill. It is the only
reason it is still usable, and the conventions that made those corrections
possible are what this skill is for.

---

## 1. Does this earn a skill at all?

A skill is justified when a rule is **recurring, non-obvious, and expensive to
rediscover**. Three failure modes to check against, all of which have happened
here:

- **A skill claimed before it existed.** `sairn-app-scaffold`'s own description
  records it: *"a prior session referenced this skill in a handoff before it
  actually existed on disk; this is the first real version, not a
  restoration."* A handoff naming a skill does not make the skill exist. Check
  the disk.
- **A skill named wrongly in the index.** `CLAUDE.md` said `code-scrubber` and
  described it as a generic pass; the real directory is `sairn-code-scrubber`
  and its content is SAIRN-specific. Corrected 2026-08-24. **A name in a
  pointer file is a claim, not a fact** — resolve it against `ls`.
- **A skill that duplicates one already there.** Run the check before writing,
  not after. Three of four "overlapping" skill groups audited on 2026-08-30
  turned out to be correctly-separated tools that a name-and-size scan made
  look like duplicates — so this cuts both ways: verify the overlap is real
  before consolidating, and verify the gap is real before adding.

## 2. Source every rule from an incident, and say which one

The distinguishing feature of a SAIRN skill is that its rules are **findings,
not advice**. `sairn-code-scrubber` states the standard in its own opening:
each item *"is a bug class that has actually shipped in a SAIRN app and was
later found live — not theoretical."*

**A rule you cannot attach to an incident is a rule you are guessing at.** Two
consequences worth holding to:

- **Cite the specific thing.** File, line, date, licence key, error code —
  whatever makes the claim checkable. `sairn-rbac`'s divergence table names all
  five auth files and all three `PROVISIONING_ROLES` values because a reader
  must be able to disprove it.
- **Machine-check the details before committing.** A skill whose selling point
  is real incidents cannot afford a remembered detail. Every factual claim in
  `sairn-rbac` was grepped against the codebase before it shipped, 12 of 12.
  Remembering is how the check-count drift below happened.

## 3. Correct IN PLACE, dated, with the wrong version still visible

This is the convention that does the most work, and it is the least intuitive.

**Do not silently fix a skill.** Mark the correction with its date, state what
the line used to say, and say what was wrong with it. `sairn-guardian-v2` does
this eight times over — *"Corrected 2026-07-26"*, *"Corrected again
2026-08-09"*, *"corrected 2026-08-25"* — and each one keeps the superseded
claim readable.

**Why the wrong version stays:** a reader who has the old claim in their head
needs to see it contradicted, or they will assume the new text is talking about
something else. A silent edit only helps readers who never read the old one.

**The strongest example, and it is worth copying exactly.** Guardian's app map
said `sairn-code-guardian` did not exist. The 2026-08-24 correction said "do
not go looking for it". The 2026-08-28 correction says that was *also* wrong —
1,230 lines of it were on an unmerged branch the whole time — and preserves the
lesson: *"it does not exist" was a claim about three directories, stated as a
claim about the whole repo.* Two corrections deep, both visible, and the second
is more useful than the first.

## 4. Never renumber. Disclose the collision instead.

Guardian has two checks numbered 16, and checks that read *"numbered 27, not
26, since 26 above already exists"*. The numbering is untidy **on purpose**.

Renumbering breaks every external reference — handoffs, commit messages,
`CLAUDE.md`, other skills — all of which cite checks by number. The collision
is disclosed in the text and the numbers stay put. **Tidiness in a numbering
scheme is worth less than the references pointing at it.**

## 5. Retire rather than delete, and say why

Guardian's check 23 is struck through, not removed: *"RETIRED 2026-08-23. Do
not run this check; do not report it as failing."* The stated reason for
keeping it is precise — *"so a future session that finds this number missing
does not 'restore' a check against a mechanism that was never replaced because
it was superseded."*

Same rule applies to whole skills. When `security-auditor` was removed on
2026-08-30, its unique content was lifted into `owasp-security` **first**,
verified present, and the original archived at
`docs/skill-backups/security-auditor/` before deletion. The order is the
control: salvage, confirm, then remove.

**And check the supersession claim itself.** The removal was authorised on
"owasp-security covers everything it does". A topic-by-topic check run before
deleting found **three more** unique topics — XSS by name, CORS, JWT — that the
first read had missed. A supersession claim is a claim like any other.

## 6. Never state a count. Point at the source of truth.

`CLAUDE.md` said Guardian had 26 checks. The loaded global copy said 28. The
committed skill said 30. **Three live numbers at once**, and the file itself
now says: *"Do not trust this number either — re-read the skill's own heading,
`## The N Checks`, which is the only source that moves when a check is added."*

Generalises past counts. **Any derived fact — a count, a file list, a "these
are the four clones" — will drift from its source.** Either point at the
source, or date the claim and expect it to go stale.

## 7. Write the description for the trigger, not for the shelf

The `description` field is what decides whether a skill fires. It carries the
trigger conditions, not a summary. Compare:

- Weak: *"Covers role-based access control."*
- SAIRN: *"Trigger before writing or reviewing ANY auth branch, role check,
  session verification, provisioning flow, or credential-lifecycle action;
  before adding a role to any app's vocabulary; and any time a role name, table
  name, or session token is shared by more than one app."*

Name the *situations*, including the ones where a session would not think to
look. And where two skills are adjacent, **say so in both descriptions** —
`sairn-client-facing-design` names `frontend-design` as its companion and draws
the boundary, which is why that pair never needed adjudicating.

## 8. State the coverage limit, in the skill

A skill that implies completeness it does not have is worse than a shorter one.
Guardian carries a whole section on this — what a Check 0b sweep actually
covered, which panels were excluded and why — and a **Known Scope Limitation**
saying plainly that a clean pass on an auth-gated app means *"the code looks
right assuming the gate opens correctly"*, not that the app works.

`sairn-rbac` inherits it: rule 13's checklist ends at "a clean write is not
evidence", because it is not.

---

## Before committing a skill change

1. Every new rule names the incident it came from.
2. Every factual detail grepped against the codebase, not recalled.
3. Corrections dated and in place; the superseded text still readable.
4. No renumbering. Collisions disclosed.
5. Nothing deleted that was not first salvaged and archived — and the
   supersession claim checked topic by topic, not asserted.
6. No count stated that the reader could instead read from the source.
7. `description` names trigger situations, and adjacent skills name each other.
8. Coverage limits stated in the skill, not left to be discovered.
