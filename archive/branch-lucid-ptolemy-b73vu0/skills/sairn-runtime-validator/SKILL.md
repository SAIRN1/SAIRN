---
name: sairn-runtime-validator
description: >
  The SAIRN Runtime Validator catches bugs that only appear at runtime — not in static
  code scans. Trigger on: every app build before push, every nav/login complaint, any
  "nothing works", "can't click", "page won't load", "blank screen", "sidebar broken",
  "button does nothing", or any report of broken UI after login. This skill specifically
  catches: broken querySelector selectors, CSS display:none blocking the app shell,
  missing showPage() call after login, nav items wired to non-existent page divs,
  conflicting function definitions where a later override breaks an earlier one, app
  div visibility not confirmed post-login, and any JavaScript that generates invalid
  CSS attribute selectors. This is the skill that would have caught the SAIRNcode
  sidebar bug — querySelector generating showPage(''id'') with broken quote escaping
  that silently failed on every single nav click. Never ship without running this.
  Works in conjunction with sairn-ultra-scan and sairn-code-guardian. All three run
  together on every push.
---

# SAIRN Runtime Validator

> *"Static scans catch what's written wrong. Runtime validation catches what fails silently."*

The Guardian and Ultra Scan catch syntax errors, color violations, and proxy rule
violations. The Runtime Validator catches what they miss: bugs that only appear when
a user actually interacts with the app — clicking nav, logging in, rendering pages.

---

## The Three Failures This Skill Was Built To Catch

### FAILURE 1 — The SAIRNcode Sidebar Bug (June 2026)

**What happened:** All 11 SAIRN apps were pushed with broken nav. Every sidebar click
did nothing. The login worked. The dashboard appeared. But clicking any nav item —
Coding Queue, Encounters, Claims, anything — produced zero response.

**Root cause — THREE simultaneous bugs:**

```
BUG A: Broken querySelector in showPage()
  WRONG:  querySelector('[onclick="showPage(\''+id+'\')"]')
  → generates: [onclick="showPage(''encounters'')"]  ← double quotes break the selector
  → returns null every time → no nav item ever gets .active class
  → function silently succeeds but does nothing visible

BUG B: #app{display:none} in CSS not overridden after login
  → login override calls el.style.display='block'
  → but CSS specificity of #app{display:none} in <style> tag wins
  → app shell appears visible but child .page elements stay hidden

BUG C: showPage() never called after login
  → login handler hides login screen, shows app div
  → but never calls showPage('dashboard')
  → all .page{display:none} elements stay hidden
  → user sees the topbar and sidebar but a blank white content area
```

**What the existing skills missed:**
- Guardian scanned for syntax errors — querySelector is valid JS syntax, just wrong logic
- Ultra Scan checked element IDs exist — it did, but querySelector never found them
- Neither skill simulated a click or verified the selector would actually match

---

## Runtime Validator — 12 Checks

Run these on every app before push. All 12 must pass.

---

### CHECK R1 — querySelector Selector Validity

Every `querySelector` call that builds a selector from a variable must produce
a valid CSS attribute selector. The most common failure: quote escaping in
attribute value selectors.

```python
def check_querySelector_validity(content):
    import re
    findings = []

    # Find all querySelector calls that build selectors dynamically
    qs_calls = re.findall(
        r"querySelector\(['\"`]([^'\"`]*)['\"`]\s*\+.*?\+\s*['\"`]([^'\"`]*)['\"`]\)",
        content
    )

    # Also find the specific broken pattern from the SAIRNcode bug
    # Pattern: querySelector('[onclick="showPage(\''+id+'\')" ]')
    broken_patterns = [
        r"""querySelector\(\s*['"`]\[onclick=['""]showPage\(\\?['""]\s*['"`]\s*\+""",
        r"""querySelector\(\s*['"`]\[onclick.*showPage.*['"`]\s*\+\s*id\s*\+""",
    ]
    for pat in broken_patterns:
        if re.search(pat, content):
            findings.append(
                "CRITICAL: querySelector builds nav selector with broken quote escaping — "
                "will NEVER match any element. "
                "Use: el.getAttribute('onclick').includes(id) instead"
            )

    # Check for the double-quote wrapping issue
    # Wrong:  '[onclick="showPage(\\''+id+'\\')"]'
    # Right:  '#nav-' + id  OR scan oncl attrs
    if "querySelector('[onclick" in content and "showPage" in content:
        # Verify it's using a safe pattern
        safe_patterns = [
            "querySelector('#nav-'",
            "querySelectorAll('.ni'",
            ".getAttribute('onclick')",
            "getAttribute(\"onclick\")",
        ]
        has_safe = any(p in content for p in safe_patterns)
        if not has_safe:
            findings.append(
                "HIGH: querySelector used to find nav by onclick attr — "
                "quote escaping is fragile. Use #nav-{id} IDs or scan .getAttribute()"
            )

    return findings
```

**Auto-fix:**
Replace broken querySelector nav pattern with ID-based lookup:
```javascript
// WRONG — breaks with any quote escaping
const navEl = document.querySelector('[onclick="showPage(\''+id+'\')"]');

// RIGHT — use the nav ID set on each .ni element
const navEl = document.getElementById('nav-' + id) ||
  Array.from(document.querySelectorAll('.ni')).find(el =>
    (el.getAttribute('onclick') || '').includes(id)
  );
```

---

### CHECK R2 — App Shell CSS Visibility After Login

The `#app` or equivalent app shell div must not have `display:none` in CSS
unless there is a guaranteed JavaScript override that uses `!important` or
removes the inline style.

```python
def check_app_shell_visibility(content):
    import re
    findings = []

    # Find app shell ID
    app_ids = re.findall(r'id=["\'](\w*app\w*|\w*shell\w*)["\']', content)

    for app_id in set(app_ids):
        # Check if CSS hides it
        css_hidden = re.search(
            rf'#{re.escape(app_id)}\s*\{{[^}}]*display\s*:\s*none',
            content
        )
        if not css_hidden:
            continue

        # Check if JS override uses !important or style.setProperty
        override_patterns = [
            f"getElementById('{app_id}').*style.*display.*block",
            f"getElementById(\"{app_id}\").*style.*display.*block",
            f"setProperty.*display.*block.*important",
            f"classList.add.*visible",
        ]
        has_strong_override = any(
            re.search(p, content, re.DOTALL) for p in override_patterns
        )
        if not has_strong_override:
            findings.append(
                f"CRITICAL: #{app_id}{{display:none}} in CSS but no !important override in JS. "
                f"App shell will stay hidden after login regardless of JS."
            )
        else:
            # Verify it's using !important
            if 'important' not in content[content.find(app_id):content.find(app_id)+500]:
                findings.append(
                    f"HIGH: #{app_id} JS override exists but no !important — "
                    f"CSS specificity may still win. Use style.setProperty('display','block','important')"
                )

    return findings
```

**Auto-fix:**
```javascript
// After login — always use setProperty with !important
var app = document.getElementById('app');
if (app) {
  app.style.setProperty('display', 'block', 'important');
  app.style.setProperty('visibility', 'visible', 'important');
  app.classList.add('visible');
}
```

---

### CHECK R3 — showPage Called After Login

Every SAIRN app must call `showPage('dashboard')` (or equivalent first page)
immediately after successful login. Without this, all `.page{display:none}` elements
stay hidden even though the app shell is visible.

```python
def check_showpage_after_login(content):
    import re
    findings = []

    # Find login success handler
    login_fns = ['doLogin', 'handleLogin', 'sairnLogin']
    for fn in login_fns:
        fn_match = re.search(rf'function\s+{fn}\s*\(', content)
        if not fn_match:
            continue

        # Get function body (next 2000 chars)
        fn_start = fn_match.start()
        fn_body  = content[fn_start:fn_start+3000]

        # Check if showPage is called in or after login
        has_showpage = 'showPage(' in fn_body
        has_nav      = 'nav(' in fn_body  # sairnbiz uses nav()

        if not has_showpage and not has_nav:
            # Check if it's called via setTimeout or post-login callback
            post_login = content[fn_start+3000:fn_start+5000]
            if 'showPage' not in post_login:
                findings.append(
                    f"CRITICAL: {fn}() does not call showPage() after login. "
                    f"Dashboard will be blank — all .page{{display:none}} stay hidden. "
                    f"Add: setTimeout(()=>showPage('dashboard'), 50) at end of login success."
                )

    return findings
```

---

### CHECK R4 — Nav ID to Page ID Mapping

Every `<div class="ni" onclick="showPage('X')">` must have a corresponding
`<div class="page" id="page-X">`. Every nav click that hits a missing page
silently does nothing — the user clicks and nothing happens.

```python
def check_nav_page_mapping(content):
    import re
    findings = []

    nav_targets = set(re.findall(r"showPage\(['\"]([^'\"]+)['\"]", content))
    page_ids    = set(re.findall(r'id=["\']page-([^"\']+)["\']', content))

    # Exclude template literals and known dynamic targets
    skip = {'${pageId}', '${id}', 'dashboard'}
    real_missing = {p for p in nav_targets - page_ids if '${' not in p and p not in skip}

    if real_missing:
        findings.append(
            f"CRITICAL: Nav items point to non-existent pages: {sorted(real_missing)}. "
            f"Every click on these nav items will silently do nothing. "
            f"Either add the page div or remove the nav item."
        )

    # Also check reverse — orphaned pages with no nav link
    orphaned = page_ids - nav_targets - {'sairnbiz-connector', 'doc-scan'}
    if orphaned:
        findings.append(
            f"LOW: Pages exist with no nav link: {sorted(orphaned)}. "
            f"Users cannot reach these pages from the sidebar."
        )

    return findings
```

---

### CHECK R5 — Page CSS Active State Reachable

The `.page` CSS must follow the exact pattern:
```css
.page { display: none; }
.page.active { display: block; }
```
If `.page.active` is missing or overridden by higher-specificity rules, `showPage()`
will add the class but nothing will appear.

```python
def check_page_css_active(content):
    import re
    findings = []

    has_page_none   = re.search(r'\.page\s*\{[^}]*display\s*:\s*none', content)
    has_page_active = re.search(r'\.page\.active\s*\{[^}]*display\s*:\s*block', content)

    if has_page_none and not has_page_active:
        findings.append(
            "CRITICAL: .page{display:none} defined but .page.active{display:block} missing. "
            "showPage() will add .active class but pages will stay hidden forever."
        )

    # Check for specificity overrides that could beat .page.active
    overrides = re.findall(
        r'(#\w+\s+\.page|\.page\s*\{[^}]*display\s*:\s*none[^}]*!important)',
        content
    )
    if overrides:
        findings.append(
            f"HIGH: Higher-specificity CSS may override .page.active: {overrides[:2]}. "
            f"Add !important to .page.active{{display:block!important}}"
        )

    return findings
```

---

### CHECK R6 — Nav Item IDs Match

Every nav item should have `id="nav-{pageId}"` matching its `onclick="showPage('{pageId}')"`.
This enables the ID-based querySelector fallback that never breaks.

```python
def check_nav_ids(content):
    import re
    findings = []

    nav_items = re.findall(
        r'<div[^>]*onclick=["\']showPage\([\'"]([^\'"]+)[\'"]\)["\'][^>]*>',
        content
    )
    for page_id in nav_items:
        if f'id="nav-{page_id}"' not in content and f"id='nav-{page_id}'" not in content:
            findings.append(
                f"MEDIUM: Nav item for page '{page_id}' missing id='nav-{page_id}'. "
                f"Add id attribute so querySelector('#nav-{page_id}') can find it reliably."
            )

    return findings
```

---

### CHECK R7 — Login Success Hides Login Screen

After `doLogin()` succeeds, the login screen must be hidden. Specifically:
the element must get `display:none` OR be removed from the DOM.

```python
def check_login_hides_screen(content):
    import re
    findings = []

    login_screen_ids = ['login', 'auth-screen', 'login-screen', 'auth-gate', 'ls']
    for lid in login_screen_ids:
        if f'id="{lid}"' not in content and f"id='{lid}'" not in content:
            continue
        # Check that doLogin or override hides it
        hide_patterns = [
            f"getElementById('{lid}').*display.*none",
            f'getElementById("{lid}").*display.*none',
            f"getElementById('{lid}').style.display='none'",
            f'_hideLogin',
            f'login.*style.*display.*none',
        ]
        hidden = any(re.search(p, content, re.DOTALL) for p in hide_patterns)
        if not hidden:
            findings.append(
                f"HIGH: Login screen #{lid} is never hidden after login. "
                f"Both login and app may be visible simultaneously."
            )

    return findings
```

---

### CHECK R8 — No Conflicting doLogin Definitions

Only ONE `doLogin` function must be in effect at runtime. If multiple exist,
the last one wins — but if the last one is incomplete (e.g. a stub), login breaks.

```python
def check_no_conflicting_login(content):
    import re
    findings = []

    definitions = [(m.start(), m.group()) for m in re.finditer(
        r'(?:window\.doLogin|function doLogin)\s*[=\(]', content
    )]

    if len(definitions) > 2:  # allow 1 original + 1 override
        findings.append(
            f"HIGH: {len(definitions)} doLogin definitions found — only 2 allowed "
            f"(original + SAIRN override). Extra definitions cause unpredictable behavior. "
            f"Remove all but the override."
        )

    # Verify the LAST definition is a real implementation (not a stub)
    if definitions:
        last_start = definitions[-1][0]
        last_body  = content[last_start:last_start+500]
        if 'return' not in last_body and 'display' not in last_body and 'style' not in last_body:
            findings.append(
                "CRITICAL: Last doLogin definition appears to be a stub or empty function. "
                "Login will succeed silently but nothing will happen."
            )

    return findings
```

---

### CHECK R9 — Touch Events on Nav Items

Nav items must be tappable on mobile. If `touch-action: none` is on the sidebar
or parent, nav clicks may not fire on iOS.

```python
def check_touch_nav(content):
    findings = []
    if 'touch-action:none' in content or 'touch-action: none' in content:
        # Make sure it's only on signature canvas, not sidebar
        ta_idx = content.find('touch-action')
        context = content[max(0,ta_idx-100):ta_idx+100]
        if 'sidebar' in context or 'nav' in context.lower():
            findings.append(
                "HIGH: touch-action:none applied near sidebar/nav — "
                "nav clicks may not fire on iOS Safari."
            )
    return findings
```

---

### CHECK R10 — Main Content Area Has Height

If `#main` or the content area has no height or `overflow:hidden`, pages may
render but be invisible (zero-height container).

```python
def check_main_height(content):
    import re
    findings = []
    main_css = re.search(r'\.main\s*\{([^}]+)\}|#main\s*\{([^}]+)\}', content)
    if main_css:
        css_body = main_css.group(1) or main_css.group(2) or ''
        if 'height' not in css_body and 'min-height' not in css_body:
            findings.append(
                "MEDIUM: .main content area has no height defined. "
                "Pages may render in a zero-height div. Add: height:calc(100vh - 64px) or min-height."
            )
        if 'overflow:hidden' in css_body.replace(' ','') or 'overflow: hidden' in css_body:
            findings.append(
                "HIGH: .main has overflow:hidden — page content will be clipped silently."
            )
    return findings
```

---

### CHECK R11 — Sidebar Visible After Login

The sidebar must be inside `#app` (or shown/hidden with it). If it's outside
the app div, it stays hidden when login is shown and may not appear after login.

```python
def check_sidebar_in_app(content):
    findings = []
    app_start  = content.find('id="app"')
    side_start = content.find('class="sidebar"')
    if app_start < 0 or side_start < 0:
        return findings
    if side_start < app_start:
        findings.append(
            "HIGH: Sidebar div appears BEFORE #app in the HTML. "
            "It will not be affected by app show/hide logic after login. "
            "Move sidebar inside #app."
        )
    return findings
```

---

### CHECK R12 — Post-Login showPage Timing

`showPage()` called synchronously immediately after setting `display:block` may
fire before the browser repaints. Add a `setTimeout(..., 50-100ms)` buffer.

```python
def check_showpage_timing(content):
    import re
    findings = []
    # Find showPage calls that immediately follow display = 'block' without timeout
    pattern = r"style\.display\s*=\s*['\"]block['\"].*?showPage\("
    if re.search(pattern, content, re.DOTALL):
        # Check if there's a setTimeout wrapper
        ctx = re.search(pattern, content, re.DOTALL)
        if ctx:
            window = content[ctx.start():ctx.start()+200]
            if 'setTimeout' not in window:
                findings.append(
                    "LOW: showPage() called synchronously after display=block. "
                    "Browser may not repaint before page switch. "
                    "Wrap in setTimeout(()=>showPage('dashboard'), 50)"
                )
    return findings
```

---

## Complete Scan Function

```python
def run_runtime_validator(app_id, content):
    all_findings = []
    checks = [
        check_querySelector_validity,
        check_app_shell_visibility,
        check_showpage_after_login,
        check_nav_page_mapping,
        check_page_css_active,
        check_nav_ids,
        check_login_hides_screen,
        check_no_conflicting_login,
        check_touch_nav,
        check_main_height,
        check_sidebar_in_app,
        check_showpage_timing,
    ]
    for check in checks:
        findings = check(content)
        if findings:
            all_findings.extend(findings)

    crits  = sum(1 for f in all_findings if 'CRITICAL' in f)
    highs  = sum(1 for f in all_findings if f.startswith('HIGH'))
    score  = max(0, 100 - crits*25 - highs*10)

    return {
        'score':    score,
        'findings': all_findings,
        'crits':    crits,
        'highs':    highs,
        'pass':     crits == 0 and highs == 0,
    }
```

---

## When This Runs

This runs as **Layer 3** after the existing Guardian and Ultra Scan:

```
Layer 1 — sairn-code-guardian     (syntax, proxy, color, unicode)
Layer 2 — sairn-ultra-scan        (27-check feature completeness)
Layer 3 — sairn-runtime-validator (THIS SKILL — runtime behavior)
```

All three must pass before any app ships. Never skip Layer 3.
A 100/100 from Layers 1 and 2 means nothing if Layer 3 catches a broken nav.

---

## The Rule This Skill Enforces

**Code that looks correct in a static scan can fail completely at runtime.**

The SAIRNcode sidebar bug was invisible to every existing check:
- Valid JavaScript syntax ✓
- Correct element IDs ✓
- Proxy rules followed ✓
- Color law obeyed ✓
- All 27 ultra-scan checks passed ✓

And yet: clicking any sidebar item did absolutely nothing.

This skill exists because that can never happen again.

*SAIRN Runtime Validator: Ship nothing that silently fails.*
