---
name: sairn-portfolio-triage
description: 'Cheap, mechanical diagnosis of ANY SAIRN app before deciding how much fixing effort it needs. Trigger the FIRST time any app (not just StoneDesk) gets touched in a session, even for a small unrelated task. Runs the 4 scanners built during StoneDesk''s fabrication sweep against a real-time report showing whether an app is nearly clean or has a real problem — before committing hours to finding out the hard way.'
---

# SAIRN Portfolio Triage

StoneDesk had 468 real missing-DOM-target findings, dozens of storage-key collisions, and multiple silent function-name collisions — all invisible until someone actually ran the right tools. That discovery took an entire session's worth of manual tracing before the real scale was known. This skill exists so the *next* app never needs that: get the honest number in minutes, before deciding anything.

## When to run this

The first time in a session that ANY SAIRN app's HTML file gets opened for real work — even if the actual task is small and unrelated to code quality. Don't wait until something looks suspicious; run it as routine reconnaissance, the same way a mechanic pulls codes before touching anything specific.

## The four scanners (already built, reusable — not StoneDesk-specific)

- `tools/duplicate_global_check.py` — function/variable names declared more than once, silently shadowing each other
- `tools/missing_dom_target_check.py` — functions referencing a container/element id that doesn't exist in markup
- `tools/panel_nesting_check.py` — panels trapped inside the wrong parent, invisible despite correct nav dispatch
- `tools/key_collision_check.py` — two independent functions writing the same storage key with different shapes

Run each against the target app's HTML file, e.g.:

```
python tools/duplicate_global_check.py <app>.html
python tools/missing_dom_target_check.py <app>.html
python tools/panel_nesting_check.py <app>.html
python tools/key_collision_check.py <app>.html
```

## Scanner Portability (added 2026-07-30)

"Reusable, not StoneDesk-specific" above was aspirational, not verified, the first time these scanners were written — and it turned out to be false for two of the four until fixed in `ce43609`. **Before trusting a raw count from any scanner on a second app, confirm it was actually validated against a second app, not just written generically and assumed to generalize.** A scanner tuned against one codebase's specific conventions can look general-purpose while silently encoding assumptions from the app it was built against.

Two confirmed, real failures from this exact mistake:

- **`panel_nesting_check.py` — identical-100%-trapped false positive.** `SAFE_PARENTS` was hardcoded to StoneDesk's own container class names (`div#.app-body`, `div#.panel-wrap`). Run against `sairnbiz.html` (`main#main`) and `sairncode.html` (`div#.container`) — both structurally fine apps — every single panel in both came back "trapped," 20/20 and 20/20. A 100%-failure result across two unrelated apps, especially an *identical* shape of failure, is itself the tell that the scanner is broken, not that both apps independently have the same total-failure bug. Fixed by generalizing to "a parent shared by 2+ panels is safe" instead of a hardcoded class list.
- **`duplicate_global_check.py` — silent undercount, not a crash.** No regex-literal awareness in the brace-depth scanner meant a line like `.replace(/'/g,'&#39;')` desynced string-tracking for the rest of the block, silently dropping every function declared after that point from the count. This one is more dangerous than the panel_nesting failure precisely because it didn't fail loudly — `sairnbiz.html` reported 2 global functions when the real count was 52, a plausible-looking low number, not an obvious 0 or a crash. It was only caught because a re-run for an unrelated fix happened to also affect `stonedesk.html`'s own count (513→685), which was the actual tell — a scanner's number changing on a file nobody touched is a bug-fix signal, not a data-drift signal.

**The practical rule:** the first time any scanner (old or newly written) runs against a *second* app, don't just record the number — sanity-check it. A suspiciously round, suspiciously total (0%, 100%), or suspiciously low count deserves the same "does this look believable" gut-check as a fabricated KPI would (see `sairn-guardian-v2` Check 0b) before it gets reported as the app's real baseline.

**Third example, found live the first time this rule was applied (2026-07-30):** `key_collision_check.py` and `missing_dom_target_check.py` both returned a literal `0` against `sairnbiz.html` on first run — `TOTAL_KEY_WRITES:0` and `TOTAL_GETELEMENTBYID_CALLS:0`. Both are blind zeros, not clean zeros: SAIRNbiz routes storage and DOM access through wrapper functions (`st(k,v){localStorage.setItem(k,JSON.stringify(v))}`, `ld(k,d){...localStorage.getItem(k)...}`, `$(s){return document.getElementById(s);}`) instead of StoneDesk's direct `localStorage.setItem('literal_key', ...)`/`document.getElementById('literal_id')` calls — both scanners' regexes only match the direct-call form, so they never even see SAIRNbiz's 16+ real `st('sb_...', ...)` writes. This is exactly the failure this section warns about, caught only because a `0` against a 52-function, 20-panel app was suspicious enough to grep-verify by hand before reporting it as a real result. Neither scanner has been generalized to recognize wrapper-function indirection yet — treat their output as StoneDesk-only-reliable until that's fixed, and manually grep for an app's actual storage/DOM-access convention before trusting a `0` from either.

**Upgraded 2026-08-07 — all three confirmed-broken scanners fixed for real, tested against all 4 apps in the portfolio (stonedesk, sairnbiz, sairngrounds, sairnscape), not just the one that exposed each bug:**

- **`panel_nesting_check.py` — hardcoded `'panel-'` id prefix.** Silently returned `NO_PANELS_FOUND` on `sairnscape.html`, an app with 11 real, structurally fine panels namespaced `id="scp-panel-X"` instead of the bare `panel-X` every other app in the portfolio happens to use. Fixed: a first HTML-parser pass collects every `<div id="PREFIXpanel-NAME">` and picks PREFIX by majority vote across the file, instead of assuming `''`. Result: `stonedesk`/`sairnbiz`/`sairngrounds` still correctly detect `'panel-'` (62/20/21 panels, 0 trapped each); `sairnscape` now correctly detects `'scp-panel-'` (11 panels, 0 trapped) instead of reporting nothing.
- **`missing_dom_target_check.py` — hardcoded single wrapper name (`sv`).** Only matched literal `getElementById(...)` plus one StoneDesk-specific wrapper name. Missed `sairnscape.html`'s real DOM-access wrapper, `scp$(s){return document.getElementById(s);}`, entirely — 261 real call sites (the overwhelming majority of that app's actual DOM access) were invisible, so its "0 missing" result was a blind zero. Fixed: any function whose body calls `document.getElementById(PARAM)` using its own first parameter is now auto-detected as a DOM wrapper for that file, whatever it's named. Building this fix reintroduced (and then closed, same session, before commit) the exact regex-literal brace-desync bug `duplicate_global_check.py` had already fixed in `ce43609` — a naive quote scanner mistakes the `'` inside `.replace(/'/g,'&#39;')` for a real string start and silently swallows tens of thousands of characters as one function's "body". Ported the same regex/division disambiguation heuristic rather than re-deriving a fix. Also found and fixed, live, while testing: a `\b` word-boundary check silently fails to match a wrapper name starting with `$` (not a `\w` character), and a wrapper call regex with no boundary on the *end* of the string argument was flagging concatenated calls like `$('panel-'+id)` as a complete reference to a literal id `"panel-"`. Result: `sairnbiz`/`sairngrounds`/`sairnscape` all now show 0 real missing targets (verified independently by hand before trusting the fixed scanner's own output); `stonedesk`'s pre-existing 184 is unchanged.
- **`key_collision_check.py` — same wrapper-blindness class, plus the same regex-literal bug, plus a literal-keyword false positive.** Only matched literal `localStorage.setItem(...)`, so it returned `TOTAL_KEY_WRITES:0` against `sairngrounds.html` (31 real distinct keys, all written through `st(k,v)`) — a blind zero. Fixed with the same auto-detect-the-wrapper-by-tracing-its-body approach as the DOM-target checker, plus the same regex-literal-aware brace scanner. One more real false-positive class surfaced once wrapper detection actually started returning results: `null`/`true`/`false`/`undefined` parse as bare identifiers under the existing "named variable" regex, so a normal `st('sb_role', prole)` on login next to `st('sb_role', null)` on logout was flagged as a fake "collision" (two different backing variables) on `sairnbiz`/`sairngrounds`/`sairnscape` alike — fixed by excluding the four JS literal keywords from the competing-variable check, same treatment as the existing inline-`{}`/`[]`-reset exclusion. Genuine collisions (2+ real named variables writing the same key) still surface: `sairngrounds`/`sairnscape` both showed several after the fix, but manual tracing found most resolve to the SAME underlying `ld('KEY',[])`/wrapper-getter call under two different local variable names (e.g. `grd_schedule`'s `list` vs `sched` both come from `bldSched()`) — a real, still-open limitation of the variable-name-only heuristic, not a new bug this fix introduced; treat any collision report as a lead to trace by hand, not a confirmed bug, same standard this section has always held for scanner output.
- **`duplicate_global_check.py` — audited, genuinely clean, not changed.** Already fixed for regex-literal desync in `ce43609`; its two declaration patterns (`function NAME(`, `window.NAME = function(`) are generic, not app-specific. Re-run against all 4 apps: 708/86/221/144 depth-0 globals, 0 duplicates each — consistent with known baselines and each other. No hidden assumption found; per this section's own standard, a clean tool doesn't get changed just because its siblings needed fixing.

## Output format

A simple table, one row per app checked:

| App | Duplicate Globals | Missing DOM Targets | Trapped Panels | Key Collisions |
|---|---|---|---|---|
| stonedesk.html | 0 | 411* | 0/61 | 0 |

*StoneDesk's number after triage — most turned out dormant/harmless, real reachable-and-broken count was much lower. Report the raw scanner count here; the triage-into-severity step happens after, not as part of this baseline.

## What this does NOT do

This is diagnosis only — do not start fixing anything based on this baseline alone. A high number doesn't mean "spend a whole session on it right now" any more than StoneDesk's raw 468 did; it means "now we know the real shape of the problem," which is the actual prerequisite for deciding how much time it deserves. Follow with the same triage StoneDesk went through (reachable-and-broken vs. dormant, mechanical-fixable vs. needs-real-judgment) before committing effort.

## The point

Fear of an unknown problem costs more than the problem usually does once it's actually measured. Five minutes of scanning turns "this app might be as bad as StoneDesk was" into a real, specific, actionable number — cheap certainty instead of expensive dread.
