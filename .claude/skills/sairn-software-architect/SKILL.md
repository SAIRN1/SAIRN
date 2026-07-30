---
name: sairn-software-architect
description: 'The senior architecture discipline for every SAIRN technical decision. Trigger on: new app builds, cross-app integration design, choosing between architectural approaches, scaling questions, "what do you think" on a technical direction, government/compliance-driven technical requirements, and any decision that will be expensive to reverse later. Not a coding-style skill (see sairn-guardian-v2 for that) — this is the layer above it: should we build this at all, how should it fit the rest of the platform, what will break at 10x scale, and what does the person actually need to know to make the call themselves.'
---

# SAIRN Software Architect

Architecture is the decisions that are expensive to reverse. Everything else is just code, and code is cheap to change. This skill is about getting the expensive decisions right the first time, and being honest the moment one of them turns out wrong.

## What SAIRN's architecture actually is (ground truth, not aspiration)

Every app is a single HTML file with inline CSS/JS, stored in a GitHub repo, deployed to Vercel (static) or Railway (StoneDesk's abandoned backend variant — confirmed dead 2026-07-26, don't resurrect it without a real reason). There is no traditional backend database for most apps — state lives in the browser's localStorage, namespaced per app. Cross-app data movement happens through two serverless functions: `/api/claude` (the AI proxy) and `/api/bridge` (cross-app sync). This is a real, deliberate architecture — not a prototype waiting to be "done properly" — and it has genuine tradeoffs that need naming rather than ignoring:

**What this buys:** zero infrastructure cost, instant deploy via a single file push, no server to patch or scale, works offline-first since the browser holds the state, trivially easy to audit (the whole app is one file you can grep).

**What this costs:** no real multi-device sync without the bridge (localStorage is per-browser, per-device), no real concurrent multi-user editing within one app, no transactional guarantees, no query capability beyond what's loaded into memory, and a single file that grows into the megabytes becomes its own operational hazard (see: the GitHub Contents API silently failing above ~1MB, discovered the hard way on stonedesk.html).

An architect's job here isn't to declare this wrong and rebuild it as a "real" backend — it's to know exactly where this model's ceiling is for each app, and say so plainly when a feature request is about to hit it.

## The core question before any build: where's the ceiling on this approach?

For every new feature or app, answer these before writing code:

1. **Does this need real-time multi-user sync?** (StoneDesk's new POS/mobile requirement does — a phone completing a sale needs the office to see it now, not on next page load.) localStorage alone can't do this. The bridge polling pattern is the current answer; know its latency ceiling (interval-based, not push) and say so if the person needs true real-time and doesn't yet realize polling isn't that.
2. **Does this need to survive the browser being closed/cleared?** If yes, localStorage-only is the wrong model for that specific data — it needs to round-trip through the bridge to somewhere durable, not just sit client-side.
3. **Does this need concurrent editing by two people on the same record at the same time?** None of the current apps handle this. If a feature implies it (two office staff both touching the same job), that's a new architectural capability, not a UI tweak — say so.
4. **Will this file's size become an operational problem?** Files over ~1MB already broke the standard GitHub read pattern once. A 2MB HTML file with 116 script blocks is close to the edge of what one person can safely hand-edit without tooling (hence Guardian v2's Check 0 additions). If a build is heading toward that size, the conversation to have is: split into multiple files/panels loaded on demand, or accept the growing operational cost and increase the rigor of the safety checks — but have that conversation, don't just keep appending.

## Decisions that are expensive to reverse — get these right before building

- **Data model shape** (what fields, what's normalized vs duplicated) — changing this later means a migration across every user's localStorage, which is much harder than a server-side migration.
- **The bridge's event/data contract** — every app that depends on `/api/bridge`'s shape breaks if it changes carelessly. Treat it like a versioned API even though it's informal.
- **Color/brand assignment per app** — small thing, but it's been gotten wrong and re-fixed platform-wide once already (blue leaking into non-SAIRNdesign apps). Cheap to avoid, annoying to unwind across a live file.
- **Which codebase is canonical** when more than one exists for the same product (see: the abandoned Fabricor/Railway app). Decide and document this explicitly the moment a second implementation appears — don't let two "real" versions coexist silently.
- **Compliance posture baked in from the start** vs retrofitted. WCAG/accessibility, data-handling language, and subprocessor disclosure are far cheaper to design in from the first line of a public-facing or government-facing app than to bolt on after a proposal has already been scored on it.

## Government/institutional context is now part of the architecture conversation

Since the Cleveland Metroparks RFP entered the picture, "architecture" for SAIRN now includes things that have nothing to do with code: insurance minimums, bonding, subprocessor disclosure (Anthropic, Vercel, Railway, Stripe are all subprocessors the moment client data touches them), data retention/deletion guarantees, and audit rights. An architect who only thinks about the stack and ignores this is giving incomplete advice for this business right now. When a technical decision has a compliance dimension (e.g., "does this feature store guest PII," "does this AI call send anything sensitive through the proxy"), name that dimension explicitly rather than treating it as someone else's problem.

## How to give architectural advice in this project

- **State the tradeoff, not just the recommendation.** "Use localStorage-only for this" is incomplete; "localStorage-only means no cross-device sync, which is fine for a single-PM-on-one-laptop tool but wrong for the phone POS feature" is what's actually useful.
- **Name the ceiling before it's hit, not after.** If a request is heading toward a known limit (file size, sync model, concurrent editing), say so at design time, not during the bug report.
- **Prefer the cheap, reversible option unless there's a specific reason not to.** SAIRN's whole model is built on cheap-to-change single files; don't introduce a database, a new service, or a new framework unless the specific feature genuinely requires it and the tradeoff has been said out loud.
- **When two codebases or two branches both claim to be canonical, resolve it immediately and explicitly** — verify against the source of truth (repo default branch, most recent real commits, actual deploy target), never trust a stale note from a prior session at face value.
- **Distrust your own prior "complete" claims.** Guardian v2's Check 0 exists because "100% complete" claims from earlier sessions have twice turned out to be wrong on independent re-verification (SAIRNbiz's syntax error, SAIRNvet's static panels). An architect re-checks the foundation before building the next floor.

## Tool completeness — what this skill needs to actually function, and current gaps

Being an effective architect here requires being able to see production reality, not just source code. As of 2026-07-26, confirmed via `search_mcp_registry`:

- **Vercel MCP connector** — already installed (`installedServerId` present) but not active in every chat by default. This gives `list_deployments`, `get_deployment`, `get_deployment_events`, `list_projects` — exactly what's needed to confirm which branch is actually deploying, whether a push is actually live, and to stop relying on `vercel.json`/repo-default-branch inference alone. **Should be connected at the start of any session doing deploy verification.**
- **Railway MCP connector** — not installed. Lower priority since Fabricor/Railway is the confirmed-abandoned codebase, but if StoneDesk's backend is ever revived or a new app targets Railway, this becomes relevant. `get-logs`, `get-status`, `create-deployment` are the useful ones.
- **Direct database access** — none currently. Not a gap today since the architecture is localStorage-first, but if any future app needs a real shared backend (the multi-user/real-time ceiling above), this becomes a real requirement to solve for, not optional.
- **bash_tool's network allowlist** does not include `vercel.app`, `railway.app`, or any live SAIRN deployment domain — meaning source-code-level verification (via GitHub) is always possible, but confirming what's actually *live and running* requires either the Vercel/Railway MCP connectors above, or asking the person to check directly. Don't assume source-level verification equals production verification — they answered different questions this session (branch existed on GitHub vs. was actually what Vercel served) and that gap needs to stay visible, not get papered over.

When architecture work requires confirming production state and the Vercel connector isn't active in the current chat, say so and suggest connecting it — don't guess from source alone and present it as equivalent to a live check.

**Third verification path, confirmed real 2026-07-26:** Claude Code, running on the actual local machine, has real network access to `sairn.vercel.app` and can `curl` the live proxy directly — something this chat's sandboxed bash_tool cannot do (its network allowlist excludes the live deployment domain entirely). Confirmed tonight: a code-level fix to `api/claude.js` was verified genuinely live by curling the production endpoint with a real `app_id` and getting a real HTTP 200 response from the model — not inferred from source, actually observed. When a fix needs live confirmation and Claude Code is available, that's the fastest real path, faster than connecting the Vercel MCP connector for a simple reachability check.

---

## The Reference Architecture (added 2026-07-26 — the concrete standard, not just the judgment layer)

Everything above this line is how to think. This section is the actual blueprint every SAIRN app should follow — existing apps get retrofitted toward it opportunistically as they're touched, every new app starts from it on day one. Note: Claude Code's local environment has its own `sairn-app-scaffold` skill with a working `scaffold-template.html` — reconcile that with this section rather than maintaining two competing standards; whichever is more current should update the other.

### 1. File structure and the size ceiling

Single HTML file (CSS + JS inline) remains the default — it's what makes SAIRN's zero-infrastructure model work. But there's a real ceiling, now confirmed twice: the GitHub Contents API silently fails above ~1MB, and a file with 100+ script blocks becomes hard for a human to safely hand-edit even with Guardian's help.

**The rule:** once an app's HTML file exceeds roughly 1MB, two things become mandatory, not optional:
- All reads/writes for that file use `raw.githubusercontent.com`, never the Contents API (Guardian v2 already covers this)
- New panels get organized as clearly-delimited, independently-checkable script blocks (one panel = one block, consistently, so `node --check` and the div-balance/nav-panel checks can isolate a single panel's problem instead of hunting across the whole file)

Splitting into genuinely separate files is the next step up (lazy-loaded panel modules) — not needed yet at StoneDesk's current size, but the point past which it becomes worth the added complexity is when a single file starts taking multiple minutes to safely fetch/verify/push, or when Guardian's per-edit checks start taking long enough to slow real work down.

### 2. The data model convention (every app, no exceptions)

**Before writing any new feature: two mandatory pre-checks (added 2026-07-27, preventive — every collision bug tonight was this exact pattern):**
1. **Grep for the storage key before creating it.** Every real bug tonight (customers, inventory, remakes, safety) was two independent features writing the same `sd_*` key with incompatible shapes, because the second feature never checked whether the key already existed. If a key exists, use its existing shape — never invent a parallel one.
   - **1a. Nuance (added 2026-07-30): a collision is not automatically "one orphan, one canonical."** The default fix-pattern is delete-the-orphan-keep-the-real-one, but StoneDesk's `sd_quote_history`/`sd_slabs` collisions were both sides genuinely live — different features, both actually used, both needing the key's data — and the correct fix was reconciling the two shapes into one, not deleting either side. Deleting on the assumption of "one must be dead" would have destroyed real user data in the case that turned out to be live-live, not live-dead. Check whether both writers are actually reachable and actually written-to in normal use before assuming which side (if either) is safe to remove.
2. **Confirm the target container exists in markup before wiring a render function to it.** Multiple functions tonight had real, correct logic but referenced a `getElementById` target that was never actually built — dead on arrival, invisible until someone specifically traced it. Before writing `functionName(){ document.getElementById('some-id')... }`, grep the HTML for `id="some-id"` first. If it doesn't exist, build it as part of the same commit — don't ship logic with no home.

- Every localStorage key is app-prefixed (`sd_` StoneDesk, `sb_` SAIRNbuild, etc.) — already a rule, still the foundation everything else builds on
- Every panel with any dynamic content has a real backing `render<n>()`/`get<n>()` function — a panel with numbers and no function behind them is not a smaller version of the app, it's a lie about the app (see Guardian v2 Check 0b)
- Every add/edit/delete flow follows the same shape: mutate the in-memory array, `save()` to localStorage, `render()` to update the DOM — never mutate the DOM directly and hope localStorage catches up later

### 3. The Bridge + Proxy pattern, formalized

This is already how cross-app data and AI calls work — the point of writing it down here is to make it the one blessed pattern, not one option among several:
- **Claude calls:** always through `/api/claude`, never direct — this is a hard Guardian block already
- **Cross-app data:** always through `/api/bridge`, treated as a versioned contract even though it's informal — a change to what the bridge sends or expects is a platform-wide architectural decision, not a local edit to one app
- **New integration points** (a new external service, a new cross-app data flow) get designed as a new bridge endpoint or a new bridge payload shape, not a new one-off connection bypassing the bridge

### 4. Mobile / POS / Real-Time pattern — extracted to its own skill

This became important enough, and reusable enough across enough apps (StoneDesk, SAIRNbuild, SAIRNhr, SAIRNacc, SAIRNcare, SAIRNvet, SAIRNlaw, and whatever comes next), that it's now its own skill: **`sairn-mobile-sync`**. Read that directly rather than duplicating it here — this pointer exists so the content has exactly one home instead of two copies drifting apart over time.

### 5. Retrofit priority for existing apps

Apply this reference architecture to apps in the order they're actively being touched, not as a separate cleanup project. StoneDesk is first because it's mid-build right now and because it's the one carrying the government-proposal "production" claim — it needs to actually hold up. Every other B2B app (SAIRNbuild, SAIRNacc, SAIRNhr, SAIRNdesign, SAIRNcare, SAIRNlaw, SAIRNcode, and whatever comes after) inherits the same standard the next time it's opened for real work, not retroactively all at once.
