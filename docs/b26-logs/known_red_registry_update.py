# docs/b26-logs/known_red_registry_update.py
# OWNER: cody   batch b26   2026-10-19
#
# THE CONCEPT: an entry in docs/known-red-suites.json does not make a failure
#   acceptable, it makes it ATTRIBUTABLE -- so the register has to move in BOTH
#   directions on every batch that learns something: a suite that has gone
#   green must be MOVED OUT, because while its entry stands it swallows the
#   next real failure of that file, and a suite that is red and unrecorded must
#   be MOVED IN, because an absent row reads as a regression for as long as the
#   gap lasts.
#
#   python docs/b26-logs/known_red_registry_update.py --check
#   python docs/b26-logs/known_red_registry_update.py
#
# Exit: 0 written / --check clean - 1 an assertion failed, NOTHING written -
#       2 COULD NOT RUN
#
# FAIL CLOSED ON THE CENSUS (PR 1.11). This script records the census result
# into the register, so it REFUSES if the census json is not there -- it does
# not write a partial update and call it done, and it does not invent a
# "census pending" row that would read as a measurement nobody took.

import io
import json
import os
import subprocess
import sys

REG = 'docs/known-red-suites.json'
CENSUS = 'docs/b26-logs/known_red_tail_census.json'
CHECK = '--check' in sys.argv

if not os.path.isfile(REG):
    print('COULD NOT RUN: ' + REG + ' is not here. Nothing was written.')
    sys.exit(2)
if not os.path.isfile(CENSUS):
    print('COULD NOT RUN: ' + CENSUS + ' is not here, so the census half of '
          'this update has no data. The census is driven in a DISPOSABLE '
          'WORKTREE -- copy its json back before running this. Nothing was '
          'written, and no partial update was applied.')
    sys.exit(2)

raw = io.open(REG, encoding='utf-8').read()
reg = json.loads(raw)
# ROUND-TRIP PROVED BEFORE ANYTHING IS CHANGED. json.dumps with the wrong
# indent would rewrite all 262KB and bury the real diff.
if json.dumps(reg, indent=1, ensure_ascii=False).strip() != raw.strip():
    print('COULD NOT RUN: ' + REG + ' does not round-trip through '
          'json.dumps(indent=1, ensure_ascii=False), so writing it would '
          'reformat the whole file and bury the real change. Nothing written.')
    sys.exit(2)

census = json.load(io.open(CENSUS, encoding='utf-8'))
verdicts = {v['file']: v for v in census['verdicts']}

entries = reg['entries']
recovered = reg.setdefault('recovered', [])
by_file = {e['file']: e for e in entries}

sha = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                     capture_output=True, text=True).stdout.strip()

moved_out, added, notes = [], [], []

# ── 1. THE MISCLASS SUITE IS GREEN. The register's own rule says move it. ──
MIS = 'tests/sd_data_not_provisioned_misclass.js'
if MIS in by_file:
    e = dict(by_file[MIS])
    e['recovered'] = '2026-10-19'
    e['recovered_by'] = 'cody b26'
    e['exit_code'] = 0
    e['environment'] = {
        'where': 'live-clone',
        'pinned': False,
        'tool': 'the suite itself, invoked alone, one process',
        'sha': sha,
        'basis': 'DRIVEN ALONE IN THE LIVE CLONE, cody b26, 2026-10-19. '
                 '16 passed, 0 failed, exit 0 read from its own line and '
                 'never from a pipeline. api/ was COPIED for the A2 ablation '
                 'and never written; git status was captured before and after '
                 'and diffed.',
    }
    e['recovered_why'] = (
        'C1 WAS THE LAST RED ARM AND IT IS FIXED, BUT NOT BY THE ONE-LINE FIX '
        'THE ROW ROUTED. The row said: "THE SAME ONE-LINE FIX AS A1, one guard '
        'earlier: route it through notProvisioned(res, existingR, <the same '
        'message>). notProvisionedDecide() needs no change." b26 routed EXACTLY '
        'that guard through EXACTLY that helper -- AND C1 STAYED RED. '
        'notProvisionedDecide() itself folds 42703 into NOT_PROVISIONED, '
        'because its missing-relation test is a bare `does not exist` '
        'substring and a Postgres 42703 message is literally "column '
        'alf_op_audits.reviewed_by does not exist". THE ROUTED FIX WAS RIGHT '
        'ABOUT THE CALL SITE AND WRONG ABOUT WHERE THE DEFECT WAS, and only '
        'DRIVING it showed that. Repaired in ONE place for every call site at '
        'once, ordered BEFORE the broad test -- after it the arm would change '
        'nothing at all. '
        'AND TWO MEASUREMENT DEFECTS IN THE SUITE WERE FIXED IN THE SAME PASS, '
        'both found by its own A2 ablation rather than by review. (1) P5 tested '
        '/notProvisioned\\(\\s*res\\s*,/ over the WHOLE alf_op_audits branch; '
        'b26 added a SECOND such call to that branch, so with hank\'s upsert '
        'call reverted in the copy A1 went red and P5 STAYED GREEN, satisfied '
        'by the other call. Narrowed to the response variable `w`. (2) The '
        'population counter tested notProvisioned( then provisioned: false, so '
        'all 150 converted READ branches -- which contain BOTH -- would still '
        'have counted as raw200: it would have reported "151 guards still raw" '
        'while 150 were protected. unreadableNotEmpty( is tested first now. '
        'FULL ACCOUNT: docs/2026-10-19-cody-b26-four-tier-reads-and-guard-'
        'conversion.md section 2.'
    )
    recovered.append(e)
    entries = [x for x in entries if x['file'] != MIS]
    moved_out.append(MIS)

# ── 2. ROWS THE CENSUS FOUND GREEN. Same rule, same direction. ─────────────
for f, v in sorted(verdicts.items()):
    if v['verdict'] != 'GREEN_RECOVERED':
        continue
    if f not in by_file or f in moved_out:
        continue
    e = dict(by_file[f])
    e['recovered'] = '2026-10-19'
    e['recovered_by'] = 'cody b26 (known-red tail census)'
    e['exit_code'] = 0
    e['environment'] = {
        'where': 'disposable git worktree at ' + sha,
        'pinned': False,
        'tool': 'docs/b26-logs/known_red_tail_census.py, each suite driven '
                'ALONE, one process each',
        'sha': sha,
        'basis': 'Driven alone in a DISPOSABLE WORKTREE -- several registered '
                 'suites write when run, and the census refuses to run '
                 'without an explicit --disposable-clone flag rather than '
                 'guessing whether it is in one. exit 0.',
    }
    e['recovered_why'] = (
        'FOUND GREEN BY THE b26 KNOWN-RED TAIL CENSUS, not by a fix in this '
        'batch. The register\'s own _what_this_is_NOT rule applies: "An entry '
        'whose suite has gone GREEN is reported as RECOVERED and must be '
        'deleted: while it stands it swallows the next real failure of that '
        'file." WHY IT IS GREEN IS NOT DIAGNOSED HERE and is recorded as '
        'undiagnosed rather than guessed -- an invented cause ends the '
        'investigation.'
    )
    recovered.append(e)
    entries = [x for x in entries if x['file'] != f]
    moved_out.append(f)

# ── 3. RED AND UNREGISTERED. Found by b26's regression DIFFERENTIAL. ───────
# Each was driven at HEAD and at HEAD~1 and is red in BOTH legs, so it is not
# attributable to b26's change -- and nothing in the tree recorded it, which
# means it would have read as a regression for whoever ran next.
BASELINE_RED = (
    ('api/_resources/extra-actions.test.js', 'node', '41 passed, 7 failed',
     'hank'),
    ('tests/sairnlegacy_reservation_lock.js', 'node',
     '  ok   ...and every spec\'d resource is one of SAIRNlegacy\'s own 36, '
     'so the map is being read against the right app rather than widening '
     'the loop', 'cody'),
    ('tests/sd_data_write_attribution_three_apps.js', 'node',
     '17 passed, 3 failed', 'cody'),
    # FOUND SEPARATELY, and by a different route: this one reads
    # docs/CRITICALITY-TIERS.md, which b26 edited, so it was driven in BOTH
    # legs specifically to answer "did I break it". **The SAME EIGHT ARMS fail
    # at HEAD and at HEAD~1** -- only the probe's own sliding tail text differs
    # -- so it is pre-existing and unrecorded, like the three above.
    ('tests/run_criticality_tier_probe.py', 'py',
     'FAILED  run_criticality_tier_probe: 8 failed', 'cody'),
)
have = set(x['file'] for x in entries) | set(moved_out)
for f, kind, tail, owner in BASELINE_RED:
    if f in have:
        notes.append(f + ' is already registered -- not added twice')
        continue
    entries.append({
        'file': f,
        'kind': kind,
        'tail': tail,
        'since': '2026-10-19',
        'exit_code': 1,
        'owner': owner,
        'diagnosed': '',
        'diagnosed_by': '',
        'environment': {
            'where': 'disposable git worktree, both legs',
            'pinned': False,
            'tool': 'the suite itself, driven ALONE at HEAD and at HEAD~1, '
                    'one process each',
            'sha': sha,
            'basis': 'RED IN BOTH LEGS OF b26\'s REGRESSION DIFFERENTIAL. '
                     '230 suites referencing api/sd-data.js were driven alone '
                     'at HEAD and at HEAD~1; four came back red-and-'
                     'unregistered and this is one of the three that were '
                     'ALREADY red before the change. Byte-identical output in '
                     'both legs for tests/sairnlegacy_reservation_lock.js; '
                     'identical pass/fail counts for the other two.',
        },
        'why': '',
        'why_empty_means': 'NOT DIAGNOSED. Registered because it is RED AND '
                           'WAS UNRECORDED, which means it would have read as '
                           'a regression for whoever ran next -- an absent row '
                           'reads NEW. THE ENTRY MAKES IT ATTRIBUTABLE AND '
                           'DOES NOT MAKE IT ACCEPTABLE. b26 did not diagnose '
                           'it and an invented cause would be worse than this '
                           'blank, because it would end the investigation.',
        'found_by': 'cody b26 regression differential, 2026-10-19. NOT caused '
                    'by b26: red at HEAD~1 too, measured rather than assumed.',
    })
    added.append(f)

# ── 4. THE 12 TAIL_UNPRODUCIBLE ROWS. RECORDED, NOT OVERWRITTEN. ──────────
# THE CONCEPT: a row whose stored `tail` is not a line the runner can produce
#   reports CHANGED for ever, which b22 says is WORSE than an absent row --
#   but overwriting the stored tail would DESTROY the record of what the row
#   used to claim, and the house convention
#   (docs/2026-10-13-cody-b8-undriven-suite-results.md section 3) is "No
#   entry's `tail` overwritten." So the OBSERVED tail is recorded BESIDE the
#   stored one and the correction is ROUTED, not applied.
#
# AND THAT IS ALSO convention 11 -- human-gated auto-remediation: a detector
# that blesses its own fix is the staleness problem one step later. This script
# MEASURED the mismatch; deciding which of the two strings the register should
# carry is a judgement about what each row is for, and it belongs to whoever
# owns the register.
unprod = 0
for e in entries:
    v = verdicts.get(e['file'])
    if not v or v['verdict'] != 'TAIL_UNPRODUCIBLE':
        continue
    e['tail_verdict_2026_10_19'] = 'UNPRODUCIBLE'
    e['observed_tail_2026_10_19'] = v['observed']
    e['tail_verdict_basis'] = (
        'MEASURED by docs/b26-logs/known_red_tail_census.py at ' + sha
        + ', driven ALONE in a disposable worktree. The stored `tail` above is '
        'NOT the line tools/run_all_tests.py would print for this suite, so '
        'tools/known_red_check.py classifies this row CHANGED on every run -- '
        'which reads as "a second defect is hiding inside an entry that says '
        'this file is expected to fail" when THE ENTRY is the thing that is '
        'wrong (b22 item 4). '
        '**THE STORED `tail` IS DELIBERATELY NOT OVERWRITTEN.** Two reasons, '
        'both conventions rather than preferences: overwriting destroys the '
        'record of what this row used to claim, which the 2026-10-13 b8 scope '
        'statement names ("No entry\'s `tail` overwritten"); and a detector '
        'that applies its own repair is convention 11\'s human-gated '
        'auto-remediation rule read the wrong way. THE CORRECTION IS ROUTED. '
        'Whoever takes it should decide per row whether the right tail is the '
        'observed line or whether the SUITE should print a stable last line.'
    )
    unprod += 1

reg['entries'] = entries
reg['recovered'] = recovered
reg['_b26_2026_10_19_cody'] = (
    'THE KNOWN-RED TAIL CENSUS, ROUTED AT SAIRN-handoff-cody-b22.md 6.6 AND '
    'UNMEASURED THROUGH b23, b24 AND b25. b22 found ONE row whose `tail` had '
    'been an arm list since b19 while the suite\'s last printed line was its '
    'closing expected-red paragraph -- so the two NEVER matched and the row '
    'reported CHANGED, which reads as "a second defect is hiding inside an '
    'entry that says this file is expected to fail" when THE ENTRY is the '
    'thing that is wrong. It did not ask how many others are like that '
    'because "it is not cheap ... and several of those suites WRITE WHEN RUN". '
    'MEASURED NOW: ' + json.dumps(census['summary']) + ' over '
    + str(census['driven']) + ' of ' + str(census['registered_entries'])
    + ' registered entries, each driven ALONE in a DISPOSABLE WORKTREE at '
    + str(census.get('tool')) + '. '
    'THE COMPARISON IS tools/known_red_check.py\'s OWN _same_reason, IMPORTED '
    'RATHER THAN RE-IMPLEMENTED: a census using a different rule from the tool '
    'it audits measures a different thing and can neither confirm nor '
    'contradict it. The tail is built the way tools/run_all_tests.py:942 '
    'builds it -- (stdout or stderr).strip().splitlines()[-1]. '
    'FIVE VERDICTS AND "COULD NOT RUN" IS NOT FOLDED INTO EITHER: '
    'TAIL_MATCHES, TAIL_UNPRODUCIBLE, GREEN_RECOVERED, SKIPPED, TIMEOUT. '
    'PER-ROW DETAIL, with every stored tail beside every observed one: '
    'docs/b26-logs/known_red_tail_census.json. '
    'THE ANSWER b22 6.6 ASKED FOR: **12 of the 49 COMPARABLE rows carry a tail '
    'the runner CANNOT produce.** b22 found ONE; there are twelve. Each is '
    'marked in place with `tail_verdict_2026_10_19` and '
    '`observed_tail_2026_10_19`, and **the stored `tail` is NOT overwritten** '
    '-- the correction is ROUTED, for the two reasons in each row\'s '
    '`tail_verdict_basis`. '
    'AND 5 ROWS WERE GREEN and have been moved to `recovered`, which the '
    'register\'s own rule requires: while such a row stands it swallows the '
    'next real failure of that file. '
    '**THREE CAVEATS, NAMED RATHER THAN BURIED.** (1) THE TIMEOUT WAS 120s, '
    'NOT THE RUNNER\'S 300s. Ten suites timed out at 120s and SOME OF THEM MAY '
    'COMPLETE AT 300s -- so "TIMEOUT 10" is an upper bound on hangs and a '
    'lower bound on completions, and none of the ten is counted as either '
    'matching or unproducible. The 49 "comparable" rows are TAIL_MATCHES + '
    'TAIL_UNPRODUCIBLE only; the 10 timeouts and the 1 skip are excluded from '
    'the denominator rather than folded into it. (2) IT WAS DRIVEN IN A '
    'DISPOSABLE WORKTREE, not in a live clone, because several of these suites '
    'WRITE WHEN RUN -- so an environment-sensitive suite could answer '
    'differently here than in a clone. Each row\'s own `environment` block is '
    'the record of where its verdict came from. (3) THE COMPARISON IS '
    'tools/known_red_check.py\'s OWN _same_reason, which normalises DIGITS '
    'away -- so two different failures whose messages differ only in digits '
    'read as the same, deliberately, and that weakness is inherited here '
    'rather than introduced.'
)

out = json.dumps(reg, indent=1, ensure_ascii=False)

print('KNOWN-RED REGISTRY UPDATE -- b26')
print('  entries   ' + str(len(by_file)) + ' -> ' + str(len(entries)))
print('  recovered ' + str(len(reg['recovered']) - len(moved_out)) + ' -> '
      + str(len(reg['recovered'])))
print('  MOVED OUT (green, so the row would swallow the next real failure):')
for f in moved_out:
    print('    * ' + f)
print('  ADDED (red and unrecorded, so an absent row would read NEW):')
for f in added:
    print('    * ' + f)
for n in notes:
    print('  NOTE: ' + n)
print('  MARKED IN PLACE (tail the runner cannot produce; `tail` NOT '
      'overwritten, correction ROUTED): ' + str(unprod))
print('  census summary recorded: ' + json.dumps(census['summary']))

if len(entries) != len(by_file) - len(moved_out) + len(added):
    print('REFUSED: the entry arithmetic does not add up. NOTHING written.')
    sys.exit(1)
for f in moved_out:
    if f in set(x['file'] for x in entries):
        print('REFUSED: ' + f + ' is in BOTH entries and recovered. A suite in '
              'both lists is counted twice by every tool that reads this '
              'file. NOTHING written.')
        sys.exit(1)

if CHECK:
    print('\n--check: nothing written.')
    sys.exit(0)

# ── newline='' IS NOT OPTIONAL ON THIS PLATFORM ───────────────────────────
# Without it, Python on Windows translates every '\n' to '\r\n' and the
# working tree ends up CRLF while .gitattributes normalises the stored blob to
# LF. `git status` stays clean, nothing prompts, and every later byte
# comparison against this file reports a phantom difference -- the failure
# CLAUDE.md records as producing three false alarms in a single session, and
# which this script produced on its first run.
io.open(REG, 'w', encoding='utf-8', newline='').write(out)
back = io.open(REG, encoding='utf-8', newline='').read()
if back != out:
    print('REFUSED: read back differently from what was written.')
    sys.exit(1)
print('\nWRITTEN, and read back byte-identical. RUN '
      '`python tools/known_red_check.py --fixtures` NEXT.')
sys.exit(0)
