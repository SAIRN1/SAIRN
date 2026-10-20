# HANDOFF — fourth / ted, batch b43, 2026-10-20

**READ THIS FILE ONLY.** It is the whole state. **6 of 6 DONE**, all on
`origin/main` and live-verified, no force, no override of any form. Wrapped
at **~58% real context** (`tools/context_verify.py --digest-line`), with
nothing half-finished.

**EVERY FIGURE NAMES THE COMMAND OR FILE THAT PRODUCED IT. Re-derive before
quoting.**

**THREE THINGS TO READ FIRST:**

1. **The "3 of 17 protected" count was wrong: on the live site, 0 of 17 root
   apps resisted framing.** sairncode and stonedesk only reassigned
   `top.location`. Chrome blocks that from a cross-origin frame without a user
   gesture, so the app keeps rendering. sairnlaw's `frame-ancestors` sits in a
   `<meta>` CSP, which browsers ignore. Measured by driving the attack, not
   by grepping for the control. §3.
2. **sairncode's old buster would also have defeated the new one.** Its catch
   replaced `documentElement.innerHTML` mid-parse, which wiped the guard, and
   the rest of the page parsed back in. It is removed, with a comment saying
   why.
3. **b41's open "one real `cert` write" is closed.** It ran through the real
   login on the demo licence: written, read back from the server, then the
   original was restored byte-identical. §4.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016.jsonl`
(the same session as b41–b42)

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016\scratchpad\b43\`
These are all **re-runnable; pass `https://sairn.vercel.app/` to drive live**:
- `drive_vendor.py`;
- `drive_frame.py`, which frames all 22 pages from a cross-origin parent,
  normal and sandboxed-without-scripts, with `--expect-protected=`;
- `drive_top.py` (top-level still usable);
- `live_design.py` (real login, real write, restore).

Also: `fix_frame.py`, `add_defect.py`, `land.sh`, plus `ffr.raw` (UK SI XML)
and `ada.txt`.

**NO SQL THIS BATCH.**

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| fixes | `91b588a2` vendor ids · `e137c3bc` anti-framing ×16 apps | `git log --author=fx` |
| register | `748ddc2d` vendor · `c19746af` clickjacking · `60bbcf66` re-seat | one record per fix |
| docs | `adafa23a` sairndesign audit §7 | — |
| on origin | **every b43 sha is an ancestor** | `git merge-base --is-ancestor` |
| manifest | **6 done**, validates | `python tools/batch_manifest.py --check --agent fourth --batch b43` |
| force / override | **NONE** | — |

## 2. CLAIMS HELD

**`fourth`: released at the end of this batch.** Held: the 16 app files, the
sairndesign audit doc, the register, the manifest, and the deliverables.
Declared negatives: `stonedesk.html` (hank holds it, re-checked at the end
and still held), `api/`, `tests/`, `tools/`, `vercel.json`, `CLAUDE.md`,
`.claude/skills/`.

## 3. ITEMS 1, 2, 4, 5 — the two fixes and their live proof

**Vendor ids (`91b588a2`).** CONCEPT, stated before the code: *vendor ids
come from the one per-device series counter b42 built for invoices and
employees — `sbNextId('V', vendors)` — so two vendors created in the same
millisecond, or on two devices, can never share an id.* **RED on LIVE 2/9:**
50 vendors in one millisecond got **one** id. **GREEN 9/9, local and live.**

**Anti-framing (`e137c3bc`).** CONCEPT: *each app is invisible until it
proves it is the top window. A `<style>` hides `<html>`, and only a script
that sees `window.self === window.top` removes it. Framed, the app tries to
break out and otherwise stays hidden, so a framed copy — including a
sandboxed frame with scripts off — has nothing to click.*
- **Where it sits:** right after `<meta charset>`. In sairnlaw and sairncode
  it sits **below the CSP meta**, so CSP still precedes every script (this
  is what `tests/sairnlaw_csp.js` 1c checks).
- **RED on LIVE:** **18 of 22** pages clickable when framed.
- **GREEN, local and live:** framed **16/16 hidden in both modes**;
  top-level **16/16 visible and clickable**, with the guard removed and no
  page errors.
- **Node suites:** the 14 failing suites also fail on `origin/main` (checked
  in a throwaway worktree). Two did not, and both are resolved:
  `phi_cache_scoped_to_user` was a could-not-run on uncommitted files (72/72
  after commit), and `sairnlaw_csp` 1c was fixed by placing the guard below
  the CSP.

## 4. ITEM 3 — SAIRNdesign, next increment (audit §7)

**Read first, because it matters: this audit already existed.** b39 wrote
the US half and b41 the EU half (§6). b43 adds the next increment, for the
items the doc itself names as unread:
- **Live B1–B3** on the running app: **9/9**. One real `cert` write, read
  back from the server, then the original was restored byte-identical.
- **UK FFR 1988** (SI 1988/1324, legislation.gov.uk XML) contradicts the US
  predicate on three answers:
  - reg. 3 **includes bedding**;
  - reg. 4's vintage line is **1 Jan 1950**;
  - reg. 14 **pulls second-hand furniture back into scope**. The app's
    vintage flag is that case.
- **2010 ADA Standards** (DOJ PDF) close §5.2. Read: 305.3 is 30×48 in,
  304.3.1 is a 60 in turning space, 403.5.1 is 36 in, 902.3 is 28–34 in,
  and 226.1 is 5 percent. None of these can be computed today, because spec
  items carry no height and projects no occupancy type.
- **New and respecified items:** B4 respecified, **B9** (jurisdiction plus a
  predicate per jurisdiction) and **B10** (layout) added.

## 5. WHAT IS OPEN — EXACT NEXT STEP PER ITEM

1. **stonedesk.html and stonedesk-hr.html are still clickable when framed.**
   Hank holds stonedesk. Next: insert the same block from
   `scratchpad/b43/fix_frame.py`. Place it below any CSP meta, and remove
   stonedesk's late LAYER 4 buster (`stonedesk.html` ~:3122). That buster
   rewrites `body.innerHTML`, the same mid-parse hazard as sairncode's. Prove
   it with `drive_frame.py --expect-protected=stonedesk,stonedesk-hr`.
2. **The four satellites** (`sairndental-book`, `sairndental-complaint`,
   `stonedesk-catalog`, `stonedesk-intake`) were measured with fewer than 2
   controls showing, because they were opened without their URL parameters.
   They are **not proven protected**. Next: drive each with a real parameter.
   Check first whether `sairndental-book` is meant to be embedded on practice
   websites, since a buster would break that.
3. **The header form** (`frame-ancestors` / `X-Frame-Options` in
   `vercel.json`) was not done, by instruction. A browser that ignores the
   inline guard is still unprotected.
4. **sairndesign B4 first half:** add a project occupancy field and a top
   height on dining/work-surface spec items, then check 902.3 plus a 226.1
   N-of-M count. **B9:** a jurisdiction field.
5. **Carried from b42:**
   - timesheet day seven (cody b29, `api/sd-data.js:16290`);
   - `sairnSyncAll` 4xx (hank, `stonedesk.html:19938`);
   - remove fourth's `assigned_overrides` entry once cody has reviewed;
   - stonedesk `INV-'+Date.now()` at two sites.

## 6. PROVED vs LEFT UNPROVEN

**PROVED:** both fixes were RED on live first, then GREEN locally and on
live. One real server write and its restore. Every sha is on origin, with no
force.

**UNPROVEN:**
- Only Chromium was driven. Firefox and Safari framing behaviour was not
  driven.
- No repo suite drives framing; the drive lives in the scratchpad.
- UK Schedules 4, 5 and 7 (test methods and label text) were not read.
- There has been no legal review.
