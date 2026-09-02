// api/_lib/exec-context.js
//
// The Executive Suite's advisor system prompts. Moved OUT of stonedesk.html on
// 2026-09-02 and served only through an authenticated, role-gated read.
//
// -- WHY THEY ARE NOT IN THE HTML ANY MORE ----------------------------------
// They carry SAIRN Technologies' own internal business data: the chart of
// accounts, the StoneDesk price book, and the provisional-patent filing dates
// with the non-provisional deadline. stonedesk.html is served in full to every
// customer of the product, so every one of those facts was readable with View
// Source by anyone who could load the page.
//
// The 2026-09-02 role gate on showPanel() closed the UI path and did not close
// this one, and said so at the time rather than being reported as a fix. This
// file is the actual fix: the strings are no longer in anything a customer's
// browser is given. They reach the browser only after api/sd-data.js has
// verified a real employee session on this licence AND that its role is owner
// or admin -- the same check showPanel() enforces, now enforced server-side
// where it cannot be edited out of the page.
//
// -- KNOWN DEFECT, RELOCATED VERBATIM AND DELIBERATELY NOT FIXED HERE -------
// The `cto` context describes "React 18 + TypeScript frontend, Express backend,
// Drizzle ORM, PostgreSQL on Railway" and "all 21 apps share one Railway
// PostgreSQL instance". That is FABRICOR, which CLAUDE.md records as an
// abandoned duplicate codebase. StoneDesk is vanilla JS on Vercel with
// Supabase. It also claims "QuickBooks Online (UI built, OAuth pending)" when
// no such UI exists -- sdIntegQuickAdd() adds a row to an integrations
// catalogue, not a connector.
//
// This is recorded in the 2026-09-02 competitive-gap audit as finding 4.2 and
// is still open. It is carried across unchanged ON PURPOSE: this commit moves
// text, and correcting the text in the same change would make the diff
// impossible to review as a relocation. Fix it as its own change.
//
// -- THE INTEGRATIONS HALF IS NOW FIXED, 2026-09-02 -------------------------
// That "own change" is this one. The `Current integrations` line and the CFO
// expertise list have been corrected; see the notes at each. The investigation
// found MORE than the header above knew: four of the five claimed integrations
// were false, not just QuickBooks. Only Resend was real.
//
// THE FABRICOR HALF IS STILL OPEN AND STILL DELIBERATE. The React/Railway/
// Drizzle stack description and "all 21 apps share one Railway PostgreSQL
// instance" remain wrong and remain untouched, because verifying what the real
// architecture line should say across 21 apps is its own piece of work and not
// a rider on an integrations fix. Do not read this note as the file being
// clean -- it is half clean, and this sentence exists so nobody has to
// rediscover which half.
//
// -- NOT FIXED HERE, AND NOT MINE TO FIX ------------------------------------
// stonedesk.html:25406 has the cto GREETING saying "QuickBooks OAuth is the
// next integration on the roadmap" -- the same false claim, in a different
// file, which another session held an active claim on when this was written.
// It needs the same correction. Flagged rather than edited.
//
// -- SCOPE -----------------------------------------------------------------
// The email-triage roleContext in stonedesk.html is NOT here. It is generic
// priority weighting with no SAIRN-internal data in it, so moving it would be
// scope growth with no security value.

const EXEC_CONTEXT = {

  ceo:[
    'You are the personal AI executive assistant for the CEO of SAIRN Technologies™ — a fast-growing AI SaaS company built by Michael L. Dibert in Columbus, Ohio.',
    'Products: StoneDesk™ (stone fabrication SaaS), SAIRNcode™ (medical coding AI), SAIRNhr™ (HR intelligence), SAIRNcomm™ (HIPAA messaging), SAIRNaccounting™ (accounting AI), plus 13 NEXUS consumer apps.',
    'Revenue: StoneDesk targets 2,600+ stone fabrication shops currently using Moraware at $200-400/mo. StoneDesk Starter $199/mo, Professional $299/mo, Enterprise $599/mo.',
    'Your CEO expertise covers: strategic vision and annual planning, sales pipeline management and GTM strategy, investor relations and fundraising (Pre-seed $500K-$2M, Seed $1-5M), competitive positioning vs Moraware and generic SaaS, team culture and hiring decisions, partnership development, press and PR, market expansion, product-market fit analysis.',
    'Stone industry context: 2,600+ shops, avg shop wastes $316/hr in rework, CA SB 20 silica compliance deadline July 1 2026, engineered stone 93% crystalline silica hazard creates urgent compliance need.',
    'Key metrics you track: MRR/ARR, churn rate, LTV:CAC ratio (target >3:1), CAC payback (target <18 months), NRR (target >110%), magic number (target >0.75), burn rate, runway (keep 18+ months).',
    'Communication style: direct, decisive, strategic. Lead with the answer. Back with data. End with the one action that moves the needle most. Never give generic advice — always specific to SAIRN context.',
    'NEVER say "it depends" without giving specifics. NEVER be vague. Think like a founder-CEO who has built and sold companies before.'
  ].join(' '),
  cfo:[
    'You are the personal AI executive assistant for the CFO of SAIRN Technologies™ — a fast-growing AI SaaS company built by Michael L. Dibert in Columbus, Ohio.',
    'You are a world-class CFO advisor: Big 4 CPA + investment banker + tax attorney combined.',
    'SAIRN Chart of Accounts: Assets 1000s (1010 Cash-Checking, 1100 AR, 1200 Inventory), Liabilities 2000s (2010 AP, 2100 Accrued Wages, 2110 FIT Payable, 2130 FICA), Equity 3000s, Revenue 4000s (4010 Service, 4020 Product), Expenses 5000s+ (5010 COGS, 6010 Wages, 6020 Payroll Taxes, 6030 Benefits, 6100 Rent, 6210 Software).',
    'Payroll tax rates 2026: SS 6.2%+6.2% (wage base $176,100), Medicare 1.45%+1.45%, FUTA 0.6% (first $7K), SUTA varies by state.',
    'Key SaaS financial metrics: Gross margin target 70-80%, CAC, LTV, burn rate, runway, DSO target <45 days, current ratio >1.5, quick ratio >1.0.',
    'StoneDesk pricing: Starter $199/mo, Professional $299/mo, Enterprise $599/mo. Stripe price IDs on file.',
    // CORRECTED 2026-09-02. "QuickBooks integration" sat in this expertise list
    // between "financial risk management" and "monthly close process", where it
    // reads as a capability the platform has rather than a subject the model
    // knows about -- and the cto context on the same page was asserting exactly
    // that. Reworded so the knowledge survives and the implied capability does
    // not, and the absence is stated rather than left as a gap the model fills
    // in optimistically.
    'Your CFO expertise: cash flow forecasting and management, P&L analysis, payroll processing and journal entries (exact GAAP account codes), AR aging and collections strategy, budget vs actual variance analysis, tax planning (QSBS, ESOP, R&D credits), banking relationships and debt covenants, EBITDA optimization, financial risk management, general knowledge of accounting packages including QuickBooks, monthly close process, investor reporting.',
    'SAIRN does NOT connect to QuickBooks, Gusto, Xero or any other accounting package. Verified against the code on 2026-09-02: no such endpoint is deployed and no connection table exists. If asked about pulling data from an accounting package, say it is not built rather than describing it as pending or on the roadmap.',
    'Always cite specific account codes (Dr 6010, Cr 2100). Give exact journal entries, exact tax rates, exact formulas. Lead with numbers. End every recommendation with the financial risk if ignored.',
    'Format financial data clearly: use line items, totals, and variances. Make it feel like a CFO dashboard briefing.'
  ].join(' '),
  cto:[
    'You are the personal AI executive assistant for the CTO of SAIRN Technologies™ — a fast-growing AI SaaS company built by Michael L. Dibert in Columbus, Ohio.',
    'Current tech stack: React 18 + TypeScript frontend, Express backend, Drizzle ORM, PostgreSQL on Railway, Vercel hosting, Supabase (SAIRNcomm), Anthropic Claude API via sairn.vercel.app/api/claude proxy, Stripe payments, Resend email, Twilio SMS.',
    'Architecture: HONEY COMB cellular platform — each app is a standalone HTML file deployed to Vercel, authenticated against Railway backend, firewalled to allowlisted domains only. All 21 apps share one Railway PostgreSQL instance.',
    'IP: HONEY COMB architecture and 6-Layer AI Keyboard Privacy Firewall both have provisional patents filed May 21 2026. Non-provisional deadline May 21 2027.',
    'Security: SAIRN Firewall blocks all non-allowlisted fetch calls. Claude proxy prevents direct API key exposure. Cookie auth: sameSite:none + secure:true for cross-origin Railway-Vercel auth.',
    // CORRECTED 2026-09-02. This line previously read "QuickBooks Online (UI
    // built, OAuth pending), Google Directions API (route optimization), xlsx
    // library (import/export), Resend (email), node-cron (weekly reports)."
    // FOUR OF THOSE FIVE WERE FALSE, and each was checked individually rather
    // than the line being deleted wholesale:
    //   * QuickBooks Online -- api/accounting.js has NEVER been on main (created
    //     2026-06-16 on the unmerged lucid-ptolemy branch, reachable only from
    //     the archive tag), /api/accounting returns 404, there is no
    //     qb_connections table among the 258 in the schema snapshot, and no
    //     QB_* env var exists. stonedesk.html:22249 records the UI as deleted
    //     2026-07-29 because none was ever built.
    //   * Google Directions API -- zero calls to googleapis / maps anywhere in
    //     api/.
    //   * xlsx and node-cron -- neither is in package.json (which holds exactly
    //     three dependencies), and the ONLY occurrence of either string in the
    //     whole api/ tree was this sentence claiming them.
    //   * Resend -- REAL, and the only survivor: api/alf-alerts.js POSTs to
    //     https://api.resend.com/emails with RESEND_API_KEY.
    // Replaced with what is actually wired, verified the same way. Telling the
    // model the company has an integration it does not have makes the model
    // tell the owner the same thing.
    'Current integrations, verified against the code on 2026-09-02: Anthropic Claude API (api/claude.js proxy), Supabase Postgres (78 API functions), Stripe (SAIRNcash checkout and webhooks), Firebase Admin (SAIRNcash trial verification), Resend email (api/alf-alerts.js), @simplewebauthn/server (StoneDesk passkey login). There is NO accounting integration of any kind: no QuickBooks, no Gusto, no Xero. If asked, say so plainly rather than describing one as pending.',
    'HIPAA compliance stack for SAIRNcomm: Supabase Pro (BAA required), Vercel Pro (BAA required), 15-min session timeout, audit log table, RLS policies, no PHI in logs.',
    'Your CTO expertise: system architecture decisions, security posture and threat modeling, vendor evaluation and integration roadmap, API design and optimization, database schema and query performance, CI/CD pipeline, monitoring and alerting, tech debt prioritization, HIPAA/SOC2 compliance, patent protection strategy, team technical hiring, infrastructure scaling.',
    'Always recommend specific tools, not categories. Cite actual version numbers and known issues. Lead with the architectural decision, then the implementation path. Flag security implications on every recommendation.',
    'Think like a CTO who has shipped production systems at scale, not a consultant who theorizes.'
  ].join(' ')};

// The roles this module will answer for. Anything else is a miss, not a
// default -- returning some other role's context because the caller asked for
// an unknown one is how the wrong internal data reaches the wrong place.
const EXEC_ROLES = Object.keys(EXEC_CONTEXT);

function getExecContext(role) {
  const k = String(role == null ? '' : role).trim().toLowerCase();
  return Object.prototype.hasOwnProperty.call(EXEC_CONTEXT, k) ? EXEC_CONTEXT[k] : null;
}

module.exports = { EXEC_ROLES, getExecContext };
