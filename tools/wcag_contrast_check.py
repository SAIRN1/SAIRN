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

── TWO MODES, AND THE GATE RUNS THE ONE THAT CAN RUN EVERYWHERE (b30) ─────
Michael's decision 2026-10-19 was to wire this into the PUSH GATE rather than a
cadence. The RENDERED mode cannot be that gate and the reason is measured, not
cautious: it needs playwright, a chromium binary, network reach to Vercel, a
live Supabase and a demo PIN, and it needs a per-app sign-in profile -- and a
survey of the seventeen root products found **seven with no `#gkey` licence
gate, five with no `nav()` panel switcher and three with no `panel-*` elements
at all**, so a rendered gate would exit 2 COULD NOT RUN on most of the platform.
A gate that cannot run is a gate that gets skipped, and 80 of the 94 rows in
docs/BYPASS-LOG.jsonl are already that shape.

So `--gate` runs the STATIC half, which needs nothing but the file:

  A. **A SELF-CONTAINED OPAQUE PAIR BELOW AA.** A CSS rule that declares BOTH
     `color` and a `background` that resolve to opaque colours is a complete
     contrast fact with no DOM required. This is where the worst of b29 lived:
     `.bp{background:var(--p);color:#fff}` at 2.77:1 was every primary button
     in SAIRNdental, and `.sb.on{background:var(--pt);color:var(--pd)}` at
     3.57:1 was every active sidebar row.
  B. **A `var(--token)` THAT IS DEFINED NOWHERE AND HAS NO FALLBACK.** This is
     not a style question: an unresolvable custom property makes the WHOLE
     declaration invalid at computed-value time, so the property is DROPPED
     rather than falling back. b28 shipped `border-left:3px solid var(--accent)`
     and the stripe rendered at 0px; 22 passing unit arms could not see it.

**WHAT THE STATIC HALF DELIBERATELY DOES NOT CLAIM.** A rule that declares a
colour and no background, or a background with alpha below 1, is an
ANCESTOR-DEPENDENT fact and this mode reports it **UNRESOLVED** -- counted,
printed, and never folded into either a pass or a failure. Guessing the
ancestor is exactly the mistake the rendered half made in b29 when it read
`rgba(255,255,255,.15)` over a blue bar as opaque white and fabricated a 1.00.
The rendered mode remains the deeper check and stays available per app.

USAGE
    python tools/wcag_contrast_check.py --selftest
    python tools/wcag_contrast_check.py --gate sairndental.html [more.html]  # push gate
    python tools/wcag_contrast_check.py --static --all                       # every product
    python tools/wcag_contrast_check.py --app sairndental                    # rendered, live
    python tools/wcag_contrast_check.py --app sairndental --local            # working tree
    python tools/wcag_contrast_check.py --app sairndental --local --file X   # any bytes
    python tools/wcag_contrast_check.py --app sairndental --json out.json

EXIT
    0  no finding
    1  at least one finding (an AA failure, or an undefined custom property)
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


# ------------------------------------------------------------ static mode ---
# Everything below needs nothing but the bytes of the file: no browser, no
# network, no credential. That is the whole reason it can be a push gate.

import re  # noqa: E402  -- kept next to the parser that is its only user

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_STYLE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
_VAR = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,([^()]*(?:\([^()]*\)[^()]*)*))?\)")
_DECL_VAR = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;}]+)")
_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# Keywords that are real colours but carry no ancestor dependency.
_NAMED = {"white": (255.0, 255.0, 255.0, 1.0), "black": (0.0, 0.0, 0.0, 1.0),
          "red": (255.0, 0.0, 0.0, 1.0), "transparent": (0.0, 0.0, 0.0, 0.0)}


def _hex_to_rgba(h):
    m = _HEX.match(h.strip())
    if not m:
        return None
    s = m.group(1)
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return (float(int(s[0:2], 16)), float(int(s[2:4], 16)), float(int(s[4:6], 16)), 1.0)


def _strip_at_blocks(css):
    """Return (top_level_css, [inner css of @media/@supports blocks]).

    An @media body holds ordinary rules and SAIRN's apps put their whole mobile
    layout there, so skipping it would skip the mobile palette entirely.
    """
    inner, out, i, n = [], [], 0, len(css)
    while i < n:
        at = css.find("@", i)
        if at < 0:
            out.append(css[i:])
            break
        brace = css.find("{", at)
        semi = css.find(";", at)
        if brace < 0 or (0 <= semi < brace):          # @import/@charset: no block
            out.append(css[i:(semi + 1) if semi >= 0 else n])
            i = (semi + 1) if semi >= 0 else n
            continue
        out.append(css[i:at])
        depth, j = 0, brace
        while j < n:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        inner.append(css[brace + 1:j])
        i = j + 1
    return "".join(out), inner


def _rules(css):
    """[(selector, {prop: value})] for one flat level of CSS."""
    out = []
    for chunk in css.split("}"):
        if "{" not in chunk:
            continue
        sel, _, body = chunk.partition("{")
        decls = {}
        for d in body.split(";"):
            if ":" not in d:
                continue
            p, _, v = d.partition(":")
            decls[p.strip().lower()] = v.strip()
        if decls:
            out.append((sel.strip(), decls))
    return out


def parse_css(text):
    """Pull every CSS rule out of an HTML file, @media bodies included."""
    css = "".join(_STYLE.findall(text))
    css = _COMMENT.sub(" ", css)
    top, inner = _strip_at_blocks(css)
    rules = _rules(top)
    for blk in inner:
        rules.extend(_rules(blk))
    return rules


# ── INLINE style="" ATTRIBUTES ARE WHERE THE b28 DEFECT ACTUALLY LIVED ──────
# The first draft of this mode read <style> blocks only, ran against the exact
# bytes b29 repaired, and reported five real contrast failures and NOT the
# undefined var(--accent) -- because that one sat in a style attribute on a
# div. A gate that misses the defect it was built from is worth nothing, and
# only running it against the known-bad bytes said so.
_INLINE = re.compile(r"""<([a-zA-Z][\w-]*)([^>]*?)\sstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.S)
_ID_ATTR = re.compile(r"""\sid\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def parse_inline(text):
    """[(label, {prop: value})] for every element carrying a style attribute."""
    out = []
    body = _HTML_COMMENT.sub(" ", text)          # a commented-out tag is not markup
    for m in _INLINE.finditer(body):
        tag, before, dq, sq = m.group(1), m.group(2) or "", m.group(3), m.group(4)
        decl_text = dq if dq is not None else (sq or "")
        idm = _ID_ATTR.search(before)
        ident = (idm.group(1) or idm.group(2)) if idm else ""
        decls = {}
        for d in decl_text.split(";"):
            if ":" not in d:
                continue
            p, _, v = d.partition(":")
            decls[p.strip().lower()] = v.strip()
        if decls:
            out.append(("inline <%s%s>" % (tag, ("#" + ident) if ident else ""), decls))
    return out


def token_map(rules):
    """Every custom property DEFINED anywhere in the file, last definition wins."""
    tokens = {}
    for _sel, decls in rules:
        for p, v in decls.items():
            if p.startswith("--"):
                tokens[p] = v
    return tokens


def resolve(value, tokens, _depth=0):
    """value -> ((r,g,b,a), None) | (None, reason).

    `reason` is one of: 'undefined-var:<name>' (the F3 class -- the declaration
    is DROPPED, not fallen back), or 'unresolvable' for anything this mode
    deliberately will not guess at (gradients, currentcolor, inherit, a named
    colour outside the small set above).
    """
    if value is None:
        return None, "unresolvable"
    v = value.strip().rstrip("!important").strip()
    if _depth > 8:
        return None, "unresolvable"
    m = _VAR.search(v)
    if m:
        name, fallback = m.group(1), m.group(2)
        if name in tokens:
            return resolve(_VAR.sub(tokens[name], v, count=1), tokens, _depth + 1)
        if fallback is not None and fallback.strip():
            return resolve(_VAR.sub(fallback.strip(), v, count=1), tokens, _depth + 1)
        # NO definition and NO fallback. This is not "we could not tell" --
        # the browser drops the whole declaration at computed-value time.
        return None, "undefined-var:" + name
    low = v.lower()
    if low in _NAMED:
        c = _NAMED[low]
        return (c, None) if c[3] > 0 else (None, "unresolvable")
    if low.startswith("#"):
        c = _hex_to_rgba(low)
        return (c, None) if c else (None, "unresolvable")
    if low.startswith("rgb"):
        c = _parse_rgb(low)
        return (c, None) if c else (None, "unresolvable")
    return None, "unresolvable"


_SIZE = re.compile(r"([0-9.]+)\s*px")


def _rule_threshold(decls):
    """AA threshold for a rule, from its OWN font declarations.

    A rule that does not state a size is treated as normal text (4.5) rather
    than as large: assuming the generous threshold is how a real failure gets
    waved through, and the conservative direction is the one that fails loud.
    """
    px = 16.0
    m = _SIZE.search(decls.get("font-size", "") or "")
    if m:
        try:
            px = float(m.group(1))
        except ValueError:
            px = 16.0
    w = (decls.get("font-weight", "") or "").strip().lower()
    bold = w in ("bold", "bolder") or (w[:3].isdigit() and int(w[:3]) >= 700)
    return required_ratio(px, bold), px, bold


def static_findings(text, label="<file>"):
    """The two static classes. Returns (findings, unresolved, stats)."""
    rules = parse_css(text)
    tokens = token_map(rules)
    inline = parse_inline(text)
    findings, unresolved = [], []
    pairs_checked = 0

    for sel, decls in rules + inline:
        # ── B: an undefined custom property anywhere in the rule ───────────
        for prop, val in decls.items():
            if prop.startswith("--"):
                continue
            for m in _VAR.finditer(val or ""):
                name, fallback = m.group(1), m.group(2)
                if name in tokens:
                    continue
                if fallback is not None and fallback.strip():
                    continue
                findings.append({
                    "kind": "undefined-var", "file": label, "selector": sel[:80],
                    "property": prop, "token": name, "value": (val or "")[:80],
                    "why": ("var(%s) is defined nowhere in this file and has no "
                            "fallback, so the whole `%s` declaration is invalid "
                            "at computed-value time and is DROPPED -- not "
                            "fallen back." % (name, prop))})

        # ── A: a self-contained opaque pair ────────────────────────────────
        if "color" not in decls:
            continue
        bg_raw = decls.get("background-color", decls.get("background"))
        fg, fg_why = resolve(decls.get("color"), tokens)
        if bg_raw is None:
            unresolved.append({"file": label, "selector": sel[:80],
                               "why": "colour declared with no background on the same rule"})
            continue
        bg, bg_why = resolve(bg_raw, tokens)
        if fg is None or bg is None:
            unresolved.append({"file": label, "selector": sel[:80],
                               "why": fg_why or bg_why or "unresolvable"})
            continue
        if fg[3] < 0.999 or bg[3] < 0.999:
            unresolved.append({"file": label, "selector": sel[:80],
                               "why": "translucent -- the real surface is a composite "
                                      "and this mode will not guess the ancestor"})
            continue
        need, px, bold = _rule_threshold(decls)
        ratio = contrast(fg, bg)
        pairs_checked += 1
        if ratio + 0.005 < need:
            findings.append({
                "kind": "aa-contrast", "file": label, "selector": sel[:80],
                "ratio": round(ratio, 2), "need": need, "px": px, "bold": bold,
                "fg": decls.get("color"), "bg": bg_raw,
                "why": "self-contained opaque pair below WCAG 2.2 AA"})
    return findings, unresolved, {"rules": len(rules), "tokens": len(tokens),
                                  "inline": len(inline),
                                  "pairs_checked": pairs_checked}


# ── THE BASELINE, AND WHY A RATCHET RATHER THAN A CLIFF ────────────────────
# Measured 2026-10-19 before this gate was wired: 153 findings across 14 of the
# 17 products -- 87 AA failures and 66 undefined custom properties -- because
# "white text on the app's brand colour" is the HOUSE PATTERN and every app's
# .gbtn/.bp carries it. A gate that denied on any finding in a changed file
# would have blocked every push touching fourteen apps on the day it landed,
# and a gate everyone must override on day one is one nobody obeys on day two
# -- 80 of the 94 rows in docs/BYPASS-LOG.jsonl are already that shape.
#
# So it is a RATCHET: existing findings are recorded in
# docs/wcag-contrast-baseline.json and a push is denied only for findings that
# are NOT in it. The debt does not become invisible -- every run prints how
# much is outstanding per file, and growing the baseline takes an explicit
# `--baseline-write`, which is a visible commit somebody can refuse.
BASELINE = REPO / "docs" / "wcag-contrast-baseline.json"


def finding_key(f):
    """Stable identity for a finding, across edits that do not touch it.

    Deliberately NOT the line number: the apps are single files that get
    thousands of lines inserted above a rule, and a line-keyed baseline would
    go stale on the first unrelated edit and read as a wall of new findings.
    """
    if f["kind"] == "undefined-var":
        return "%s|undefined-var|%s|%s|%s" % (f["file"], f["selector"], f["property"], f["token"])
    return "%s|aa-contrast|%s|%s|%s" % (f["file"], f["selector"], f["fg"], f["bg"])


def load_baseline():
    """-> (counts dict, None) | (None, reason). FAILS CLOSED on a bad file."""
    if not BASELINE.is_file():
        return {}, None
    try:
        d = json.loads(BASELINE.read_text(encoding="utf-8"))
    except Exception as e:
        return None, "%s is unreadable (%s) -- a baseline that cannot be " \
                     "parsed is not an empty one" % (BASELINE.name, type(e).__name__)
    c = d.get("counts")
    if not isinstance(c, dict):
        return None, "%s has no `counts` object" % BASELINE.name
    return c, None


def split_against_baseline(findings, counts):
    """-> (new, accepted). Counted per key, so a SECOND copy of an accepted
    finding is still NEW -- adding another failing button is a regression even
    where one already sat."""
    seen, new, accepted = {}, [], []
    for f in findings:
        k = finding_key(f)
        seen[k] = seen.get(k, 0) + 1
        (accepted if seen[k] <= counts.get(k, 0) else new).append(f)
    return new, accepted


def static_run(paths, show_unresolved=False, json_out=None,
               use_baseline=False, write_baseline=False):
    all_f, all_u, rows = [], [], []
    for p in paths:
        fp = pathlib.Path(p)
        if not fp.is_absolute():
            fp = REPO / p
        if not fp.is_file():
            print("COULD NOT RUN: %s is not a file" % p)
            return 2
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print("COULD NOT RUN: %s could not be read -- %s" % (p, type(e).__name__))
            return 2
        f, u, st = static_findings(text, fp.name)
        if not st["rules"]:
            print("COULD NOT RUN: no CSS rules parsed out of %s -- a file this "
                  "mode cannot read is not a clean one" % fp.name)
            return 2
        all_f.extend(f)
        all_u.extend(u)
        rows.append((fp.name, st, len(f), len(u)))

    if write_baseline:
        counts = {}
        for f in all_f:
            k = finding_key(f)
            counts[k] = counts.get(k, 0) + 1
        BASELINE.write_text(json.dumps({
            "_what_this_is":
                "Contrast and undefined-token findings that EXISTED when "
                "tools/wcag_contrast_check.py was wired into the push gate on "
                "2026-10-19. The gate denies on findings NOT in here. This is "
                "a ratchet and a debt list, not an exemption: every gate run "
                "prints what is still outstanding, and this file only grows by "
                "an explicit --baseline-write, which is a commit somebody can "
                "refuse to approve.",
            # WHO WROTE IT, DERIVED. These two fields were the literals
            # "2026-10-19" and "fourth b30" until 2026-10-19 (b22), so EVERY
            # re-record claimed fourth's b30 authorship whoever ran it and
            # whenever -- a provenance line that cannot change is a provenance
            # line that is wrong the second time. Caught by re-recording it.
            "written": _today(), "written_by": _who(),
            "files_scanned": sorted(r[0] for r in rows),
            "regenerate": "python tools/wcag_contrast_check.py --static --all "
                          "--baseline-write",
            "total": len(all_f), "counts": counts}, indent=1, sort_keys=True),
            encoding="utf-8", newline="\n")
        print("wrote %s with %d finding(s) accepted as existing debt"
              % (BASELINE.name, len(all_f)))
        return 0

    accepted = []
    if use_baseline:
        counts, why = load_baseline()
        if counts is None:
            print("COULD NOT RUN: %s" % why)
            return 2
        all_f, accepted = split_against_baseline(all_f, counts)

    print("STATIC CONTRAST + TOKEN CHECK -- %d file(s)" % len(rows))
    for name, st, nf, nu in rows:
        print("  %-22s %4d rules  %4d inline  %3d tokens  %3d opaque pair(s) "
              "checked  %2d finding(s)  %3d unresolved"
              % (name, st["rules"], st["inline"], st["tokens"],
                 st["pairs_checked"], nf, nu))
    if use_baseline:
        per = {}
        for f in accepted:
            per[f["file"]] = per.get(f["file"], 0) + 1
        print("  BASELINE DEBT STILL OUTSTANDING: %d finding(s)%s"
              % (len(accepted),
                 ("  -- " + ", ".join("%s %d" % (k, v) for k, v in sorted(per.items())))
                 if per else ""))
    for f in sorted(all_f, key=lambda x: (x["kind"], x.get("ratio", 0))):
        if f["kind"] == "aa-contrast":
            print("  FAIL %-20s %-34s %.2f:1 (need %.1f)  %s on %s"
                  % (f["file"], f["selector"][:34], f["ratio"], f["need"], f["fg"], f["bg"]))
        else:
            print("  FAIL %-20s %-34s undefined var(%s) in `%s`"
                  % (f["file"], f["selector"][:34], f["token"], f["property"]))
    if show_unresolved:
        for u in all_u:
            print("  unresolved %-18s %-34s %s" % (u["file"], u["selector"][:34], u["why"]))
    print("%s: %d   UNRESOLVED (neither pass nor fail): %d"
          % ("NEW FINDINGS (not in the baseline)" if use_baseline else "FINDINGS",
             len(all_f), len(all_u)))
    if json_out:
        pathlib.Path(json_out).write_text(
            json.dumps({"findings": all_f, "unresolved": all_u,
                        "files": [{"file": n, **s} for n, s, _a, _b in rows]}, indent=1),
            encoding="utf-8")
        print("wrote %s" % json_out)
    return 1 if all_f else 0


def _today():
    """The calendar date, LOCAL rather than UTC -- tools/sairn_stale_snapshot
    _scan.py exists because UTC derivation dates an evening's work tomorrow."""
    import time
    return time.strftime("%Y-%m-%d")


def _who():
    """Who re-recorded the baseline, from the clone's own identity marker.
    'unknown' rather than a guess: a wrong name is worse than no name."""
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).parent))
    try:
        import sairn_session_identity as _sid
        return _sid.session_name()
    except Exception:                                            # noqa: BLE001
        return "unknown (this clone has no session-identity marker)"


def is_product_stem(stem):
    """Is this root HTML stem one of this platform's shipped products?

    THE WHOLE STEM, HYPHENS INTACT. Until 2026-10-19 (b22) this read
    `stem.startswith("sairn") and "-" not in stem`, and the hyphen clause is
    the defect: it did not narrow the list to products, it silently removed
    the five SUB-APPS -- sairndental-book, sairndental-complaint,
    stonedesk-catalog, stonedesk-hr, stonedesk-intake.

    WHY THAT WAS NOT A COSMETIC MISCOUNT. docs/wcag-contrast-baseline.json is
    generated from THIS list and the push gate runs on EVERY changed `.html`.
    So the baseline's universe was narrower than the gate's, and the two
    sub-apps carrying debt -- sairndental-book 6 findings,
    sairndental-complaint 2 -- denied any push that touched them, on
    PRE-EXISTING debt, with no route but a skip. Measured in b21.

    A PREFIX RULE RATHER THAN A LIST, deliberately: a future `sairnfoo-bar`
    sub-app is included the day it is added rather than the day somebody
    remembers. A root HTML that is NOT a product (an index page, a scratch
    file) still does not match, because it does not carry either prefix.
    """
    return stem == "stonedesk" or stem.startswith("stonedesk-") \
        or stem.startswith("sairn")


def product_files():
    """The root products, DERIVED rather than listed (b29 corrected 18 -> 17;
    b22 corrected 17 -> every root product INCLUDING the five sub-apps)."""
    import subprocess
    r = subprocess.run(["git", "ls-files", "*.html"], capture_output=True,
                       text=True, cwd=str(REPO))
    if r.returncode != 0:
        return None
    out = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if "/" in line:
            continue
        if is_product_stem(line[:-5]):
            out.append(line)
    return sorted(out)


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

    # ── 7. THE STATIC HALF (b30), in both directions ──────────────────────
    # The SUBJECT of each fixture is the real defect b29 found, so a rewrite
    # that stops catching it fails here rather than on a future app.
    def one(css, **kw):
        f, u, st = static_findings("<style>%s</style>" % css, "fixture")
        return f, u, st

    f, u, _ = one(":root{--p:#0EA5E9}\n.bp{background:var(--p);color:#fff;}")
    ok("b29's primary button IS caught statically", len(f), 1)
    ok("...and at the ratio the browser measured", f[0]["ratio"] if f else 0, 2.77)
    f, _u, _ = one(":root{--pd:#0369A1}\n.bp{background:var(--pd);color:#fff;}")
    ok("...and the SHIPPED fix passes", len(f), 0)

    f, _u, _ = one(":root{--pd:#0284C7;--pt:#E0F2FE}\n"
                   ".sb.on{background:var(--pt);color:var(--pd);font-weight:700;font-size:13px;}")
    ok("b29's active sidebar row IS caught", len(f), 1)
    ok("...at 13px BOLD it still needs 4.5, not 3.0", f[0]["need"] if f else 0, 4.5)

    f, _u, _ = one(".banner{border-left:3px solid var(--accent);color:#000;background:#fff;}")
    ok("b28's undefined var(--accent) IS caught", len([x for x in f if x["kind"] == "undefined-var"]), 1)
    # AND IN AN INLINE ATTRIBUTE, which is where b28's really was. The first
    # draft read <style> blocks only and missed it on the real bytes.
    fi, _u, sti = static_findings(
        '<style>:root{--p:#0EA5E9}</style>'
        '<div id="pc-edit-banner" style="border-left:3px solid var(--accent)"></div>',
        "fixture")
    ok("an undefined token in a style ATTRIBUTE is caught",
       [x["kind"] for x in fi], ["undefined-var"])
    ok("...and the element is named, not just the file",
       fi[0]["selector"] if fi else "", "inline <div#pc-edit-banner>")
    ok("...and the inline rule was really parsed", sti["inline"], 1)
    fi, _u, _ = static_findings(
        '<style>:root{--p:#0EA5E9}</style>'
        '<!-- <div style="color:var(--gone)"></div> -->', "fixture")
    ok("...but a COMMENTED-OUT tag is not markup", len(fi), 0)
    fi, _u, _ = static_findings(
        '<style>:root{--p:#0EA5E9}</style>'
        '<span style="background:var(--p);color:#fff;font-size:12px">x</span>', "fixture")
    ok("an inline opaque pair below AA is caught too",
       (len(fi), fi[0]["ratio"] if fi else 0), (1, 2.77))

    f, _u, _ = one(":root{--accent:#0EA5E9}\n.banner{border-left:3px solid var(--accent);}")
    ok("...and a DEFINED token is not a finding", len(f), 0)
    f, _u, _ = one(".banner{border-left:3px solid var(--nope,#0EA5E9);}")
    ok("...and an undefined token WITH a fallback is not a finding", len(f), 0)

    # the direction that would have been wrong: refusing to guess
    f, u, _ = one(".hbadge{background:rgba(255,255,255,.15);color:#fff;}")
    ok("a TRANSLUCENT surface is UNRESOLVED, not a fabricated 1.00", (len(f), len(u)), (0, 1))
    f, u, _ = one(".kt{color:#22C55E;}")
    ok("a colour with no background on the rule is UNRESOLVED", (len(f), len(u)), (0, 1))
    f, u, _ = one(".x{background:linear-gradient(#fff,#000);color:#fff;}")
    ok("a gradient surface is UNRESOLVED", (len(f), len(u)), (0, 1))

    # large-text thresholds applied from the rule's own declarations
    # #8E8E8E under white is 3.28:1 -- ABOVE the 3.0 large-text bar and BELOW
    # the 4.5 normal-text one, so it is the only pair that can tell the two
    # thresholds apart. #767676 (4.54:1) cannot, and the first draft of this
    # fixture used it and asserted a failure that should never have happened.
    f, _u, _ = one(".big{background:#8E8E8E;color:#fff;font-size:30px;}")
    ok("30px at 3.28:1 clears the LARGE threshold", len(f), 0)
    f, _u, _ = one(".small{background:#8E8E8E;color:#fff;font-size:13px;}")
    ok("...the same colours at 13px do NOT", len(f), 1)

    # the parser itself
    rs = parse_css("<style>@media (max-width:900px){.a{color:#fff;background:#000}}</style>")
    ok("a rule inside @media is parsed, not skipped", len(rs), 1)
    rs = parse_css("<style>/* .ghost{color:#fff;background:#fff} */ .real{color:#000}</style>")
    ok("a commented-out rule is NOT parsed", [s for s, _d in rs], [".real"])
    f, _u, st = one(":root{--a:var(--b);--b:#000}\n.x{color:var(--a);background:#fff;}")
    ok("a token defined THROUGH another token resolves", (len(f), st["pairs_checked"]), (0, 1))
    f, _u, st = one(":root{--a:var(--b);--b:#fff}\n.x{color:var(--a);background:#fff;}")
    ok("...and the chain is really followed, not just tolerated: white on "
       "white through two hops FAILS", (len(f), f[0]["ratio"] if f else 0), (1, 1.0))

    # ── THE PRODUCT LIST (b22). THE DEFECT THESE LOCK, IN BOTH DIRECTIONS ──
    # The old rule was `startswith("sairn") and "-" not in stem`. It did not
    # narrow the list to products; it removed the five SUB-APPS, so the
    # baseline this list generates could not see files the gate judges.
    for stem in ("sairndental-book", "sairndental-complaint",
                 "stonedesk-catalog", "stonedesk-hr", "stonedesk-intake"):
        ok("A HYPHENATED SUB-APP IS A PRODUCT: %s -- the b21 finding, and the "
           "two dental ones carried 8 findings the gate denied on while the "
           "baseline could not see them" % stem, is_product_stem(stem), True)
    for stem in ("stonedesk", "sairndental", "sairnroofing", "sairnbiz"):
        ok("...and an UNHYPHENATED root product is still one: %s" % stem,
           is_product_stem(stem), True)
    ok("ABLATION: the OLD rule would have refused sairndental-book, which is "
       "the one arm that fails on the pre-fix code and passes on this one",
       ("sairndental-book".startswith("sairn")
        and "-" not in "sairndental-book"), False)
    for stem in ("index", "test", "scratch", "readme", "404"):
        ok("a root HTML that is NOT a product still does not match: %s"
           % stem, is_product_stem(stem), False)
    ok("the prefix rule admits a sub-app that does not exist yet, so a future "
       "one is covered the day it is added rather than the day somebody "
       "remembers", is_product_stem("sairnfoo-bar"), True)
    ok("...and `stonedeskish` is NOT admitted by the stonedesk arm -- the "
       "prefix is `stonedesk-`, so a near-name does not slip in through it",
       ("stonedeskish" == "stonedesk"
        or "stonedeskish".startswith("stonedesk-")), False)

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
    ap.add_argument("--gate", nargs="*", default=None,
                    help="static check over the given files; this is the push-gate mode")
    ap.add_argument("--static", action="store_true",
                    help="static check (use with --all or --gate <files>)")
    ap.add_argument("--all", action="store_true",
                    help="with --static: every root product, derived from git ls-files")
    ap.add_argument("--show-unresolved", action="store_true")
    ap.add_argument("--baseline", action="store_true",
                    help="deny only on findings NOT in docs/wcag-contrast-baseline.json")
    ap.add_argument("--baseline-write", action="store_true",
                    help="record the current findings AS the baseline (a visible commit)")
    ap.add_argument("--app", default=None)
    ap.add_argument("--local", action="store_true",
                    help="serve the working-tree file at the real origin")
    ap.add_argument("--file", default=None, help="with --local, serve these bytes instead")
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if a.gate is not None or a.static:
        # THE LOCK FIRST, here too: a gate running on broken criteria would
        # deny or pass on arithmetic nobody checked.
        if selftest():
            print("COULD NOT RUN: the fixtures do not classify, so this gate "
                  "decides nothing.")
            return 2
        print("")
        paths = list(a.gate or [])
        if a.all:
            prods = product_files()
            if prods is None:
                print("COULD NOT RUN: `git ls-files` failed, so the product "
                      "list could not be DERIVED and this mode will not fall "
                      "back to a hardcoded one.")
                return 2
            paths.extend(prods)
        if not paths:
            print("COULD NOT RUN: --gate/--static needs file paths, or --all.")
            return 2
        return static_run(paths, a.show_unresolved, a.json_out,
                          use_baseline=a.baseline, write_baseline=a.baseline_write)

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
