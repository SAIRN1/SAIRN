"""tests/server_wins_hydration.js must REFUSE, not merely agree.

Run: python tests/run_server_wins_hydration_sabotage_probe.py

# REQUIREMENT: the suite guarding server-wins hydration must go RED when any
#   app reverts to the additive/never-overwrite merge, when the
#   pending-first-push carve-out is removed or quietly neutered, when an
#   unreadable synced map stops failing closed, or when the transport stops
#   recording which pushes really landed -- because every one of those failures
#   is SILENT at runtime, and the suite is the only thing that would notice

WHY EACH ARM IS PLANTED IN A REAL APP FILE, PER APP. The rule now exists as
one copy in each of two single-file apps with no shared module. A control that
only sabotaged one of them would prove nothing about the other, and "the same
lines in a second file" is exactly the assumption CLAUDE.md's Ariane 5 note
refuses -- a second copy is not a second opinion.

── WHAT IS PLANTED ────────────────────────────────────────────────────────
  1/2. THE OLD BEHAVIOUR, RESTORED, in each app: a locally-held id is never
       overwritten. This is the state of both files up to 2026-09-21 and the
       state any revert produces.
  3/4. THE CARVE-OUT REMOVED, in each app: every id the server has is
       overwritten, including one whose own first push has never landed. This
       is what "just use whether the server has the id" looks like, and it is
       the reading the carve-out exists to refuse.
  5.   AN UNREADABLE MAP STOPS FAILING CLOSED: a corrupt synced map reads as
       "nothing has ever been seeded", which is permission to overwrite
       everything. The destructive direction, and the one PR 1.11 is about.
  6.   A KEPT RECORD IS MARKED SYNCED ANYWAY: the subtle one. The carve-out
       still appears to work -- the record survives THIS hydrate -- and is
       overwritten on the next one, because being kept recorded it as landed.
       A suite that only ran one hydrate would call this green.
  7.   SEEDING SKIPPED ON AN EMPTY READ: the resource is never marked seeded,
       so every later hydrate re-enters the never-seeded branch and overwrites
       unconditionally -- the carve-out silently never applies again.
  8/9. THE TRANSPORT STOPS RECORDING LANDED PUSHES, in each app: nothing is
       ever synced, so after the first seeding pass no record is ever
       overwritable again. Server-wins becomes inert without a single error.

The suite and BOTH app files are staged into the worktree rather than taken
from HEAD, because none of them is committed when this first runs -- and a
baseline that is red for that reason is a baseline that proves nothing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'server_wins_hydration.js')
LEG = 'sairnlegacy.html'
DSN = 'sairndesign.html'

WINS = "      if(neverSeeded||syncedHere[id]){"
KEPT_COMMENT = ("      // else: pending first push. Keep local, and do NOT record it as synced --")
MAP_USABLE = "  var syncedMap=syncedRead.map,mapUsable=syncedRead.state!=='unreadable';"
SEED_WRITE = "      syncedMap[key]=arr;mapDirty=true;"

MUTATIONS = [
    ("1. [sairnlegacy] THE OLD BEHAVIOUR RESTORED -- a locally-held id is "
     "never overwritten, which is the state of this file up to 2026-09-21",
     LEG, WINS, "      if(false){"),

    ("2. [sairndesign] THE OLD BEHAVIOUR RESTORED -- same revert, in the "
     "second copy of the rule, because a second file is not a second opinion",
     DSN, WINS, "      if(false){"),

    ("3. [sairnlegacy] THE CARVE-OUT REMOVED -- every id the server has is "
     "overwritten, including one whose first push never landed",
     LEG, WINS, "      if(true){"),

    ("4. [sairndesign] THE CARVE-OUT REMOVED -- the same wrong reading, in "
     "the second app",
     DSN, WINS, "      if(true){"),

    ("5. [sairnlegacy] AN UNREADABLE MAP STOPS FAILING CLOSED -- a corrupt "
     "map reads as never-seeded, which is permission to overwrite everything",
     LEG, MAP_USABLE,
     "  var syncedMap=syncedRead.map,mapUsable=true;"),

    ("6. [sairnlegacy] A KEPT RECORD IS MARKED SYNCED ANYWAY -- it survives "
     "THIS hydrate and is overwritten by the next, which a one-hydrate arm "
     "would call green",
     LEG, KEPT_COMMENT,
     "      landed.push(id);\n" + KEPT_COMMENT),

    ("7. [sairndesign] SEEDING SKIPPED ON AN EMPTY READ -- the resource is "
     "never marked seeded, so every later hydrate overwrites unconditionally",
     DSN, SEED_WRITE,
     "      if(landed.length){syncedMap[key]=arr;mapDirty=true;}"),

    ("8. [sairnlegacy] THE TRANSPORT STOPS RECORDING LANDED PUSHES -- nothing "
     "is ever synced, so server-wins goes inert with no error anywhere",
     LEG,
     "      if(action==='write'&&payload&&payload.id!==undefined&&payload.id!==null)legMarkSynced(resource,payload.id);",
     "      if(false)legMarkSynced(resource,payload.id);"),

    ("9. [sairndesign] THE TRANSPORT STOPS RECORDING LANDED PUSHES -- the "
     "same silent inertness, in the second app",
     DSN,
     "      if(action==='write'&&payload&&payload.id!==undefined&&payload.id!==null)sdnMarkSynced(resource,payload.id);",
     "      if(false)sdnMarkSynced(resource,payload.id);"),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='server-wins hydration, and the first-push carve-out, must be '
          'REFUSABLE -- in every app that carries the rule',
    stage=(LEG, DSN),
))
