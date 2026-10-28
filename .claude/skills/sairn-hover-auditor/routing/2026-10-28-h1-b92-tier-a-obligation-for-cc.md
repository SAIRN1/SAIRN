# H1 b92 -- Tier A review obligation to record for hover's held test file (route to cc's next queue)

**Why this is a routing and not a write by hover.** Chat ruled in b92 that a Tier A review obligation is never skipped and that hover records it as a DATA write to `docs/tier-a-reviews.json` if no builder tool is needed. The write was attempted and the hover auditor scope gate REFUSED the commit (`docs/tier-a-reviews.json` is outside `ALLOWED`; the file is the build agents' shared ledger, 308 records). Boundary stop, logged in the b92 handoff. Nothing of it is committed; the working tree and index were restored (308 records, last author cody).

**What is held.** `.claude/skills/sairn-hover-auditor/empirical-tests/test_965_sen_caregivers_phone_unredacted.py` (75 lines) on local branch `hover-b91-empirical-tests`, commit `7ec9c912d`. The platform push gate refused it as TIER A CODE CHANGED WITH NO RECORDED REVIEW OBLIGATION because the text names `sen_caregivers`. It is a data-only reader of `api/sd-data.js` and `sairnsenior.html`; no endpoint serves it.

**The exact entry to append to `records` in `docs/tier-a-reviews.json`** (a data write by cc; identity of the ledger is author_session plus opened_at, so this is a union-by-identity append). The fields marked CC STAMPS can only be known at write time. Serialization of the file is `json.dumps(data, indent=2, ensure_ascii=False)` plus a newline, which was checked byte for byte against the current file.

```json
{
  "author_session": "hover",
  "opened_at": "CC STAMPS the UTC time of the write, format YYYY-MM-DDTHH:MM:SSZ",
  "opened_at_sha": "CC STAMPS the origin/main tip at the time of the write",
  "opened_at_sha_basis": "head",
  "opened_at_sha_extra_files": null,
  "resources": [
    "sen_caregivers"
  ],
  "rules": [],
  "irreversible": [],
  "files": [
    ".claude/skills/sairn-hover-auditor/empirical-tests/test_965_sen_caregivers_phone_unredacted.py"
  ],
  "what": "hover b92: a data-only test script for finding H1-965 (the sen_caregivers read branch of api/sd-data.js still returns phone and the rest of the roster to every authenticated role after the b384a513f HR-field redaction). It reads api/sd-data.js and sairnsenior.html as text and executes nothing from them; it is the first test run by hover_empirical_gate.py (promotion record in the hover log, RFC 3161 token verified). It is not served by any endpoint: the file names the resource, which is all the gate matched. Review: does the script's claim (the only session.role use in the read branch is the HR-field decision; phone is not among the redacted fields; the whole data blob is returned) match the code, and can it be made to exit 0 when it should exit 1 (negative controls: phone added to the redaction list exits 1, the list renamed exits 3).",
  "status": "open",
  "reviewer_owner": "cc",
  "owner_assigned_at": "CC STAMPS the same time as opened_at",
  "reviewer_session": null,
  "reviewed_at": null,
  "verdict": null,
  "owner_note": "hover computed cc by the gate's least-loaded-then-alphabetical rule over the open records in this file (cc 5, cody 6, fourth 6, hank 5 at 2026-10-28); roster liveness not checked, so cc re-assigns with its own roster function if cc is not the right reviewer or is not live."
}
```

**Order that makes it land.** (1) cc appends the entry and pushes it. (2) hover pulls, cherry-picks `7ec9c912d`'s test file onto a fresh branch off origin/main and pushes; the gate then finds a covering open obligation for `sen_caregivers`. (3) A reviewer other than hover discharges it.

**Caveats, so nothing here reads as more than it is.** The record is opened BEFORE the file exists on main, so `opened_at_sha_basis` is `head` and the staleness check will report the file as new since the stamped sha; the reviewer should read the file at its first appearance. Whether the gate accepts a `files` entry for a path that does not yet exist at the stamped sha was not tested, because testing it means running `tools/tier_a_review_gate.py`, which hover does not run. If it does not, the alternative is `--resources sen_caregivers` with no `files`.
