# Which non-SAIRN skills are worth rebuilding as SAIRN originals

**2026-08-30. Reconciled from two independent passes** — CC's and Cody's — run
against the same disk inventory without seeing each other's answer. This is the
settled list. Neither original is authoritative on its own, and this file exists
so whoever writes rebuild specs next builds from **one** list.

**Nothing built. Nothing deleted.** Classification only.

## The inventory this is drawn from

51 skills in `~/.claude/skills/` (was 52 — `security-auditor` was removed
2026-08-30 after its unique content was lifted into `owasp-security`; see
`2026-08-30-skill-precedence.md` and commit `3dbd9a4`). 23 are SAIRN-prefixed
and out of scope here. **28 general-purpose skills** are the candidate pool.

## The test applied

A sellable skill needs a moat, and for this platform the only available moat is
**production incident history**. Anyone can restate OWASP or WCAG from public
sources. Nobody else has SAIRN's thirteen-app scar tissue.

So the question for each skill is not "is this useful" — most are — but: **would
SAIRN's version be better than the generic one, for a reason a buyer could
check?**

---

## The two passes agreed more than they disagreed

**CC's rebuild list (6):** `differential-review`, `ponytail`,
`self-improving-agent`, `skill-vetter`, `api-tester`, `perf-profiler`.

**Cody's list (9):** those same six, **plus** `access-control-rbac`,
`skill-creator`, `token-budget-advisor`.

**CC's list is a strict subset.** There is no skill either pass wanted to
*exclude* that the other wanted to include — the disagreement is entirely about
three additions, which is a much easier disagreement to settle than a conflict
would have been.

### Agreed — 6, no dispute

| Skill | The moat |
|---|---|
| `differential-review` | Its coverage-honesty rule ("state coverage limits and confidence") **is** Guardian's disclosure standard. SAIRN would ship the version that refuses to imply completeness. Nearest neighbours are `sairn-precommit-gate` and `sairn-adversarial-reviewer`, not `owasp-security` — it is a process skill, not a vulnerability catalogue |
| `self-improving-agent` | Harvesting learnings into durable knowledge is what this platform does relentlessly — handoffs, lesson docs, the four-lesson consolidation of 2026-08-30 |
| `api-tester` | Refuses to guess status codes or invent SLAs. That is SAIRN's no-fabrication rule, already written |
| `perf-profiler` | Reproducible baseline, refuses to invent timing numbers. Same discipline, server-side |
| `skill-vetter` | Supply-chain gate on third-party skills. SAIRN runs its own marketplace (`sairn-skills`), so this is operationally real here |
| `ponytail` / `ponytail-review` | YAGNI and anti-over-engineering are **already** SAIRN's stated guardrails in `CLAUDE.md` |

### Disputed — 3, and here is the call on each

**`access-control-rbac` — INCLUDE. Cody only, and it is the strongest single
case on either list.**

SAIRN has shipped per-employee RBAC across thirteen apps *and has the failures
written down*:

- the 2026-08-03 cross-app role collision — a client-supplied
  `body.app_id === 'sairnbiz'` trusted with zero verification
- `verifySessionToken` called without its `expectedApp` third argument **twice
  more in the same session** after the fix, because `'owner'` is a valid role in
  two apps' vocabularies
- the last-admin lockout, and `bootstrap` deliberately **not** auto-healing it
- RF-PINNACLE-2026 found live with zero active owners and no API route back
- the full `set_active` deactivation lifecycle across five apps, including
  StoneDesk being the only two-provisioning-role app

**And there is a confirmed gap to fill:** CC's own supersession check recorded
that **RBAC is "absent from both originally"** — neither `security-auditor` nor
`owasp-security` covers it by name. So this is not duplicating a stronger
neighbour; the ground is empty.

**`skill-creator` — INCLUDE. Cody only.**

SAIRN has 23 skills built from real production failures, and — unusually — the
correction history is *visible inside the files*: `sairn-guardian-v2` documents
drift in its own app map four times over, `CLAUDE.md` corrects its own handoff
convention. A skill about authoring skills, written by an author whose skills
record their own errors, is differentiated from a generic how-to.

**`token-budget-advisor` — INCLUDE, but lowest priority of the nine.**

Real agent-ops knowledge this platform accumulates daily, and genuinely
under-served elsewhere. But SAIRN's experience here is *tacit* — it is not
written down as incidents the way RBAC is, so the moat has to be created before
it can be sold. Build it last, or after a session deliberately logs the
evidence.

**`ponytail` — the split was softer than it looked.** Both passes want it. The
only reservation was that the existing skill carries someone else's voice and
branding, which is an argument for rebuilding it as a SAIRN original rather than
against including it. **No real disagreement.**

---

## Settled list — 9, in build order

1. **`access-control-rbac`** — strongest moat, confirmed gap, most reusable
2. `differential-review`
3. `self-improving-agent`
4. `skill-creator`
5. `api-tester`
6. `perf-profiler`
7. `ponytail` (+ `ponytail-review`)
8. `skill-vetter`
9. `token-budget-advisor` — build last; moat needs documenting first

## Not worth rebuilding — 19

**Restates a public standard, no moat:** `owasp-security`, `accessibility`,
`performance`, `core-web-vitals`, `domain-authentication`,
`transactional-email`, `email-diagnostics`

**Vendor or product-locked:** `claude-api` (Anthropic's own reference),
`varlock`, `playwright-devops` (424 bytes, two links)

**Generic tooling, no SAIRN angle:** `domain-check`, `dep-auditor`,
`refactor-advisor`, `graphify`

**Design taste — already covered by `sairn-client-facing-design`:**
`frontend-design`, `design-taste-frontend`, `ui-ux-pro-max`

**Stub:** `grill-me` (154 bytes, `disable-model-invocation: true`)

**The one borderline call, recorded as borderline:** the three email skills are
72 KB combined and genuinely deep. Deliverability is still a commodity domain,
and SAIRN's only real experience is the `RESEND_FROM_ADDRESS` typo — a config
lesson, not an email moat. Leave them out **unless email becomes a product
line**, in which case revisit rather than assume this call still holds.

---

## A structural difference between the two passes, worth keeping

CC's six are **all process/meta skills** — how to review, how to improve, how to
admit a dependency, how to test, how to profile, how to stay minimal. That is a
coherent product on its own: *SAIRN's engineering discipline, packaged.*

Cody's additions include the only **domain-knowledge** candidate on either list,
`access-control-rbac`. That is a different kind of moat — not "how we work" but
"what we know because we broke it".

Both are valid and they are not competing. If the package ever needs a shape,
the honest one is: **a discipline suite, with RBAC as the first domain title.**
