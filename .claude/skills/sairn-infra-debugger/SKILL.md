---
name: sairn-infra-debugger
description: Playbook for debugging SAIRN platform infrastructure — Supabase auth/permission errors (403/401 on the REST API), Vercel environment variables that "won't update," and confirming what's actually deployed vs what's in the repo. Trigger this AGGRESSIVELY whenever a 403, 401, or 500 shows up from a Supabase or Vercel-hosted endpoint; whenever an env var change doesn't seem to take effect after a redeploy; whenever it's unclear which branch or commit is actually live in production; or whenever setting up a new service-role/API key for any SAIRN app (all 10 currently live -- StoneDesk, SAIRNbiz, SAIRNbuild, SAIRNcode, SAIRNdesign, SAIRNgrounds, SAIRNlaw, SAIRNlegacy, SAIRNscape, SAIRNvet -- or any future app). Also trigger on phrases like "still 403," "key doesn't work," "won't save," "is this actually deployed," "which branch is live."
---

# SAIRN Infra Debugger

Hard-won lessons from a real multi-hour StoneDesk incident (July 2026). Every step below exists because skipping it burned real time that day. Follow the order — each step is cheap and rules out a whole category of cause before spending a redeploy cycle on a guess.

## The #1 lesson: GRANTs and RLS are different things

**If a valid service-role/secret key still gets 403 or "permission denied" on a Supabase table, check base table GRANTs before touching RLS, keys, or env vars at all.**

`BYPASSRLS` (which `service_role` has) only skips *policy* checks. It does **not** replace the underlying Postgres `GRANT SELECT/INSERT/UPDATE/DELETE`. A table created by raw SQL migration (rather than Supabase's Table Editor UI, which auto-grants this) can easily end up with `service_role` holding only `TRUNCATE/REFERENCES/TRIGGER` — and nothing else. That produces a 403 that looks exactly like a bad key or a bad RLS policy, and wastes hours if you chase those instead.

**Run this FIRST, before suspecting the key or RLS, whenever service-role access to any table fails:**

```sql
select grantee, privilege_type
from information_schema.table_privileges
where table_name = '<table_name>';
```

If `service_role` is missing `SELECT`/`INSERT`/`UPDATE`/`DELETE`, that's the bug. Fix:

```sql
grant select, insert, update, delete on <table_name> to service_role;
```

Check every new table you create this same way — this bug tends to affect every table created in the same migration, not just one.

## Order of operations for ANY "403/401 from Supabase" report

Do these in order. Each one is fast and rules something out — don't skip ahead on a guess, it costs a full redeploy-and-retest cycle if you're wrong.

1. **Check GRANTs** (see above) — the single most common real cause, and the one most likely to be skipped because BYPASSRLS makes it feel like it shouldn't matter.
2. **Test the key directly with curl, from a plain terminal, before touching any env var or config:**
   ```
   curl -s -o /dev/null -w "%{http_code}\n" -H "apikey: <KEY>" "https://<project>.supabase.co/rest/v1/<table>?select=*&limit=1"
   ```
   Use the `apikey` header **only** — do NOT also send `Authorization: Bearer <key>` unless the key is a legacy JWT (starts with `eyJ`). The newer `sb_secret_...`/`sb_publishable_...` key format is NOT a JWT and Supabase's own docs say not to send it as a bearer token.
   - 200 → key is fine, keep going down this list.
   - 403 → could be GRANTs (step 1) or RLS — don't touch env vars yet.
   - 401 → key itself is wrong/malformed (commonly: truncated during copy — see "copying secrets" below).
3. **If step 2 passes locally but production still fails**, the problem is in how the key got INTO the deployment, not the key itself. Check the env var directly rather than assuming an edit "saved":
   ```
   vercel env ls
   ```
   Look at the "updated" timestamp for the var in question. If you just edited it and the timestamp hasn't changed, **the edit did not actually save** — this happens more often than you'd expect with in-place dashboard edits. Don't redeploy yet; fix the save first.
4. **To reliably update a Vercel env var, don't trust in-place dashboard editing if step 3 shows it didn't take. Remove and re-add via CLI instead:**
   ```
   vercel env rm <VAR_NAME> production
   vercel env add <VAR_NAME> production
   ```
   (Prompts for the value — paste it directly into the terminal, never into a chat window. Same for `preview`/`development` if needed.)
5. **Only after 1-4 all check out, redeploy and retest:**
   ```
   vercel --prod --force
   ```
   Then re-run the curl test against the LIVE URL, not just locally — a redeploy is the only way a new env var value actually reaches production.

## Confirming what's actually deployed (don't assume push = live)

Before debugging application behavior, confirm production is running the code you think it's running:

1. Check whether Vercel's Git-integration auto-deploy is actually working, or silently erroring on every push while manual deploys succeed. Compare: does the latest entry in `vercel ls` / the Deployments dashboard tab show a recent Git-triggered build, or only manual `vercel deploy` entries? If auto-deploy is broken, pushing to GitHub does **nothing** to production until someone runs `vercel --prod --force` by hand — this can silently persist for weeks.
2. Check which branch Vercel's project settings actually deploy from (`Project Settings → Git → Production Branch`, or just check `origin/HEAD` and compare to the project's connected branch). If your team has more than one long-lived branch (e.g. `main` and `master`), confirm they haven't silently diverged — `git log --oneline <branch-a>..<branch-b>` and vice versa shows the real gap, if any, before you assume a risky merge is needed.
3. When in doubt, the deployment page itself is ground truth: check the deployment's timestamp and "Source" (which commit/branch it actually built from) rather than trusting what you assume just pushed.

## Copying secrets without corrupting them

Several real failures this session traced back to a secret being copied incorrectly:

- Always use the platform's own **copy icon**, never manually select-and-copy displayed/masked text — masked views (`sb_secret_1I-Ix••••••`) often only show a truncated prefix.
- When testing a key via curl, paste it in **once**, verify the command looks right before running, and don't reuse a stale copy-paste from earlier in a long session — keys get regenerated/rotated more often than you'd expect mid-investigation.
- Never paste a real secret (API key, token, PAT) into a Claude.ai chat window — it will very likely get flagged/auto-revoked by the platform, same as pasting it in any other public/logged channel. If Claude Code needs a secret, type it directly into Claude Code's own terminal/prompt, not into a message here.
- In Claude Code, prefix a command with `!` to run it as a raw terminal command when you need to bypass Claude's own interpretation of plain text (e.g. `!vercel env rm ...`) — useful when Claude Code has been treating literal commands as conversational chat instead of executing them.

## When Claude Code treats a command as chat instead of running it

If you paste something like `cd some/path` or `dir` and Claude Code responds conversationally ("I see you've navigated to...") instead of actually running it — it interpreted the paste as a chat message, not a shell command. Fix: give it an explicit instruction instead ("Run `dir` in this folder and show me the output"), or prefix the literal command with `!`.

## Quick reference: the verification triad for any code change

Before AND after any change to a SAIRN app's HTML/JS (not just this incident — standing practice):
```
node --check <extracted script block>
python div_balance_check.py <file>.html      # gap should not change unless that's the point of the change
python nav_panel_check.py <file>.html         # reconciled count should not change unless that's the point of the change
```
For any new API endpoint, add a smoke-test pass (one read/write per resource/action combination) before considering it done — a 200 status alone doesn't confirm real persistence; check the actual returned data matches what was written.
