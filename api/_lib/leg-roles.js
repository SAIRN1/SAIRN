// api/_lib/leg-roles.js
//
// SAIRNlegacy role granularity: ONE data table, read by ONE function.
//
// ── WHY THIS FILE EXISTS (2026-10-14, fourth b15 spec) ────────────────────
// MEASURED, not asserted: SAIRNlegacy had THREE roles and NO per-resource
// role check anywhere.
//
//     grep -n "sairnlegacy:" api/_lib/auth.js   ->  ['owner','director','staff']
//     grep -nE "LEG_[A-Z_]*ROLES" api/sd-data.js ->  (no output)
//
// So `staff` -- every employee who is not the owner or a director -- read and
// wrote the same 36 resources an owner did, including leg_deathrecords,
// leg_cremations, leg_custodylog and leg_preneed. For comparison sairnlaw had
// one gate and sairnvet had one; this app had zero.
//
// The band assignment and the role vocabulary are TRANSCRIBED from
// docs/2026-10-14-fourth-b15-sairnlegacy-role-matrix.md, not derived here.
// Changing them is a decision of the same kind and needs the same authority.
// Shape copied from api/_lib/law-roles.js, which solved the same problem on
// the same handler two days earlier -- not a second spelling of it.
//
// ── FIVE OF THE EIGHT ROLE NAMES ARE [CONFIRM] IN THE SPEC AND STILL ARE ──
// `owner` and `director` are the app's own words. `arranger`, `prep`,
// `office`, `apprentice` and `livery` are the spec's names for job titles a
// funeral home may call something else, and the spec says plainly that nobody
// here has arranged a funeral. They are implemented because a vocabulary is
// needed before a gate can exist; they are NOT settled, and the open question
// is named in the handoff rather than buried in a comment.
//
// ── THE MIGRATION, WHICH IS THE PART THAT CAN BREAK A LIVE PRACTICE ───────
// `staff` STAYS in the vocabulary as a DEPRECATED value mapped to the
// NARROWEST band -- OPERATIONS read/write, no MONEY, no REGULATED write --
// until a human re-assigns each person. A migration that silently promoted
// `staff` to `arranger` would grant 15 money resources to everyone who had a
// login yesterday. That is the single most expensive mistake available here
// and it is why `staff` is a row in this table rather than a rename.

'use strict';

// ── THE APPEND-ONLY LOCK, FIRST, BECAUSE IT IS NOT A ROW IN THE TABLE ─────
// A chain-of-custody log that can be EDITED is not a chain of custody. This is
// the record of which human remains were in whose hands and when, and it binds
// the owner exactly as it binds a driver -- so it is a separate structure
// consulted independently of the role table rather than a value inside it. A
// rule expressed only as a role grant is a rule a role grant can erase.
//
// It does NOT stop a new entry. Appending is the whole purpose of the log.
const LEG_APPEND_ONLY = Object.freeze(Object.assign(Object.create(null), {
  leg_custodylog: true
}));

// ── THE TABLE. 36 ROWS, ONE PER RESOURCE, NO RESOURCE WITHOUT A ROW ───────
// Values are the ACTIONS each role may take: 'rw', 'r', or '' for none.
// `band` is carried on every row because the policy was given as THREE BANDS
// and the mapping from a band to a resource name is the part a reviewer has to
// be able to check. A wrong band is then visible rather than averaged away.
const R = 'r', RW = 'rw', NO = '';

// The three band templates, written once. A row that follows its band exactly
// spreads the template; a row that departs from it says so on the row, which
// is the only way an exception stays visible in a 36-row table.
const REGULATED = { owner: RW, director: RW, arranger: R, prep: R, office: R,
                    apprentice: R, livery: NO, staff: R };
const MONEY     = { owner: RW, director: RW, arranger: RW, prep: NO, office: RW,
                    apprentice: NO, livery: NO, staff: NO };
const OPERATIONS = { owner: RW, director: RW, arranger: RW, prep: R, office: RW,
                     apprentice: R, livery: NO, staff: RW };
// The three OPERATIONS resources livery actually needs: the schedule, and
// nothing else. Spelled as its own template rather than as three edits to
// OPERATIONS, so "which three" is one readable list.
const OPERATIONS_LIVERY = Object.assign({}, OPERATIONS, { livery: R });

function row(band, bandName, over, why) {
  return Object.freeze(Object.assign({}, band, over || {},
    { band: bandName, why: why || '' }));
}

const LEG_ROLE_MATRIX = Object.freeze(Object.assign(Object.create(null), {
  // ── REGULATED (9) ───────────────────────────────────────────────────────
  leg_aftercare:     row(REGULATED, 'REGULATED', null, 'bereavement follow-up against a named family'),
  leg_cases:         row(REGULATED, 'REGULATED', null, 'the death case itself -- every other regulated record hangs off it'),
  leg_certs:         row(REGULATED, 'REGULATED', null, 'death certificates -- a state-filed vital record, signed by a licensed director'),
  // RULE 2: a cremation authorisation is the sharpest irreversible act in this
  // app. The band already gives write to owner and director only; it is
  // restated here because a reader scanning for "who may authorise a
  // cremation" must find an answer on the row, not infer it from a template.
  leg_cremations:    row(REGULATED, 'REGULATED', null, 'cremation authority -- write is owner/director ONLY, never a task role. Whether a SECOND named person is legally required is a state-law question the spec flags and this code does not answer'),
  // RULE 1: append-only for EVERYONE INCLUDING THE OWNER, enforced by
  // LEG_APPEND_ONLY above rather than by this row.
  leg_custodylog:    row(REGULATED, 'REGULATED', null, 'chain of custody -- APPEND-ONLY for every role including owner'),
  // RULE 4: the one REGULATED resource where even read is not broad.
  leg_deathrecords:  row(REGULATED, 'REGULATED', { livery: NO }, 'death records -- read is NOT broad; livery is refused outright'),
  leg_dispatches:    row(REGULATED, 'REGULATED', null, 'removal dispatches -- who was sent to collect a body, and when'),
  leg_documents:     row(REGULATED, 'REGULATED', null, 'the regulated document set: authorisations, permits and filings'),
  leg_petcases:      row(REGULATED, 'REGULATED', null, 'pet cases -- tier B, banded REGULATED by shape rather than by tier'),

  // ── MONEY (15) ──────────────────────────────────────────────────────────
  leg_catererorders: row(MONEY, 'MONEY', null, 'a catering ORDER is a purchase the home is billed for and bills on'),
  leg_caterers:      row(MONEY, 'MONEY', null, 'caterer records carry the pricing the invoice is built from'),
  leg_floristorders: row(MONEY, 'MONEY', null, 'a florist ORDER is a purchase the home is billed for and bills on'),
  leg_florists:      row(MONEY, 'MONEY', null, 'florist records carry the pricing the invoice is built from'),
  leg_gplservices:   row(MONEY, 'MONEY', null, 'the General Price List -- what the home charges'),
  leg_insurance:     row(MONEY, 'MONEY', null, 'insurance assignment -- the policy proceeds that pay the invoice'),
  leg_invoices:      row(MONEY, 'MONEY', null, 'the invoice to the family. The single clearest MONEY row in the app'),
  leg_keepsakes:     row(MONEY, 'MONEY', null, 'keepsake merchandise, priced and sold on the General Price List'),
  leg_liverybookings: row(MONEY, 'MONEY', null, 'banded MONEY by the vendor-order pattern. [CONFIRM] whether livery is invoiced through the home or billed direct -- that decides whether the livery role needs any MONEY read at all'),
  leg_liveryvendors: row(MONEY, 'MONEY', null, 'vendor records -- same [CONFIRM] as leg_liverybookings'),
  leg_merch_catalog: row(MONEY, 'MONEY', null, 'the merchandise catalogue -- what is offered and at what price'),
  leg_merch_units:   row(MONEY, 'MONEY', null, 'merchandise units -- ALSO carries the b8 reservation lock, which is a transition gate and is unaffected by this table'),
  leg_monuments:     row(MONEY, 'MONEY', null, 'monuments, sold and billed like any other merchandise line'),
  leg_plots:         row(MONEY, 'MONEY', null, 'burial plots -- an interment right sold to a family, Tier A'),
  // RULE 3: money AND a long-dated obligation. Write is the MONEY band
  // (owner/director/arranger/office). Deletion should be owner-only and a
  // state change rather than a delete -- THERE IS NO DELETE ACTION ON THIS
  // HANDLER, so that half is not implemented and is named in the handoff
  // instead of being silently treated as done.
  leg_preneed:       row(MONEY, 'MONEY', null, 'pre-need -- money AND a long-dated obligation. The owner-only DELETION rule is NOT implemented here: this handler has no delete verb'),

  // ── OPERATIONS (12) ─────────────────────────────────────────────────────
  leg_bookings:      row(OPERATIONS_LIVERY, 'OPERATIONS', null, 'the schedule -- one of the three livery may read'),
  leg_clergy:        row(OPERATIONS, 'OPERATIONS', null, 'the clergy contact list -- who can be booked, not a charge'),
  leg_clergybookings: row(OPERATIONS, 'OPERATIONS', null, 'clergy scheduling. Carries the overlap gate, which is a separate control'),
  leg_facilities:    row(OPERATIONS, 'OPERATIONS', null, 'rooms, vehicles and -- per the seed data -- named staff treated as bookable'),
  leg_guestbook:     row(OPERATIONS, 'OPERATIONS', null, 'the guestbook -- attendee entries, no money and no filing'),
  leg_keepsakeorders: row(OPERATIONS, 'OPERATIONS', null, 'banded OPERATIONS by the spec, despite the name: the ORDER of a keepsake is fulfilment, the keepsake catalogue is the money row'),
  leg_maintenance:   row(OPERATIONS, 'OPERATIONS', null, 'facility maintenance tickets against rooms and vehicles'),
  leg_memorials:     row(OPERATIONS, 'OPERATIONS', null, 'memorial pages -- public-facing presentation, not a record of filing'),
  leg_obituaries:    row(OPERATIONS, 'OPERATIONS', null, 'obituary drafts and placements -- presentation, not a vital record'),
  leg_processions:   row(OPERATIONS_LIVERY, 'OPERATIONS', null, 'processions -- one of the three livery may read. Tier A, and banded OPERATIONS: it is the route and the running order, not a charge'),
  leg_tributes:      row(OPERATIONS, 'OPERATIONS', null, 'tribute entries from the public, alongside the guestbook'),
  leg_vehicles:      row(OPERATIONS_LIVERY, 'OPERATIONS', null, 'vehicles -- one of the three livery may read')
}));

// Verdicts. Three, not two: NOT_LEG is a real answer and is never folded into
// ALLOW, because a silent ALLOW for a non-leg resource would read as "this
// table approved it".
const ALLOW = 'ALLOW';
const DENY = 'DENY';
const NOT_LEG = 'NOT_LEG';

/**
 * The one function. (resource, role, action) -> ALLOW | DENY | NOT_LEG.
 *
 * FAILS CLOSED IN EVERY DIRECTION THAT MATTERS:
 *  - a leg_ resource with no row    -> DENY. The table IS the policy; a
 *    resource nobody wrote a rule for is not "allowed by default", which is
 *    exactly the state this file exists to end.
 *  - a role not in the row          -> DENY. An eighth role added to
 *    ROLES_BY_APP.sairnlegacy without a column here gets nothing, loudly,
 *    rather than inheriting owner's access.
 *  - a missing or empty role        -> DENY.
 *  - any action that is not 'read'  -> treated as WRITE-class, so a future
 *    verb cannot slip through on a read grant.
 *
 * APPEND-ONLY IS NOT DECIDED HERE and the split is deliberate: whether a
 * custody write is an append or an edit depends on whether the row already
 * exists, which is a database question. `isAppendOnly()` answers "does this
 * resource have the rule", the handler answers "is this an edit".
 */
// ══ THE PRACTITIONER ANSWERS, 2026-10-15 (b17) ════════════════════════════
// Michael's answers to two of the funeral questions, recorded HERE because
// this file is the one place that owns SAIRNlegacy role policy.
//
// ── ANSWER 1: "funeral prep gets a licensed-embalmer tier." ───────────────
// RECORDED AND IT CHANGES NO ROW TODAY, and that is a measurement rather than
// a hedge: there is NO PREPARATION-ROOM RESOURCE in this app. The 36 rows above
// are the whole table and none of them is the embalming/preparation record a
// licensure tier would gate. `sairnlegacy.html:974` carries a "Staff
// Certifications / Licensing" panel describing "Funeral director/embalmer
// licenses, expiration tracking" and it is a placeholder with no resource
// behind it.
//
// SO A TIER THAT GRANTED SOMETHING TODAY WOULD BE DORMANT CODE -- Guardian
// Check 0d's exact shape, a policy nothing reaches that goes live with no
// warning the day somebody wires it up. What is built instead is a LIVE
// CHECK: LEG_PREP_ROOM_RESOURCES is empty, and the matrix suite fails if a
// preparation-room resource is ever added without a tier decision on it. The
// decision cannot be forgotten and nothing unreachable was written.
//
// THE ROLE VOCABULARY IS ALSO NOT HERE YET. api/_lib/auth.js's ROLES_BY_APP
// gives sairnlegacy owner/director/arranger/prep/office/apprentice/livery/
// staff -- there is no `embalmer`. Adding one is a live CHECK-constraint
// change on sairnlegacy_employee_auth, so it is in the b17 SQL package for
// Michael rather than written here where it would make
// api/role-picker-vs-check-constraint.test.js red against the real database.
const LEG_EMBALMER_TIER = Object.freeze({
  // The tier as Michael described it: a licensed embalmer, distinct from the
  // unlicensed preparation-room helper the `prep` role currently covers.
  tier: 'licensed_embalmer',
  // The role name this tier WOULD use. Not in ROLES_BY_APP yet -- see above.
  role: 'embalmer',
  // What the tier is for, so a future implementer does not have to re-derive
  // it: write on the preparation-room record, where `prep` has read only.
  grants: 'rw on the preparation/embalming record; `prep` keeps r',
  recorded: '2026-10-15 (b17), Michael'
});
// EMPTY, AND MEASURED EMPTY. If a preparation-room resource is added, put it
// here WITH its tier decision -- the matrix suite fails while a resource whose
// name looks like the prep room is absent from this map.
const LEG_PREP_ROOM_RESOURCES = Object.freeze(Object.create(null));

// ── ANSWER 2: livery is blocked from leg_dispatches and leg_custodylog ────
//    "...unless access is granted by personnel above them."
//
// THE BLOCK ALREADY HELD. Both rows are REGULATED and the band gives
// `livery: NO`, so livery was already refused on both -- verified against the
// table rather than assumed, which is why no row changed. What did NOT exist
// is the EXCEPTION: a route for personnel above them to grant it.
//
// THE POLICY IS COMPLETE AND CALLABLE HERE; THE STORAGE IS NOT BUILT AND IS
// NAMED. decide() takes an optional `grants` object, so a caller that has a
// grant can present it and the answer is computed in ONE place. Nothing
// persists a grant yet -- that needs a table and a grant/revoke path with its
// own audit, which is a feature and not a role-map entry. Stated in the b17
// handoff with its exact next step.
//
// NARROW ON PURPOSE, THREE WAYS:
//   * only these two resources are grantable at all
//   * only owner and director may grant -- "personnel above them", and in this
//     app's matrix those are the two roles with RW on REGULATED
//   * a grant yields READ, never write. leg_custodylog is append-only for
//     EVERY role including the owner, so a write grant would be a route around
//     LEG_APPEND_ONLY, and leg_dispatches records who was sent to collect a
//     body -- livery needing to SEE their own dispatch is the operational
//     case, and nothing in it requires changing the record.
const LEG_LIVERY_GRANTABLE = Object.freeze(Object.assign(Object.create(null), {
  leg_dispatches: true,
  leg_custodylog: true
}));
const LEG_LIVERY_GRANTOR_ROLES = Object.freeze(Object.assign(Object.create(null), {
  owner: true, director: true
}));

// ══ F2 (2026-10-17, b18): IS LIVERY INVOICED THROUGH THE HOME? A SETTING ══
// Michael's answer to practitioner question F2: IT IS A PER-HOME SETTING. Both
// arrangements are real, so neither is the platform's answer, and the home
// that signs up tells the app which one it runs.
//
// ── WHAT THE SETTING ACTUALLY DECIDES, AND WHAT IT DELIBERATELY DOES NOT ──
// F2's own text names ONE consequence: "the band decides whether the `livery`
// role gets any MONEY read at all". MEASURED BEFORE BUILDING ANYTHING: the
// MONEY band already gives `livery: NO`, so a driver can see no price under
// EITHER answer today, and a setting that "narrowed" that would narrow nothing.
// Saying so is the measurement; pretending the setting fixed a leak would be
// the fabrication.
//
// SO IT DECIDES WHETHER leg_liverybookings IS GRANTABLE, which is the one
// thing that follows from the answer rather than from a preference:
//
//   through_the_home   The booking IS a purchase order the home owes money on.
//                      It is the home's commercial record, it is not the
//                      driver's, and it is NOT grantable. This is the shipped
//                      behaviour and the DEFAULT.
//   direct_to_family   The booking is the livery company's own contract with
//                      the family and the home is a referrer. A driver reading
//                      THEIR OWN booking is then the operational case, so the
//                      resource becomes grantable -- still per-employee, still
//                      READ only, still only by owner or director, and still
//                      nothing by default.
//
// NOTHING WIDENS BY DEFAULT AND NOTHING WIDENS AUTOMATICALLY. A setting of
// `direct_to_family` does not grant a single driver anything; it makes a grant
// POSSIBLE, which personnel above them still have to perform per F2's own
// companion answer from 2026-10-15.
//
// leg_liveryvendors IS NOT GRANTABLE UNDER EITHER SETTING, and that is the
// row worth being firm about: the vendor record carries the pricing the
// invoice is built from, so there is no arrangement under which a driver needs
// it. F2's warning is about exactly this -- "a driver who can see what a
// grieving family is being charged for a casket is a real problem".
const LEG_LIVERY_BILLING_VALUES = Object.freeze([
  'through_the_home',
  'direct_to_family'
]);
const LEG_LIVERY_BILLING_DEFAULT = 'through_the_home';
// Which resources become grantable UNDER WHICH SETTING. A map rather than an
// `if`, so "what does this setting change" is one readable answer and a second
// resource cannot be added by a condition nobody re-reads.
const LEG_LIVERY_BILLING_GRANTABLE = Object.freeze(Object.assign(Object.create(null), {
  through_the_home: Object.freeze(Object.create(null)),
  direct_to_family: Object.freeze(Object.assign(Object.create(null), {
    leg_liverybookings: true
  }))
}));

/**
 * The setting, normalised. AN UNKNOWN OR MISSING VALUE IS THE NARROW ONE --
 * not an error and not the permissive one. A home that has never answered F2
 * gets the shipped behaviour, and a typo in a stored setting cannot open a
 * resource.
 */
function liveryBilling(setting) {
  const v = String(setting || '');
  return (LEG_LIVERY_BILLING_VALUES.indexOf(v) === -1)
    ? LEG_LIVERY_BILLING_DEFAULT
    : v;
}

// ══ F3 (2026-10-17, b18): WHAT AN APPRENTICE MAY NOT SIGN -- A CONFIG ═════
// Michael's answer to practitioner question F3: IT IS A CONFIG. F3 asked for
// the licensing board's wording precisely because the answer is per-state, and
// a per-state legal constraint modelled as one platform rule is the failure
// mode F3's own last paragraph names: "a supervision rule modelled wrongly is
// worse than one left unmodelled with a note, because the wrong model LOOKS
// like compliance."
//
// SO THE APP CARRIES THE THREE SHAPES F3 ENUMERATED, as three separate fields,
// and a home fills in the ones its board actually imposes:
//
//   countersign  "an apprentice may do the work, a director must sign the
//                record" -- the SAME countersignature lock as F1, which is why
//                F3 said the two should be built together. An apprentice gets
//                `prepare` on these resources and never `write`.
//   forbidden    "an apprentice may not touch these records at all" -- a
//                NARROWING of named rows. It can only ever remove access:
//                consulted after the band, never instead of it.
//   presence     "a director must be physically present" -- THE APP CANNOT
//                EXPRESS THIS AND DOES NOT PRETEND TO. It is a disclosure
//                string, not a gate, and `presence_disclosure` being true is
//                what makes the UI say so. A gate here would be the wrong
//                model that looks like compliance.
//
// THE DEFAULT IS THE SHIPPED BEHAVIOUR AND GRANTS NOTHING NEW. Empty
// countersign, empty forbidden, disclosure ON -- so a home that has not
// answered F3 keeps exactly today's policy (apprentice reads the regulated
// band, writes none of it) and is TOLD the app cannot enforce supervision.
// An empty default is also the only honest one: we do not know any particular
// home's board.
const LEG_APPRENTICE_POLICY_DEFAULT = Object.freeze({
  // Resources an apprentice may PREPARE for a licensed director to sign.
  // Empty by default; a home names its board's list.
  countersign: Object.freeze([]),
  // Resources an apprentice may not touch at all. Narrowing only.
  forbidden: Object.freeze([]),
  // The app cannot model physical presence. ON by default, because a home
  // that has said nothing has not told us supervision is unnecessary.
  presence_disclosure: true,
  recorded: '2026-10-17 (b18), Michael -- "apprentice permission config"'
});

// The sentence the UI shows when `presence_disclosure` is on. HERE and not in
// the HTML, because it is the honest limit of a compliance claim and belongs
// with the policy it qualifies -- and because two apps must not grow two
// wordings of one limitation.
const LEG_APPRENTICE_PRESENCE_DISCLOSURE =
  'This record was entered by an apprentice. SAIRNlegacy cannot verify that a '
+ 'licensed director was physically present, and nothing here should be read '
+ 'as evidence that one was. If your state requires supervision in person, '
+ 'that remains your record to keep.';

/**
 * The apprentice config, normalised, with every field present and of the right
 * shape. A STORED CONFIG IS UNTRUSTED INPUT: a string where a list belongs, or
 * a resource name that is not in the table, must not be able to widen
 * anything.
 *
 * TWO FILTERS, BOTH NARROWING:
 *  - a name that is not a resource in LEG_ROLE_MATRIX is DROPPED, so a typo
 *    grants nothing rather than matching nothing silently in a later lookup
 *  - `countersign` and `forbidden` overlapping resolves to FORBIDDEN. "May not
 *    touch it at all" and "may prepare it" cannot both be true, and the
 *    narrower reading is the only safe one to guess.
 */
function apprenticePolicy(cfg) {
  const src = (cfg && typeof cfg === 'object') ? cfg : {};
  const known = (list) => (Array.isArray(list) ? list : [])
    .filter((r) => typeof r === 'string'
                && Object.prototype.hasOwnProperty.call(LEG_ROLE_MATRIX, r));
  const forbidden = known(src.forbidden);
  const countersign = known(src.countersign)
    .filter((r) => forbidden.indexOf(r) === -1);
  return {
    countersign: countersign,
    forbidden: forbidden,
    // Anything other than an explicit `false` leaves the disclosure ON. A
    // missing, null or malformed value must not silently remove a disclosure.
    presence_disclosure: src.presence_disclosure !== false,
    disclosure_text: LEG_APPRENTICE_PRESENCE_DISCLOSURE
  };
}

// The action name, spelled once, matching api/_lib/law-roles.js's
// LAW_PREPARE_ACTION by construction -- one verb across the platform, so the
// countersignature endpoint does not have to know which app it is serving.
const LEG_PREPARE_ACTION = 'prepare';

// ══ F1 (2026-10-17, b18): A CREMATION NEEDS A SECOND NAMED PERSON ═════════
// Michael's answer to practitioner question F1: YES. A cremation
// authorisation takes a second named, signing person.
//
// SO leg_cremations JOINS THE COUNTERSIGNATURE LOCK, and the pattern is
// api/sv-witness.js's -- the one SAIRNvet ships for a controlled-substance
// entry and SAIRNcare lifted for a two-person count. F1's own text said that
// pattern "lifts onto leg_cremations directly", and the three things that make
// it work are not restated here: read api/sv-witness.js.
//
// ── RE-QUALIFIED FOR THIS RESOURCE, NOT COPIED ON THE STRENGTH OF A DIFF ──
// Item 7 of docs/2026-09-13-cross-domain-disciplines.md: byte-identical is not
// safe-in-context. Three things are different here and each one is a decision:
//
//   1. THE FIRST SIGNATURE IS ALREADY TRUSTWORTHY, as in SAIRNcare and unlike
//      SAIRNvet: `leg_cremations` is written by owner or director only and the
//      session names the writer. Only the SECOND signature was unverified.
//
//   2. A SELF-COUNTERSIGNED AUTHORISATION IS REFUSED, NOT FLAGGED. Same call
//      as SAIRNcare's and for the same reason: an authorisation whose second
//      signature is the first person is NOT a two-person authorisation, and
//      recording it as one is the false record. There is no undoing a
//      cremation, so a flag on a wrong record helps nobody.
//
//   3. THERE IS NO `require_two_person` SETTING. SAIRNvet made it per-licence
//      because a one-vet practice cannot staff a second witness and the count
//      still has to happen. HERE THE ANSWER IS A STATE-LAW READING, NOT A
//      STAFFING QUESTION -- F1 asked whether the state requires it or the
//      house does, and a legal requirement is not something a licensee turns
//      off in Settings. A home that cannot produce a second signer cannot
//      file the authorisation, which is the paper position too.
//
// WHO MAY COUNTERSIGN. owner and director -- the two roles with RW on the
// REGULATED band, which in this app is what "a licensed funeral director"
// means. DERIVED from the band rather than retyped: see
// LEG_REGULATED_WRITE_ROLES below, which is computed from the table so a band
// change cannot leave this list behind.
const LEG_COUNTERSIGN_REQUIRED = Object.freeze(Object.assign(Object.create(null), {
  leg_cremations: true
}));

// COMPUTED FROM THE TABLE, NOT TYPED. The one row that defines the REGULATED
// write set is leg_cremations itself; deriving the countersigner list from it
// means a band edit moves both together. Re-typing role names in two places is
// the drift this platform has already paid for, and here the two places would
// be an irreversible authorisation and the list of people who may approve it.
const LEG_REGULATED_WRITE_ROLES = Object.freeze((function () {
  const out = Object.create(null);
  const row = LEG_ROLE_MATRIX.leg_cremations;
  Object.keys(row).forEach((role) => {
    if (role === 'band' || role === 'why') return;
    if (String(row[role] || '') === 'rw') out[role] = true;
  });
  return out;
})());

/** Does this resource require a second named signature before it is filed? */
function requiresCountersignature(resource) {
  return !!LEG_COUNTERSIGN_REQUIRED[resource];
}

/**
 * The countersignature refusal, as its own message, because it is not a role
 * problem and must not read as one. A director told "your role does not have
 * access" to a cremation they ARE allowed to authorise would go and ask for a
 * permission they already have.
 */
function countersignatureMessage(resource) {
  const noun = (resource === 'leg_cremations')
    ? 'A cremation authorisation' : 'This record';
  return noun + ' needs a second named, signing person before it can be '
       + 'filed. Ask another licensed director to review and countersign it. '
       + 'Nothing was saved and nothing was authorised.';
}

/**
 * @param {object} [grants] OPTIONAL per-employee grants, shape
 *   { <resource>: true }. Only consulted for role 'livery', only for the
 *   resources that are grantable under the home's F2 setting, and only ever
 *   yields READ.
 * @param {object} [home] OPTIONAL per-home settings, shape
 *   { livery_billing: <string>, apprentice: { countersign, forbidden,
 *   presence_disclosure } }. Both are normalised to their NARROW default, so
 *   omitting this argument reproduces the pre-b18 answer exactly.
 *
 * ── THE ORDER OF THE FOUR THINGS BELOW IS THE POLICY (b18) ───────────────
 *   1. F3 `forbidden`      NARROWS. First, so nothing downstream can grant a
 *                          resource a board has said an apprentice may not
 *                          touch -- including the band and including a
 *                          countersignature route.
 *   2. the band            the table, unchanged.
 *   3. F3 `countersign`    WIDENS, and only for the `prepare` verb. An
 *                          apprentice may prepare; they still cannot write.
 *   4. F2 + b17 grants     WIDENS, read only, role `livery` only, and only
 *                          for a resource grantable under this home's F2
 *                          setting.
 *
 * NARROWING BEFORE WIDENING IS NOT STYLE. If `forbidden` were consulted last
 * it would be unable to refuse anything an earlier branch had already
 * returned ALLOW for, which is the shape that made the trust lock unreachable
 * in api/_lib/law-roles.js until this same batch.
 */
function decide(resource, role, action, grants, home) {
  if (!resource || !Object.prototype.hasOwnProperty.call(LEG_ROLE_MATRIX, resource)) {
    return (String(resource || '').indexOf('leg_') === 0)
      ? DENY        // a NEW leg_ resource nobody added to the table: fail closed
      : NOT_LEG;
  }
  const settings = (home && typeof home === 'object') ? home : {};
  const wantsWrite = (action !== 'read');
  const wantsPrepare = (action === LEG_PREPARE_ACTION);

  // ── 1. F3 FORBIDDEN -- narrowing, and it runs first ─────────────────────
  if (role === 'apprentice') {
    const pol = apprenticePolicy(settings.apprentice);
    if (pol.forbidden.indexOf(resource) !== -1) return DENY;
  }

  const r = LEG_ROLE_MATRIX[resource];
  const grant = (role && Object.prototype.hasOwnProperty.call(r, role))
    ? String(r[role] || '')
    : '';
  // ── 2. THE BAND ─────────────────────────────────────────────────────────
  // `prepare` is NOT a read and is NOT a write grant: it is handled by branch
  // 3 alone. Treating it as WRITE-class here is what makes branch 3 the only
  // route in, so a future verb still cannot ride in on a read grant.
  const allowed = wantsWrite ? (grant === 'rw') : (grant === 'rw' || grant === 'r');
  if (allowed && !wantsPrepare) return ALLOW;

  // ── 3. F3 COUNTERSIGN -- widening, `prepare` only, apprentice only ──────
  // An apprentice on this list may PREPARE the record. Preparing is not
  // filing: the row is pending and a licensed director's countersignature is
  // what files it (api/leg-countersign.js). THE RESOURCE MUST ALSO BE ONE THE
  // PLATFORM KNOWS HOW TO COUNTERSIGN -- a home naming a resource with no
  // countersignature route would otherwise get a prepare nobody can complete.
  if (wantsPrepare && role === 'apprentice') {
    const pol = apprenticePolicy(settings.apprentice);
    if (pol.countersign.indexOf(resource) !== -1
        && LEG_COUNTERSIGN_REQUIRED[resource] === true) {
      return ALLOW;
    }
  }
  // A `prepare` by anyone already holding RW is an ALLOW -- a director may of
  // course prepare what they may file. Checked after the apprentice branch so
  // the narrower case is decided first, and never for a role the band denies.
  if (wantsPrepare && grant === 'rw') return ALLOW;

  // ── 4. F2 + b17 -- the granted livery exception, read only, LAST ────────
  // It is last so it can only ever widen a refusal and never narrow an
  // allowance. b18 adds the F2 half: `grantableForHome` is the b17 pair PLUS
  // whatever this home's livery-billing answer makes grantable.
  if (!wantsWrite && role === 'livery'
      && liveryGrantable(resource, settings.livery_billing)
      && grants && grants[resource] === true) {
    return ALLOW;
  }
  return DENY;
}

/**
 * Is this resource grantable to `livery` at this home? The b17 pair always,
 * plus the F2-dependent set. ONE FUNCTION so the handler, the grant/revoke
 * path and any UI cannot disagree about which resources a grant may name --
 * the disagreement that cost SAIRNsenior a real bug when two halves each
 * called effectiveClock() and only one passed the as-of.
 */
function liveryGrantable(resource, liveryBillingSetting) {
  if (LEG_LIVERY_GRANTABLE[resource] === true) return true;
  const byBilling = LEG_LIVERY_BILLING_GRANTABLE[liveryBilling(liveryBillingSetting)];
  return !!(byBilling && byBilling[resource] === true);
}

/** Does this resource carry the append-only rule? */
function isAppendOnly(resource) {
  return !!LEG_APPEND_ONLY[resource];
}

/** Every resource the table covers. Used by the matrix test, not the handler. */
function resources() { return Object.keys(LEG_ROLE_MATRIX); }

/**
 * The refusal message. IT NAMES THE ROLE, not only the resource -- negative
 * control L1 in the spec requires that, because "you cannot do this" with no
 * subject sends a person to the wrong place to get it fixed.
 */
// NO `resource` PARAMETER. api/_lib/law-roles.js's version takes one because
// it has a second, trust-specific sentence to choose between; this one has a
// single message, and a declared-and-unused argument is the shape that makes a
// reader believe the resource is in the refusal when it is not.
function denyMessage(role) {
  return 'Your role (' + String(role || 'unknown') + ') does not have access '
       + 'to this record';
}

/**
 * The append-only refusal, separately, because it is not a role problem. It
 * takes the resource and USES it: LEG_APPEND_ONLY could carry a second table
 * one day, and a message that names "the chain-of-custody log" for a resource
 * that is not it would be a confident wrong answer.
 */
const APPEND_ONLY_NOUN = { leg_custodylog: 'The chain-of-custody log' };
function appendOnlyMessage(resource) {
  const noun = APPEND_ONLY_NOUN[resource] || 'This record';
  return noun + ' cannot be edited by anyone, including the owner -- a '
       + 'custody record that can be changed is not a custody record. Add a '
       + 'new entry instead. Nothing was saved.';
}

module.exports = {
  LEG_ROLE_MATRIX, LEG_APPEND_ONLY,
  ALLOW, DENY, NOT_LEG,
  decide, isAppendOnly, resources, denyMessage, appendOnlyMessage,
  // b17, Michael's funeral practitioner answers. Exported so a suite can
  // assert them and a future implementer reads the decision rather than
  // re-deriving it.
  LEG_EMBALMER_TIER, LEG_PREP_ROOM_RESOURCES,
  LEG_LIVERY_GRANTABLE, LEG_LIVERY_GRANTOR_ROLES,
  // b18, the remaining three funeral answers. F1 the countersignature lock,
  // F2 the livery-billing setting, F3 the apprentice config.
  LEG_COUNTERSIGN_REQUIRED, LEG_REGULATED_WRITE_ROLES,
  requiresCountersignature, countersignatureMessage,
  LEG_LIVERY_BILLING_VALUES, LEG_LIVERY_BILLING_DEFAULT,
  LEG_LIVERY_BILLING_GRANTABLE, liveryBilling, liveryGrantable,
  LEG_APPRENTICE_POLICY_DEFAULT, LEG_APPRENTICE_PRESENCE_DISCLOSURE,
  apprenticePolicy, LEG_PREPARE_ACTION
};
