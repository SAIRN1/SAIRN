// api/_lib/wip-accounting.js
// SHARED progress-billing engine: draw requests, retainage, and over/under
// billing. Pure functions, no I/O, no app names.
//
// ── WHAT THIS IS FOR ─────────────────────────────────────────────────────
// The 2026-08-26 worldwide competitive-gap audit's Tier-B item B3: WIP /
// percentage-of-completion accounting, retainage and certified payroll, found
// "only in general construction ERP (Sage 300 CRE, Viewpoint Vista) and
// essentially absent from every roofing-specific product surveyed", against
// one keyword hit in sairnroofing.html. Re-verified 2026-09-02: ZERO
// occurrences of retainage, over/under billing or WIP anywhere in
// sairnroofing.html, api/ or sql/.
//
// ── AN IMPLEMENTATION ALREADY EXISTS AND THIS DOES NOT REPLACE IT ────────
// Said up front, because the last shared layer I wrote did not say it and was
// wrong for a day. SAIRNbuild HAS retainage and WIP today -- `jobWIP()`
// (sairnbuild.html:6263), a Draw Requests panel, `bld_draws` with
// retainage_pct/retainage_held, and a default retainage setting. It is
// CLIENT-SIDE, in-file, over localStorage, and it is untouched by this file.
// So this is the SECOND implementation on the platform, deliberately, because
// SAIRNbuild's is not a server engine and cannot be called; repointing it is
// its own task and not a rider on a feature branch.
//
// ── THE HONESTY HINGE: WHERE PERCENT COMPLETE COMES FROM ─────────────────
// The accounting standard method is COST-TO-COST -- cost incurred divided by
// total estimated cost. This engine does NOT do that, and the reason is not
// preference: the consuming app has no job-cost store, so cost-to-cost would
// need a cost figure that does not exist. Inventing one, or quietly
// substituting a different basis under the same label, is how a WIP schedule
// becomes a number an accountant relies on and cannot reproduce.
//
// So percent complete is whatever the contractor STATED on the draw -- which
// is how a roofing draw is actually written, usually off squares installed --
// and every result carries `basis: 'contractor_stated_percent'`. A caller may
// pass costs and get `basis: 'cost_to_cost'` instead. What it will never do is
// report one basis while using the other.
//
// ── RETAINAGE IS DERIVED, NEVER STORED TWICE ─────────────────────────────
// held = amount x pct, computed on read. SAIRNbuild's bld_draws stores both
// `retainage_pct` AND `retainage_held`, which can disagree the moment anyone
// edits one. Same rule as outstanding money in subcontractor-compliance.js.
//
// ── IT WILL NOT ASSUME A CLOCK ───────────────────────────────────────────
// Anything date-dependent requires a caller-supplied `today`.

'use strict';

const DRAW_STATUSES = ['draft', 'requested', 'approved', 'received', 'rejected'];
// A draw is "aged" past this many days outstanding. A review window a caller
// overrides, not an industry term.
const DEFAULT_AGED_DAYS = 30;

function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
function str(v) { return typeof v === 'string' ? v.trim() : ''; }
function num(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return (typeof n === 'number' && isFinite(n)) ? n : null;
}
function money(n) { return Math.round(n * 100) / 100; }
function daysBetween(a, b) {
  const x = Date.parse(a + 'T00:00:00Z'), y = Date.parse(b + 'T00:00:00Z');
  if (!isFinite(x) || !isFinite(y)) return null;
  return Math.round((y - x) / 86400000);
}

// ── One draw request ─────────────────────────────────────────────────────
function summariseDraw(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const d = input.draw || {};
  const aged = num(input.aged_days) === null ? DEFAULT_AGED_DAYS : num(input.aged_days);

  const amount = num(d.amount) || 0;
  const pct = num(d.retainage_pct);
  const status = DRAW_STATUSES.indexOf(d.status) === -1 ? null : d.status;
  const out = {
    ok: true,
    draw_id: str(d.draw_id) || null,
    job_id: str(d.job_id) || null,
    draw_no: num(d.draw_no),
    period_end: isDate(d.period_end) ? d.period_end : null,
    pct_complete: num(d.pct_complete),
    amount: money(amount),
    status: status,
    problems: status === null && d.status !== undefined
      ? ['unrecognised draw status "' + String(d.status) + '"'] : []
  };

  // Retainage. A missing percentage is NOT zero: "we hold nothing" and "nobody
  // recorded what is held" are different facts, and defaulting to zero would
  // silently tell a contractor the full amount is collectable.
  if (pct === null) {
    out.retainage_pct = null;
    out.retainage_held = null;
    out.net_requested = null;
    out.problems.push('no retainage percentage recorded -- what is collectable cannot be worked out');
  } else if (pct < 0 || pct > 100) {
    out.retainage_pct = null;
    out.retainage_held = null;
    out.net_requested = null;
    out.problems.push('retainage percentage "' + d.retainage_pct + '" is outside 0-100');
  } else {
    out.retainage_pct = pct;
    out.retainage_held = money(amount * pct / 100);
    out.net_requested = money(amount - out.retainage_held);
  }

  const received = num(d.amount_received) || 0;
  out.received = money(received);
  if (out.net_requested === null) {
    out.outstanding = null;
  } else {
    const o = money(out.net_requested - received);
    out.outstanding = o < 0 ? 0 : o;
    // Overpayment surfaced rather than clamped away, same rule as
    // subcontractor-compliance.js's summariseAssignment.
    out.overpaid = o < 0 ? money(Math.abs(o)) : 0;
  }

  // Ageing. Measured from when it was REQUESTED, because that is when the
  // clock an owner is judged against starts -- not the period end.
  out.days_outstanding = null;
  out.aged = false;
  const reqOn = isDate(d.requested_at) ? d.requested_at : null;
  if (status === 'requested' || status === 'approved') {
    if (!reqOn) {
      out.problems.push('outstanding but with no requested date -- its age cannot be worked out');
    } else {
      const n = daysBetween(reqOn, today);
      out.days_outstanding = n;
      out.aged = n !== null && n > aged;
    }
  }
  return out;
}

// ── One job: earned vs billed ────────────────────────────────────────────
// The number that matters in construction accounting and the one the audit
// says roofing products do not have. Over-billed is not a bonus and
// under-billed is not a saving: both are a mismatch between revenue recognised
// and cash requested, and an owner or a surety will ask about either.
function jobWip(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const job = input.job || null;
  if (!job) return { ok: false, error: { code: 'NO_JOB', message: 'no job supplied' } };

  const contract = num(job.contract_value);
  const draws = (Array.isArray(input.draws) ? input.draws : [])
    .filter(function (d) { return str(d && d.job_id) === str(job.job_id); });

  const summaries = draws.map(function (d) {
    return summariseDraw({ draw: d, today: today, aged_days: input.aged_days });
  }).filter(function (s) { return s.ok; });

  const out = {
    ok: true,
    job_id: str(job.job_id) || null,
    contract_value: contract,
    draw_count: summaries.length,
    retainage_held: money(summaries.reduce(function (s, d) { return s + (d.retainage_held || 0); }, 0)),
    requested_total: money(summaries.reduce(function (s, d) { return s + (d.amount || 0); }, 0)),
    received_total: money(summaries.reduce(function (s, d) { return s + (d.received || 0); }, 0)),
    outstanding_total: money(summaries.reduce(function (s, d) { return s + (d.outstanding || 0); }, 0)),
    aged_draws: summaries.filter(function (d) { return d.aged; }).map(function (d) { return d.draw_id; }),
    basis: null,
    pct_complete: null,
    earned: null,
    billed: null,
    over_under: null,
    problems: []
  };

  // Any draw that could not have its retainage worked out makes the retainage
  // total an UNDERCOUNT, and that is said rather than left for the reader to
  // notice the number looks low.
  const unpriced = summaries.filter(function (d) { return d.retainage_held === null; });
  if (unpriced.length) {
    out.problems.push(unpriced.length + ' draw(s) have no usable retainage percentage -- the retainage total is an undercount');
  }

  // ---- percent complete, and where it came from ----
  const costToDate = num(input.cost_to_date);
  const estTotalCost = num(input.estimated_total_cost);
  if (costToDate !== null && estTotalCost !== null && estTotalCost > 0) {
    // The accounting standard method, used ONLY when a caller actually
    // supplies costs. Never inferred.
    out.basis = 'cost_to_cost';
    out.pct_complete = Math.round(Math.min(1, costToDate / estTotalCost) * 1000) / 10;
  } else {
    // What the contractor stated on the most recent draw by period end. This
    // is how a roofing draw is really written -- usually off squares installed
    // -- and it is LABELLED as stated rather than computed.
    const dated = summaries.filter(function (d) { return d.period_end && d.pct_complete !== null; })
      .sort(function (a, b) { return a.period_end < b.period_end ? -1 : a.period_end > b.period_end ? 1 : 0; });
    if (dated.length) {
      out.basis = 'contractor_stated_percent';
      out.pct_complete = dated[dated.length - 1].pct_complete;
      out.pct_complete_as_of = dated[dated.length - 1].period_end;
    } else {
      out.basis = 'none';
      out.problems.push('no percent complete on any draw and no costs supplied -- earned revenue cannot be worked out');
    }
  }

  if (out.pct_complete !== null && contract !== null) {
    out.earned = money(contract * out.pct_complete / 100);
    out.billed = out.requested_total;
    out.over_under = money(out.billed - out.earned);
    out.position = out.over_under > 0 ? 'over_billed' : (out.over_under < 0 ? 'under_billed' : 'level');
  } else {
    if (contract === null) out.problems.push('no contract value on the job -- earned revenue cannot be worked out');
    out.position = 'unknown';
  }
  return out;
}

// ── The whole book ───────────────────────────────────────────────────────
function portfolio(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const jobs = Array.isArray(input.jobs) ? input.jobs : [];
  const rows = jobs.map(function (j) {
    return jobWip({ job: j, draws: input.draws, today: today, aged_days: input.aged_days });
  }).filter(function (r) { return r.ok; });

  const computable = rows.filter(function (r) { return r.over_under !== null; });
  const uncomputable = rows.filter(function (r) { return r.over_under === null; });

  return {
    ok: true,
    today: today,
    jobs: rows,
    retainage_held: money(rows.reduce(function (s, r) { return s + (r.retainage_held || 0); }, 0)),
    outstanding_total: money(rows.reduce(function (s, r) { return s + (r.outstanding_total || 0); }, 0)),
    over_billed: money(computable.filter(function (r) { return r.over_under > 0; })
      .reduce(function (s, r) { return s + r.over_under; }, 0)),
    under_billed: money(computable.filter(function (r) { return r.over_under < 0; })
      .reduce(function (s, r) { return s + Math.abs(r.over_under); }, 0)),
    aged_draws: rows.reduce(function (s, r) { return s + r.aged_draws.length; }, 0),
    // NOT a footnote. A WIP schedule that silently omits the jobs it could not
    // compute reads as a complete book, and the omitted ones are exactly the
    // jobs nobody has stated a percent complete for.
    not_computable: uncomputable.map(function (r) {
      return { job_id: r.job_id, reasons: r.problems };
    })
  };
}

module.exports = {
  DRAW_STATUSES,
  DEFAULT_AGED_DAYS,
  summariseDraw,
  jobWip,
  portfolio
};
