-- sql/sairnroofing_tax_provenance_backfill_2026-09-01.sql
-- SAIRNroofing -- the LEGACY half of open-work row 141.
--
-- STATUS: NOT RUN. Written 2026-09-01, never executed against any database
-- from this session -- no service-role access here. Run it yourself in the
-- Supabase SQL editor, SECTION BY SECTION, and read section 0 before running
-- section 1.
--
-- ---------------------------------------------------------------------------
-- WHY THIS EXISTS: the code fix was write-path only
-- ---------------------------------------------------------------------------
-- Row 141 says a rate-taxed invoice "misreports how its own tax was derived on
-- every read". `b044f35` fixed that on 2026-08-26 by adding
-- `taxFieldsToStore()` -- the write now persists the QUESTION the user asked
-- (`tax_rate`) and never the ANSWER the app computed (`tax`). That commit
-- changed api/_lib/roofing-billing.js, api/sd-data.js (both write branches),
-- the isolation suite and sairnroofing.html. It shipped NO migration.
--
-- So every invoice and issued proposal written BEFORE that commit still
-- carries both keys, and still misreports on every read, today. The index row
-- is therefore half right and half stale: the defect it names is fixed going
-- forward and is still live for existing rows -- including INV-00001 on
-- RF-PINNACLE-2026, the very row it cites as its live evidence.
--
-- Reproduced 2026-09-01 in isolation against the real library, not inferred:
--   stored blob {"tax_rate":7.5,"tax":787.5}
--     -> tax_basis 'amount', tax_rate null,
--        problems ["both a tax rate and a tax amount were given; ..."]
--   same row with `tax` removed
--     -> tax_basis 'rate', problems []
--   tax 787.5 and total 11287.5 IDENTICAL in both cases.
--
-- ---------------------------------------------------------------------------
-- THE SAFETY PROPERTY, AND WHY THIS IS SAFE ON FINANCIAL ROWS
-- ---------------------------------------------------------------------------
-- This UPDATE cannot move a number a customer was billed. It only ever removes
-- `tax` when the stored value is EXACTLY what the rate re-derives, so the read
-- path lands on the rate branch and computes the identical figure. Subtotal,
-- tax and total are unchanged by construction; only `tax_basis` and `problems`
-- change, from a false 'amount' + invented warning to a true 'rate' + none.
--
-- That property is asserted in code, not just argued here --
-- api/_lib/roofing-billing.test.js, "legacy: dropping the derived tax key
-- changes the disclosure and NOT the money". 40/40 pass as of 2026-09-01.
--
-- A GENUINE conflict is deliberately left alone. If the user really did give
-- both a rate and a different amount, the stored tax does NOT equal the
-- re-derived figure, the condition fails, both keys survive, and the warning
-- keeps firing on every read -- which is correct, and is the one case
-- `taxFieldsToStore` was careful to preserve. Also asserted in the suite.
--
-- ---------------------------------------------------------------------------
-- ARITHMETIC, MATCHED TO THE LIBRARY RATHER THAN INVENTED
-- ---------------------------------------------------------------------------
-- normalizeLineItems: amount   = round(quantity * unit_price, 2)  per line
-- computeTotals:      subtotal = round(sum(amounts), 2)
--                     tax      = round(subtotal * rate / 100, 2)
-- `money()` is Math.round(n*100)/100 -- half away from zero for positives,
-- which is what Postgres `round(numeric, 2)` does. The match is exact for
-- positive money.
--
-- ONE HONEST LIMIT: the library rounds in float64, Postgres in exact numeric.
-- In a rare edge case the two could differ by a cent, the condition would not
-- match, and the row would be SKIPPED. That is the conservative direction --
-- a skipped row keeps today's behaviour and changes nothing. Section 2 counts
-- what is left so a skip is visible rather than silent, instead of widening
-- the condition with a tolerance and risking a match that should not happen.
--
-- Safe to re-run: after section 1, matching rows no longer have a `tax` key,
-- so a second run matches nothing.

-- ===========================================================================
-- SECTION 0 -- READ-ONLY SURVEY. Run this FIRST and read it.
-- Writes nothing. Tells you how many rows section 1 would touch, and lets you
-- eyeball the money staying still before you change anything.
-- ===========================================================================
with inv as (
  select
    i.id,
    i.invoice_id,
    i.invoice_number,
    i.license_hash,
    i.created_at,
    (i.data->>'tax_rate')::numeric as rate,
    (i.data->>'tax')::numeric      as stored_tax,
    (
      select round(coalesce(sum(round(
                coalesce((li->>'quantity')::numeric, 0)
              * coalesce((li->>'unit_price')::numeric, 0), 2)), 0), 2)
      from jsonb_array_elements(i.data->'line_items') li
    ) as subtotal
  from public.rf_invoices i
  where i.data ? 'tax_rate'
    and i.data ? 'tax'
    and jsonb_typeof(i.data->'line_items') = 'array'
)
select
  'rf_invoices'                                   as table_name,
  invoice_number,
  invoice_id,
  created_at,
  subtotal,
  rate,
  stored_tax,
  round(subtotal * rate / 100, 2)                 as rate_derived_tax,
  case
    when stored_tax = round(subtotal * rate / 100, 2)
      then 'BACKFILL -- derived figure, disclosure is wrong today'
    else 'LEAVE -- a real rate/amount disagreement, warning is true'
  end                                             as verdict
from inv
order by created_at;

-- Same survey for issued proposals. Decision rows (accepted/declined/
-- withdrawn) carry no line items and are untouched by all of this.
with pro as (
  select
    p.id,
    p.proposal_id,
    p.license_hash,
    p.created_at,
    (p.data->>'tax_rate')::numeric as rate,
    (p.data->>'tax')::numeric      as stored_tax,
    (
      select round(coalesce(sum(round(
                coalesce((li->>'quantity')::numeric, 0)
              * coalesce((li->>'unit_price')::numeric, 0), 2)), 0), 2)
      from jsonb_array_elements(p.data->'line_items') li
    ) as subtotal
  from public.rf_proposals p
  where p.event_type = 'issued'
    and p.data ? 'tax_rate'
    and p.data ? 'tax'
    and jsonb_typeof(p.data->'line_items') = 'array'
)
select
  'rf_proposals'                                  as table_name,
  proposal_id,
  created_at,
  subtotal,
  rate,
  stored_tax,
  round(subtotal * rate / 100, 2)                 as rate_derived_tax,
  case
    when stored_tax = round(subtotal * rate / 100, 2)
      then 'BACKFILL -- derived figure, disclosure is wrong today'
    else 'LEAVE -- a real rate/amount disagreement, warning is true'
  end                                             as verdict
from pro
order by created_at;

-- ===========================================================================
-- SECTION 1 -- THE BACKFILL. Run only after reading section 0.
-- Removes the derived `tax` key. Removes nothing else. Touches no other
-- column, no other key, and no row whose stored tax is not exactly the
-- re-derived figure.
-- ===========================================================================
update public.rf_invoices i
set data = i.data - 'tax',
    updated_at = now()
where i.data ? 'tax_rate'
  and i.data ? 'tax'
  and jsonb_typeof(i.data->'line_items') = 'array'
  and (i.data->>'tax')::numeric = round(
        (
          select round(coalesce(sum(round(
                    coalesce((li->>'quantity')::numeric, 0)
                  * coalesce((li->>'unit_price')::numeric, 0), 2)), 0), 2)
          from jsonb_array_elements(i.data->'line_items') li
        ) * (i.data->>'tax_rate')::numeric / 100, 2);

-- rf_proposals is APPEND-ONLY as a product rule -- there is no update verb in
-- the API and the schema header says a wrong proposal is superseded, never
-- edited. This statement is a one-off data repair of a field the app itself
-- wrote by mistake, not a product write path, and it changes no figure any
-- party agreed to. RUN IT DELIBERATELY, or skip it and accept that issued
-- proposals keep the wrong disclosure -- that is a real choice, not an
-- oversight, and it is called out here so it is made rather than defaulted.
update public.rf_proposals p
set data = p.data - 'tax'
where p.event_type = 'issued'
  and p.data ? 'tax_rate'
  and p.data ? 'tax'
  and jsonb_typeof(p.data->'line_items') = 'array'
  and (p.data->>'tax')::numeric = round(
        (
          select round(coalesce(sum(round(
                    coalesce((li->>'quantity')::numeric, 0)
                  * coalesce((li->>'unit_price')::numeric, 0), 2)), 0), 2)
          from jsonb_array_elements(p.data->'line_items') li
        ) * (p.data->>'tax_rate')::numeric / 100, 2);

-- ===========================================================================
-- SECTION 2 -- CONFIRM. Run after section 1.
-- `derived_left` MUST be 0. `conflicts_left` is expected to be non-zero if
-- section 0 showed any LEAVE rows -- those are real disagreements and are
-- meant to survive. If `derived_left` is not 0, a row was skipped by the
-- rounding limit in the header; report the number rather than widening the
-- condition.
-- ===========================================================================
with inv as (
  select
    (i.data->>'tax_rate')::numeric as rate,
    (i.data->>'tax')::numeric      as stored_tax,
    (
      select round(coalesce(sum(round(
                coalesce((li->>'quantity')::numeric, 0)
              * coalesce((li->>'unit_price')::numeric, 0), 2)), 0), 2)
      from jsonb_array_elements(i.data->'line_items') li
    ) as subtotal
  from public.rf_invoices i
  where i.data ? 'tax_rate' and i.data ? 'tax'
    and jsonb_typeof(i.data->'line_items') = 'array'
),
pro as (
  select
    (p.data->>'tax_rate')::numeric as rate,
    (p.data->>'tax')::numeric      as stored_tax,
    (
      select round(coalesce(sum(round(
                coalesce((li->>'quantity')::numeric, 0)
              * coalesce((li->>'unit_price')::numeric, 0), 2)), 0), 2)
      from jsonb_array_elements(p.data->'line_items') li
    ) as subtotal
  from public.rf_proposals p
  where p.event_type = 'issued'
    and p.data ? 'tax_rate' and p.data ? 'tax'
    and jsonb_typeof(p.data->'line_items') = 'array'
)
select
  (select count(*) from inv where stored_tax =  round(subtotal * rate / 100, 2)) as inv_derived_left,
  (select count(*) from inv where stored_tax <> round(subtotal * rate / 100, 2)) as inv_conflicts_left,
  (select count(*) from pro where stored_tax =  round(subtotal * rate / 100, 2)) as pro_derived_left,
  (select count(*) from pro where stored_tax <> round(subtotal * rate / 100, 2)) as pro_conflicts_left;
