# SAIRNscape — Scope

**Phase 1 scope, decided 2026-08-05.** Confirmed this session: SAIRNscape
and SAIRNgrounds are two distinct products — SAIRNscape serves general
residential/small-commercial landscapers, SAIRNgrounds serves golf
courses/HOAs/large commercial property. Current state of `sairnscape.html`
verified by direct read: a demo shell only — marketing page + 5-mode chat,
1053 lines, no real panels, no data model, `app_id:'sairnscape'` already
allowlisted in `api/claude.js` `KNOWN_APP_IDS` (confirmed present, unlike
SAIRNgrounds which needs adding). This doc covers **Phase 1 only**; later
phases listed at the bottom as known future scope.

| # | Decision |
|---|---|
| 1 | Supabase table prefix: **`scp_*`** — no collision with any existing app prefix. |
| 2 | Licence prefix: **`SCP-`** — not yet provisioned; Michael's step. |
| 3 | `KNOWN_APP_IDS` already includes `'sairnscape'` — no server change needed there, confirmed by direct read. |
| 4 | The existing marketing page + 5-mode chat demo is kept as a reference for **tone/voice only** — the real build uses the standard panel-based scaffold (auth gate, nav shell, data-layer), not the chat-demo architecture, per the working decision this session. |

---

## 1. Target persona + trade

**Trade:** general residential and small-commercial landscaping — mowing,
planting, seasonal cleanup, hardscape, small water features — as distinct
from SAIRNgrounds' golf-course/HOA/large-commercial-acreage focus.

**Primary persona — the owner-operator landscaper.** Runs a crew of 1-8
across dozens of residential/small-commercial accounts, often seasonal
(spring cleanup, mowing season, fall cleanup, snow in some markets). Daily
pain, in priority order:
1. **Customer and job list for today** — recurring mowing routes plus
   one-off jobs, on one board.
2. **Quoting new work fast**, often standing in the customer's yard.
3. **Scheduling recurring service** — the thing that makes landscaping
   different from a one-time-job trade like StoneDesk: most revenue is
   repeat/recurring, not one-off.
4. **Getting paid** — invoicing tied to completed visits.

**Deliberately out of scope for Phase 1:** small aquatic features (ponds/
fountains), AR walk-and-design (shared build with SAIRNgrounds — see
Future scope in both docs).

---

## 2. Phase 1 panel list

Same business-operation spine convention as every other app, adapted to
this persona's recurring-service model rather than one-off jobs.

| Panel | id | Purpose | Status |
|---|---|---|---|
| Dashboard | `dashboard` | Today's jobs/routes across all customers, at a glance. | Not built |
| AI Assistant | `ai` | Claude via `/api/claude`, `app_id:'sairnscape'` (already allowlisted). | Not built |
| Customer Directory | `customers` | Core record: name, address, contact, service type, recurring-schedule flag. | Not built |
| Job Intake | `intake` | New job capture: one-off or tied to a recurring schedule, scope, target date. | Not built |
| Quoting | `quotes` | Line-item quote builder, Low/Mid/High — same proven shape as StoneDesk/SAIRNgrounds, adapted to landscaping line items (mowing, mulch, planting, cleanup). | Not built |
| Scheduling | `schedule` | Recurring-route + one-off job calendar — the panel that makes the recurring-revenue model real rather than every job looking one-off. | Not built |
| Invoicing | `invoices` | Bills tied to completed visits/jobs, paid/unpaid status. | Not built |

**7 Phase-1 panels.** No Golf Module equivalent — this app's differentiator
is the recurring-service scheduling model, not a specialized vertical
feature, so Phase 1 stays spine-only rather than inventing a parallel
"defining differentiator" panel that doesn't reflect a real persona need.

**The existing chat demo:** kept live as-is (it's a working marketing/demo
surface, not broken), but is not the architecture the panels above are
built on — the panels get the standard auth-gate/nav-shell/data-layer
scaffold, same as every other app.

---

## 3. Data model (Phase 1 tables only)

```
scp_customers   customer_id, license_hash, updated_at, data{
                  name, address, contact_phone, contact_email,
                  service_type, recurring (bool), notes }

scp_jobs        job_id, license_hash, customer_id, updated_at, data{
                  scope, target_date, status, recurring_schedule_id }

scp_quotes      quote_id, license_hash, customer_id, updated_at, data{
                  line_items[], total_low, total_mid, total_high,
                  status (draft|sent|accepted|rejected), valid_until }

scp_schedule    schedule_id, license_hash, customer_id, updated_at, data{
                  frequency (weekly|biweekly|monthly|one_off),
                  next_date, assigned_crew, notes }

scp_invoices    invoice_id, license_hash, customer_id, job_id, updated_at,
                  data{ amount, status (unpaid|paid|overdue), issued_date,
                  paid_date }
```

**Unique constraints:** `UNIQUE (license_hash, <entity>_id)` on every table,
probe-verified before client code depends on it — same standing rule as
every other app's scope doc.

---

## 4. Shared infrastructure — reuse vs new

### Reused unchanged
| Component | Note |
|---|---|
| `api/_lib/license.js` | Untouched. |
| `api/claude.js` `KNOWN_APP_IDS` | Already includes `'sairnscape'` — no change needed, confirmed by direct read. |
| Pattern 13 entitlement gate | Applies as-is once resources are added. |

### Required server changes
| Component | Change |
|---|---|
| `api/sd-data.js` (or equivalent) `RESOURCES` | Add `customers`, `jobs`, `quotes`, `schedule`, `invoices` — same read+write branch pattern as every other app. |
| `vercel.json` | Confirm/add a `/sairnscape$` route for the real app if not already routed correctly alongside the existing demo shell. |
| `sairn-guardian-v2` App File Map | Confirm entry exists/is current for `sairnscape.html` given the scope change from demo shell to real app. |

### New, client-side only
| Component | Note |
|---|---|
| `sairnscape.html` real build | The existing 1053-line file is the marketing/chat demo. The panel-based app is new construction on top of it (or alongside it), using `sairnbiz.html` as the structural reference for auth-gate/nav-shell/data-layer — same correction as noted in `SAIRNGROUNDS-SCOPE.md`: `sairn-app-scaffold` does not itself contain that template, it only covers the photo→Claude pattern. |
| Licence gate | Prefix allowlist must include `'SCP-'` once the row is provisioned. |

### Licence provisioning — Michael's step
Same as every prior app: requires service-role/Supabase dashboard access.
One `SCP-*` row needs creating and endpoint-verified before the client gate
depends on it.

---

## 5. Future scope (explicitly deferred, not forgotten)

- Small aquatic features (residential ponds/fountains)
- AR walk-and-design — shared build with SAIRNgrounds' course-plotting
  feature; build once, decide which app gets it first once both have
  their Phase 1 spine live.

---

## 6. Verification standard for the build

Same non-negotiable standard as `SAIRNGROUNDS-SCOPE.md` §6: `node --check`
per script block, full Guardian v2 pass before push, live-verify against
the deployed URL after push. Nothing in this doc is "built" until it
passes both.
