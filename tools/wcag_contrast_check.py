#!/usr/bin/env python
# OWNER: fourth
"""tools/wcag_contrast_check.py -- WCAG 2.2 AA contrast, measured in the
RENDERED page, on every panel of a SAIRN app.

WHY THIS EXISTS (2026-10-17, fourth b29). Guardian checks source. The code
scrubber checks patterns. `sairn-visual-review` says to compute real contrast
ratios rather than eyeball them -- and nothing on this platform could, so for
nineteen apps nobody ever had. The first time it was run, against SAIRNdental's
live deployment, it found **41 distinct AA failures**, including every primary
button in the app (white on #0EA5E9, 2.77:1) and every active sidebar item
(3.57:1). None of them were visible to any check that reads a file, because a
contrast ratio does not exist in a file. It exists after the cascade resolves.

── THE BACKGROUND IS A COMPOSITE, AND THE FIRST DRAFT GOT THAT WRONG ──────
The first version resolved a text node's background by walking up to the first
ancestor whose `background-color` alpha exceeded 0.1 and treating it as opaque.
`.hbadge` and `.hbtn` in sairndental are `rgba(255,255,255,.15)` painted on a
blue header, so it reported **white on white, ratio 1.00, on all 23 panels** --
a fabricated figure on elements that really render at 3.29:1. The real surface
exists only after the compositor combines the layers. `_EFF_BG` below composites
them with real alpha, and `--selftest` carries that exact case as a fixture in
both directions, because the rule this tool was built to serve is the one it
broke first. Cross-domain convention 38.

── FAIL-CLOSED ───────────────────────────────────────────────────────────
Playwright absent, a browser missing, a sign-in that does not land in the app:
**exit 2 COULD NOT RUN**, never 0. A signed-out app renders a licence gate and
almost nothing else, so a sweep of it would return very few failures and would
look exactly like a clean app. "Could not run" is a third state and is never
folded into "passed" -- CLAUDE.md, PR S1.11.

USAGE
    python tools/wcag_contrast_check.py --selftest
    python tools/wcag_contrast_check.py --app sairndental
    python tools/wcag_contrast_check.py --app sairndental --local            # working tree
    python tools/wcag_contrast_check.py --app sairndental --local --file X   # any bytes
    python tools/wcag_contrast_check.py --app sairndental --json out.json

EXIT
    0  no AA failure on any panel visited
    1  at least one AA failure
    2  COULD NOT RUN (and it says which part could not run)
"""
import argparse
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# Each app's sign-in facts. Credentials are NOT stored here -- they are read
# from docs/2026-09-03-demo-credentials.md's table at run time, so this file
# never becomes a second place a PIN lives and go stale.
APPS = {
    "sairndental": {
        "url": "https://sairn.vercel.app/sairndental",
        "file": "sairndental.html",
        "nav": "nav",                       # the app's own panel switcher
        "panel_prefix": "panel-",
    },
}

CREDS_DOC = REPO / "docs" / "2026-09-03-demo-credentials.md"

# ---------------------------------------------------------------- colour ---


def _parse_rgb(css):
    """'rgba(1, 2, 3, .5)' -> (1.0, 2.0, 3.0, 0.5). None if unparseable."""
    s = str(css)
    i, j = s.find("("), s.rfind(")")
    if i < 0 or j < 0:
        return None
    # `rgb(1 2 3 / .5)` is as valid as `rgba(1,2,3,.5)` and getComputedStyle
    # returns the space form in some engines. Splitting on commas alone turned
    # it into one unparseable token and the whole colour was REFUSED -- a
    # fixture caught that, not a reading of this line.
    body = s[i + 1:j].replace("/", " ").replace(",", " ")
    parts = [p for p in body.split() if p]
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        return None
    if len(vals) < 3:
        return None
    return (vals[0], vals[1], vals[2], vals[3] if len(vals) > 3 else 1.0)


def _lum(c):
    def f(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contrast(fg, bg):
    """WCAG 2.2 contrast ratio between two OPAQUE colours."""
    l1, l2 = _lum(fg), _lum(bg)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def composite(layers, base=(255.0, 255.0, 255.0, 1.0)):
    """Alpha-composite `layers` (nearest-first) over `base`, like the compositor.

    This is the function the first draft did not have. Returns opaque RGB.
    """
    out = base
    for c in reversed(layers):
        a = c[3]
        out = (c[0] * a + out[0] * (1 - a),
               c[1] * a + out[1] * (1 - a),
               c[2] * a + out[2] * (1 - a),
               1.0)
    return out


def required_ratio(px, bold):
    """AA: 3.0 for large text (>=24px, or >=18.66px bold), else 4.5."""
    return 3.0 if (px >= 24 or (bold and px >= 18.66)) else 4.5


# ------------------------------------------------------------- in-page JS ---

_PAGE_ASSERT = r"""
() => {
  const parse = (c) => { const s = String(c); const i = s.indexOf('('), j = s.lastIndexOf(')');
    if (i < 0 || j < 0) return null;
    const p = s.slice(i+1, j).replace(/\//g, ',').split(',').map(x => parseFloat(x.trim())).filter(x => !isNaN(x));
    if (p.length < 3) return null;
    return {r:p[0], g:p[1], b:p[2], a:(p.length>3?p[3]:1)}; };
  const lum = (c) => { const f=(v)=>{v/=255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4);};
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
  const ratio = (a,b) => { const l1=lum(a), l2=lum(b); return (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05); };
  // THE EFFECTIVE BACKGROUND IS A COMPOSITE. Taking the first ancestor whose
  // alpha clears a threshold reported white-on-white at 1.00 for every
  // translucent pill in the app. Collect the stack, composite it.
  const effBg = (el) => {
    const layers = []; let n = el;
    while (n && n !== document.documentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 0.999) break; }
      n = n.parentElement;
    }
    let out = {r:255,g:255,b:255,a:1};
    for (let i = layers.length - 1; i >= 0; i--) { const c = layers[i];
      out = {r:c.r*c.a+out.r*(1-c.a), g:c.g*c.a+out.g*(1-c.a), b:c.b*c.a+out.b*(1-c.a), a:1}; }
    return out;
  };
  const out = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    const t = (n.nodeValue||'').trim(); if (t.length < 2) continue;
    const el = n.parentElement; if (!el || el.offsetParent === null) continue;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || parseFloat(st.opacity||'1') < 0.15) continue;
    const fg = parse(st.color); if (!fg) continue;
    const px = parseFloat(st.fontSize) || 16;
    const bold = (parseInt(st.fontWeight,10)||400) >= 700;
    const large = px >= 24 || (bold && px >= 18.66);
    const bg = effBg(el);
    const r = ratio(fg, bg);
    const need = large ? 3.0 : 4.5;
    if (r + 0.005 < need) out.push({
      ratio: Math.round(r*100)/100, need: need, px: px, bold: bold,
      color: st.color,
      bg: 'rgb(' + [Math.round(bg.r), Math.round(bg.g), Math.round(bg.b)].join(',') + ')',
      where: el.tagName.toLowerCase() + (el.id ? '#'+el.id : '') +
             (typeof el.className === 'string' && el.className ? '.'+el.className.split(/\s+/)[0] : ''),
      text: t.slice(0, 60)});
  }
  return out;
}
"""


# ---------------------------------------------------------------- selftest ---

def selftest():
    """Fixtures in BOTH directions. Criteria locked here, before any run."""
    cases = []

    def ok(name, got, want, tol=0.01):
        good = abs(got - want) <= tol if isinstance(want, float) else got == want
        cases.append((good, name, got, want))

    W = (255.0, 255.0, 255.0, 1.0)
    BLACK = (0.0, 0.0, 0.0, 1.0)

    # 1. the two WCAG anchors
    ok("white on black is 21", round(contrast(W, BLACK), 2), 21.0)
    ok("white on white is 1", round(contrast(W, W), 2), 1.0)

    # 2. the sky-500 primary button, the defect this tool was built on
    ok("white on #0EA5E9 (sky-500) is 2.77",
       round(contrast(W, (14.0, 165.0, 233.0, 1.0)), 2), 2.77)
    ok("white on #0369A1 (sky-700) is 5.93",
       round(contrast(W, (3.0, 105.0, 161.0, 1.0)), 2), 5.93)

    # 3. THE COMPOSITING FIXTURE, in the direction that was wrong.
    #    rgba(255,255,255,.15) over #0369A1 is NOT white; white text on the
    #    real composite is a failure at ~4.37, not a fabricated 1.00.
    veil = [(255.0, 255.0, 255.0, 0.15)]
    comp = composite(veil, base=(3.0, 105.0, 161.0, 1.0))
    ok("a .15 white veil over sky-700 is NOT white", round(comp[0]), 41)
    # 4.40 unrounded; 4.37 if the channels are first quantised to the 8-bit
    # values actually painted. Both are below AA and the fixture asserts the
    # one this code returns rather than the one a note remembered.
    ok("white on that composite is 4.40", round(contrast(W, comp), 2), 4.40)
    naive = contrast(W, (255.0, 255.0, 255.0, 1.0))
    ok("...and the NAIVE first-opaque-ancestor answer would have been 1.00",
       round(naive, 2), 1.0)

    # 4. compositing is order-sensitive and nearest-first
    stack = [(0.0, 0.0, 0.0, 0.5), (255.0, 0.0, 0.0, 1.0)]
    ok("black .5 over red composites to 128,0,0", round(composite(stack)[0]), 128)

    # 5. the large-text threshold, on both sides of each boundary
    ok("13px normal needs 4.5", required_ratio(13, False), 4.5)
    ok("24px normal needs 3.0", required_ratio(24, False), 3.0)
    ok("23.9px normal still needs 4.5", required_ratio(23.9, False), 4.5)
    ok("19px BOLD needs 3.0", required_ratio(19, True), 3.0)
    ok("18px bold still needs 4.5", required_ratio(18, True), 4.5)

    # 6. parser arms, including the ones that must REFUSE
    ok("rgb() parses", _parse_rgb("rgb(1, 2, 3)"), (1.0, 2.0, 3.0, 1.0))
    ok("rgba() parses alpha", _parse_rgb("rgba(1, 2, 3, 0.5)"), (1.0, 2.0, 3.0, 0.5))
    ok("space/slash syntax parses", _parse_rgb("rgb(1 2 3 / 0.5)"), (1.0, 2.0, 3.0, 0.5))
    ok("a named colour is REFUSED, not guessed", _parse_rgb("transparent"), None)
    ok("garbage is REFUSED", _parse_rgb("not a colour"), None)
    ok("a two-component colour is REFUSED", _parse_rgb("rgb(1,2)"), None)

    bad = [c for c in cases if not c[0]]
    for good, name, got, want in cases:
        print("  %-4s %-62s got=%r want=%r" % ("ok" if good else "FAIL", name, got, want))
    print("%d/%d fixtures classify correctly" % (len(cases) - len(bad), len(cases)))
    return 1 if bad else 0


# -------------------------------------------------------------------- run ---

def read_demo_credential(app):
    """Pull the app's demo licence/PIN out of the credentials DOC, not from here."""
    if not CREDS_DOC.is_file():
        return None, "credentials doc is absent: %s" % CREDS_DOC
    want = {"sairndental": "/api/dnt-auth"}.get(app)
    for line in CREDS_DOC.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|") or (want and want not in line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        lic = cells[1].strip("`")
        emp = cells[2].strip("`")
        pin = "".join(ch for ch in cells[3] if ch.isdigit())
        if lic and emp and len(pin) >= 6:
            return {"lic": lic, "emp": emp, "pin": pin[:8]}, None
    return None, "no usable row for %s in %s" % (app, CREDS_DOC.name)


def run(app, local, file_override, json_out, quiet):
    cfg = APPS.get(app)
    if not cfg:
        print("COULD NOT RUN: no sign-in profile for %r (known: %s)"
              % (app, ", ".join(sorted(APPS))))
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("COULD NOT RUN: playwright is not installed in this interpreter.")
        print("  python -m pip install playwright && python -m playwright install chromium")
        return 2

    cred, why = read_demo_credential(app)
    if not cred:
        print("COULD NOT RUN: %s" % why)
        return 2

    body = None
    if local:
        src = pathlib.Path(file_override) if file_override else (REPO / cfg["file"])
        if not src.is_file():
            print("COULD NOT RUN: --local asked for %s and it is not a file" % src)
            return 2
        body = src.read_text(encoding="utf-8")
        if not quiet:
            print("LOCAL: serving %d bytes of %s at the real origin"
                  % (len(body.encode("utf-8")), src.name))

    findings = {}
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:
                print("COULD NOT RUN: chromium would not launch -- %s: %s"
                      % (type(e).__name__, str(e)[:160]))
                return 2
            pg = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
            if body is not None:
                # Keep the REAL ORIGIN and swap only the document bytes. Over
                # file:// the page gets an opaque origin, every API call is
                # refused and sign-in cannot happen -- which would sweep a
                # signed-out app and call it clean.
                pg.route(cfg["url"], lambda route: route.fulfill(
                    status=200, content_type="text/html; charset=utf-8", body=body))
            pg.goto(cfg["url"], wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(1500)
            pg.fill("#gkey", cred["lic"])
            pg.click("#gate .gbtn")
            pg.wait_for_timeout(1000)
            pg.fill("#au-emp", cred["emp"])
            pg.fill("#au-pin", cred["pin"])
            pg.click("#pin button.gbtn")
            pg.wait_for_timeout(6000)
            if not pg.is_visible("#app"):
                err = (pg.text_content("#perr") or "").strip()
                print("COULD NOT RUN: sign-in did not enter the app%s"
                      % ((" -- the app said: %r" % err) if err else ""))
                print("  A signed-out app renders a licence gate and almost nothing")
                print("  else, so sweeping it would look like a clean result.")
                browser.close()
                return 2
            panels = pg.evaluate(
                "(pfx) => Array.from(document.querySelectorAll('.panel'))"
                ".map(p => p.id).filter(Boolean).map(id => id.slice(pfx.length))",
                cfg["panel_prefix"])
            if not panels:
                print("COULD NOT RUN: no .panel elements found after sign-in")
                browser.close()
                return 2
            for pid in panels:
                pg.evaluate("([fn, id]) => window[fn](id)", [cfg["nav"], pid])
                pg.wait_for_timeout(900)
                for f in pg.evaluate(_PAGE_ASSERT):
                    key = (f["ratio"], f["color"], f["bg"], f["px"], f["bold"], f["where"])
                    rec = findings.setdefault(str(key), {"f": f, "panels": []})
                    if pid not in rec["panels"]:
                        rec["panels"].append(pid)
            browser.close()
    except Exception as e:
        print("COULD NOT RUN: the sweep raised -- %s: %s" % (type(e).__name__, str(e)[:200]))
        return 2

    items = sorted(findings.values(), key=lambda v: v["f"]["ratio"])
    print("WCAG 2.2 AA -- %s, %d panel(s) visited, %s"
          % (app, len(panels), "working tree" if local else "live deployment"))
    for v in items:
        f = v["f"]
        try:
            text = f["text"].encode("ascii", "replace").decode("ascii")
        except Exception:
            text = "?"
        print("  %5.2f (need %.1f)  %-20s on %-18s %gpx%s  x%d panel(s)  %-34s %s"
              % (f["ratio"], f["need"], f["color"], f["bg"], f["px"],
                 " bold" if f["bold"] else "", len(v["panels"]), f["where"][:34], text[:40]))
    print("DISTINCT AA FAILURES: %d" % len(items))
    if json_out:
        pathlib.Path(json_out).write_text(
            json.dumps([{"f": v["f"], "panels": sorted(v["panels"])} for v in items], indent=1),
            encoding="utf-8")
        print("wrote %s" % json_out)
    return 1 if items else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--app", default=None)
    ap.add_argument("--local", action="store_true",
                    help="serve the working-tree file at the real origin")
    ap.add_argument("--file", default=None, help="with --local, serve these bytes instead")
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.app:
        ap.print_help()
        return 2
    # EVERY MODE RUNS THE FIXTURES FIRST and refuses to report if they fail,
    # rather than reporting with a caveat.
    rc = selftest()
    if rc:
        print("COULD NOT RUN: the fixtures do not classify, so no sweep is trustworthy.")
        return 2
    print("")
    return run(a.app, a.local, a.file, a.json_out, a.quiet)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
