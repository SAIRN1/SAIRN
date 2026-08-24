---
name: sairn-app-scaffold
description: 'The starting-point checklist for scaffolding a new SAIRN app from zero. Created 2026-07-30 -- a prior session referenced this skill in a handoff before it actually existed on disk; this is the first real version, not a restoration. Covers TWO required components as of 2026-08-24: (1) photo-capture -> Claude analysis -> structured app output, generalized from StoneDesk''s Field Sketch Quote; (2) the credential-deactivation lifecycle (set_active with last-admin refusal, no self-deactivation, deactivated-caller re-check, audit on every outcome), required in v1 for any app with per-employee credentials after the same gap was found and fixed independently in three apps. Still not a full scaffold from A to Z. Trigger when starting a new SAIRN app from scratch, or when deciding what a new app''s v1 must include before the first panel gets built.'
---

# SAIRN App Scaffold

This file does not yet cover everything a new app needs (data model conventions, licensing setup, etc. live in `sairn-software-architect` and `SAIRNBUILD-SCOPE.md`-style scoping docs for now). What it does cover is TWO standing requirements: **every new SAIRN app's v1 scope must include the photo-to-Claude-suggestion pattern** (added 2026-07-30), and **any new app with per-employee or per-account credentials must ship the credential-deactivation lifecycle in v1** (added 2026-08-24). Neither is to be bolted on after the fact -- the second is here precisely because it was bolted on after the fact three separate times.

## Required component: Photo Capture → Claude Analysis → Structured Output

### Why this is required, not optional

StoneDesk's Field Sketch Quote (a rep photographs a hand-drawn sketch on a jobsite, Claude reads it, asks up to 3 clarifying questions, then generates a priced quote) is a proven, working pattern — real code, live in production, not a concept. The standing product rule: every new SAIRN app should carry the same *shape* of feature from day one, with the output adapted to that app's vertical. What changes per app is only the output; the photo-capture → Claude-call plumbing is identical and should not be reinvented per app.

### The generic 3-stage pattern

1. **Photo capture UI** — a tap-to-photograph zone, camera-first on mobile:
   ```html
   <input type="file" accept="image/*" capture="environment">
   ```
   `capture="environment"` opens the rear camera directly on a phone instead of a generic file picker — this is what makes it a field tool, not a desktop upload form. Show a preview (`<img>`) after capture, and encode the file to base64 client-side before sending it anywhere (`FileReader.readAsDataURL`).

2. **Claude analysis call, through the proxy — never direct**. Per the platform's standing Proxy rule (Guardian Check 1), this must go through `sairn.vercel.app/api/claude`, never `api.anthropic.com` directly, and the request body must include `app_id` and `is_demo:true` (Guardian Checks 3–4). The image goes in as a multimodal content block alongside a text instruction:
   ```js
   const msgs = [{
     role: 'user',
     content: [
       {type:'image', source:{type:'base64', media_type:'image/jpeg', data: img64}},
       {type:'text', text: 'Analyze this photo for <app-specific task>.'}
     ]
   }];
   const res = await fetch('https://sairn.vercel.app/api/claude', {
     method:'POST', headers:{'Content-Type':'application/json'},
     body: JSON.stringify({app_id: APP_ID, is_demo:true, system, messages: msgs})
   });
   ```
   The system prompt is where the app-specific behavior lives — StoneDesk's says "read the drawing, ask MAXIMUM 3 questions, be fast, the customer is watching." Cap the clarifying questions explicitly in the prompt; an open-ended back-and-forth is not what a field rep standing in front of a customer needs.

3. **App-specific structured output.** This is the one piece that must NOT be copy-pasted between apps — the shape of what Claude returns should match the vertical:
   - **StoneDesk / trades (built, live)** — photo → up to 3 questions → itemized quote (line items, Low/Mid/High total, exclusions, 30-day validity, signature line)
   - **SAIRNbuild** — photo of a jobsite issue → cost/scope suggestions (not yet built — flag this as a gap against the current 4-panel scope, not an existing feature)
   - **SAIRNvet** — photo → diagnosis suggestions (not yet built — same caveat; SAIRNvet's current build status should be re-verified independently before assuming this is a gap vs. already covered)
   - Any new app — pick the output shape that matches what that app's user actually needs from a photo, don't default to "generate a quote" if the vertical isn't sales-facing.

### Honest note on "structured output" — read the real implementation before overclaiming

StoneDesk's actual implementation is **not** strict JSON-schema output. Both Claude calls (`sairnFQAnalyze`, `sairnFQGenQuote` in `stonedesk.html`) return free-text (`data.content[0].text`), and the app extracts what it needs with a targeted regex against that text (e.g. `r.match(/Mid[:\s]+\$?([\d,]+)/i)` to pull one dollar figure for a deposit calculation) rather than parsing a JSON object. That is the proven baseline — free text plus light, targeted extraction, not a fragile full-JSON contract. A new app is free to ask Claude for stricter JSON if its output genuinely needs it (e.g. a diagnosis-suggestions list with confidence scores), but should treat that as an enhancement on top of the proven pattern, not assume the reference implementation already works that way.

### Reference implementation (the one real one — verify current line numbers before citing, `stonedesk.html` grows)

- DOM: `#sairn-fq-modal` and children (`#sairn-fq-p1`–`p5` — the 5 steps: trade select, photo capture, AI Q&A, quote output, close/deposit)
- Photo capture + preview: `~L12265-12280`, file input handler ending `reader.readAsDataURL(file)` at `L12557`
- Analysis call: `window.sairnFQAnalyze` at `L12560`
- Quote generation call: `window.sairnFQGenQuote` at `L12592`
- Shared proxy helper: `async function sairnCallClaude(system, messages)` at `L12740` — POSTs to `SAIRN_PROXY = 'https://sairn.vercel.app/api/claude'` with `{app_id, is_demo:true, system, messages}`, returns `data.content?.[0]?.text || ''`

New apps should write their own equivalent of `sairnCallClaude` (or literally reuse the same shape) rather than inventing a different request/response contract — one proxy-call convention across the platform, not one per app.

## Required component: the credential-deactivation lifecycle (added 2026-08-24)

**Any new app with per-employee or per-account credentials must ship
`set_active` in v1.** Not "add it when someone asks" — in the first version,
alongside `bootstrap`/`login`/`setup`/`roster`.

### Why this is required, not optional

This is the second standing requirement in this file, and it is here because
the same gap was found and fixed independently in three apps rather than once:

| App | How it got there |
|---|---|
| StoneDesk (`api/sd-auth.js`) | Retrofitted 2026-08-23 |
| SAIRNcode (`api/sc-auth.js`) | Retrofitted 2026-08-23/24 (`12c670c`) |
| SAIRNroofing (`api/rf-auth.js`) | Shipped in v1, deliberately, *because* of the two retrofits above |

Found three times means nothing was checking for it. `api/rf-auth.js`'s own
header already states the case better than a rule can: before `set_active`
existed, *"the only way to neutralise a credential was a hand-written SQL
DELETE run by a human with Supabase access, which is how three StoneDesk
licences were lost (SD-PINNACLE-2026's PIN is still undocumented)."*

**A correction worth carrying:** this pattern is sometimes described as
StoneDesk / SAIRNcode / **SAIRNcash**. It is not. `api/sairncash/` has no auth
lifecycle at all — verified 2026-08-24, the directory holds only
checkout/trial/verify/waitlist handlers. SAIRNcash's trial-deactivation
equivalent is still an open product decision, not an implementation. The real
third instance is SAIRNroofing.

### The four guards, and what each one is actually for

Copy the shape from `api/rf-auth.js` (built after the lessons) or
`api/sd-auth.js` (the fullest retrofit). Every one of these exists because
something went wrong without it:

1. **Last-active-admin refusal** — refuse to deactivate the only remaining
   credential that can provision. Returns `409 LAST_ADMIN` naming what would
   happen: *"Deactivating it would lock everyone out with no way back in
   through the app — provision another first, then retry."*

   Note StoneDesk's own comment marks this guard **unreachable by
   construction** today, and keeps it anyway: *"reachability is a property of
   today's rule set — a new provisioning role or any path skipping that check
   makes it live again, and a lockout is not worth re-discovering in
   production."* Keep it in a new app for the same reason. A guard that costs
   nothing and prevents an unrecoverable state stays.

2. **No self-deactivation** — `409 SELF_DEACTIVATE`. An admin removing their
   own credential is almost always a mistake, and is indistinguishable from
   the lockout case at the moment it happens.

3. **Deactivated-caller re-check** — the one that is easy to miss and was found
   live on SAIRNcode. **A session token carries its role claim and stays valid
   for its full 12-hour life after the credential behind it is deactivated**,
   so a just-removed admin can keep removing other people. Verifying the token
   is not enough; re-read the caller's CURRENT row and confirm `active === true`
   before honouring any privileged action. Returns `403 CREDENTIAL_INACTIVE`.

   Apply it to `roster` too, not only to `set_active` — StoneDesk does.

4. **Audit entry on every outcome, including refusals** — not just successes.
   `credential_deactivated`, `credential_reactivated`, and
   `credential_change_refused` with a `reason_code` (`SELF_DEACTIVATE`,
   `LAST_ADMIN`, `CREDENTIAL_INACTIVE`). The refusals are the interesting
   half: an attempt to lock out a company is exactly what someone will later
   want to see. Return the write's own result as `audited:` in the response so
   a failed audit write is visible rather than assumed.

### Three more things the real implementations get right

- **Deactivate, never DELETE.** Deleting destroys `created_at`, role history
  and audit linkage — *"deleting is what made those three cleanups both
  unrecoverable and unauditable."*
- **`roster` must include inactive rows.** It originally filtered
  `active=eq.true`, which was fine when nothing could be deactivated and became
  wrong the moment reactivation existed: an admin has to *see* a deactivated
  person to turn them back on.
- **A deactivated credential must not become re-bootstrappable.** Otherwise
  anyone holding the licence key can deactivate their way to a fresh bootstrap
  and seize the account. Both `sd-auth.js` and `rf-auth.js` call this out
  explicitly.

### Require a `reason` when deactivating

`reason` is mandatory on deactivation (max 500 chars) and lands in the audit
entry. Reactivation does not require one.

## What still needs to be added to this scaffold (not done tonight)

This file currently covers only the photo→Claude→output requirement. A complete new-app scaffold checklist (data model prefix convention, licence gate pattern, Vercel route + `vercel.json` wiring per the Iron Law, demo-seed conventions) is not yet consolidated here — those live piecemeal in `sairn-software-architect`, `sairn-guardian-v2`, and per-app `*-SCOPE.md` docs today. Flagging so a future session doesn't assume this file is comprehensive just because it exists.
