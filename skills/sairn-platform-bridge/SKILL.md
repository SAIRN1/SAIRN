---
name: sairn-platform-bridge
description: >
  The complete SAIRN platform integration architecture. Trigger on ANY request involving
  cross-app connections, bridge sync, app launchers, "connect to SAIRNbiz", "add bridge",
  "link apps", "add SAIRNdesign to StoneDesk", "integrate", "unified platform", or any
  task that touches how SAIRN apps communicate with each other. This skill defines exactly
  which apps connect to which, what data flows across the bridge, what launcher panels
  appear in each app, and what the SAIRN Suite connector looks like in every vertical.
  Also triggers when building any new SAIRN B2B app — the bridge connections are defined
  here and must be implemented on day one. No app ships without its correct bridge map.
---

# SAIRN Platform Bridge Architecture
> *"Every app. Connected. One platform. No gaps."*

This skill is the master integration map for the entire SAIRN platform.
Every B2B app connects to every other relevant app via the SAIRN Data Bridge.
This document defines exactly what connects to what, what data flows where,
and what the SAIRN Suite launcher looks like in each app.

---

## Bridge Endpoint
All cross-app data flows through: `https://sairn.vercel.app/api/bridge`

```javascript
// Standard bridge call pattern — every app, every sync
async function bridgeSync(fromApp, toApp, dataType, payload) {
  const res = await fetch('https://sairn.vercel.app/api/bridge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: fromApp,
      to: toApp,
      type: dataType,
      data: payload,
      timestamp: new Date().toISOString()
    })
  });
  return res.json();
}
```

---

## Master App Bridge Map

### The Rule
Every SAIRN B2B app connects to:
1. **SAIRNbiz** (always — HR + payroll + accounting backbone)
2. **Every other app relevant to that industry** (defined below per app)
3. **SAIRNdesign** (if the trade involves finished spaces — interiors, aesthetics, client selections)
4. **SAIRNscape** (if the trade involves exterior site work or landscaping)
5. **SAIRNbuild** (if the trade is a subcontractor trade under a GC)

---

## Per-App Bridge Connections

### StoneDesk (Stone Fabrication — Money Green #16C762)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + payroll for fabricators, installers, sales | Employees, hours, payroll, GL entries |
| SAIRNdesign | Designers order countertops — biggest referral channel | Job orders, material selections, client approvals |
| SAIRNbuild | GCs order countertops for new builds | Job orders, install schedule, POs |
| SAIRNscape | Outdoor kitchen countertops, fire pit surrounds | Job orders, install schedule |

**SAIRN Suite Launcher in StoneDesk:**
```
[SAIRNbiz — HR & Payroll] [SAIRNdesign — Designer Portal] [SAIRNbuild — GC Orders] [SAIRNscape — Outdoor]
```

**Field Quote:** Client sketch → countertop quote (kitchen, bath, outdoor) ✅
**Blueprint AI:** Kitchen floor plan → slab layout + square footage ✅
**Sketch Intelligence:** Napkin drawing → countertop scope + pricing ✅

---

### SAIRNbuild (General Contractor — Amber #F59E0B)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + payroll for GC employees, GL for job costing | Employees, payroll, POs, job cost GL |
| StoneDesk | Order countertops for builds | PO, install date, spec |
| SAIRNdesign | Interior finish selections for builds | Finish schedule, client approvals, selections |
| SAIRNscape | Site work, final landscaping for builds | Scope, schedule, completion |
| SAIRNmechanical | HVAC/plumbing subs | Sub scope, schedule, inspection status |
| SAIRNlaw | Contract management for builds | Contract status, lien waivers, permits |
| SAIRNvet | Vet clinic build-outs (niche but high value) | Project scope if applicable |
| SAIRNcare | Home care facility build-outs | Project scope if applicable |
| SAIRNfuneral | Funeral home renovations | Project scope if applicable |

**SAIRN Suite Launcher in SAIRNbuild:**
```
[SAIRNbiz] [StoneDesk] [SAIRNdesign] [SAIRNscape] [SAIRNmechanical] [SAIRNlaw]
+ All Trade Sub-Portals (Roofing / Electrical / Framing / Plumbing / Tile / HVAC / Siding)
```

**SAIRNbuild is the hub** — it connects to more apps than any other vertical.

---

### SAIRNscape (Lawn & Landscape — Sky Green #22C55E)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + payroll for crews, GL for job costing | Employees, hours, payroll, invoices |
| SAIRNbuild | Coordinate with GC on new construction site work | Site plan, grading schedule, completion |
| SAIRNdesign | Landscape ties to interior/exterior design vision | Design brief, plant selections, hardscape specs |
| StoneDesk | Outdoor kitchen countertops, fire pit caps | PO, material spec, install date |

**SAIRN Suite Launcher in SAIRNscape:**
```
[SAIRNbiz — HR & Payroll] [SAIRNbuild — GC Coordination] [SAIRNdesign — Design Brief] [StoneDesk — Outdoor Surfaces]
```

---

### SAIRNdesign (Interior Design — Indigo #6366F1)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + accounting for design firm | Employees, invoices, project billing |
| StoneDesk | Order countertops for design projects | Material spec, client approval, order |
| SAIRNbuild | Coordinate with GC on renovations | Finish schedule, install dates, punch list |
| SAIRNscape | Exterior/landscape design coordination | Site plan, plant palette, hardscape spec |
| SAIRNfuneral | Funeral home interior design | Design brief, finish selections |
| SAIRNcare | Home care / medical facility interiors | ADA compliance, finish selections |
| SAIRNvet | Veterinary clinic interiors | Design brief, finish selections |

**SAIRN Suite Launcher in SAIRNdesign:**
```
[SAIRNbiz] [StoneDesk — Surfaces] [SAIRNbuild — GC] [SAIRNscape — Exterior] [SAIRNfuneral] [SAIRNcare] [SAIRNvet]
```

---

### SAIRNlaw (Law Firms — Forest Green #15803D)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + payroll for attorneys and staff | Employees, billing hours, payroll |
| SAIRNbuild | Construction contracts, lien waivers, permit disputes | Contract review requests, lien status |
| StoneDesk | Fabrication contracts, warranty disputes | Contract review |
| SAIRNscape | Landscape contracts, property disputes | Contract review |

**SAIRN Suite Launcher in SAIRNlaw:**
```
[SAIRNbiz — HR & Billing] [SAIRNbuild — Construction Contracts] [StoneDesk — Fabrication Contracts]
```

---

### SAIRNmechanical (HVAC & Mechanical — Lime #84CC16)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + payroll for techs, GL for job costing | Employees, payroll, invoices |
| SAIRNbuild | HVAC sub under GC — most common relationship | Sub portal submissions, inspection status, schedule |
| SAIRNdesign | HVAC coordination for design projects | Equipment placement, duct routing |
| SAIRNcare | HVAC for home care facilities (critical environment) | Equipment schedule, maintenance log |
| SAIRNvet | HVAC for veterinary clinics (specialized requirements) | Equipment schedule, air exchange spec |

**SAIRN Suite Launcher in SAIRNmechanical:**
```
[SAIRNbiz — HR & Payroll] [SAIRNbuild — GC Portal] [SAIRNdesign — Coordination] [SAIRNcare] [SAIRNvet]
```

---

### SAIRNcode (Medical Coding — Light Red #F87171)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + payroll for coding staff | Employees, payroll |
| SAIRNcare | Medical coding for home care billing | Patient encounter codes, billing submissions |

**SAIRN Suite Launcher in SAIRNcode:**
```
[SAIRNbiz — HR & Payroll] [SAIRNcare — Home Care Billing]
```

---

### SAIRNcare (Home Care — Teal #0D9488)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + payroll for caregivers | Employees, hours, payroll |
| SAIRNcode | Medical coding for billing | Billing codes, insurance submissions |
| SAIRNmechanical | HVAC maintenance for care homes | Equipment service log |
| SAIRNdesign | ADA-compliant facility design | Design brief, accessibility specs |
| SAIRNbuild | Care facility renovations | Project scope, ADA modifications |

**SAIRN Suite Launcher in SAIRNcare:**
```
[SAIRNbiz — HR & Payroll] [SAIRNcode — Billing] [SAIRNmechanical — HVAC] [SAIRNdesign — Facility Design]
```

---

### SAIRNvet (Veterinary — Violet #7C3AED)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + payroll for vet staff | Employees, payroll |
| SAIRNmechanical | HVAC for clinic (critical air quality) | Equipment schedule, air exchange |
| SAIRNdesign | Clinic interior design | Design brief, finish selections |
| SAIRNbuild | Clinic build-out or renovation | Project scope, construction schedule |

**SAIRN Suite Launcher in SAIRNvet:**
```
[SAIRNbiz — HR & Payroll] [SAIRNmechanical — HVAC] [SAIRNdesign — Clinic Design] [SAIRNbuild — Construction]
```

---

### SAIRNfuneral (Funeral Homes — Slate #6B7280)

**Connects to:**
| App | Why | Data Flow |
|-----|-----|-----------|
| SAIRNbiz | HR + payroll for funeral staff | Employees, payroll |
| SAIRNdesign | Facility interior design (dignified, critical) | Design brief, finish selections |
| SAIRNbuild | Facility renovations | Project scope, construction schedule |
| SAIRNmechanical | HVAC for specialized facility requirements | Equipment schedule |

**SAIRN Suite Launcher in SAIRNfuneral:**
```
[SAIRNbiz — HR & Payroll] [SAIRNdesign — Facility Design] [SAIRNbuild — Construction] [SAIRNmechanical — HVAC]
```

---

## Universal SAIRN Suite Connector Component

Every B2B app gets this identical component. Only the connected apps change per the map above.

```html
<!-- SAIRN Suite Connector — paste in every B2B app -->
<div class="sairn-suite-connector">
  <div class="suite-header">
    <div class="suite-logo">S</div>
    <div>
      <div class="suite-title">SAIRN Suite</div>
      <div class="suite-sub">Connected apps for your business</div>
    </div>
    <div class="suite-status">● Live</div>
  </div>

  <div class="suite-app-grid" id="suite-app-grid">
    <!-- Populated dynamically per app — see appSuiteConfig below -->
  </div>

  <div class="suite-sync-row">
    <button class="suite-sync-btn" onclick="syncAllApps()">🔄 Sync All Apps</button>
    <button class="suite-sync-btn outline" onclick="exportBridgeCSV()">📊 CSV Export</button>
    <span class="suite-last-sync" id="suite-last-sync">Last sync: --</span>
  </div>
</div>
```

```javascript
// App suite configuration — each app defines its own connections
const appSuiteConfig = {
  stonedesk: [
    { id: 'sairnbiz',    name: 'SAIRNbiz',    icon: 'SB', color: '#14B8A6', desc: 'HR & Payroll',       url: 'https://sairn.vercel.app/sairnbiz' },
    { id: 'sairndesign', name: 'SAIRNdesign',  icon: 'SD', color: '#6366F1', desc: 'Designer Orders',    url: 'https://sairn.vercel.app/sairndesign' },
    { id: 'sairnbuild',  name: 'SAIRNbuild',   icon: 'SB', color: '#F59E0B', desc: 'GC Orders',          url: 'https://sairn.vercel.app/sairnbuild' },
    { id: 'sairnscape',  name: 'SAIRNscape',   icon: 'SS', color: '#22C55E', desc: 'Outdoor Surfaces',   url: 'https://sairn.vercel.app/sairnscape' }
  ],
  sairnbuild: [
    { id: 'sairnbiz',       name: 'SAIRNbiz',      icon: 'SB', color: '#14B8A6', desc: 'HR & Payroll'        },
    { id: 'stonedesk',      name: 'StoneDesk',      icon: 'SD', color: '#16C762', desc: 'Countertops'         },
    { id: 'sairndesign',    name: 'SAIRNdesign',    icon: 'SD', color: '#6366F1', desc: 'Interior Design'     },
    { id: 'sairnscape',     name: 'SAIRNscape',     icon: 'SS', color: '#22C55E', desc: 'Site Work'           },
    { id: 'sairnmechanical',name: 'SAIRNmech',      icon: 'SM', color: '#84CC16', desc: 'HVAC/Mechanical'     },
    { id: 'sairnlaw',       name: 'SAIRNlaw',       icon: 'SL', color: '#15803D', desc: 'Contracts & Legal'   }
  ],
  sairnscape: [
    { id: 'sairnbiz',    name: 'SAIRNbiz',    icon: 'SB', color: '#14B8A6', desc: 'HR & Payroll'  },
    { id: 'sairnbuild',  name: 'SAIRNbuild',  icon: 'SB', color: '#F59E0B', desc: 'GC Coordination' },
    { id: 'sairndesign', name: 'SAIRNdesign', icon: 'SD', color: '#6366F1', desc: 'Design Brief'   },
    { id: 'stonedesk',   name: 'StoneDesk',   icon: 'SD', color: '#16C762', desc: 'Outdoor Surfaces' }
  ],
  sairndesign: [
    { id: 'sairnbiz',       name: 'SAIRNbiz',      icon: 'SB', color: '#14B8A6', desc: 'HR & Billing'    },
    { id: 'stonedesk',      name: 'StoneDesk',      icon: 'SD', color: '#16C762', desc: 'Surfaces'        },
    { id: 'sairnbuild',     name: 'SAIRNbuild',     icon: 'SB', color: '#F59E0B', desc: 'GC Coordination' },
    { id: 'sairnscape',     name: 'SAIRNscape',     icon: 'SS', color: '#22C55E', desc: 'Exterior'        },
    { id: 'sairnfuneral',   name: 'SAIRNfuneral',   icon: 'SF', color: '#6B7280', desc: 'Funeral Homes'   },
    { id: 'sairncare',      name: 'SAIRNcare',      icon: 'SC', color: '#0D9488', desc: 'Care Facilities' },
    { id: 'sairnvet',       name: 'SAIRNvet',       icon: 'SV', color: '#7C3AED', desc: 'Vet Clinics'     }
  ],
  sairnlaw: [
    { id: 'sairnbiz',    name: 'SAIRNbiz',   icon: 'SB', color: '#14B8A6', desc: 'HR & Billing'  },
    { id: 'sairnbuild',  name: 'SAIRNbuild', icon: 'SB', color: '#F59E0B', desc: 'Construction Contracts' },
    { id: 'stonedesk',   name: 'StoneDesk',  icon: 'SD', color: '#16C762', desc: 'Fabrication Contracts' }
  ],
  sairnmechanical: [
    { id: 'sairnbiz',    name: 'SAIRNbiz',    icon: 'SB', color: '#14B8A6', desc: 'HR & Payroll'  },
    { id: 'sairnbuild',  name: 'SAIRNbuild',  icon: 'SB', color: '#F59E0B', desc: 'GC Portal'     },
    { id: 'sairndesign', name: 'SAIRNdesign', icon: 'SD', color: '#6366F1', desc: 'Coordination'  },
    { id: 'sairncare',   name: 'SAIRNcare',   icon: 'SC', color: '#0D9488', desc: 'Care Facilities' },
    { id: 'sairnvet',    name: 'SAIRNvet',    icon: 'SV', color: '#7C3AED', desc: 'Vet Clinics'   }
  ],
  sairncode: [
    { id: 'sairnbiz',  name: 'SAIRNbiz', icon: 'SB', color: '#14B8A6', desc: 'HR & Payroll' },
    { id: 'sairncare', name: 'SAIRNcare',icon: 'SC', color: '#0D9488', desc: 'Home Care Billing' }
  ],
  sairncare: [
    { id: 'sairnbiz',       name: 'SAIRNbiz',      icon: 'SB', color: '#14B8A6', desc: 'HR & Payroll'    },
    { id: 'sairncode',      name: 'SAIRNcode',      icon: 'SC', color: '#F87171', desc: 'Medical Billing' },
    { id: 'sairnmechanical',name: 'SAIRNmech',      icon: 'SM', color: '#84CC16', desc: 'HVAC Service'    },
    { id: 'sairndesign',    name: 'SAIRNdesign',    icon: 'SD', color: '#6366F1', desc: 'Facility Design' },
    { id: 'sairnbuild',     name: 'SAIRNbuild',     icon: 'SB', color: '#F59E0B', desc: 'Construction'    }
  ],
  sairnvet: [
    { id: 'sairnbiz',       name: 'SAIRNbiz',      icon: 'SB', color: '#14B8A6', desc: 'HR & Payroll'   },
    { id: 'sairnmechanical',name: 'SAIRNmech',      icon: 'SM', color: '#84CC16', desc: 'HVAC/Air'       },
    { id: 'sairndesign',    name: 'SAIRNdesign',    icon: 'SD', color: '#6366F1', desc: 'Clinic Design'  },
    { id: 'sairnbuild',     name: 'SAIRNbuild',     icon: 'SB', color: '#F59E0B', desc: 'Construction'   }
  ],
  sairnfuneral: [
    { id: 'sairnbiz',       name: 'SAIRNbiz',      icon: 'SB', color: '#14B8A6', desc: 'HR & Payroll'   },
    { id: 'sairndesign',    name: 'SAIRNdesign',    icon: 'SD', color: '#6366F1', desc: 'Facility Design' },
    { id: 'sairnbuild',     name: 'SAIRNbuild',     icon: 'SB', color: '#F59E0B', desc: 'Construction'   },
    { id: 'sairnmechanical',name: 'SAIRNmech',      icon: 'SM', color: '#84CC16', desc: 'HVAC'           }
  ]
};

// Render suite connector for current app
function renderSuiteConnector(appId) {
  const apps = appSuiteConfig[appId] || [];
  const grid = document.getElementById('suite-app-grid');
  if (!grid) return;
  grid.innerHTML = apps.map(app => `
    <div class="suite-app-tile" onclick="launchApp('${app.id}', '${app.url || '#'}')"
         style="border-top: 3px solid ${app.color}">
      <div class="suite-app-icon" style="background:${app.color}">${app.icon}</div>
      <div class="suite-app-name">${app.name}</div>
      <div class="suite-app-desc">${app.desc}</div>
    </div>
  `).join('');
}

// Sync all connected apps via bridge
async function syncAllApps() {
  const btn = event.target;
  btn.textContent = '🔄 Syncing...';
  try {
    await bridgeSync(CURRENT_APP_ID, 'sairnbiz', 'full-sync', getSyncPayload());
    document.getElementById('suite-last-sync').textContent =
      'Last sync: ' + new Date().toLocaleTimeString();
    btn.textContent = '✅ Synced';
    setTimeout(() => btn.textContent = '🔄 Sync All Apps', 3000);
  } catch(e) {
    btn.textContent = '❌ Sync Failed — Retry';
  }
}
```

---

## Bridge Data Types (Standard Across All Apps)

```javascript
// What gets sent across the bridge — all typed, all versioned
const bridgeDataTypes = {
  // People
  'employee-sync':    'Employee record + hours + role',
  'payroll-hours':    'Hours worked by employee for payroll period',
  'payroll-run':      'Completed payroll run for GL posting',

  // Money
  'gl-entry':         'General ledger entry (debit/credit/account/amount)',
  'invoice':          'Invoice to client (itemized, total, due date)',
  'purchase-order':   'PO to vendor (items, quantities, amounts)',
  'payment':          'Payment made or received',

  // Jobs
  'job-order':        'Job/project order from one app to another',
  'job-update':       'Status update on an active job',
  'job-complete':     'Job completion notification',
  'schedule-request': 'Scheduling request between apps',

  // Materials
  'material-spec':    'Material specification (for countertops, finishes, etc.)',
  'material-order':   'Material purchase order',

  // Contracts
  'contract-request': 'Request for contract review (to SAIRNlaw)',
  'contract-status':  'Contract status update from SAIRNlaw',
  'lien-waiver':      'Lien waiver request/status',

  // Design
  'design-brief':     'Design brief from SAIRNdesign to trade app',
  'finish-selection': 'Material/finish selection for client approval',
  'client-approval':  'Client approval of design selection',

  // Alerts
  'flag-alert':       'Claude-detected issue requiring cross-app attention',
  'field-quote':      'Field quote sent from one app (e.g. for referral jobs)'
};
```

---

## CSS for Suite Connector (Universal)

```css
/* SAIRN Suite Connector — universal styles, paste into every app */
.sairn-suite-connector {
  background: linear-gradient(135deg, #F8FAFC, #FFFFFF);
  border: 1.5px solid #E2E8F0;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}
.suite-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.suite-logo {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, #F59E0B, #16C762);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 900; color: white;
}
.suite-title { font-size: 15px; font-weight: 700; color: #1E293B; }
.suite-sub   { font-size: 12px; color: #94A3B8; }
.suite-status { margin-left: auto; font-size: 12px; font-weight: 700; color: #16A34A; }
.suite-app-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.suite-app-tile {
  background: white;
  border: 1.5px solid #E2E8F0;
  border-radius: 8px;
  padding: 12px 10px;
  cursor: pointer;
  transition: all 0.12s;
  text-align: center;
}
.suite-app-tile:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.10);
  transform: translateY(-1px);
}
.suite-app-icon {
  width: 32px; height: 32px;
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 900; color: white;
  margin: 0 auto 6px;
}
.suite-app-name { font-size: 12px; font-weight: 700; color: #1E293B; }
.suite-app-desc { font-size: 10px; color: #94A3B8; margin-top: 2px; }
.suite-sync-row {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.suite-sync-btn {
  padding: 8px 14px;
  background: #1E293B; color: white;
  border: none; border-radius: 6px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: background 0.12s;
}
.suite-sync-btn:hover { background: #334155; }
.suite-sync-btn.outline {
  background: white; color: #1E293B;
  border: 1.5px solid #E2E8F0;
}
.suite-sync-btn.outline:hover { background: #F8FAFC; }
.suite-last-sync {
  font-size: 12px; color: #94A3B8; margin-left: auto;
}
```

---

## Field Quote + Sketch Intelligence — Required in All Apps

Per the permanent rule (memory #27), every B2B app ships with:

1. **📷 Field Quote button** — topbar, always visible, one tap
2. **Admin Pricing Panel** — owner sets rates, Claude uses them
3. **Sketch Intelligence** — any drawing → max 3 questions → quote
4. **Signature capture** — on-screen, touch/stylus
5. **Deposit link** — via navigator.share or SMS

Reference: `skills/sairn-sketch-intelligence/SKILL.md` SHA `bf1099e9`

---

## Blueprint AI + LiDAR — Per-App Applicability

| App | Blueprint AI | LiDAR | Notes |
|-----|-------------|-------|-------|
| StoneDesk | ✅ Kitchen/bath floor plan → slab layout | ✅ Room scan → countertop dimensions | Primary use: kitchen scan |
| SAIRNbuild | ✅ Full blueprint read, all trades | ✅ Room/space scan | Hub for all trade takeoffs |
| SAIRNscape | ✅ Site plan / property sketch | ✅ Outdoor space scan | Lot scan → landscape scope |
| SAIRNdesign | ✅ Floor plan → finish schedule | ✅ Room scan → space planning | Primary use: room scan |
| SAIRNmechanical | ✅ Floor plan → equipment/duct layout | ✅ Mechanical room scan | Equipment placement |
| SAIRNvet | ✅ Clinic plan → equipment layout | ✅ Exam room scan | Clinic optimization |
| SAIRNcare | ✅ Home plan → care planning | ✅ Home scan → ADA assessment | Accessibility planning |
| SAIRNfuneral | ✅ Facility plan → service layout | ✅ Chapel/room scan | Capacity planning |
| SAIRNlaw | ❌ | ❌ | No physical scope |
| SAIRNcode | ❌ | ❌ | No physical scope |

---

## Weather Command Engine — Per-App Applicability

Pattern 12 rule: crews go outside = gets it. No = skip.

| App | Weather | Reason |
|-----|---------|--------|
| SAIRNbuild | ✅ | Crews outside every day |
| SAIRNscape | ✅ | Entire business is outdoors |
| StoneDesk | ✅ | Delivery/install crews outside |
| SAIRNdesign | ✅ | Site visits, exterior work |
| SAIRNlaw | ✅ | Site visits for property disputes |
| SAIRNmechanical | ✅ | Outdoor condenser/rooftop units |
| SAIRNvet | ❌ | Interior clinic only |
| SAIRNcare | ❌ | Interior home care only |
| SAIRNcode | ❌ | Office only |
| SAIRNfuneral | ❌ | Interior facility only |

---

## Build Priority Order for Bridge Injection

When patching existing apps with bridge connections, do in this order:

1. **SAIRNbiz connector** (payroll/GL sync) — all apps, always first
2. **SAIRN Suite launcher panel** (app grid per config above)
3. **Field Quote button + modal** (topbar + full flow)
4. **Admin Pricing Panel** (owner sets rates)
5. **Blueprint AI module** (where applicable)
6. **Weather Command Engine** (where applicable)
7. **Sync All / CSV Export buttons**

---

## Patch Template (inject into any existing app)

When adding bridge connections to an existing app, insert after the existing sidebar:

```html
<!-- INJECT: SAIRN Suite Panel — add as a sidebar nav item and page -->
<div class="nav-item" onclick="showPage('sairn-suite')">
  <span class="nav-icon">🔗</span> SAIRN Suite
</div>

<!-- INJECT: Field Quote — add to topbar -->
<button class="field-quote-topbar-btn" onclick="openFieldQuote()">
  📷 Field Quote
</button>

<!-- INJECT: Admin Pricing — add to admin/settings section -->
<div class="nav-item" onclick="showPage('admin-pricing')">
  <span class="nav-icon">💲</span> Pricing Setup
</div>
```

---

*SAIRN Platform Bridge: Every app connected. Every trade equipped. One platform.*
