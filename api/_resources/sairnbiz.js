// api/_resources/sairnbiz.js
// Resource registry for SAIRNbiz.
//
// WHY THIS FILE EXISTS AT ALL: SAIRNbiz was the one app with a live server
// integration and NO registry module. It reached /api/sd-data through two
// resources owned by other modules -- `employees` and `shared_knowledge`,
// both in shared.js -- so nothing here was ever registered under its own
// name. See api/_resources/index.js for why each app owns its own file.
//
// -- THE BUSINESS RECORD (2026-09-04) -------------------------------------
// Closes docs/SAIRN-OPEN-WORK-INDEX.md's "No server-side persistence for
// anything except the employee roster -- and the ledger implies more data
// integrity than actually exists", size L, unassigned.
//
// MEASURED BEFORE ANYTHING WAS WRITTEN, off sairnbiz.html rather than
// estimated: the file writes SEVENTEEN localStorage collections through
// st()/ld() (plus a licence fingerprint and a trial timestamp written
// directly, which are not business records). Exactly ONE of the seventeen
// reached a server: sb_emps, via the bespoke `employees` branch. Invoices,
// expenses, AP bills, vendors, PAYROLL RUNS, training certifications,
// performance reviews, the hiring pipeline and the budget existed in one
// browser and nowhere else.
//
// WHY THAT IS WORSE HERE THAN IN A NORMAL LOCAL-ONLY APP, and it is the
// reason this row was written separately from SAIRNbuild's: SAIRNbiz posts
// real double-entry journal entries to Postgres through /api/ledger, and
// those entries are durable. A ledger row saying "Paid Ace Supply $1,234.56"
// survives a browser-data clear; the bill it settled does not. The books stay
// intact while the records that justify them are gone -- and the surviving
// half is the one that looks authoritative.
//
// The nine below are handled by the generic SB_RESOURCES read/write pair in
// api/sd-data.js -- one pair, not nine copy-pasted blocks, same shape as
// BLD_RESOURCES and LEG_RESOURCES. See sql/sairnbiz_data_schema.sql, which
// must be run before any of these answer anything but 503 NOT_PROVISIONED.
//
// NAMING: the resource name is the localStorage key verbatim. That is not
// cosmetic -- the client's sync hook keys off the storage key directly, so a
// rename here would need a mapping table on both sides to stay correct.
// Checked before writing, not assumed: no sb_* resource was registered by any
// app (259 resources, zero collisions), and the only pre-existing sb_* TABLE
// in sql/ is sb_employee_auth, which does not appear below.

module.exports = {
  app: 'sairnbiz',
  resources: [
  // Accounts receivable. Carries paid/paidDate and drives the AR aging report.
    'sb_invs',
  // Expenses. Deductible flag and receipt status -- the tax substantiation trail.
    'sb_exps',
  // Accounts payable. Bills received, balance, and whether they were settled.
    'sb_ap',
  // Vendor roster with YTD spend, terms and W-9 status.
    'sb_vends',
  // PAYROLL RUNS. Each row records that a calculation was performed, with the
  // basis it was computed on. Nothing else in the app can answer "did we run
  // payroll this period, and on what figures".
    'sb_payruns',
  // Training certifications and expiries -- OSHA 30, forklift, wet saw.
    'sb_train',
  // Performance reviews: scores, raise flags, PIP flags.
    'sb_perf',
  // Open positions and where each candidate pipeline stands.
    'sb_hire',
  // Annual budget by category, with actuals synced from recorded expenses.
    'sb_bud',
  // DELIBERATELY NOT SYNCED, and why -- so the next reader does not have to
  // re-derive the judgement or assume it was an oversight:
  //   sb_emps -- ALREADY synced, by the bespoke `employees` branch, which
  //     carries an owner/hr role gate and tenants on customer_email rather
  //     than license_hash. Folding it into the generic loop would route the
  //     roster past that gate and into a second, differently-tenanted copy.
  //   sb_co -- the company profile: a single object, not a keyed collection.
  //     The generic loop requires an array of id-bearing records. A one-row
  //     shape needs its own conflict story (two devices editing one profile)
  //     and this is not it.
  //   sb_cfg -- fiscal year / overtime rule / default payment terms. Same
  //     single-object shape as sb_co, and it is configuration rather than a
  //     business record.
  //   sb_incidents -- nothing in the app writes it after seed(). It is set to
  //     [] once and read only for a count. Syncing a collection with no write
  //     path would back up an empty array forever and read as coverage.
  //   sb_lic -- the licence key itself.
  //   sb_role -- a client-side display value. The real role comes from the
  //     session token.
  //   sb_seeded -- a local seed marker. See sairnbiz.html's sbApplyLoggedIn:
  //     hydration SETS this deliberately on a fresh device, so syncing it as
  //     a record would fight that logic.
  //   sb_sync -- a "last synced" display timestamp, local to the device.
  ],
};
