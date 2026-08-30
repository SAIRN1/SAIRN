-- sql/license_keys_customer_check_2026-08-30.sql
--
-- IS THERE A PAYING CUSTOMER ON SAIRNCARE, SAIRNDENTAL OR SAIRNROOFING?
--
-- READ-ONLY. Four SELECTs, no DDL, no writes, no branch that can reach one.
-- Safe to run any number of times.
--
-- ── WHY THIS FILE EXISTS ───────────────────────────────────────────────────
-- The `verified_by` -> `loaded_by` rename is deferred, and the whole deferral
-- rests on one fact: every licence on the five reference tables is a house
-- tenant. That fact has only ever been checked against the REPO -- by grepping
-- for licence keys named in docs and SQL -- which proves what we have written
-- down, not what the database holds. See
-- docs/2026-08-30-verified-by-rename-scoping.md section 8, which says so in
-- those words and names this as the check that would settle it.
--
-- ── WHY IT IS A PASTE AND NOT A TOOL ───────────────────────────────────────
-- `license_keys` is readable only with SUPABASE_SERVICE_ROLE_KEY. No tool in
-- tools/ reads it, no endpoint exposes it, and no SAIRN clone carries the key
-- (.env.local is empty in Documents\SAIRN-hank). `api/_lib/license.js` looks up
-- exactly ONE row, by the raw key presented in the request, so it cannot
-- enumerate. The nearest live probe available without the service key is
-- `check_license` on each app's auth endpoint, which confirms a key you ALREADY
-- KNOW is valid, active and bound to an app -- and says nothing about the ones
-- you do not know. That probe was run on 2026-08-30 for ALF-TEST-2026,
-- DNT-PINNACLE-2026 and RF-PINNACLE-2026; all three came back
-- {ok:true, active:true} on sairncare / sairndental / sairnroofing
-- respectively. It is corroboration, not enumeration.
--
-- ── HOW TO READ THE RESULT ─────────────────────────────────────────────────
-- Section 1 is the answer. A row with a NON-NULL stripe_subscription_id is a
-- paying customer and the line HAS been crossed. Everything else is judgement:
-- look at customer_email and plan, and remember that "PINNACLE" is the
-- internal canonical tenant name used across every SAIRN app, not a customer.
--
-- Sections 2-4 narrow it. Section 2 asks which licences have actually touched
-- the five reference tables. Section 3 is the join that matters -- a licence
-- that BOTH holds reference rows AND looks like a customer. Section 4 is the
-- control: if it returns zero rows the join in section 3 is broken and section
-- 3's emptiness means nothing.
--
-- ── IF SECTION 1 RETURNS A CUSTOMER ────────────────────────────────────────
-- Option A in the scoping doc (rename, deploy, accept a ~1-2 minute window
-- where writes 400) stops being available for that app. Option B
-- (expand/contract) is still available and gets more expensive to schedule the
-- longer it waits.


-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 1 -- every licence issued for the three apps.
-- This is the question. Everything below is refinement.
-- ═══════════════════════════════════════════════════════════════════════════
select
  app_id,
  key,
  status,
  plan,
  customer_email,
  stripe_subscription_id,
  trial_ends_at,
  created_at,
  -- A blunt first read. Deliberately conservative: anything with a Stripe
  -- subscription is called a customer regardless of what else the row says.
  case
    when stripe_subscription_id is not null then 'PAYING CUSTOMER -- line crossed'
    when key ilike '%PINNACLE%' or key ilike '%TEST%' or key ilike '%DEMO%'
                                                    then 'looks like a house tenant'
    else 'UNCLASSIFIED -- read customer_email and plan by hand'
  end as first_read
from license_keys
where app_id in ('sairncare', 'sairndental', 'sairnroofing')
order by app_id, created_at;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 2 -- which licences have actually written to the five tables.
-- A licence can exist on an app without ever touching them; the rename only
-- migrates rows that exist.
-- ═══════════════════════════════════════════════════════════════════════════
select 'alf_compliance_rules' as tbl, license_hash, count(*) as rows
  from alf_compliance_rules group by 2
union all
select 'alf_payer_rules',       license_hash, count(*) from alf_payer_rules       group by 2
union all
select 'dnt_cred_rules',        license_hash, count(*) from dnt_cred_rules        group by 2
union all
select 'rf_cert_rules',         license_hash, count(*) from rf_cert_rules         group by 2
union all
select 'rf_contingency_rules',  license_hash, count(*) from rf_contingency_rules  group by 2
order by 1, 3 desc;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 3 -- the join that matters: a licence that holds reference rows AND
-- is not obviously a house tenant. ZERO ROWS HERE IS THE GOOD ANSWER.
--
-- license_keys stores the RAW key; the reference tables are scoped by
-- sha256(key) hex. pgcrypto's digest() is used to bridge them. If the extension
-- is not enabled, run section 1 and section 2 and match them by eye instead --
-- there are only a handful of licences, and a hand match is honest where a
-- failed join would silently return nothing.
-- ═══════════════════════════════════════════════════════════════════════════
with hashed as (
  select
    lk.app_id, lk.key, lk.status, lk.plan, lk.customer_email,
    lk.stripe_subscription_id,
    encode(digest(lk.key, 'sha256'), 'hex') as license_hash
  from license_keys lk
  where lk.app_id in ('sairncare', 'sairndental', 'sairnroofing')
),
touched as (
  select license_hash from alf_compliance_rules
  union select license_hash from alf_payer_rules
  union select license_hash from dnt_cred_rules
  union select license_hash from rf_cert_rules
  union select license_hash from rf_contingency_rules
)
select h.app_id, h.key, h.status, h.plan, h.customer_email, h.stripe_subscription_id
from hashed h
join touched t on t.license_hash = h.license_hash
where h.stripe_subscription_id is not null
   or not (h.key ilike '%PINNACLE%' or h.key ilike '%TEST%' or h.key ilike '%DEMO%')
order by h.app_id, h.key;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 4 -- THE CONTROL. Run this whenever section 3 returns nothing.
--
-- Section 3 returns zero rows both when there is no customer AND when the hash
-- join never matched anything -- a broken join and a clean result look
-- identical. This shows the join working on rows we already know exist, so an
-- empty section 3 can be trusted. If THIS returns zero, section 3 proved
-- nothing and the join needs fixing before any conclusion is drawn.
-- ═══════════════════════════════════════════════════════════════════════════
with hashed as (
  select lk.app_id, lk.key,
         encode(digest(lk.key, 'sha256'), 'hex') as license_hash
  from license_keys lk
  where lk.app_id in ('sairncare', 'sairndental', 'sairnroofing')
),
touched as (
  select license_hash from alf_compliance_rules
  union select license_hash from alf_payer_rules
  union select license_hash from dnt_cred_rules
  union select license_hash from rf_cert_rules
  union select license_hash from rf_contingency_rules
)
select h.app_id, h.key, 'hash join matched' as control
from hashed h
join touched t on t.license_hash = h.license_hash
order by h.app_id, h.key;
