// api/_lib/sf-roles.js
//
// SAIRNfreedom role granularity: ONE data table, read by ONE function.
//
// ── WHY THIS FILE EXISTS (2026-10-13, Michael's decision (b)) ─────────────
// SAIRNfreedom had NO role distinction of any kind on its data surface. Every
// one of its 36 resources was authorised by the licence key alone until the
// gate waves of 2026-09-21 through 2026-10-13, and after those waves it was
// authorised by A SESSION OF ANY ROLE. So a chaplain's sign-in could rewrite
// the general ledger, a service officer could edit the officer roster, and the
// post had ten distinct capability roles that the server treated as one.
//
// Built on the SAIRNlaw precedent deliberately and structurally, not by
// analogy: api/_lib/law-roles.js, one table read by one `decide()`, wired at
// the gates that already existed rather than at a new call site per resource.
// That shape was chosen there because "a role check written at one call site
// and not the nineteen others is indistinguishable from no policy at all when
// read one branch at a time", and SAIRNfreedom has 36 branches rather than 19.
//
// ── THE ROLE VOCABULARY IS THE APP'S OWN AND IS NOT INVENTED HERE ──────────
// SAIRNfreedom's roles ARE its capability ids -- `post.govern`,
// `finance.write`, `chaplain.pastoral` and so on -- because an officer holds a
// capability, not a job title (titles vary per org type: a Commander, an
// Exalted Ruler, a Worthy President). The authoritative list is
// ROLES_BY_APP.sairnfreedom in api/_lib/auth.js, which api/sf-auth.js:80 reads
// to validate a provisioned role. TEN roles.
//
// ── AND THE CLIENT OFFERS AN ELEVENTH THE SERVER WILL NOT ACCEPT ───────────
// sairnfreedom.html:2314 declares `trustee.audit` in CAPABILITIES -- added
// 2026-09-27 for the VFW quarterly trustee audit, with its own written
// justification citing the VFW Manual of Procedure. It is NOT in
// ROLES_BY_APP.sairnfreedom, so api/sf-auth.js REFUSES to provision a
// credential with that role. A post can assign the capability in the Access
// panel and then cannot give that trustee a sign-in.
//
// THAT IS REPORTED AND NOT FIXED HERE, deliberately. Adding a role to
// ROLES_BY_APP is a per-app role-vocabulary decision, and this platform's own
// rules name that as the thing not to do silently -- the same reason
// api/sd-data.js twice declined to invent SAIRNlaw's paralegal policy. The
// matrix below therefore has TEN columns, and `sf_trustee_audits` is granted to
// the roles that exist. Routed in docs/2026-10-13-hank-b6-routing.md.
//
// ── WHAT IS HARD-LOCKED AND WHY IT IS NOT A ROW ───────────────────────────
// Two things, both because a default is a policy an override can erase.
'use strict';

// ── 1. THE GOVERNANCE LOCK ────────────────────────────────────────────────
// sf_officers IS THE POST'S GOVERNANCE RECORD -- who holds which office -- and
// three guards over it ran ENTIRELY IN THE BROWSER until today
// (sairnfreedom.html:2916 activeProvisioners, :2927 the SPEC 1c
// last-provisioner refusal, :2942 the sole-holder refusal). A server write past
// those guards can leave a post at ZERO ACTIVE PROVISIONERS, which is
// unrecoverable through the API -- RF-PINNACLE-2026 is the live instance of
// that state. docs/CRITICALITY-TIERS.md:365 carries it A on integrity.
//
// Writing the roster is therefore PROVISIONING-CLASS authority and is locked to
// the two provisioning capabilities, checked separately from the table so an
// override layer that forgets the lock still cannot open it.
const SF_GOVERNANCE_LOCKED = Object.freeze(Object.assign(Object.create(null), {
  sf_officers: true
}));

// ── 2. THE MONEY LOCK ─────────────────────────────────────────────────────
// The general ledger, the chart of accounts and the two ORC Chapter 2915 payee
// records. `finance.write` is "Finance (bonded)" in the app's own words -- a
// bonded office -- so these are owner/deputy/finance and nothing else, locked
// rather than merely defaulted. A post whose chaplain can write a disbursement
// row has an ORC 2915.10 problem, not a UX problem.
const SF_MONEY_LOCKED = Object.freeze(Object.assign(Object.create(null), {
  sf_ledger: true,
  sf_accounts: true,
  sf_disbursements: true,
  sf_gaming_expenses: true
}));

const PROVISIONING = ['post.govern', 'post.govern.deputy'];
const FINANCE = ['post.govern', 'post.govern.deputy', 'finance.write'];

// ── THE TABLE. 36 ROWS, ONE PER RESOURCE, NO RESOURCE WITHOUT A ROW ───────
// Values are the ACTIONS each role may take: 'rw', 'r', or '' for none.
//
// THE POLICY IS DERIVED FROM THE CAPABILITY LABELS THE APP ITSELF SHIPS, and
// every row says which. That is the only honest basis available: nobody has
// handed down a 36x10 grid, and inventing one silently is what this file's
// SAIRNlaw ancestor refused to do. Where a resource is not inside any
// capability's stated scope the non-governing roles get READ and not write --
// READ because this is one post's own records and a member-facing officer
// genuinely needs to see the roster, the calendar and the inventory to do the
// job the capability names; NOT WRITE because write is where the integrity
// tier lives.
//
// THE TWO GOVERNING ROLES ARE 'rw' ON EVERYTHING. That is a decision and not an
// oversight: `post.govern` is the post commander and `post.govern.deputy` the
// vice. A governance structure where the commander cannot correct a record is
// not a safety property, it is a support ticket -- and it is the same shape
// SAIRNlaw's matrix uses for owner and attorney.
//
// `why` IS NOT DECORATION. It names the capability label the grant comes from,
// so a reviewer checks a mapping rather than re-deriving a policy.
// NOT FROZEN ON THIS LINE ANY MORE. The eleventh column is DERIVED below the
// literal (see THE ELEVENTH COLUMN IS DERIVED), so the freeze moved to after
// that derivation. It is still frozen before anything can require() this file --
// rows first, then the table.
const SF_ROLE_MATRIX = Object.assign(Object.create(null), {
  // ── GOVERNANCE: the roster itself. Locked above as well. ────────────────
  sf_officers: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'r', 'member.admit': 'r',
    'services.refer': 'r', 'legal.review': 'r', 'history.write': 'r',
    'ceremonial.manage': 'r', 'chaplain.pastoral': 'r',
    why: 'GOVERNANCE -- who holds which office. Write is provisioning-class and hard-locked; every officer may READ the roster because the app renders it on the dashboard.' },

  // ── MONEY: owner / deputy / finance.write ("Finance (bonded)"). Locked. ──
  sf_ledger: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'MONEY -- the general ledger. finance.write is a BONDED office by the app own label. legal.review reads it for bylaws and disputes.' },
  sf_accounts: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'MONEY -- the chart of accounts every ledger line posts to.' },
  sf_disbursements: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'MONEY -- an ORC 2915.10(A)(2) charitable disbursement: payee name and amount.' },
  sf_gaming_expenses: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'MONEY -- an ORC 2915.10(C) gaming expense: payee name and amount.' },

  // ── THE GAMING FLOOR: money on the row, finance plus governance. ────────
  sf_sessions: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'GAMING -- prizeCap is a STATUTORY limit under ORC Chapter 2915, plus receipts and prizes. records.write keeps the session record; finance reconciles it.' },
  sf_tickets: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': 'r',
    'services.refer': '', 'legal.review': '', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'GAMING -- a sale at a snapshotted price against a named member. member.admit reads it to see a member activity.' },
  sf_shifts: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'GAMING -- a CASH VARIANCE attributed to a NAMED employee. Tier A on confidentiality as well as integrity, so the reader set is narrow.' },
  sf_rentals: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': 'r',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'MONEY -- a hall rental charge and proceeds, plus the alcohol/notified compliance pair. legal.review reads the compliance pair.' },
  sf_operators: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'r', 'member.admit': '',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'GAMING + SHARPEST PII -- a named volunteer DOB with FELONY and GAMBLING disqualification flags, behind a statutory eligibility gate citing ORC 2915.09. Write is governance-only; the reader set is deliberately the narrowest in this table.' },
  sf_permit_flags: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': '',
    'services.refer': '', 'legal.review': 'rw', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'COMPLIANCE -- gaming permit state. legal.review is "Bylaws and disputes" and this is the regulatory half of that.' },

  // ── MEMBERSHIP AND PEOPLE: member.admit is "Admit members". ─────────────
  sf_members: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': 'rw',
    'services.refer': 'r', 'legal.review': 'r', 'history.write': 'r',
    'ceremonial.manage': 'r', 'chaplain.pastoral': 'r',
    why: 'MEMBERSHIP -- member.admit by its own label. Broad read: a chaplain and a service officer both need to find a member.' },
  sf_staff: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': 'r',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'PEOPLE -- carries a DOB the app age-gates off. records.write keeps personnel records; the reader set stays narrow because of the DOB.' },
  sf_youth_participants: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': '', 'member.admit': 'r',
    'services.refer': 'r', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': 'r', 'chaplain.pastoral': 'r',
    why: 'MINORS. Write is records.write and governance only. ceremonial.manage and chaplain.pastoral read because youth programmes are run through both.' },
  sf_waivers: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': '', 'member.admit': 'r',
    'services.refer': 'r', 'legal.review': 'rw', 'history.write': '',
    'ceremonial.manage': 'r', 'chaplain.pastoral': 'r',
    why: 'HEALTH + MILITARY STATUS disclosure. legal.review writes because a waiver is an instrument; chaplain reads for pastoral contact.' },
  sf_signatures: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': '',
    'services.refer': '', 'legal.review': 'rw', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'A REUSABLE INSTRUMENT -- a named signer, their typed signature and the governance document it binds them to. Can be lifted off one document and re-applied to another, so the write set is governance, records and legal only.' },
  sf_donations: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'rw', 'member.admit': 'r',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'MONEY + DONOR IDENTITY -- donor name and amount. finance writes it.' },
  sf_donor_awards: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': 'r',
    'services.refer': '', 'legal.review': '', 'history.write': 'r',
    'ceremonial.manage': 'r', 'chaplain.pastoral': '',
    why: 'THIS PERSON GAVE AT LEAST THIS MUCH -- the same disclosure sf_donations was gated for. ceremonial.manage reads it because awards are presented.' },
  sf_donor_tiers: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': 'r',
    'services.refer': '', 'legal.review': '', 'history.write': 'r',
    'ceremonial.manage': 'r', 'chaplain.pastoral': '',
    why: 'No person on the row. Gated only so an awards row opaque tierId cannot be resolved back to an amount -- defence in depth, per its own gate comment.' },

  // ── SERVICE OFFICER: "Service officer (referral only)". ─────────────────
  sf_service_appointments: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': '', 'member.admit': 'r',
    'services.refer': 'rw', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': 'r',
    why: 'A member tied to a VA-adjacent referral outcome. services.refer by its own label.' },
  sf_service_referrals: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': '', 'member.admit': 'r',
    'services.refer': 'rw', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': 'r',
    why: 'services.refer -- the referral record itself.' },
  sf_service_hours: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': 'r',
    'services.refer': 'rw', 'legal.review': '', 'history.write': 'r',
    'ceremonial.manage': 'r', 'chaplain.pastoral': 'r',
    why: 'Volunteer hours. Broad because every capability logs its own programme hours.' },

  // ── RECORDS AND MINUTES: records.write by its own label. ────────────────
  sf_documents: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': 'r',
    'services.refer': 'r', 'legal.review': 'rw', 'history.write': 'r',
    'ceremonial.manage': 'r', 'chaplain.pastoral': 'r',
    why: 'records.write -- "Records and minutes". legal.review writes because bylaws live here.' },
  sf_events: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': 'r',
    'services.refer': 'r', 'legal.review': '', 'history.write': 'r',
    'ceremonial.manage': 'rw', 'chaplain.pastoral': 'r',
    why: 'The post calendar. ceremonial.manage writes because ceremonies ARE events.' },
  sf_trustee_audits: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'r', 'member.admit': '',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'THE QUARTERLY FINANCIAL-CONTROLS ATTESTATION and the fidelity bond covering whoever handles gaming receipts. THE CAPABILITY THAT SHOULD WRITE THIS -- trustee.audit -- IS NOT A SERVER ROLE (see this file header), so write is governance-only and finance.write gets READ ONLY, NOT write: the VFW rule the client cites is that the Quartermaster must not prepare the audit. Granting finance write here would encode the opposite of the source.' },
  sf_district_imports: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': 'r',
    'services.refer': '', 'legal.review': 'r', 'history.write': 'r',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'Records arriving from the district. records.write keeps them.' },
  sf_national_categories: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': 'r',
    'services.refer': 'r', 'legal.review': 'r', 'history.write': 'rw',
    'ceremonial.manage': 'r', 'chaplain.pastoral': 'r',
    why: 'National reporting categories. history.write writes because national reporting is the historian own work.' },
  sf_honor_details: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': '', 'member.admit': 'r',
    'services.refer': 'r', 'legal.review': '', 'history.write': 'rw',
    'ceremonial.manage': 'rw', 'chaplain.pastoral': 'rw',
    why: 'Honor guard details. ceremonial.manage, chaplain.pastoral and history.write are exactly the three capabilities this concerns.' },
  sf_ceremonial_items: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'r', 'member.admit': '',
    'services.refer': '', 'legal.review': '', 'history.write': 'r',
    'ceremonial.manage': 'rw', 'chaplain.pastoral': 'r',
    why: 'ceremonial.manage -- "Ceremonial and honor guard".' },

  // ── CANTEEN, INVENTORY, VEHICLES: operations. ──────────────────────────
  sf_products: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': 'r',
    'services.refer': '', 'legal.review': '', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'The priced catalogue every ticket snapshots from -- money on the row, so write is finance and records.' },
  sf_vendor_prices: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'r', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': '', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'Supplier pricing -- commercially sensitive and money. finance writes.' },
  sf_vendors: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'Supplier records -- name and terms for whoever the canteen buys from. Commercially sensitive rather than personal; legal.review reads it because a supply dispute is a bylaws matter.' },
  sf_inventory_counts: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': '', 'history.write': '',
    'ceremonial.manage': 'r', 'chaplain.pastoral': '',
    why: 'Stock counts feeding the canteen reconciliation.' },
  sf_bottle_fills: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'rw', 'member.admit': '',
    'services.refer': '', 'legal.review': '', 'history.write': '',
    'ceremonial.manage': '', 'chaplain.pastoral': '',
    why: 'Bar pour tracking, an input to the canteen variance.' },
  sf_vehicles: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': '',
    'services.refer': 'r', 'legal.review': 'r', 'history.write': '',
    'ceremonial.manage': 'r', 'chaplain.pastoral': '',
    why: 'Post vehicles -- the van that drives veterans to appointments, which is why services.refer and ceremonial.manage read it.' },
  sf_vehicle_service: { 'post.govern': 'rw', 'post.govern.deputy': 'rw',
    'records.write': 'rw', 'finance.write': 'r', 'member.admit': '',
    'services.refer': 'r', 'legal.review': '', 'history.write': '',
    'ceremonial.manage': 'r', 'chaplain.pastoral': '',
    why: 'THE ONLY THING THAT ADVANCES THE ODOMETER sf_vehicles computes its service-due flag from -- A on integrity for exactly that reason.' }
});

// ── THE ELEVENTH COLUMN IS DERIVED, NOT TRANSCRIBED (2026-10-13) ───────────
// MICHAEL'S DECISION: a VFW post trustee gets their own login, VIEW-ONLY ON
// FINANCIAL RECORDS. `trustee.audit` is now in ROLES_BY_APP.sairnfreedom and in
// the employee_auth CHECK, so a trustee can hold a real session -- and
// decide() DENIES any role without a cell, so without this the eleventh role
// would have inherited nothing and the login would have been useless.
//
// THIRTY-SIX CELLS WERE NOT HAND-WRITTEN, AND THAT IS THE POINT RATHER THAN A
// SHORTCUT. "View-only on financial records" is one sentence; transcribing it
// into 36 cells makes 36 chances to disagree with it, and nothing afterwards
// could tell a deliberate exception from a typo. So the column is COMPUTED from
// the one thing in this file that already defines what a financial record IS in
// this app:
//
//   THE RULE: trustee.audit READS exactly what the bonded finance office may
//   WRITE. Every row where `finance.write` is 'rw' -> 'r'. Everything else ->
//   '' (no access). Plus ONE named exception below.
//
// WHY THAT IS THE RIGHT SOURCE and not merely a convenient one: `finance.write`
// is "Finance (bonded)" in the app's own capability label, and the rows it may
// write are the rows the post's money passes through -- the ledger, the chart of
// accounts, the two ORC 2915 payee records, the gaming floor, donations, and the
// bar/retail chain that produces the takings those records reconcile against.
// That IS the audit surface a quarterly trustee audit covers. Sixteen rows at
// the time of writing; the figure is not written anywhere because the rule
// yields it.
//
// THE ONE EXCEPTION, AND IT IS THE TRUSTEE'S OWN RECORD: `sf_trustee_audits`
// gets 'rw'. The trustee is individually liable for producing the quarterly
// audit, so read-only on the document they themselves must file would make the
// login decorative. Note what is NOT changed by it: `finance.write` stays 'r'
// on that row, deliberately, because the VFW Manual of Procedure is explicit
// that the Quartermaster must not prepare the audit.
//
// WHAT A TRUSTEE DELIBERATELY CANNOT SEE, stated so it reads as a decision: the
// member roster, minors' names, the felony and gambling-disqualification flags
// on sf_operators, health and military status on waivers, and the VA-adjacent
// referral records. Michael's decision was about financial records. The other
// non-governing roles get 'r' on those rows because their capability's stated
// scope covers them; a trustee's does not, so the derivation gives '' and no
// separate argument is needed.
//
// IF THE DECISION CHANGES, ONE RULE CHANGES. That is the methodology half of
// this batch: a role's scope is derived from a single source, and
// api/sd-data-sf-role-matrix.test.js re-derives the same expectation
// independently, so a hand-edit to any cell here would fail rather than pass
// quietly.
const TRUSTEE = 'trustee.audit';
const TRUSTEE_RW = Object.freeze(['sf_trustee_audits']);
Object.keys(SF_ROLE_MATRIX).forEach(function (resource) {
  const row = SF_ROLE_MATRIX[resource];
  row[TRUSTEE] = TRUSTEE_RW.indexOf(resource) !== -1
    ? 'rw'
    : (row['finance.write'] === 'rw' ? 'r' : '');
});
// FROZEN AFTER the column is added, not before: freezing the literal would have
// made this loop a silent no-op in non-strict code and a throw in strict code,
// and the silent half is the one worth engineering against.
Object.keys(SF_ROLE_MATRIX).forEach(function (r) { Object.freeze(SF_ROLE_MATRIX[r]); });
Object.freeze(SF_ROLE_MATRIX);

const ALLOW = 'ALLOW';
const DENY = 'DENY';
const NOT_SF = 'NOT_SF';

/**
 * The one function. (resource, role, action) -> ALLOW | DENY | NOT_SF.
 *
 * FAILS CLOSED IN EVERY DIRECTION, and each one is a real shape this platform
 * has already been bitten by:
 *  - an sf_ resource with NO ROW          -> DENY. The table is the policy; a
 *    resource nobody wrote a rule for is not allowed by default, which is the
 *    state this file exists to end. A 37th sf_ resource gets nothing, loudly.
 *  - a role not in the row                -> DENY. An 11th role added to
 *    ROLES_BY_APP without a column here inherits nothing rather than inheriting
 *    post.govern's access.
 *  - an absent or empty role              -> DENY.
 *  - any action that is not 'read'        -> WRITE-class, so a future verb
 *    cannot arrive on a read grant.
 *  - a GOVERNANCE- or MONEY-locked resource -> DENY unless the role is in the
 *    lock, checked AFTER the table agrees so an override layer that edits the
 *    table still cannot open the lock.
 */
function decide(resource, role, action) {
  if (!resource || !Object.prototype.hasOwnProperty.call(SF_ROLE_MATRIX, resource)) {
    return String(resource || '').indexOf('sf_') === 0 ? DENY : NOT_SF;
  }
  const row = SF_ROLE_MATRIX[resource];
  const grant = (role && Object.prototype.hasOwnProperty.call(row, role))
    ? String(row[role] || '')
    : '';
  const wantsWrite = (action !== 'read');
  const allowed = wantsWrite ? (grant === 'rw') : (grant === 'rw' || grant === 'r');
  if (!allowed) return DENY;
  if (wantsWrite && SF_GOVERNANCE_LOCKED[resource]
      && PROVISIONING.indexOf(role) === -1) return DENY;
  if (wantsWrite && SF_MONEY_LOCKED[resource]
      && FINANCE.indexOf(role) === -1) return DENY;
  return ALLOW;
}

/** Every resource the table covers. Used by the matrix test, not the handler. */
function resources() { return Object.keys(SF_ROLE_MATRIX); }

/** The refusal a caller sees. One sentence, no policy dump. */
function denyMessage(resource, role) {
  if (SF_GOVERNANCE_LOCKED[resource]) {
    return 'The officer roster is governance-only -- a Commander or Vice '
         + 'Commander (or your post equivalent) must make this change';
  }
  if (SF_MONEY_LOCKED[resource]) {
    return 'Post financial records are available to governance and the bonded '
         + 'finance officer only';
  }
  return 'Your office (' + String(role || 'unknown') + ') does not have access '
       + 'to this record';
}

module.exports = {
  SF_ROLE_MATRIX, SF_GOVERNANCE_LOCKED, SF_MONEY_LOCKED,
  PROVISIONING, FINANCE,
  ALLOW, DENY, NOT_SF,
  decide, resources, denyMessage
};
