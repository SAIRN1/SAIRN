# Platform audit — where the licence key reaches a customer, and what gating it would break

Audit pass, 2026-09-02. **No fix applied in this pass.** Requested explicitly as
a list-before-touching, and §4 is the reason that was the right order: the
proposed fix has a blast radius that changes its shape.

Scope: all 20 live app files, the whole `api/` layer, and the two public
customer-facing pages. `archive/branch-lucid-ptolemy-b73vu0/**` is excluded —
CLAUDE.md records it as an abandoned duplicate codebase.

---

## 1. What was searched, so the negative result means something

Three findings today were wrong because a grep for an expected name was
mistaken for a search for the thing. This pass enumerated **sinks** as well as
**sources**, and both directions are listed so the gaps in it are visible.

**Sources — every way a licence key can be read:**

- every `*LicenseKey()` accessor in every app: `alf`, `dnt`, `bld`, `leg`,
  `law`, `sdn`, `sen`, `rf`, `hr`, `sd`, plus StoneDesk's `slabLicKey()` alias
  — **106 call sites**, each classified;
- every inline `localStorage.getItem('*_license_key')` that bypasses an
  accessor — 17 sites;
- the server side: `api/**/*.js`.

**Sinks — every way a value can reach a customer:**

`navigator.share` · `clipboard.writeText` · `mailto:` · `sms:` · `wa.me` /
`api.whatsapp` · `window.open` with a constructed URL · `document.write` print
output · QR-code payloads · URL query-string construction · outbound email
bodies in the API layer.

**Cross-search:** every line where a key identifier and a URL-ish literal
(`http`, `sairn.vercel.app`, `?x=`, `&x=`) appear together — 7 candidate lines,
all resolved below.

---

## 2. The one real instance — StoneDesk intake link (FIXED, `508eaa5`)

`intakeBuildLink()` built:

```js
INTAKE_FORM_URL + '?shop=' + shop + '&lic=' + encodeURIComponent(slabLicKey())
```

and `intakeShareLink()` wraps it in *"Hi! Before your appointment, please take
2 minutes to fill out this quick project form…"* — copy that exists to be sent
to customers. `slabLicKey()` → `sdLicenseKey()` → the same string sent as
`Authorization: Bearer` on every `/api/sd-data` call.

**Capability of the leaked key, verified live against `SD-AUDIT-2026` with the
bearer key and no employee session:**

| resource | result |
|---|---|
| `slabs` | 200 — full inventory returned, **and writable** (`write` is a blind upsert; `reserve` also needs no session) |
| `profile` | 200 — company, EIN, city, headcount, revenue range, owner, AI notes |
| `memory` | 200 — the shop's AI memories |
| `employees` | 403 FORBIDDEN |
| `sd_crm`, `sd_hr_employees` | 401 NO_SESSION |
| `sd_approvals`, `supplier_lead_times` | 403 FORBIDDEN |

Removed. It cost nothing that worked: `https://sairn.vercel.app/stonedesk-intake`
returns **404** — verified — so the form never existed and nothing consumed
`lic`. The panel now says so rather than presenting the link as ready.

---

## 3. Everything else checked, and clean — with the evidence

**No other app puts a licence key in a customer-visible URL.** Each line below
is a place it could have and does not.

| Where | What it actually is |
|---|---|
| All ~100 `var lic = *LicenseKey()` sites across 9 apps | Presence checks (`if(!lic) return`) or values handed to a header builder. Every one has `Authorization: Bearer` within six lines or delegates to a helper that adds it. |
| `sairndental-book.html`, `sairndental-complaint.html` | **The correct pattern, and the precedent to copy.** Public links use `?slug=` (a purpose-made public identifier) and a per-thread `?token=`. Never the licence key. |
| `sairnvet.html:3158` `copyConsultLink()` | A random placeholder id on a placeholder domain, labelled as such in the toast. No credential. |
| `sairnmechanical.html:910` `fqShare()`, `stonedesk.html:32491` | Share the quote **text**. No URL, no key. |
| StoneDesk suite launcher (`:16341+`) | Plain `https://sairn.vercel.app/<app>` links. No key. |
| QR payloads | The only `new QRCode(` on the platform is the slab label added today: payload `SDSLAB:<slab id>`. No key. |
| Print / `document.write` output | No key in any printed document. The apparent hits are `slice(` and `licensed` matching on the substring "lic". |
| `api/**` outbound content | Every `license_key` hit is a request-validation guard. The only keys in server-built URLs are `license_hash` — a hash, not the key. Patient reminder emails contain no links at all. |

**One thing that is not a customer disclosure but belongs on the list:**
`stonedesk.html:5127` and `:35861` display the **full** licence key in the
Admin and IT Admin panels. `sairndesign.html:3203` masks it
(`lic.slice(0,3)+'-***-'+lic.slice(-4)`). Same class of data, two different
standards, and given §2 establishes the key is a live credential, the masked
one is the correct standard. Cheap to align; not urgent; not customer-facing.

---

## 4. The blast radius of the proposed fix — read this before gating anything

Session-gating `slabs` / `profile` / `memory` is **not a one-line change**, and
two dependencies would break silently rather than loudly.

### 4.1 SAIRNcode uses `read profile` as its pre-login licence probe

`sairncode.html:3044-3049`, inside the licence-key gate:

```js
fetch('https://sairn.vercel.app/api/sd-data', {
  headers: { 'Authorization': 'Bearer ' + key },
  body: JSON.stringify({ action: 'read', resource: 'profile' })
});
// res.status === 401 -> "Unknown license key"
```

It is not reading a profile; it is asking *"is this key real?"* **There is no
session at that moment, and cannot be.** Session-gating `profile` **read**
would make every SAIRNcode licence look invalid and lock every user out at the
gate.

That needs a decision: either `profile` read stays open, or SAIRNcode moves to a
dedicated validate-licence action (`api/sc-auth.js` already exists and could
carry it — StoneDesk validates against `api/sd-auth.js`, not `profile`, which
is why it is unaffected).

### 4.2 StoneDesk loads all three **before** an employee logs in

`stonedesk.html:26097-26101`, on `DOMContentLoaded`:

```js
loadSDProfile();   // read profile
loadSDMemories();  // read memory
loadSlabs();       // read slabs
```

The licence key lives in `localStorage` and survives a tab close. The session
token lives in **`sessionStorage`** and does not. So on every fresh tab these
three run with a bearer key and **no session token**.

Gated, all three would 403 — and `sdData()` **returns `null` on any failure
without reporting it**, so the result would be:

- the AI system prompt silently loses the business profile and the shop
  memories (the exact regression `[0040]` was raised to fix);
- the dashboard low-stock alert renders empty;
- the Slabs panel renders empty until something else re-syncs.

Nothing would say why. The fix is to move those three loads into the existing
post-login init list in `showApp()` — where `sdApprovalsLoad` was added today —
**and that must land in the same change as the gate**, or the gate ships a
silent data-loss regression.

### 4.3 Scope of the gate itself, once those two are handled

- `slabs` **write** and `reserve` — StoneDesk only. Safe to gate. This is the
  one that matters most: it is the write path a leaked key could abuse.
- `slabs` **read** — StoneDesk only, safe once §4.2 is done.
- `profile` **write**, `memory` read/write — StoneDesk only, safe once §4.2 is
  done.
- `profile` **read** — blocked on §4.1.

---

## 5. What this audit did not cover

Stated rather than implied, because a clean result is only as wide as its
search:

- **Licence keys already in the wild.** Any key that has been in a shared link,
  an SMS thread or a browser history is disclosed and this pass cannot find or
  recall it. If StoneDesk's intake link was ever sent to a customer,
  `SD-PINNACLE-2026` should be treated as compromised and rotated — a question
  only Michael can answer.
- **Non-HTML surfaces**: no check of anything the apps do not build — printed
  marketing, saved bookmarks, screenshots.
- **`api/bridge.js` and `api/network.js`** were checked for licence keys in
  outbound content and are clean, but their full payloads were not audited for
  other sensitive fields. Different question, not asked here.
