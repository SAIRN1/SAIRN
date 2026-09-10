"""Probe the SAIRNdental vendor backup, and specifically the half that would
have been a BUG without it.

WHY. tools/local_only_collection_check.py reported sairndental.html as 18 of 22
collections covered and FOUR with no route to a server: dnt_supplies_list,
dnt_vendor_contacts, dnt_vendor_order_history and dnt_vendor_pricing_rules.
Everything clinical has been server-backed since 2026-09-05, so a browser-data
clear left the chart intact and took the purchasing history and the negotiated
vendor discounts with it -- a SELECTIVE gap, which is worse than a uniform one
because what survives looks authoritative.

THE PART WORTH A PROBE IS NOT THE BACKUP. It is the delete.

removeSupply() drops an item from dnt_supplies_list. dntSyncFromServer() merges
the server's rows back in BY ID. So adding a backup and nothing else would make
a removed supply REAPPEAR on the next sync -- a backup that resurrects deleted
records, which is worse than no backup because it looks like the app losing
track of a deletion the user watched succeed. dnt_supplies therefore carries the
platform's `soft_delete` extra action, the read filters `_deleted_at is null`,
and removeSupply() calls it.

The other three need no delete verb and that is asserted too, because "we added
it everywhere" is the easy wrong answer: the two object resources are replaced
wholesale, and dnt_vendor_orders is append-only (the client's 200-row cap is a
local storage bound, not a deletion -- the server keeps every order, which is
the point of an archive).

Run: python tests/dnt_vendor_backup_probe.py
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, 'sairndental.html')
SDDATA = os.path.join(REPO, 'api', 'sd-data.js')
SCHEMA = os.path.join(REPO, 'sql', 'sairndental_vendor_schema.sql')
CHECKER = os.path.join(REPO, 'tools', 'local_only_collection_check.py')

html = io.open(HTML, encoding='utf-8', errors='replace').read()
sd = io.open(SDDATA, encoding='utf-8', errors='replace').read()
sql = io.open(SCHEMA, encoding='utf-8', errors='replace').read()
results = {}

FOUR = ['dnt_supplies', 'dnt_vendor_orders', 'dnt_vendor_contacts', 'dnt_vendor_pricing_rules']

# ── ARM 1: the measurement moved, and it is the tool that says so ───────────
p = subprocess.run([sys.executable, CHECKER, 'sairndental.html'],
                   capture_output=True, text=True, cwd=REPO)
out = (p.stdout or '') + (p.stderr or '')
row = ''
for ln in out.splitlines():
    if ln.startswith('sairndental.html '):
        row = ln
nums = [t for t in row.split() if t.isdigit()]
results['arm1_row_parsed'] = len(nums) >= 5
# colls / covered / local-only / cannot-tell -- read off the END of the row,
# because the setter column can contain a space (see local_only_shape_probe).
results['arm1_all_22_covered'] = len(nums) >= 5 and nums[-5] == '22' and nums[-4] == '22'
results['arm1_zero_local_only'] = len(nums) >= 5 and nums[-3] == '0'
results['arm1_zero_cannot_tell'] = len(nums) >= 5 and nums[-2] == '0'

# ── ARM 2: every one of the four is registered, tabled and pushed ───────────
registry = io.open(os.path.join(REPO, 'api', '_resources', 'sairndental.js'),
                   encoding='utf-8', errors='replace').read()
for name in FOUR:
    results['arm2_%s_registered' % name] = ("'%s'," % name) in registry
    results['arm2_%s_has_table' % name] = ('create table if not exists public.%s (' % name) in sql
results['arm2_client_pushes_lists'] = ("dntPushOne('dnt_supplies'," in html
                                       and "dntPushOne('dnt_vendor_orders'," in html)
results['arm2_client_pushes_objects'] = ("dntPushOne('dnt_vendor_pricing_rules'," in html
                                         and "dntPushOne('dnt_vendor_contacts'," in html)

# ── ARM 3: THE DELETE. Without this the backup resurrects removed supplies ──
rm = re.search(r'function removeSupply\(id\)\{.*?\n\}', html, re.S)
results['arm3_removeSupply_found'] = bool(rm)
body = rm.group(0) if rm else ''
results['arm3_removeSupply_soft_deletes'] = "sdnData('soft_delete','dnt_supplies'" in body
# ...and it must REPORT a failed delete rather than leaving the user believing
# the removal is safe. A silent failure here is precisely the resurrect case.
results['arm3_failed_delete_is_reported'] = ('r===null' in body
                                             and 'come back on the next sync' in body)
results['arm3_extra_action_declared'] = "dnt_supplies: ['soft_delete']" in registry
results['arm3_handler_exists'] = "resource === 'dnt_supplies' && action === 'soft_delete'" in sd
results['arm3_read_filters_deleted'] = 'DNT_SOFT_DELETE_RESOURCES[resource]' in sd

# ── ARM 4 (CONTROL): the other three must NOT get a delete verb ─────────────
# "We added it everywhere" is the easy wrong answer. dnt_vendor_orders is an
# append-only archive; the two objects are replaced wholesale.
for name in ('dnt_vendor_orders', 'dnt_vendor_contacts', 'dnt_vendor_pricing_rules'):
    results['arm4_%s_has_no_delete' % name] = ("%s: ['soft_delete']" % name) not in registry
    results['arm4_%s_not_soft_deleted_by_client' % name] = (
        "sdnData('soft_delete','%s'" % name) not in html

# ── ARM 5 (CONTROL): the 200-row cap must not be pushed as a deletion ───────
# The client trims to 200 for LOCAL storage. Pushing the trimmed array would
# make that bound look like the practice deleting its own order history.
# The push argument is read directly rather than by counting lines from the
# trim: the first version of this arm assumed the two statements were adjacent,
# and three comment lines between them failed it while the code was correct.
pushed = re.findall(r"dntPushOne\('dnt_vendor_orders',\s*(\w+)\)", html)
results['arm5_pushes_one_order_not_the_list'] = pushed == ['order']
results['arm5_trimmed_list_is_not_pushed'] = 'hist' not in pushed
results['arm5_cap_still_applied_locally'] = 'if(hist.length>200)hist=hist.slice(0,200);' in html

# ── ARM 6: no new database privilege, and no delete grant ──────────────────
# Soft delete is an UPDATE. If this file ever grows a `delete` grant the whole
# argument for the design collapses.
results['arm6_no_delete_grant'] = not re.search(r'^grant[^;]*\bdelete\b', sql, re.M | re.I)
results['arm6_four_tables_four_grants'] = (
    sql.count('grant select, insert, update on public.') == 4)
results['arm6_rls_on_every_table'] = sql.count('enable row level security') == 4

# ── ARM 7: the two objects are stored as ONE row each, id 'default' ────────
results['arm7_pricing_row_is_default'] = "Object.assign({id:'default'},rules)" in html
results['arm7_contacts_row_is_default'] = "{id:'default',vendors:contacts}" in html
# ...and the hydrate unwraps them the matching way round. The shapes differ by
# one level on purpose (a contacts MAP keyed by vendor name would collide with
# `id` if spread), which is exactly the kind of asymmetry that rots silently.
results['arm7_hydrate_unwraps_contacts'] = 'vcRow.vendors' in html
results['arm7_hydrate_rebuilds_pricing'] = ('vpRow.vendorDiscounts' in html
                                            and 'vpRow.categoryDiscounts' in html
                                            and 'vpRow.productOverrides' in html)

# ── ARM 8: law_billingcodes stays local, and the reason is written down ────
# The sibling decision in the same pass. It is a hardcoded UTBMS constant with
# no editor, so backing it up would copy a constant to a server to copy back.
law = io.open(os.path.join(REPO, 'api', '_resources', 'sairnlaw.js'),
              encoding='utf-8', errors='replace').read()
# READ THE EXPORTED ARRAY, not the file text. The first version matched
# "'law_billingcodes'," inside the very comment that explains the decision --
# a check its own documentation could break.
_law_names = subprocess.run(
    ['node', '-e', "process.stdout.write(require('./api/_resources/sairnlaw.js').resources.join(','))"],
    capture_output=True, text=True, cwd=REPO, shell=False).stdout.split(',')
results['arm8_registry_loaded'] = len(_law_names) > 10
results['arm8_law_billingcodes_not_registered'] = 'law_billingcodes' not in _law_names
results['arm8_reason_is_recorded'] = 'law_billingcodes' in law and 'REFERENCE DATA' in law
lawhtml = io.open(os.path.join(REPO, 'sairnlaw.html'), encoding='utf-8', errors='replace').read()
results['arm8_still_has_no_editor'] = lawhtml.count('law_billingcodes') == 2

print('--- results ---')
bad = 0
for k in sorted(results):
    v = results[k]
    print('  %-46s %s' % (k, v))
    if isinstance(v, bool) and not v:
        bad += 1

print('')
print('%d ARM(S) FAILED' % bad if bad else 'ALL ARMS PASS')
sys.exit(1 if bad else 0)
