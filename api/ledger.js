// api/ledger.js
// SHARED double-entry general ledger endpoint.
//
// ── THE ONE RULE, AND WHERE IT LIVES ─────────────────────────────────────
// An entry posts only if its debits equal its credits. That decision is made
// entirely by api/_lib/ledger.js and NOTHING is written until it says yes.
// This file carries no accounting rules of its own, for the reason every
// shared engine on this platform gives: two implementations of "does this
// balance" would eventually disagree, and the one in the endpoint would be the
// one nobody tested.
//
// ── WHAT MAKES THE GUARANTEE REAL ────────────────────────────────────────
// 1. VALIDATE FIRST, WRITE SECOND. The whole entry -- header and every line --
//    arrives in one call and is validated as a unit. There is no path that
//    accepts lines one at a time, because a half-built entry sitting in the
//    table is an unbalanced entry however briefly.
// 2. LINES BEFORE STATUS. The header is written as `draft`, then the lines,
//    and only then is the header flipped to `posted`. If anything fails
//    mid-way the entry is left as a draft -- visible, incomplete, and NOT
//    counted by the trial balance. The failure mode is a stuck draft rather
//    than a posted lie.
// 3. IDEMPOTENT ON THE BUSINESS EVENT. A post carrying source_kind +
//    source_id refuses if an entry already exists for that pair. Without this
//    a double-clicked "Record payment" posts revenue twice, which is exactly
//    the class of silent money bug this platform keeps finding.
// 4. POSTED IS IMMUTABLE. There is no edit action. Correction is a reversing
//    entry, built by the engine so the mirror cannot be got subtly wrong.
//
// ── WHAT THIS ENDPOINT WILL NOT DO ───────────────────────────────────────
// It will not post an entry the caller did not fully specify. There is no
// "auto-balance the remainder into a suspense account" convenience, because
// that turns a refusal into a silent guess about somebody's books.

'use strict';

const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest, roleSet } = require('./_lib/auth');
const ledger = require('./_lib/ledger');

const IDENT_RE = /^[A-Za-z0-9_.:-]+$/;
const MAX_ID_LEN = 96;
const MAX_LINES = 200;

// Posting to the general ledger is an accounting action, not an operational
// one. Same tier as bonding limits and programme standing.
const MANAGEMENT_ROLES = roleSet({ owner: true, admin: true });

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-SD-Auth');
}

module.exports = async (req, res) => {
  setCors(res);
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'Method not allowed' } }); return; }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  const body = req.body || {};
  const action = String(body.action || '');
  const appId = String(body.app_id || '');
  const payload = body.payload || {};
  const lic = await validateLicenseKey((req.headers.authorization || '').replace(/^Bearer\s+/i, '').trim());
  if (!lic || !lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }
  const licHash = lic.license_hash;

  // ── app_id VALIDATION MOVED BELOW LICENCE VALIDATION 2026-09-05 ──────────
  // Above it, a caller holding no valid licence learned the shape this shared
  // endpoint expects of app_id -- a body-dependent refusal answered before the
  // caller was known. Same shape as api/sd-data.js and api/sd-sub-data.js. The
  // 405 stays above it because it says nothing about what exists. The cost is
  // real and is not hidden: a junk key now costs one license_keys lookup it did
  // not before. It must still run BEFORE verifySessionToken below, which pins
  // the token to the app the caller claims to be.
  if (!/^[a-z0-9_-]+$/i.test(appId) || appId.length > 64) {
    res.status(400).json({ error: { message: 'app_id is required and must be a short identifier' } });
    return;
  }

  const session = verifySessionToken(tokenFromRequest(req), licHash, appId);
  if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
  if (!MANAGEMENT_ROLES[session.role]) {
    res.status(403).json({ error: { code: 'FORBIDDEN', message: 'The general ledger is management-level information' } });
    return;
  }

  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (p) => SUPABASE_URL + '/rest/v1/' + p;
  const enc = encodeURIComponent;
  const today = (payload && typeof payload.today === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(payload.today)) ? payload.today : null;
  if (!today) { res.status(400).json({ error: { code: 'NO_TODAY', message: 'payload.today (YYYY-MM-DD) is required' } }); return; }

  // rowsOrFail(): DELETED 2026-09-14 with its last caller.
  //
  // WHAT IT WAS FOR IS WORTH KEEPING EVEN THOUGH THE CODE IS GONE. Four reads
  // in this file did `x.ok ? await x.json() : []`, and on a set of BOOKS that
  // is not a degraded display, it is a fabricated financial statement:
  // trial_balance produced a BALANCED, EMPTY trial balance from a failed read,
  // and reverse produced a reversal with NO LINES, posted as though it had
  // reversed something. Every one of them answered "the answer is none" to
  // "I could not ask".
  //
  // Its three callers were read / trial_balance / reverse, all deleted below
  // as dead. api/duplicate-check-fail-closed.test.js still asserts the SHAPE
  // is absent from this whole file, which is the assertion that found those
  // four in the first place and is the one worth keeping.

  const notProvisioned = () => res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The ledger is not set up yet — run sql/ledger_schema.sql in Supabase first.' } });

  try {
    // ── CHART ─────────────────────────────────────────────────────────────
    // So a client never hardcodes a second copy of the account list.
    if (action === 'chart') {
      res.status(200).json({ ok: true, accounts: ledger.ACCOUNTS, statuses: ledger.ENTRY_STATUSES });
      return;
    }

    // ── VALIDATE ──────────────────────────────────────────────────────────
    // Deliberately available on its own so a UI can show "this does not
    // balance, out by $50" BEFORE anybody presses post, without writing a
    // draft to find out.
    if (action === 'validate') {
      const v = ledger.validateEntry({ today: today, entry: payload.entry });
      if (!v.ok) { res.status(400).json({ error: v.error }); return; }
      res.status(200).json({ ok: true, validation: v });
      return;
    }

    // ── POST ──────────────────────────────────────────────────────────────
    if (action === 'post') {
      const e = payload.entry || {};
      const entryId = String(e.entry_id || '').trim();
      if (!entryId || !IDENT_RE.test(entryId) || entryId.length > MAX_ID_LEN) {
        res.status(400).json({ error: { message: 'entry.entry_id is required and must be a short identifier' } });
        return;
      }
      if (!Array.isArray(e.lines) || e.lines.length > MAX_LINES) {
        res.status(400).json({ error: { message: 'entry.lines must be an array of at most ' + MAX_LINES + ' lines' } });
        return;
      }

      // THE GATE. Nothing below runs unless this passes, and the refusal
      // carries every reason rather than the first.
      const v = ledger.validateEntry({ today: today, entry: e });
      if (!v.ok) { res.status(400).json({ error: v.error }); return; }
      if (!v.postable) {
        res.status(422).json({
          error: {
            code: 'DOES_NOT_BALANCE',
            message: 'Refused: ' + v.problems.join('; '),
            problems: v.problems,
            debit_total: v.debit_total, credit_total: v.credit_total, difference: v.difference
          }
        });
        return;
      }

      // IDEMPOTENCE ON THE BUSINESS EVENT, checked before writing anything.
      // A double-clicked "Record payment" must not post revenue twice.
      const sk = String(e.source_kind || '').trim(), si = String(e.source_id || '').trim();
      if (sk && si) {
        const dup = await fetch(rest('ledger_entries?license_hash=eq.' + enc(licHash) +
          '&app_id=eq.' + enc(appId) + '&source_kind=eq.' + enc(sk) + '&source_id=eq.' + enc(si) +
          '&status=eq.posted&select=entry_id&limit=1'), { headers });
        if (dup.status === 404 || dup.status === 400) { notProvisioned(); return; }
        // A DUPLICATE CHECK THAT COULD NOT RUN IS NOT A CLEAN BILL (2026-09-04).
        // `dup.ok ? await dup.json() : []` meant a 401, 403, 500 or 503 -- a
        // revoked key, a missing grant, an unreachable store -- read as "no
        // existing entry found", and the code posted the entry anyway. This
        // check exists precisely so a double-clicked "Record payment" cannot
        // post revenue twice, and the failure mode of the check was to allow
        // exactly that, silently, into a double-entry general ledger.
        //
        // Refusing costs a retry. Allowing costs a second posted entry against
        // the same business event, which someone then has to find and reverse.
        if (!dup.ok) {
          console.error('ledger: idempotence check failed, HTTP', dup.status, '-- refusing rather than posting unchecked');
          res.status(502).json({ error: {
            code: 'DUPLICATE_CHECK_FAILED',
            message: 'Could not confirm whether this transaction is already in the ledger, so nothing was posted. Try again.'
          } });
          return;
        }
        const drows = await dup.json().catch(function () { return null; });
        if (!Array.isArray(drows)) {
          console.error('ledger: idempotence check returned a non-array -- refusing rather than posting unchecked');
          res.status(502).json({ error: {
            code: 'DUPLICATE_CHECK_FAILED',
            message: 'Could not confirm whether this transaction is already in the ledger, so nothing was posted. Try again.'
          } });
          return;
        }
        if (Array.isArray(drows) && drows[0]) {
          res.status(409).json({
            error: {
              code: 'ALREADY_POSTED',
              message: 'That transaction is already in the ledger as ' + drows[0].entry_id + ' — nothing was posted again.',
              entry_id: drows[0].entry_id
            }
          });
          return;
        }
      }

      // HEADER AS DRAFT FIRST. If the lines fail, what is left behind is an
      // incomplete DRAFT -- visible and excluded from the trial balance --
      // rather than a posted entry with missing sides.
      const hw = await fetch(rest('ledger_entries?on_conflict=license_hash,entry_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: appId, entry_id: entryId,
          entry_date: v.entry_date, memo: v.memo, status: 'draft',
          source_app: v.source_app || appId, source_kind: sk || null, source_id: si || null,
          data: e.data || {}, updated_at: new Date().toISOString()
        })
      });
      if (hw.status === 404 || hw.status === 400) { notProvisioned(); return; }
      if (!hw.ok) { res.status(502).json({ error: { message: 'Data store rejected the entry header' } }); return; }

      const lineRows = v.lines.map((l, i) => ({
        license_hash: licHash, app_id: appId, entry_id: entryId, line_no: i + 1,
        account_code: l.account_code,
        // THE CORE OWNS THE CENTS-TO-MONEY RULE (item 92, 2026-09-14). This
        // was `l.debit_cents / 100` -- a second money rule in the shell, next
        // to nine uses of `money()` inside api/_lib/ledger.js. They agree only
        // while `debit_cents` is an integer, which `cents()` happens to
        // guarantee and nothing asserts.
        debit: ledger.money(l.debit_cents), credit: ledger.money(l.credit_cents),
        memo: l.memo
      }));
      const lw = await fetch(rest('ledger_lines'), {
        method: 'POST', headers: Object.assign({}, headers, { Prefer: 'return=minimal' }),
        body: JSON.stringify(lineRows)
      });
      if (!lw.ok) {
        const detail = await lw.text();
        // Said plainly, including what state the entry was left in. A caller
        // that is told only "failed" does not know whether to retry.
        res.status(502).json({ error: {
          code: 'LINES_REJECTED',
          message: 'The lines were rejected, so entry ' + entryId + ' remains a DRAFT and is not in the trial balance. Nothing was posted.',
          detail: detail.slice(0, 300)
        } });
        return;
      }

      // Only now does it become real.
      const pw = await fetch(rest('ledger_entries?license_hash=eq.' + enc(licHash) + '&entry_id=eq.' + enc(entryId)), {
        method: 'PATCH', headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({ status: 'posted', posted_at: today, posted_by: session.employee_id, updated_at: new Date().toISOString() })
      });
      const saved = await pw.json();
      if (!pw.ok) { res.status(502).json({ error: { code: 'POST_FAILED', message: 'Lines were written but the entry could not be marked posted — it remains a DRAFT.' } }); return; }
      res.status(200).json({
        ok: true, entry: Array.isArray(saved) ? saved[0] : saved,
        debit_total: v.debit_total, credit_total: v.credit_total, lines: lineRows.length
      });
      return;
    }

    // ── read / trial_balance / reverse: DELETED 2026-09-14 ───────────────
    // Three actions with ZERO callers anywhere on the platform. sairnbiz.html
    // is this endpoint's only client and it calls `post` and nothing else.
    //
    // THEY CARRIED THE ONLY SOFT FAILURE SHAPE LEFT IN THIS FILE: an absent
    // ledger_entries answered 200 with provisioned:false and trial_balance:null,
    // so whoever wired a trial balance up would have inherited A BALANCED, EMPTY
    // SET OF BOOKS RENDERED FROM A TABLE THAT DOES NOT EXIST -- which is exactly
    // the defect the 2026-09-04 comment block above rowsOrFail was written
    // about, one step removed. The write path has always refused properly
    // (notProvisioned(), twice), so nothing a caller can reach is affected.
    //
    // DELETED RATHER THAN HARDENED, on Michael's call: hardening code nobody
    // calls leaves the same trap for later and adds a second thing to keep
    // true. git history has them if they are ever wanted.
    //
    // A REQUEST FOR ONE NOW FALLS THROUGH TO THE 400 BELOW, which is the right
    // answer: a named refusal, not a silent 200 with an empty body.
    //
    // api/_lib/ledger.js KEEPS trialBalance() and reversalOf(). They are pure,
    // tested directly by api/_lib/ledger.test.js, and they are what a real
    // trial-balance feature should be built on -- with the HARD
    // notProvisioned() shape this file already proves three times.

    res.status(400).json({ error: { message: 'Unknown action: ' + action } });
  } catch (err) {
    console.error('ledger endpoint error:', err && err.message);
    res.status(500).json({ error: { message: 'Server error — try again' } });
  }
};
