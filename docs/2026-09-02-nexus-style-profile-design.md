# NEXUS per-user style profile — design, scoped before building

**Date:** 2026-09-02 · **Session:** CC · **Status:** scope. Read this before the code.

## What exists today, read from the files rather than assumed

| Thing | Keyed on | Set by | Shape |
|---|---|---|---|
| `buildSDSystemPrompt()` (`stonedesk.html:25440`) | — | — | string concatenation: base + shop profile + shop memories + one style word |
| `_sdBizProfile` → `business_profiles` | licence + app | the shop owner, in a form | the **shop**: name, EIN, city, headcount, revenue |
| `_sdMemories` → `ai_memories` | licence + app | the AI, from past sessions | the **shop**'s facts |
| `sd_employee_profiles` | `(license_hash, employee_id)` | **a manager, deliberately** | two enums + notes |
| `sd_shared_knowledge` | licence | inferred | **company-wide** topic frequency |

`sd_employee_profiles`' own header states the split it was built on: shared
knowledge answers *"what does this shop talk about"*, that table answers *"how
should the AI talk to THIS person"* — and it answers it with a value **a manager
typed in**.

## The actual gap

Nothing **observes** anything about an individual. The one per-person signal in
the prompt is `p.preferences.ai_style`, a single enum from
`{direct, detailed, conversational}`, **set by hand, on the shop record, not per
user**. So today two people at the same shop get byte-identical prompts, and the
"personalization" is one word somebody picked once.

There is no structured, persistent profile object. That is the thing to build.

## Decision 1 — where it lives: ONE shared table, and the honest limit on "shared"

One table, `sairn_style_profiles`, with an `app_id` column, used by every app —
not a per-app table each app reimplements. A writing style belongs to the
person, not to the product they happen to be typing into, and a per-app table
guarantees eleven divergent copies of the same analyser.

**The honest limit, stated because it constrains what can be claimed.** The
session token carries `(license_hash, employee_id, app)` and no email. The only
cross-app identity anchor on the platform is `employees.customer_email`, which
is not in the token and not reachable from a data endpoint without a join that
does not exist today. So the profile is keyed **`(license_hash, employee_id)`**,
and because `license_hash` is per-app-licence, **the same human working in two
apps gets two profiles.** The table is *shaped* for cross-app aggregation —
`app_id` is recorded and is deliberately NOT part of the key — but aggregation
across apps is not delivered here and must not be described as if it were. When
a real identity join exists, the merge is a `union` over rows, not a migration.

## Decision 2 — what is captured

Only things derivable from the user's own text, deterministically, with no model
call. Every field is a number or a small list, so a profile can be merged
incrementally without re-reading history.

| Signal | Field | Derived from |
|---|---|---|
| Response length wanted | `avg_words`, `median_words` | the user's own message lengths |
| Sentence complexity | `avg_sentence_words` | words ÷ sentence-enders |
| Register | `question_ratio`, `imperative_ratio` | leading verbs, `?` |
| Formatting | `uses_bullets`, `uses_numbered`, `uses_markdown` | line-start `-`/`*`, `1.`, `**`/`` ` `` |
| Emphasis habit | `uses_caps_emphasis` | ALL-CAPS words of 3+ chars |
| Politeness | `hedge_ratio`, `courtesy_ratio` | "maybe/perhaps/I think", "please/thanks" |
| Vocabulary | `top_terms` (≤12) | content words the user actually uses, stopworded |
| Jargon density | `abbrev_ratio` | short all-caps/mixed tokens (`THH`, `LF`, `COI`) |
| Confidence | `samples`, `total_words` | how much evidence there is |

**Merged incrementally, never recomputed from stored history.** The profile
holds running counts, so a message is analysed once and folded in. This is also
why nothing stores the user's raw messages: the profile is statistics, not a
transcript. That is a deliberate privacy property and is asserted in the tests.

## Decision 3 — how it is retrieved and applied

- **Write:** the client analyses the message locally and posts the *deltas*, not
  the text. The endpoint merges server-side.
- **Read:** one row on session start, cached in the page.
- **Apply:** `renderStyleDirectives(profile)` returns a compact block appended by
  `buildSDSystemPrompt()`, replacing the hand-set enum.

**A confidence floor, because this is the failure mode that matters.** Under
`MIN_SAMPLES` (5) the block is **omitted entirely** and the old behaviour stands.
Two terse messages must not convince the model the user wants telegrams forever.
The renderer states the sample count in the prompt so the model can weigh it.

**Directives are instructions, not statistics.** "Target ~40 words" beats
"avg_words: 38.6" — a number invites the model to reason about the number.

## What this is not

- Not a model call. The analyser is deterministic and runs in microseconds.
- Not a transcript store. No raw text is persisted; the tests assert it.
- Not cross-app yet. See Decision 1.
- Not a replacement for `sd_employee_profiles`. That is declared intent set by a
  manager and outranks observation; where both exist the manager's value wins,
  and the renderer says so.
