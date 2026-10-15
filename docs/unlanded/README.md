# Unlanded work, preserved as patches rather than dropped

A `git stash` is invisible to every other clone, survives no rebase anyone
else does, and is lost outright when somebody "clears the stashes". This
directory is where a stash goes when the instruction is to clear it and the
stash turns out to carry work rather than dirt.

**Reading a stash before dropping it is the whole point.** cc b12 was told to
clear two stashes. There was one, and `git stash show --stat` said it was 260
added lines across six `tools/` files -- the shared open-work row reader from
b6 item 5, which never landed. Dropping it on the instruction's word would
have destroyed it and nothing would have said so.

## 2026-10-13-cc-b6-open-work-shard-read-rows.patch

From `stash@{0}` (`4919942a`, WIP on `229d582e`, 2026-10-13). 366 lines.

**What it does.** Adds `read_rows()` to `tools/open_work_shard.py` -- one
reader for `docs/SAIRN-OPEN-WORK-INDEX.md`'s pipe rows, reading the SHARDS
rather than the 2.38MB monolith, returning each row with its shard and line
number -- and converts five call sites to it: `dispatch_state.py`,
`independence_check.py`, `index_duplicate_check.py`, `stale_row_sweep.py`,
`traceability_matrix.py`.

Its own comment states the fallback and why it is loud: a clone that has not
fetched since the shards landed has no `docs/open-work/`, and a reader that
returned zero rows there would make `index_duplicate_check` report CLEAN. The
`source` field names which it used.

**Why it is not landed here.** cc b12's dispatch did not ask for it. It is a
six-file `tools/` change with no probe driven against it in this batch, and
landing unverified work at the end of a batch to tidy a stash is the wrong
trade. The content is now in git, which is the only property the stash did not
have.

**To apply:**

    git apply docs/unlanded/2026-10-13-cc-b6-open-work-shard-read-rows.patch

Then drive the five converted call sites and `python tools/open_work_shard.py
--check`, which proves the shards are byte-identical to the monolith and exits
1 if they ever stop being.
