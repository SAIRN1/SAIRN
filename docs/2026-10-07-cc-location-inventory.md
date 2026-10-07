# Location inventory -- build-agent tools, skills, methodology, shared settings

**Item 7, 2026-10-07 (cc). READ-ONLY: every operation was a read or a stat.
No moves, no edits.** Generated output of a scratch script, pasted verbatim
rather than retyped, so the numbers are the program's.

**The seven sibling clones were DERIVED by globbing for a `.git`, not read
from a list** -- `CLAUDE.md` once named four for weeks after a fifth existed
and was pushing commits, and the correction it carries is in capitals:
count the directories.

```
LOCATION INVENTORY -- READ-ONLY. 7 sibling clone(s) found by globbing for a .git: 
    C:\Users\marsh\Documents\SAIRN
    C:\Users\marsh\Documents\SAIRN-cody
    C:\Users\marsh\Documents\SAIRN-fourth
    C:\Users\marsh\Documents\SAIRN-hank
    C:\Users\marsh\Documents\SAIRN-hover
    C:\Users\marsh\Documents\SAIRN-hover2
    C:\Users\marsh\Documents\trading-bot

what                       where        owner      exists  visible from a sibling clone
build-agent tools          CLONE        -          yes     6 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
tool tests / probes        CLONE        -          yes     5 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
git hooks (repo copy)      CLONE        -          yes     5 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
hook + permission wiring   CLONE        CLAIMED:co yes     6 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
local wiring override      CLONE        -          yes     6 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
skills, repo mirror        CLONE        -          yes     6 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
subagent definitions       CLONE        -          yes     6 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
claim records              CLONE        -          yes     5 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
methodology                CLONE        CLAIMED:ha yes     5 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
cross-domain disciplines   CLONE        -          yes     5 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
process rules              CLONE        -          yes     5 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
project primer             CLONE        -          yes     6 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
open-work index            CLONE        CLAIMED:ha yes     5 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
tool owner map             CLONE        -          yes     5 of 7 siblings hold the same relative path -- SEPARATE COPIES, not shared
skills, USER STORE         SHARED HOME  -          yes     YES -- shared by construction, every clone sees the same bytes
user-level settings        SHARED HOME  -          yes     YES -- shared by construction, every clone sees the same bytes
global primer              SHARED HOME  -          yes     YES -- shared by construction, every clone sees the same bytes
auto-memory                SHARED HOME  -          yes     YES -- shared by construction, every clone sees the same bytes
status registry + locks    SHARED HOME  -          yes     YES -- shared by construction, every clone sees the same bytes

  tools/*.py in this clone        : 305
  repo-mirrored skill dirs        : 34
  USER-STORE skill dirs           : 62
  claim record files              : 7

THE DISTINCTION THAT MATTERS, stated rather than left implied:
  * A CLONE path exists once PER CLONE. Editing it changes nothing for
    any other session until it is committed and they pull.
  * A SHARED HOME path is ONE SET OF BYTES for every session on this
    machine. Editing it takes effect immediately, everywhere, with no
    commit, no pull, and no claim record able to protect it -- the claim
    system only covers paths inside the repo.
  * THE STATUS REGISTRY IS DELIBERATELY IN THE HOME FOLDER, which is
    why it is current without a fetch. That is the whole design.

BLIND SPOTS:
  - this lists the locations I know to look for; a tool or skill kept
    somewhere else entirely is invisible here
  - "visible from a sibling clone" means the PATH exists there, NOT
    that the bytes match. Two clones can both hold tools/x.py at
    different commits and this reports both as present
  - the hover auditor clones are siblings and are INCLUDED in the count
    above; a build agent must not write into them, and this tool only
    reads
```
