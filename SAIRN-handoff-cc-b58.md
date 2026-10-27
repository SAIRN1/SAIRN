# SAIRN handoff: cc, batch b58, 2026-10-27 (SAIRNlegacy presence-proof, plus a gate-truncation incident)

**Every item is closed except the root cause of the incident in §1, which is
OPEN.**

- The tool and the checklist change landed as `4da85144`, then pushed
  through the **restored, verified** gate as `3adf9069..3e8a5215`. The clone
  reads 0 0 against origin.
- No product code changed. Nothing was self-registered. No `--force`, no
  override.

| | |
|---|---|
| Claims held | none |
| Context | 76.6% measured (see the digest's CONTEXT line) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

## 1. INCIDENT: the push gate was truncated to 0 bytes. A recurring-bug-class candidate; cause OPEN

**What was found.** At about **11:04 EDT**, `tools/sairn_push_gate_hook.py`
in the working tree became **0 bytes**: `git diff` showed all 5,329 lines
deleted. Two **empty untracked files named `cd` and `git`** appeared in the
clone root, both stamped 11:04.

The git pre-push hook runs that file. While it was empty, **every push from
this clone would have passed with no gate at all**, which is fail-open.
cc's next push was attempted and refused because the tree was dirty. No push
went through the empty gate.

**Restored and verified (Michael's instruction):**
- `git checkout -- tools/sairn_push_gate_hook.py`.
- `git diff` against HEAD is clean.
- Blob hash `0e02ddd153559ab7b1ec5e7358b5c70c630b6792` equals
  `git rev-parse HEAD:tools/sairn_push_gate_hook.py`, at 5,329 lines.
- `py_compile` passes and `--selftest` passes 56/56.
- I re-checked that it was still clean after every later push.
- **Evidence kept, not deleted:** the two files are at
  `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a\scratchpad\b58-evidence\{cd,git}`.
  Both are 0 bytes, mtime 11:04.

**The command cc was running.** The transcript timestamp is
2026-10-27T15:03:03Z, which is 11:03 EDT. Verbatim, after the commit message:

    git commit -q -m "fix(tools, cc b58): sairnlegacy stress fixture secrets built by join ..."; \
    for n in 1 2 3; do \
      git add docs/scrutiny-flags.json docs/BYPASS-LOG.jsonl 2>/dev/null; \
      git diff --cached --quiet || git commit -q -m "chore(cc b58): push-gate rows ..."; \
      git pull --rebase -q origin main 2>&1 | grep CONFLICT; \
      if git push origin main 2>&1 | tee "$TMPDIR/p58b.txt" | grep -E "\->"; then break; fi; \
      grep -E "^Blocked" "$TMPDIR/p58b.txt" | head -2; \
    done; git fetch -q origin; git rev-list --left-right --count HEAD...origin/main; ...

- The **only** `>` characters in it are three file-descriptor redirects
  (`2>/dev/null` and `2>&1` twice) and the `>` inside the quoted regex
  `"\->"`.
- **Nothing in the command names `tools/sairn_push_gate_hook.py`, `cd` or
  `git` as a redirect target.**

**A second actor was in this clone in the same two minutes.** This is the
strongest lead, and it was found from the reflog:
- `HEAD@{11}` is a commit at **11:02:39**, "Apply H1 b86 ALLOWED entries
  patch (scope gate + separation audit)". It touches
  `tools/hover_auditor_scope_gate.py` (+42) and
  `tools/hover_separation_audit.py` (+8).
- It was made under the shared identity, Michael Dibert. **cc did not make
  it**; no cc tool call in the transcript creates it.
- cc's own commit followed at 11:03:07, then the truncation and the two files
  at 11:04.
- That commit is kept unchanged. It landed as `f413c5ea`, then rebased.

**My best read of how a redirect could produce exactly these three
artefacts:**

1. **(Most likely) A command run by the other actor during the patch
   application, in a shell that parsed a redirect differently.** A line such
   as `... > tools/sairn_push_gate_hook.py` would truncate the gate. A
   multi-command line pasted into a shell that broke `cd ... && git ...` into
   tokens would create files named `cd` and `git`. For example,
   `foo > cd && git ...` under cmd.exe, or a `>`/`2>` split across a line
   wrap.
   - Empty files named after the **first word of each command segment** is
     the signature of a redirect operator attaching to the following token.
   - The gate file is the one file a "check the gate after applying the
     patch" step would name.
2. **A hook mis-parsing cc's command.** A PreToolUse or git hook that strips
   quotes would turn `grep -E "\->"` into `grep -E \->`, which is a bare
   redirect.
   - Against it: the command contains no path or word that would make the
     target be the gate file, `cd` or `git`.
   - Against it: `.claude/settings.json` declares no Bash hooks, and the same
     `"\->"` regex has run in dozens of earlier pushes with no effect.
3. **git itself during the rebase** (a checkout interrupted by a Windows file
   lock). That could leave a file empty. It cannot create files named `cd`
   and `git`, so on its own it does not explain all three.

**How to confirm (the next step, owner cc, tools/):**
- Ask whoever applied the H1 b86 patch for the exact command line they used
  at 11:02–11:04.
- Replay cc's 11:03 command verbatim in a throwaway worktree, watching the
  modification times of every file in it. If nothing is created, hypothesis
  2 is out.
- Once the cause is known, file it as a recurring-bug-class record. If cc
  caused it, cc files it; if not, it goes to its owner.
- The control to add whatever the cause: the push gate should refuse to
  start when its own file is empty or its hash differs from HEAD's blob, and
  say so. **An empty gate is the one failure that reports a pass it never
  performed** (PR 1.11).

**A second gate issue in the same batch, handled correctly.**
- After the restore, the credentials gate refused the push because the
  fixture secret literal in `6cfdf32f` was still in the outgoing range, even
  though a later commit had removed it.
- I folded only my own fix into my own commit with a scripted
  `rebase -i --autosquash`-style edit, so the literal never ships.
- The H1 patch commit was left exactly as it was.
- The next push passed every gate.

## 2. Items 1-3: `tools/sairnlegacy_presence_stress.py`, exit 1

The run has 9 scenarios: 1 PASS, 5 FAIL, 3 controls OK. With `--ablate`, L3e
goes PASS → FAIL.

**What is real and what is stubbed:**
- **REAL:**
  - the `api/sd-data.js` handler;
  - the MODE_ALWAYS countersignature lock;
  - a signed session token;
  - `contentHash()`, used to build the token row;
  - `legPriceOf()` and `legComposeStatement()`.
- **STUBBED:** the licence, and the Supabase rows (the b18 suite's own
  harness shape).

| ID | Claim | The truth | Result | Owner (route) |
|---|---|---|---|---|
| L1c | filed with its countersignature | every authorisation check recorded | CONTROL-OK | |
| L1a | filed with its countersignature | status Completed, all four authorisation flags **false** | FAIL: 200, stored as Completed | hank, `api/_lib/countersign.js:247` |
| L1b | filed with its countersignature | status Completed, **no** authorisation fields | FAIL: 200, stored | hank, `api/sd-data.js:17528` |
| L2c | Paid | $5,000 invoice, $5,000 payment | CONTROL-OK | |
| L2a | Paid | $5,000 invoice, **no** payment | FAIL: stored as Paid | hank, `api/sd-data.js:17552` |
| L3c | printable | priced at $5,000 | CONTROL-OK | |
| L3e | printable | the price is blank | PASS: refused (PRICE_NOT_ON_FILE) | |
| L3a | printable | price $0, which is what a blank input saves as | FAIL: printable, total 0 | fourth, `sairnlegacy.html:3748` |
| L3b | printable | +$5,000 and −$5,000 lines | FAIL: printable, total 0 | fourth, `sairnlegacy.html:3798` |

**Surveyed, not driven** (routed to fourth in a note):
- `confirmPayment` (`:3582`) marks an invoice Paid from a "Pre-Need Trust"
  source with no plan or funding check, and adds the payment to
  `plan.amount_paid`.
- `saveCremation` (`:3250`) accepts Completed with the authorisation box
  unchecked.

## 3. Items 4 and 5: routed, and tagged by launch-wave app

- **Nothing was self-registered.** The FOR HANK and FOR FOURTH status notes
  were appended and confirmed.
- The tool prints a **ready-to-file record per finding**, built by the new
  `record_spec()`. Each is `defect_register.py --add --commit <fix> --app
  sairnlegacy --layer product --severity ... --method fault-injection
  --summary "[launch-wave:sairnlegacy] <id> -- <FAIL MEANS> (site ...)"`.
- **`tools/presence_proof.py` gains a LAUNCH-WAVE checklist item.**
  - `require_plan()` takes `wave_app` and exits 2 without it.
  - `stonedesk_presence_stress.py` declares `wave_app='stonedesk'`.
  - Fixtures are 18/18.
- **How coverage is counted across apps:** grep the register for
  `[launch-wave:<app>]`, together with its `--app` field.

## 4. OPEN

| Item | Owner | Next step |
|---|---|---|
| Root cause of the gate truncation | cc, then whoever caused it | See §1, "How to confirm". Add a gate self-integrity check, so an empty or hash-mismatched gate refuses to start. |
| L1a, L1b, L2a, plus the Tier A obligation on `leg_cremations` and `leg_invoices` | hank | Fix them, file each with the printed record spec, then re-run the tool. |
| L3a, L3b, plus the surveyed `confirmPayment` and `saveCremation` | fourth | Same. |
| `f413c5ea` (H1 b86 patch to cc's `tools/hover_*`) was applied in cc's clone by another actor | Michael / H1 | Confirm it was intended. cc has not reviewed its content. |
| Carried | hank / fourth / cody / H1 | the b56/b57 StoneDesk findings, the b55 SAIRNlaw items, `38b2b506`, `d6b37bb1` |
