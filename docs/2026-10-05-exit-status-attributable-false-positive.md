# `exit_status_attributable` fires on a correct measurement — repro for CC

**Written 2026-10-05 (Fourth). FOR CC, who owns the hook. Nothing changed.**

The hook is right about the failure it was built for and I am not asking for
it to be weakened. It has a false positive on the exact command shape its own
message tells you to use, and because it fires on *every* such command the
warning is becoming wallpaper — which is the way a good check stops being
read.

---

## 1. What it says to do, and what happens when you do it

The message ends:

> *measure it alone: `<tool> > /tmp/out 2>&1` then read `$?` on its own line.*

That is exactly what this does:

```sh
node tests/sairnlegacy_item_price_lists.js > /tmp/t1 2>&1; echo "price-lists exit=$?"
```

`$?` is expanded by the shell **before** `echo` runs, so the value printed is
`node`'s status. The measurement is correct. The hook still fires:

> *this command runs `tests/sairnlegacy_item_price_lists.js` but its exit
> status will come from `echo` — the status will come from the LAST element,
> `echo`.*

## 2. Why it misfires

The check appears to decide attribution **positionally** — it finds the last
element of the command and reports that the status comes from it. That is true
of the *command's* status and irrelevant to what was printed: the question is
not which process exits last, it is **whether `$?` was read before anything
else could overwrite it.**

Shell expansion order is the fact that settles it, and a positional scan
cannot see expansion order.

## 3. Three shapes, and the hook treats them the same

| # | command | correct? | hook |
|---|---|---|---|
| 1 | `tool > /tmp/o 2>&1; echo "exit=$?"` | **YES** — `$?` expands before `echo` runs | fires |
| 2 | `tool \| tail -3` | **NO** — status is `tail`'s, `$?` never saw the tool | fires (right) |
| 3 | `tool > /tmp/o 2>&1; tail -3 /tmp/o; echo "exit=$?"` | **NO** — `$?` is now `tail`'s | fires (right) |

Shape 1 is the one the message recommends. Shapes 2 and 3 are the real defect.
The discriminator between 1 and 3 is **whether anything runs between the tool
and the `$?` expansion**, not what sits last on the line.

## 4. Smallest repro

```sh
false > /dev/null 2>&1; echo "exit=$?"     # prints exit=1  -- CORRECT
false | cat;            echo "exit=$?"     # prints exit=0  -- the real defect
```

Both trip the hook. Only the second is wrong.

## 5. A suggested discriminator, offered not prescribed

Fire only when **something executes between the measured command and the `$?`
expansion**:

* if the measured command is in a **pipeline** (`|`) whose status is read
  without `PIPESTATUS`/`pipefail` → fire. This is the real class.
* if `$?` appears in the **same statement list** with only a redirect and a
  `;` separating it from the measured command → **do not fire**. Nothing ran
  in between.
* if a command runs between them and `$?` is then read → fire.
* anything the parse cannot decide → fire, with *"could not tell which"*
  rather than the positional assertion. A hook about attribution should not
  assert an attribution it did not establish.

The middle rule alone would remove every false positive I hit today without
weakening shapes 2 or 3.

## 6. Why I am reporting it rather than fixing it

The hook is CC's. It also fires on **every** command in a session that
measures tools carefully, so the cost is not a wrong answer reaching a
document — it is the warning being skimmed, and this check exists precisely
because one was skimmed once. That makes it worth a cheap fix rather than a
tolerated annoyance.

## 7. Where this sits in the pattern

This is the **seventh** confirmed instance this session of a check keying on
**position or surface text** instead of the real signal:

1. the push epilogue `error: failed to push some refs`, present on every
   failure, matched as if it identified one — ten retries on a one-line fix
2. a sabotage loop grepping `^  FAIL`, printing nothing for five mutations
   because the mutated copies failed to **load**
3. `deploy_verify_notify.py` matching the literal `git push`, so the deploy
   check never ran for `push_retry.py` — **fixed**
4. my own misdiagnosis of the SQL preflight as a message-body match, when the
   condition never looked at the message — **corrected**
5. the SQL preflight denying any commit while unrelated SQL sits untracked —
   **written up for hank**
6. the Tier A gate reading a **read-only schema snapshot** as code serving
   ~200 Tier A resources, because the file names every table
7. this

**The standing rule they all point at: go and read the thing that made the
decision.** Not the text it printed, not where the words sit on the line.
