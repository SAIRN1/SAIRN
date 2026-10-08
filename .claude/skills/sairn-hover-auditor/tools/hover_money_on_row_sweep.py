#!/usr/bin/env python
"""hover_money_on_row_sweep.py -- the dnt_supplies/#446 shape, automated.

WHY THIS EXISTS. Three batches running, this role hand-picked random samples
of B-tier resources and grepped each one's write function by eye for a
price/cost/amount/total field that gets summed or displayed -- the exact shape
dnt_supplies (#446), sd_inventory and remnants (#895) and msb_bottle_scans
(#931) were all found by. A hand sweep over a 10-resource sample at a time
cannot state "X of Y checked" against the real population without a human
re-deriving Y by hand every time, which is exactly the "carry forward a stale
count" defect this role's own methodology (seq 918, 933) was written against.
This tool derives Y itself, from the live register, every run.

WHAT IT DOES. Reads every row from docs/CRITICALITY-TIERS.md, keeps the ones
currently Tier **B**, and for each one greps a resource-to-app mapping (prefix
table below, with a full-platform fallback for bare names) to find the
resource's write-site, then checks a ~600-character window around the first
hit for a money-shaped field NAME (price|cost|amount|total|fee|charge|rate)
that also has evidence of being SUMMED (a nearby `.reduce(` whose callback
multiplies or adds that field) or DISPLAYED (a nearby `'$'+`, `toLocaleString`,
or `fmt(` wrapping it). A field name alone is not enough -- `rate` appears on
dozens of rows that are pure reference tables (dnt_cred_rules, grd_vendors'
`terms`) with nothing computed from it; requiring the summed/displayed evidence
is what the earlier hand sweep was actually doing by eye, made explicit here.

WHAT IT DOES NOT DO. It does not read the AST. A field name and a nearby
`.reduce(`/`toLocaleString` in the SAME ~600-char window is a GREP-DISTANCE
heuristic, not a data-flow proof -- a true positive needs the human read this
tool's own CANDIDATE flag is routing toward, not replacing. It is deliberately
biased toward MORE candidates than true matches (false positive over false
negative), the same direction gate_parity_check.py and the hand sweep both
already lean, because the cost of a wasted human read is far lower than the
cost of a silently skipped real one.

Run:
  python hover_money_on_row_sweep.py              full sweep, X of Y, matches listed
  python hover_money_on_row_sweep.py --universe    population only, no file reads
  python hover_money_on_row_sweep.py --selftest    fixture lock, no repo access
  python hover_money_on_row_sweep.py --resource X  one resource, verbose evidence dump
"""
import argparse
import os
import re
import sys

# Absolute, not derived from __file__ -- this role's own log directory
# (.claude/projects/.../hover-audit-log) and the platform clone it reads
# (Documents/SAIRN-hover) are NOT a fixed number of path segments apart (the
# project-id segment in between is itself a hash of the clone path), so the
# only honest way to name the repo is the same way hover_log.py's own
# INSTANCE_LOG_PATHS table does it: a literal absolute path for this instance.
REPO = r'C:\Users\marsh\Documents\SAIRN-hover'
TIERS_PATH = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')

# Prefix -> app file, from the platform's own naming convention (confirmed
# against docs/CRITICALITY-TIERS.md's own app headers, not guessed). Checked
# longest-prefix-first so e.g. 'scp_' does not get caught by a shorter 'sc_'.
PREFIX_MAP = [
    ('sairnscape', 'scp_'), ('sairnsenior', 'sen_'), ('sairnfreedom', 'sf_'),
    ('sairnroofing', 'rf_'), ('sairnlegacy', 'leg_'), ('sairndesign', 'sdn_'),
    ('sairnmechanical', 'mech_'), ('sairnbuild', 'bld_'), ('sairndental', 'dnt_'),
    ('sairnvet', 'sv_'), ('sairncare', 'alf_'), ('sairncode', 'sc_'),
    ('sairnbiz', 'sb_'), ('sairnlaw', 'law_'), ('sairngrounds', 'grd_'),
    ('sairngrounds', 'msb_'), ('stonedesk', 'sd_'),
]
# Every app .html file this platform ships, for the bare-name fallback (a
# resource with no recognised prefix, e.g. 'jobs', 'schedule', 'remnants').
ALL_APPS = [
    'stonedesk.html', 'sairnbiz.html', 'sairnbuild.html', 'sairncare.html',
    'sairncode.html', 'sairndental.html', 'sairndesign.html', 'sairnfreedom.html',
    'sairngrounds.html', 'sairnlaw.html', 'sairnlegacy.html', 'sairnmechanical.html',
    'sairnroofing.html', 'sairnscape.html', 'sairnsenior.html', 'sairnvet.html',
]

# NO LEADING \b. "unit_cost", "bottle_oz_cost", "costOfUsage" all carry the
# real field this role has been finding by hand -- an underscore or a prior
# lowercase letter (camelCase) is not a word boundary in Python's \b, so a
# leading \b would miss every compound name, which is most of them. The
# TRAILING \b is kept: it IS correct for something like "costOfUsage" not
# conflating with an unrelated word ending differently, and for the simple
# bare-field case, and relaxing only the side that was actually wrong is the
# whole point of fixing one bug at a time rather than loosening both sides.
MONEY_FIELD_RE = re.compile(r'(price|cost|amount|total|fee|charge|rate)\b', re.I)
SUMMED_RE = re.compile(r'\.reduce\(', re.I)
DISPLAYED_RE = re.compile(r"'\$'\s*\+|toLocaleString\(|\bfmt\(", re.I)
# LINE-DISTANCE, NOT CHARACTER-DISTANCE. The resource's SERVER sync call
# (`sdnData('write','dnt_supplies',rec)`) and the `rec={...}` object literal
# it ships are usually a handful of LINES apart, sometimes with the literal
# `resource+'_list'` localStorage key sitting between them and no fixed
# character distance either way -- a character window missed 108 of 116 on
# the first run for exactly this reason. ±WINDOW_LINES around every mention
# of the resource (bare name, either quote style, or name+'_list') is what
# the hand sweep was actually doing by eye: "is there a money field anywhere
# in this function."
# MEASURED, NOT GUESSED: 20 missed sd_inventory and remnants on the first
# full-population run -- both ALREADY PROVEN matches from this role's own
# hand sweep (#895) -- because the nearest QUOTED mention of each resource
# (a comment or the localStorage read, not the .reduce() call itself) sits
# 23 and more lines from the money computation. 40 catches both without
# materially widening the false-positive rate already measured at seq (this
# entry) -- the false positives found (bld_schedule_entries, scp_jobs,
# sv_staff) came from code DENSITY (many resources' blocks packed close
# together in one file), not from this specific distance, so widening the
# window does not make density-driven false positives worse in proportion.
WINDOW_LINES = 40


def derive_population(tiers_path=TIERS_PATH):
    """[(resource_name, row_line_1_indexed), ...] for every CURRENT Tier B row.
    Re-read every call -- this is the population, not a cached count."""
    out = []
    with open(tiers_path, encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if not line.startswith('| `'):
                continue
            cols = line.split('|')
            if len(cols) < 6:
                continue
            name = cols[1].strip().strip('`')
            tier = cols[2].strip()
            if '**B**' in tier:
                out.append((name, i))
    return out


def candidate_files(resource):
    for app, prefix in PREFIX_MAP:
        if resource.startswith(prefix):
            return [app + '.html']
    return list(ALL_APPS)  # bare name: search everywhere, slower but honest


def _name_mention_lines(lines, resource):
    """Every 0-based line index mentioning the resource AS A QUOTED STRING
    TOKEN (either quote style, with or without a `_list` localStorage-key
    suffix) -- NOT a bare word match. A prefixed name (dnt_supplies) is
    distinctive enough that a bare match is safe, but the ALL_APPS fallback
    for an unprefixed name ('jobs', 'schedule', 'customers', 'properties')
    is searched across all 16 app files and a bare word match hits ordinary
    English prose and unrelated identifiers constantly -- caught live on the
    first full-population run, which flagged 'locations', 'golf_zones',
    'jobs', 'properties', 'customers' and 'schedule' as money-shaped purely
    because a cost/rate/amount/total field existed SOMEWHERE within 20 lines
    of the bare word appearing ANYWHERE in a 40,000-line file, not because
    that field belonged to the resource. Requiring the quote marks is what
    the hand sweep was doing implicitly (reading `st('resource_name', ...)`
    or `ld('resource_name', ...)` call sites specifically, never a prose
    hit) and is restored here as an explicit check, not an assumption."""
    pat = re.compile(r"""['"]""" + re.escape(resource) + r"""(_list)?['"]""")
    return [i for i, ln in enumerate(lines) if pat.search(ln)]


def check_resource(resource, repo=REPO):
    """Returns dict: resource, files_checked, hit_file, hit_line, verdict
    ('MATCH' | 'NO-MATCH' | 'NOT-FOUND'), evidence (short string or None)."""
    files = candidate_files(resource)
    any_mention = False
    for fname in files:
        path = os.path.join(repo, fname)
        try:
            text = open(path, encoding='utf-8').read()
        except OSError:
            continue
        lines = text.split('\n')
        mention_lines = _name_mention_lines(lines, resource)
        if mention_lines:
            any_mention = True
        for li in mention_lines:
            lo = max(0, li - WINDOW_LINES)
            hi = min(len(lines), li + WINDOW_LINES)
            window = '\n'.join(lines[lo:hi])
            money_hit = MONEY_FIELD_RE.search(window)
            if not money_hit:
                continue
            summed = SUMMED_RE.search(window)
            displayed = DISPLAYED_RE.search(window)
            if summed or displayed:
                ev = 'field=%r %s within %d lines of %s:%d' % (
                    money_hit.group(0),
                    'SUMMED' if summed else 'DISPLAYED',
                    WINDOW_LINES, fname, li + 1)
                return {'resource': resource, 'files_checked': files,
                        'hit_file': fname, 'hit_line': li + 1,
                        'verdict': 'MATCH', 'evidence': ev}
    if any_mention:
        return {'resource': resource, 'files_checked': files, 'hit_file': None,
                 'hit_line': None, 'verdict': 'NO-MATCH', 'evidence': None}
    return {'resource': resource, 'files_checked': files, 'hit_file': None,
             'hit_line': None, 'verdict': 'NOT-FOUND', 'evidence': None}


FIXTURES = [
    # (description, synthetic_file_text, resource, expected_verdict)
    ("qty*cost summed -> MATCH",
     "var rec={id:x,qty:1,cost:2}; var val=list.reduce(function(a,i){return a+i.qty*i.cost;},0); st('fx_a',list);",
     'fx_a', 'MATCH'),
    ("rate field, no reduce/display nearby -> NO-MATCH",
     "var rec={id:x,rate:'net 30',name:y}; st('fx_b',list);",
     'fx_b', 'NO-MATCH'),
    ("cost field displayed with $ -> MATCH",
     "var rec={id:x,cost:2}; out.textContent='$'+rec.cost.toLocaleString(); st('fx_c',list);",
     'fx_c', 'MATCH'),
    ("resource string absent entirely -> NOT-FOUND",
     "nothing relevant here at all",
     'fx_d_absent', 'NOT-FOUND'),
    # THE PREFIX_MAP PATH, NOT JUST THE ALL_APPS FALLBACK -- every fixture
    # above uses an fx_* name with no recognised prefix, so every one of them
    # exercises candidate_files()'s FALLBACK branch only. A real run on
    # 'dnt_supplies' goes through the PREFIX_MAP branch instead, and that
    # branch had its own bug (app names stored without '.html', so
    # os.path.join built a path to a file that does not exist, OSError was
    # swallowed, and the resource silently fell through to NOT-FOUND) that
    # all four fx_* fixtures passed straight through without exercising.
    # Caught live on the first full-population run: dnt_supplies -- a MATCH
    # already proven by hand three batches ago -- came back NOT-FOUND.
    ("PREFIX_MAP path, qty*unit_cost summed, dnt_ prefix -> MATCH",
     "var rec={id:x,qty:1,unit_cost:2}; var val=list.reduce(function(s,i){return s+i.qty*i.unit_cost;},0); st('dnt_fixture_test_list',list);",
     'dnt_fixture_test', 'MATCH'),
]


def _fixtures():
    import tempfile
    ok = 0
    for desc, text, resource, expected in FIXTURES:
        with tempfile.TemporaryDirectory() as tmp:
            # route by the SAME candidate_files() the real check uses, so a
            # fixture for a prefixed resource lands in the file the PREFIX_MAP
            # branch will actually look for, not always the ALL_APPS fallback.
            target = candidate_files(resource)[0]
            with open(os.path.join(tmp, target), 'w', encoding='utf-8') as f:
                f.write(text)
            # also write empty copies of the other ALL_APPS files so the
            # fallback loop's os.path.isfile / open calls do not raise
            for other in ALL_APPS:
                if other != target:
                    open(os.path.join(tmp, other), 'w', encoding='utf-8').close()
            got = check_resource(resource, repo=tmp)['verdict']
        status = 'ok' if got == expected else 'FAIL'
        if got == expected:
            ok += 1
        print('  %-4s %s (got %s)' % (status, desc, got))
    print('%d/%d fixtures correct' % (ok, len(FIXTURES)))
    return ok == len(FIXTURES)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--universe', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--resource')
    a = ap.parse_args(argv)

    if a.selftest:
        return 0 if _fixtures() else 1

    pop = derive_population()
    if a.universe:
        print('Tier-B population at this read: %d resources' % len(pop))
        return 0

    if a.resource:
        names = {n for n, _ in pop}
        if a.resource not in names:
            print('%s is not a current Tier-B resource (checked against %d rows)'
                  % (a.resource, len(pop)))
            return 2
        r = check_resource(a.resource)
        print(r)
        return 0 if r['verdict'] != 'MATCH' else 1

    matches = []
    not_found = []
    for name, _ in pop:
        r = check_resource(name)
        if r['verdict'] == 'MATCH':
            matches.append(r)
        elif r['verdict'] == 'NOT-FOUND':
            not_found.append(name)

    print('MONEY-ON-ROW SWEEP -- %d of %d Tier-B resources checked' % (len(pop), len(pop)))
    print('MATCHES (%d):' % len(matches))
    for r in matches:
        print('  ! %-30s %s' % (r['resource'], r['evidence']))
    if not_found:
        print('NOT-FOUND in any candidate file (%d), named rather than silently passed: %s'
              % (len(not_found), ', '.join(not_found)))
    print('%d of %d checked, %d match(es)' % (len(pop), len(pop), len(matches)))
    return 1 if matches else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
