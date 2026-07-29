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
