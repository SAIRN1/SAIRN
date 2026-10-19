# docs/b26-logs/retier_b26_four_rows.py
# OWNER: cody   batch b26   2026-10-19
#
# THE CONCEPT: a criticality row's tier is a property of the FIELDS THAT ROW
#   ACTUALLY STORES, so each of the four rows that b25 left disagreeing with
#   `customers` is decided by reading its own sql/ schema and its own write
#   site, ONE TEST is applied to all four and to `customers` as a control, and
#   only the rows the test MOVES are rewritten -- rebuilt WHOLE, never split on
#   `|`, with every other byte of the file asserted unchanged.
#
#   python docs/b26-logs/retier_b26_four_rows.py --check   # measure only
#   python docs/b26-logs/retier_b26_four_rows.py           # measure and write
#
# Exit: 0 wrote (or --check and the file already matches) - 1 an assertion
#       failed and NOTHING was written - 2 COULD NOT RUN
#
# ---------------------------------------------------------------------------
# THE TEST, STATED BEFORE THE VERDICTS SO IT CANNOT BE FITTED TO THEM
#
#   A row is CONFIDENTIALITY A when its own written fields, read together,
#   identify a specific private individual AND attach to them something
#   beyond how a business reaches them -- a dwelling, an unbounded narrative,
#   or a protected characteristic.
#   A row is B when the fields identify a BUSINESS, or identify a person ONLY
#   by how a business reaches them.
#
# THE CONTROL IS `customers`, WHICH THE TEST MUST RETURN A FOR. Without it
# this is a test that happens to return B three times and nothing establishes
# that it can return anything else. `customers` writes
# {id,name,service,recurring,phone,email,address,notes} -- `address` is a
# DWELLING, so A, which is the tier b25 landed on other grounds. The test
# reproduces a verdict it did not set.
#
# ---------------------------------------------------------------------------
# WHAT THE sql/ SCHEMAS ANSWER, AND IT IS THE SAME ANSWER FOR ALL FOUR
#
# ALL FOUR ARE OPAQUE `data jsonb` ENVELOPES. Not one of them carries a single
# payload field as a named column:
#
#   bld_suppliers        sql/sairnbuild_data_schema.sql:383-393
#   sf_vendors           sql/sairnfreedom_data_schema.sql:678-688
#   leg_clergy           sql/sairnlegacy_data_schema.sql:117-121
#   dnt_vendor_contacts  sql/sairndental_vendor_schema.sql:108-118
#
# Each is {id uuid, license_hash, app_id, <resource>_id, data jsonb,
# created_at, updated_at}, unique(license_hash, <resource>_id), with the house
# `octet_length(data::text) <= 65536` cap.
#
# SO AN sql-ONLY READ OF THESE FOUR WOULD REPORT "NO PII" FOR ALL FOUR --
# INCLUDING THE TWO THAT CARRY A NAMED INDIVIDUAL's DIRECT PHONE AND EMAIL.
# That is the whole reason the instruction says "its own sql/ schema AND its
# own write site": the schema half of this read is load-bearing only as the
# fact that it cannot decide anything, and a reader who stopped there would
# have confirmed B four times and called it four individual reads.
#
# ---------------------------------------------------------------------------
# THE FOUR READS -- columns quoted from the write site at HEAD
#
# bld_suppliers        B/B CONFIRMED, field-grounded
#   saveSupplier()  sairnbuild.html:6649   {id,name,category,terms,contact,phone}
#   Labels, sairnbuild.html:1701-1703: "Supplier Name", "Category", "Terms",
#   "Contact" (placeholder "Optional"), "Phone" (placeholder "Optional").
#   NO email field exists anywhere on this row. Identifies a BUSINESS; the one
#   person-shaped field is how to reach it. -> B.
#   THE NUANCE THE REGISTER DOES NOT STATE, recorded rather than left implied:
#   the register's basis is "`contact` IS A DEPARTMENT, NOT A PERSON in every
#   seeded row". That is true of the SEED (`:3472` -- "Order Desk", "Sales",
#   "Estimating", "Account Rep") and the UI DOES NOT ENFORCE IT: `supm-contact`
#   is free text with a bare "Optional" placeholder. It does not move the tier,
#   because even typed with a person's name the row holds a name plus a
#   business switchboard number and no email, no address and no narrative.
#   Integrity B: `terms` is a string ("Net 30"); spend is computed live from
#   `bld_pos` (panel `:956` "spend-to-date", KPI `sup-spend` `:960` "Via issued
#   POs, all time"), not stored here.
#   REGISTER CITATION RE-DERIVED: the cell cites `:3379` for the write. `:3379`
#   is not the write and not the seed at HEAD -- the seed is `:3472` and the
#   write is `saveSupplier()` at `:6649`. Named, not silently repointed, and
#   the verdict is unchanged.
#
# sf_vendors           B/B CONFIRMED, and the class never applied to it
#   sfAddVendor()   sairnfreedom.html:5654  {id,name,category,brand,licensed}
#   NO person, NO phone, NO email, NO address. There is no individual on this
#   row at ALL, so it cannot be in `customers`' confidentiality class on any
#   reading. Identifies a BUSINESS. -> B.
#   REGISTER CITATION RE-DERIVED: the cell says sfAddVendor() is "currently
#   near `:5263`"; it is at `:5654`. DRIFT +391.
#
# leg_clergy           B/B -> A/A. THE TEST MOVES THIS ROW.
#   saveClergyPartner()  sairnlegacy.html:4930
#     {id,name,faith_tradition,phone,email,notes,created_at}
#   Seed `:2152`: {id:'CG-1', name:'Rev. Thomas Boyle',
#     faith_tradition:'Catholic', phone:'(440) 555-0210', email:'', notes:''}
#   A named individual's DIRECT phone AND email, PLUS `notes` -- an unbounded
#   free-text field about that person, which no other row of the four has --
#   PLUS `faith_tradition`.
#   THE RETIER DOES NOT REST ON `faith_tradition` AND THE REGISTER's EXISTING
#   ARGUMENT ABOUT IT IS NOT OVERTURNED. That cell says the field is the
#   public professional-service category the officiant advertises under, on the
#   `sv_staff` precedent, and that reading is sound and is kept. The row moves
#   on `notes` + {name, phone, email}: an unbounded narrative attached to a
#   named individual is the second limb of the test, and it is satisfied
#   without touching the belief question. The caveat the cell records -- re-read
#   this row first if a special-category-belief rule is ever adopted -- stays a
#   caveat and is kept verbatim.
#   Integrity stays B: no money, no regulated determination computed from this
#   row. `clergyBookingConflict()` (`sairnlegacy.html:4917`) reads
#   `leg_clergybookings`, NOT this row -- checked, not assumed.
#
# dnt_vendor_contacts  B/B CONFIRMED -- but the JUSTIFICATION MOVES
#   vEditContact()  sairndental.html:6803   {rep_name,phone,email} per vendor
#   A named individual, and NOTHING beyond how a business reaches them: no
#   address, no narrative, no protected characteristic. -> B.
#   AND THIS IS THE ROW THAT MOST NEEDED THE READ, because its cell holds it
#   at B *on the CLASS*, in terms: "the same shape already at B for
#   `bld_suppliers`, `sf_vendors` and `sen_applicants`". That comparison is
#   FALSE ON THE FIELDS in two of three directions -- `bld_suppliers` has no
#   email field at all and `sf_vendors` has no person at all -- so the class it
#   was held at B on contains no member carrying a named individual's direct
#   phone AND email. The tier survives; the reasoning under it does not, and it
#   is replaced with the field test rather than left resting on a clause b25
#   struck through.
#   REGISTER CITATION RE-DERIVED: the cell cites vEditContact() at `:6598`; it
#   is at `:6803`. DRIFT +205.
#
# ---------------------------------------------------------------------------
# WHAT IS DELIBERATELY NOT DONE
#
# NO BULK RETIER. Two rows are rewritten: `leg_clergy`, whose tier the test
# moves, and `dnt_vendor_contacts`, whose tier it confirms and whose
# justification it replaces. `bld_suppliers` and `sf_vendors` are NOT
# rewritten -- their cells already say "individually read, not re-classified by
# the rule" and the read confirms them, so there is nothing to correct and
# editing them would be a diff with no finding in it.
#
# `sen_applicants` (`:552`, name+phone only, no email, no narrative) returns B
# under the same test and is NOT touched: it is not one of the four and its
# cell is already field-grounded. Named so the next reader does not have to
# re-derive that it was considered.

import io
import os
import re
import sys

REG = 'docs/CRITICALITY-TIERS.md'
CHECK = '--check' in sys.argv

if not os.path.isfile(REG):
    print('COULD NOT RUN: ' + REG + ' is not here. Nothing was verified.')
    sys.exit(2)

raw = io.open(REG, 'rb').read()
if b'\r\n' in raw:
    print('COULD NOT RUN: ' + REG + ' has CRLF line endings in the working '
          'tree. This script rebuilds a line byte-exactly and would rewrite '
          'the whole file. Run the one-time `git rm --cached -r -q . && git '
          'reset --hard` from CLAUDE.md first. Nothing was verified.')
    sys.exit(2)
lines = raw.split(b'\n')

# ── THE TWO SUBJECT ROWS, ANCHORED ON THEIR OWN RESOURCE CELL ──────────────
# NOT by line number. A line number in a script is the thing that rots, and
# this register has had four citations in one cell with two of them stale.
# The anchor is `| \`<resource>\` |` at the start of the line and it must
# occur EXACTLY ONCE, which is a third state and not folded into a pass.


def find_row(res):
    pat = b'| `' + res.encode() + b'` |'
    hits = [i for i, l in enumerate(lines) if l.startswith(pat)]
    if len(hits) != 1:
        print('COULD NOT RUN: ' + res + ' starts ' + str(len(hits))
              + ' lines in ' + REG + ', so the row could not be located '
              'unambiguously. Nothing was verified.')
        sys.exit(2)
    return hits[0]


IDX_LEG = find_row('leg_clergy')
IDX_DNT = find_row('dnt_vendor_contacts')

OLD_LEG = lines[IDX_LEG].decode('utf-8')
OLD_DNT = lines[IDX_DNT].decode('utf-8')

# ── PRECONDITIONS ON THE OLD TEXT. If any fails, the row is not what this
#    script was written against and it must NOT be rebuilt from a guess.
PRE = [
    ('leg_clergy is at B/B', OLD_LEG.startswith('| `leg_clergy` | **B** | **B** |')),
    ('leg_clergy carries the belief caveat this script preserves',
     'special-category-belief rule' in OLD_LEG),
    ('dnt_vendor_contacts is at B/B',
     OLD_DNT.startswith('| `dnt_vendor_contacts` | **B** | **B** |')),
    ('dnt_vendor_contacts still rests on the CLASS clause this script replaces',
     'Held at **B** on the CLASS, not on absence' in OLD_DNT),
    ('both rows are ONE physical line each (7 pipes)',
     OLD_LEG.count('|') == 7 and OLD_DNT.count('|') == 7),
]
bad = [n for n, okk in PRE if not okk]
if bad:
    print('COULD NOT RUN -- preconditions failed, NOTHING was written:')
    for n in bad:
        print('  * ' + n)
    sys.exit(2)

# ── THE REBUILT ROWS, WHOLE. Never split on `|`. ───────────────────────────

NEW_LEG = (
    '| `leg_clergy` | **A** | **A** | Operational data lost or wrong. '
    '**The integrity axis is genuinely B and is unchanged; the TIER is A '
    'because the worse axis is confidentiality** -- the rule this file already '
    'carries `sd_sms_log` and `customers` under. **Nothing on this row is '
    'money or a regulated determination, checked rather than assumed:** '
    '`clergyBookingConflict()` (`sairnlegacy.html:4917`) reads '
    '`leg_clergybookings`, NOT this row, so a wrong clergy record means a call '
    'placed to the wrong officiant | A clergy partner\'s business contact '
    'details and their professed `faith_tradition` are disclosed -- the public '
    'professional-service category they advertise under, not an inference about '
    'a private person. **AND `notes`: an UNBOUNDED FREE-TEXT FIELD ABOUT A '
    'NAMED INDIVIDUAL, which is the limb that moves this row and is not a '
    'belief question at all** | **RE-TIERED B -> A ON BOTH AXES 2026-10-19 '
    '(cody b26), ON MICHAEL\'S EXPLICIT INSTRUCTION TO READ THIS ROW '
    'INDIVIDUALLY** -- one of the four that b25 left disagreeing with '
    '`customers` after that row\'s class justification was struck through. '
    '**READ OFF ITS OWN sql/ SCHEMA AND ITS OWN WRITE SITE, NOT OFF THE '
    'REGISTER AND NOT OFF THE `customers` DECISION.** The schema '
    '(`sql/sairnlegacy_data_schema.sql:117`-`121`) is an OPAQUE `data jsonb` '
    'envelope -- `{id, license_hash, app_id, clergy_id, data, created_at, '
    'updated_at}` with the house 65,536-byte cap and `unique (license_hash, '
    'clergy_id)` -- so **it carries no payload field at all and cannot decide '
    'this row**; an sql-only read would have reported "no PII". The columns are '
    'the WRITE SITE\'s: `saveClergyPartner()` at `sairnlegacy.html:4930` stores '
    '`{id, name, faith_tradition, phone, email, notes, created_at}`, and the '
    'seed at `:2152` is `{id:\'CG-1\', name:\'Rev. Thomas Boyle\', '
    'faith_tradition:\'Catholic\', phone:\'(440) 555-0210\', email:\'\', '
    'notes:\'\'}`. **THE TEST APPLIED, stated before the verdict rather than '
    'fitted to it:** a row is confidentiality A when its own written fields '
    'identify a specific private individual AND attach to them something '
    'beyond how a business reaches them -- a dwelling, an unbounded narrative, '
    'or a protected characteristic. `notes` is that narrative. **THE RETIER '
    'DOES NOT REST ON `faith_tradition` AND THE PRIOR READING OF IT IS NOT '
    'OVERTURNED:** the 2026-09-24 argument (hover H1 log #531, folded by CC) '
    'that the field is a SERVICE OFFERING on the `sv_staff` precedent is sound '
    'and is kept -- the row moves on `notes` plus `{name, phone, email}`, which '
    'is satisfied without touching the belief question. **THE CAVEAT THAT CELL '
    'RECORDED STANDS AND IS NOT DISCHARGED BY THIS RETIER: if this platform '
    'ever adopts a special-category-belief rule, re-read this row first** -- '
    'religious belief is a special category in every regime that has one, and '
    'that argument rests on the field describing a service offering, not a '
    'belief record. **CONSEQUENCE NAMED RATHER THAN DISCOVERED:** at A, '
    '`tools/tier_a_review_gate.py` now records a Tier A review obligation '
    'against any future change whose diff names `leg_clergy` -- that lands on '
    'whoever next touches `sairnlegacy.html`, and it is the point of the tier '
    'rather than a side effect. '
    'docs/2026-10-19-cody-b26-four-tier-reads-and-guard-conversion.md |'
)

NEW_DNT = (
    OLD_DNT
    .replace(
        'Held at **B** on the CLASS, not on absence: business-side contact '
        'detail for a supplier\'s representative -- the same shape already at '
        'B for `bld_suppliers`, `sf_vendors` and `sen_applicants`, the last of '
        'which was corrected on 2026-09-24 for this identical stale clause',
        '~~Held at **B** on the CLASS, not on absence: business-side contact '
        'detail for a supplier\'s representative -- the same shape already at '
        'B for `bld_suppliers`, `sf_vendors` and `sen_applicants`, the last of '
        'which was corrected on 2026-09-24 for this identical stale clause~~ '
        '**-- THE CLASS JUSTIFICATION IS SUPERSEDED 2026-10-19 (cody b26) AND '
        'THE TIER IS NOT. STILL B, ON THE FIELDS THIS TIME.** The class clause '
        'is struck through rather than deleted because it is the record of what '
        'this row rested on for three weeks, and **it was false on the fields '
        'in two of its three directions:** `bld_suppliers` has NO email field '
        'anywhere on the row and `sf_vendors` has NO person on the row at all, '
        'so the class it was held at B on contained no other member carrying a '
        'named individual\'s direct phone AND email. **THE TEST, applied to '
        'all four of b25\'s disagreeing rows and to `customers` as the '
        'control:** a row is confidentiality A when its own written fields '
        'identify a specific private individual AND attach to them something '
        'beyond how a business reaches them -- a dwelling, an unbounded '
        'narrative, or a protected characteristic. `{rep_name, phone, email}` '
        'is a named person and **nothing beyond how a business reaches them**: '
        'no address, no `notes`, no protected characteristic. That is the '
        'difference from `customers`, which carries a STREET ADDRESS (a '
        'dwelling), and from `leg_clergy`, which carries an unbounded `notes` '
        'field and went B -> A in the same read')
    .replace(
        'READ OFF ITS OWN sql/ SCHEMA AS WELL AS ITS WRITE SITE',
        'READ OFF ITS OWN sql/ SCHEMA AS WELL AS ITS WRITE SITE')
    .replace(
        '**Both stale clauses are named rather than one:** the "no PII" claim '
        'and the "never individually read" claim |',
        '**Both stale clauses are named rather than one:** the "no PII" claim '
        'and the "never individually read" claim. **AND A THIRD IS NAMED NOW, '
        '2026-10-19 (cody b26): the CLASS clause.** Re-read off its own sql/ '
        'schema and its own write site on Michael\'s explicit instruction. The '
        'schema (`sql/sairndental_vendor_schema.sql:108`-`118`) is an OPAQUE '
        '`data jsonb` envelope -- `{id, license_hash, app_id, '
        'vendor_contact_id, data, created_at, updated_at}`, 65,536-byte cap, '
        '`unique (license_hash, vendor_contact_id)` -- so **it carries no '
        'payload field and could not decide this row; an sql-only read would '
        'have reported "no PII".** The columns are the write site\'s: '
        '`vEditContact()` stores `{rep_name, phone, email}` keyed by vendor. '
        '**THAT CITATION DRIFTED AND IS RE-DERIVED: this cell said `:6598`; it '
        'is `sairndental.html:6803` at HEAD, drift +205** -- the fifth stale '
        'citation found in this one cell, which is why a cell is verified '
        'citation by citation and never as a unit. **TIER UNCHANGED AT B/B, '
        'JUSTIFICATION REPLACED** -- see the confidentiality cell for the test '
        'and for why the class comparison was false on the fields. '
        'docs/2026-10-19-cody-b26-four-tier-reads-and-guard-conversion.md |')
)

# ── ASSERTIONS ON THE REBUILT ROWS, BEFORE ANYTHING IS WRITTEN ─────────────
POST = [
    ('leg_clergy rebuilt to A/A',
     NEW_LEG.startswith('| `leg_clergy` | **A** | **A** |')),
    ('leg_clergy still ONE physical line with 7 pipes', NEW_LEG.count('|') == 7),
    ('leg_clergy PRESERVES the belief caveat verbatim',
     'special-category-belief rule, re-read this row first' in NEW_LEG),
    ('dnt_vendor_contacts tier UNCHANGED at B/B',
     NEW_DNT.startswith('| `dnt_vendor_contacts` | **B** | **B** |')),
    ('dnt_vendor_contacts still ONE physical line with 7 pipes',
     NEW_DNT.count('|') == 7),
    ('dnt_vendor_contacts class clause is STRUCK THROUGH, not deleted',
     '~~Held at **B** on the CLASS, not on absence' in NEW_DNT),
    ('dnt_vendor_contacts actually changed', NEW_DNT != OLD_DNT),
    ('leg_clergy actually changed', NEW_LEG != OLD_LEG),
]
bad = [n for n, okk in POST if not okk]
if bad:
    print('REFUSED -- post-conditions on the rebuilt rows failed, NOTHING was '
          'written:')
    for n in bad:
        print('  * ' + n)
    sys.exit(1)

new_lines = list(lines)
new_lines[IDX_LEG] = NEW_LEG.encode('utf-8')
new_lines[IDX_DNT] = NEW_DNT.encode('utf-8')
out = b'\n'.join(new_lines)

# ── EVERY OTHER LINE BYTE-IDENTICAL, ASSERTED RATHER THAN INTENDED ─────────
# b25's row edit asserted this and it is the only reason a 2.3MB-class
# standing document can be edited by a script at all: "I only touched one
# line" is an intention, and the diff is the thing that is checked.
if len(new_lines) != len(lines):
    print('REFUSED: the line count changed ' + str(len(lines)) + ' -> '
          + str(len(new_lines)) + '. NOTHING was written.')
    sys.exit(1)
differing = [i for i in range(len(lines)) if lines[i] != new_lines[i]]
if differing != sorted([IDX_LEG, IDX_DNT]):
    print('REFUSED: lines ' + str([i + 1 for i in differing]) + ' differ, '
          'expected exactly ' + str([i + 1 for i in sorted([IDX_LEG, IDX_DNT])])
          + '. NOTHING was written.')
    sys.exit(1)

ROW_RE = re.compile(br'^\|')
rows_before = len([l for l in lines if ROW_RE.match(l)])
rows_after = len([l for l in new_lines if ROW_RE.match(l)])

print('REGISTER ROW REBUILD -- b26, four reads, TWO rows rewritten')
print('  lines          ' + str(len(lines)) + ' -> ' + str(len(new_lines)))
print('  `|`-rows       ' + str(rows_before) + ' -> ' + str(rows_after))
print('  bytes          ' + str(len(raw)) + ' -> ' + str(len(out)))
print('  leg_clergy     line ' + str(IDX_LEG + 1) + '  B/B -> A/A   pipes '
      + str(OLD_LEG.count('|')) + ' -> ' + str(NEW_LEG.count('|')))
print('  dnt_vendor_... line ' + str(IDX_DNT + 1) + '  B/B -> B/B   pipes '
      + str(OLD_DNT.count('|')) + ' -> ' + str(NEW_DNT.count('|')))
print('  lines differing from the original: '
      + str([i + 1 for i in differing]) + '  (expected exactly these two)')
print('  bld_suppliers  line 233  B/B CONFIRMED, cell NOT rewritten -- it '
      'already says "individually read, not re-classified by the rule"')
print('  sf_vendors     line 382  B/B CONFIRMED, cell NOT rewritten -- same')

if rows_before != rows_after:
    print('REFUSED: the table row count changed. NOTHING was written.')
    sys.exit(1)

if CHECK:
    print('\n--check: nothing written. The two rebuilt rows passed every '
          'assertion above.')
    sys.exit(0)

io.open(REG, 'wb').write(out)
back = io.open(REG, 'rb').read()
if back != out:
    print('REFUSED: the file read back differently from what was written.')
    sys.exit(1)
print('\nWRITTEN, and read back byte-identical to what was written.')
sys.exit(0)
