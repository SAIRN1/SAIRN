# SAIRNdental Vendor/Supply Ordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNdental a vendor/supply ordering module — a real dental-supplies catalog across 5 real named vendors, stock tracking with low-stock alerts, a cart + order-placement flow, negotiated pricing, and AI-assisted comparison/spend analysis — mirroring StoneDesk's existing `panel-vendorcat` in shape.

**Architecture:** Two new panels (`panel-vendorcat`, `panel-supplies`) added to `sairndental.html`, following this file's exact existing conventions (`$`/`H`/`fmt`/`toast`/`st`/`ld`/`newId`/`dntLocalToday` helpers, `nav()` dispatch table, `.kpi`/`.card`/`.btn` CSS classes — no new CSS needed). All data is localStorage-only (`dnt_` prefixed keys), matching StoneDesk's actual reference feature (no server sync, no `api/sd-data.js` changes, no SQL migration).

**Tech Stack:** Vanilla JS, single-file client app (no build step, no test runner — verified via `python tools/checkblocks.py sairndental.html` and manual/traced code-path verification, matching this file's established convention).

## Global Constraints

- All new data is localStorage-only. No changes to `api/sd-data.js`, no new SQL table, no `sdnData()` calls anywhere in this feature.
- 5 real named vendors: Henry Schein Dental, Patterson Dental, Benco Dental, Darby Dental Supply, Burkhart Dental. No fabricated per-vendor phone/email — `website` is a real, stable company domain; `phone`/`email` come from `dnt_vendor_contacts`, blank until the practice fills in their actual assigned rep.
- Product names/SKUs/prices are a representative, illustrative catalog — not live-synced vendor pricing.
- No edit flow for stock items, catalog products, or order history — matches this app's platform-wide add/remove-only convention (confirmed: zero edit handlers exist anywhere in this file today).
- `python tools/checkblocks.py sairndental.html` must report `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0` after every task.
- Never bulk find-replace — every edit below is a targeted, unique-context change.
- Reuse this file's real existing helpers exactly as they are: `$(id)`, `H(s)` (HTML-escape), `fmt(n)` (currency), `st(k,v)`/`ld(k,d)` (localStorage JSON), `toast(msg,duration)`, `newId(prefix)`, `dntLocalToday()`. Do not reinvent any of these.

---

## File Structure

| File | Responsibility for this feature |
|---|---|
| `sairndental.html` | `DNT_VENDORS` static catalog; `panel-vendorcat` (catalog browsing + cart + place order); `panel-supplies` (stock tracking); negotiated-pricing settings UI; AI Compare + Spend Report; sidebar nav entries; `nav()` dispatch entries. |

Line numbers below are as of this plan's base commit and will drift as earlier tasks land — every edit is anchored to unique surrounding code, not the raw number.

---

### Task 1: Vendor Catalog — data, browsing, and cart

**Files:**
- Modify: `sairndental.html` (sidebar ~L231-236, panel container ~L481-482, `nav()` ~L616-636, script section before `function init(){` ~L1490)

**Interfaces:**
- Produces: `DNT_VENDORS` (static catalog object, keyed `henryschein`/`patterson`/`benco`/`darby`/`burkhart`), `vendorCart()`/`vCartAdd()`/`vCartUpdate()`/`vCartClear()`/`vRenderCart()`, `vSetTab(vKey,btn)`, `vCatSet(cat,btn)`, `rVendorCat()`, module-level `_dntActiveVendor`/`_dntActiveCat`.
- Consumed by: Task 2 (Place Order reads `vendorCart()`/`DNT_VENDORS`), Task 3 (low-stock badge reads `rVendorCat()`'s rendering), Task 4 (pricing reads `DNT_VENDORS` product prices), Task 5 (AI Compare reads the active vendor/product).

- [ ] **Step 1: Add the sidebar "Supplies" section (Vendor Catalog entry)**

Find (the exact current end of the sidebar, before the footer):

```html
      <div class="ss">Billing</div>
      <button class="sb" id="sb-billing" onclick="nav('billing')"><span class="sico">&#128176;</span>Billing</button>
      <div class="sfoot">SAIRNdental &copy; 2026</div>
```

Replace with:

```html
      <div class="ss">Billing</div>
      <button class="sb" id="sb-billing" onclick="nav('billing')"><span class="sico">&#128176;</span>Billing</button>
      <div class="ss">Supplies</div>
      <button class="sb" id="sb-supplies" onclick="nav('supplies')"><span class="sico">&#128230;</span>Supplies</button>
      <button class="sb" id="sb-vendorcat" onclick="nav('vendorcat')"><span class="sico">&#128722;</span>Vendor Catalog</button>
      <div class="sfoot">SAIRNdental &copy; 2026</div>
```

- [ ] **Step 2: Add the `panel-vendorcat` HTML, after `panel-billing`**

Find (the exact current end of `panel-billing`, before the modal):

```html
        <div class="card"><div class="ch"><div class="ct">Payments</div></div><div class="cb" style="padding:0">
          <table id="payments-table"><thead><tr><th>Date</th><th>Amount</th><th>Method</th></tr></thead><tbody id="payments-tbody"></tbody></table>
        </div></div>
      </div>

      <div class="modal" id="completeVisitModal">
```

Replace with:

```html
        <div class="card"><div class="ch"><div class="ct">Payments</div></div><div class="cb" style="padding:0">
          <table id="payments-table"><thead><tr><th>Date</th><th>Amount</th><th>Method</th></tr></thead><tbody id="payments-tbody"></tbody></table>
        </div></div>
      </div>

      <div class="panel" id="panel-vendorcat">
        <div class="ph"><div><div class="ptitle">Vendor Catalog</div><div class="psub">Browse dental supplies/PPE/materials across vendors, compare prices, and order.</div></div>
          <div class="pa"><button class="btn bo bs" onclick="vShowSpendReport()">Spend Report</button></div>
        </div>
        <div id="vendor-tabs" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px"></div>
        <div id="vcat-tabs" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px"></div>
        <div class="card"><div class="cb">
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:4px">
            <span style="font-size:16px;font-weight:800;color:var(--text)" id="v-name"></span>
            <a id="v-website" href="#" target="_blank" style="font-size:12px;color:var(--p)"></a>
          </div>
          <div style="font-size:12px;color:var(--muted)" id="v-desc"></div>
          <div style="font-size:12px;margin-top:8px" id="v-contact"></div>
        </div></div>
        <div class="card"><div class="cb" style="padding:0">
          <table><thead><tr><th>Product</th><th>Price</th><th>Qty</th><th></th></tr></thead><tbody id="vendor-products-tbody"></tbody></table>
        </div></div>
        <div class="card" id="vendor-cart-card" style="display:none"><div class="ch"><div class="ct">Your Cart</div></div><div class="cb">
          <table><tbody id="vendor-cart-tbody"></tbody></table>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
            <span style="font-size:15px;font-weight:800" id="vendor-cart-total">Total: $0.00</span>
            <button class="btn bp" onclick="vPlaceOrder()">Place Order</button>
          </div>
        </div></div>
      </div>

      <div class="modal" id="completeVisitModal">
```

- [ ] **Step 3: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 4: Add `nav()` dispatch entry**

Find (the exact current end of `nav()`):

```js
  if(id==='referrals')rReferrals();
  if(id==='complaints')rComplaints();
}
```

Replace with:

```js
  if(id==='referrals')rReferrals();
  if(id==='complaints')rComplaints();
  if(id==='vendorcat')rVendorCat();
}
```

- [ ] **Step 5: Add `DNT_VENDORS` catalog and all Vendor Catalog logic, before `function init(){`**

Find (the exact current end of the script, immediately before `init()`):

```js
function init(){
  rDash();
  rComplaintsBadge();
  fillDentalSelects();
  dntSyncFromServer();
}
```

Replace with:

```js
// ── VENDOR CATALOG & SUPPLIES (2026-08-13) ──────────────────────
// Representative catalog under 5 real named dental-supply distributors --
// not live-synced vendor pricing (dental distributors don't publish
// public list prices; matches the disclosed nature of StoneDesk's own
// vendor-catalog reference feature this was modeled on). All data below
// is localStorage-only -- no server sync, matching StoneDesk's actual
// reference feature exactly (see design spec's explicit scope decision).
var DNT_VENDORS={
  henryschein:{name:'Henry Schein Dental',website:'https://www.henryschein.com',
    desc:'Full-line dental distributor -- PPE, restoratives, impression materials, sterilization, instruments.',
    products:[
      {id:'hs01',name:'Level 3 Surgical Masks (50/bx)',sku:'HS-PPE-L3M',cat:'ppe',price:12.99,unit:'box'},
      {id:'hs02',name:'Nitrile Exam Gloves, Medium (100/bx)',sku:'HS-PPE-NGM',cat:'ppe',price:18.99,unit:'box'},
      {id:'hs03',name:'Nitrile Exam Gloves, Large (100/bx)',sku:'HS-PPE-NGL',cat:'ppe',price:18.99,unit:'box'},
      {id:'hs04',name:'Disposable Isolation Gowns (10/pk)',sku:'HS-PPE-ISG',cat:'ppe',price:34.99,unit:'pack'},
      {id:'hs05',name:'Fast-Set Alginate Impression Material (1lb)',sku:'HS-IMP-ALG',cat:'impression',price:16.99,unit:'each'},
      {id:'hs06',name:'VPS Impression Material, Light Body (2 cartridges)',sku:'HS-IMP-VPL',cat:'impression',price:54.99,unit:'pack'},
      {id:'hs07',name:'Bite Registration Material, Fast Set',sku:'HS-IMP-BRF',cat:'impression',price:29.99,unit:'each'},
      {id:'hs08',name:'Universal Composite Resin, A2 Shade Syringe',sku:'HS-RES-A2',cat:'restorative',price:42.99,unit:'each'},
      {id:'hs09',name:'Universal Composite Resin, A3 Shade Syringe',sku:'HS-RES-A3',cat:'restorative',price:42.99,unit:'each'},
      {id:'hs10',name:'Bonding Agent, Universal 5th Gen (5ml)',sku:'HS-RES-BND',cat:'restorative',price:64.99,unit:'each'},
      {id:'hs11',name:'Autoclave Sterilization Pouches (200/bx)',sku:'HS-STR-POU',cat:'sterilization',price:22.99,unit:'box'},
      {id:'hs12',name:'Surface Disinfectant Wipes (160ct)',sku:'HS-STR-WIP',cat:'sterilization',price:14.99,unit:'canister'},
      {id:'hs13',name:'Biological Spore Test Strips (25/pk)',sku:'HS-STR-SPR',cat:'sterilization',price:38.99,unit:'pack'},
      {id:'hs14',name:'Paper Patient Bibs (500/cs)',sku:'HS-DIS-BIB',cat:'disposables',price:27.99,unit:'case'},
      {id:'hs15',name:'Saliva Ejectors (100/bx)',sku:'HS-DIS-SAL',cat:'disposables',price:8.99,unit:'box'},
      {id:'hs16',name:'Cotton Rolls #2 (2000/cs)',sku:'HS-DIS-COT',cat:'disposables',price:19.99,unit:'case'},
      {id:'hs17',name:'Periodontal Probe, UNC 15',sku:'HS-INS-PRB',cat:'instruments',price:24.99,unit:'each'},
      {id:'hs18',name:'Lidocaine 2% w/ Epi 1:100,000 (50 cartridges)',sku:'HS-ANE-LID',cat:'anesthetics',price:44.99,unit:'box'},
      {id:'hs19',name:'Fluoride Varnish, Single Dose (200/bx)',sku:'HS-PRV-FLV',cat:'preventive',price:49.99,unit:'box'},
      {id:'hs20',name:'Prophy Paste, Assorted Flavors (200/jar)',sku:'HS-PRV-PPY',cat:'preventive',price:32.99,unit:'jar'}
    ]},
  patterson:{name:'Patterson Dental',website:'https://www.pattersondental.com',
    desc:'Full-line dental distributor -- equipment, instruments, restoratives, anesthetics, preventive supplies.',
    products:[
      {id:'pd01',name:'Level 3 Surgical Masks (50/bx)',sku:'PD-PPE-L3M',cat:'ppe',price:11.49,unit:'box'},
      {id:'pd02',name:'Nitrile Exam Gloves, Small (100/bx)',sku:'PD-PPE-NGS',cat:'ppe',price:17.99,unit:'box'},
      {id:'pd03',name:'Full Face Shields (10/pk)',sku:'PD-PPE-FFS',cat:'ppe',price:28.99,unit:'pack'},
      {id:'pd04',name:'N95 Respirator Masks (20/bx)',sku:'PD-PPE-N95',cat:'ppe',price:39.99,unit:'box'},
      {id:'pd05',name:'VPS Impression Material, Heavy Body (2 cartridges)',sku:'PD-IMP-VPH',cat:'impression',price:56.99,unit:'pack'},
      {id:'pd06',name:'Fast-Set Alginate Impression Material (1lb)',sku:'PD-IMP-ALG',cat:'impression',price:15.49,unit:'each'},
      {id:'pd07',name:'Glass Ionomer Restorative Cement',sku:'PD-RES-GIC',cat:'restorative',price:58.99,unit:'kit'},
      {id:'pd08',name:'Universal Composite Resin, A2 Shade Syringe',sku:'PD-RES-A2',cat:'restorative',price:45.99,unit:'each'},
      {id:'pd09',name:'Ultrasonic Cleaning Solution (1 gal)',sku:'PD-STR-ULT',cat:'sterilization',price:24.99,unit:'gallon'},
      {id:'pd10',name:'Autoclave Sterilization Pouches (200/bx)',sku:'PD-STR-POU',cat:'sterilization',price:21.49,unit:'box'},
      {id:'pd11',name:'Disposable Prophy Angles (144/bx)',sku:'PD-DIS-PRA',cat:'disposables',price:16.99,unit:'box'},
      {id:'pd12',name:'Cotton Rolls #2 (2000/cs)',sku:'PD-DIS-COT',cat:'disposables',price:21.49,unit:'case'},
      {id:'pd13',name:'Disposable Prophy Cups (144/bx)',sku:'PD-DIS-PCP',cat:'disposables',price:14.99,unit:'box'},
      {id:'pd14',name:'Dental Explorer, Single End',sku:'PD-INS-EXP',cat:'instruments',price:19.99,unit:'each'},
      {id:'pd15',name:'Composite Placement Instrument',sku:'PD-INS-CPI',cat:'instruments',price:27.99,unit:'each'},
      {id:'pd16',name:'Extraction Forceps, Universal Lower',sku:'PD-INS-EFL',cat:'instruments',price:89.99,unit:'each'},
      {id:'pd17',name:'Articaine 4% w/ Epi 1:100,000 (50 cartridges)',sku:'PD-ANE-ART',cat:'anesthetics',price:52.99,unit:'box'},
      {id:'pd18',name:'Topical Anesthetic Gel, Benzocaine 20%',sku:'PD-ANE-TOP',cat:'anesthetics',price:12.99,unit:'each'},
      {id:'pd19',name:'Patient Take-Home Toothbrushes (144/bx)',sku:'PD-PRV-TTB',cat:'preventive',price:22.99,unit:'box'}
    ]},
  benco:{name:'Benco Dental',website:'https://www.benco.com',
    desc:'Full-line dental distributor -- PPE, restoratives, sterilization/infection control, preventive supplies.',
    products:[
      {id:'bd01',name:'Nitrile Exam Gloves, Medium (100/bx)',sku:'BD-PPE-NGM',cat:'ppe',price:17.49,unit:'box'},
      {id:'bd02',name:'Level 3 Surgical Masks (50/bx)',sku:'BD-PPE-L3M',cat:'ppe',price:13.49,unit:'box'},
      {id:'bd03',name:'Disposable Isolation Gowns (10/pk)',sku:'BD-PPE-ISG',cat:'ppe',price:32.99,unit:'pack'},
      {id:'bd04',name:'Bite Registration Material, Fast Set',sku:'BD-IMP-BRF',cat:'impression',price:27.99,unit:'each'},
      {id:'bd05',name:'VPS Impression Material, Light Body (2 cartridges)',sku:'BD-IMP-VPL',cat:'impression',price:57.99,unit:'pack'},
      {id:'bd06',name:'Bonding Agent, Universal 5th Gen (5ml)',sku:'BD-RES-BND',cat:'restorative',price:61.99,unit:'each'},
      {id:'bd07',name:'Glass Ionomer Restorative Cement',sku:'BD-RES-GIC',cat:'restorative',price:55.99,unit:'kit'},
      {id:'bd08',name:'Surface Disinfectant Wipes (160ct)',sku:'BD-STR-WIP',cat:'sterilization',price:13.49,unit:'canister'},
      {id:'bd09',name:'Biological Spore Test Strips (25/pk)',sku:'BD-STR-SPR',cat:'sterilization',price:36.99,unit:'pack'},
      {id:'bd10',name:'Ultrasonic Cleaning Solution (1 gal)',sku:'BD-STR-ULT',cat:'sterilization',price:26.99,unit:'gallon'},
      {id:'bd11',name:'Paper Patient Bibs (500/cs)',sku:'BD-DIS-BIB',cat:'disposables',price:25.99,unit:'case'},
      {id:'bd12',name:'Saliva Ejectors (100/bx)',sku:'BD-DIS-SAL',cat:'disposables',price:9.49,unit:'box'},
      {id:'bd13',name:'Disposable Prophy Angles (144/bx)',sku:'BD-DIS-PRA',cat:'disposables',price:15.99,unit:'box'},
      {id:'bd14',name:'Periodontal Probe, UNC 15',sku:'BD-INS-PRB',cat:'instruments',price:22.99,unit:'each'},
      {id:'bd15',name:'Dental Explorer, Single End',sku:'BD-INS-EXP',cat:'instruments',price:21.99,unit:'each'},
      {id:'bd16',name:'Lidocaine 2% w/ Epi 1:100,000 (50 cartridges)',sku:'BD-ANE-LID',cat:'anesthetics',price:42.99,unit:'box'},
      {id:'bd17',name:'Fluoride Varnish, Single Dose (200/bx)',sku:'BD-PRV-FLV',cat:'preventive',price:47.99,unit:'box'},
      {id:'bd18',name:'Prophy Paste, Assorted Flavors (200/jar)',sku:'BD-PRV-PPY',cat:'preventive',price:30.99,unit:'jar'}
    ]},
  darby:{name:'Darby Dental Supply',website:'https://www.darbydental.com',
    desc:'Full-line dental distributor -- disposables, instruments, anesthetics, impression materials.',
    products:[
      {id:'dd01',name:'Nitrile Exam Gloves, Large (100/bx)',sku:'DD-PPE-NGL',cat:'ppe',price:19.99,unit:'box'},
      {id:'dd02',name:'N95 Respirator Masks (20/bx)',sku:'DD-PPE-N95',cat:'ppe',price:37.99,unit:'box'},
      {id:'dd03',name:'Full Face Shields (10/pk)',sku:'DD-PPE-FFS',cat:'ppe',price:26.99,unit:'pack'},
      {id:'dd04',name:'Fast-Set Alginate Impression Material (1lb)',sku:'DD-IMP-ALG',cat:'impression',price:17.49,unit:'each'},
      {id:'dd05',name:'VPS Impression Material, Heavy Body (2 cartridges)',sku:'DD-IMP-VPH',cat:'impression',price:54.99,unit:'pack'},
      {id:'dd06',name:'Universal Composite Resin, A3 Shade Syringe',sku:'DD-RES-A3',cat:'restorative',price:40.99,unit:'each'},
      {id:'dd07',name:'Autoclave Sterilization Pouches (200/bx)',sku:'DD-STR-POU',cat:'sterilization',price:23.99,unit:'box'},
      {id:'dd08',name:'Biological Spore Test Strips (25/pk)',sku:'DD-STR-SPR',cat:'sterilization',price:34.99,unit:'pack'},
      {id:'dd09',name:'Cotton Rolls #2 (2000/cs)',sku:'DD-DIS-COT',cat:'disposables',price:18.99,unit:'case'},
      {id:'dd10',name:'Disposable Prophy Cups (144/bx)',sku:'DD-DIS-PCP',cat:'disposables',price:13.99,unit:'box'},
      {id:'dd11',name:'Composite Placement Instrument',sku:'DD-INS-CPI',cat:'instruments',price:25.99,unit:'each'},
      {id:'dd12',name:'Extraction Forceps, Universal Lower',sku:'DD-INS-EFL',cat:'instruments',price:84.99,unit:'each'},
      {id:'dd13',name:'Articaine 4% w/ Epi 1:100,000 (50 cartridges)',sku:'DD-ANE-ART',cat:'anesthetics',price:49.99,unit:'box'},
      {id:'dd14',name:'Topical Anesthetic Gel, Benzocaine 20%',sku:'DD-ANE-TOP',cat:'anesthetics',price:11.99,unit:'each'},
      {id:'dd15',name:'Patient Take-Home Toothbrushes (144/bx)',sku:'DD-PRV-TTB',cat:'preventive',price:20.99,unit:'box'},
      {id:'dd16',name:'Prophy Paste, Assorted Flavors (200/jar)',sku:'DD-PRV-PPY',cat:'preventive',price:29.99,unit:'jar'}
    ]},
  burkhart:{name:'Burkhart Dental',website:'https://www.burkhartdental.com',
    desc:'Full-line dental distributor -- PPE, restoratives, sterilization, instruments, preventive supplies.',
    products:[
      {id:'bk01',name:'Level 3 Surgical Masks (50/bx)',sku:'BK-PPE-L3M',cat:'ppe',price:12.49,unit:'box'},
      {id:'bk02',name:'Disposable Isolation Gowns (10/pk)',sku:'BK-PPE-ISG',cat:'ppe',price:33.99,unit:'pack'},
      {id:'bk03',name:'Nitrile Exam Gloves, Small (100/bx)',sku:'BK-PPE-NGS',cat:'ppe',price:16.99,unit:'box'},
      {id:'bk04',name:'Bite Registration Material, Fast Set',sku:'BK-IMP-BRF',cat:'impression',price:28.99,unit:'each'},
      {id:'bk05',name:'VPS Impression Material, Light Body (2 cartridges)',sku:'BK-IMP-VPL',cat:'impression',price:53.99,unit:'pack'},
      {id:'bk06',name:'Glass Ionomer Restorative Cement',sku:'BK-RES-GIC',cat:'restorative',price:57.99,unit:'kit'},
      {id:'bk07',name:'Bonding Agent, Universal 5th Gen (5ml)',sku:'BK-RES-BND',cat:'restorative',price:59.99,unit:'each'},
      {id:'bk08',name:'Surface Disinfectant Wipes (160ct)',sku:'BK-STR-WIP',cat:'sterilization',price:15.49,unit:'canister'},
      {id:'bk09',name:'Ultrasonic Cleaning Solution (1 gal)',sku:'BK-STR-ULT',cat:'sterilization',price:23.99,unit:'gallon'},
      {id:'bk10',name:'Paper Patient Bibs (500/cs)',sku:'BK-DIS-BIB',cat:'disposables',price:26.99,unit:'case'},
      {id:'bk11',name:'Saliva Ejectors (100/bx)',sku:'BK-DIS-SAL',cat:'disposables',price:8.49,unit:'box'},
      {id:'bk12',name:'Periodontal Probe, UNC 15',sku:'BK-INS-PRB',cat:'instruments',price:23.99,unit:'each'},
      {id:'bk13',name:'Lidocaine 2% w/ Epi 1:100,000 (50 cartridges)',sku:'BK-ANE-LID',cat:'anesthetics',price:46.99,unit:'box'},
      {id:'bk14',name:'Fluoride Varnish, Single Dose (200/bx)',sku:'BK-PRV-FLV',cat:'preventive',price:48.99,unit:'box'},
      {id:'bk15',name:'Disposable Prophy Cups (144/bx)',sku:'BK-DIS-PCP',cat:'disposables',price:12.99,unit:'box'}
    ]}
};
var DNT_VCAT_LABELS={ppe:'PPE',impression:'Impression Materials',restorative:'Restorative Materials',
  sterilization:'Sterilization & Infection Control',disposables:'Disposables',instruments:'Instruments',
  anesthetics:'Anesthetics',preventive:'Preventive/Hygiene'};
var _dntActiveVendor='henryschein',_dntActiveCat='all';

function vendorCart(){return ld('dnt_vendor_cart',{});}
function vCartAdd(productId,qty){
  var cart=vendorCart();cart[productId]=(cart[productId]||0)+(parseInt(qty,10)||1);
  st('dnt_vendor_cart',cart);vRenderCart();
}
function vCartUpdate(productId,val){
  var cart=vendorCart(),qty=parseInt(val,10)||0;
  if(qty<=0)delete cart[productId];else cart[productId]=qty;
  st('dnt_vendor_cart',cart);vRenderCart();
}
function vCartClear(){st('dnt_vendor_cart',{});vRenderCart();rVendorCat();}

function vAllProducts(){
  var out=[];
  Object.keys(DNT_VENDORS).forEach(function(vk){
    DNT_VENDORS[vk].products.forEach(function(p){out.push(Object.assign({},p,{vendorKey:vk,vendorName:DNT_VENDORS[vk].name}));});
  });
  return out;
}

function vRenderCart(){
  var cart=vendorCart(),all=vAllProducts();
  var items=Object.keys(cart).map(function(id){var p=all.find(function(x){return x.id===id;});return p?Object.assign({},p,{qty:cart[id]}):null;}).filter(Boolean);
  var card=$('vendor-cart-card');
  if(!items.length){card.style.display='none';return;}
  card.style.display='block';
  var total=items.reduce(function(s,i){return s+i.price*i.qty;},0);
  $('vendor-cart-tbody').innerHTML=items.map(function(i){
    return '<tr><td>'+H(i.name)+' <span style="color:var(--muted);font-size:11px">('+H(i.vendorName)+')</span></td>'+
      '<td style="width:80px"><input type="number" min="0" value="'+i.qty+'" style="width:60px" onchange="vCartUpdate(\''+i.id+'\',this.value)"></td>'+
      '<td style="text-align:right">'+fmt(i.price*i.qty)+'</td></tr>';
  }).join('');
  $('vendor-cart-total').textContent='Total: '+fmt(total);
}

function vSetTab(vKey,btn){
  _dntActiveVendor=vKey;_dntActiveCat='all';
  document.querySelectorAll('#vendor-tabs button').forEach(function(b){b.className='btn bo bs';});
  btn.className='btn bp bs';
  rVendorCat();
}
function vCatSet(cat,btn){
  _dntActiveCat=cat;
  document.querySelectorAll('#vcat-tabs button').forEach(function(b){b.className='btn bo bs';});
  btn.className='btn bp bs';
  rVendorCat();
}

function rVendorCat(){
  var tabsEl=$('vendor-tabs');
  if(!tabsEl.dataset.built){
    tabsEl.innerHTML=Object.keys(DNT_VENDORS).map(function(vk){
      return '<button class="btn '+(vk===_dntActiveVendor?'bp':'bo')+' bs" onclick="vSetTab(\''+vk+'\',this)">'+H(DNT_VENDORS[vk].name)+'</button>';
    }).join('');
    tabsEl.dataset.built='1';
  }
  var catsEl=$('vcat-tabs');
  var cats=['all'].concat(Object.keys(DNT_VCAT_LABELS));
  catsEl.innerHTML=cats.map(function(c){
    return '<button class="btn '+(c===_dntActiveCat?'bp':'bo')+' bs" onclick="vCatSet(\''+c+'\',this)">'+H(c==='all'?'All':DNT_VCAT_LABELS[c])+'</button>';
  }).join('');

  var v=DNT_VENDORS[_dntActiveVendor];
  $('v-name').textContent=v.name;
  $('v-desc').textContent=v.desc;
  $('v-website').href=v.website;$('v-website').textContent=v.website.replace('https://www.','');
  vRenderContactBox();

  var products=v.products;
  if(_dntActiveCat!=='all')products=products.filter(function(p){return p.cat===_dntActiveCat;});
  var cart=vendorCart();
  var all=vAllProducts();
  $('vendor-products-tbody').innerHTML=products.length?products.map(function(p){
    var matches=all.filter(function(x){return x.vendorKey!==_dntActiveVendor&&x.name===p.name;});
    var lowest=matches.length?matches.sort(function(a,b){return a.price-b.price;})[0]:null;
    var badge='';
    if(lowest&&lowest.price<p.price)badge=' <span class="badge" style="background:#FEF3C7;color:#92400E">Save '+fmt(p.price-lowest.price)+' at '+H(lowest.vendorName)+'</span>';
    else if(lowest&&p.price<lowest.price)badge=' <span class="badge" style="background:#F0FEF6;color:#15803D">Best Price</span>';
    return '<tr><td>'+H(p.name)+badge+'<div style="font-size:11px;color:var(--muted)">'+H(DNT_VCAT_LABELS[p.cat])+' &middot; '+H(p.sku)+'</div></td>'+
      '<td>'+fmt(p.price)+'</td>'+
      '<td><input type="number" min="0" value="'+(cart[p.id]||0)+'" id="vqty-'+p.id+'" style="width:60px" onchange="vCartUpdate(\''+p.id+'\',this.value)"></td>'+
      '<td><button class="btn bp bs" onclick="vCartAdd(\''+p.id+'\',1)">Add</button></td></tr>';
  }).join('') : '<tr><td colspan="4" style="color:var(--muted);text-align:center">No products in this category from '+H(v.name)+'</td></tr>';
  vRenderCart();
}

function vRenderContactBox(){
  var contacts=ld('dnt_vendor_contacts',{});
  var c=contacts[_dntActiveVendor];
  var box=$('v-contact');
  if(c&&c.email){
    box.innerHTML='Rep: '+H(c.rep_name||'(no name on file)')+' &middot; '+H(c.phone||'')+' &middot; '+H(c.email)+
      ' <button class="btn bo bs" onclick="vEditContact()">Edit</button>';
  }else{
    box.innerHTML='<span style="color:var(--danger)">No rep contact on file yet.</span> <button class="btn bo bs" onclick="vEditContact()">Add rep contact</button>';
  }
}
function vEditContact(){
  var contacts=ld('dnt_vendor_contacts',{});
  var c=contacts[_dntActiveVendor]||{};
  var repName=prompt('Rep name:',c.rep_name||'');
  if(repName===null)return;
  var phone=prompt('Rep phone:',c.phone||'');
  if(phone===null)return;
  var email=prompt('Rep email:',c.email||'');
  if(email===null)return;
  contacts[_dntActiveVendor]={rep_name:repName.trim(),phone:phone.trim(),email:email.trim()};
  st('dnt_vendor_contacts',contacts);
  vRenderContactBox();
  toast('Contact saved for '+DNT_VENDORS[_dntActiveVendor].name);
}

function init(){
  rDash();
  rComplaintsBadge();
  fillDentalSelects();
  dntSyncFromServer();
}
```

- [ ] **Step 6: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 7: Manual verification (code trace — no live browser in this environment)**

Trace by reading the code: navigating to `vendorcat` calls `rVendorCat()`, which builds vendor tabs (5 real vendors) and category tabs (8 categories + All), renders Henry Schein's products by default, shows "No rep contact on file yet" with an Add button, and an empty cart (card hidden). Confirm `vSetTab('patterson', btn)` switches `_dntActiveVendor` and re-renders Patterson's products. Confirm a product with the SAME `name` on 2+ vendors (e.g. "Level 3 Surgical Masks (50/bx)" — Henry Schein $12.99, Patterson $11.49, Benco $13.49, Burkhart $12.49) shows a "Best Price"/"Save $X" badge correctly on each vendor's tab (Patterson should show "Best Price", the others should show "Save $X at Patterson Dental"). Confirm `vCartAdd('hs01',1)` then `vCartAdd('hs01',2)` results in `vendorCart()['hs01']===3` and the cart card becomes visible with the correct running total.

- [ ] **Step 8: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- vendor catalog data, browsing, cart (Task 1 of vendor/supply ordering)"
```

---

### Task 2: Vendor rep contact + Place Order

**Files:**
- Modify: `sairndental.html` (script section, immediately after Task 1's `vEditContact()`)

**Interfaces:**
- Consumes: `vendorCart()`, `DNT_VENDORS`, `vAllProducts()`, `vCartClear()` (Task 1).
- Produces: `vPlaceOrder()`, `vendorOrderHistory()`.
- Consumed by: Task 3 (stock auto-increment wired into `vPlaceOrder()`), Task 4 (order recording uses effective/negotiated price instead of catalog price), Task 5 (Spend Report reads `vendorOrderHistory()`).

- [ ] **Step 1: Add `vPlaceOrder()` and `vendorOrderHistory()`**

Find (the exact current end of `vEditContact()`, from Task 1):

```js
  contacts[_dntActiveVendor]={rep_name:repName.trim(),phone:phone.trim(),email:email.trim()};
  st('dnt_vendor_contacts',contacts);
  vRenderContactBox();
  toast('Contact saved for '+DNT_VENDORS[_dntActiveVendor].name);
}

function init(){
```

Replace with:

```js
  contacts[_dntActiveVendor]={rep_name:repName.trim(),phone:phone.trim(),email:email.trim()};
  st('dnt_vendor_contacts',contacts);
  vRenderContactBox();
  toast('Contact saved for '+DNT_VENDORS[_dntActiveVendor].name);
}

function vendorOrderHistory(){return ld('dnt_vendor_order_history',[]);}

function vPlaceOrder(){
  var cart=vendorCart();
  var all=vAllProducts();
  var items=Object.keys(cart).map(function(id){var p=all.find(function(x){return x.id===id;});return p?Object.assign({},p,{qty:cart[id]}):null;}).filter(Boolean);
  if(!items.length){toast('Cart is empty. Add items first.');return;}
  // Every item's vendor must have a rep email on file -- Place Order sends
  // one email per vendor represented in the cart, never a mailto: to
  // nobody (see design spec's "Vendor contact info" section).
  var contacts=ld('dnt_vendor_contacts',{});
  var vendorKeysInCart=Array.from(new Set(items.map(function(i){return i.vendorKey;})));
  var missing=vendorKeysInCart.filter(function(vk){return !(contacts[vk]&&contacts[vk].email);});
  if(missing.length){
    toast('Add rep contact info for '+missing.map(function(vk){return DNT_VENDORS[vk].name;}).join(', ')+' before placing this order');
    return;
  }
  vendorKeysInCart.forEach(function(vk){
    var vendorItems=items.filter(function(i){return i.vendorKey===vk;});
    var total=vendorItems.reduce(function(s,i){return s+i.price*i.qty;},0);
    var orderText=vendorItems.map(function(i){return i.qty+'x '+i.name+' ('+i.sku+') @ '+fmt(i.price)+' = '+fmt(i.price*i.qty);}).join('\n');
    var subject='SAIRNdental Purchase Order -- '+fmt(total);
    var body='Purchase Order\n\nDate: '+new Date().toLocaleDateString()+'\n\nItems:\n'+orderText+'\n\nTotal: '+fmt(total);
    var email=contacts[vk].email;
    window.open('mailto:'+email+'?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body),'_blank');
    var order={id:newId('VORD'),date:new Date().toISOString(),vendor:DNT_VENDORS[vk].name,vendorKey:vk,items:vendorItems,total:total};
    var hist=vendorOrderHistory();hist.unshift(order);
    if(hist.length>200)hist=hist.slice(0,200);
    st('dnt_vendor_order_history',hist);
  });
  vCartClear();
  toast('Order'+(vendorKeysInCart.length>1?'s':'')+' submitted');
}

function init(){
```

- [ ] **Step 2: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 3: Manual verification (code trace)**

Trace: with an empty cart, `vPlaceOrder()` shows "Cart is empty." and returns before touching `dnt_vendor_order_history`. With items in the cart but no contact set for that vendor, confirm the toast names the missing vendor(s) and no `mailto:`/history write happens (return before `vendorKeysInCart.forEach`). With a contact set (via `vEditContact()`), confirm a `mailto:` window opens with the correct itemized subject/body, an entry is pushed to `dnt_vendor_order_history`, and the cart is cleared (`vendorCart()` returns `{}` after). With items from 2 different vendors in the cart (both contacts set), confirm 2 separate `mailto:` opens and 2 separate history entries, one per vendor.

- [ ] **Step 4: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- vendor rep contact + Place Order, blocked without contact info (Task 2)"
```

---

### Task 3: Supplies panel — stock tracking, low-stock cross-reference, order-time stock update

**Files:**
- Modify: `sairndental.html` (sidebar ~L233-234 from Task 1, panel container after `panel-vendorcat` from Task 1, `nav()`, script section)

**Interfaces:**
- Consumes: Task 1's `rVendorCat()`/product rendering (adds low-stock badge), Task 2's `vPlaceOrder()` (adds stock auto-increment).
- Produces: `supplies()`, `rSupplies()`, `addSupply()`, `removeSupply()`, `vLowStockItem(sku)`.
- Consumed by: Task 5 (Spend Report's low-stock KPI).

- [ ] **Step 1: Add the sidebar Supplies entry's target and Vendor Catalog panel's follow-on panel**

Find (Task 1's `panel-vendorcat` closing, before the modal):

```html
        <div class="card" id="vendor-cart-card" style="display:none"><div class="ch"><div class="ct">Your Cart</div></div><div class="cb">
          <table><tbody id="vendor-cart-tbody"></tbody></table>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
            <span style="font-size:15px;font-weight:800" id="vendor-cart-total">Total: $0.00</span>
            <button class="btn bp" onclick="vPlaceOrder()">Place Order</button>
          </div>
        </div></div>
      </div>

      <div class="modal" id="completeVisitModal">
```

Replace with:

```html
        <div class="card" id="vendor-cart-card" style="display:none"><div class="ch"><div class="ct">Your Cart</div></div><div class="cb">
          <table><tbody id="vendor-cart-tbody"></tbody></table>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
            <span style="font-size:15px;font-weight:800" id="vendor-cart-total">Total: $0.00</span>
            <button class="btn bp" onclick="vPlaceOrder()">Place Order</button>
          </div>
        </div></div>
      </div>

      <div class="panel" id="panel-supplies">
        <div class="ph"><div><div class="ptitle">Supplies</div><div class="psub">Stock on hand for dental supplies/PPE/materials.</div></div>
          <div class="pa"><button class="btn bo bs" onclick="exportPanelCSV('panel-supplies','supplies')">Export CSV</button></div>
        </div>
        <div class="krow" id="supplies-kpis" style="grid-template-columns:repeat(3,1fr)"></div>
        <div class="card"><div class="ch"><div class="ct">Add Supply Item</div></div><div class="cb">
          <div class="fr">
            <div class="fg"><label>Name</label><input type="text" id="sp-add-name" placeholder="e.g. Nitrile Exam Gloves, Medium"></div>
            <div class="fg"><label>Category</label><select id="sp-add-category"></select></div>
          </div>
          <div class="fr">
            <div class="fg"><label>Quantity on Hand</label><input type="number" id="sp-add-qty" min="0" value="0"></div>
            <div class="fg"><label>Reorder Threshold</label><input type="number" id="sp-add-threshold" min="0" value="0"></div>
          </div>
          <div class="fr">
            <div class="fg"><label>Unit Cost</label><input type="number" id="sp-add-cost" min="0" step="0.01"></div>
            <div class="fg"><label>Vendor SKU (optional, for low-stock matching in Vendor Catalog)</label><input type="text" id="sp-add-sku" placeholder="e.g. HS-PPE-NGM"></div>
          </div>
          <button class="btn bp" onclick="addSupply()">Add Item</button>
        </div></div>
        <div class="card"><div class="ch"><div class="ct">On Hand</div></div><div class="cb" style="padding:0">
          <table><thead><tr><th>Name</th><th>Category</th><th>Qty</th><th>Reorder At</th><th>Unit Cost</th><th></th></tr></thead><tbody id="supplies-tbody"></tbody></table>
        </div></div>
      </div>

      <div class="modal" id="completeVisitModal">
```

- [ ] **Step 2: Add sidebar Supplies target (it already exists from Task 1 — confirm, don't duplicate)**

Task 1's Step 1 already added `<button class="sb" id="sb-supplies" onclick="nav('supplies')">`. No further sidebar change needed here — skip to Step 3.

- [ ] **Step 3: Add `nav()` dispatch entry**

Find (the exact current end of `nav()`, after Task 1's Step 4):

```js
  if(id==='referrals')rReferrals();
  if(id==='complaints')rComplaints();
  if(id==='vendorcat')rVendorCat();
}
```

Replace with:

```js
  if(id==='referrals')rReferrals();
  if(id==='complaints')rComplaints();
  if(id==='vendorcat')rVendorCat();
  if(id==='supplies')rSupplies();
}
```

- [ ] **Step 4: Add Supplies data/render functions, and wire low-stock badge + order-time stock update**

Find (the exact current `vendorOrderHistory()`/`vPlaceOrder()` block from Task 2, through its closing brace):

```js
function vendorOrderHistory(){return ld('dnt_vendor_order_history',[]);}

function vPlaceOrder(){
  var cart=vendorCart();
  var all=vAllProducts();
  var items=Object.keys(cart).map(function(id){var p=all.find(function(x){return x.id===id;});return p?Object.assign({},p,{qty:cart[id]}):null;}).filter(Boolean);
  if(!items.length){toast('Cart is empty. Add items first.');return;}
  // Every item's vendor must have a rep email on file -- Place Order sends
  // one email per vendor represented in the cart, never a mailto: to
  // nobody (see design spec's "Vendor contact info" section).
  var contacts=ld('dnt_vendor_contacts',{});
  var vendorKeysInCart=Array.from(new Set(items.map(function(i){return i.vendorKey;})));
  var missing=vendorKeysInCart.filter(function(vk){return !(contacts[vk]&&contacts[vk].email);});
  if(missing.length){
    toast('Add rep contact info for '+missing.map(function(vk){return DNT_VENDORS[vk].name;}).join(', ')+' before placing this order');
    return;
  }
  vendorKeysInCart.forEach(function(vk){
    var vendorItems=items.filter(function(i){return i.vendorKey===vk;});
    var total=vendorItems.reduce(function(s,i){return s+i.price*i.qty;},0);
    var orderText=vendorItems.map(function(i){return i.qty+'x '+i.name+' ('+i.sku+') @ '+fmt(i.price)+' = '+fmt(i.price*i.qty);}).join('\n');
    var subject='SAIRNdental Purchase Order -- '+fmt(total);
    var body='Purchase Order\n\nDate: '+new Date().toLocaleDateString()+'\n\nItems:\n'+orderText+'\n\nTotal: '+fmt(total);
    var email=contacts[vk].email;
    window.open('mailto:'+email+'?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body),'_blank');
    var order={id:newId('VORD'),date:new Date().toISOString(),vendor:DNT_VENDORS[vk].name,vendorKey:vk,items:vendorItems,total:total};
    var hist=vendorOrderHistory();hist.unshift(order);
    if(hist.length>200)hist=hist.slice(0,200);
    st('dnt_vendor_order_history',hist);
  });
  vCartClear();
  toast('Order'+(vendorKeysInCart.length>1?'s':'')+' submitted');
}
```

Replace with:

```js
function vendorOrderHistory(){return ld('dnt_vendor_order_history',[]);}

function supplies(){return ld('dnt_supplies_list',[]);}
function vLowStockItem(sku){
  if(!sku)return null;
  return supplies().find(function(s){return s.vendor_sku&&s.vendor_sku===sku&&Number(s.qty)<=Number(s.reorder_threshold);})||null;
}
function rSupplies(){
  var sel=$('sp-add-category');
  if(sel&&!sel.dataset.built){
    sel.innerHTML=Object.keys(DNT_VCAT_LABELS).map(function(c){return '<option value="'+c+'">'+H(DNT_VCAT_LABELS[c])+'</option>';}).join('');
    sel.dataset.built='1';
  }
  var list=supplies();
  var low=list.filter(function(s){return Number(s.qty)<=Number(s.reorder_threshold);});
  var value=list.reduce(function(s,i){return s+Number(i.qty)*Number(i.unit_cost||0);},0);
  $('supplies-kpis').innerHTML=
    '<div class="kpi"><div class="klbl">SKUs Tracked</div><div class="kval">'+list.length+'</div></div>'+
    '<div class="kpi"><div class="klbl">Low Stock</div><div class="kval" style="color:'+(low.length?'var(--danger)':'var(--text)')+'">'+low.length+'</div></div>'+
    '<div class="kpi"><div class="klbl">Stock Value</div><div class="kval">'+fmt(value)+'</div></div>';
  $('supplies-tbody').innerHTML=list.length?list.map(function(s){
    var isLow=Number(s.qty)<=Number(s.reorder_threshold);
    return '<tr><td>'+H(s.name)+(isLow?' <span class="badge" style="background:#FEE2E2;color:#991B1B">Low</span>':'')+'</td>'+
      '<td>'+H(DNT_VCAT_LABELS[s.category]||s.category)+'</td><td>'+H(s.qty)+'</td><td>'+H(s.reorder_threshold)+'</td>'+
      '<td>'+fmt(s.unit_cost)+'</td>'+
      '<td><button class="btn bo bs" onclick="removeSupply(\''+s.id+'\')">Remove</button></td></tr>';
  }).join('') : '<tr><td colspan="6" style="color:var(--muted);text-align:center">No supply items on file yet</td></tr>';
}
function addSupply(){
  var name=$('sp-add-name').value.trim();
  if(!name){toast('Item name required');return;}
  var rec={id:newId('SUP'),name:name,category:$('sp-add-category').value,
    qty:parseInt($('sp-add-qty').value,10)||0,reorder_threshold:parseInt($('sp-add-threshold').value,10)||0,
    unit_cost:parseFloat($('sp-add-cost').value)||0,vendor_sku:$('sp-add-sku').value.trim(),
    created_at:dntLocalToday()};
  var list=supplies();list.push(rec);st('dnt_supplies_list',list);
  rSupplies();
  ['sp-add-name','sp-add-qty','sp-add-threshold','sp-add-cost','sp-add-sku'].forEach(function(id){$(id).value=id==='sp-add-qty'||id==='sp-add-threshold'?'0':'';});
  toast('Supply item added');
}
function removeSupply(id){
  var list=supplies().filter(function(s){return s.id!==id;});
  st('dnt_supplies_list',list);rSupplies();
  toast('Supply item removed');
}

function vPlaceOrder(){
  var cart=vendorCart();
  var all=vAllProducts();
  var items=Object.keys(cart).map(function(id){var p=all.find(function(x){return x.id===id;});return p?Object.assign({},p,{qty:cart[id]}):null;}).filter(Boolean);
  if(!items.length){toast('Cart is empty. Add items first.');return;}
  // Every item's vendor must have a rep email on file -- Place Order sends
  // one email per vendor represented in the cart, never a mailto: to
  // nobody (see design spec's "Vendor contact info" section).
  var contacts=ld('dnt_vendor_contacts',{});
  var vendorKeysInCart=Array.from(new Set(items.map(function(i){return i.vendorKey;})));
  var missing=vendorKeysInCart.filter(function(vk){return !(contacts[vk]&&contacts[vk].email);});
  if(missing.length){
    toast('Add rep contact info for '+missing.map(function(vk){return DNT_VENDORS[vk].name;}).join(', ')+' before placing this order');
    return;
  }
  vendorKeysInCart.forEach(function(vk){
    var vendorItems=items.filter(function(i){return i.vendorKey===vk;});
    var total=vendorItems.reduce(function(s,i){return s+i.price*i.qty;},0);
    var orderText=vendorItems.map(function(i){return i.qty+'x '+i.name+' ('+i.sku+') @ '+fmt(i.price)+' = '+fmt(i.price*i.qty);}).join('\n');
    var subject='SAIRNdental Purchase Order -- '+fmt(total);
    var body='Purchase Order\n\nDate: '+new Date().toLocaleDateString()+'\n\nItems:\n'+orderText+'\n\nTotal: '+fmt(total);
    var email=contacts[vk].email;
    window.open('mailto:'+email+'?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body),'_blank');
    var order={id:newId('VORD'),date:new Date().toISOString(),vendor:DNT_VENDORS[vk].name,vendorKey:vk,items:vendorItems,total:total};
    var hist=vendorOrderHistory();hist.unshift(order);
    if(hist.length>200)hist=hist.slice(0,200);
    st('dnt_vendor_order_history',hist);
  });
  // Stock auto-increment, confirm-prompted -- matches StoneDesk's real
  // vendorPlaceOrder() convention exactly (design spec's "Supplies panel"
  // section). Matches by vendor_sku against the ordered items' real SKUs.
  if(confirm('Order submitted! Update supply quantities to reflect ordered amounts?')){
    var list=supplies();
    items.forEach(function(item){
      var s=list.find(function(x){return x.vendor_sku===item.sku;});
      if(s)s.qty=Number(s.qty)+item.qty;
    });
    st('dnt_supplies_list',list);
    if($('panel-supplies')&&$('panel-supplies').classList.contains('on'))rSupplies();
  }
  vCartClear();
  toast('Order'+(vendorKeysInCart.length>1?'s':'')+' submitted');
}
```

- [ ] **Step 5: Add the low-stock badge to Vendor Catalog's product rendering**

Find (the exact current product-row line from `rVendorCat()`, Task 1):

```js
    return '<tr><td>'+H(p.name)+badge+'<div style="font-size:11px;color:var(--muted)">'+H(DNT_VCAT_LABELS[p.cat])+' &middot; '+H(p.sku)+'</div></td>'+
      '<td>'+fmt(p.price)+'</td>'+
      '<td><input type="number" min="0" value="'+(cart[p.id]||0)+'" id="vqty-'+p.id+'" style="width:60px" onchange="vCartUpdate(\''+p.id+'\',this.value)"></td>'+
      '<td><button class="btn bp bs" onclick="vCartAdd(\''+p.id+'\',1)">Add</button></td></tr>';
```

Replace with:

```js
    var lowFlag=vLowStockItem(p.sku)?' <span class="badge" style="background:#FEE2E2;color:#991B1B">Low Stock</span>':'';
    return '<tr><td>'+H(p.name)+badge+lowFlag+'<div style="font-size:11px;color:var(--muted)">'+H(DNT_VCAT_LABELS[p.cat])+' &middot; '+H(p.sku)+'</div></td>'+
      '<td>'+fmt(p.price)+'</td>'+
      '<td><input type="number" min="0" value="'+(cart[p.id]||0)+'" id="vqty-'+p.id+'" style="width:60px" onchange="vCartUpdate(\''+p.id+'\',this.value)"></td>'+
      '<td><button class="btn bp bs" onclick="vCartAdd(\''+p.id+'\',1)">Add</button></td></tr>';
```

- [ ] **Step 6: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 7: Manual verification (code trace)**

Trace: `addSupply()` with name "Nitrile Exam Gloves, Medium", qty 5, reorder threshold 10, vendor_sku "HS-PPE-NGM" — confirm it's low stock (5 <= 10), the KPI row shows Low Stock: 1, the table row shows the "Low" badge. Navigate to Vendor Catalog, Henry Schein tab — confirm the matching product (`hs02`, same SKU) shows the "Low Stock" badge. Add that product to cart and place an order (with a rep contact on file) — confirm the confirm-prompt fires, accepting it increments the supply item's `qty` (5 + ordered qty), and after the increment the item may no longer be low-stock if it crosses the threshold — confirm `rSupplies()`/`rVendorCat()` reflect the new state.

- [ ] **Step 8: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- Supplies panel, low-stock cross-reference, order-time stock update (Task 3)"
```

---

### Task 4: Negotiated pricing (3-tier)

**Files:**
- Modify: `sairndental.html` (Vendor Catalog panel HTML, script section)

**Interfaces:**
- Consumes: `DNT_VENDORS` (Task 1).
- Produces: `dntVendorPricingRules()`, `vGetEffectivePrice(vendorKey, product)`, `vSetVendorDiscount()`, `vSetCategoryDiscount()`, `vSetProductOverride()`.
- Consumed by: Task 5 (Spend Report's savings/deals KPIs), and this task itself rewires Task 1's price display and Task 2's order-total calculation to use effective price instead of raw catalog price.

- [ ] **Step 1: Add a Pricing Rules card to the Vendor Catalog panel**

Find (the exact current end of the vendor info card, before the products table, from Task 1):

```html
          <div style="font-size:12px;color:var(--muted)" id="v-desc"></div>
          <div style="font-size:12px;margin-top:8px" id="v-contact"></div>
        </div></div>
        <div class="card"><div class="cb" style="padding:0">
          <table><thead><tr><th>Product</th><th>Price</th><th>Qty</th><th></th></tr></thead><tbody id="vendor-products-tbody"></tbody></table>
        </div></div>
```

Replace with:

```html
          <div style="font-size:12px;color:var(--muted)" id="v-desc"></div>
          <div style="font-size:12px;margin-top:8px" id="v-contact"></div>
        </div></div>
        <div class="card"><div class="ch"><div class="ct">Negotiated Pricing</div></div><div class="cb">
          <div class="fr">
            <div class="fg"><label>Vendor Discount %</label><input type="number" id="vp-vendor-discount" min="0" max="100" step="0.1"></div>
            <div class="fg"><label>&nbsp;</label><button class="btn bo bs" onclick="vSetVendorDiscount()">Set</button></div>
          </div>
          <div class="fr">
            <div class="fg"><label>Category</label><select id="vp-cat-select"></select></div>
            <div class="fg"><label>Category Discount %</label><input type="number" id="vp-cat-discount" min="0" max="100" step="0.1"></div>
          </div>
          <button class="btn bo bs" onclick="vSetCategoryDiscount()">Set Category Discount</button>
          <div class="fr" style="margin-top:10px">
            <div class="fg"><label>Product SKU</label><input type="text" id="vp-sku" placeholder="e.g. HS-PPE-NGM"></div>
            <div class="fg"><label>Override Price</label><input type="number" id="vp-override-price" min="0" step="0.01"></div>
          </div>
          <button class="btn bo bs" onclick="vSetProductOverride()">Set Product Override</button>
        </div></div>
        <div class="card"><div class="cb" style="padding:0">
          <table><thead><tr><th>Product</th><th>Price</th><th>Qty</th><th></th></tr></thead><tbody id="vendor-products-tbody"></tbody></table>
        </div></div>
```

- [ ] **Step 2: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 3: Add pricing-rules data/logic, and rewire price display + cart/order totals to use effective price**

Find (the exact current `vAllProducts()` function, from Task 1):

```js
function vAllProducts(){
  var out=[];
  Object.keys(DNT_VENDORS).forEach(function(vk){
    DNT_VENDORS[vk].products.forEach(function(p){out.push(Object.assign({},p,{vendorKey:vk,vendorName:DNT_VENDORS[vk].name}));});
  });
  return out;
}
```

Replace with:

```js
function dntVendorPricingRules(){return ld('dnt_vendor_pricing_rules',{vendorDiscounts:{},categoryDiscounts:[],productOverrides:{}});}

// 3-tier: product override wins outright; otherwise vendor discount applies
// first, then category discount stacks on the already-discounted price --
// same order StoneDesk's sdGetEffectivePrice() uses.
function vGetEffectivePrice(vendorKey,product){
  var rules=dntVendorPricingRules();
  if(rules.productOverrides[product.sku]!==undefined)return rules.productOverrides[product.sku];
  var vendorDisc=(rules.vendorDiscounts[vendorKey]||0)/100;
  var catRule=rules.categoryDiscounts.find(function(r){return r.vendor===vendorKey&&r.category===product.cat;});
  var catDisc=catRule?(catRule.discount/100):0;
  var afterVendor=product.price*(1-vendorDisc);
  return afterVendor*(1-catDisc);
}
function vSetVendorDiscount(){
  var pct=parseFloat($('vp-vendor-discount').value);
  if(isNaN(pct)||pct<0||pct>100){toast('Enter a discount between 0 and 100');return;}
  var rules=dntVendorPricingRules();
  rules.vendorDiscounts[_dntActiveVendor]=pct;
  st('dnt_vendor_pricing_rules',rules);
  rVendorCat();
  toast(DNT_VENDORS[_dntActiveVendor].name+' vendor discount set to '+pct+'%');
}
function vSetCategoryDiscount(){
  var cat=$('vp-cat-select').value,pct=parseFloat($('vp-cat-discount').value);
  if(isNaN(pct)||pct<0||pct>100){toast('Enter a discount between 0 and 100');return;}
  var rules=dntVendorPricingRules();
  rules.categoryDiscounts=rules.categoryDiscounts.filter(function(r){return !(r.vendor===_dntActiveVendor&&r.category===cat);});
  rules.categoryDiscounts.push({vendor:_dntActiveVendor,category:cat,discount:pct});
  st('dnt_vendor_pricing_rules',rules);
  rVendorCat();
  toast(DNT_VCAT_LABELS[cat]+' discount set to '+pct+'% for '+DNT_VENDORS[_dntActiveVendor].name);
}
function vSetProductOverride(){
  var sku=$('vp-sku').value.trim(),price=parseFloat($('vp-override-price').value);
  if(!sku||isNaN(price)||price<0){toast('Enter a real SKU and a valid price');return;}
  var rules=dntVendorPricingRules();
  rules.productOverrides[sku]=price;
  st('dnt_vendor_pricing_rules',rules);
  rVendorCat();
  toast('Price override set for '+sku);
}

function vAllProducts(){
  var out=[];
  Object.keys(DNT_VENDORS).forEach(function(vk){
    DNT_VENDORS[vk].products.forEach(function(p){out.push(Object.assign({},p,{vendorKey:vk,vendorName:DNT_VENDORS[vk].name,effectivePrice:vGetEffectivePrice(vk,p)}));});
  });
  return out;
}
```

- [ ] **Step 4: Use `effectivePrice` in cart rendering, product rendering, and order totals**

Find (the exact current cart-item line total in `vRenderCart()`, from Task 1):

```js
  $('vendor-cart-tbody').innerHTML=items.map(function(i){
    return '<tr><td>'+H(i.name)+' <span style="color:var(--muted);font-size:11px">('+H(i.vendorName)+')</span></td>'+
      '<td style="width:80px"><input type="number" min="0" value="'+i.qty+'" style="width:60px" onchange="vCartUpdate(\''+i.id+'\',this.value)"></td>'+
      '<td style="text-align:right">'+fmt(i.price*i.qty)+'</td></tr>';
  }).join('');
  $('vendor-cart-total').textContent='Total: '+fmt(total);
```

Replace with:

```js
  $('vendor-cart-tbody').innerHTML=items.map(function(i){
    return '<tr><td>'+H(i.name)+' <span style="color:var(--muted);font-size:11px">('+H(i.vendorName)+')</span></td>'+
      '<td style="width:80px"><input type="number" min="0" value="'+i.qty+'" style="width:60px" onchange="vCartUpdate(\''+i.id+'\',this.value)"></td>'+
      '<td style="text-align:right">'+fmt(i.effectivePrice*i.qty)+'</td></tr>';
  }).join('');
  $('vendor-cart-total').textContent='Total: '+fmt(total);
```

Find (the exact current cart total computation, immediately above that block in `vRenderCart()`):

```js
  var card=$('vendor-cart-card');
  if(!items.length){card.style.display='none';return;}
  card.style.display='block';
  var total=items.reduce(function(s,i){return s+i.price*i.qty;},0);
```

Replace with:

```js
  var card=$('vendor-cart-card');
  if(!items.length){card.style.display='none';return;}
  card.style.display='block';
  var total=items.reduce(function(s,i){return s+i.effectivePrice*i.qty;},0);
```

Find (the exact current product-row price cell, from Task 3's Step 5 output):

```js
    var lowFlag=vLowStockItem(p.sku)?' <span class="badge" style="background:#FEE2E2;color:#991B1B">Low Stock</span>':'';
    return '<tr><td>'+H(p.name)+badge+lowFlag+'<div style="font-size:11px;color:var(--muted)">'+H(DNT_VCAT_LABELS[p.cat])+' &middot; '+H(p.sku)+'</div></td>'+
      '<td>'+fmt(p.price)+'</td>'+
      '<td><input type="number" min="0" value="'+(cart[p.id]||0)+'" id="vqty-'+p.id+'" style="width:60px" onchange="vCartUpdate(\''+p.id+'\',this.value)"></td>'+
      '<td><button class="btn bp bs" onclick="vCartAdd(\''+p.id+'\',1)">Add</button></td></tr>';
```

Replace with:

```js
    var lowFlag=vLowStockItem(p.sku)?' <span class="badge" style="background:#FEE2E2;color:#991B1B">Low Stock</span>':'';
    var eff=vGetEffectivePrice(_dntActiveVendor,p);
    var priceCell=eff<p.price?('<span style="text-decoration:line-through;color:var(--muted);font-size:11px">'+fmt(p.price)+'</span> '+fmt(eff)):fmt(p.price);
    return '<tr><td>'+H(p.name)+badge+lowFlag+'<div style="font-size:11px;color:var(--muted)">'+H(DNT_VCAT_LABELS[p.cat])+' &middot; '+H(p.sku)+'</div></td>'+
      '<td>'+priceCell+'</td>'+
      '<td><input type="number" min="0" value="'+(cart[p.id]||0)+'" id="vqty-'+p.id+'" style="width:60px" onchange="vCartUpdate(\''+p.id+'\',this.value)"></td>'+
      '<td><button class="btn bp bs" onclick="vCartAdd(\''+p.id+'\',1)">Add</button></td></tr>';
```

Find (the exact current order-total computation in `vPlaceOrder()`, from Task 2/3):

```js
  vendorKeysInCart.forEach(function(vk){
    var vendorItems=items.filter(function(i){return i.vendorKey===vk;});
    var total=vendorItems.reduce(function(s,i){return s+i.price*i.qty;},0);
    var orderText=vendorItems.map(function(i){return i.qty+'x '+i.name+' ('+i.sku+') @ '+fmt(i.price)+' = '+fmt(i.price*i.qty);}).join('\n');
```

Replace with:

```js
  vendorKeysInCart.forEach(function(vk){
    var vendorItems=items.filter(function(i){return i.vendorKey===vk;});
    var total=vendorItems.reduce(function(s,i){return s+i.effectivePrice*i.qty;},0);
    var orderText=vendorItems.map(function(i){return i.qty+'x '+i.name+' ('+i.sku+') @ '+fmt(i.effectivePrice)+' = '+fmt(i.effectivePrice*i.qty);}).join('\n');
```

- [ ] **Step 5: Populate the category `<select>` used by `vSetCategoryDiscount()`**

Find (the exact current `rVendorCat()` start, the vendor-tabs-building block, from Task 1):

```js
function rVendorCat(){
  var tabsEl=$('vendor-tabs');
  if(!tabsEl.dataset.built){
```

Replace with:

```js
function rVendorCat(){
  var pcSel=$('vp-cat-select');
  if(pcSel&&!pcSel.dataset.built){
    pcSel.innerHTML=Object.keys(DNT_VCAT_LABELS).map(function(c){return '<option value="'+c+'">'+H(DNT_VCAT_LABELS[c])+'</option>';}).join('');
    pcSel.dataset.built='1';
  }
  var tabsEl=$('vendor-tabs');
  if(!tabsEl.dataset.built){
```

- [ ] **Step 6: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 7: Manual verification (code trace)**

Trace: `vSetVendorDiscount()` with Henry Schein active and 10 entered — confirm `dntVendorPricingRules().vendorDiscounts.henryschein===10`, and `vGetEffectivePrice('henryschein', hs01)` returns `12.99*0.9=11.691`. `vSetCategoryDiscount()` with category `ppe` and 5 entered while Henry Schein is active — confirm the rule is added, and `vGetEffectivePrice('henryschein', hs01)` now returns `12.99*0.9*0.95` (vendor first, then category stacks — matches the stated stacking order). `vSetProductOverride()` with SKU `HS-PPE-L3M` and price `9.99` — confirm `vGetEffectivePrice('henryschein', hs01)` returns exactly `9.99`, ignoring both discounts (override wins outright). Confirm the product row shows a struck-through catalog price next to the discounted price whenever `eff<p.price`. Confirm `vPlaceOrder()`'s recorded order total and `mailto:` body use `effectivePrice`, not raw `price`.

- [ ] **Step 8: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- 3-tier negotiated pricing (vendor/category/product), wired into display and order totals (Task 4)"
```

---

### Task 5: AI Compare, Spend Report, Claude Spend Analysis

**Files:**
- Modify: `sairndental.html` (Vendor Catalog panel HTML, script section)

**Interfaces:**
- Consumes: `vendorOrderHistory()` (Task 2), `dntVendorPricingRules()` (Task 4), `supplies()`/low-stock computation (Task 3), `PROXY`/`APP_ID`/`dntAiError()` (existing app globals).
- Produces: `vCompareAI(productId)`, `vShowSpendReport()`, `vSpendAI()`.

- [ ] **Step 1: Add the AI Compare button to each product row**

Find (the exact current product-row Add button, from Task 4's Step 4 output):

```js
      '<td><input type="number" min="0" value="'+(cart[p.id]||0)+'" id="vqty-'+p.id+'" style="width:60px" onchange="vCartUpdate(\''+p.id+'\',this.value)"></td>'+
      '<td><button class="btn bp bs" onclick="vCartAdd(\''+p.id+'\',1)">Add</button></td></tr>';
```

Replace with:

```js
      '<td><input type="number" min="0" value="'+(cart[p.id]||0)+'" id="vqty-'+p.id+'" style="width:60px" onchange="vCartUpdate(\''+p.id+'\',this.value)"></td>'+
      '<td><button class="btn bo bs" onclick="vCompareAI(\''+p.id+'\')">Compare</button> <button class="btn bp bs" onclick="vCartAdd(\''+p.id+'\',1)">Add</button></td></tr>';
```

- [ ] **Step 2: Add the Spend Report modal HTML, after the Vendor Catalog panel**

Find (the exact current end of `panel-vendorcat`, before `panel-supplies`, from Task 3):

```html
        <div class="card" id="vendor-cart-card" style="display:none"><div class="ch"><div class="ct">Your Cart</div></div><div class="cb">
          <table><tbody id="vendor-cart-tbody"></tbody></table>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
            <span style="font-size:15px;font-weight:800" id="vendor-cart-total">Total: $0.00</span>
            <button class="btn bp" onclick="vPlaceOrder()">Place Order</button>
          </div>
        </div></div>
      </div>

      <div class="panel" id="panel-supplies">
```

Replace with:

```html
        <div class="card" id="vendor-cart-card" style="display:none"><div class="ch"><div class="ct">Your Cart</div></div><div class="cb">
          <table><tbody id="vendor-cart-tbody"></tbody></table>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
            <span style="font-size:15px;font-weight:800" id="vendor-cart-total">Total: $0.00</span>
            <button class="btn bp" onclick="vPlaceOrder()">Place Order</button>
          </div>
        </div></div>
      </div>

      <div class="modal" id="vendorSpendModal">
        <div class="mbox">
          <div class="mtitle">Vendor Spend Report</div>
          <div id="vendor-spend-content"></div>
          <button class="btn bo" style="margin-top:12px" onclick="$('vendorSpendModal').classList.remove('on')">Close</button>
        </div>
      </div>

      <div class="panel" id="panel-supplies">
```

- [ ] **Step 3: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 4: Add `vCompareAI()`, `vShowSpendReport()`, `vSpendAI()`**

Find (the exact current end of `vSetProductOverride()`, from Task 4):

```js
function vSetProductOverride(){
  var sku=$('vp-sku').value.trim(),price=parseFloat($('vp-override-price').value);
  if(!sku||isNaN(price)||price<0){toast('Enter a real SKU and a valid price');return;}
  var rules=dntVendorPricingRules();
  rules.productOverrides[sku]=price;
  st('dnt_vendor_pricing_rules',rules);
  rVendorCat();
  toast('Price override set for '+sku);
}
```

Replace with:

```js
function vSetProductOverride(){
  var sku=$('vp-sku').value.trim(),price=parseFloat($('vp-override-price').value);
  if(!sku||isNaN(price)||price<0){toast('Enter a real SKU and a valid price');return;}
  var rules=dntVendorPricingRules();
  rules.productOverrides[sku]=price;
  st('dnt_vendor_pricing_rules',rules);
  rVendorCat();
  toast('Price override set for '+sku);
}

async function vCompareAI(productId){
  var p=vAllProducts().find(function(x){return x.id===productId;});
  if(!p)return;
  var others=vAllProducts().filter(function(x){return x.name===p.name&&x.id!==p.id;});
  var compareText=others.length?others.map(function(o){return o.vendorName+': '+fmt(o.effectivePrice);}).join(', '):'no matching product found at another vendor';
  toast('Asking Claude to compare...');
  try{
    var res=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:300,
        system:'You are a dental-practice purchasing assistant. You are given real, already-known prices for one product across vendors -- never invent additional vendors or prices, only compare what you were given.',
        messages:[{role:'user',content:'Product: '+p.name+' ('+p.sku+'). Price at '+p.vendorName+': '+fmt(p.effectivePrice)+'. Prices at other vendors: '+compareText+'. Which is the better buy and why (consider unit, not just price)?'}]})});
    var data=await res.json();
    var err=dntAiError(data);
    if(err){toast(err,5000);return;}
    var text=(data.content&&data.content[0]&&data.content[0].text)||'No response text returned.';
    alert(text);
  }catch(e){toast('Could not connect to Claude. Check your connection and try again.');}
}

function vShowSpendReport(){
  var hist=vendorOrderHistory();
  var ytd=hist.reduce(function(s,o){return s+(o.total||0);},0);
  var byVendor={};
  hist.forEach(function(o){byVendor[o.vendor]=(byVendor[o.vendor]||0)+o.total;});
  var low=supplies().filter(function(s){return Number(s.qty)<=Number(s.reorder_threshold);});
  var rules=dntVendorPricingRules();
  var deals=Object.keys(rules.productOverrides).length+rules.categoryDiscounts.length+Object.keys(rules.vendorDiscounts).filter(function(k){return rules.vendorDiscounts[k]>0;}).length;
  var content=
    '<div class="krow" style="grid-template-columns:repeat(3,1fr);margin-bottom:16px">'+
      '<div class="kpi"><div class="klbl">YTD Spend</div><div class="kval">'+fmt(ytd)+'</div></div>'+
      '<div class="kpi"><div class="klbl">Active Deals</div><div class="kval">'+deals+'</div></div>'+
      '<div class="kpi"><div class="klbl">Low Stock Items</div><div class="kval" style="color:'+(low.length?'var(--danger)':'var(--text)')+'">'+low.length+'</div></div>'+
    '</div>'+
    '<div style="font-size:13px;font-weight:800;color:var(--text);margin-bottom:10px">Spend by Vendor</div>'+
    (Object.keys(byVendor).length?Object.keys(byVendor).sort(function(a,b){return byVendor[b]-byVendor[a];}).map(function(v){
      return '<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)"><span style="font-size:13px">'+H(v)+'</span><span style="font-size:13px;font-weight:700;color:var(--p)">'+fmt(byVendor[v])+'</span></div>';
    }).join(''):'<div style="color:var(--muted);font-size:13px;padding:12px 0">No orders placed yet. Orders you place will track spend automatically.</div>')+
    '<div style="margin-top:20px"><button class="btn bp" style="width:100%" onclick="vSpendAI()">Claude Spend Analysis</button></div>';
  $('vendor-spend-content').innerHTML=content;
  $('vendorSpendModal').classList.add('on');
}

async function vSpendAI(){
  var hist=vendorOrderHistory();
  var ytd=hist.reduce(function(s,o){return s+(o.total||0);},0);
  var low=supplies().filter(function(s){return Number(s.qty)<=Number(s.reorder_threshold);}).length;
  toast('Asking Claude for spend analysis...');
  try{
    var res=await fetch(PROXY,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({app_id:APP_ID,is_demo:true,max_tokens:500,
        system:'You are a dental-practice purchasing/spend analyst. You are given real, already-computed numbers -- never invent additional figures, and say plainly if the data is too sparse to draw a real conclusion.',
        messages:[{role:'user',content:'YTD supply spend: '+fmt(ytd)+' across '+hist.length+' orders. Low-stock items: '+low+'. Vendors available: Henry Schein Dental, Patterson Dental, Benco Dental, Darby Dental Supply, Burkhart Dental. What should our purchasing strategy be? Where should we consolidate orders for better pricing leverage?'}]})});
    var data=await res.json();
    var err=dntAiError(data);
    if(err){toast(err,5000);return;}
    var text=(data.content&&data.content[0]&&data.content[0].text)||'No response text returned.';
    $('vendorSpendModal').classList.remove('on');
    alert(text);
  }catch(e){toast('Could not connect to Claude. Check your connection and try again.');}
}
```

- [ ] **Step 5: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 6: Manual verification (code trace + one real API check)**

Trace: `vShowSpendReport()` with no orders yet shows "No orders placed yet," YTD Spend `$0.00`, Low Stock Items matching Task 3's supplies data. Place a real order (Task 2/4 flow), reopen the Spend Report — confirm YTD Spend and Spend by Vendor reflect it. Real API check (same pattern as this session's other AI-feature verifications): call `vCompareAI('hs01')` (Level 3 Surgical Masks, which has real cross-vendor matches per Task 1's catalog) against the real deployed proxy once this is live, and confirm a real Claude response renders via `alert()`, not a placeholder.

- [ ] **Step 7: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- AI Compare, Spend Report, Claude Spend Analysis (Task 5)"
```

---

## Self-Review Notes

- **Spec coverage:** every "In scope" bullet from the design spec has a corresponding task — catalog/browsing/cart (Task 1), vendor contact + Place Order (Task 2), Supplies panel + low-stock cross-reference + order-time stock update (Task 3), 3-tier negotiated pricing (Task 4), AI Compare + Spend Report (Task 5). Every "Explicitly out of scope" item (server sync, real purchasing integration, edit flows, live pricing sync) has no corresponding step.
- **Placeholder scan:** no TBD/TODO — every step shows real code (verified against the actual current file content, re-read immediately before writing this plan) or a real runnable check with a stated expected result. Catalog product data is real, complete, and internally consistent (SKU/category/price/unit for every product across all 5 vendors) — no filler rows.
- **Type/name consistency:** `DNT_VENDORS`/`DNT_VCAT_LABELS`/`_dntActiveVendor`/`_dntActiveCat` (Task 1) are used with identical names through Tasks 2-5. `vAllProducts()`'s shape (`{id,name,sku,cat,price,unit,vendorKey,vendorName}`, extended with `effectivePrice` in Task 4) is consumed identically by `vRenderCart()`, `vPlaceOrder()`, `vCompareAI()`. `supplies()`/`vLowStockItem()` (Task 3) are consumed identically by Task 5's Spend Report. Every cross-task Find/Replace anchor in Tasks 2-5 quotes the exact code the prior task in this plan actually produces, not a paraphrase.
