/* tools/sairn_dom_snapshot.js
 *
 * Produces the RENDERED-DOM snapshot that tools/sairn_reachability_check.py
 * consumes in --live mode.
 *
 * WHY A SNAPSHOT AND NOT STATIC ANALYSIS. The reachability check's own
 * docstring admits its limit: "Static. It cannot see a handler attached at
 * runtime from a computed name." That limit is not academic -- every SAIRN app
 * builds its tables by assigning innerHTML from JS template strings, so a
 * button that exists for the customer exists nowhere in the markup a grep can
 * read. An R3 "defined but never called or wired" finding against such a
 * handler is a false positive, and a checker people learn to disbelieve is a
 * checker nobody runs.
 *
 * It is also the lesson from SAIRNbiz on 2026-09-01: grepping the source for a
 * removed string reported a survivor five separate times when the only hit was
 * a comment documenting the removal. The discriminating question is always
 * what the LIVE page does, not what the file says.
 *
 * HOW TO USE
 *   1. Open the app (deployed or local) and get past the licence gate, so the
 *      panels have actually rendered. A snapshot of the gate screen describes
 *      the gate screen and nothing else -- the tool records `panels_seen` so
 *      that mistake is visible rather than silent.
 *   2. Exercise the app: click through every nav entry. Handlers only exist in
 *      the DOM once their panel has rendered.
 *   3. Run this whole file in the console.
 *   4. Save the printed JSON as dom/<app>.dom.json in the clone.
 *   5. python tools/sairn_reachability_check.py --live dom/<app>.dom.json <app>.html
 *
 * THE SNAPSHOT IS ONLY AS GOOD AS THE CLICKING. A handler on a panel you never
 * opened is absent from the snapshot and will still read as unreachable. That
 * is why `panels_seen` and `nav_total` are both recorded: the tool refuses to
 * clear a finding from a snapshot that visited fewer panels than the app has.
 */
(function () {
  'use strict';

  var out = {
    _generated_at: new Date().toISOString(),
    url: location.href,
    handler_names: [],   // every function name referenced by an on*= attribute
    element_ids: [],     // every id present in the rendered DOM
    window_functions: [] // every function currently hanging off window
  };

  // 1. Handler names from every on*= attribute in the LIVE tree. This is the
  //    half a source grep cannot do: these attributes were written by JS.
  var names = {};
  var all = document.querySelectorAll('*');
  for (var i = 0; i < all.length; i++) {
    var el = all[i];
    if (el.id) { names['#' + el.id] = 1; }
    var attrs = el.attributes || [];
    for (var j = 0; j < attrs.length; j++) {
      var a = attrs[j];
      if (a.name.slice(0, 2) !== 'on') continue;
      var m = String(a.value).match(/([A-Za-z_$][\w$]*)\s*\(/g) || [];
      for (var k = 0; k < m.length; k++) {
        names['fn:' + m[k].replace(/\s*\($/, '')] = 1;
      }
    }
  }

  var ids = [], fns = [];
  Object.keys(names).forEach(function (key) {
    if (key.charAt(0) === '#') ids.push(key.slice(1));
    else fns.push(key.slice(3));
  });
  out.element_ids = ids.sort();
  out.handler_names = fns.sort();

  // 2. What is actually callable right now. A window function absent here was
  //    never defined at all, which is a different finding from unreachable.
  var wf = [];
  for (var key in window) {
    try { if (typeof window[key] === 'function') wf.push(key); } catch (e) { /* cross-origin */ }
  }
  out.window_functions = wf.sort();

  // 3. Coverage, so a snapshot taken too early cannot quietly clear findings.
  //
  // MEASURED BY HANDLERS PRESENT, NOT BY VISIBILITY, and the first version got
  // this wrong. Counting panels whose computed display is not 'none' returns 1
  // of 62 on StoneDesk no matter how much you click -- panels are all in the
  // tree and all hidden but the active one -- so the guard would have refused
  // to clear anything, forever, and the live mode would have been useless.
  //
  // What matters is whether a panel's handlers are IN THE TREE. Markup-declared
  // ones are, hidden or not; only rows a renderer has never built are missing.
  // On a freshly loaded StoneDesk this reads 62/62 with 9 panels carrying
  // rendered rows, which is the honest picture: the structure is all there, the
  // dynamic content is not, and `panels_with_rendered_rows` says so plainly
  // rather than being folded into one number.
  var panels = document.querySelectorAll('[id^="panel-"], .panel');
  var withHandlers = 0, withRows = 0;
  for (var p = 0; p < panels.length; p++) {
    if (panels[p].querySelectorAll('[onclick],[onchange],[oninput],[onsubmit],[onblur]').length) withHandlers++;
    if (panels[p].querySelectorAll('tbody tr').length) withRows++;
  }
  out.panels_total = panels.length;
  out.panels_with_handlers = withHandlers;
  out.panels_with_rendered_rows = withRows;
  out.gated = !!(document.getElementById('gateLicense') || document.getElementById('gatePin'));

  var json = JSON.stringify(out, null, 2);
  try { console.log(json); } catch (e) { /* ignore */ }
  return json;
})();
