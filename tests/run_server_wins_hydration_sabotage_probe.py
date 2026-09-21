"""tests/server_wins_hydration.js must REFUSE, not merely agree.

Run: python tests/run_server_wins_hydration_sabotage_probe.py

# REQUIREMENT: the suite guarding server-wins hydration must go RED when any
#   of the SEVEN apps reverts to the additive/never-overwrite merge, when the
#   pending-first-push carve-out is removed or quietly neutered, when the
#   one-time bootstrap fails to record what a device already holds or records
#   something it does not, when it overwrites during its own pass, when an
#   unreadable map stops failing closed, or when an auto-push app's store seam
#   stops suppressing -- because every one of those failures is SILENT at
#   runtime and this suite is the only thing that would notice

WHY THE MERGE IS SABOTAGED IN ALL SEVEN APPS. The rule exists as one copy per
single-file app. A control that sabotaged one and inferred the rest is the
assumption CLAUDE.md's Ariane 5 note refuses: a second copy is not a second
opinion. The BOOTSTRAP mutations are planted in one app each, because the
suite's same-rule arm independently proves the other six are byte-identical
once names are normalised -- that is a different argument from inference, and
it is the argument being relied on.

── WHAT IS PLANTED ────────────────────────────────────────────────────────
  1-7.  THE OLD BEHAVIOUR, RESTORED, in each of the seven apps: a locally-held
        id is never overwritten. This is the state of every one of these files
        before 2026-09-21 and the state any revert produces.
  8.    THE CARVE-OUT REMOVED: every id the server has is overwritten,
        including one whose own first push has never landed. This is what
        "just use whether the server has the id" looks like.
  9.    A KEPT RECORD IS MARKED SYNCED ANYWAY. The subtle one: the carve-out
        appears to work -- the record survives THIS merge -- and it is
        overwritten by the next, because being kept recorded it as landed.
  10.   THE BOOTSTRAP SKIPS MARKING A PRE-EXISTING ID. The first of the two
        the decision specifically asked to be controlled. Its consequence is
        NOT an overwrite: an unmarked id is ABSENT from the map, and after the
        bootstrap absent means PROTECTED -- so a pre-existing record becomes
        permanently unreachable by a server correction. That is the additive
        defect returning silently, for exactly the data the bootstrap exists
        to bring under the rule.
  11.   THE BOOTSTRAP MARKS AN ID THAT IS NOT THERE, by dropping the guard on
        records with no id -- which marks the string 'undefined' as seeded.
        The second one asked for, and its consequence IS an overwrite: the
        first real record that arrives without an id is overwritable by a
        stranger's row. Nothing at runtime would ever report it.
  12.   THE BOOTSTRAP OVERWRITES DURING ITS OWN PASS, by not setting the
        this-load flag. The whole point of the read-only bootstrap is that the
        upgrade itself discards nothing; this is the version that does.
  13.   THE BOOTSTRAP RUNS OVER AN UNREADABLE MAP, seeding from a map it could
        not read and then writing the done-flag -- so the real map is lost and
        the bootstrap can never run again.
  14.   THE DONE-FLAG SURVIVES A FAILED MAP WRITE: the bootstrap is recorded
        as complete when nothing was recorded, and it will never run again.
  15.   AN UNREADABLE MAP STOPS FAILING CLOSED in the merge -- a corrupt map
        read as permission to overwrite everything. PR 1.11.
  16.   AN AUTO-PUSH APP'S STORE SEAM STOPS SUPPRESSING, so every hydrated row
        is echoed straight back to the server. Silent, and only visible under
        load.

All seven app files and the suite are staged into the worktree rather than
taken from HEAD, because none of them is committed when this first runs -- and
a baseline that is red for that reason is a baseline that proves nothing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'server_wins_hydration.js')

APPS = [
    ('sairnlegacy',  'sairnlegacy.html',  'leg'),
    ('sairndesign',  'sairndesign.html',  'sdn'),
    ('sairnlaw',     'sairnlaw.html',     'law'),
    ('sairnsenior',  'sairnsenior.html',  'sen'),
    ('stonedesk',    'stonedesk.html',    'sd'),
    ('sairnbiz',     'sairnbiz.html',     'sb'),
    ('sairnfreedom', 'sairnfreedom.html', 'sf'),
]
FILES = tuple(f for _, f, _ in APPS)

WINS = "    if(!%sBootstrappedNow&&usable&&seeded[id]){"
LEG = 'sairnlegacy.html'

MUTATIONS = []

for i, (app, f, p) in enumerate(APPS, start=1):
    MUTATIONS.append((
        "%d. [%s] THE OLD BEHAVIOUR RESTORED -- a locally-held id is never "
        "overwritten, which is the state of this file before 2026-09-21" % (i, app),
        f, WINS % p, "    if(false){"))

MUTATIONS += [
    ("8. [sairnlegacy] THE CARVE-OUT REMOVED -- every id the server has is "
     "overwritten, including one whose first push never landed",
     LEG, WINS % 'leg', "    if(true){"),

    ("9. [sairnlegacy] A KEPT RECORD IS MARKED SYNCED ANYWAY -- it survives "
     "THIS merge and is overwritten by the next, which a one-merge arm would "
     "call green",
     LEG,
     "    // else: pending first push, or the bootstrap load. Keep local, and do NOT",
     "    landed.push(id);\n"
     "    // else: pending first push, or the bootstrap load. Keep local, and do NOT"),

    ("10. [sairnlegacy] THE BOOTSTRAP SKIPS MARKING A PRE-EXISTING ID -- the "
     "id stays ABSENT, absent means protected, and a pre-existing record is "
     "permanently unreachable by a server correction",
     LEG,
     "      if(arr.indexOf(id)===-1)arr.push(id);\n    }\n    map[key]=arr;",
     "      if(false)arr.push(id);\n    }\n    map[key]=arr;"),

    ("11. [sairnlegacy] THE BOOTSTRAP MARKS AN ID THAT IS NOT THERE -- the "
     "no-id guard is dropped, 'undefined' is seeded, and the first real "
     "record without an id becomes overwritable by a stranger",
     LEG,
     "      if(!rec||rec.id===undefined||rec.id===null)continue;",
     "      if(!rec)continue;"),

    ("12. [sairnlegacy] THE BOOTSTRAP OVERWRITES DURING ITS OWN PASS -- the "
     "upgrade discards whatever local edit was sitting there, which is the "
     "exact cost the read-only bootstrap was chosen to avoid",
     LEG, "  legBootstrappedNow=true;\n  return 'ran';",
     "  legBootstrappedNow=false;\n  return 'ran';"),

    ("13. [sairnlegacy] THE BOOTSTRAP RUNS OVER AN UNREADABLE MAP -- it seeds "
     "from a map it could not read and writes the done-flag, so the real map "
     "is lost and it can never run again",
     LEG,
     "  if(r.state==='unreadable')return 'unreadable';   // never bootstrap over a map we could not read",
     "  // guard removed"),

    ("14. [sairnlegacy] THE DONE-FLAG SURVIVES A FAILED MAP WRITE -- the "
     "bootstrap is recorded complete when nothing was recorded",
     LEG,
     "  if(!st(LEG_SYNCED_KEY,map))return 'unreadable';  // the flag must NOT outlive a failed map write",
     "  st(LEG_SYNCED_KEY,map);"),

    ("15. [sairndesign] AN UNREADABLE MAP STOPS FAILING CLOSED -- a corrupt "
     "map reads as permission to overwrite everything",
     'sairndesign.html',
     "  var map=r.map,usable=r.state!=='unreadable';\n  var seeded={};",
     "  var map=r.map,usable=true;\n  var seeded={};"),

    ("16. [sairnfreedom] THE STORE SEAM STOPS SUPPRESSING -- every hydrated "
     "row is echoed straight back to the server, silently",
     'sairnfreedom.html',
     "function sfHydrateStore(key,value){\n"
     "  var was=sfSyncSuppressed;\n"
     "  sfSyncSuppressed=true;\n"
     "  try{ return st(key,value); } finally { sfSyncSuppressed=was; }\n"
     "}",
     "function sfHydrateStore(key,value){\n"
     "  return st(key,value);\n"
     "}"),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='server-wins hydration, its first-push carve-out and its one-time '
          'read-only bootstrap must all be REFUSABLE -- in every app that '
          'carries the rule',
    stage=FILES,
))
