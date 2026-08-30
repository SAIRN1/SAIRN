# The transplanted feature series, its missing chat host, and the stub block that hides three live features

**What this started as:** a follow-up to the NEXUS handoff finding — the sender
half rendered into `#chatArea`, an empty `display:none` div, so its buttons were
invisible. The question was whether other modules did the same.

**What it turned out to be:** two distinct defects sharing one cause, and the
second is worse than the first. One is dormant code. The other is **three
complete, working, AI-backed features that a customer cannot reach at all.**

---

## 0. Correction first — `is_demo: true` is not a bug, and I was wrong to call it one

I reported `is_demo: true` in the handoff payload and the multi-modal API call
as "a real, live defect on a paying app." **That was wrong, and the instruction
to fix it rested on my error, so no code was changed.**

`is_demo: true` is the platform-wide convention. It appears at roughly **ninety**
call sites in `stonedesk.html` alone, and `api/_lib/ai-rate-limit.js:14` states
plainly that **10 of 11 live SAIRN apps send it**. In `api/claude.js:180` the
flag does one thing: it opts the call **into** the shared daily AI rate limit.

So `is_demo: true` on a paying B2B app is the **safer** setting, not a defect.
`is_demo: false` is the exception, used by SAIRNcash alone and only because it
is "gated upstream by its own real Stripe subscription check"
(`api/claude.js:38`). "Fixing" it would have **exempted StoneDesk from all AI
rate limiting** — the opposite of the intent.

The one genuinely odd instance is narrow and not worth a change: the handoff
payload at `:17897` carries `is_demo:true` inside a **sessionStorage object**
that is never sent to the proxy. It is a meaningless field cargo-culted from the
API body shape. Harmless.

## 1. The root cause — a block of placeholder stubs added to satisfy guards

`stonedesk.html:14490–14508` holds eighteen empty divs, every one
`style="display:none"`:

    cust-form-wrap  fu-pulse-style  live-pulse-style  pin-input
    roam-action-row  sa-result  sairn-blink-style  sairn-intake-actions
    sairn-knowledge-indicator  sairn-lock-overlay  sairn-memory-indicator
    sairn-memory-panel  sairn-tone-bar  sairn-tone-tooltip  sairn-voice-btn
    slow-pulse-style  topbar-shop  upload-zone

They exist so that transplanted modules' `getElementById` guards find
*something*. **Eleven of the eighteen share an id with an element the JavaScript
also creates and appends**, which produces duplicate IDs in the live document:

    fu-pulse-style   live-pulse-style   sairn-blink-style
    sairn-knowledge-indicator   sairn-lock-overlay   sairn-memory-indicator
    sairn-memory-panel   sairn-tone-bar   sairn-tone-tooltip
    sairn-voice-btn   slow-pulse-style

`getElementById` returns the **first** match in document order. The stubs sit in
the body markup; the created elements are appended to the end of `<body>`. **The
stub always wins.** Two consequences, and the second is the damaging one:

1. A module that creates an element and later looks it up by id operates on the
   **hidden stub**, not on the thing it built.
2. A module using the standard install-once idiom —
   `if (document.getElementById('X')) return;` — sees the stub and **refuses to
   install at all.** `injectVoiceButton()` at `:17792` is exactly this:
   `sairn-voice-btn` is a stub, so Feature 7 Voice Input never installs.

## 2. The severe finding — three complete features are unreachable

**Three separate modules inject their only trigger button into
`#sairn-intake-actions`**, which exists nowhere except as a `display:none` stub
at `:14494`:

| Module | Injects | Line |
|---|---|---|
| SAIRN UNIVERSAL DOCUMENT UPLOAD + ANALYSIS | `sairn-doc-trigger` | `:16756` |
| SAIRN FEATURE 9 — SMART COMPARISON MODE | `sairn-compare-trigger` | `:18148` |
| **SAIRN MULTI-MODAL INPUT** (camera → Claude) | `sairn-cam-trigger` | `:20371` |

All three append their button into the hidden stub. **All three buttons are
invisible.**

**Verified there is no other way in**, rather than assumed:

- **Zero** markup `onclick` handlers call `openDocModal`, `openCompare` or
  `openCamera` — the injected button is the *only* caller
  (`btn.onclick = window.openCompare` at `:18159`,
  `btn.onclick = window.openCamera` at `:20382`).
- **Nothing ever un-hides `#sairn-intake-actions`** — no `.style` or
  `.classList` write against it exists anywhere in the file.
- The fallback chain does not save it. `injectCameraButton` tries
  `sairn-intake-actions || roam-action-row`, and because the first resolves to
  the stub, the `sendBtn`-based fallback below it never runs — and `sendBtn` is
  *also* a hidden stub.

**This corrects something I said earlier today.** I reported that Feature 9
Compare was "live independent of its addMsg hook" because it exports
`openCompare` and injects a trigger. The export is real; the trigger is
invisible. It is not reachable.

**Why this matters beyond three features:** the multi-modal camera path is the
one named in `docs/2026-08-30-ar-measure-iphone-gap.md` as the infrastructure a
reference-object measurement fallback would reuse. That recommendation still
holds — the capture code is real and works — but the entry point needs fixing
first, which was not known when that document was written.

## 3. The dormant-hook finding — `addMsg` is never defined

Eight modules wrap `window.addMsg`:

| Line | Module |
|---|---|
| 16842 | AI Follow-Up Questions |
| 17096 | Session Memory |
| 17469 | Feature 5 — Multi-Step Action Plans |
| 17646 | Feature 6 — Simplify + Explain |
| 17932 | Feature 8 — Handoff sender |
| 18450 | Feature 9 — Compare (hook 1) |
| 18976 | Feature 9 — Compare (hook 2) |
| 19643 | Real Personalization AI |

Every one reads `window.addMsg` before assigning, and **all eight installs are
guarded** `if (typeof window.addMsg !== 'function') return;` — checked
individually, not sampled. **No base definition exists anywhere in the file.**
The install sites poll for 10 seconds and give up. Silently: no error, no throw,
nothing in console.

**Scope correction on my own earlier wording.** I said "eight modules are
permanently dormant." The accurate claim is narrower: **the `addMsg` hook in
eight modules is permanently dormant**, and several of those modules have other
halves that do run — five of them patch `window.fetch` unconditionally
(`:17076`, `:17279`, `:18684`, `:18900`, `:19128`), and Session Memory builds a
real indicator and panel. Those halves are live. Only the hook is dead.

Session Memory is where both defects meet: it appends a real
`sairn-memory-indicator` and `sairn-memory-panel` (`:17022`, `:17029`) whose ids
already exist as stubs, so `showMemoryPanel()` at `:17041` toggles the **stub**
and the real panel stays hidden forever.

## 4. Revive or retire

**The root fix is one function, and that is exactly why it should not be done
casually.** Defining a single base `addMsg(role, content)` that renders into
`#ai-chat` would revive all eight hooks at once, because they are already
chained and waiting. **On a live paying app that means eight dormant behaviours
switching on simultaneously.** That is a deliberate product decision, not a
cleanup, and it is not made here.

| Module | Call | Reasoning |
|---|---|---|
| **Multi-Modal camera** | **Revive — first** | Complete working feature, one hidden button between it and the customer. Highest value, smallest fix. |
| **Document Upload + Analysis** | **Revive** | Same shape: complete, working, one invisible trigger. |
| **Feature 9 — Compare** | **Revive the trigger; leave the hooks** | The modal and `runComparison` work. Its two `addMsg` hooks are cosmetic. |
| **Feature 8 — Handoff sender** | **Revive with the receiver** | Data retargeted today (below); the sender still needs pointing at `#ai-chat`. |
| **AI Follow-Up Questions** | Revive, low priority | Genuine chat UX value, but pure addition to a live surface. |
| **Feature 5 — Action Plans** | Revive, low priority | Turning AI answers into checklists suits a shop; unproven here. |
| **Session Memory** | **Fix the id collision** | Half-live already. Renaming the stubs is the whole fix. |
| **Feature 6 — Simplify + Explain** | **Retire** | A consumer-app affordance. StoneDesk's users are trade professionals; "explain this simply" is not a need they have. |
| **Real Personalization AI** | Assess separately | Its live half patches `window.fetch` globally. That deserves its own review, not a revive/retire line. |

**The cheapest high-value change is not in this table:** delete or rename the
eleven colliding stub ids. That single edit un-hides three complete features and
repairs Session Memory, without activating a single dormant hook. It is also the
riskiest to do blind — every stub was added to satisfy some guard, and removing
one may re-expose whatever it was papering over. It needs a per-stub check, not
a bulk delete.

## 5. What was changed in this pass

1. **`CELL_MAP` retargeted** (`stonedesk.html:17867`) from nine non-existent
   consumer files to **five real B2B apps with live `vercel.json` routes** —
   SAIRNbiz, SAIRNbuild, SAIRNdesign, SAIRNscape, SAIRNlaw. Keywords deliberately
   narrowed to multi-word phrases (`mechanics lien`, not `contract`; `interior
   design`, not `home`) because the old table matched everyday stone-shop
   vocabulary. Follows Guardian's June 16 2026 precedent: correct the data, keep
   the mechanism.
2. **`checkIncomingHandoff` ported** into all five destination apps as an
   identical, unedited snippet. Ids resolved from a candidate list because the
   apps disagree on names (`ai-input`/`ainp`/`scp-ainp`/`ai-question`). Two
   improvements over the original: the key is **cleared only on success** (the
   original consumed the context and dropped it if the licence gate had not
   cleared yet), and the banner is built with `textContent`, not `innerHTML`.
3. **XSS sink closed in StoneDesk's own receiver** (`:17860`). It concatenated
   `ctx.situation` straight into `innerHTML`. Fixed in the same pass rather than
   shipping the safe version to five apps and leaving the unsafe original.

Syntax verified after every edit: `stonedesk.html` **126/126** inline script
blocks pass `node --check`; the five destination apps pass at 2/2, 2/2, 2/2, 5/5
and 2/2, each exactly one block more than its own pre-edit baseline. Div balance
unchanged in all six files.

## 6. What was not done, and why

- **No base `addMsg` was defined.** See §4 — it is the one-line revival of eight
  behaviours at once on a live app, and it is a product call.
- **No stub was deleted or renamed.** Needs a per-stub check of what guard it was
  added to satisfy.
- **The handoff sender is still dormant.** Its data is now correct, but it still
  renders into `#chatArea`. Reviving it is a visible change to a paying app and
  was not part of the request.
- **`window.fetch` is patched in at least seven places** (`:2095`, `:2527`,
  `:17076`, `:17279`, `:18684`, `:18900`, `:19128`). Whether those chain
  correctly or shadow each other was **not** investigated. It is the next thing
  I would look at.
- **Nothing here was verified in a real browser.** Every claim is from the source
  and from live HTTP checks. The three unreachable features are a strong
  prediction — no markup caller, no un-hiding code, injection into a
  `display:none` parent — but a browser session is what would confirm it, and
  that is precisely the "auth-gated blind spot" Guardian v2 names in its own
  Known Scope Limitation.
