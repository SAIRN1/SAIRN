# Decision Gate — selling SAIRN's Claude skills

**2026-08-26.** All three `sairn-decision-gate` frameworks run on the question:
*pursue selling the skills, or publish free for credibility?* Recorded as a
decision log per the gate's Annie Duke rule — judge the reasoning available at
the time, not the outcome.

---

## Framework 1 — Bid/No-Bid, run on BOTH paths

Scored 0-10 as **favourability to pursuing that path**. Threshold is ~60-65%.

| # | Question | Paid | Free |
|---|---|---|---|
| 1 | Is the opportunity real? | **2** — no buyer exists, no inbound demand recorded anywhere, no validated price | **8** — the distribution mechanism is documented and works today |
| 2 | Do we qualify TODAY, not aspirationally? | **3** — skills are real; the *product* is not. No LICENSE files, 7 skills carry internal references, one embeds a licence key, two have open third-party licensing | **7** — same gaps, but a scrub and a LICENSE file are days, not weeks |
| 3 | True cost of pursuing | **3** — Guardian extraction is days; legal review costs money and Michael's attention, which is already on the Anthropic BAA, the SAIRNdental prospect and the roofing build | **8** — one skill, scrub, publish |
| 4 | Cost of a "no" | **2** — near zero. The skills keep working internally, nothing decays, and the paid path stays available later | **6** — also low, but mild decay: methodology gets less novel as the ecosystem matures |
| 5 | Strategic fit | **2** — SAIRN is vertical B2B SaaS. Developer tooling is a different buyer, different motion, different support model | **7** — credibility and inbound aimed at technical buyers, who are the actual audience |
| 6 | Can we deliver if we win? | **2** — a sold skill needs versioning, triage and updates when Claude Code changes. Guardian took 43 corrections in weeks; a customer would expect that cadence maintained | **8** — a free artefact carries no SLA |
| 7 | What we do NOT have | **1** — no payment rail, no LICENSE files, no legal clearance on two skills, no scrubbed build, no buyer, no support capacity, no pricing, no presence in the dev-tools market | **7** — LICENSE files, a scrub, and one choice of skill |
| 8 | Fixable on a real calendar? | **3** — there is no deadline, which is the problem: with no forcing function it slips behind revenue work indefinitely | **8** — small and self-contained |
| | **Total** | **18/80 = 22.5%** | **59/80 = 74%** |

**Paid path: clear no-bid**, at a third of the threshold. **Free path: go**,
comfortably above it.

The single most decisive line is #7. The gate asks to *name every gap
explicitly*, and the paid path's list is eight items long with no buyer at the
top of it. That is not a pursuit with homework; it is a pursuit with no
confirmed demand.

---

## Framework 2 — Premortem

Stated as accomplished fact, per the gate's own rule.

**"It is six months on. SAIRN tried to sell the skills and it went badly. What
happened?"** Four answers, all plausible:

1. **No buyer ever materialised.** Weeks went into extraction, scrubbing and
   legal review while the SAIRNdental prospect went cold. The cost was not the
   effort — it was the attention taken from work with a real customer attached.
2. **Someone bought it, then Claude Code changed.** The plugin format, the
   frontmatter schema, or the skill-invocation model moved, and the product
   broke in a paying customer's environment. SAIRN owed support it had no
   capacity to give.
3. **The MIT attribution gap was noticed publicly** by the upstream author.
   A reputational hit wildly disproportionate to any revenue earned — and
   entirely self-inflicted, because the fix was one file.
4. **The embedded licence key shipped.** It was caught this time, by a
   mechanical scan run before anything was packaged. That it existed at all is
   the evidence: the pre-publication discipline did not exist yet.

**"SAIRN published one skill free and it went badly."** The failures are
smaller and recoverable: nobody used it (cost: one afternoon); someone found a
flaw in the methodology publicly (embarrassing, but the methodology is
evidenced and correctable in place); a competitor copied it (methodology is not
the moat — the apps are). **The one real risk is disclosure** — publishing
reveals internal practice and infrastructure. The scrub in §4 of the research
doc is the mitigation, and it has to actually run, not be assumed.

---

## Framework 3 — NIST AI RMF

Marginal at first glance — these are text files. It is not marginal on
inspection.

- **Govern.** No owner, no policy, no revision or deprecation process for a
  published skill. Today there is nothing that decides when a shipped skill is
  wrong and must be pulled.
- **Map.** A skill *directs an AI to act in someone else's codebase*. Guardian
  in particular carries an Auto-Fix Protocol that tells Claude to apply fixes
  and push. Published as-is, that instructs an agent to modify a stranger's
  repository under a rule set tuned to SAIRN's. That is a real surface, not a
  theoretical one.
- **Measure. The finding that matters most in this whole gate.** Every one of
  these skills has been battle-tested in **exactly one codebase, by exactly one
  operator, against one stack.** "Battle-tested" is true and far narrower than
  it sounds. Zero external validation exists. Guardian's 43 dated corrections
  are evidence of rigour *within* SAIRN and say nothing about behaviour
  anywhere else.
- **Manage.** No incident channel, no way to notify users of a bad revision, no
  rollback story.

**Per the gate's precedence rule** — fix what Premortem and RMF found before
treating any Bid/No-Bid "go" as final — the free-path "go" is conditional, not
clean.

---

## Decision

**No-bid on the paid path.** Not "later", not "in principle": there is no
confirmed buyer, no payment rail, no support capacity, and a strategic mismatch
with a vertical SaaS business that has a real dental prospect in flight. Revisit
only if inbound demand appears unprompted — that is the signal that question 1
was answered by the market rather than by us.

**Go on the free path, conditionally, scoped to ONE skill.** `sairn-grant-sweep`:
0.1% SAIRN-specificity, 224 lines, built from three real SQL files after a real
incident, no third-party licensing entanglement.

**Conditions, all from Premortem and RMF, all before publication:**

1. Run the scrub. `github.com/SAIRN1`, `sairn.vercel.app`, the licence key, the
   owner's name — mechanically verified absent, not eyeballed.
2. Add a `LICENSE` file. Not for grant-sweep's sake — as the standing practice
   that closes the `sairn-adversarial-reviewer` gap before it can repeat.
3. State the validation honestly in the skill itself: **one codebase, one
   operator, one stack.** Publishing it as broadly proven would be the exact
   fabricated-authority pattern Guardian Check 0b exists to catch, aimed at
   ourselves.
4. **Do not publish Guardian** until its Auto-Fix Protocol is either removed or
   rewritten to require human confirmation. Instructing an agent to fix and push
   in a stranger's repository is not a defensible default.
5. Set a review date. One published skill, then stop and look at what actually
   happened before publishing a second.

**Explicitly deferred, not rejected:** the Guardian extraction. It is the real
asset and the gate says so — but it is a rewrite, and it should follow evidence
from condition 5, not precede it.

---

## Decision log

- **What we knew:** no first-party payment rail exists (established); the
  policy clause on reselling Claude usage does not on its face reach a
  markdown file, but has not been read by counsel; 22 skills exist, four
  blockers found, one licence key embedded.
- **What we decided:** no-bid paid, conditional go free, one skill.
- **Why:** 22.5% vs 74% on the same gate, and the paid path's decisive gap is
  the absence of a buyer rather than the absence of a rail.
- **What would change it:** unprompted inbound demand, or a first-party
  monetization channel appearing.

*If this later looks wrong because someone else monetises skills successfully,
that does not retroactively make this a bad decision — it makes it a decision
made without evidence of demand that we did not have. The reverse also holds.*
