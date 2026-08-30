# The `target="_blank"` + sessionStorage auth class, swept platform-wide

**Question:** the StoneDesk → `/stonedesk-hr` link was found broken earlier today
because Chrome does not carry sessionStorage into a tab opened from a link. Is
that bug class present anywhere else on the platform?

**Answer: no. It is a one-instance class and the instance is fixed.** But the
sweep found two real defects of a *different* class in the code it had to read
to answer, and those are the part worth acting on.

---

## 1. The class, and why only one page could ever have it

The bug needs three things at once: a **same-origin** destination, opened in a
**new tab**, whose auth is read from **sessionStorage written by a different
page**. All thirteen apps share one origin (`sairn.vercel.app`), so the first
condition is met platform-wide and the other two decide it.

**The detector.** For every `*.html`, list the sessionStorage keys the file
*reads* and subtract the keys it *writes*. A page that reads a session key it
never writes is depending on a sibling page — the exact shape.

Four hits, three of them false positives, each checked rather than assumed:

| File | Key | Verdict |
|---|---|---|
| `stonedesk-hr.html` | `sd_session_token`, `sd_session_role` | **Real.** Reads only, never writes. This is the known instance — **fixed** to same-tab `<a href="/stonedesk-hr">` at `stonedesk.html:28308` |
| `sairnbiz.html` | `sb_session_token` | False positive — written via the `SB_SESSION_KEY` constant at `:1197` and `:1233` |
| `stonedesk.html` | `sd_sub_session_token` | False positive — written via `SD_SUB_SESSION_KEY` at `:31461` |

The detector matches literal strings, so a write through a constant reads as
absent. **That is the detector's own blind spot, disclosed rather than papered
over** — it produces false positives, never false negatives, which is the safe
direction for this check.

## 2. The other two conditions, checked directly

**Every `target="_blank"` on the platform points off-site.** Extracted the
`href` paired with each one across all nineteen HTML files: `osha.gov`,
`irs.gov`, `uscis.gov`, `stoneworld.com`, `naturalstoneinstitute.org`,
`google.com/maps`, and dynamic `source_url` / `authority.url` values that are
external citations by construction. **Zero internal same-origin new-tab links
exist.**

**The one internal new-tab set is safe, though partly by accident.** The SAIRN
Suite modal fires `window.open('https://sairn.vercel.app/<app>','_blank')` eight
times (`stonedesk.html:15392–15420`), and `sairnmechanical.html:1066` does the
same. Those destinations authenticate on *different* keys — `sb_session_token`
and siblings — which StoneDesk never writes. There is nothing to inherit, so
nothing is lost. It would break the moment two apps shared a token key.

**The cross-app NEXUS handoff is correct.** `sendHandoff` uses
`window.location.href = cell.file` — same-tab — which preserves sessionStorage
by the same rule that fixed the HR link.

## 3. Finding 1 — the NEXUS handoff navigates to nine files that do not exist

`CELL_MAP` (`stonedesk.html:17867`) lists nine destinations:

    /index.html  /health.html  /money.html   /legal.html  /study.html
    /lingual.html  /senior.html  /home.html  /roam.html

**None of them are in this repo.** `vercel.json` routes none of them. Confirmed
live rather than inferred from the file list:

    GET https://sairn.vercel.app/legal.html    -> 404
    GET https://sairn.vercel.app/health.html   -> 404
    GET https://sairn.vercel.app/money.html    -> 404
    GET https://sairn.vercel.app/roam.html     -> 404

`sendHandoff` then does `window.location.href = cell.file`. A click navigates
the user **off StoneDesk into a 404**, losing whatever they were doing. The
matching keywords are not exotic ones either — `contract`, `home`, `property`,
`lease`, `budget` are ordinary vocabulary in a countertop shop's AI replies.

`sairn_handoff_context` is read by exactly one file: `stonedesk.html` itself. So
even if those pages existed, nothing on the platform would consume the payload.

## 4. Finding 2 — why nobody has reported the 404

**The sender half is dormant, and it is dormant for the same reason the receiver
was.** The comment at `stonedesk.html:17828` records that the *receiver* was
retargeted from the dead `#chatArea`/`#messages` legacy chat to the real
`#ai-chat` widget, having been "silently no-oping on every incoming handoff
before this fix."

The **sender** hook was not retargeted. At `:17936` it still resolves
`document.getElementById('chatArea')` and appends the handoff row there.
`#chatArea` is one of a block of empty placeholder divs at `:14500–14508`, all
carrying `style="display:none"`. The buttons render into a hidden element.

So the module is currently: a working receiver with no sender anywhere on the
platform, and a sender that renders invisibly into destinations that 404.

**This is the same half-fixed shape as the AR premise settled the same day** —
one half of a mechanism repaired, the other half left pointing at the old
target, with no test that spans both.

## 5. Recommendation, and the question it depends on

**Delete the module** — `CELL_MAP`, `sendHandoff`, `addHandoffButtons`,
`installHandoffHook` and `checkIncomingHandoff`, roughly 70 lines. Retargeting
the sender to `#ai-chat` would *activate* navigation into 404s, which is
strictly worse than dormant.

**Not done, deliberately, because one fact decides it and it is not in this
repo:** is the consumer app line — SAIRNtype, SAIRNhealth, SAIRNmoney,
SAIRNstudy, SAIRNlingual, SAIRNhome, SAIRNroam — real and coming to this
deployment? If yes, the work is "build the receivers and ship the pages," not
"delete." Deleting a module another session repaired hours earlier, on an
assumption about a product line, is not a call this sweep should make alone.

`sairnsenior.html` already exists in this repo, which is weak evidence the line
is not purely hypothetical — but it is a B2B app, and `CELL_MAP` points at
`/senior.html`, a different file that does not exist. That coincidence is worth
noticing and not worth trusting.

## 6. What was not checked

- Whether `#chatArea` receiving `appendChild` at `:18203` and `:18459` while
  carrying `display:none` breaks anything else. Several other hooks target the
  same hidden element; only the handoff one was in scope here.
- localStorage-backed cross-page state. sessionStorage is per-tab and
  localStorage is not, so localStorage cannot exhibit this class — but that
  makes it a different question, not an answered one.
- Whether `window.open(...,'_blank')` without `noopener` matters on the Suite
  tiles. Same-origin, so it is not a cross-origin `window.opener` leak; noted
  as an inconsistency, not assessed as a risk.
