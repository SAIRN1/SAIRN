// api/legal-deadlines.js
// ---------------------------------------------------------------------------
// SAIRNlaw deadline rules engine endpoint.
//
// Computation itself lives in api/_lib/deadline-engine.js and is PURE -- this
// file only loads rules and calendars and hands them over. That split exists
// so the date arithmetic can be tested against worked examples from the rule
// text without a database, which is what a legal-deadline computation needs.
//
// FAIL CLOSED, ALWAYS. Every refusal names the missing thing. There is no code
// path here that returns an approximate, estimated or best-guess date, and no
// path that falls back to "today" when a trigger is absent. A wrong deadline
// in a legal product is malpractice exposure, not a bug.
//
// Auth mirrors api/legal-citator.js and api/legal-reference.js: bearer license
// key scoped to sairnlaw, with an OPTIONAL session token used to attribute the
// audit entry and to record WHO verified a rule.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { tokenFromRequest, verifySessionToken } = require('./_lib/auth');
const { writeAuditLog } = require('./_lib/audit');
const { sbClient } = require('./_lib/courtlistener');
const { computeDeadline, COMPUTATION_STANDARDS, SERVICE_EXTENSION_STANDARDS } = require('./_lib/deadline-engine');

const ACTIONS = ['compute', 'rules_status', 'add_rule', 'add_holidays'];

// ── Display labels (Phase 4) ──────────────────────────────────────────────
// Presentation only. A jurisdiction is stored and matched by its CODE -- these
// never participate in rule selection, and an unknown code FALLS BACK TO
// ITSELF rather than being hidden or guessed at, so seeding a new jurisdiction
// without adding a label here degrades to showing the raw code, never to
// showing nothing or showing the wrong name.
const JURISDICTION_LABELS = {
  'us-federal': 'United States (Federal)',
  oh: 'Ohio', in: 'Indiana', mi: 'Michigan', pa: 'Pennsylvania', il: 'Illinois', fl: 'Florida'
};
const DOMAIN_LABELS = {
  'civil-litigation': 'Civil litigation',
  appellate: 'Appellate'
};
function jurLabel(code) { return JURISDICTION_LABELS[code] || code; }
function domLabel(code) { return DOMAIN_LABELS[code] || code; }

// Turns a stored rule into the trigger option a caller can actually select.
// A multi-trigger rule is reported with the events it REQUIRES, because a
// caller supplying one date for it gets INCOMPLETE_TRIGGERS -- the UI needs to
// know to ask for all of them up front rather than discovering that by
// refusal. Single-trigger rules report requires_dates: null.
function triggerOption(r) {
  const t = r.trigger_event;
  // A designated-period rule needs one more input than a date: the period the
  // requesting party actually chose. Reported here so the UI asks for it up
  // front rather than the caller discovering it through a refusal, the same
  // reason requires_dates is reported for multi-trigger rules.
  const dp = r.designated_period
    ? { min: r.designated_period.min, unit: r.designated_period.unit || 'calendar_days',
        designated_by: r.designated_period.designated_by || null }
    : null;
  // Same reasoning as requires_dates and designated_period: a rule whose
  // deadline is capped by a date the other party fixed needs that date up
  // front, not discovered through a refusal.
  const capSpec = r.cap ? { event: r.cap.event, label: r.cap.label } : null;
  if (typeof t === 'string') {
    return { event: t, label: r.label || t, rule_id: r.rule_id, citation: (r.authority && r.authority.citation) || null, requires_dates: null, designated_period: dp, cap: capSpec };
  }
  if (t && Array.isArray(t.events)) {
    return { event: t.id || t.events[0], label: r.label || t.id, rule_id: r.rule_id,
      citation: (r.authority && r.authority.citation) || null,
      requires_dates: t.events.slice(), resolve: t.resolve || null, designated_period: dp, cap: capSpec };
  }
  return null;
}

// A rule with no traceable authority cannot be saved. Same discipline as
// sc_scrubrules and sc_credential_scope: this table only ever holds rules a
// human actually read and sourced.
function validateRulePayload(p) {
  if (!p || typeof p !== 'object') return 'A rule object is required.';
  const need = ['rule_id', 'jurisdiction', 'domain', 'trigger_event', 'count', 'computation', 'effective_from'];
  for (const k of need) {
    if (!p[k]) return 'Missing required field: ' + k;
  }
  // trigger_event is either a plain event name, or a multi-trigger spec for a
  // rule that runs from the later/earlier of several events (FRAP 4(b)(1)(A),
  // FRCP 12(a)(3)). A malformed spec is rejected rather than stored, because a
  // multi-trigger rule that silently degrades to one trigger produces a date
  // that is wrong in the direction that loses a right.
  if (typeof p.trigger_event !== 'string') {
    const t = p.trigger_event;
    if (!t || !Array.isArray(t.events) || t.events.length < 2) {
      return 'trigger_event must be an event name, or a multi-trigger spec with at least two events.';
    }
    if (t.resolve !== 'later_of' && t.resolve !== 'earlier_of') {
      return 'A multi-trigger spec needs resolve: "later_of" or "earlier_of".';
    }
    if (!t.id) return 'A multi-trigger spec needs an id so the rule can be referred to as a whole.';
  }
  // A retrigger clause REPLACES the trigger; it does not add days. Validated
  // separately from service_extension for exactly that reason -- the two are
  // different mechanisms and conflating them misstates the rule.
  if (p.retrigger) {
    const rt = p.retrigger;
    if (!Array.isArray(rt.on_events) || !rt.on_events.length) {
      return 'retrigger.on_events must list the events that restart the period.';
    }
    if (!rt.substitute_trigger) return 'retrigger.substitute_trigger is required — name the event the period then runs from.';
    if (rt.add || rt.days) return 'retrigger must not specify days to add. A retrigger replaces the trigger date; use service_extension if days are genuinely added.';
  }
  if (!COMPUTATION_STANDARDS[p.computation]) {
    return 'computation must be one of: ' + Object.keys(COMPUTATION_STANDARDS).join(', ');
  }
  const c = p.count;
  if (!c || typeof c.value !== 'number' || !c.unit || !c.direction) {
    return 'count requires { value (number), unit, direction }.';
  }
  if (['calendar_days', 'business_days', 'months', 'years'].indexOf(c.unit) === -1) {
    return 'count.unit must be calendar_days, business_days, months or years.';
  }
  if (['forward', 'backward'].indexOf(c.direction) === -1) {
    return 'count.direction must be forward or backward.';
  }
  // A rule may only name a service-extension standard the engine implements.
  // Storing an unknown one is allowed to FAIL at compute time (visibly, as
  // refused_unknown_standard), but rejecting it here stops the bad row from
  // being written in the first place.
  if (p.service_extension) {
    const se = p.service_extension;
    if (!se.standard) return 'service_extension.standard is required (e.g. frcp_6d, frap_26c).';
    if (!SERVICE_EXTENSION_STANDARDS[se.standard]) {
      return 'service_extension.standard must be one of: ' + Object.keys(SERVICE_EXTENSION_STANDARDS).join(', ') +
        '. FRCP 6(d) and FRAP 26(c) are differently shaped — 6(d) is an enumerated allowlist, 26(c) is a negative condition excluding electronic service — so a standard the engine does not implement cannot be evaluated.';
    }
    if (typeof se.add !== 'number') return 'service_extension.add must be a number of days.';
  }

  // The requirement that makes this table trustworthy.
  if (!p.authority || !p.authority.citation || !p.authority.url) {
    return 'authority.citation and authority.url are both required -- a deadline rule with no traceable source must not be stored.';
  }
  if (!/^https?:\/\//i.test(p.authority.url)) {
    return 'authority.url must be a real resolvable URL.';
  }
  // None of the standards implemented so far counts in business days. FRCP
  // and its family count calendar days and roll only the last day; Ohio's and
  // Indiana's short-period weekend/holiday exclusion is applied by the engine
  // itself, so a rule declaring business_days would double up a mechanism
  // already applied internally on top of misdeclaring the unit the rule text
  // actually uses.
  //
  // DENY BY DEFAULT, opt in per standard. This was previously an allowlist of
  // impl strings, which silently went stale the moment Indiana was added with
  // a new impl -- an Indiana rule declaring business_days would have passed a
  // guard written before that impl existed. A standard must now explicitly
  // declare allows_business_days to use the unit, so a state added later
  // fails closed instead of slipping through a list nobody remembered to
  // extend.
  // A designated-period rule sets a FLOOR, not a deadline. Its count.value is
  // the minimum a valid request may demand and must never be the thing counted
  // -- the engine counts the figure the caller supplies. Validated here so a
  // malformed floor cannot be stored at all.
  if (p.designated_period) {
    const dp = p.designated_period;
    if (typeof dp.min !== 'number' || Math.floor(dp.min) !== dp.min || dp.min <= 0) {
      return 'designated_period.min must be a positive whole number — it is the minimum period the rule permits.';
    }
    if (dp.unit && ['calendar_days', 'business_days', 'months', 'years'].indexOf(dp.unit) === -1) {
      return 'designated_period.unit must be calendar_days, business_days, months or years.';
    }
    if (!dp.designated_by) {
      return 'designated_period.designated_by is required — name who chooses the period, since the rule itself does not set one.';
    }
    if (dp.min !== c.value) {
      return 'designated_period.min must equal count.value for this rule shape. count.value holds the rule’s floor and is never counted from; a mismatch means one of the two is wrong.';
    }
    if (p.service_extension) {
      return 'A designated-period rule cannot also declare a service_extension: the designated figure already is the period, and adding days to a party-chosen period would extend a deadline the rule does not set.';
    }
  }
  // A cap rule's deadline is the EARLIER of its own computed period and a date
  // the other party fixed. Distinct from designated_period: that validates a
  // party-chosen DAY COUNT against a floor, this compares the computed result
  // against a party-chosen DATE. A rule cannot sensibly be both.
  if (p.cap) {
    if (!p.cap.event) return 'cap.event is required — name the event whose date caps this period.';
    if (!p.cap.label) return 'cap.label is required — it is shown to the user when the cap date is requested and when it governs.';
    if (p.designated_period) {
      return 'A rule cannot declare both cap and designated_period. One takes a party-chosen day count validated against a floor; the other compares the computed result against a party-chosen date. A rule needing both has not been understood yet.';
    }
  }
  if (c.unit === 'business_days' && !COMPUTATION_STANDARDS[p.computation].allows_business_days) {
    return COMPUTATION_STANDARDS[p.computation].label + ' counts calendar days (with its own weekend/holiday handling built into the engine), so a rule using this standard cannot specify business_days. No implemented standard currently counts in business days; if a jurisdiction genuinely does, its standard must declare that explicitly rather than relying on the unit alone.';
  }
  return null;
}

function validateHolidayPayload(p) {
  if (!p || !p.jurisdiction || !p.year) return 'jurisdiction and year are required.';
  if (!Array.isArray(p.dates)) return 'dates must be an array.';
  for (const d of p.dates) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d.date || '')) return 'Each date must be YYYY-MM-DD.';
    if (String(d.date).slice(0, 4) !== String(p.year)) return 'Date ' + d.date + ' does not fall in year ' + p.year + '.';
    if (['federal', 'declared', 'state'].indexOf(d.kind) === -1) {
      return 'Each date needs kind: federal, declared or state. The kind is load-bearing -- FRCP 6(a)(6) counts state holidays only for forward-counted periods.';
    }
  }
  if (!p.authority || !p.authority.citation) return 'authority.citation is required for a holiday calendar.';
  return null;
}

async function readAll(sb, table, licHash) {
  const r = await fetch(sb.rest(table + '?license_hash=eq.' + encodeURIComponent(licHash) + '&select=entry_id,data'), { headers: sb.headers });
  if (r.status === 404 || r.status === 400) return { provisioned: false, rows: [] };
  if (!r.ok) throw new Error(table + ' read failed: HTTP ' + r.status);
  const rows = await r.json();
  return { provisioned: true, rows: (rows || []).map((x) => x.data) };
}

async function upsert(sb, table, licHash, entryId, data) {
  const r = await fetch(sb.rest(table + '?on_conflict=license_hash,entry_id'), {
    method: 'POST',
    headers: Object.assign({}, sb.headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
    body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', entry_id: String(entryId), data, updated_at: new Date().toISOString() })
  });
  if (r.status === 404 || r.status === 400) return { provisioned: false };
  if (!r.ok) throw new Error(table + ' write failed: HTTP ' + r.status);
  return { provisioned: true };
}

// Shapes the flat holiday rows into the { jurisdiction: { year: [...] } } map
// the pure engine expects.
function buildCalendars(rows) {
  const out = {};
  for (const row of rows) {
    if (!row || !row.jurisdiction || !row.year) continue;
    out[row.jurisdiction] = out[row.jurisdiction] || {};
    out[row.jurisdiction][String(row.year)] = row.dates || [];
  }
  return out;
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) { res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } }); return; }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { res.status(400).json({ error: { message: 'Invalid JSON body' } }); return; }
  }
  const action = body && body.action;
  if (ACTIONS.indexOf(action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: ' + ACTIONS.join(', ') } });
    return;
  }

  let lic;
  try { lic = await validateLicenseKey(licenseKey); }
  catch (err) {
    if (err.code === 'CONFIG') { console.error('legal-deadlines config error:', err.message); res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }
    console.error('legal-deadlines license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }
  if (lic.app_id && lic.app_id !== 'sairnlaw') { res.status(403).json({ error: { code: 'WRONG_APP', message: 'This license is not issued for sairnlaw' } }); return; }

  const caller = verifySessionToken(tokenFromRequest(req), lic.license_hash, 'sairnlaw');
  const audit = (detail) => writeAuditLog(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
    license_hash: lic.license_hash,
    employee_id: caller ? caller.employee_id : null,
    role: caller ? caller.role : null,
    event_type: 'deadline_engine',
    detail
  }).catch((e) => { console.error('legal-deadlines audit write failed:', e && e.message); });

  let sb;
  try { sb = sbClient(); }
  catch (err) { console.error('legal-deadlines supabase config error:', err.message); res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }

  try {
    // ── RULES_STATUS: what is actually loaded. Its own action so the UI can
    // state coverage honestly without first running a computation and
    // inferring the gaps from a refusal. ──
    if (action === 'rules_status') {
      const rules = await readAll(sb, 'law_deadline_rules', lic.license_hash);
      const hols = await readAll(sb, 'law_holidays', lic.license_hash);
      if (!rules.provisioned || !hols.provisioned) {
        res.status(503).json({ ok: false, code: 'NOT_PROVISIONED',
          message: 'The deadline-engine tables are not set up yet — run sql/sairnlaw_deadline_rules_schema.sql in Supabase. Nothing is computed until then.' });
        return;
      }
      // Phase 4: this response now also carries the TRIGGERS and the display
      // labels the UI needs. Before, rules_status reported only counts, so the
      // client had no source for its trigger list and shipped an empty
      // <select> -- the engine was reachable by API and unreachable by a
      // person. Serving triggers from the same query that counts them means
      // the list cannot drift from what is actually loaded.
      const blank = (code) => ({
        jurisdiction: code, jurisdiction_label: jurLabel(code),
        domains: {}, domain_labels: {}, triggers: {}, rule_count: 0, holiday_years: []
      });
      const byJur = {};
      for (const r of rules.rows) {
        if (!r || !r.jurisdiction) continue;
        byJur[r.jurisdiction] = byJur[r.jurisdiction] || blank(r.jurisdiction);
        const j = byJur[r.jurisdiction];
        j.domains[r.domain] = (j.domains[r.domain] || 0) + 1;
        j.domain_labels[r.domain] = domLabel(r.domain);
        j.rule_count++;
        const opt = triggerOption(r);
        if (opt) {
          j.triggers[r.domain] = j.triggers[r.domain] || [];
          if (!j.triggers[r.domain].some((x) => x.event === opt.event)) j.triggers[r.domain].push(opt);
        }
      }
      for (const h of hols.rows) {
        if (!h || !h.jurisdiction) continue;
        byJur[h.jurisdiction] = byJur[h.jurisdiction] || blank(h.jurisdiction);
        byJur[h.jurisdiction].holiday_years.push(String(h.year));
      }
      Object.values(byJur).forEach((j) => {
        j.holiday_years.sort();
        Object.keys(j.triggers).forEach((d) => j.triggers[d].sort((a, b) => a.label.localeCompare(b.label)));
      });
      res.status(200).json({ ok: true, jurisdictions: Object.values(byJur),
        note: 'A jurisdiction with rules but no holiday calendar for a year a computation crosses will still refuse — the engine checks the year it actually needs, not the year of the trigger.' });
      return;
    }

    // ── COMPUTE ──
    if (action === 'compute') {
      const rules = await readAll(sb, 'law_deadline_rules', lic.license_hash);
      const hols = await readAll(sb, 'law_holidays', lic.license_hash);
      if (!rules.provisioned || !hols.provisioned) {
        res.status(503).json({ ok: false, code: 'NOT_PROVISIONED',
          message: 'The deadline-engine tables are not set up yet — run sql/sairnlaw_deadline_rules_schema.sql in Supabase. No date is produced.' });
        return;
      }
      const result = computeDeadline({
        trigger_date: body.trigger_date,
        // Multi-trigger rules take their dates here instead of trigger_date.
        trigger_dates: body.trigger_dates,
        trigger_event: body.trigger_event,
        // Qualifying motions that REPLACE the trigger (FRAP 4(a)(4)(A)).
        retrigger_events: body.retrigger_events,
        jurisdiction: body.jurisdiction,
        domain: body.domain,
        service_method: body.service_method,
        // The period a requesting party actually designated, for rules that
        // set only a floor rather than a deadline (Ohio Civ.R. 33(A)/36(A),
        // Ind. T.R. 33(C)/36(A)).
        designated_period_days: body.designated_period_days,
        // The date fixed by the other party that caps a computed period
        // (FRCP 45(d)(2)(B), Ohio Civ.R. 45(C)(3) -- the time specified
        // for compliance in the subpoena).
        cap_date: body.cap_date,
        rules: rules.rows,
        calendars: buildCalendars(hols.rows)
      });
      await audit({ action: 'compute', jurisdiction: body.jurisdiction, domain: body.domain,
        trigger_event: body.trigger_event, trigger_date: body.trigger_date,
        ok: !!result.ok, code: result.code || null, due_date: result.due_date || null,
        service_extension_state: (result.service_extension && result.service_extension.state) || null,
        retriggered: !!(result.steps || []).some((st) => st.step === 'trigger_substitution') });
      // A refusal is a 200-level *answer* only when it is a data-coverage
      // statement the user can act on; genuine gaps are 503 so a caller cannot
      // mistake "not loaded" for "no deadline".
      const status = result.ok ? 200
        : (result.code === 'NOT_PROVISIONED' ? 503
          : ['NO_MATCHING_RULE', 'NO_RULE_IN_FORCE', 'AMBIGUOUS_RULE', 'UNKNOWN_STANDARD', 'UNKNOWN_UNIT', 'BAD_RULE_TRIGGER'].indexOf(result.code) !== -1 ? 409
            // INCOMPLETE_TRIGGERS and MOTION_PENDING are 422: the request is
            // well-formed and the rule is loaded, but the facts needed to run
            // the clock are not all present yet. That is a different thing
            // from a bad request and from missing rule data, and a caller
            // should be able to tell them apart.
            // DESIGNATED_PERIOD_REQUIRED joins them: the rule is loaded and the
            // request is well-formed, but this rule sets no deadline of its own
            // and the caller has not yet said what period was designated.
            : ['INCOMPLETE_TRIGGERS', 'MOTION_PENDING', 'DESIGNATED_PERIOD_REQUIRED', 'CAP_DATE_REQUIRED'].indexOf(result.code) !== -1 ? 422
              // DESIGNATED_PERIOD_BELOW_FLOOR is a genuine 400: the caller did
              // supply a period and it is not one the rule permits. That is a
              // defect in the request being described, not missing information,
              // and it is the one refusal here that says something is WRONG
              // rather than merely absent.
              : 400);
      res.status(status).json(result);
      return;
    }

    // ── ADD_RULE ──
    if (action === 'add_rule') {
      const err = validateRulePayload(body.rule);
      if (err) { res.status(400).json({ ok: false, code: 'INVALID_RULE', message: err }); return; }
      const rule = Object.assign({}, body.rule, {
        version: body.rule.version || 1,
        authority: Object.assign({}, body.rule.authority, {
          retrieved_at: body.rule.authority.retrieved_at || new Date().toISOString().slice(0, 10),
          // Server-derived, never client-supplied: who actually verified this.
          verified_by: caller ? caller.employee_id : null
        })
      });
      const w = await upsert(sb, 'law_deadline_rules', lic.license_hash, rule.rule_id, rule);
      if (!w.provisioned) { res.status(503).json({ ok: false, code: 'NOT_PROVISIONED', message: 'Run sql/sairnlaw_deadline_rules_schema.sql in Supabase first.' }); return; }
      await audit({ action: 'add_rule', rule_id: rule.rule_id, jurisdiction: rule.jurisdiction, domain: rule.domain });
      res.status(200).json({ ok: true, rule_id: rule.rule_id, stored: rule });
      return;
    }

    // ── ADD_HOLIDAYS ──
    if (action === 'add_holidays') {
      const err = validateHolidayPayload(body.calendar);
      if (err) { res.status(400).json({ ok: false, code: 'INVALID_CALENDAR', message: err }); return; }
      const cal = body.calendar;
      const entryId = cal.jurisdiction + ':' + cal.year;
      const stored = Object.assign({}, cal, {
        authority: Object.assign({}, cal.authority, {
          retrieved_at: (cal.authority && cal.authority.retrieved_at) || new Date().toISOString().slice(0, 10),
          verified_by: caller ? caller.employee_id : null
        })
      });
      const w = await upsert(sb, 'law_holidays', lic.license_hash, entryId, stored);
      if (!w.provisioned) { res.status(503).json({ ok: false, code: 'NOT_PROVISIONED', message: 'Run sql/sairnlaw_deadline_rules_schema.sql in Supabase first.' }); return; }
      await audit({ action: 'add_holidays', jurisdiction: cal.jurisdiction, year: cal.year, count: cal.dates.length });
      res.status(200).json({ ok: true, entry_id: entryId, count: cal.dates.length });
      return;
    }

    res.status(400).json({ error: { message: 'Unsupported action' } });
  } catch (err) {
    console.error('api/legal-deadlines error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};
