"""SAIRNcare's MAR, incident and pharmacy-review suites must DENY.

Run: python tests/sairncare_fault_probe.py

── GATE 4, ON THE VERTICAL WITH THE MOST SUITES AND NO PROBE ────────────────
`docs/MASTER-PLAN.md` gate 4: the guards are known to DENY, not merely to pass.
On 2026-09-15 SAIRNcare read **20 suites, 0 fault probes** -- the largest
never-proven-to-fail surface left on the platform after SAIRNroofing was closed.
18 suites in `tests/sairncare/` are green and not one of them had ever been
observed red against a real defect. A suite that has never failed is a suite
that has never been shown to test anything.

── ONE SUBJECT FILE, THREE SUITES, AND THE REASON THAT MATTERS ─────────────
Every SAIRNcare gate lives in `api/sd-data.js`, so a single mutation can reach
three suites at once. That is the point rather than an inconvenience: the
question gate 4 asks is "does ANY guard catch this", and the honest way to ask
it is to break the shared file and run everything that claims to cover it.

── THREE DIRECTIONS, CHOSEN BECAUSE THEY FAIL DIFFERENTLY ──────────────────
  * SCOPE-OF-PRACTICE. `ALF_MAR_ROLES` / `ALF_MAR_BROAD_ROLES` /
    `ALF_MAR_ORDER_ROLES` are three tables, not one, and the split is clinical:
    a med_aide may log an administration and may NOT write a medication order.
    Widening any of them lets somebody act outside their licence and the screen
    looks completely normal. api/rf-auth.js's own header already names
    duplicated role logic as SAIRNsenior's root cause; SAIRNcare has the
    densest instance of it on the platform.
  * ASSIGNEE SCOPING, WHICH IS PHI. The MAR read filter restricts a med_aide to
    their own residents. `out = out.filter((r) => r.assigned_employee_id ===
    session.employee_id);` appears at EIGHT sites in api/sd-data.js -- measured,
    not assumed -- so this is the most-copied privacy idiom in the file and the
    one most likely to be edited at one site and not the rest.
  * APPEND-ONLY INTEGRITY. A re-used administration id must be a 409, never a
    silent overwrite: overwriting says a dose was refused when the record said
    given. `api/alf-append-only-fail-closed.test.js` exists because this exact
    check once failed OPEN, which is why the arms below break it in both the
    "stop checking" and the "check but mis-compare" directions.

── EVERY ARM IS A DEFECT THIS PLATFORM REALLY HAD ──────────────────────────
Role-table widening (SAIRNsenior, api/rf-auth.js header), a trusted
client-supplied assignee (the alf_mar write path's own comment forbids it by
name), an append-only check that failed open (alf-append-only-fail-closed),
and a server-stamped attribution field replaced by a client value
(care_level_history.changed_by, op-audit reviewed_by). None are invented.

── EVERY ARM RUNS IN A THROWAWAY WORKTREE, never this clone ────────────────
Subject and suites are copied from the WORKING TREE, not taken from HEAD, so a
suite change made to close a hole this probe finds is visible to it. That trap
was hit for real on tests/sairnbiz_fault_probe.py's first run.

── EVERY ANCHOR IS COUNTED, NOT MERELY FOUND ───────────────────────────────
`once()` asserts exactly one match and refuses rather than letting `replace()`
pick which of eight sites to damage -- which on this subject is not a
hypothetical worry, it is the measured shape of the file.

── AND THE RESTORE IS ITSELF CHECKED ───────────────────────────────────────
A restore that silently failed would leave every later arm running against an
already-mutated file, reporting green while testing a corrupted state. The
closing control byte-compares the subject and re-runs all three suites.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
DATA = os.path.join('api', 'sd-data.js')
HTML = 'sairncare.html'
MAR = os.path.join('tests', 'sairncare', 'test-alf-mar.js')
INC = os.path.join('tests', 'sairncare', 'test-alf-incidents.js')
PH3 = os.path.join('tests', 'sairncare', 'test-alf-phase3.js')
RULES = os.path.join('tests', 'faults', 'alf_rule_read_faults.js')
PHI = os.path.join('tests', 'phi_cache_scoped_to_user.js')
SUITES = (MAR, INC, PH3, RULES, PHI)
SUBJECTS = (DATA, HTML) + SUITES

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(wt, suite):
    r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('sairncare -- the MAR, incident and pharmacy-review gates must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-care-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    for _rel in SUBJECTS:
        shutil.copyfile(os.path.join(REPO, _rel), os.path.join(wt, _rel))

    ORIG = {}
    for rel in (DATA, HTML):
        ORIG[rel] = io.open(os.path.join(wt, rel), encoding='utf-8', newline='').read()

    def write(rel, text):
        io.open(os.path.join(wt, rel), 'w', encoding='utf-8', newline='').write(text)

    def restore():
        for rel, txt in ORIG.items():
            write(rel, txt)

    def once(rel, needle):
        n = ORIG[rel].count(needle)
        assert n == 1, ('fixture invalid: %r matches %d places in %s, not 1 -- '
                        'widen the anchor rather than letting replace() pick'
                        % (needle[:60], n, rel))
        return needle

    def apply(edits):
        """Apply every edit, grouped by file so two edits to one file compose."""
        texts = {}
        for rel, old, new in edits:
            texts[rel] = texts.get(rel, ORIG[rel]).replace(once(rel, old), new, 1)
        for rel, text in texts.items():
            write(rel, text)

    def arm(label, suite, edits):
        try:
            apply(edits)
            rc, out = run(wt, suite)
            check(label + '  [' + os.path.basename(suite) + ']', rc != 0,
                  'the suite still PASSED against the mutation\n' + out[-300:])
        finally:
            restore()

    # ── ARM 0: THE CONTROLS, FIRST ─────────────────────────────────────────
    # A probe that never establishes green cannot tell a mutation it caught
    # from a suite that was already broken.
    for suite in SUITES:
        rc, out = run(wt, suite)
        check('the shipped tree passes %s' % os.path.basename(suite), rc == 0,
              out[-400:])

    # ── 1. SCOPE OF PRACTICE: THE OUTER MAR TABLE WIDENS ───────────────────
    # A caregiver is not licensed to touch a medication record at all. Adding
    # one role to this object opens both read and write in a single edit.
    arm('a caregiver added to ALF_MAR_ROLES is caught', MAR,
        [(DATA, 'const ALF_MAR_ROLES = { owner: true, nursing: true, med_aide: true };',
          'const ALF_MAR_ROLES = { owner: true, nursing: true, med_aide: true, caregiver: true, billing: true, activities: true };')])

    # ── 2. ...AND THE OTHER DIRECTION, WHICH IS NOT THE SAME BUG ───────────
    # Refusing everybody is a broken app rather than a breach. A suite that
    # only catches the permissive direction would let a MAR nobody can open
    # ship, and on this subject that means medications are not administered.
    arm('a MAR nobody may open is caught too', MAR,
        [(DATA, 'const ALF_MAR_ROLES = { owner: true, nursing: true, med_aide: true };',
          'const ALF_MAR_ROLES = {};')])

    # ── 3. THE ASSIGNEE FILTER STOPS APPLYING ──────────────────────────────
    # BROAD_ROLES gaining med_aide is a one-word edit that turns a scoped MAR
    # into a facility-wide one: every resident's medications, to every aide.
    arm('med_aide promoted into ALF_MAR_BROAD_ROLES is caught', MAR,
        [(DATA, 'const ALF_MAR_BROAD_ROLES = { owner: true, nursing: true };',
          'const ALF_MAR_BROAD_ROLES = { owner: true, nursing: true, med_aide: true };')])

    # ── 4. ...OR THE FILTER IS SIMPLY DELETED ──────────────────────────────
    # Same outcome by a different edit, and this is the one the eight-site
    # copy count makes likely: somebody tidies one of the eight and takes the
    # guard with it.
    arm('deleting the MAR read filter outright is caught', MAR,
        [(DATA, '      if (!ALF_MAR_BROAD_ROLES[session.role]) {\n'
                '        out = out.filter((r) => r.assigned_employee_id === session.employee_id);\n'
                '      }',
          '      if (false) {\n'
          '        out = out.filter((r) => r.assigned_employee_id === session.employee_id);\n'
          '      }')])

    # ── 5. THE CLINICAL-DECISION ENTRY TYPES OPEN TO A MED AIDE ────────────
    # administration and count are routine execution; medication_order,
    # reconciliation and assessment_refusal are clinical decisions. Collapsing
    # that distinction is the scope-of-practice defect in its purest form.
    arm('a med_aide allowed to write clinical-decision entry types is caught', MAR,
        [(DATA, "      if (payload.entry_type !== 'administration' && payload.entry_type !== 'count' && !ALF_MAR_ORDER_ROLES[session.role]) {",
          '      if (false) {')])

    # ── 6. THE ENTRY-TYPE WHITELIST STOPS BEING A WHITELIST ────────────────
    # An unrecognised entry_type stored silently is a MAR row no panel filters
    # on and no report counts -- present in the table, absent from the record.
    arm('an unvalidated entry_type is caught', MAR,
        [(DATA, '      if (ALF_MAR_ENTRY_TYPES.indexOf(payload.entry_type) === -1) {',
          '      if (false) {')])

    # ── 7. THE ASSIGNMENT IS TAKEN FROM THE CLIENT ─────────────────────────
    # The write path's own comment says "never trust a client-supplied
    # assigned_employee_id for this table". This arm does exactly that.
    arm('a client-supplied assignee replacing the live look-up is caught', MAR,
        [(DATA, '      const residentAssignee = residentRow.assigned_employee_id || null;',
          '      const residentAssignee = payload.assigned_employee_id || residentRow.assigned_employee_id || null;')])

    # ── 8. APPEND-ONLY STOPS CHECKING ──────────────────────────────────────
    # The re-used-id check is skipped entirely: a second write to the same
    # administration id overwrites the first. "Given" becomes "refused" and
    # nothing records that it ever said otherwise.
    arm('the append-only check being skipped is caught', MAR,
        [(DATA, "      if (payload.entry_type !== 'medication_order') {",
          '      if (false) {')])

    # ── 9. ...OR CHECKS AND MIS-COMPARES ───────────────────────────────────
    # A different failure from arm 8 and the more realistic one: the query
    # still runs, the rows still come back, and the comparison is off by one.
    # This is the shape alf-append-only-fail-closed.test.js exists for.
    arm('an off-by-one append-only comparison is caught', MAR,
        [(DATA, '        if (Array.isArray(existingRows) && existingRows.length > 0) {\n'
                "          res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'This entry has already been recorded and cannot be overwritten' } });",
          '        if (Array.isArray(existingRows) && existingRows.length > 1) {\n'
          "          res.status(409).json({ error: { code: 'ALREADY_RECORDED', message: 'This entry has already been recorded and cannot be overwritten' } });")])

    # ── 10. THE INCIDENT LOG OPENS TO THE FLOOR ────────────────────────────
    # Deliberately asymmetric: anyone may FILE, only management/nursing/
    # billing may READ. Widening the read side publishes every resident's
    # falls, med errors and abuse allegations to every employee.
    arm('the incident log opened to every role is caught', INC,
        [(DATA, 'const ALF_INCIDENT_READ_ROLES = { owner: true, nursing: true, billing: true };',
          'const ALF_INCIDENT_READ_ROLES = { owner: true, nursing: true, billing: true, caregiver: true, med_aide: true, activities: true };')])

    # ── 11. THE FILER CAN EDIT THEIR OWN REPORT AFTER FILING ───────────────
    # The one guard that makes an incident report evidence rather than a note.
    # Remove it and the person who filed can rewrite what they witnessed.
    arm('the post-filing edit lock being removed is caught', INC,
        [(DATA, '      if (alreadyExists && !ALF_INCIDENT_READ_ROLES[session.role]) {',
          '      if (false) {')])

    # ── 12. THE PHARMACY-REVIEW GATE, PEELED ONE LAYER AT A TIME ───────────
    #        AND WHAT THAT PEEL ACTUALLY FOUND
    # Breaking the pharmacy-review role check ALONE does not turn test-alf-
    # phase3.js red, and the first run of this probe recorded that as a
    # coverage gap. It is not one, and the real answer is more interesting:
    # `med_aide CANNOT accept a pharmacy order` is refused by THREE independent
    # gates before it ever reaches the one the assertion is named after.
    #   L1  the outer clinical-decision gate -- entry_type is medication_order,
    #       so every role outside ALF_MAR_ORDER_ROLES is already 403
    #   L2  the assignee gate -- phase3's own fixture has RES-1 assigned to
    #       NOBODY (`assigned_employee_id: null`), so MA-1 is refused again
    #   L3  the pharmacy-review role check itself, which is the only one the
    #       test's name refers to
    # L1 makes L3 UNREACHABLE BY CONSTRUCTION in production: entry_type is
    # already known to be medication_order when L3 runs, so
    # `!ALF_MAR_ORDER_ROLES[session.role]` there can never be true. That is
    # dormant defence rather than a defect, and it is left in place
    # deliberately -- deleting a role check out of a medication path to satisfy
    # a dormant-code scan is the wrong trade. It is RECORDED here instead,
    # which is what this probe is for.
    # The three arms below state the layering as fact rather than intention.
    # Two of them assert a suite stays GREEN, which is unusual and is the
    # point: it is the only way to show a redundant guard is redundant rather
    # than decorative.
    L1 = ("      if (payload.entry_type !== 'administration' && payload.entry_type !== 'count' && !ALF_MAR_ORDER_ROLES[session.role]) {",
          '      if (false) {')
    L2 = ('      if (!ALF_MAR_BROAD_ROLES[session.role] && residentAssignee !== session.employee_id) {',
          '      if (false) {')
    L3 = ('        if (!ALF_MAR_ORDER_ROLES[session.role]) {',
          '        if (false) {')

    def holds(label, edits):
        try:
            apply([(DATA, old, new) for old, new in edits])
            rc, out = run(wt, PH3)
            check(label + '  [' + os.path.basename(PH3) + ']', rc == 0,
                  'the remaining layer did not hold -- it is decoration, not '
                  'defence\n' + out[-300:])
        finally:
            restore()

    holds('L1 gone: the assignee gate alone still refuses a med_aide the '
          'pharmacy order', [L1])
    holds('L1+L2 gone: the pharmacy-review check alone still refuses -- so L3 '
          'is real defence, merely unreachable', [L1, L2])

    arm('...and with all three gone a med_aide accepts a pharmacy order', PH3,
        [(DATA,) + L1, (DATA,) + L2, (DATA,) + L3])

    # ── 13. THE REVIEWER'S NAME COMES FROM THE CLIENT ──────────────────────
    # reviewed_by is who cleared this drug for this resident. A client-supplied
    # value makes the attribution a claim by the caller rather than a fact.
    arm("a forged reviewed_by overriding the session is caught", PH3,
        [(DATA, '          marData.reviewed_by = session.employee_id;',
          '          marData.reviewed_by = payload.reviewed_by || session.employee_id;')])

    # ── 14. TWO TABLES AT ONCE ─────────────────────────────────────────────
    # Both role tables widened together, because a suite that catches either
    # alone might be keying on a total rather than on each gate.
    arm('both MAR role tables widened at once is caught', MAR,
        [(DATA, 'const ALF_MAR_ROLES = { owner: true, nursing: true, med_aide: true };',
          'const ALF_MAR_ROLES = { owner: true, nursing: true, med_aide: true, caregiver: true };'),
         (DATA, 'const ALF_MAR_BROAD_ROLES = { owner: true, nursing: true };',
          'const ALF_MAR_BROAD_ROLES = { owner: true, nursing: true, med_aide: true };')])

    # ── 15. THE CLIENT HALF: A GUARD DEFEATED BY THE LINE ABOVE IT ─────────
    # `tests/faults/alf_rule_read_faults.js` exists because prRefresh() and
    # cqRefresh() both coalesced a failed read to `[]` while their renderers
    # still tested `=== null` to print "not loaded". The coalesce ran first, so
    # after any click of Refresh Rules that branch was unreachable and a FAILED
    # READ rendered as an authoritative empty rule set -- with the run-the-SQL
    # remediation advice attached, which is the harmful part. This arm puts the
    # defect back exactly as it was.
    arm('the billing-rule read coalescing a failure to [] is caught', RULES,
        [(HTML, '_prRules=Array.isArray(rows)?rows:null;',
          '_prRules=Array.isArray(rows)?rows:[];')])

    # ── 16. ...AND THE COMPLIANCE HALF, WHERE THE STAKES ARE HIGHER ────────
    # "Coverage: 0 of 4 states fully loaded" beside "No compliance rules are
    # loaded yet" tells an assisted-living operator their state's staffing,
    # training and licensure requirements are absent. The read had simply
    # failed. An uncovered state must read as an explicit gap; a failure is not
    # a gap.
    arm('the compliance-rule read coalescing a failure to [] is caught', RULES,
        [(HTML, '_cqRules=Array.isArray(rows)?rows:null;',
          '_cqRules=Array.isArray(rows)?rows:[];')])

    # ── 17. ...AND THE FAILURE FLAG ITSELF STOPS BEING SET ─────────────────
    # A different edit with the same end state: `_prRules` still goes to null,
    # so the renderer takes the null branch, but `_prReadFailed` is stuck false
    # and it prints "Coverage: not loaded / Click Refresh Rules" over a read
    # that did come back and failed. The three states collapse back to two.
    arm('the read-failure flag never being set is caught', RULES,
        [(HTML, '_prReadFailed=!Array.isArray(rows);', '_prReadFailed=false;')])

    # ── 18. THE PHI CACHE STOPS BEING SCOPED TO THE PERSON ─────────────────
    # `alf_clients` is resident PHI held in localStorage. Dropping it from
    # ALF_SCOPED_CACHES means it is not purged when the signed-in employee
    # changes -- on a shared facility tablet the next aide to sign in reads the
    # previous one's residents, and the server gate that scoped the read is
    # defeated by a cache that outlived the session.
    arm('resident PHI dropped from the scoped-cache list is caught', PHI,
        [(HTML, "ALF_SCOPED_CACHES = ['alf_clients','alf_staff','alf_mar','alf_billing',",
          "ALF_SCOPED_CACHES = ['alf_staff','alf_mar','alf_billing',")])

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    ok_all = all(io.open(os.path.join(wt, rel), encoding='utf-8',
                         newline='').read() == ORIG[rel] for rel in ORIG)
    check('api/sd-data.js and sairncare.html are byte-identical to the working '
          'tree after every arm',
          ok_all, 'a restore did not land -- later arms tested a mutated file')
    for suite in SUITES:
        rc, out = run(wt, suite)
        check('...and %s is green again on it' % os.path.basename(suite),
              rc == 0, out[-300:])
finally:
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)
    print('\n  the throwaway worktree is gone: %s' % (not os.path.isdir(wt)))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
