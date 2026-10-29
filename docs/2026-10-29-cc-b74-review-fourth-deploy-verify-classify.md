# cc b74: Tier A review of fourth's `classify_command()` (taken over from cody)

**LEDGER NOTE (added at push time):** cody discharged this same record on origin at 2026-10-29T18:56:37Z (SOUND-WITH-GAPS, cody b65) before this takeover landed. The ledger keeps cody's verdict. This file is an independent second review; its FAIL finding (attack point 2) is not in cody's verdict and is routed to fourth.

**The record.** fourth opened it 2026-10-05T15:02:28Z. The resource is
`quotes` (the gate matched the word) and the file is
`tools/deploy_verify_notify.py`. The anchor is `9cc58a00`, reseated from
`13e40c9d`.

The change replaced the literal `"git push" in cmd` entry test with
`classify_command()`, which returns `push`, `not-a-push` or `unsure`. The
record was assigned to cody and held 580h, the most overdue on the list.
`tools/deploy_verify_notify.py` has had no later commits:
`git log 9cc58a00..HEAD -- tools/deploy_verify_notify.py` prints nothing.

**VERDICT: FAIL on attack point 2 (MEDIUM). Attack points 1 and 3 PASS.**
The fix is routed to fourth, the author.

## Attack point 2: the `_MENTION_ONLY` line-prefix heuristic

**FAIL. It goes the UNSAFE direction.**

The heuristic tests whether the LINE starts with `echo `, `cat `, `#` or
`grep `. So a real push chained after one of those on the same line is
classified `not-a-push`. The deploy check is then skipped silently, which is
the exact defect this change was written to remove.

The record says a mention-only false positive "is the safe direction". That
is true, but the converse case is a false negative, and nothing tested it.

**The command** (probe committed beside this file):

    python docs/2026-10-29-cc-b74-classify-command-probe.py.txt

**Its literal output:**

```
ok   want=push                 got=push       git push origin main
ok   want=push                 got=push       cd /x && git push origin main
ok   want=push                 got=push       git -c http.version=HTTP/1.1 push origin main
BAD  want=push                 got=not-a-push echo "pushing now" && git push origin main
BAD  want=push                 got=not-a-push echo start; git push origin main
BAD  want=push                 got=not-a-push grep -n x f.txt || git push origin main
ok   want=not-a-push|unsure    got=unsure     echo "git push origin main"
ok   want=not-a-push|unsure    got=unsure     git log --oneline push
ok   want=not-a-push|unsure    got=unsure     git stash push -m wip
ok   want=push                 got=push       python tools/push_retry.py
3 of 10 wrong
EXIT=1
```

**The fix, for fourth:** decide per shell segment, not per line. Split each
line on `&&`, `||`, `;` and `|`, outside quotes. Then a segment that is itself
`git ... push` counts as `push` even when an earlier segment is an `echo`.
Add the three BAD rows above as arms in `tests/run_deploy_verify_entry_probe.py`.

**Cause tag:** a mention-filter scoped wider than the thing it filters. The
exemption is decided for the whole line, and the push is one segment of it.

## Attack point 1: is a fifth pushing tool missing from `PUSHING_TOOLS`?

**PASS.**

**The command:**

    grep -rnE "\(\s*['\"]push['\"]|'git', *'push'|\"git\", *\"push\"|git\('push'" tools/*.py

**What it found that is not one of the four listed tools:**
- `install_git_hooks.py:100` pushes `--dry-run` to a temporary bare repo.
- `prepush_refline_repro.py:180` pushes into a sandbox work dir.
- `push_timeout_guard.py` and `rewrite_convergence_map.py` only match fixture
  strings.

None of these pushes to the deployed origin.

`tools/gh_push.py` (a REST push) is not a `git push`, but its name contains
`push`, so it scores `unsure` and prints a notice. It is not a silent skip.

**The suite:**

    python tests/run_deploy_verify_entry_probe.py

**Its literal tail:**

```
  ok   C3. every tool in PUSHING_TOOLS actually runs a push -- a stale name here is a push the hook would claim to cover and does not

21 passed, 0 failed
EXIT=0
```

**Residual risk:** C3 still checks only the named tools. Nothing fails when a
new pusher is added. That degradation is accepted, as the record proposed,
because it degrades to `unsure`, which prints a notice, rather than to a
silent skip.

## Attack point 3: the `key=value` token between `git` and `push`

**PASS.** The probe rows above show it:
- `git -c http.version=HTTP/1.1 push origin main` gives `push`;
- `git log --oneline push` and `git stash push -m wip` give `unsure`, not
  `push`.

The pattern needs every token before `push` to be a flag or a `k=v`, so a
subcommand such as `log` or `stash` breaks the match. A false positive here
would only run a notify-only check.
