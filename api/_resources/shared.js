// api/_resources/shared.js
// Resource registry for resources shared across multiple SAIRN apps.
//
// WHY THIS FILE EXISTS: api/sd-data.js used to carry one shared RESOURCES map
// that every SAIRN app appended to, plus a hand-maintained error-message
// string listing the same names. Both were single shared lines, so any two
// sessions adding a resource in parallel collided on every push -- that was
// the cause of every api/sd-data.js merge conflict, not the request handlers,
// which append in separate regions and merge cleanly.
//
// Each app now owns its own registry file. sd-data.js merges them at load and
// GENERATES the error string from the merge, so the two can no longer drift
// apart (they already had: employee_profile was a valid resource missing from
// the hand-maintained list).
//
// Adding a resource: add the name here, and add its handler branch in
// api/sd-data.js as before. Nothing else needs editing.
//
// The request-handling branches themselves were deliberately NOT moved -- they
// close over ~15 handler-local bindings and serve 11 live apps, and they were
// never the source of the collisions.

module.exports = {
  app: 'shared',
  // 'reserve' on slabs (2026-09-02). It is declared HERE rather than in
  // stonedesk.js because this file owns 'slabs', and index.js enforces that a
  // module may only grant verbs to its own resources -- it refused the first
  // attempt to put this in stonedesk.js, which is the guard working.
  //
  // NOT a second way to write a slab. 'write' is a blind upsert
  // (resolution=merge-duplicates, last writer wins) and that is exactly how a
  // slab reserved for one customer was silently reassigned to another,
  // destroying `reservedFor` -- the only record of who had it. 'reserve' is a
  // compare-and-swap that REFUSES on conflict. The two verbs are kept apart on
  // purpose: ordinary slab edits stay cheap, and a reservation does not.
  //
  // The handler branch is StoneDesk's, and the verb reaches only 'slabs'.
  extraActions: {
    slabs: ['reserve'],
  },
  resources: [
    'profile',
    'memory',
    'employees',
    'slabs',
    'render_usage',
    'shared_knowledge',
  // StoneDesk Employee Profiles (2026-08-06) -- see sql/sd_employee_profiles_schema.sql.
    'employee_profile',
  ],
};
