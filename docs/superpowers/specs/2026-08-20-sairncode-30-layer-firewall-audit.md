# SAIRNcode — 30-Layer Universal Security Firewall: verification against real deployed code

**Date:** 2026-08-20 · **Scope:** verification only, nothing built, nothing changed.
**Spec audited:** the 30-layer Universal Security Firewall designed 2026-06-13,
never re-verified against deployed code since.
**Code audited:** `sairncode.html`, `api/claude.js`, `api/sc-auth.js`,
`api/sc-credentials.js`, `api/sc-eligibility.js`, `api/sd-data.js`,
`api/_lib/auth.js`, `sql/sairncode_*.sql` — at commit `f62687e`.

## Headline

**Present or genuinely superseded: 10 of 30. Missing: 20 of 30.**

But the raw count is misleading, and acting on it as a checklist would be a
mistake. The June 13 spec was written for an app that **had no real
server-side auth** — at that time every control had to live in the browser.
That premise is now obsolete: `api/sc-auth.js` (2026-08-18) replaced the
hardcoded client-side PIN gate with real per-employee credentials, and
`api/sd-data.js` enforces server-side RBAC on destructive operations.

Consequently ~8 of the 20 "missing" layers are things that **should not be
built**, because in a browser app they are bypassable-by-design and would
create a false sense of coverage. Section 4 separates the ones that genuinely
matter from the ones that are security theater — that separation is the
actual value of this audit, not the 10/30 score.

---

## 1. WALL 1 — BROWSER (18 layers): 5 present/superseded, 13 missing

| # | Layer | Verdict | Evidence |
|---|---|---|---|
| 1 | Domain allowlist fetch interceptor | **MISSING** | No `window.fetch` or `XMLHttpRequest.prototype.open` override anywhere in `sairncode.html`. |
| 2 | API key scrubbing | **MISSING** | Zero matches. (All "scrub" hits are the unrelated *Prebill Scrubber* claim feature — easy to mistake for a hit.) |
| 3 | PII pattern detection | **MISSING** | Zero real matches; grep hits were `className` false positives. |
| 4 | Credential blocking | **MISSING** — see §3, superseded in effect | No such function. Real credential handling now server-side. |
| 5 | Network origin validation | **MISSING** | No allowlist/host validation client-side. |
| 6 | Direct API call blocking | **N/A by design** | Zero `api.anthropic.com` references in `sairncode.html`; all AI traffic goes via `APP_CONFIG.proxy`. Nothing to block. Enforced at review time (Guardian hard-block) + server-side `KNOWN_APP_IDS` allowlist (`api/claude.js:31`). |
| 7 | Rate limiting simulation | **MISSING** client-side | See §4 — "simulation" is the tell; real limiting must be server-side (layer 22). |
| 8 | Error sanitization | **PRESENT** | 69 catch blocks; user-facing text is generic (`'Error: Unable to process request'`). Server endpoints return generic messages and log detail server-side only — `upstream()` in `sc-auth.js:237`, `sc-credentials.js`, `sc-eligibility.js` all return `'Data store error — try again'`. Implemented in practice, not as a named layer. |
| 9 | Console warning system | **PARTIAL** | Exactly 2 `console.warn` calls (`sairncode.html:3987, 3990`, scData failures). Useful, not a system. |
| 10 | CSP meta tag | **MISSING** | No `Content-Security-Policy`, no `http-equiv` anywhere. **See §4 — worth fixing.** |
| 11 | XSS output sanitizer | **PRESENT AND SOUND** | `escHtml()` at `sairncode.html:1651` (escapes `& < > " '`), 53 call sites. Mechanically verified: of 95 `innerHTML` assignments, only 2 interpolate without `escHtml` (L1926, L3930) and **both interpolate only numeric `.length` values** — no user-controlled unescaped path found. |
| 12 | Clickjacking / frame-busting | **MISSING** | No `window.top`/`frameElement` check, no `frame-ancestors`. **See §4 — worth fixing.** |
| 13 | SRI on CDN scripts | **NOT APPLICABLE** | Zero external `<script src=>`. Single-file app with no CDN dependencies, so there is nothing to pin. |
| 14 | Session timeout + auto-lock | **SUPERSEDED — STRONGER** | Server-side HMAC-signed session tokens, `SESSION_TTL_MS = 12h` (`api/_lib/auth.js:43,177`), verified on every privileged call. Plus PIN re-entry forced on every page load/reload. **One real residual gap:** no client-side idle timer, so an unattended unlocked workstation stays unlocked for up to 12h. |
| 15 | Data exfiltration monitor | **MISSING** | No `sendBeacon`/exfil monitoring. See §4 — not meaningfully achievable client-side. |
| 16 | Clipboard protection | **MISSING** | No copy/paste handlers. See §4 — recommend NOT building. |
| 17 | DevTools-open detection | **MISSING** | Only match is a comment at `sairncode.html:1412` acknowledging DOM/devtools bypass. See §4 — recommend NOT building. |
| 18 | Input sanitization / entity encoding on render | **PRESENT** | Same mechanism and same evidence as layer 11. |

## 2. WALL 2 — API PROXY (5 layers): 1 present-but-weak, 4 missing

| # | Layer | Verdict | Evidence |
|---|---|---|---|
| 19 | HMAC request signing | **MISSING for `/api/claude`** — but see note | No signing between client and the AI proxy. **However** HMAC-SHA256 *is* used for session tokens (`api/_lib/auth.js:168,189`), and every `sc-*` data endpoint requires a real signed session via `X-SD-Auth`. So the data plane is authenticated; the AI proxy is not. See §4 — a browser cannot hold an HMAC secret, so this is not fixable as specified. |
| 20 | Prompt injection detection | **MISSING** | No injection/jailbreak screening in `api/claude.js`. **See §4 — this one genuinely matters here.** |
| 21 | Response sanitization (strip echoed PII) | **MISSING** | `sanitizeTools()` (`api/claude.js:68`) is a **tool-definition allowlist**, not response sanitization — easy to miscount as a hit. No response-body scrubbing exists. |
| 22 | Rate limiting per app_id | **PRESENT BUT WEAK — and self-disclosed as such** | `demoCallCounts` / `DEMO_DAILY_LIMIT = 200` keyed `app_id\|day` (`api/claude.js:83-88,165-170`). SAIRNcode does send `is_demo: true` (`sairncode.html` APP_CONFIG), so it applies. But `api/claude.js:13-17` already documents it as in-memory, per-instance, resetting on cold start — it does **not** reliably cap usage or cost. |
| 23 | Anomaly detection | **MISSING** | No anomaly/threshold logic. |

## 3. WALL 3 — DATA (3 layers) · WALL 4 — COMPLIANCE (4 layers)

| # | Layer | Verdict | Evidence |
|---|---|---|---|
| 24 | localStorage encryption at rest | **MISSING for app data** | All `sc_*` keys are plain `JSON.stringify`. Note: server-side credentials *are* AES-256-GCM encrypted (Phase 1, `api/_lib/auth.js:374`) — a different layer than this spec item. **See §4 — real risk, but harder than it looks.** |
| 25 | Data minimization | **PARTIAL — real where it counts** | Deliberate and documented: the raw 271 response is **not** stored (`sql/sairncode_eligibility_schema.sql:14`, panel copy `sairncode.html:1137`). No general minimization policy across the other 18 resources. |
| 26 | Automatic purge / expiry | **MISSING** | Only manual `removeItem` of role/token/employee_id on logout (`sairncode.html:1583-1585`). No retention or expiry for any PHI-bearing resource. |
| 27 | CCPA/GDPR consent notice | **MISSING** | Zero matches for consent/GDPR/CCPA. |
| 28 | Privacy policy / data-handling disclosure | **MISSING in-app** | No privacy/subprocessor/terms disclosure anywhere in the app. (The platform *does* produce these as .docx for SAIRNbiz/SAIRNvet/SAIRNcare/etc. — but none exists for SAIRNcode, and none is surfaced in any app.) |
| 29 | Right to delete | **PARTIAL** | Real per-entry delete exists across every resource (`removeXEntry` → `scData('delete')` → admin-gated server-side, `api/sd-data.js:2280-2284`). No bulk "delete all data for this practice". |
| 30 | Local audit log of every AI call | **MISSING in SAIRNcode** | No audit logging of AI calls. **Notable:** `api/_lib/audit.js` exists and is already used by `api/law-auth.js` and `api/legal-citator.js` — the platform has this capability; SAIRNcode simply does not use it. **See §4 — cheapest high-value item on this list.** |

## 4. What actually matters — risk-ordered, not checklist-ordered

Applying `sairn-decision-gate`'s prioritization principle (risk first, never
scope or list order).

### Worth building (real risk, real fix)

1. **Layer 30 — audit log of AI calls.** SAIRNcode sends clinical notes to an
   LLM and has no record of it. For a PHI-handling medical-billing app that is
   the clearest gap on this list, and `api/_lib/audit.js` already exists and is
   proven in SAIRNlaw. Cheapest high-value item here.
2. **Layers 27 + 28 — consent + in-app data-handling disclosure.** A medical
   app routing PHI through a third-party subprocessor (Anthropic) with no
   in-app disclosure is a genuine compliance gap, not a paperwork nicety.
   Directly relevant to the NIST AI RMF *Govern* function already flagged in
   the Phase 2 scope.
3. **Layer 20 — prompt injection detection.** Users paste **clinical notes**
   into the AI. A note containing injected instructions is a live vector, and
   this app's whole differentiator is grounded, non-fabricated output. Highest
   Wall-2 value.
4. **Layer 10 — CSP meta tag.** One tag, meaningful defense in depth for a
   single-file app with no external scripts (layer 13 confirms nothing legit
   would break).
5. **Layer 12 — frame-busting.** Cheap, prevents clickjacking a PHI app.
6. **Layer 26 — purge/expiry.** PHI retention with no expiry is a real
   liability. Needs a policy decision from Michael first, not just code.
7. **Layer 22 — strengthen the existing rate limit.** Already flagged unreliable
   by its own author. A persistent counter (Supabase, like
   `api/_lib/courtlistener.js`'s real rate limiter already does) is the known
   fix and the precedent already exists in-repo.
8. **Layer 14's residual gap — client idle timer.** The 12h server TTL is
   strong, but a shared clinic workstation left unattended stays unlocked.
   Small, real.

### Should NOT be built — security theater in a browser app

Building these would create coverage that does not exist. Recommending against
them is a finding, not a gap.

- **17 (DevTools detection)** — trivially bypassed; annoys legitimate users.
- **16 (clipboard protection)** — bypassable and actively hostile to coders who
  legitimately copy codes between systems.
- **15 (exfiltration monitor)** — cannot meaningfully work client-side.
- **1, 5, 6 (fetch interceptor / origin validation / direct-call blocking)** —
  anyone with DOM access removes them in seconds. The real control is
  server-side and already exists (`KNOWN_APP_IDS`, license validation, session
  verification).
- **2, 3, 4 (client-side key scrubbing / PII detection / credential blocking)** —
  same class. Worth reconsidering **only** as server-side controls in
  `api/claude.js`, where they cannot be edited away — which is layers 20/21,
  already listed above.
- **7 (rate limiting *simulation*)** — the word "simulation" is the tell; a
  client-side limiter is advisory only. Fix layer 22 instead.
- **19 (HMAC signing client→proxy)** — **not fixable as specified.** A browser
  app cannot hold a signing secret; shipping one would put the key in the
  client source. The real answer is what the `sc-*` endpoints already do:
  require a server-issued, HMAC-signed session token.

### Superseded by stronger controls built since June 13

The spec assumed no server-side auth. What exists now is materially stronger
than layers 4, 7, 14, and 17 would have been:

- **Real per-employee auth** (`api/sc-auth.js`): scrypt-hashed PINs with
  per-credential salt (`api/_lib/auth.js:129`), constant-time verification
  (`:152`), 5-attempt lockout / 15-minute cooldown (`sc-auth.js:43-44`).
- **HMAC-SHA256 session tokens**, 12h TTL, pinned to `expectedApp` so a token
  from another SAIRN app on the same license is rejected.
- **Server-side RBAC on destructive operations** — delete re-verifies a real
  admin session server-side regardless of client state (`api/sd-data.js:2280`).
- **Supabase RLS**: 15 SAIRNcode tables, service-role-only, `anon`/`authenticated`
  revoked (`sql/sairncode_data_schema.sql`).
- **Server-tool type allowlist + `max_uses` ceiling** (`api/claude.js:65-80`).
- **AES-256-GCM credential encryption** (Phase 1).

## 5. New finding — not one of the 30

**`demo_pin: '1234'` (`sairncode.html:1369`) is dead config.** Defined in
`APP_CONFIG`, **never read anywhere** — verified: 3 total matches, all inside
the definition block. Vestigial from the pre-2026-08-18 hardcoded-PIN era that
`api/sc-auth.js` replaced.

Not exploitable (nothing consumes it; the real gate is server-side), but it
advertises a credential that looks live, and it is exactly the dormant-code
class Guardian flags. **Recommend deleting the line.** Flagged, not changed —
this pass is verification only.

## 6. Verification method — and what it could not see

Every verdict above is grep/read evidence against the real file at `f62687e`,
with line numbers, plus one mechanical XSS check that parsed all 95 `innerHTML`
assignments rather than eyeballing them.

**What this method structurally could not see** (per the premortem discipline —
asking what the review itself misses, not just what it found):

- **No runtime verification.** Nothing here was confirmed in a running browser.
  A control could exist in source and be broken at runtime, or be neutralized
  by load order. Same real-credentials gap as the rest of this session
  (SC-PINNACLE-2026's admin PIN is unknown).
- **Absence of a grep match is weaker evidence than presence.** A control
  implemented under unexpected naming could read as "missing". Mitigated by
  searching several synonyms per layer, but not eliminated.
- **Deployed-vs-committed** was not re-verified for this audit specifically;
  it reads the committed working tree. Prior pushes this session were
  live-confirmed, but that is not the same claim.
