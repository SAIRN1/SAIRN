-- Mints ONE dedicated SAIRNlaw scratch licence -- LAW-AUDIT-0002 -- for the
-- M5 live verification (hank b72, Michael's b72 item 1). That check writes a
-- bank statement and a stale deposit in transit into the trust ledger, which
-- must NOT go on LAW-PINNACLE-2026 (the canonical licence; trust rows are not
-- deletable through the API). It cannot go on LAW-AUDIT-2026 either: that
-- licence already has an owner, and this session does not hold its PIN.
--
-- Same shape as sql/audit_license_seed_mech_law_2026-09-28.sql:
--   * touches ONLY public.license_keys -- no employee row, no PIN hash. The
--     owner is created afterwards through the API, with a PIN chosen then:
--         POST https://sairn.vercel.app/api/law-auth
--         Authorization: Bearer LAW-AUDIT-0002
--         {"action":"bootstrap","employee_id":"audit-owner",
--          "display_name":"Audit Owner","pin":"<choose one>"}
--   * the key matches tools/audit_licence.py's AUDIT_KEY_RE, so a writing
--     probe accepts it.
--
-- Idempotent: `on conflict (key) do nothing`, so re-running changes nothing and
-- cannot disturb an existing licence.
-- ---------------------------------------------------------------------------

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('LAW-AUDIT-0002', 'active', 'audit@sairnlaw.example', 'sairnlaw', 'demo', null)
on conflict (key) do nothing;

-- ── VERIFY ─────────────────────────────────────────────────────────────────
-- Expect exactly one row: status active, app_id sairnlaw, plan demo.
select key, status, app_id, plan, created_at
  from public.license_keys
 where key = 'LAW-AUDIT-0002';
