// api/_lib/dental-bi.js
// ---------------------------------------------------------------------------
// SAIRNdental B5 -- open BI / data-warehouse feed. PURE LOGIC ONLY.
// The HTTP half is api/dnt-bi.js. Not routed by Vercel (leading underscore),
// same convention as every other api/_lib file.
//
// WHAT THE GAP ASKED FOR AND WHAT THIS IS
// The 2026-08-26 competitive audit, SAIRNdental B5: "Open BI / data-warehouse
// connectors -- tab32 Summit's Tableau/Power BI/Looker connectors are a genuine
// Tier B differentiator. Absent. CSV export only." Re-derived and still OPEN as
// of docs/2026-09-02-competitive-gap-status-rederived.md.
//
// This is a GENERIC POLLABLE READ-ONLY FEED, not a Power BI-specific connector.
// A real Power BI custom connector is a signed .mez artifact with its own
// distribution, versioning and gateway story, and it would serve exactly one of
// the three tools the gap names. All three -- Power BI's Web source, Tableau's
// Web Data Connector, Looker Studio's community connectors -- read paginated
// JSON from a URL. So the feed IS the connector.
//
// -- THE FEED SHIPS FACTS, NOT DERIVED METRICS. THIS IS DELIBERATE. --
// sairndental.html's DNT_EXPORTS carries columns like "Appeal deadline",
// "Due by", "Standing" and "Patient portion". Every one of those is computed by
// an engine that runs IN THE BROWSER (dnAppealWindow, gfeDeadline, rcRows,
// tpPlanTotals). Reimplementing them here would create a second implementation
// of the same rule, reachable by a different door, free to drift -- and the
// drift would surface as a practice's dashboard disagreeing with its own app
// about a federal deadline. So the feed carries STORED fields, typed and
// flattened, and the analyst models on top of them. That is also what a
// warehouse connector is FOR: give me the facts, I will build the measures.
//
// Anything a BI tool cannot derive from these columns is a gap in this file and
// should be closed by promoting the underlying FIELD, never by porting the
// derivation.
//
// -- THE FEED CANNOT SEE MORE THAN THE PERSON WHO MINTED IT --
// api/sd-data.js enforces two independent read gates on dental data:
//   1. FINANCIAL TIER  -- dnt_charges/payments/denial/ar/revenue/coverage_rules/
//      txplans/gfe are readable only by {owner, frontdesk} (sd-data.js:8063).
//   2. PROVIDER SCOPE  -- patient-bearing resources are filtered to the
//      requesting provider's own patients unless the role is {owner, frontdesk}
//      (sd-data.js:8103, :8352).
// A BI token that ignored either would be a complete authorisation bypass
// wearing a reporting label. Both gates are reimplemented here against the SAME
// role names, and datasetsForRole()/scopeFor() exist so a test can assert the
// two agree. If sd-data.js's tiers ever change, THIS FILE IS A COPY THAT MUST
// BE CORRECTED WITH IT -- the same relationship sd-data.js's own
// DNT_MANAGEMENT_ROLES declares toward api/dnt-auth.js.
//
// The role is NOT snapshotted into the token. api/dnt-bi.js re-reads it from
// sairndental_employee_auth on every request, so a demoted or deactivated
// employee's feed stops at their next poll rather than at their token's expiry.
// A snapshot would be the stale-credential shape this platform already has a
// standing rule about.
//
// -- PHI IS OFF BY DEFAULT AND JOINS STILL WORK --
// dnt_patients carries name, date of birth, phone, email, insurance member ID
// and guardian contact details. A warehouse almost never needs any of it: the
// analytics are per-patient, not about the patient. So every column carrying a
// direct identifier is marked phi:true and is OMITTED unless the token was
// explicitly minted with identifiers included -- and every patient-bearing row
// carries patient_key, a stable pseudonym, so patients/appointments/charges
// still join without a single name leaving the building.
//
// The projection is a BUILDER, not a delete-list. A column reaches the output
// only by being named in a dataset definition, so a field added to the jsonb
// blob later cannot leak by default. Same construction as
// api/_lib/stonedesk-public.js's publicSlabView, for the same reason.
// ---------------------------------------------------------------------------

const crypto = require('crypto');

// -- ROLE GATES: mirrors of api/sd-data.js. Change both or neither. ---------
const FINANCIAL_ROLES = { owner: true, frontdesk: true };
const PATIENT_BROAD_READ_ROLES = { owner: true, frontdesk: true };

// -- TYPE COERCION ----------------------------------------------------------
// A CSV hands a BI tool text and lets it guess; guessing is how a practice ends
// up with "12.50" sorting before "9.00". Declared types are coerced here so the
// JSON a tool receives is already the right primitive.
//
// An unparseable value becomes null, NEVER 0 or "". A zero collection day and a
// day nobody recorded are different facts, and a feed that reports the second
// as the first is fabricating data at the point it is hardest to notice.
function coerce(type, v) {
  if (v === undefined || v === null || v === '') return null;
  switch (type) {
    case 'number': {
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    }
    case 'boolean': {
      if (typeof v === 'boolean') return v;
      const s = String(v).toLowerCase();
      if (s === 'true' || s === 'yes' || s === '1') return true;
      if (s === 'false' || s === 'no' || s === '0') return false;
      return null;
    }
    case 'date': {
      // Date-only, kept as the ISO calendar date it was stored as. Deliberately
      // NOT passed through new Date() -- that would reinterpret "2026-09-02" as
      // UTC midnight and hand a BI tool in a negative-offset timezone the day
      // before. The same UTC-vs-local defect was fixed in two SAIRN apps on
      // 2026-09-02; it is not being reintroduced in the reporting layer.
      const s = String(v).slice(0, 10);
      return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null;
    }
    case 'datetime': {
      const t = new Date(v);
      return Number.isNaN(t.getTime()) ? null : t.toISOString();
    }
    default:
      return String(v);
  }
}

// -- PATIENT PSEUDONYM ------------------------------------------------------
// Stable for a given (practice, patient) so joins and period-over-period
// comparisons hold. HMAC keyed on a server secret AND salted with the practice's
// own license hash, so the same patient id at two practices does not collide,
// and the mapping cannot be reversed by anyone holding only the feed.
//
// NOT a HIPAA de-identification safe harbour on its own. It removes the direct
// identifiers this feed would otherwise carry; the remaining rows are still a
// limited data set about real people and are still the practice's to protect.
// Said plainly here so nobody reads "pseudonymised" as "no longer PHI".
function patientKey(licenseHash, patientId, secret) {
  if (patientId === undefined || patientId === null || patientId === '') return null;
  return crypto.createHmac('sha256', String(secret || 'dental-bi-fallback-key'))
    .update(String(licenseHash || '') + '|' + String(patientId))
    .digest('hex').slice(0, 24);
}

// -- DATASETS ---------------------------------------------------------------
// col: [name, type, path, phi?]
//   path -- a key on the row's jsonb blob, or a function(row, ctx).
//   phi  -- a DIRECT identifier. Omitted entirely unless includeIdentifiers.
//
// EVERY PATH BELOW WAS READ OFF THE WRITER, NOT GUESSED. A path that does not
// exist coerces to null silently, which would put a column of blanks in a
// practice's dashboard and read as "we have no data" rather than "this feed is
// wrong" -- so each dataset names the function that mints its rows, and that is
// the thing to re-read if a column ever comes back empty. The first draft of
// this file had six invented columns on dnt_charges alone.
//
// created_at is a DATE, not a timestamp, on every client-written resource:
// they are all stamped dntLocalToday(). Typing it 'datetime' would invent a
// midnight that was never recorded.
//
// Free-text `note` fields are deliberately absent from every dataset. They
// carry no dimension a report groups by and are the likeliest place for a
// clinician to have typed something about a person.
const DATASETS = {
  // sairndental.html addPatient() -- newId('PT')
  patients: {
    resource: 'dnt_patients',
    label: 'Patients',
    grain: 'One row per patient on file.',
    financial: false,
    patientScoped: true,
    scopeKey: 'id',
    columns: [
      ['patient_key', 'string', (r, c) => patientKey(c.licenseHash, r.id, c.secret)],
      ['name', 'string', 'name', true],
      ['date_of_birth', 'date', 'dob', true],
      ['phone', 'string', 'phone', true],
      ['email', 'string', 'email', true],
      ['insurance_payer', 'string', 'insurance_payer'],
      ['insurance_member_id', 'string', 'insurance_member_id', true],
      ['insurance_plan_type', 'string', 'insurance_plan_type'],
      ['has_guardian', 'boolean', (r) => !!r.guardian_name],
      ['guardian_name', 'string', 'guardian_name', true],
      ['guardian_relationship', 'string', 'guardian_relationship'],
      // 0 is this form's "not set" for the override, so it reports null rather
      // than a zero-month recall interval, which is not a thing.
      ['recall_months_override', 'number', (r) => (Number(r.recall_months_override) || null)],
      ['location_id', 'string', 'location_id'],
      ['created_at', 'date', 'created_at']
    ]
  },
  // sairndental.html addProvider() -- newId('PV')
  providers: {
    resource: 'dnt_providers',
    label: 'Providers',
    grain: 'One row per provider in the practice registry.',
    financial: false,
    patientScoped: false,
    columns: [
      ['provider_id', 'string', 'id'],
      // A provider row is about a clinician, not a patient. Their name is how
      // every productivity report is read and is not a patient identifier, so
      // it is not marked phi.
      ['name', 'string', 'name'],
      ['role', 'string', 'role'],
      ['operatory_id', 'string', 'operatory_id'],
      // WHETHER a login is linked is an access-control fact worth reporting.
      // WHICH login is not, and never leaves this function.
      ['is_linked_to_login', 'boolean', (r) => !!r.linked_employee_id],
      ['active', 'boolean', (r) => r.active !== false],
      ['location_id', 'string', 'location_id'],
      ['created_at', 'date', 'created_at']
    ]
  },
  // sairndental.html addOperatory() -- newId('OP')
  operatories: {
    resource: 'dnt_operatories',
    label: 'Operatories',
    grain: 'One row per treatment room.',
    financial: false,
    patientScoped: false,
    columns: [
      ['operatory_id', 'string', 'id'],
      ['name', 'string', 'name'],
      // Stamped server-side by dnt-location.stampLocation on write. Rows written
      // before that shipped have none and report null rather than being
      // back-filled with a default this feed would be inventing.
      ['location_id', 'string', 'location_id'],
      ['created_at', 'date', 'created_at']
    ]
  },
  // sairndental.html addProcedureType() -- newId('PC')
  procedure_types: {
    resource: 'dnt_procedure_types',
    label: 'Procedure types',
    grain: 'One row per CDT procedure this practice performs.',
    financial: false,
    patientScoped: false,
    columns: [
      ['procedure_type_id', 'string', 'id'],
      ['cdt_code', 'string', 'cdt_code'],
      ['description', 'string', 'description'],
      ['default_fee', 'number', 'default_fee'],
      ['default_length_minutes', 'number', 'default_length_minutes'],
      // The CDT versioning fields (audit item A4). A code's meaning changes
      // between CDT years, so a report that trends one code across years
      // without them is comparing two different procedures.
      ['cdt_version', 'string', 'cdt_version'],
      ['effective_from', 'date', 'effective_from'],
      ['effective_to', 'date', 'effective_to'],
      ['superseded_by', 'string', 'superseded_by'],
      ['recall_months', 'number', (r) => (Number(r.recall_months) || null)],
      ['created_at', 'date', 'created_at']
    ]
  },
  // api/sairndental/public-book.js and sairndental.html's staff scheduling.
  // NOTE: no created_at -- appointment rows have never carried one. start_time
  // is the date a scheduling report actually wants anyway.
  appointments: {
    resource: 'dnt_appointments',
    label: 'Appointments',
    grain: 'One row per scheduled appointment. The scheduling fact table.',
    financial: false,
    patientScoped: true,
    scopeKey: 'patient_id',
    // Filtered in the DATABASE on the promoted provider_id column for a scoped
    // role, exactly as api/sd-data.js:8352 does -- an appointment blob can carry
    // patient photos up to ~1.26 MB, so reading the practice to discard most of
    // it would be both a privacy and a payload problem.
    providerColumn: 'provider_id',
    columns: [
      ['appointment_id', 'string', 'id'],
      ['patient_key', 'string', (r, c) => patientKey(c.licenseHash, r.patient_id, c.secret)],
      ['provider_id', 'string', 'provider_id'],
      ['operatory_id', 'string', 'operatory_id'],
      ['procedure_type_id', 'string', 'procedure_type_id'],
      ['start_time', 'datetime', 'start_time'],
      ['end_time', 'datetime', 'end_time'],
      ['status', 'string', 'status'],
      // 'self-scheduled' or 'staff'. Self-booking conversion is one of the few
      // things this feed can answer that the app's own panels cannot.
      ['source', 'string', (r) => r.source || 'staff'],
      ['location_id', 'string', 'location_id'],
      // Photo BYTES are never in the feed -- a warehouse has no use for them and
      // they are clinical images of a person. Whether any exist is the fact a
      // report actually asks for. patient_notes is excluded for the same reason
      // as every other free-text field.
      ['photo_count', 'number', (r) => (Array.isArray(r.photos) ? r.photos.length : 0)]
    ]
  },
  // sairndental.html addChargeEntry() -- newId('CH'). Deliberately thin: this
  // record carries no cdt_code, provider or payer of its own. Join
  // procedure_type_id to procedure_types for the code, and appointment_id to
  // appointments for the provider. Saying so beats shipping four columns of
  // nulls that look like missing data.
  charges: {
    resource: 'dnt_charges',
    label: 'Charges',
    grain: 'One row per posted charge. The production fact table.',
    financial: true,
    patientScoped: false,
    columns: [
      ['charge_id', 'string', 'id'],
      ['patient_key', 'string', (r, c) => patientKey(c.licenseHash, r.patient_id, c.secret)],
      ['appointment_id', 'string', 'appointment_id'],
      ['procedure_type_id', 'string', 'procedure_type_id'],
      ['amount', 'number', 'amount'],
      // What the app ESTIMATED insurance would cover when the charge was posted.
      // An estimate, stored -- not what a payer actually paid, which is in
      // payments. The column name says estimated for that reason.
      ['estimated_insurance_portion', 'number', 'estimated_insurance_portion'],
      ['charge_date', 'date', 'date'],
      ['location_id', 'string', 'location_id']
    ]
  },
  // sairndental.html addPaymentEntry() -- newId('PM')
  payments: {
    resource: 'dnt_payments',
    label: 'Payments',
    grain: 'One row per payment received. The collections fact table.',
    financial: true,
    patientScoped: false,
    columns: [
      ['payment_id', 'string', 'id'],
      ['patient_key', 'string', (r, c) => patientKey(c.licenseHash, r.patient_id, c.secret)],
      ['amount', 'number', 'amount'],
      ['method', 'string', 'method'],
      ['payment_date', 'date', 'date'],
      ['location_id', 'string', 'location_id']
    ]
  },
  // sairndental.html saveDenial() -- newId('DN')
  denials: {
    resource: 'dnt_denial',
    label: 'Denials and appeals',
    grain: 'One row per payer denial, with the appeal stage as recorded.',
    financial: true,
    patientScoped: true,
    scopeKey: 'patient_id',
    columns: [
      ['denial_id', 'string', 'id'],
      ['patient_key', 'string', (r, c) => patientKey(c.licenseHash, r.patient_id, c.secret)],
      ['charge_id', 'string', 'charge_id'],
      ['payer', 'string', 'payer'],
      ['denied_on', 'date', 'denied_on'],
      // The payer's code and reason AS GIVEN. Not normalised here, because
      // normalising would silently merge two payers' different meanings for the
      // same string.
      ['code', 'string', 'code'],
      ['reason', 'string', 'reason'],
      ['amount_denied', 'number', 'amount'],
      ['stage', 'string', 'stage'],
      ['submitted_on', 'date', 'submitted_on'],
      ['decided_on', 'date', 'decided_on'],
      ['recovered', 'number', 'recovered'],
      ['created_at', 'date', 'created_at']
      // NO appeal_deadline column. dnAppealWindow() computes it in the browser
      // from this practice's payer terms; a second copy here could disagree with
      // the app about when a payer's window shuts. Ship payer + denied_on and
      // let the model derive it once.
    ]
  },
  // sairndental.html saveTxPlan() -- newId('TP')
  treatment_plans: {
    resource: 'dnt_txplans',
    label: 'Treatment plans',
    grain: 'One row per proposed plan. Case-acceptance analysis starts here.',
    financial: true,
    patientScoped: true,
    scopeKey: 'patient_id',
    columns: [
      ['txplan_id', 'string', 'id'],
      ['patient_key', 'string', (r, c) => patientKey(c.licenseHash, r.patient_id, c.secret)],
      ['provider_id', 'string', 'provider_id'],
      ['title', 'string', 'title'],
      ['status', 'string', 'status'],
      ['decided_on', 'date', 'decided_on'],
      ['item_count', 'number', (r) => (Array.isArray(r.items) ? r.items.length : 0)],
      // The stored per-item fees, summed. NOT tpPlanTotals(): that also derives
      // an insurance estimate from coverage rules, which is a modelled figure
      // and belongs in the model. A plan with no items reports null, not 0 -- an
      // empty plan has no fee, it does not have a fee of nothing.
      ['total_fee', 'number', (r) => (Array.isArray(r.items) && r.items.length
        ? r.items.reduce((t, it) => t + (Number(it && it.fee) || 0), 0)
        : null)],
      ['created_at', 'date', 'created_at']
    ]
  },
  // sairndental.html saveRecallOutreach() -- newId('RC')
  recall_outreach: {
    resource: 'dnt_recall_outreach',
    label: 'Recall outreach',
    grain: 'One row per contact actually made about a patient being due back.',
    financial: false,
    patientScoped: true,
    scopeKey: 'patient_id',
    columns: [
      ['outreach_id', 'string', 'id'],
      ['patient_key', 'string', (r, c) => patientKey(c.licenseHash, r.patient_id, c.secret)],
      ['procedure_type_id', 'string', 'procedure_type_id'],
      ['contacted_on', 'date', 'on'],
      ['channel', 'string', 'channel'],
      ['outcome', 'string', 'outcome'],
      ['created_at', 'date', 'created_at']
    ]
  },
  // sairndental.html addReferral() -- newId('RF')
  referrals: {
    resource: 'dnt_referrals',
    label: 'Referrals',
    grain: 'One row per referral in or out.',
    financial: false,
    patientScoped: true,
    scopeKey: 'patient_id',
    columns: [
      ['referral_id', 'string', 'id'],
      ['patient_key', 'string', (r, c) => patientKey(c.licenseHash, r.patient_id, c.secret)],
      // Free-typed on the form and often filled in for someone with no patient
      // record yet, so it is a direct identifier in its own right rather than a
      // duplicate of the patients table.
      ['patient_name', 'string', 'patient_name', true],
      ['direction', 'string', 'direction'],
      ['referral_date', 'date', 'date'],
      // The practice or clinician on the other end -- an organisation, not a
      // patient. It is the dimension the whole referral report groups by.
      ['external_party', 'string', 'external_party'],
      ['internal_provider_id', 'string', 'internal_provider_id'],
      ['reason', 'string', 'reason'],
      ['status', 'string', 'status'],
      ['created_at', 'date', 'created_at']
    ]
  }
};

// -- GATES ------------------------------------------------------------------

// The datasets a role may pull at all. Mirrors sd-data.js's financial tier.
function datasetsForRole(role) {
  return Object.keys(DATASETS).filter((k) => !DATASETS[k].financial || !!FINANCIAL_ROLES[role]);
}

function canRead(datasetName, role) {
  const d = DATASETS[datasetName];
  if (!d) return { ok: false, code: 'UNKNOWN_DATASET' };
  if (d.financial && !FINANCIAL_ROLES[role]) {
    return { ok: false,
      code: 'ROLE_NOT_PERMITTED',
      message: 'Financial records are limited to the practice owner and front desk' };
  }
  return { ok: true };
}

// How a given role's read of a dataset must be narrowed.
//   { kind: 'none' }            -- practice-wide; the role reads everything
//   { kind: 'provider_column' } -- filter in the database on provider_id
//   { kind: 'patient_ids' }     -- filter rows to the provider's own patients
function scopeFor(datasetName, role) {
  const d = DATASETS[datasetName];
  if (!d || !d.patientScoped) return { kind: 'none' };
  if (PATIENT_BROAD_READ_ROLES[role]) return { kind: 'none' };
  if (d.providerColumn) return { kind: 'provider_column', column: d.providerColumn };
  return { kind: 'patient_ids', key: d.scopeKey };
}

// -- PROJECTION -------------------------------------------------------------

// The columns a caller actually receives. PHI columns are dropped from the
// SCHEMA as well as from the rows, so a tool bound to a feed without
// identifiers never sees a column of nulls it might mistake for missing data.
function visibleColumns(datasetName, includeIdentifiers) {
  const d = DATASETS[datasetName];
  if (!d) return [];
  return d.columns.filter((c) => !c[3] || includeIdentifiers === true);
}

function projectRow(datasetName, row, ctx) {
  const out = {};
  visibleColumns(datasetName, ctx && ctx.includeIdentifiers).forEach((c) => {
    const name = c[0], type = c[1], path = c[2];
    let raw;
    try {
      raw = typeof path === 'function' ? path(row || {}, ctx || {}) : (row || {})[path];
    } catch (e) {
      raw = null;
    }
    out[name] = coerce(type, raw);
  });
  return out;
}

function projectRows(datasetName, rows, ctx) {
  return (rows || []).map((r) => projectRow(datasetName, r, ctx));
}

// Applies the patient-id narrowing for a scoped role. Rows whose scope key is
// absent are DROPPED, not kept: a row that cannot be shown to belong to this
// provider's patients has not been shown to be safe to disclose.
function applyPatientScope(datasetName, rows, allowedPatientIds) {
  const d = DATASETS[datasetName];
  const key = d && d.scopeKey;
  if (!key) return [];
  const allowed = allowedPatientIds || {};
  return (rows || []).filter((r) => r && r[key] != null && allowed[String(r[key])] === true);
}

// -- PAGING -----------------------------------------------------------------
// A BI tool pulls until a page comes back short. Deterministic ordering is what
// makes that safe: without it two pages can both contain the same row and both
// miss another, and the tool has no way to notice.
const DEFAULT_PAGE_SIZE = 1000;
const MAX_PAGE_SIZE = 5000;

function pageParams(query) {
  const q = query || {};
  let limit = parseInt(q.limit, 10);
  if (!Number.isFinite(limit) || limit <= 0) limit = DEFAULT_PAGE_SIZE;
  limit = Math.min(limit, MAX_PAGE_SIZE);
  let offset = parseInt(q.offset, 10);
  if (!Number.isFinite(offset) || offset < 0) offset = 0;
  return { limit, offset };
}

// Sorted by the dataset's own first column -- an id on every dataset except
// patients, where it is the pseudonym and equally stable. String compare, so the
// order does not depend on the database's collation.
function orderAndPage(datasetName, projected, limit, offset) {
  const cols = DATASETS[datasetName].columns;
  const keyName = cols[0][0];
  const sorted = (projected || []).slice().sort((a, b) => {
    const x = a[keyName] == null ? '' : String(a[keyName]);
    const y = b[keyName] == null ? '' : String(b[keyName]);
    return x < y ? -1 : x > y ? 1 : 0;
  });
  return { rows: sorted.slice(offset, offset + limit), total: sorted.length };
}

// -- CATALOG ----------------------------------------------------------------
// What this role can pull and what each column means. A BI tool does not read it
// automatically -- a person setting the connection up does, and without it the
// only way to learn the column list is to pull a dataset and look.
function catalog(role, includeIdentifiers) {
  return {
    app: 'sairndental',
    feed: 'read-only',
    role: role,
    identifiers_included: includeIdentifiers === true,
    note: 'Stored facts only. Derived measures (appeal deadlines, GFE due dates, ' +
          'recall standing, insurance estimates) are computed in the app and are ' +
          'deliberately not duplicated here -- model them from these columns.',
    datasets: datasetsForRole(role).map((k) => ({
      dataset: k,
      label: DATASETS[k].label,
      grain: DATASETS[k].grain,
      contains_financial_data: !!DATASETS[k].financial,
      scoped_to_your_patients: scopeFor(k, role).kind !== 'none',
      columns: visibleColumns(k, includeIdentifiers).map((c) => ({ name: c[0], type: c[1] }))
    }))
  };
}

// -- TOKENS -----------------------------------------------------------------
// The token is shown once, at mint. Only its hash is stored, so a leak of the
// tokens table does not hand anyone a working feed -- the same reason a password
// column holds a hash. sha256 with no per-row salt is correct HERE and would not
// be for a password: this is 256 bits of CSPRNG output, not something a human
// chose, so there is no dictionary to run against it.
function mintToken() {
  return 'dntbi_' + crypto.randomBytes(32).toString('hex');
}
function hashToken(token) {
  return crypto.createHash('sha256').update(String(token || '')).digest('hex');
}

module.exports = {
  DATASETS, FINANCIAL_ROLES, PATIENT_BROAD_READ_ROLES,
  DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE,
  coerce, patientKey,
  datasetsForRole, canRead, scopeFor,
  visibleColumns, projectRow, projectRows, applyPatientScope,
  pageParams, orderAndPage, catalog,
  mintToken, hashToken
};
