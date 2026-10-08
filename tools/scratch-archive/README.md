# `tools/scratch-archive/` — one-shot scripts a committed handoff tells you to run

**Added 2026-10-08 (cody), batch 26 item 6.**

**THESE ARE NOT SUPPORTED TOOLS.** They are one-shot scripts written in a session
scratchpad. They are in the repo for exactly one reason: **a committed handoff
names them as the NEXT STEP for an open item**, and a scratchpad lives in
`%TEMP%`. The moment that directory is cleared, the next step becomes
unperformable and the handoff is a instruction nobody can follow.

**THE ADMISSION RULE, so this directory does not become a dumping ground.**
A script lands here only if **both** hold:

1. it is named in a **committed** document, and
2. that mention is an **open NEXT STEP**, not a record of something already done.

Measured 2026-10-08: of **65** scripts I had authored that existed only outside
git, **26** were cited by name in some committed document and only **6** met both
conditions. The other 59 are **registered, not committed** —
`docs/external-files-index.json` carries each one's session, path, size, sha256
prefix and mtime, so a figure quoted from one can be traced even after the
directory is gone.

**WHAT IS HERE AND WHICH OPEN ITEM NEEDS IT**

| file | the open next step it serves |
|---|---|
| `childwatch.py` | name the long-running test file — run it beside the next `--pinned` suite. **The pid-binding bug is fixed**; it has never run against a full suite. |
| `launch_suite.ps1` | launch `--pinned` **detached**, so a harness stop cannot kill it. The only launch shape that has ever produced a completed run. |
| `triage86.py` | re-run a named set of failing probes alone on a clean clone and classify each REAL / ARTIFACT / COULD-NOT-RUN. |
| `analyse_times.py` | read `childwatch`'s live log into per-file durations. |
| `prove_childwatch.py` | prove the watcher sees a named child before trusting a run of it. |
| `inventory.py` | **chain link 1 of 3** — walk the four external places into `i6_raw.json`. |
| `inventory2.py` | **chain link 2 of 3** — re-derive the script list with the repo-copy sandboxes pruned, into `i6_raw2.json`. |
| `build_index.py` | **chain link 3 of 3** — write `docs/external-files-index.json` from the two raws. |

**THE REGENERATION CHAIN, AND TWO OF ITS THREE LINKS WERE MISSING FROM THE FIRST
VERSION OF THIS DIRECTORY.** The index declares itself derived and names its own
command. On 2026-10-08 that command named `scratchpad/b26/build_index.py` and did
not name `inventory.py` at all — so **the generator had excluded itself from its
own population**, and the "derived, not hand-written" claim in the header would
have gone false, silently, on the day that `%TEMP%` directory cleared. Caught by
`tools/external_file_index_audit.py`, which was written for that arm and found it
on its first live run. All three links are committed now and the audit is clean:

    python tools/scratch-archive/inventory.py   --out <scratch>
    python tools/scratch-archive/inventory2.py  --out <scratch>
    python tools/scratch-archive/build_index.py --raw-dir <scratch> --repo <repo>
    python tools/external_file_index_audit.py            # exit 0 CLEAN / 1 finding / 2 could-not-run

**`--out`, `--raw-dir` and `--repo` are REQUIRED with no defaults** (convention
26). `build_index.py` writes into a repo and `inventory2.py` used to drop its raw
beside itself, which was harmless in a scratchpad and became a live-path fallback
the moment it was committed here.

**THEY ARE NOT WIRED INTO ANY SUITE OR GATE, deliberately.** `run_all_tests.py`
discovers `tests/`, not this directory, so nothing here can fail a suite or be
mistaken for a check. If one of these ever earns a standing role it should be
rewritten as a real tool under `tools/` with a fixture, not promoted by moving it.

**PATHS INSIDE THEM ARE ABSOLUTE AND SESSION-SPECIFIC.** They were written to run
from one scratchpad. Read the top of a file before running it; several take their
output directory as an argument and `triage86.py` reads an input TSV it expects
beside itself. **`childwatch.py` carries the fix for its own worst bug in a
comment** — `powershell -Command` does not bind trailing arguments to `param()`,
which made an earlier copy watch pid 0 for 3h13m and report "6 distinct children"
as though that were a finding.
