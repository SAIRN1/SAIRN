# H1 -> hank: sairnlaw.html matter conflict-check override has no attribution

Written 2026-10-13, batch b24 item 2 -- the same override-shape sweep
that found item 1's leg_monuments gap, found this second, independently,
in a different app. `api/` is hank's directory; same fix shape as item
1 (route, not fix).

## The gap, exact file:line

`sairnlaw.html:3028-3047`, `saveMatter()`:

```js
async function saveMatter(){
  ...
  var hits=conflictCheck(namesToCheck,null);
  if(hits.length&&!$('mtoverride').checked){
    $('matter-err').textContent='Conflict(s) found -- review above and check the override box to proceed, or resolve the conflict first';
    return;
  }
  var rec={id:newId('MT'),matter_number:nextMatterNumber(),client_id:clientId,matter_name:name,
    practice_area:$('mtarea').value.trim(),status:'Open',opened_date:lawLocalToday(),closed_date:'',
    responsible_attorney:$('mtattorney').value.trim(),opposing_parties:parties,
    conflict_check_result:hits,notes:$('mtnotes').value.trim(),created_at:lawLocalToday()};
  ...
}
```

## What IS recorded, checked before assuming the worst

`conflict_check_result:hits` IS saved on every matter, always -- so the
WHAT (which specific conflict hits existed) is not lost, and because the
save is BLOCKED when `hits.length` is truthy and override is unchecked,
a saved matter with a non-empty `conflict_check_result` necessarily means
an override happened. That inference is real and the record does not
silently hide that a conflict existed.

## What is NOT recorded

Nothing on `rec` says WHO authorized proceeding despite the conflict, or
WHEN the override decision itself was made (`created_at`/`opened_date`
cover when the matter record was created, which is the same moment, but
there is no separately named override timestamp if the matter is edited
later). `responsible_attorney` is a FREE-TEXT field
(`$('mtattorney').value.trim()`) typed into the form -- not the
authenticated session's identity, not cross-checked against who is
actually signed in, and not specifically the person who checked the
override box (whoever is filling out the form controls both fields).

## Why this is HIGHER stakes than the leg_monuments shape (item 1)

A law firm opening a matter despite a detected conflict of interest,
with no verifiable record of which attorney actually reviewed and
authorized that decision, is a real professional-responsibility exposure
-- bar disciplinary rules in most jurisdictions require documented,
attorney-level conflict waivers, not a self-reported text field anyone
at a keyboard could fill in. This is the same accountability-gap SHAPE
as item 1 and as seq958's original employee-credential-attribution
finding, now found a third time, in a context where the real-world cost
of the gap is a bar complaint rather than a reputational one.

## The audit-event shape needed

Same recommendation as item 1: an attributed event (or at minimum a
server-stamped `overridden_by`/`override_at` pair) written from the
VERIFIED session, not a client-supplied free-text field. `law_matters`'
write path would need the session's `employee_id` threaded through the
same way `bld_draws`'s dedicated branch already does
(`dSession.employee_id`), rather than trusting
`$('mtattorney').value`.

## Not this role's to decide

Naming the gap and the shape of evidence a fix should produce is this
role's job; the design (new column, new audit table, or something
else) is hank's.
