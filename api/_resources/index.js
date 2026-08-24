// api/_resources/index.js
// Merges the per-app resource registries into the single map api/sd-data.js
// validates against, and GENERATES the "resource must be one of: ..." error
// text from that same merge.
//
// WHY: sd-data.js used to hold one shared RESOURCES map plus a separately
// hand-maintained error string listing the same names. Every SAIRN app
// appended to both, on the same lines, so parallel sessions collided on every
// push. Verified against real history before changing anything: all three
// merge conflicts hit while building SAIRNcode were in exactly these two
// places, while the request-handler branches changed by 100+ lines in the same
// commits and merged cleanly every time, because each app appends its branch
// in its own region.
//
// The handler branches were therefore deliberately left in sd-data.js. They
// close over roughly fifteen handler-local bindings (licHash, headers, rest,
// enc, nowISO, payload, isPaid, ...) and serve 11 live apps; moving them would
// have been a large behavioural risk for no additional collision benefit.
//
// TWO REAL PROBLEMS THIS FIXES, beyond the collisions:
//   1. Drift between the map and the error text. They had already diverged --
//      employee_profile was a valid, working resource that was missing from
//      the hand-maintained list, so a caller who mistyped it got a "must be
//      one of" list that omitted a resource which actually works. Generating
//      the text from the map makes that class of drift impossible.
//   2. Silent duplicate registration. Two apps claiming the same resource name
//      previously just overwrote each other in an object literal with no
//      signal. assertNoDuplicates() below throws at load instead, which is the
//      exact hazard sairnscape.js's own comment warns about for scp_jobs.
//
// EXTRA ACTIONS (2026-08-24). Resources whose verbs go beyond read/write now
// declare them here too, via each module's optional `extraActions` map. This
// closes a third, separate trap that sd-data.js had already documented against
// itself: adding a resource meant editing THREE places -- the registry, the
// handler branch, and a hand-written verb condition in sd-data.js -- and
// missing the third produced a registered resource with a working branch that
// still answered 400. Two of the three now live in the same file, and
// assertExtraActionsAreOwned() below refuses to load a verb declared for a
// resource its own module does not register.

const REGISTRY_MODULES = [
  require('./shared'),
  require('./stonedesk'),
  require('./sairnscape'),
  require('./sairngrounds'),
  require('./sairndesign'),
  require('./sairnlegacy'),
  require('./sairndental'),
  require('./sairnlaw'),
  require('./sairncode'),
  require('./sairnbuild'),
  require('./sairnsenior'),
  require('./sairncare'),
  require('./sairnroofing'),
];

// Fail loudly at load rather than silently letting one app shadow another's
// resource. A duplicate here means two apps would share a table route, which
// is the failure mode that would be hardest to diagnose from the outside.
function assertNoDuplicates(modules) {
  const seen = Object.create(null);
  for (const mod of modules) {
    for (const name of mod.resources) {
      if (seen[name]) {
        throw new Error(
          'Duplicate resource "' + name + '" registered by both ' +
          seen[name] + ' and ' + mod.app + ' (api/_resources). Resource names ' +
          'must be unique across apps -- prefix the newer one.'
        );
      }
      seen[name] = mod.app;
    }
  }
  return seen;
}

const OWNER_BY_RESOURCE = assertNoDuplicates(REGISTRY_MODULES);

// A module may only grant extra verbs to resources it actually registers.
// Without this, a typo ('alf_payer_rule') would silently produce a verb
// permission that can never match, which is indistinguishable from the bug
// this map exists to prevent -- and a deliberate grant against another app's
// resource would be a cross-app authorization change hidden in a data literal.
function assertExtraActionsAreOwned(modules) {
  const merged = Object.create(null);
  for (const mod of modules) {
    const extra = mod.extraActions || {};
    const own = new Set(mod.resources);
    for (const name of Object.keys(extra)) {
      if (!own.has(name)) {
        throw new Error(
          'api/_resources/' + mod.app + '.js declares extraActions for "' + name +
          '", which it does not register. A module may only grant verbs to its ' +
          'own resources.'
        );
      }
      const verbs = extra[name];
      if (!Array.isArray(verbs) || verbs.length === 0) {
        throw new Error(
          'api/_resources/' + mod.app + '.js: extraActions["' + name + '"] must be ' +
          'a non-empty array of verb strings.'
        );
      }
      for (const verb of verbs) {
        if (verb === 'read' || verb === 'write') {
          throw new Error(
            'api/_resources/' + mod.app + '.js: extraActions["' + name + '"] lists "' +
            verb + '", which every resource already allows. Remove it.'
          );
        }
      }
      merged[name] = verbs.slice();
    }
  }
  return merged;
}

// resource -> array of verbs allowed beyond the universal 'read'/'write'.
const EXTRA_ACTIONS = assertExtraActionsAreOwned(REGISTRY_MODULES);

// Ordered list, app by app, in the registration order above.
const RESOURCE_NAMES = REGISTRY_MODULES.reduce(
  (all, mod) => all.concat(mod.resources), []
);

// The map sd-data.js checks with `if (!RESOURCES[resource])`. Same shape and
// same truthiness as the object literal it replaces.
const RESOURCES = RESOURCE_NAMES.reduce((map, name) => {
  map[name] = true;
  return map;
}, Object.create(null));

// Generated, so it can never again disagree with the map above.
const RESOURCE_LIST_TEXT = RESOURCE_NAMES.join(', ');

module.exports = {
  RESOURCES,
  RESOURCE_NAMES,
  RESOURCE_LIST_TEXT,
  OWNER_BY_RESOURCE,
  REGISTRY_MODULES,
  EXTRA_ACTIONS,
};
