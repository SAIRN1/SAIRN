# SAIRN Backend Setup — Complete in ~20 Minutes
Michael L. Dibert · SAIRN Technologies · 2026

---

## STEP 1 — Supabase Setup (8 min)

1. Go to https://supabase.com and sign in
2. Click **New Project** → name it `sairn-platform` → pick a strong DB password → save it
3. Wait for project to provision (~60 seconds)
4. Go to **SQL Editor** → click **New Query**
5. Paste and run `schema.sql` first (already in repo)
6. Paste and run `schema_b2b.sql` second (just pushed)
7. Go to **Settings → API** → copy:
   - **Project URL** → this is `SUPABASE_URL`
   - **anon public key** → this is `SUPABASE_ANON_KEY`
   - **service_role secret key** → this is `SUPABASE_SERVICE_ROLE_KEY`

---

## STEP 2 — Vercel Environment Variables (5 min)

Go to https://vercel.com → SAIRN project → Settings → Environment Variables

Add ALL of these (Production + Preview + Development):

```
SUPABASE_URL                = https://YOUR-PROJECT.supabase.co
SUPABASE_ANON_KEY           = eyJ...  (anon public)
SUPABASE_SERVICE_ROLE_KEY   = eyJ...  (service role)
STRIPE_SECRET_KEY           = sk_live_... (already in Vercel?)
STRIPE_WEBHOOK_SECRET       = whsec_...
ANTHROPIC_API_KEY           = sk-ant-... (already in Vercel)
```

Then go to **Deployments** → click the 3 dots on latest → **Redeploy**

---

## STEP 3 — Stripe Webhook (3 min)

1. Go to https://dashboard.stripe.com/webhooks
2. Click **Add endpoint**
3. URL: `https://sairn.vercel.app/api/stripe` (the existing webhook handler)
4. Select events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Copy the **Signing secret** → add to Vercel as `STRIPE_WEBHOOK_SECRET`

---

## STEP 4 — Wire Apps to Backend (per app, ~2 min each)

Add this to the `<head>` of StoneDesk first:

```html
<!-- Stripe.js for card collection -->
<script src="https://js.stripe.com/v3/"></script>
<!-- SAIRN DB SDK -->
<script src="https://sairn.vercel.app/sairn-db-sdk.js"></script>
```

Add this to the boot function:

```javascript
// Initialize DB on boot
var db;
async function bootDB() {
  db = await SAIRNDb.firstRun('stonedesk', 'mikied68@gmail.com');
  console.log('DB connected, shop:', db.shopId);
  localStorage.setItem('sairn_shop_stonedesk', db.shopId);
  await loadDashboardData();
}

// Load real data
async function loadDashboardData() {
  const [jobs, customers] = await Promise.all([
    db.loadTodayJobs(),
    db.loadCustomers('', 10)
  ]);
  // update dashboard KPIs from real data
  document.getElementById('dash-jobs-today').textContent = jobs.length;
  document.getElementById('dash-customers').textContent = customers.length;
}

// Save a job (call this from job intake)
async function saveJobToDB(jobData) {
  const job = await db.saveJob(jobData);
  notify('Job saved: ' + job.job_number);
  return job;
}

// Charge card on file
async function chargeInvoiceCard(invoiceId, total) {
  const result = await db.chargeCard(invoiceId, Math.round(total * 100));
  if (result.ok && result.status === 'paid') {
    notify('Payment collected: $' + total.toFixed(2));
  } else if (result.no_card) {
    // No card on file — generate payment link instead
    const link = await db.paymentLink(invoiceId);
    window.open(link.payment_url, '_blank');
  }
}
```

---

## WHAT EACH FILE DOES

| File | Purpose |
|------|---------|
| `schema_b2b.sql` | Supabase tables: shops, customers, jobs, invoices, payments, parts, slabs, projects, gl_entries |
| `api/db.js` | All CRUD operations — save/load jobs, customers, invoices, parts, slabs, projects, GL |
| `api/pay.js` | Stripe: card setup, charge on file, payment links, B2B subscription checkout, refunds |
| `api/claude.js` | Updated proxy: Sonnet for B2B (50/day demo), Haiku for consumer (15/day demo) |
| `sairn-db-sdk.js` | Client SDK — drop into any app, gives `db.saveJob()`, `db.chargeCard()` etc |
| `sw.js` | PWA service worker — offline-first, background sync when signal returns |

---

## ORDER TO WIRE APPS

1. **StoneDesk** — highest priority, most mature
2. **SAIRNbuild** — construction PM, projects table ready
3. **SAIRNtrade** — trade service, jobs + invoices + payments
4. **SAIRNscape** — outdoor ops, same jobs pattern
5. **SAIRNhr** — people data, shop_users table
6. **SAIRNacc** — GL entries table bridges all others

---

## STRIPE PUBLISHABLE KEY

For card collection in the browser you need this in each app's HTML:
```javascript
var stripe = Stripe('pk_live_YOUR_PUBLISHABLE_KEY');
```

Get it from: https://dashboard.stripe.com/apikeys

