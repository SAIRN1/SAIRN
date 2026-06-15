---
name: sairnbuild-master
description: >
  The complete build intelligence skill for SAIRNbuild — SAIRN's general contractor platform.
  Trigger this skill on ANY SAIRNbuild task: building or extending the app, adding trade modules
  (roofing, electrical, framing, plumbing, siding, windows, tile, HVAC, and all others), building
  or modifying the subcontractor portal, implementing blueprint photo AI takeoffs, setting up
  trade-specific portals, adding Claude intelligence layers to jobsite photos or sub submissions,
  integrating SAIRNdesign for builders, or connecting the vendor/employee management system.
  Also triggers on: "sub portal", "subcontractor login", "blueprint scan", "takeoff", "trade module",
  "roofing panel", "electrical module", "framing module", "GC dashboard", "jobsite photos",
  "materials log", "safety log", "Claude watch the job", "builder repertoire", or any request
  to extend SAIRNbuild's capabilities. This skill makes SAIRNbuild the only platform on earth
  where a GC manages every trade, every sub, every vendor, every employee — with Claude watching
  the whole job in real time.
---

# SAIRNbuild Master Build Skill

> *"Every sub. Every trade. Every vendor. Every employee. Claude watching it all."*

SAIRNbuild is SAIRN's general contractor platform. It is the only construction management tool
where Claude AI is embedded at the intelligence layer — reading jobsite photos, analyzing sub
submissions, flagging problems before they happen, and giving GCs instant blueprint takeoffs
by trade. This skill governs every build decision for SAIRNbuild.

---

## Platform Identity

- **Color:** Amber `#F59E0B` | Dark: `#92400E` | Tint: `#FFFBEB` | Accent: `#FCD34D`
- **Price:** $199/mo | Founding Member: $149/mo
- **File:** `sairnbuild_v3_UPLOAD_TO_GITHUB222.html`
- **GitHub repo:** `SAIRN1/SAIRN`
- **Proxy:** `https://sairn.vercel.app/api/claude` (NEVER api.anthropic.com)
- **Bridge:** `https://sairn.vercel.app/api/bridge`
- **Supabase:** `https://ejrlrrkvhtllxbbypdjb.supabase.co`
- **Background:** Always light. Never dark. Print-first always.
- **SAIRNdesign access:** Builders get SAIRNdesign (Indigo `#6366F1`) integrated — interior
  design capability bundled into the GC platform.
- **Weather Command Engine (Pattern 12):** REQUIRED — crews go outside.

---

## Core Architecture — What SAIRNbuild Must Do

SAIRNbuild has four intelligence pillars:

### PILLAR 1 — Subcontractor Portal (Claude-Watched)
Every sub gets a unique portal login tied to a specific project and trade.
From their portal, subs submit:
- **Time logs** — clock in/out, hours by task, crew count
- **Materials log** — item, quantity, unit cost, supplier, receipt photo upload
- **Photo submissions** — progress photos, safety compliance photos, issue photos
- **Safety checklist** — PPE compliance, hazard identification, incident reports
- **Daily field report** — narrative summary, blockers, next-day plan

Claude receives every submission and:
1. Reads all photos using vision — looks for safety violations, quality issues, wrong materials,
   structural concerns, code violations visible in photos
2. Cross-references materials logged vs. budget allocated
3. Flags anomalies: time gaps, missing safety items, unusual material costs, photo-detected issues
4. Generates a **Sub Intelligence Brief** for the GC — routed to that sub's file/directory
5. Proactively warns GC before problems escalate: "Electrical sub's photo shows junction box
   placement that conflicts with HVAC rough-in — recommend pre-inspection before drywall."

**Sub portal is role-gated:** Sub only sees their own project scope. GC sees everything.

### PILLAR 2 — Trade Modules (First-Class, Not Add-Ons)
Each trade is a full module inside the GC dashboard. Current required modules:

| Module | Key Features |
|--------|-------------|
| **Plumbing** | Fixture schedules, rough-in tracking, pressure test logs, permit status |
| **Roofing** | Square calculation, material takeoff by pitch/plane, warranty tracking, storm damage log |
| **Electrical** | Circuit schedules, panel load calculations, permit status, inspection checklist |
| **Framing** | Linear footage tracking, lumber schedule, structural inspection log, shear wall schedule |
| **Tile** | Area calculation by room, grout/adhesive takeoff, pattern tracking, substrate log |
| **HVAC** | Load calc summary, duct schedule, equipment schedule, startup checklist |
| **Siding & Windows** | Linear/square footage, opening schedule, flashing log, warranty register |
| **SAIRNdesign** | Interior design integration — finish schedule, material selections, 3D render links |
| **SAIRNscape** | Landscape integration — site work, grading, drainage, final landscaping |

Every trade module connects to:
- Sub portal (that trade's sub logs into their module)
- Blueprint AI (auto-populates quantities from scan)
- Claude intelligence (watches the trade's submissions)
- GC master dashboard (all trades visible in one view)

### PILLAR 3 — Blueprint AI Takeoff Engine
The single most powerful feature. GC or sub uploads a photo or PDF of blueprints.
Claude reads the blueprint and delivers instant trade-specific takeoffs.

**How it works:**
1. User selects their role/trade before scanning
2. Uploads blueprint photo(s) — phone camera acceptable, PDF also accepted
3. Claude reads the blueprint using vision + OCR reasoning
4. Returns trade-specific output:

| Trade | What Claude Extracts |
|-------|---------------------|
| **GC (full read)** | All dimensions, room areas, total SF, exterior perimeter, window/door schedule, structural notes, spec callouts |
| **Roofer** | Roof planes, pitch, total square footage, ridge/valley/hip linear footage, penetrations count |
| **Electrician** | Panel locations, circuit counts, outlet/switch/fixture counts by room, service size |
| **Framer** | Wall linear footage by floor, header schedule, beam spans, stud count estimate |
| **Plumber** | Fixture count by type, drain line linear footage, hot/cold run estimates |
| **Tile** | Room-by-room floor/wall area, SF with 10% waste factor built in, substrate type per area |
| **HVAC** | Conditioned area by zone, window exposure, R-value callouts, equipment rough-in locations |
| **Siding** | Exterior wall SF minus openings, linear footage of trim, soffit/fascia linear footage |

Claude outputs a **Takeoff Report Card** — formatted, printable, saveable to project file.
Includes: quantities, suggested material list, estimated labor hours by SAIRN benchmark, price range.

**Confidence scoring:** Claude flags any area where blueprint is unclear or scale is ambiguous.
User can correct and Claude re-calculates instantly.

### PILLAR 4 — GC Master Command Dashboard
The GC's single view of the entire project:
- All trades: status, last submission, open flags, completion %
- All subs: active, inactive, flagged, pending submission
- All vendors: PO status, delivery schedule, invoice status
- All employees: time logged today, assigned trade, location
- **Project Health Score** — Claude-generated 0-100 score updated daily
- **Risk Flags** — Claude's proactive warnings sorted by severity
- **Budget Tracker** — committed vs. actual vs. projected, by trade
- **Schedule Tracker** — critical path, current delay risk, next 7-day lookahead
- SAIRNdesign link — open interior design module for this project
- SAIRNbiz link — HR/payroll for employees on this job
- Print: Daily Project Report (one-click, all trades, signature lines)

---

## Build Rules for SAIRNbuild

### SAIRN Hard Rules (always enforced)
- Proxy ONLY: `https://sairn.vercel.app/api/claude` — never `api.anthropic.com`
- No Unicode box chars in JS — use `===` or `---` in comments only
- No dark backgrounds — Amber `#F59E0B` on white/`#FFFBEB` tint
- No blue — SAIRNdesign owns all blue (`#6366F1`); when linking to SAIRNdesign, use their color
- Bridge required: all cross-app data via `sairn.vercel.app/api/bridge`
- SAIRNbiz connector: every B2B app gets the SAIRNbiz launcher panel
- Guardian scan before every push
- Python urllib for GitHub pushes (never curl for files over 100KB)
- 3-phase protocol for full app builds
- Regex: always escape newlines as `\\n` in JS

### Claude API Call Pattern for SAIRNbuild
```javascript
// Standard Claude call — SAIRNbuild pattern
async function callClaude(prompt, systemPrompt, imageBase64 = null) {
  const messages = [{ role: 'user', content: imageBase64
    ? [
        { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: imageBase64 }},
        { type: 'text', text: prompt }
      ]
    : prompt
  }];

  const res = await fetch('https://sairn.vercel.app/api/claude', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      app_id: 'sairnbuild',
      is_demo: true,
      system: systemPrompt,
      messages
    })
  });
  const data = await res.json();
  return data.content?.[0]?.text || '';
}
```

### Sub Portal Login Pattern
```javascript
// Sub portals use project_token + trade_code — NOT the main PIN system
// Format: sairnbuild.io/sub?token=PROJ-001&trade=roofing
// Token is generated by GC and texted/emailed to sub
// Sub sees ONLY their trade scope for that project
// GC role sees all trades, all projects
```

### Blueprint Image Upload Pattern
```javascript
// Convert uploaded file to base64 for Claude vision
async function readBlueprintImage(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result.split(',')[1]); // base64 only
    reader.readAsDataURL(file);
  });
}
// Then pass base64 to callClaude() with blueprint analysis system prompt
```

---

## System Prompts by Feature

### Sub Portal — Claude Intelligence Brief
```
You are the SAIRN Construction Intelligence Engine embedded in SAIRNbuild.
A subcontractor has just submitted their daily field report for a construction project.
Your job is to:
1. Analyze all submitted data: time logs, materials, photos, safety checklist, narrative
2. Identify ANY anomaly, risk, quality concern, or safety issue
3. If photos are included, examine them carefully for: safety violations, wrong materials,
   poor workmanship visible in photos, code-concern installations, conflicts with other trades
4. Generate a Sub Intelligence Brief for the General Contractor
5. Lead with CRITICAL flags (stop-work level), then HIGH (fix today), then MEDIUM (watch),
   then LOW (noted for record)
6. If everything looks good, say so clearly — GCs need confidence, not noise
Format: Brief header with sub name/trade/date, then flagged items with severity,
then "All Clear" items, then recommended GC action. Be direct. Be fast. Save the job.
```

### Blueprint Takeoff — Trade-Specific
```
You are the SAIRN Blueprint Intelligence Engine.
The user has uploaded a construction blueprint photo or scan.
Their trade/role is: {TRADE}

Your job is to read this blueprint and extract ALL information relevant to {TRADE}.
Be precise. Show your work. Note any areas where the blueprint is unclear or scale is uncertain.

For the takeoff, provide:
1. All key quantities for {TRADE} (see trade-specific list)
2. Material list with quantities and waste factors
3. Estimated labor hours (use industry standard benchmarks)
4. Price range estimate (low/mid/high based on current regional material costs)
5. Any spec callouts, notes, or details visible that affect {TRADE} scope
6. Confidence rating per quantity: HIGH (clear dimension shown) / MEDIUM (calculated from scale)
   / LOW (estimated, recommend field verify)

Format as a printable Takeoff Report Card. Be fast. Be accurate. Flag uncertainty honestly.
```

### Project Health Score
```
You are the SAIRN Project Intelligence Engine generating a daily Project Health Score.
Score this project 0-100 based on all available data:
- Schedule adherence (are trades on track?)
- Budget burn rate (is spending aligned with completion %)
- Sub submission compliance (are subs logging daily as required?)
- Open flags (unresolved critical/high issues drag score down hard)
- Safety record (any incidents = immediate score impact)
- Photo evidence of progress (visual confirmation of claimed work)

Output: Score (0-100), one-sentence verdict, top 3 factors driving the score,
and one recommended GC action for today. Be direct. No filler.
```

---

## Panel Registry — SAIRNbuild Required Panels

### GC Dashboard (Home)
- Project selector + Project Health Score
- All-trades status grid
- Today's sub activity feed
- Risk flags from Claude (sorted: CRITICAL → HIGH → MEDIUM)
- Quick actions: Add Project, Invite Sub, Upload Blueprint, Print Day Report

### Projects
- Project list with status, trade count, budget, schedule health
- Individual project view: all trades, all subs, budget tracker, schedule
- Add/edit project: address, owner, contract value, start/end dates, trade scope

### Subcontractor Portal Manager
- Sub list: name, trade, active projects, last submission, compliance score
- Invite sub: generate portal token, send via text/email
- Sub detail: full submission history, all photos, all flags, Claude briefs
- Sub compliance tracker: submission rate, safety score, flag history

### Trade Modules (one panel per trade, expandable)
See trade module table above. Each panel has:
- Sub assigned to this trade on this project
- Scope summary + quantities
- Submission log (last 30 days)
- Claude flags for this trade
- Blueprint takeoff for this trade
- Inspection status + permit status

### Blueprint AI Takeoff
- Upload zone (drag-drop or camera)
- Trade selector (GC full read / specific trade)
- Takeoff Report Card output
- Save to project / Print / Export CSV

### Employees
- Employee list: name, role, trade, current project, hours today
- Time log: clock in/out, project, trade, task
- Schedule: who's on what job this week
- Export to SAIRNbiz payroll

### Vendors
- Vendor list: name, trade specialty, contact, rating
- PO register: open, received, invoiced, paid
- Delivery schedule
- Export to SAIRNbiz GL

### Compensation (role-gated)
- Sales/estimator commission tracking
- Salary/commission/hybrid structures
- Rep approve/dispute workflow
- Manager resolve/mark-paid
- Role gates: owner/admin see all, manager sees team, rep sees own only

### SAIRNdesign Link
- Project finish schedule
- Material selections tracker
- Link to SAIRNdesign app for full interior design capability
- Color/finish approval log (client sign-off)

### Reports & Print
- Daily Project Report (all trades, all subs, one printable page)
- Sub Performance Report
- Budget Variance Report
- Safety Incident Log
- Blueprint Takeoff Archive
- All reports: print-first, signature lines, SAIRNbuild amber branding

### SAIRNbiz Connector (required on every B2B app)
- Sync employees to SAIRNbiz HR
- Sync payroll hours to SAIRNbiz payroll
- Sync vendor POs to SAIRNbiz GL
- "Sync All" button
- Bridge status indicator

### Check Register / Print
- Bank setup (routing/account/check number)
- Write-a-check form (payee, auto-written dollar amount, memo, project link)
- 3-per-page print on blank check stock
- Register history + CSV export
- Auto-GL-post via SAIRN Bridge

---

## Competitive Moats — Never Lose These

1. **Claude watches every photo** — no competitor does this
2. **Sub portal with AI brief to GC** — no competitor does this
3. **Trade-specific blueprint AI** — tile guy gets tile SF, roofer gets squares — unique
4. **Every trade in one $199/mo platform** — Procore charges $10K+/year
5. **SAIRNdesign bundled** — GC gets interior design capability — unique
6. **Proactive risk flags before problems happen** — no competitor does this
7. **Project Health Score updated daily by Claude** — unique

---

## 3-Phase Build Protocol (for full builds)

**Phase 1** — DOCTYPE + full CSS (Amber theme) + login screen + app shell + topbar + sidebar.
No page content. No JS. Confirm complete, wait for "continue."

**Phase 2** — All page content panels (HTML structure only). No JS.
Confirm complete, wait for "continue."

**Phase 3** — All JavaScript + Guardian scan + Python push to GitHub.
Zero failures before push.

---

## Guardian Scan Checklist (run before every push)

- [ ] No `api.anthropic.com` calls — proxy only
- [ ] No Unicode box chars in JS (`─ │ ╔ ═` etc.)
- [ ] No regex with literal newlines — must be `\\n`
- [ ] No `service_role` key in frontend
- [ ] No blue colors except SAIRNdesign link sections
- [ ] No dark backgrounds
- [ ] All Claude calls include `app_id: 'sairnbuild'` and `is_demo: true`
- [ ] SAIRNbiz connector panel present
- [ ] Bridge sync buttons present
- [ ] Check register module present
- [ ] Weather Command Engine present (Pattern 12 — crews go outside)
- [ ] Print buttons on all report panels
- [ ] Role gates on Compensation module
- [ ] Sub portal token system (not PIN system) implemented
- [ ] Blueprint image upload converts to base64 correctly

---

*SAIRNbuild: Every sub. Every trade. Every vendor. Every employee. Claude watching it all.*
