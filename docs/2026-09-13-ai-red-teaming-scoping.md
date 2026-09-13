# AI red-teaming — sizing, engine pick, and the SOUP question

**2026-09-13 (Hank).** Item 8, answered as a report and stopped there
deliberately. Three questions were open — how big is it, which engine, and what
would make a third-party engine trustworthy. All three are answered below with
measured or cited evidence. **Nothing is installed and nothing is built.**

Skill used: **`sairn-decision-gate`** — Bid/No-Bid on the build itself, and a
premortem on the engine choice. The premortem is what produced the
data-egress finding that changed the recommendation.

---

## 1. The reframe that decides everything else

**The target is not the model.** Anthropic red-teams Claude; a scanner that
proves Claude can be talked into writing something rude has tested Anthropic's
work, spent SAIRN's API budget, and told this platform nothing about its own
code.

What is actually SAIRN's, and therefore what a red-team here has to attack:

| Ours | Where it lives |
|---|---|
| the `app_id` allowlist | `api/claude.js` `KNOWN_APP_IDS` — 20 entries |
| the licence gate and its four states | `api/claude.js`, `SAIRN_CLAUDE_AUTH_MODE` |
| the server-tool type whitelist | `ALLOWED_SERVER_TOOL_TYPES = ['web_search_20250305']` |
| the tool-use ceiling | `MAX_TOOL_USES_CEILING = 5` |
| the token clamp | `MAX_TOKENS_CEILING = 4096`, clamp-not-refuse |
| the rate limiter | `api/_lib/ai-rate-limit.js` |
| **102 system prompts** | the 17 app HTML files |
| **the indirect-injection paths** | OCR'd documents, uploaded images, customer-written text |
| **per-app refusals stated as requirements** | e.g. SAIRNfreedom must REFUSE VA claim-strategy questions |

Every one of those is SAIRN-written, none of them is covered by any
off-the-shelf probe corpus, and the last three are where a real incident would
come from. That asymmetry is the single most important input to the engine
choice, and it is why the recommendation below is a split one.

---

## 2. Sizes — measured, not estimated

Server side, counted over `api/**.js` excluding `node_modules`:

| | Count |
|---|---|
| files touching Anthropic (incl. tests) | 6 |
| non-test files | 5 |
| non-test files that actually POST to `api.anthropic.com` | **3** (`claude.js`, `legal-citator.js`, `sd-agent.js`) |
| non-test files handling `tool_use` | 2 (`claude.js`, `sd-agent.js`) |
| non-test lines across those 5 | 1,827 |

Client side, counted over the 17 root `*.html` files that reference the proxy:

| | Count |
|---|---|
| apps with an AI surface | **17** |
| `system:` prompt sites | **102 kept / 103 raw** — one HTML comment removed |
| `callClaude(` occurrences | 51 — **this includes each app's own definition**, so real call sites are ~34 |
| apps sending image content blocks | 11 |
| apps referencing tool use (`toolDefs` / `tool_use`) | 12 |

Largest single surface by a wide margin: `stonedesk.html`, 37 system prompts and
10 `callClaude(` occurrences.

**20 allowlisted `app_id`s against 17 apps with an AI surface — and the three
extras are not a measurement error.** `sairnfuneral`, `sairnhr` and `sairnacc`
are in `KNOWN_APP_IDS`, and no `sairnfuneral.html` / `sairnhr.html` /
`sairnacc.html` exists in this repo; the only copies are under `archive/`. So
the allowlist carries three identities for apps that are not live. In observe
mode this changes nothing — any allowlisted id already works without a licence —
but it is a stale allowlist entry of exactly the kind that made the list wrong
in the other direction three times, and it should be confirmed or removed by
whoever owns that list. **Not changed here; this is a report.**

**Two numbers are reported where the filter changed one, rather than one clean
figure** — per disciplines §2. The comment filter removed exactly one site
(`<!-- Safety 5-tab system: Training … -->` in `stonedesk.html`); if a future
run removes twenty, that is a signal, and a single number would hide it.

**THE FIXTURE LOCK FIRED AGAIN, AND IT WAS RIGHT AGAIN — fifth time.** The
criteria were locked against six synthetic cases before the real files were
read. The first comment filter asked only *"does `<!--` appear before the
match"*, which drops a genuine prompt sitting after a comment that has already
CLOSED on the same line. Fixture 4 failed, the script refused to measure real
files, and the criterion was fixed to *"the nearest `<!--` before the match has
no `-->` between it and the match"*. Had that shipped, the 102 would have been
quietly low by however many minified lines carry a closed comment — and I would
have had no way to know, because the real data would have ratified it.

**What these counts are NOT.** `system:` is a textual match on a property name;
it counts *sites*, not *distinct prompt strings*, and several sites pass the
same `sys` variable. Deduplicating to distinct prompt text is a real piece of
work and was not done — the corpus a red-team actually needs is the distinct
set, and it is **≤ 102**.

---

## 3. The live state that sets the priority — verified, not read

**Live-verified 2026-09-13T22:01Z** against `https://sairn.vercel.app/api/claude`
with one request, no `Authorization` header, `max_tokens: 1`, via
`tools/sairn_http.py`:

    status: 200
    {"content":[{"type":"text","text":"x"}], "model":"claude-sonnet-4-6", …}

**`SAIRN_CLAUDE_AUTH_MODE` is still `observe` in production.** An
unauthenticated caller — anyone on the internet, with no licence key — gets a
real completion billed to SAIRN's Anthropic key. That is the documented,
deliberate rollout state (`docs/2026-09-05-claude-proxy-auth-rollout.md`,
observe → measure → enforce), not a regression. It is recorded here because it
changes the red-team plan in two concrete ways:

1. **Every probe in section 4 is reachable by an unauthenticated stranger
   today.** The severity of anything found is one tier higher than it would be
   behind the gate.
2. **A red-team run does not need a licence key**, which removes the worst of
   the SOUP concern in section 5 — there is no customer credential to hand an
   external tool while the platform is in observe mode. That protection
   disappears the day enforce is switched on, and the SOUP entry has to be
   re-read at that moment, exactly like the `stripe` entry's
   `STRIPE_SECRET_KEY` note.

**Out of scope for item 8, recorded because it was observed and should not be
lost:** the proxy answers on `claude-sonnet-4-6`. Whether that is the intended
pin is a separate question and is not being changed here.

---

## 4. Engine pick

Assessed on the axis that actually differs between them for this platform:
**can it point at our own HTTP endpoint, and where does our data go.**

### garak (NVIDIA) — **recommended for the generic half**

- **Apache-2.0.** 20+ probe families: prompt injection, data leakage, jailbreaks,
  encoding attacks, XSS, toxicity, package hallucination.
- **`rest.RestGenerator` fits this proxy exactly.** It takes a custom
  `req_template_json_object`, custom `headers`, and a `response_json_field` that
  accepts a JSONPath. SAIRN's envelope maps onto it with no adapter code:

      "req_template_json_object": {
        "app_id": "stonedesk", "is_demo": true, "max_tokens": 1000,
        "system": "$SYSTEM", "messages": [{"role":"user","content":"$INPUT"}]
      },
      "response_json": true,
      "response_json_field": "$.content[0].text"

- **It has no hosted service in the loop.** The corpus is local. That is the
  deciding property, not the probe count.
- **Cost ceiling, with the arithmetic shown rather than an estimate:**
  `run.generations` defaults to **5**, and `soft_probe_prompt_cap` defaults to
  **256** prompts for probes that auto-scale. So **one auto-scaling probe module
  is bounded at 256 × 5 = 1,280 completions**, and a full `probes.all` run is
  that multiplied by the number of active probe families. **This is a ceiling
  per probe, not a prediction of a real run** — the actual figure has to come
  from a dry run with a stub target, which is the first build step below.

### promptfoo — better mapped, and the reason it is not recommended

- **MIT.** Its red-team mode is the best OWASP mapping available: an
  `owasp:llm` plugin collection against the **2025** list, with per-item
  selectors (`owasp:llm:01`), and an HTTP provider at least as flexible as
  garak's.
- **And by default it sends our material to `api.promptfoo.app`.** Its own
  data-handling documentation lists what goes: the application purpose, plugin
  configuration, **the prompt sent to the target, the target's response**, and
  red-team configuration details including **"request examples, target URLs, and
  auth headers."**
- `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=true` exists. Its own issue
  tracker records that the flag **was not respected by `SimulatedUser`**, which
  instantiated the remote provider regardless (issue #5808, opened 2025-10-03,
  now closed; #4618 and #3552 are the same complaint). The docs also state
  plainly that the flag "is not a network isolation guarantee and does not
  disable telemetry, account/license checks, sharing, or Cloud sync."
- The documented way to minimise egress is to **set your own `OPENAI_API_KEY`**
  — i.e. take on a second model vendor to red-team the first one.

**The premortem is what settled this.** *"It is six months from now and SAIRN's
system prompts and a customer licence key turned up in a third party's logs.
What happened?"* — the answer is a one-line default in a dev-time tool that a
documented env flag was believed to have switched off. A platform whose SOUP
register's founding rule is *"'it is popular' is not a reason"* cannot adopt
that as its security tooling. This is not a claim promptfoo is malicious; it is
a claim the default is wrong for this platform and the off-switch has a
published history of not fully working.

### PyRIT (Microsoft), Giskard, deepeval — **not assessed**

Named so the absence is visible. No claim is made about them either way. If the
recommendation below is rejected, PyRIT is the next one to read.

### The half no engine covers, and it is the important half

Nine of the ten items in section 1's table are SAIRN-specific and appear in no
public probe corpus. Those belong in **a SAIRN-owned probe set under `tools/`**,
in the shape this repo already uses 109 times — deterministic, fail-closed, with
a negative control that proves each arm can go red. Concretely:

1. an `app_id` outside `KNOWN_APP_IDS` is refused (and every listed one works —
   the allowlist has silently 400'd live apps **three times**: 2026-07-26 nine
   apps, SAIRNsenior, and the two caught at build time since);
2. a server tool type outside `ALLOWED_SERVER_TOOL_TYPES` is refused;
3. `max_uses` above `MAX_TOOL_USES_CEILING` is capped, not honoured;
4. `max_tokens` of `true`, `[5]`, `"64000"`, `-1`, `NaN` each land on the
   documented value — this exact type-coercion trap has already produced one
   real bug here;
5. the four licence states (`absent`/`invalid`/`inactive`/`valid`) each behave as
   documented in **both** modes, including that a licence-store outage fails
   OPEN and says so;
6. **indirect injection**: text carried in an OCR'd document, an uploaded image,
   or a customer-written complaint cannot redirect an app's system prompt;
7. **stated refusals hold** — SAIRNfreedom refusing VA claim-strategy questions
   is a written requirement, and nothing tests it;
8. system-prompt extraction against all ≤102 prompts.

Items 1–5 are cheap, deterministic, and need **no model call at all** — they are
assertions about the proxy's own branching and can run in CI for free. **Those
are the ones to build first**, and they are also the ones garak will never
write.

---

## 5. The SOUP trust reason

**The register does not currently cover this, and that gap is the finding.**
`docs/SOUP-REGISTER.md` states under *What this register does NOT claim*: it
"does not track the toolchain — Node, Python, `node --check`, the checkers in
`tools/`."

That exclusion was written with `node --check` in mind: a local tool, given a
file, producing a verdict. **A red-team engine is a different animal wearing the
same coat.** It is handed a live production URL, it is pointed at real customer
apps, its entire purpose is to send hostile input to them, and in enforce mode
it would be handed a valid licence key. Calling that "toolchain" and leaving it
unregistered would be the same shape of blind spot as `tesseract.js` — a
component the checker's own definition could not see, running unregistered.

**Recommendation: register it anyway**, in the register's own five-point shape,
and add a short *Toolchain with production reach* section stating the boundary —
a tool that authenticates to production or receives production data gets an
entry; `node --check` still does not.

The entry, drafted:

> **`garak` (NVIDIA) — why it would be trusted.** Apache-2.0, NVIDIA-maintained,
> and the alternative is writing an adversarial prompt corpus by hand — which
> means this platform inventing its own jailbreak research, badly, and grading
> its own homework. It runs against a URL and a JSON template; it is given no
> repository access, no database credential, and no Anthropic key (it reaches
> Claude only through the same public proxy any browser does).
>
> **What a hostile version could do:** exfiltrate whatever it is pointed at —
> the target URL, the request template (which contains SAIRN system prompts),
> every model response it elicits, and, once enforce mode is on, the licence key
> in the `headers` block. It executes with the operator's own privileges on a
> developer machine, so in the worst case it is arbitrary code execution in this
> clone.
>
> **What bounds it:** *pinned version and a hash, or nothing.* An unpinned
> `pip install garak` is bounded by nothing at all, and pip has no SRI. What
> bounds it is (a) an exact pinned version recorded here, (b) running it in a
> throwaway environment rather than the clone, and (c) **while the proxy is in
> observe mode, the fact that no customer credential exists to hand it.** (c)
> expires the day enforce is switched on. Re-read this entry at that moment.
>
> **Why the alternative is worse:** hand-writing the generic corpus is
> reinventing published security research; skipping the generic half entirely
> leaves the well-known attack classes untested.

**Note the honest asymmetry:** the SAIRN-owned probes in section 4 introduce
**no SOUP at all** — they are stdlib Python against our own endpoint. That is
another reason to build them first: the highest-value half of this work has zero
supply-chain cost.

---

## 6. Bid/No-Bid on the build itself

Scored against the gate's eight questions, the honest summary:

- **Is the opportunity real?** Yes — 17 apps, 102 prompts, an unauthenticated
  production endpoint, and zero adversarial tests today.
- **Do we meet the qualifications today?** For the SAIRN-owned half, yes. For
  the garak half, not yet — nothing is installed and the corpus size is unmeasured.
- **True cost?** The SAIRN-owned probe set is **M** (one session) and needs no
  model calls. The garak integration is **M** plus an unmeasured API spend that
  must be bounded by a dry run before a real one.
- **Cost of a no?** For the garak half, low — the generic classes are the ones
  Anthropic already defends. For the SAIRN-owned half, high: nothing else on
  this platform tests the allowlist, the clamp, or the stated refusals.
- **Biggest gap:** no measurement of what a real garak run costs. Do not run
  `probes.all` against production to find out.

**Verdict: build the SAIRN-owned probe set; treat garak as a second, separately
approved step gated on a dry-run cost measurement against a stub target.**

---

## 7. What this report does NOT claim

- **No probe has been run.** Nothing here says the proxy is or is not vulnerable
  to anything — only what is untested and how big the untested surface is.
- **Nothing is installed.** garak's probe count and defaults are cited from its
  documentation, not observed in a run here.
- **PyRIT, Giskard and deepeval were not assessed at all.**
- **The 102 is prompt SITES, not distinct prompts** — see §2.
- **The one live request** measured the auth mode and nothing else. It is a
  snapshot of 2026-09-13T22:01Z; the env var can change without a deploy.

---

## Sources

- [NVIDIA/garak](https://github.com/NVIDIA/garak) — licence, probe families, REST generator
- [Configuring garak](https://reference.garak.ai/en/latest/configurable.html) — `run.generations` default 5, `soft_probe_prompt_cap` default 256
- [garak RestGenerator config](https://github.com/NVIDIA/garak/blob/main/docs/source/configurable.rst) — `req_template_json_object`, `headers`, `response_json_field` JSONPath
- [promptfoo](https://github.com/promptfoo/promptfoo) — MIT, red-team mode
- [promptfoo HTTP provider](https://www.promptfoo.dev/docs/providers/http/)
- [promptfoo OWASP LLM Top 10](https://www.promptfoo.dev/docs/red-team/owasp-llm-top-10/) — `owasp:llm`, 2025 list
- [promptfoo data handling](https://www.promptfoo.dev/docs/red-team/troubleshooting/data-handling/) — what is sent to `api.promptfoo.app`
- [promptfoo issue #5808](https://github.com/promptfoo/promptfoo/issues/5808) — disable flag not respected by `SimulatedUser`
