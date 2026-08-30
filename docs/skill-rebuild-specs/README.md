# The SAIRN skill pack — nine skills, rebuilt from incidents

**Status 2026-08-30: all nine installed.** Nothing here is a draft.

Nine skills, rebuilt as SAIRN originals to replace third-party equivalents that
were doing roughly the right job with none of the specifics. They sit alongside
the 23 platform skills (`sairn-guardian-v2`, `sairn-code-scrubber`,
`sairn-decision-gate` and the rest), which were always original.

---

## The claim, and it is a narrow one

**Every rule in these nine is traceable to a failure that shipped and was found
live.** Not a principle, not a best practice, not a restatement of a public
standard — a thing that broke, with the file, the date and the error code.

That is the entire differentiator, and it is checkable. Pick any rule and ask
what incident produced it. If the answer is "it's generally true", the rule
should not be there.

**How that is enforced, not just asserted:** every factual claim in the three
newest skills was machine-verified against the live codebase before install —
31 checks, 31 passing. Five checks failed during that pass; **four were the
check being wrong and one was a real citation error**, which is recorded rather
than smoothed over because a verifier that produces false failures trains you to
dismiss the real ones.

## Two moat types, and they are not equal in size

**Process discipline — 8 of 9.** How this platform works: how to review a
change, test an endpoint, profile a slowdown, curate what a session learned,
stay minimal, admit an outside dependency, author a skill, work against data
that does not fit. Sellable as *"a team's engineering discipline, packaged"*.

**Domain incident history — 1 of 9.** `sairn-rbac`. Not how we work, but what we
know because we broke it: thirteen apps of per-employee access control, the
cross-app role collision, the last-admin lockout that stranded a real licence,
five apps that ship the same feature and disagree three ways about it.

**The imbalance is the interesting part.** Process skills are easier to write
because the evidence is everywhere. Domain skills are worth more because nobody
else can write them — `sairn-rbac` is the largest file in the pack at 11.4 KB,
and it is the one a competitor cannot reproduce from public sources at any
length. **The growth direction is more domain titles, not more process ones.**

## What replaced what

| SAIRN skill | Replaces | What actually changed |
|---|---|---|
| `sairn-rbac` | `access-control-rbac` (4.5 KB) | 11.4 KB. The generic skill covers roles, permissions and policies in the abstract. This one covers **one backend shared by thirteen apps that do not share a role vocabulary**, which is where every real failure came from |
| `sairn-skill-author` | `skill-creator` (33.7 KB) | 9.2 KB — **deliberately a third the size**. The original teaches you to *create* a skill. Creation was never where ours went wrong; **maintenance** was. Dated in-place corrections, never renumbering, retiring instead of deleting, never stating a count |
| `sairn-context-budget` | `token-budget-advisor` (6.1 KB) | **Renamed, and the rename is the finding.** Not "manage an allowance" but *a truncated read is indistinguishable from a complete one and becomes a confident wrong claim* |
| `sairn-differential-review` | `differential-review` (7.1 KB) | Scoped to a diff's blast radius on **this** platform, and positioned against its real neighbours — `sairn-code-scrubber` (patterns in a file) and `sairn-adversarial-reviewer` (personas on a feature) |
| `sairn-api-tester` | `api-tester` (5.6 KB) | Encodes the specific ways tests here have been **green while the code was broken** |
| `sairn-memory-curator` | `self-improving-agent` (7.2 KB) | Where a fact belongs, and the pruning pass that stops a stale note becoming a lie |
| `sairn-minimalism` | `ponytail` + `ponytail-review` | One skill, both directions, in SAIRN's own voice rather than someone else's branding |
| `sairn-perf-profiler` | `perf-profiler` (3.8 KB) | Server and data layer, where SAIRN slowness actually lives. **Never states a timing it did not measure** |
| `sairn-skill-vetter` | `skill-vetter` (3.5 KB) | A supply-chain gate, plus the honesty checks a skill must pass to carry the SAIRN name |

**Bigger is not the claim.** `sairn-skill-author` is a third the size of what it
replaces. The pack is smaller where the generic version padded and larger only
where an incident needed recording.

## What was deliberately NOT rebuilt

Nineteen of the 28 general skills stay as they are, and the reasoning is in
`docs/2026-08-30-skill-rebuild-classification.md`:

- **Restating a public standard has no moat** — OWASP, WCAG, Core Web Vitals,
  SPF/DKIM/DMARC. Anyone can write those from the source. We would be selling a
  worse copy of a free document.
- **Vendor-locked skills are not ours to sell** — `claude-api` is Anthropic's
  own reference.
- **Design taste is already covered** by `sairn-client-facing-design`, which
  knows the brand system the general ones cannot.

The one borderline call is recorded **as** borderline: the three email skills
are 72 KB and genuinely deep, but deliverability is a commodity domain and
SAIRN's only real experience there is a config typo. Revisit if email becomes a
product line — do not assume the call still holds.

## Provenance

Two sessions classified the 28 general skills independently. CC's list of six
turned out to be a **strict subset** of Cody's nine — no skill either wanted to
exclude that the other wanted in. Reconciled in
`docs/2026-08-30-skill-rebuild-classification.md` so specs were written from one
settled list rather than two competing ones. CC built six; Cody built three.

The lessons that came out of that night are in
`docs/superpowers/specs/2026-08-30-research-method-lessons.md` — four of them,
and they turned out to be **the same mistake four times**: substituting a cheap
adjacent question for the actual one, and getting a confident answer to the
wrong question.

## Before shipping this to anyone outside the team

Run `sairn-skill-vetter` over the pack — it covers the honesty checks a SAIRN
skill must pass to carry the name, and it explicitly names *"before shipping any
SAIRN skill pack to a customer"* as a trigger. A pack whose selling point is
verified incidents has to survive its own gate first.

Then `sairn-decision-gate`, before any claim that this is production, complete
or sellable is made to someone outside the team.
