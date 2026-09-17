"""api/sd-data-mech-credentials.test.js must go RED when the boundary is undone.

Run: python tests/sd_data_mech_credentials_probe.py

WHY THIS SUITE. mech_credentials is Tier A because an EPA 608 card is a federal
certification (40 CFR 82.161) and the board built on these rows is what decides
whether a technician may be sent to a job at all. The suite's own header says
what it covers -- "who may read, who may write, what the endpoint refuses to
store, and that a renewal cannot overwrite the record it renews" -- and every
one of those is a REFUSAL. A suite made mostly of refusals is the kind that can
go green forever while the refusals quietly stop happening, because the arms
that assert a 403 or a 400 all still pass against a gate that refuses
EVERYTHING, and the arms that assert a success are the only ones that would
notice. Mutation 8 is that direction on purpose.

Every arm drives the real handler against a fake REST layer, so these are
behavioural mutations: each changes what the endpoint DOES.

ONE PROPERTY PER MUTATION:

  1. the session gate on the whole resource goes away, so an unauthenticated
     caller reads the credential board;
  2. writing stops being management-only, so a technician records their own
     licence -- the one thing the boundary exists to prevent;
  3. the EPA section stops being required, so an `epa_608` row exists that
     cannot answer the question it was created to answer;
  4. has_expiry gets defaulted instead of stated, which is the app making a
     claim about a legal document nobody made;
  5. `recorded_by` is taken from the body, so the client asserts who entered a
     licence record;
  6. expires_on is stored beside has_expiry:false, so a lifetime credential
     carries an expiry date nobody stated;
  7. the plain insert becomes an upsert, so a renewal overwrites the record it
     renews and the 409 that says "a renewal is a NEW record" never fires;
  8. AND THE OTHER DIRECTION: eligibility starts answering rather than refusing
     an empty requirement list -- "anyone may go", which is the failure that
     reads as a success.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-mech-credentials.test.js')
SRC = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    # ANCHORED ON THE ACTION TUPLE ABOVE IT, because `verifySessionToken(...,
    # 'sairnmechanical')` appears twice in this file and a bare `if (!session)`
    # would plant in whichever came first.
    ("1. the session gate goes away, so an unauthenticated caller reads the "
     "credential board",
     SRC,
     "        (action === 'read' || action === 'write' || action === 'eligibility')) {\n"
     "      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnmechanical');\n"
     "      if (!session) {",
     "        (action === 'read' || action === 'write' || action === 'eligibility')) {\n"
     "      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnmechanical')\n"
     "        || { role: 'owner', employee_id: null };\n"
     "      if (!session) {"),
    ("2. writing stops being management-only, so a technician records their "
     "own licence",
     SRC, "      if (!mechAuth.MANAGEMENT_ROLES[session.role]) {",
     "      if (false && !mechAuth.MANAGEMENT_ROLES[session.role]) {"),
    ("3. the EPA 608 section stops being required, so the record cannot answer "
     "the question it exists for",
     SRC,
     "      if (p.record_type === 'epa_608' && !mechCred.EPA_SECTIONS[p.epa_section]) {",
     "      if (false && !mechCred.EPA_SECTIONS[p.epa_section]) {"),
    ("4. has_expiry is defaulted instead of stated, so the app makes a claim "
     "about a legal document nobody made",
     SRC, "      if (typeof p.has_expiry !== 'boolean') {",
     "      if (typeof p.has_expiry !== 'boolean' && false) {"),
    # THE COMMENT IS PART OF THE ANCHOR, because the assignment alone appears
    # three times in this file.
    ("5. `recorded_by` is taken from the body, so the client asserts who "
     "entered a licence record",
     SRC,
     "          // From the verified session, never the body -- who entered a licence\n"
     "          // record is not a field the client gets to assert.\n"
     "          recorded_by: session.employee_id || null",
     "          // From the verified session, never the body -- who entered a licence\n"
     "          // record is not a field the client gets to assert.\n"
     "          recorded_by: p.recorded_by || session.employee_id || null"),
    ("6. expires_on is stored beside has_expiry:false, so a lifetime "
     "credential carries an expiry nobody stated",
     SRC, "          expires_on: p.has_expiry ? p.expires_on : null,",
     "          expires_on: p.expires_on || null,"),
    ("7. the plain insert becomes an upsert, so a renewal overwrites the "
     "record it renews",
     SRC, "      const r = await fetch(rest('mech_credentials'), {\n"
          "        method: 'POST',\n"
          "        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),",
     "      const r = await fetch(rest('mech_credentials?on_conflict=license_hash,credential_id'), {\n"
     "        method: 'POST',\n"
     "        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),"),
    # ── THE FAILURE THAT READS AS A SUCCESS ────────────────────────────────
    # Every other arm in this suite asserts a refusal, and a gate that refused
    # everything would satisfy all of them. This is the one direction where
    # going WRONG means answering rather than refusing.
    ("8. eligibility answers on an empty requirement list rather than refusing "
     "-- \"anyone may go\"",
     SRC, "        if (!eva.ok) { res.status(400).json({ error: eva.error }); return; }",
     "        if (false) { res.status(400).json({ error: eva.error }); return; }"),
]

if __name__ == '__main__':
    sys.exit(run_probe(SUITE, MUTATIONS,
                       title='negative control -- api/sd-data-mech-credentials.test.js '
                             'must refuse each way the credential boundary can be undone'))
