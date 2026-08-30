# Work claims — one file per session

`<session>.json` per clone: `cc.json`, `hank.json`, `cody.json`, `fourth.json`.
Written by `tools/sairn_claim.py`. Read them with `list`, not by hand.

**One file per session, not one shared file, and that is deliberate.**
`SAIRN-ACTIVE-WORK.md` was a single shared append target until 2026-08-24, when
four sessions appending to one file's end produced repeated merge conflicts in a
single night and it was split per clone. A shared `active-claims.json` rebuilds
that exact failure inside the tool meant to reduce friction between parallel
sessions. Every write here goes to a file exactly one clone touches, so merge
conflicts are impossible by construction.

## Use

    python tools/sairn_claim.py check   sairnfreedom competitive scan
    python tools/sairn_claim.py claim   sairnfreedom competitive scan
    python tools/sairn_claim.py release sairnfreedom
    python tools/sairn_claim.py list

`check` exits 1 when blocked. `claim` runs `check` first and refuses if blocked.

## What it is not

**Not a lock.** Claims travel by git, so a claim is invisible to another clone
until it is pushed *and* that clone fetches. Two sessions starting within the
same minute can still both claim. This narrows a four-hour duplication window to
about a one-fetch window; it does not close it.

**It cannot tell you a claim is being worked**, only that one was made. A
crashed or context-compacted session leaves its claim behind, which is why
claims expire after 4 hours (`SAIRN_CLAIM_STALE_HOURS` to override).

An expired claim can mean the session died — or that the work was finished and
never released. Check before repeating it.

Released claims are kept rather than deleted: "who ran this gate, and when" is
the question the next session actually asks.
