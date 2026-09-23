"""Negative control for tests/claims/run_registry_claim_probe.py.

    python tests/claims/run_registry_claim_sabotage_probe.py

Exit 0  every planted defect was refused by the suite
Exit 1  one was not -- the suite does not bite where it says it does
Exit 3  COULD NOT RUN -- never folded into either of the other two

── THE TWO DIRECTIONS THIS CHANGE CAN FAIL IN, AND THEY ARE NOT ALIKE ──────
The live-registry read closes a six-second window between one session's claim
and another session's fetch. It can break two ways:

  QUIETLY -- the registry stops being read and the tool goes back to the
  behaviour that let seven rows of docs/CRITICALITY-TIERS.md be re-tiered
  twice. Nothing errors. Every existing claim probe still passes, because none
  of them knows the registry exists.

  LOUDLY AND WORSE -- the registry becomes a REQUIREMENT. A missing directory,
  a corrupt row or a clone still on the older build starts refusing work.
  Three sessions are using this tool right now, and a new dependency that can
  block a claim is a worse defect than the collision it prevents.

So the mutations are split between them. 1, 2, 4 and 6 are the quiet
direction; 3 and 5 are the loud one -- 5 in particular destroys another
session's row, which is the single property that makes an unlocked registry
safe at all.

STAGED: both tools and the suite, none of them committed when this first runs.
Anchors carry no line endings: this clone's working tree is CRLF and an anchor
ending in a newline would match nothing and report ANCHOR-0 instead of a
finding.

carry_identity=True, AND THE BASELINE TAUGHT ME THAT RATHER THAN THE DESIGN.
The first run went red on four arms inside the worktree while passing in this
clone. sairn_claim.py resolves "who am I" from a marker in the git dir, a
worktree has its own private git dir with no marker, and every invocation
inside it therefore answered differently than it does here -- the same
dependency that had run_push_verify_probe.py dead for four days, met again
from the other side within the hour.
"""
# REQUIREMENT: a claim visible only in the live status registry keeps blocking,
#   and every way that registry can be unavailable keeps leaving the claim tool
#   exactly as it behaved before it existed
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sabotage_harness import run_probe                          # noqa: E402

SUITE = os.path.join('tests', 'claims', 'run_registry_claim_probe.py')
CLAIM = os.path.join('tools', 'sairn_claim.py')
STATUS = os.path.join('tools', 'sairn_status.py')

MUTATIONS = [
    # 1. THE WHOLE CHANGE, REVERTED IN ONE TOKEN. The registry is still read,
    #    still parsed, still correct -- and the result is dropped on the floor
    #    before the overlap loop. This is the quiet direction in its purest
    #    form: no error, no warning, and the six-second window is back.
    ('registry claims stop reaching the overlap loop', CLAIM,
     "    for c in _git + _reg:",
     "    for c in _git:"),

    # 2. The refusal stops saying WHERE the evidence came from. "not pushed
    #    yet" is what tells the reader to go and ask the other session rather
    #    than wait for a fetch, so a block without it is a block nobody can
    #    act on correctly.
    ('the refusal stops naming the registry as its source', CLAIM,
     "                if c.get('_registry'):",
     "                if False:"),

    # 3. THE LOUD DIRECTION, AIMED AT THE GUARD THAT CAN ACTUALLY FIRE.
    #    The first version planted a `raise` in a try/except wrapped around
    #    glob.glob(), and it ran SILENT -- glob returns [] for a missing
    #    directory rather than raising, so nothing could reach that handler.
    #    The handler was DELETED rather than kept, and this now targets the
    #    per-file read, which is what every fail-open arm depends on: one
    #    corrupt row must not take the registry down for the whole session.
    ('a corrupt registry row raises instead of being skipped', STATUS,
     "        except Exception:                                        # noqa: BLE001\n            continue",
     "        except Exception:                                        # noqa: BLE001\n            raise"),

    # 4. Expiry and release stop being honoured on the fast path, so a row
    #    nobody cleaned up blocks work for ever -- the four-hour rule with the
    #    rule taken out, which is worse than having no row at all.
    ('a released or expired registry claim is treated as active', CLAIM,
     "        if not isinstance(c, dict) or c.get('status') != 'active':",
     "        if not isinstance(c, dict):",),

    # 5. THE ONE THAT MATTERS MOST. publish_claims writes a row it does not
    #    own. Ownership-per-key is the entire reason this registry is safe to
    #    write without locking; a tool that writes another session's row
    #    silently erases whatever that session had there.
    # RE-AIMED AFTER THE FIRST VERSION RAN SILENT. It set prev['session'] to
    # another name, which mislabels this session's OWN row and leaves every
    # other file untouched -- damage, but not the damage the arm was about.
    # Writing to another session's PATH is the failure that destroys a row
    # nobody else can recover, and it is what ownership-per-key exists to
    # make impossible.
    ('a session writes a row it does not own', STATUS,
     "        p = path_for(name)\n        prev = {}",
     "        p = path_for('hank')\n        name = 'hank'\n        prev = {}"),

    # 6. The shared FILE stops being its own overlap signal. Today this is
    #    survivable because a path tokenises out of the task prose -- which is
    #    exactly why it needs an arm: the protection is an accident of
    #    spelling, and the arm is what makes it deliberate.
    ('a shared declared FILE stops being an overlap signal', CLAIM,
     "        shared = shared | {'FILE:' + p for p in (a & b)}",
     "        shared = shared",),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS, stage=(CLAIM, STATUS, SUITE), carry_identity=True,
        title='negative control: the live-registry early warning must keep '
              'blocking, and must keep failing open'))
