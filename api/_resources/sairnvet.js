// api/_resources/sairnvet.js
// Resource registry for SAIRNvet.
//
// THIS FILE USED TO REGISTER NOTHING, AND THAT WAS THE RIGHT ANSWER UNTIL
// TODAY. Its 2026-09-05 header read: "IT OWNS NOTHING, AND THE EMPTY LIST IS
// THE POINT ... Deliberately NOT invented: SAIRNvet has a large localStorage
// surface, and it would have been easy to register `sv_*` names for it. Not
// one of them is sent to sd-data today, and a registry that lists resources
// no code requests is a claim about the platform that nothing backs."
//
// That was accurate, and the file still existed for a separate reason worth
// keeping in view: an app with NO module is unattributable, so its licences
// take the full-list fallback and bypass the app-boundary gate. Registering
// with an empty list was what made SAIRNvet attributable.
//
// WHAT CHANGED IS THE CODE, NOT THE STANDARD. tools/local_only_collection_check.py
// on 2026-09-09 measured sairnvet.html at 42 of 42 collections with NO route
// to a server -- the worst ratio on the platform, on the app with the most
// regulated content. sairnvet.html now writes these through svData(), so the
// names belong here. The old rule stands: a registry entry without a caller
// is still a claim nothing backs.
//
// FORTY-ONE RESOURCES. One generic read/write pair in api/sd-data.js, not
// forty-one copy-pasted blocks -- same shape and reasoning as BLD_RESOURCES,
// SD_RESOURCES and LEG_RESOURCES. See sql/sairnvet_data_schema.sql for the
// tables and the id-column rule.
//
// NAMING: the resource name is the localStorage key verbatim. The client's
// sync hook keys off the storage key directly, so a rename would need a
// mapping table on both sides to stay correct.
//
// NO SESSION GATE, and it is not an omission. SAIRNvet HAS NO PER-EMPLOYEE
// AUTHENTICATION AT ALL -- `role` is a self-selected dropdown at login, never
// server-verified, which this app's own AI dispatcher header already gives as
// the reason it carries no role gate. A session gate here would gate on a
// session that does not exist. The licence is the whole boundary this app
// has, and the open-work row "SAIRNvet: no employee authentication subsystem"
// is where that changes, for all forty-one at once rather than for whichever
// ones somebody remembered.
//
// TWO OF THESE ARE REGULATED RECORDS AND ARE NAMED RATHER THAN BURIED IN THE
// LIST: sv_controlled is the controlled-substance register (DEA-relevant) and
// sv_audit_log is its dosing audit trail. Both are in the scope of that same
// auth row. Backing them up does not make them compliant; not backing them up
// guaranteed they were lost with the browser profile.
module.exports = {
  app: 'sairnvet',
  resources: [
    'sv_audit_log',
    'sv_billing',
    'sv_boarding',
    'sv_clients',
    'sv_coggins',
    'sv_comms',
    'sv_compliance',
    'sv_conservation',
    'sv_controlled',
    'sv_dental',
    'sv_documents',
    'sv_equinedental',
    'sv_examrooms',
    'sv_farmcalls',
    'sv_financials',
    'sv_herdhealth',
    'sv_imaging',
    'sv_invoicing',
    'sv_labresults',
    'sv_lameness',
    'sv_mobilevet',
    'sv_multisite',
    'sv_patients',
    'sv_peerconsults',
    'sv_petinsurance',
    'sv_portal',
    'sv_prepurchase',
    'sv_referrals',
    'sv_reminders',
    'sv_reports',
    'sv_reproduction',
    'sv_scheduling',
    'sv_soapnotes',
    'sv_speciesref',
    'sv_staff',
    'sv_surgery',
    'sv_teleconsults',
    'sv_vitals',
    'sv_wellness',
    'sv_whiteboard',
    'sv_wildliferehab',
  // ── DELIBERATELY NOT BACKED UP, with the reason ─────────────────────────
  // Written down here rather than left as an absence, because "not in the
  // list" and "decided against" look identical to the next reader.
  //
  //   sv_examrooms_turnover -- NOT RECORDS. saveExamRoomTurnoverLog() is
  //                            handed the output of `log.push(minutes)`: a
  //                            flat array of NUMBERS, one per room cleaning,
  //                            with no id and no shape. It feeds an average
  //                            turnover figure and is recomputed from use.
  //                            Syncing it would need a record identity the
  //                            data does not have, and inventing one to make
  //                            the loop happy is how a derived metric ends up
  //                            looking like a clinical record.
  //
  //                            WATCH OUT WHEN RE-RUNNING THE CHECKER. Since
  //                            st() gained the sync hook, tools/local_only_
  //                            collection_check.py reports this key as COVERED
  //                            -- "same data as a server call in
  //                            saveExamRoomTurnoverLog()" -- because that
  //                            function is a one-line `return st(...)` and
  //                            st() now contains a server call. It is NOT
  //                            covered: it is not in SV_SYNCED and nothing
  //                            pushes it. That is a false clean in the tool,
  //                            of exactly the kind its own header warns about
  //                            ("excusing any key written inside a function
  //                            that touched a server anywhere cleared six
  //                            genuinely local-only keys"), and it is recorded
  //                            in the open-work index rather than fixed here.
  //   sv_settings           -- device configuration. Already excluded by the
  //                            checker as device state, listed here so the
  //                            count reconciles: 42 collections measured, 41
  //                            backed up, 1 excluded above.
  ],
  // ── DECLARED NOT SYNCED (2026-09-10) ────────────────────────────────────
  // The same decisions already written in prose above, in a form the checker
  // can read. tools/local_only_collection_check.py had been CLEARING these
  // through a bug -- a one-line save wrapper matched its own signature as the
  // server call -- so they never appeared. With that fixed they surfaced all
  // at once and read like a regression, when every one of them is a choice
  // somebody made and recorded.
  //
  // A DECLARATION IS NOT COVERAGE. These keys still reach no server; what this
  // changes is whether that is news. Absent means UNDECIDED, not exempt, so a
  // new local-only key still shows up in the findings section where it belongs.
  notSynced: [
    'sv_examrooms_turnover',  // NOT RECORDS -- a flat array of NUMBERS from log.push(minutes)
    'sv_settings',            // device configuration
  ],
};
