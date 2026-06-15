---
name: sairn-ultra-scan
description: >
  The most advanced SAIRN platform scan. Goes far beyond the 8-point Guardian check into
  27 categories covering: logic correctness, UX completeness, integration gaps, security
  hardening, cross-app consistency, Claude intelligence wiring, Field Quote flow integrity,
  blueprint AI completeness, bridge connectivity, pattern compliance, mobile readiness,
  print fidelity, and business logic correctness. Trigger on: "advanced scan", "deep scan",
  "ultra scan", "full audit", "find everything wrong", "fix all gaps", "perfection scan",
  "platform audit", "make it perfect", "find all bugs", "complete audit", "scan everything",
  or any request to do a comprehensive quality review of one or all SAIRN apps. Always
  runs the existing 8-point Guardian first, then adds 19 additional advanced checks.
  Auto-fixes every finding it can. Flags everything it cannot. Produces a scored report
  (0-100) per app. Never ships below 92/100. This is the skill that makes SAIRN world-class.
---

# SAIRN Ultra Scan — Advanced Platform Intelligence Auditor

> *"Not just no bugs. Perfect. Every app. Every time."*

The Ultra Scan is the highest-level quality system in the SAIRN platform.
It runs the existing 8-point Guardian plus 19 advanced intelligence checks
across every dimension: code correctness, UX, security, integration, business logic,
mobile, print, AI wiring, cross-app consistency, and performance.

Target score: **95/100 minimum**. Never ship below **92/100**.

---

## Scan Architecture

### Layer 1 — Guardian Foundation (8 checks, existing)
Run the existing sairn-code-guardian 8-point scan first.
These are hard mechanical checks. Any FAIL here blocks everything else.

1. JS String Integrity (no orphaned HTML)
2. Unicode Box Char scan
3. Regex newline safety
4. Proxy compliance (no api.anthropic.com)
5. Print render compliance
6. Bridge sync validator
7. Role gate audit
8. Color compliance

### Layer 2 — Ultra Intelligence (19 additional checks)
Only run after Layer 1 passes. These go deeper into logic, UX, and integration.

---

## Layer 2 — The 19 Ultra Checks

### CHECK 9 — Claude API Wiring Integrity
**What it catches:** Claude calls that exist but have broken, incomplete, or mismatched
system prompts, missing content types, wrong message formats, or no error handling.

```python
def check_claude_wiring(content):
    findings = []
    # Every fetch to proxy must have system prompt
    proxy_calls = [i+1 for i,l in enumerate(content.splitlines())
                   if 'sairn.vercel.app/api/claude' in l]
    for ln in proxy_calls:
        block = '\n'.join(content.splitlines()[max(0,ln-10):ln+20])
        if 'system' not in block:
            findings.append(f"PROXY CALL line {ln}: missing 'system' prompt — Claude has no instructions")
        if 'messages' not in block:
            findings.append(f"PROXY CALL line {ln}: missing 'messages' array")
        if 'try' not in block and 'catch' not in block:
            findings.append(f"PROXY CALL line {ln}: no try/catch — Claude failure will crash the UI")
        if 'loading' not in block.lower() and 'spinner' not in block.lower():
            findings.append(f"PROXY CALL line {ln}: no loading state — user sees frozen UI during API call")
    # Check that Claude responses are displayed to the user
    if proxy_calls and 'content?.[0]?.text' not in content and "content[0].text" not in content:
        findings.append("Claude response extraction pattern missing — responses may never display")
    return findings
```

**Auto-fix:** Add try/catch wrapper, loading state, and response extraction where missing.

---

### CHECK 10 — Field Quote Flow Completeness
**What it catches:** Partial Field Quote implementations — steps that exist but don't
connect, broken trade selection, missing pricing param injection into Claude prompt,
no signature canvas, no deposit step.

```python
FQ_REQUIRED = {
    'Trade selector':         ['sairnSelectTrade', 'fq-chips', 'trade-chip'],
    'Camera capture':         ['capture="environment"', 'sairn-fq-file', 'FileReader'],
    'Claude analysis call':   ['sairnFQAnalyze', 'fqAnalyzeSketch'],
    'Max 3 questions rule':   ['MAXIMUM 3', 'max 3', 'MAX 3', 'maximum 3'],
    'Pricing in system prompt':['JSON.stringify(pricing)', 'JSON.stringify(p)', 'unitPricing'],
    'Quote output display':   ['sairn-fq-quote-out', 'fq-quote-output', 'quoteOut'],
    'Signature canvas':       ['sig-canvas', 'sairn-sig-canvas', 'getContext'],
    'Deposit step':           ['deposit', 'sairn-fq-deposit'],
    'Save/share':             ['sairnSaveQuote', 'saveQuote', 'navigator.share'],
    'Step navigation':        ['sairnFQStep', 'fqGoToStep', 'fq-step'],
}

def check_field_quote(content):
    findings = []
    has_fq = 'Field Quote' in content or 'sairnOpenFQ' in content or 'fqGoToStep' in content
    if not has_fq:
        findings.append("CRITICAL: No Field Quote module found — required in all B2B apps")
        return findings
    for feature, patterns in FQ_REQUIRED.items():
        if not any(p in content for p in patterns):
            findings.append(f"Field Quote INCOMPLETE: '{feature}' missing ({patterns[0]})")
    return findings
```

---

### CHECK 11 — Blueprint AI / SAIRNscan Module
**What it catches:** Missing blueprint AI, broken image-to-base64 conversion,
no trade-specific output, no LiDAR device detection, no PDF mode fallback.

```python
BP_REQUIRED = {
    'Device detection':     ['detectBlueprintMode', 'navigator.xr', 'isSessionSupported'],
    'iOS fallback':         ['isIOS', 'iPad|iPhone', 'photo'],
    'Image to base64':      ['FileReader', 'readAsDataURL', 'split(\',\')[1]', "split(',')[1]"],
    'Trade selection':      ['selectBPTrade', 'bpSelectedTrade', 'trade-chip'],
    'Claude analysis':      ['runBlueprintAnalysis', 'analyzeBlueprint'],
    'Output display':       ['bp-takeoff-output', 'takeoff-output', 'reportCard'],
    'Print/export':         ['window.print', 'exportTakeoff', 'Export CSV'],
}

def check_blueprint_ai(content):
    findings = []
    has_bp = 'Blueprint AI' in content or 'blueprint-ai' in content or 'Takeoff' in content
    if not has_bp:
        findings.append("WARN: No Blueprint AI module found — consider adding per sairnscan skill")
        return findings
    for feature, patterns in BP_REQUIRED.items():
        if not any(p in content for p in patterns):
            findings.append(f"Blueprint AI INCOMPLETE: '{feature}' missing")
    return findings
```

---

### CHECK 12 — SAIRN Suite Connector Completeness
**What it catches:** Suite connector present but missing required apps per the
platform bridge map, broken launch links, no Sync All button, no bridge URL.

```python
SUITE_REQUIRED = {
    'SAIRNbiz always':     ['SAIRNbiz', 'sairnbiz'],
    'Sync All button':     ['Sync All', 'syncAll', 'sairnSyncAll'],
    'Bridge URL':          ['sairn.vercel.app/api/bridge', 'SAIRN_BRIDGE'],
    'Last sync indicator': ['last-sync', 'lastSync', 'Last sync'],
}

APP_SUITE_REQUIRED = {
    'stonedesk':  ['SAIRNdesign', 'SAIRNbuild', 'SAIRNscape'],
    'sairnbuild': ['StoneDesk', 'SAIRNdesign', 'SAIRNscape', 'SAIRNmech'],
    'sairnscape': ['SAIRNbuild', 'SAIRNdesign', 'StoneDesk'],
    'sairndesign':['StoneDesk', 'SAIRNbuild', 'SAIRNscape'],
    'sairnlaw':   ['SAIRNbuild', 'StoneDesk'],
    'sairnbiz':   ['StoneDesk', 'SAIRNbuild', 'SAIRNscape'],
    'sairnmechanical': ['SAIRNbuild', 'SAIRNdesign'],
    'sairncare':  ['SAIRNcode', 'SAIRNmechanical'],
    'sairnvet':   ['SAIRNmechanical', 'SAIRNdesign'],
    'sairnfuneral':['SAIRNdesign', 'SAIRNbuild'],
}

def check_suite_connector(app_id, content):
    findings = []
    for feature, patterns in SUITE_REQUIRED.items():
        if not any(p in content for p in patterns):
            findings.append(f"Suite connector missing: '{feature}'")
    required_apps = APP_SUITE_REQUIRED.get(app_id, [])
    for app in required_apps:
        if app not in content:
            findings.append(f"Suite missing required app: '{app}' — per platform bridge map")
    return findings
```

---

### CHECK 13 — Admin Pricing Panel
**What it catches:** Missing pricing admin, no localStorage save/load,
no default pricing params, Field Quote without pricing injection.

```python
PRICING_REQUIRED = [
    'sairnSavePricing', 'savePricingParams',
    'localStorage.*pricing', 'pricing.*localStorage',
    'materialMarkup', 'profitPercent', 'laborRates',
    'unitPricing',
]

def check_admin_pricing(content):
    findings = []
    import re
    has_pricing = any(re.search(p, content) for p in PRICING_REQUIRED)
    if not has_pricing:
        findings.append("CRITICAL: No Admin Pricing module — Field Quote uses generic rates instead of company rates")
    if 'unitPricing' not in content:
        findings.append("Unit pricing not defined — Field Quote cannot generate trade-specific estimates")
    if 'localStorage' not in content and 'unitPricing' in content:
        findings.append("Pricing defined but not persisted to localStorage — resets on every page load")
    return findings
```

---

### CHECK 14 — Mobile Readiness
**What it catches:** No viewport meta, touch events not handled, fixed widths
breaking on mobile, signature canvas missing touch-action:none, no responsive breakpoints.

```python
MOBILE_REQUIRED = {
    'Viewport meta':       ['viewport', 'width=device-width'],
    'Touch events':        ['touchstart', 'touchmove', 'touchend'],
    'Responsive CSS':      ['@media', 'max-width'],
    'No fixed px widths':  [],  # checked via pattern — no width:NNNpx on main containers
    'Touch-action none':   ['touch-action:none', 'touch-action: none'],
    'Input type numeric':  ['inputmode="numeric"', 'type="number"', 'type="tel"'],
    'Camera capture attr': ['capture="environment"'],
}

def check_mobile(content):
    findings = []
    for feature, patterns in MOBILE_REQUIRED.items():
        if patterns and not any(p in content for p in patterns):
            findings.append(f"Mobile WARN: '{feature}' missing")
    # Check for overly wide fixed containers
    import re
    wide_fixed = re.findall(r'width:\s*([6-9]\d{2}|[1-9]\d{3})px', content)
    if wide_fixed:
        findings.append(f"Mobile WARN: Fixed widths {wide_fixed[:5]} may break on mobile — use max-width or %")
    return findings
```

---

### CHECK 15 — Print Fidelity
**What it catches:** Deep print issues beyond basic print-color-adjust —
missing signature lines on printable documents, missing date fields,
print CSS hiding essential content, no page-break control on long documents.

```python
def check_print_fidelity(content):
    findings = []
    has_print = 'window.print' in content or '@media print' in content
    if not has_print:
        findings.append("No print functionality found — required for all B2B apps")
        return findings
    if 'print-color-adjust' not in content:
        findings.append("Missing print-color-adjust:exact — colors will not print")
    if '-webkit-print-color-adjust' not in content:
        findings.append("Missing -webkit-print-color-adjust:exact — Chrome print broken")
    # Signature lines on printable outputs
    printable_docs = 'quote' in content.lower() or 'report' in content.lower() or 'invoice' in content.lower()
    if printable_docs:
        has_sig_line = any(p in content for p in ['sig-line','signature','Signature:','______'])
        if not has_sig_line:
            findings.append("Printable document missing signature line — required per print-first rule")
    return findings
```

---

### CHECK 16 — Login & Auth Completeness
**What it catches:** Missing role selector, PIN with no validation, no wrong-PIN
feedback, no role-gated navigation hiding, default PIN exposed in production code.

```python
AUTH_REQUIRED = {
    'Role selector':       ['role-btn', 'selectRole', 'data-role'],
    'PIN input':           ['pin-input', 'pinInput', 'type="password"'],
    'PIN validation':      ['doLogin', 'handleLogin', 'pins['],
    'Wrong PIN feedback':  ['login-error', 'loginError', 'Incorrect'],
    'LocalStorage PINs':   ['localStorage.*pin', 'pin.*localStorage', '_pins'],
    'Role gate applied':   ['applyRoleGates', 'roleGate', 'currentRole'],
}

def check_auth(content):
    findings = []
    import re
    for feature, patterns in AUTH_REQUIRED.items():
        found = any(re.search(p, content) for p in patterns)
        if not found:
            findings.append(f"Auth INCOMPLETE: '{feature}' missing")
    # Check default PINs are not hardcoded insecurely
    obvious_pins = ["'1234'", '"1234"', "'0000'", '"0000"']
    exposed = [p for p in obvious_pins if p in content]
    if exposed:
        findings.append(f"WARN: Default PIN {exposed} visible in code — ensure admin changes on first use")
    return findings
```

---

### CHECK 17 — Error Handling Coverage
**What it catches:** Async functions with no try/catch, fetch calls that can crash
the entire UI on network failure, Claude responses not checked for null/undefined.

```python
def check_error_handling(content):
    import re
    findings = []
    # Count async functions vs try/catch blocks
    async_fns  = len(re.findall(r'async\s+function|async\s*\(|=\s*async', content))
    try_blocks = len(re.findall(r'\btry\s*\{', content))
    catch_blocks = len(re.findall(r'\bcatch\s*\(', content))
    fetch_calls = len(re.findall(r'\bfetch\(', content))

    if fetch_calls > 0 and try_blocks == 0:
        findings.append(f"CRITICAL: {fetch_calls} fetch() calls with ZERO try/catch — network errors will crash UI")
    elif fetch_calls > try_blocks * 2:
        findings.append(f"WARN: {fetch_calls} fetch calls but only {try_blocks} try blocks — some calls unprotected")

    # Check Claude response extraction is null-safe
    if 'content?.[0]?.text' not in content and "content[0].text" in content:
        findings.append("Claude response extraction not null-safe — use content?.[0]?.text || ''")

    # Check localStorage is wrapped
    ls_calls = len(re.findall(r'localStorage\.(get|set|remove)', content))
    if ls_calls > 2 and 'try' not in content:
        findings.append(f"WARN: {ls_calls} localStorage calls without try/catch — Safari private mode will throw")

    return findings
```

---

### CHECK 18 — Navigation Completeness
**What it catches:** Sidebar nav items that point to pages that don't exist,
pages that exist but have no nav link, dead onclick handlers.

```python
def check_navigation(content):
    import re
    findings = []
    # Extract showPage calls from nav
    nav_pages  = set(re.findall(r"showPage\(['\"]([^'\"]+)['\"]", content))
    # Extract page IDs
    page_ids   = set(re.findall(r'id=["\']page-([^"\']+)["\']', content))
    # Also check sairnOpenFQ, sairnOpenSuite etc
    for page in nav_pages:
        target_id = 'page-' + page
        if page not in page_ids and target_id not in content:
            findings.append(f"NAV: showPage('{page}') called but no matching page element found")
    # Check for orphaned pages (exist but no nav link)
    for page_id in page_ids:
        if page_id not in nav_pages and page_id not in ['dashboard']:
            # Allow some internal pages without direct nav links
            if page_id not in ['field-quote-modal','sairn-suite','brief-modal']:
                findings.append(f"NAV WARN: Page 'page-{page_id}' exists but has no nav link")
    return findings
```

---

### CHECK 19 — Weather Command Engine (Pattern 12) Accuracy
**What it catches:** Weather present where it shouldn't be, absent where required,
broken geolocation calls, no error fallback, hardcoded weather data.

```python
WEATHER_REQUIRED = ['stonedesk','fabricor','sairnbuild','sairnscape','sairndesign','sairnlaw']
WEATHER_FORBIDDEN = ['sairncode','sairnvet','sairncare','sairnfuneral','sairnhr','sairnacc']

def check_weather_engine(app_id, content):
    findings = []
    has_weather = any(p in content.lower() for p in
                      ['weather','geolocation','open-meteo','wx-temp','weathercode'])
    should_have = any(a in app_id.lower() for a in WEATHER_REQUIRED)
    must_not    = any(a in app_id.lower() for a in WEATHER_FORBIDDEN)

    if must_not and has_weather:
        findings.append(f"Pattern 12 VIOLATION: Weather found in {app_id} — crews don't go outside — remove it")
    if should_have and not has_weather:
        findings.append(f"Pattern 12 MISSING: Weather required in {app_id} — crews go outside — add it")
    if has_weather:
        if 'geolocation' not in content:
            findings.append("Weather: no geolocation — using hardcoded location or no location at all")
        if 'catch' not in content or 'denied' not in content.lower():
            findings.append("Weather: no geolocation denied handling — will silently fail on permission deny")
        if 'crew' not in content.lower() and 'go' not in content.lower():
            findings.append("Weather WARN: No crew go/no-go indicator displayed to user")
    return findings
```

---

### CHECK 20 — Supabase Integration Depth
**What it catches:** Supabase connected but not actually saving data, wrong table names,
missing error handling on queries, anon key in wrong format, no offline fallback.

```python
SUPABASE_TABLES = ['business_profiles','ai_memories','network_insights','session_logs']

def check_supabase_depth(content):
    findings = []
    if 'supabase' not in content.lower():
        return []  # No Supabase — skip
    if 'service_role' in content:
        findings.append("CRITICAL SECURITY: service_role key in frontend — HARD STOP")
    # Verify known tables are referenced
    has_any_table = any(t in content for t in SUPABASE_TABLES)
    if not has_any_table and '.from(' in content:
        findings.append("Supabase .from() calls but no known SAIRN tables referenced — verify table names match schema")
    # Check for offline fallback
    if '.from(' in content and 'localStorage' not in content:
        findings.append("Supabase queries with no localStorage fallback — app breaks when offline")
    # Verify anon key format
    if 'supabase' in content.lower() and 'sb_publishable_' not in content and 'eyJ' not in content:
        findings.append("WARN: Supabase client may not be initialized — no anon key pattern found")
    return findings
```

---

### CHECK 21 — Performance & Load Time
**What it catches:** External scripts blocking render, CDN scripts without fallbacks,
large inline data, missing async/defer on scripts, images without lazy loading.

```python
def check_performance(content):
    import re
    findings = []
    # Scripts without async/defer
    script_tags = re.findall(r'<script\s+src=["\'][^"\']+["\'][^>]*>', content)
    blocking = [s for s in script_tags if 'async' not in s and 'defer' not in s]
    if blocking:
        findings.append(f"Performance: {len(blocking)} blocking scripts without async/defer: {blocking[:2]}")
    # Images without loading=lazy
    imgs = re.findall(r'<img\s[^>]+>', content)
    not_lazy = [i[:60] for i in imgs if 'lazy' not in i and 'data:' not in i]
    if len(not_lazy) > 3:
        findings.append(f"Performance: {len(not_lazy)} images without loading=lazy")
    # Inline data blobs over 10KB
    large_inline = re.findall(r'base64,[A-Za-z0-9+/]{10000,}', content)
    if large_inline:
        findings.append(f"Performance: {len(large_inline)} large inline base64 blobs — consider lazy loading")
    return findings
```

---

### CHECK 22 — UX Completeness (Loading States, Empty States, Feedback)
**What it catches:** Async actions with no loading indicator, empty list states
showing blank space, no success/error feedback on saves, forms with no submit feedback.

```python
UX_REQUIRED = {
    'Loading indicator':  ['loading','spinner','sairn-thinking','ai-thinking','Analyzing','Generating'],
    'Toast/feedback':     ['sairnToast','showToast','toast','alert('],
    'Empty state':        ['empty-state','no results','nothing here','get started'],
    'Success feedback':   ['saved','success','complete','Synced','pushed'],
    'Error feedback':     ['error','failed','try again','check connection'],
}

def check_ux(content):
    findings = []
    for feature, patterns in UX_REQUIRED.items():
        if not any(p.lower() in content.lower() for p in patterns):
            findings.append(f"UX WARN: No '{feature}' pattern found — users get no feedback")
    return findings
```

---

### CHECK 23 — Cross-App Data Contract Consistency
**What it catches:** Bridge calls with wrong `from` values, bridge payload missing
required fields, data types sent to bridge not matching what receiving app expects.

```python
def check_bridge_contracts(app_id, content):
    import re
    findings = []
    bridge_calls = re.findall(
        r"fetch\(['\"]https://sairn\.vercel\.app/api/bridge['\"].*?body.*?JSON\.stringify\((\{[^)]+\})\)",
        content, re.DOTALL
    )
    for call in bridge_calls:
        if 'from' not in call:
            findings.append("Bridge call missing 'from' field — receiving app won't know origin")
        if 'type' not in call:
            findings.append("Bridge call missing 'type' field — receiving app can't route the payload")
        if app_id not in call and f"'{app_id}'" not in call:
            findings.append(f"Bridge call 'from' may not match app_id '{app_id}' — verify")
    return findings
```

---

### CHECK 24 — Compensation Module Gate Hardness
**What it catches:** Compensation/commission visible to wrong roles,
role check done in JS only (must also restrict data display),
dispute/approve flow accessible to wrong role.

```python
def check_compensation_gate(content):
    findings = []
    has_comp = any(p in content.lower() for p in ['commission','compensation','salary','payroll'])
    if not has_comp:
        return []
    gate_patterns = ['currentRole','role ===','role !==','owner','admin','manager']
    has_gate = any(p in content for p in gate_patterns)
    if not has_gate:
        findings.append("CRITICAL: Compensation visible but no role gate found — all roles can see pay data")
    # Check approve/dispute flow is gated
    has_approve = 'approve' in content.lower() or 'dispute' in content.lower()
    if has_approve and 'currentRole' not in content and 'role' not in content:
        findings.append("Approve/dispute flow not gated by role — anyone can approve commissions")
    return findings
```

---

### CHECK 25 — Field Sales Sketch Intelligence Max-3-Questions Rule
**What it catches:** Sketch/napkin mode without the hard 3-question limit in
the system prompt, which causes Claude to interrogate the customer endlessly.

```python
def check_sketch_3q_rule(content):
    findings = []
    has_sketch = any(p in content for p in ['sketch','napkin','drawing','rough'])
    if not has_sketch:
        return []
    max3_patterns = ['MAXIMUM 3', 'MAX 3', 'max 3', 'maximum 3', 'max three', '3 questions']
    if not any(p in content for p in max3_patterns):
        findings.append("Sketch mode MISSING max-3-questions rule in system prompt — Claude will interrogate customers")
    return findings
```

---

### CHECK 26 — SAIRNbiz Connector Presence
**What it catches:** Every B2B app must have SAIRNbiz HR+payroll connector.
Checks for connector panel, sync buttons, and bridge call to SAIRNbiz.

```python
def check_sairnbiz_connector(content):
    findings = []
    biz_patterns = ['SAIRNbiz','sairnbiz','#14B8A6']
    has_biz = any(p in content for p in biz_patterns)
    if not has_biz:
        findings.append("CRITICAL: SAIRNbiz connector missing — required in every B2B app per permanent rule")
        return findings
    sync_patterns = ['Sync.*Payroll','Sync.*HR','payroll.*sync','sairnbiz.*sync']
    import re
    has_sync = any(re.search(p, content, re.IGNORECASE) for p in sync_patterns)
    if not has_sync:
        findings.append("SAIRNbiz connector present but no payroll sync button found")
    return findings
```

---

### CHECK 27 — Universal Pattern Completeness Score
**What it catches:** Missing patterns from the 11 universal patterns of "the first".
Scores each pattern 0-1 and reports total pattern coverage.

```python
PATTERNS = {
    'P1 Role PIN auth':          ['pin','role','doLogin','selectRole'],
    'P2 Structured intake':      ['form-group','form-label','form-input','<label'],
    'P3 Live calc engine':       ['oninput','onchange','updatePreview','calculate','toFixed'],
    'P4 Line item breakdown':    ['line-item','lineItem','<td>','<tr>','table'],
    'P5 Range benchmarking':     ['progress-bar','range-bar','progress-fill','benchmark'],
    'P6 Smart flags':            ['flag','alert','warn','CRITICAL','risk'],
    'P7 Save + history':         ['localStorage','save','history','quotes','jobs'],
    'P8 Print + sig lines':      ['window.print','signature','sig-','______'],
    'P9 Client view':            ['client-view','clientView','clean.*view','client mode'],
    'P10 Admin formula editor':  ['admin','pricing','formula','rate','markup'],
    'P11 CSV export':            ['CSV','csv','export','download'],
}

def check_universal_patterns(content):
    findings = []
    scores   = {}
    for pattern, keywords in PATTERNS.items():
        found = any(k.lower() in content.lower() for k in keywords)
        scores[pattern] = 1 if found else 0
        if not found:
            findings.append(f"Pattern MISSING: {pattern} — add per 'the first' universal standard")
    total = sum(scores.values())
    pct   = round(total / len(PATTERNS) * 100)
    findings.insert(0, f"Universal Pattern Score: {total}/{len(PATTERNS)} ({pct}%)")
    return findings
```

---

## Scoring System

Each check produces a score contribution:

| Check | Weight | Category |
|-------|--------|----------|
| 1-8 Guardian | 4pts each = 32pts | Hard mechanical |
| 9 Claude wiring | 5pts | AI integration |
| 10 Field Quote | 6pts | Core feature |
| 11 Blueprint AI | 4pts | Core feature |
| 12 Suite connector | 4pts | Integration |
| 13 Admin pricing | 5pts | Business logic |
| 14 Mobile | 3pts | UX |
| 15 Print fidelity | 3pts | Output |
| 16 Auth | 4pts | Security |
| 17 Error handling | 4pts | Reliability |
| 18 Navigation | 3pts | UX |
| 19 Weather P12 | 2pts | Pattern |
| 20 Supabase depth | 3pts | Data |
| 21 Performance | 2pts | Speed |
| 22 UX states | 3pts | UX |
| 23 Bridge contracts | 3pts | Integration |
| 24 Comp gate | 4pts | Security |
| 25 Sketch 3Q rule | 3pts | AI |
| 26 SAIRNbiz connector | 4pts | Integration |
| 27 Universal patterns | 5pts | Platform |
| **TOTAL** | **100pts** | |

Deduct points per finding: CRITICAL = full weight lost, HIGH = 60%, MEDIUM = 30%, WARN = 10%.

**Grades:**
- 95-100: PERFECT — ship it
- 92-94: STRONG — ship after minor fixes
- 85-91: GOOD — fix HIGH+ before shipping
- 70-84: NEEDS WORK — fix all HIGH and CRITICAL
- Below 70: REBUILD REQUIRED

---

## Auto-Fix Capabilities

The Ultra Scan auto-fixes what it can without human review:

| Finding Type | Auto-Fix |
|-------------|---------|
| Unicode box chars in JS | Replace with ASCII equivalents |
| Missing try/catch on fetch | Wrap in try/catch with toast error |
| Missing `content?.[0]?.text` null safety | Add optional chaining |
| Missing `print-color-adjust` | Inject into `@media print` block |
| Missing loading state on Claude call | Add `.loading` class toggle |
| Missing toast feedback | Inject `sairnToast()` call |
| Missing `async` on script tags | Add `defer` attribute |
| Missing `loading="lazy"` on images | Add attribute |
| Regex literal newlines | Escape as `\\n` |

**Cannot auto-fix (requires business logic judgment):**
- Missing Feature Quote flow (too much business logic)
- Missing suite connector apps (need correct app URLs)
- Missing role gates on compensation (structural change)
- Navigation dead links (page content may not exist)
- Missing universal patterns (structural build required)

---

## Full Scan Execution Script

```python
import base64, json, urllib.request, urllib.parse, re, pickle

PAT  = "[USER_PAT]"
REPO = "SAIRN1/SAIRN"

APPS = {
    'stonedesk':  'fabricor UPLOAD TO GITHUB.html',
    'sairnbiz':   'sairnbiz.html',
    'sairnlaw':   'sairnlaw.html',
    'sairnscape': 'SAIRNscape UPLOAD TO GITHUB101.html',
    'sairnbuild': 'sairnbuild_v3_UPLOAD_TO_GITHUB222.html',
}

def pull_app(filepath):
    encoded = urllib.parse.quote(filepath)
    req     = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/{encoded}",
        headers={"Authorization": f"token {PAT}", "User-Agent": "Python"}
    )
    with urllib.request.urlopen(req) as r:
        meta    = json.loads(r.read())
        content = base64.b64decode(meta['content']).decode('utf-8', errors='replace')
    return content, meta['sha']

def push_app(filepath, content, sha, message):
    encoded_path    = urllib.parse.quote(filepath)
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    payload = json.dumps({"message": message, "content": encoded_content, "sha": sha}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/{encoded_path}",
        data=payload, method="PUT",
        headers={"Authorization": f"token {PAT}", "User-Agent":"Python","Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['content']['sha']

def run_ultra_scan(app_id, content):
    # Run all 27 checks, collect findings, score, auto-fix
    all_findings = {}
    # ... [all check functions called here]
    return all_findings, score, fixed_content

# Main execution loop
for app_id, filepath in APPS.items():
    content, sha = pull_app(filepath)
    findings, score, fixed = run_ultra_scan(app_id, content)

    print(f"\n{'='*55}")
    print(f"APP: {app_id.upper()} | SCORE: {score}/100")
    print(f"{'='*55}")
    for check, items in findings.items():
        for item in items:
            print(f"  [{check}] {item}")

    if score < 95 and fixed != content:
        new_sha = push_app(filepath, fixed, sha,
                           f"ultra-scan: {27-len([f for fs in findings.values() for f in fs])} fixes applied, score {score}/100")
        print(f"  PUSHED fixed version: {new_sha[:10]}")
    elif score >= 95:
        print(f"  PERFECT -- no push needed")
```

---

## Report Format

```
============================================================
SAIRN ULTRA SCAN REPORT
============================================================
App:    [app_id]
File:   [filepath]
Lines:  [N]  Size: [KB]  SHA: [first10]
Date:   [timestamp]

--- LAYER 1: GUARDIAN (8 checks) ---
CHECK 1  JS String Integrity:      PASS
CHECK 2  Unicode Box Chars:        PASS
CHECK 3  Regex Newline Safety:     PASS
CHECK 4  Proxy Compliance:         PASS  [HARD STOP IF FAIL]
CHECK 5  Print Render:             PASS
CHECK 6  Bridge Sync:              PASS
CHECK 7  Role Gates:               WARN  [1 finding]
CHECK 8  Color Compliance:         PASS

--- LAYER 2: ULTRA (19 checks) ---
CHECK 9  Claude Wiring:            PASS
CHECK 10 Field Quote:              PASS
CHECK 11 Blueprint AI:             WARN  [2 findings]
CHECK 12 Suite Connector:          PASS
CHECK 13 Admin Pricing:            PASS
CHECK 14 Mobile Readiness:         WARN  [1 finding]
CHECK 15 Print Fidelity:           PASS
CHECK 16 Auth Completeness:        PASS
CHECK 17 Error Handling:           WARN  [3 findings]
CHECK 18 Navigation:               PASS
CHECK 19 Weather Engine P12:       PASS
CHECK 20 Supabase Depth:           PASS
CHECK 21 Performance:              WARN  [1 finding]
CHECK 22 UX States:                PASS
CHECK 23 Bridge Contracts:         PASS
CHECK 24 Compensation Gate:        PASS
CHECK 25 Sketch 3Q Rule:           PASS
CHECK 26 SAIRNbiz Connector:       PASS
CHECK 27 Universal Patterns:       10/11 (91%)

FINDINGS: 0 CRITICAL | 0 HIGH | 8 MEDIUM | 4 WARN
AUTO-FIXED: 6 of 12 findings
MANUAL REQUIRED: 6 findings (listed below with exact locations)

SCORE: 94/100  |  GRADE: STRONG — ship after minor fixes

AUTO-FIXES APPLIED:
  [line 847] Added try/catch to Claude fetch call
  [line 1203] Added null safety: content?.[0]?.text
  [line 2891] Added -webkit-print-color-adjust:exact
  [line 412] Added loading state toggle on fqAnalyze()
  [line 1890] Added sairnToast() on save success
  [line 3301] Added defer to PDF.js script tag

MANUAL FIXES NEEDED:
  [CHECK 18] showPage('employees-full') has no matching page element
  [CHECK 27] Pattern P5 (range benchmarking) not found — add to estimate output
  ...

FINAL SHA PUSHED: [sha]
============================================================
```

---

## When to Run Ultra Scan

- **Every time before shipping any SAIRN app update**
- After any major injection or feature addition
- When Michael says anything like: "make it perfect", "deep scan", "full audit", "find everything"
- At the start of every new build session (quick version — Layer 1 only)
- At the end of every build session (full version — both layers)
- After platform-wide injections (like the bridge injection we just ran)

---

*SAIRN Ultra Scan: 27 checks. Auto-fix. Score it. Ship it perfect.*
