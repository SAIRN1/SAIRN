-- sql/sairncare_mar_schema.sql
-- SAIRNcare Medication Administration Record (MAR) -- Supabase schema
--
-- WHY THIS IS A SEPARATE TABLE, NOT folded into alf_clients.data like ADL
-- assessments: ADL assessments are low-frequency (periodic reassessment),
-- bounded growth. Medication administration events are high-frequency (one
-- row per dose, potentially several times a day per resident, ongoing for
-- the length of the stay) -- folding that into alf_clients.data would blow
-- past its 64KB per-resident size cap within weeks for an active resident.
-- Same reasoning sen_visits used for the identical high-vs-low-frequency
-- split against sen_clients.
--
-- WHY THIS IS A SEPARATE GATE, NOT the alf_clients four-tier gate: medication
-- data carries real scope-of-practice sensitivity that resident-record edit
-- access does not. alf_clients' narrow tier (med_aide AND caregiver) can
-- edit any field of their own assigned resident -- appropriate for ADL/
-- general notes, NOT appropriate for medication orders or administration
-- records, which only a medication-certified role (or clinical/management
-- oversight) should be able to touch. This table is gated to owner/
-- nursing/med_aide ONLY -- caregiver, billing, and activities get a real
-- 403 on every alf_mar action, never silent access via the general
-- resident-write path.
--
-- entry_type discriminates five real sub-shapes, researched before
-- building (2026-08-20 MAR research pass, no single uniform ALF standard
-- found -- see SAIRN-ACTIVE-WORK.md for full sourcing):
--   medication_order    -- the standing order (name, dose, route, schedule,
--                          prn flag, controlled-substance flag, prescriber).
--                          Mutable-in-place: payload.id stays the same
--                          across edits/discontinue, same upsert shape as
--                          alf_clients itself. owner/nursing only.
--   administration       -- one real dose event (given/refused/held/not
--                          available). Append-only -- a fresh id every
--                          time, never edited after the fact (server
--                          rejects reusing an id already used for this
--                          type -- see api/sd-data.js). owner/nursing
--                          facility-wide, med_aide own-assigned-only.
--   count                 -- controlled-substance count (the one genuinely
--                          converged best practice found in research: a
--                          joint count with a second signature). Append-
--                          only, same as administration.
--   reconciliation        -- admission/transfer/discharge medication
--                          reconciliation. Borrowed from Joint Commission
--                          NPSG.03.06.01 (a hospital accreditation
--                          standard, NOT an ALF regulatory requirement --
--                          labelled as such in the client UI). owner/
--                          nursing only, append-only.
--   assessment_refusal    -- refusal of a medication-management
--                          ASSESSMENT specifically (distinct from refusing
--                          a routine dose, which is an 'administration'
--                          entry with status:'refused'). Modelled on
--                          Minnesota Stat. 144G.71's real requirement to
--                          document refusal of this specific assessment
--                          type. owner/nursing only, append-only.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_mar (
  id                    uuid primary key default gen_random_uuid(),
  license_hash          text not null,
  app_id                text not null default 'sairncare',
  entry_id              text not null,                 -- client-generated (MAR-<timestamp> or a
                                                          -- stable medication id for medication_order)
  resident_id           text not null,                  -- references alf_clients.client_id
  assigned_employee_id  text,                            -- denormalized from alf_clients at write
                                                          -- time (live-looked-up, never trusted from
                                                          -- the client) -- null = resident unassigned
  entry_type            text not null,                   -- medication_order | administration | count |
                                                          -- reconciliation | assessment_refusal
  data                  jsonb not null default '{}'::jsonb,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfmar_entry_type_check check (entry_type in
    ('medication_order','administration','count','reconciliation','assessment_refusal')),
  constraint alfmar_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfmar_license on public.alf_mar(license_hash);
create index if not exists idx_alfmar_resident on public.alf_mar(license_hash, resident_id);
create index if not exists idx_alfmar_assignee on public.alf_mar(license_hash, assigned_employee_id);

grant select, insert, update on public.alf_mar to service_role;
revoke all on public.alf_mar from anon, authenticated;

-- ── ATOMIC CHECK-AND-INSERT (2026-09-21) ───────────────────────────────────
-- Closes a real TOCTOU race in api/sd-data.js's alf_mar write branch
-- (hover_log #314): the handler SELECTed for an existing entry_id, returned
-- 409 ALREADY_RECORDED if found, and otherwise POSTed with
-- on_conflict=license_hash,entry_id and Prefer: resolution=merge-duplicates.
-- Two callers racing the SAME entry_id could both pass the SELECT before
-- either INSERT landed; the second INSERT's merge-duplicates resolution then
-- silently OVERWRITES the first row rather than hitting the 409 path --
-- exactly the "never silently overwritten" guarantee this table's append-only
-- entry types (administration, count, reconciliation, assessment_refusal)
-- exist to hold. Modelled directly on
-- public.law_check_and_insert_disbursement() (sql/sairnlaw_trusttx_
-- functions.sql:104-254), the platform's own proven pattern for exactly this
-- shape: pg_advisory_xact_lock scoped to the row's real unique key, held
-- across the check-then-write inside one transaction, with the same
-- READ-COMMITTED precondition asserted rather than assumed -- see that
-- function's own header comment for the full reasoning on why the isolation
-- level matters even though the lock is held correctly either way.
create or replace function public.alf_check_and_insert_mar_entry(
  p_license_hash text, p_entry_id text, p_resident_id text,
  p_assigned_employee_id text, p_entry_type text, p_data jsonb
) returns public.alf_mar
language plpgsql
as $$
declare
  v_row public.alf_mar;
  v_iso text;
begin
  v_iso := current_setting('transaction_isolation');
  if v_iso <> 'read committed' then
    raise exception
      'alf_check_and_insert_mar_entry requires READ COMMITTED; this '
      'transaction is %. The advisory lock serialises acquisition, not the '
      'snapshot, so under % a waiting caller''s existence check can still see '
      'a pre-lock snapshot and reach the insert believing no row exists, '
      'with the lock held correctly the whole time.',
      v_iso, v_iso
      using errcode = 'invalid_transaction_state';
  end if;

  -- Scoped to (license_hash, entry_id) -- the exact pair the real unique
  -- constraint covers (unique (license_hash, entry_id), above) -- so two
  -- callers racing the SAME entry_id serialise here and two callers on
  -- different entry_ids never contend with each other.
  perform pg_advisory_xact_lock(hashtext(p_license_hash || ':' || p_entry_id));

  if p_entry_type <> 'medication_order' then
    -- APPEND-ONLY TYPES: administration, count, reconciliation,
    -- assessment_refusal. Genuinely atomic now that the lock is held across
    -- both statements -- a second caller for the same entry_id blocks on the
    -- lock, and by the time it acquires it the first caller's row is already
    -- committed and visible (READ COMMITTED, asserted above), so this INSERT
    -- correctly finds the conflict and refuses rather than merging over it.
    insert into public.alf_mar
      (license_hash, app_id, entry_id, resident_id, assigned_employee_id, entry_type, data, updated_at)
    values
      (p_license_hash, 'sairncare', p_entry_id, p_resident_id, p_assigned_employee_id, p_entry_type, p_data, now())
    on conflict (license_hash, entry_id) do nothing
    returning * into v_row;

    if v_row.id is null then
      raise exception
        'ALREADY_RECORDED: entry % has already been recorded and cannot be overwritten',
        p_entry_id
        using errcode = 'P0001';
    end if;
  else
    -- medication_order is the one mutable-in-place type (edit/discontinue an
    -- order) -- same upsert shape alf_clients itself uses, safe to merge
    -- because it is not an append-only event log.
    insert into public.alf_mar
      (license_hash, app_id, entry_id, resident_id, assigned_employee_id, entry_type, data, updated_at)
    values
      (p_license_hash, 'sairncare', p_entry_id, p_resident_id, p_assigned_employee_id, p_entry_type, p_data, now())
    on conflict (license_hash, entry_id) do update set
      resident_id = excluded.resident_id,
      assigned_employee_id = excluded.assigned_employee_id,
      data = excluded.data,
      updated_at = excluded.updated_at
    returning * into v_row;
  end if;

  -- NO PATH ABOVE CAN RETURN NULL. Asserted rather than assumed, same
  -- discipline as law_check_and_insert_disbursement's own closing guard: if a
  -- future edit reintroduces a null path, this raises instead of handing the
  -- caller a success it did not earn.
  if v_row.id is null then
    raise exception
      'MAR_ENTRY_NOT_WRITTEN: no alf_mar row was produced for % -- nothing was recorded',
      p_entry_id
      using errcode = 'P0001';
  end if;

  return v_row;
end;
$$;

revoke all on function public.alf_check_and_insert_mar_entry from public;
grant execute on function public.alf_check_and_insert_mar_entry to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_mar;
