# ROUTED TO cc — the ONE hook `.claude/settings.json` carries: who, when, and what actually authorises it — 2026-10-14, fourth b13

**SUPERSEDED IN PART, 2026-10-14 (fourth b17): THE HOOK THIS DOCUMENT AUDITS
NO LONGER EXISTS.** `.claude/settings.json` now reads `"hooks": {}` at `:166`
and the file is 174 lines, not 187 — the `SessionStart`/`compact` group was
removed and arrived here through hank's merge `3857890a`. **Every
`.claude/settings.json:166-180`, `:167`, `:169`, `:173`, `:174` and `:186`
citation below therefore describes the file AS IT STOOD when this was written
and resolves to different text today.** They are kept rather than renumbered:
a citation to a block that has been deleted cannot be pointed at a line, and
rewriting it would erase the state the audit was about. `_hooks_note` is now at
`:172` and says *"NO HOOKS, AND THE EMPTY OBJECT IS COMMITTED ON PURPOSE"*.
**Consequence for §4.3: the `compact` matcher can never now be observed firing,
so that finding closes by deletion rather than by evidence.** Re-derived by
`scratchpad/cite_recheck_b16.py`; recorded in
`docs/2026-10-14-fourth-b17-citation-recheck-b12-b14.md`.

**READ-ONLY. Nothing was edited.** No hook was added, restored, re-worded or
removed; `.claude/settings.json` is not in this batch's `FILES` and was not
written. `git status --porcelain` was empty before and after every command
below.

---

## 1. WHO MADE IT, AND WHEN

```
CMD git log -1 --format='%h|%an|%ae|%cI|%s' eb53e267
eb53e267|Michael Dibert|mikied68@gmail.com|2026-10-13T17:32:59-04:00|feat(compaction survival): ONE SessionStart hook on matcher compact -- the authorised exception, and not a restoration
```

| | |
|---|---|
| commit | `eb53e267` |
| git author / committer | **Michael Dibert `<mikied68@gmail.com>`** — the only git identity in this repo, so authorship does not identify the session |
| authored | 2026-10-13 **06:25:36** -0400 |
| committed (rebased) | 2026-10-13 **17:32:59** -0400 — an 11-hour gap, so the commit date is the *landing*, not the writing |
| co-author trailer | `Claude Opus 5 (1M context)` |
| **session** | **cc, batch b6** — and this is derived, not assumed, see below |
| files in the commit | `.claude/settings.json`, `docs/2026-10-13-cc-b6-clone-rules.txt`, `tests/run_hook_integrity_probe.py`, `tools/compaction_brief.py`, `tools/hook_integrity_check.py` |

**The session is identified from the claim record, which is the only thing on
this platform that names one:**

```
CMD git log -1 --format='%h %cI' --grep='claims cc' --before=2026-10-13T17:33:00-04:00
c0eb14d7 2026-10-13T06:05:07-04:00
CMD git log -1 --format=%s c0eb14d7 | grep -o "compaction[^.;]*"
compaction-survival SessionStart hook with matcher compact for all six clones -- THE ONE AUTHORISED settings
```

cc's b6 claim, committed **20 minutes before** `eb53e267` was authored, names
this exact hook and calls it *"THE ONE AUTHORISED settings"* change. Two
independent facts agreeing — the claim and the commit — which is what
attribution on this platform is allowed to rest on.

---

## 2. WHAT IS WIRED, EXACTLY

```
CMD python -c "import io,json; print(json.dumps(json.load(io.open('.claude/settings.json',encoding='utf-8'))['hooks'],indent=1))"
```

`.claude/settings.json:166-180` — one event, one group, one command:

| field | value | line |
|---|---|---|
| event | `SessionStart` | `.claude/settings.json:167` |
| matcher | `compact` | `.claude/settings.json:169` |
| command | `python "${CLAUDE_PROJECT_DIR:-.}/tools/compaction_brief.py"` | `.claude/settings.json:173` |
| timeout | `30` | `.claude/settings.json:174` |
| the written rationale | `_hooks_note` | `.claude/settings.json:186` |

Hook **groups: 1, entries: 1.** No other event is wired.

---

## 3. THE FINDING THAT CHANGES THE QUESTION: `docs/2026-10-13-per-gate-skip-design.md` CARRIES NO SessionStart/compact DESIGN

**I was sent to check this hook against "the approved SessionStart:compact
design from `docs/2026-10-13-per-gate-skip-design.md`". That document does not
contain one, and saying so is the finding rather than a reason to stop.**

```
CMD grep -n -i "SessionStart\|compact\|hook" docs/2026-10-13-per-gate-skip-design.md
119:- the **hook-integrity** check — skipping the thing that notices disarmament is
```

**ONE line of 7,449 bytes mentions a hook at all**, and it is
`docs/2026-10-13-per-gate-skip-design.md:119`, in a list of three gates that
must never be skippable — a statement *about* the hook-integrity check, not a
design *for* a hook. The document's own first line is
`# Per-gate named skip, with a required reason — DESIGN ONLY`, and its sections
are the `SAIRN_SKIP` variable, the required reason, the log row, gate ids and
the non-skippable list.

**So the hook has no prose design document, and the authority is mechanical
instead.** Three artefacts, all of which the hook satisfies:

1. **`tools/hook_integrity_check.py:350` `_only_compaction_brief()`** — the
   accepted shape, as code: `set(hooks) == {'SessionStart'}` (`:351`), exactly
   one group (`:354`), `matcher == 'compact'` (`:357`), exactly one command
   (`:360`), and that command names `compaction_brief.py` (`:362`, constant at
   `:347`). The wired entry matches all five.
2. **`.claude/settings.json:186` `_hooks_note`** — the written decision: one
   hook, not a restoration, the 23 cleared hooks stay cleared.
3. **`docs/hooks-disabled-2026-10-13.json`** — required to exist by
   `tools/hook_integrity_check.py:398`, so the exception cannot
   self-certify without the record of what was removed.

**VERDICT, by the tool rather than by my reading:**

```
CMD python tools/hook_integrity_check.py --wiring-only        ->  exit 0
INTENTIONALLY DISARMED -- the ONLY wired hook is the authorised SessionStart/compact compaction brief, and
docs\hooks-disabled-2026-10-13.json records what was removed, by whom and why.
```

`tools/hook_integrity_check.py:675` is the line that prints it.

---

## 4. THREE THINGS FOR cc, EACH WITH `file:line`

### 4.1 `tools/hook_integrity_check.py:366` — the predicate's DOCSTRING still says EMPTY, the code no longer requires it

```
CMD sed -n '365,398p' tools/hook_integrity_check.py
366:    """Is `hooks` present and EMPTY in this clone's settings.json?
377:    SO THE TEST IS DELIBERATELY NARROW: the key must EXIST and be EMPTY. A
393:    if h and not _only_compaction_brief(h):
```

Line `:393` accepts a non-empty `hooks` object when it is the one authorised
entry. Lines `:366` and `:377` still state the opposite, in the imperative.
**This is the one predicate that gates the hooks exception, and its own
documentation now disagrees with it.** An auditor who reads the docstring
concludes the wired hook is drift and that this clone has been tampered with;
an auditor who reads line 393 concludes it is fine. Both are reading the same
function.

**Exact next step:** re-word `:366` and `:377` to the shape the code actually
accepts — present and either empty **or** exactly the compaction entry — or a
`NOT_PROMOTED` entry naming `tools/hook_integrity_check.py:366` and saying the
docstring is left as the historical statement on purpose. **Nothing else closes
it**, because this is a correctness question about a comment, and a comment
cannot be tested.

### 4.2 `docs/hook-manifest.json:12` — `compaction_brief.py` IS NOT IN THE MANIFEST, so the one authorised hook's tool is the one tool nothing checks

```
CMD python -c "import io,json; t=json.load(io.open('docs/hook-manifest.json',encoding='utf-8'))['tools']; print(len(t)); print('compaction_brief.py' in t)"
29
False
CMD grep -c compaction_brief docs/hook-manifest.json
0
```

`eb53e267` added `tools/compaction_brief.py` **and wired it as the only hook**,
and did not add it to the manifest that same commit's own checker reads. The
full run says so itself:

```
CMD python tools/hook_integrity_check.py                      ->  exit 1
  ! TOOL compaction_brief.py is NOT IN THE MANIFEST at all.
  ! TOOL report_sha_check.py is NOT IN THE MANIFEST at all.
  ! TOOL commit_tool_entry_check.py is NOT IN THE MANIFEST at all.
  ! TOOL temp_state_leak_check.py is NOT IN THE MANIFEST at all.
  ! THIS CHECKER ITSELF has drifted from the manifest
  DRIFT (13)
```

**The shape is worse than a missing row.** A tool absent from the manifest is
not compared to anything, so an edit to `compaction_brief.py` — the one program
a hook invokes in every clone, on every compaction — is invisible to the check
built to notice exactly that. `--wiring-only` exits **0** and the full run exits
**1**, and the 0 is the one a reader is likely to quote.

**Exact next step:** `python tools/hook_integrity_check.py --regenerate` in
cc's own clone, which the tool says *names every change*, then commit the
manifest. **Not done from here:** `docs/hook-manifest.json` is the checker's
own expectation file and regenerating it from this clone would have me writing
cc's expectation and blessing my own reading of it — the detector-blesses-its-
own-fix shape. 13 drift findings is also not mine to clear.

### 4.3 UNVERIFIED, and it was unverified when it landed: nobody has seen the `compact` matcher fire

`eb53e267`'s own message says so plainly — *"invoking /compact is a harness
command this session cannot issue, so the matcher half is UNVERIFIED rather
than claimed"*. **That is still true today and I cannot close it either**: I
can read the settings entry and run the tool by hand, and neither of those is
the matcher firing.

**Exact next step:** whoever next survives a real compaction records whether
the 12-line brief appeared, in one line, with the date. That is the only
evidence available for this one, and it costs nothing to capture when it
happens.

---

## 5. WHAT THIS AUDIT DOES NOT SAY

* **It does not say the hook is harmless to performance.** The 23 hooks were
  cleared on 2026-10-11 because they were causing agent compaction; this one
  runs only on the compaction path, which is the argument, not a measurement.
* **It does not say the other five clones carry the same single entry.**
  `.claude/settings.json` is one tracked path, so they will carry it once they
  rebase — and reading another clone's working tree to confirm is not this
  batch's business.
* **It does not say the manifest's other 12 drift findings are safe.** They are
  reported here only because they came out of the same run; they are cc's, and
  I have not triaged them.
