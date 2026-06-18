// ============================================================
// SAIRN Data Bridge — api/bridge.js  v2.0
// Real-time relay between StoneDesk, SAIRNbiz, SAIRNacc, SAIRNhr
//
// v2.0 changes:
//   - Supabase persistence: data survives Vercel cold starts
//   - Falls back to in-memory if Supabase not configured
//   - New data types: slabs, expenses, checks, customers
//   - SAIRNbiz can now pull in real time
//
// Actions:
//   push    POST  ?action=push   { shopId, ...dataTypes }
//   pull    GET   ?action=pull   ?shop=ID&type=all|jobs|invoices|...
//   context GET   ?action=context ?shop=ID
//   csv     GET   ?action=csv    ?shop=ID&type=jobs|payroll|gl
//   clear   POST  ?action=clear  { shopId }
//   maps-optimize  POST  ?action=maps-optimize
//   maps-static    POST  ?action=maps-static
// ============================================================

const inMemory = new Map();

const SUPABASE_URL = process.env.SUPABASE_URL || 'https://ejrlrrkvhtllxbbypdjb.supabase.co';
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_ANON_KEY || '';

function emptyShop() {
  return { jobs:[], employees:[], payroll:[], invoices:[], slabs:[], customers:[], expenses:[], financialSummary:null, updatedAt:null };
}

async function loadShop(shopId) {
  // Try Supabase first
  if (SUPABASE_KEY) {
    try {
      const r = await fetch(`${SUPABASE_URL}/rest/v1/bridge_data?shop_id=eq.${encodeURIComponent(shopId)}&select=data&limit=1`, {
        headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}`, 'Content-Type': 'application/json' }
      });
      if (r.ok) {
        const rows = await r.json();
        if (rows && rows.length && rows[0].data) return rows[0].data;
      }
    } catch(e) {}
  }
  // Fall back to in-memory
  if (!inMemory.has(shopId)) inMemory.set(shopId, emptyShop());
  return inMemory.get(shopId);
}

async function saveShop(shopId, data) {
  data.updatedAt = new Date().toISOString();
  inMemory.set(shopId, data);
  if (SUPABASE_KEY) {
    try {
      await fetch(`${SUPABASE_URL}/rest/v1/bridge_data`, {
        method: 'POST',
        headers: {
          'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}`,
          'Content-Type': 'application/json', 'Prefer': 'resolution=merge-duplicates'
        },
        body: JSON.stringify({ shop_id: shopId, data, updated_at: data.updatedAt })
      });
    } catch(e) {}
  }
}

function setCors(res, origin) {
  const allowed = [
    'https://sairn.vercel.app','https://stonedesk.io',
    'https://fabricor-production.up.railway.app',
    'http://localhost:3000','http://localhost:5173','http://localhost:8765'
  ];
  const o = allowed.includes(origin) ? origin : 'https://sairn.vercel.app';
  res.setHeader('Access-Control-Allow-Origin', o);
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Shop-Token, Authorization');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
}

export default async function handler(req, res) {
  const origin = req.headers.origin || '';
  setCors(res, origin);
  if (req.method === 'OPTIONS') return res.status(200).end();

  const url = new URL(req.url, 'https://sairn.vercel.app');
  const pathAction = url.pathname.replace('/api/bridge', '').replace(/^\//, '');
  const action = pathAction || url.searchParams.get('action') || 'status';
  const shopId = url.searchParams.get('shop') || (req.body && req.body.shopId) || null;
  const type   = url.searchParams.get('type') || 'all';

  // ── STATUS ──────────────────────────────────────────────────
  if (action === 'status' || action === '') {
    return res.status(200).json({
      bridge: 'SAIRN Data Bridge v2.0',
      status: 'active',
      persistence: SUPABASE_KEY ? 'supabase' : 'in-memory',
      shops: inMemory.size,
      endpoints: {
        push:   'POST /api/bridge?action=push { shopId, jobs?, employees?, payroll?, invoices?, slabs?, customers?, expenses?, financialSummary? }',
        pull:   'GET  /api/bridge?action=pull&shop=ID&type=all|jobs|employees|payroll|invoices|slabs|customers|expenses',
        context:'GET  /api/bridge?action=context&shop=ID',
        csv:    'GET  /api/bridge?action=csv&shop=ID&type=jobs|payroll|gl',
        clear:  'POST /api/bridge?action=clear { shopId }'
      }
    });
  }

  // ── PUSH ────────────────────────────────────────────────────
  if (action === 'push' && req.method === 'POST') {
    if (!shopId) return res.status(400).json({ error: 'shopId required' });
    const body = req.body || {};
    const data = await loadShop(shopId);

    const upsert = (arr, incoming, key='id') => {
      if (!Array.isArray(incoming)) return;
      incoming.forEach(item => {
        const idx = arr.findIndex(x => x[key] === item[key]);
        if (idx >= 0) arr[idx] = { ...arr[idx], ...item };
        else arr.push(item);
      });
    };

    if (body.jobs)            upsert(data.jobs, body.jobs);
    if (body.employees)       upsert(data.employees, body.employees);
    if (body.payroll)         upsert(data.payroll, body.payroll);
    if (body.invoices)        upsert(data.invoices, body.invoices);
    if (body.slabs)           upsert(data.slabs, body.slabs);
    if (body.customers)       upsert(data.customers, body.customers);
    if (body.expenses)        upsert(data.expenses, body.expenses);
    if (body.financialSummary) data.financialSummary = body.financialSummary;

    await saveShop(shopId, data);

    return res.status(200).json({
      ok: true, shopId,
      counts: { jobs: data.jobs.length, employees: data.employees.length,
        payroll: data.payroll.length, invoices: data.invoices.length,
        slabs: data.slabs.length, customers: data.customers.length, expenses: data.expenses.length },
      updatedAt: data.updatedAt
    });
  }

  // ── PULL ─────────────────────────────────────────────────────
  if (action === 'pull' && req.method === 'GET') {
    if (!shopId) return res.status(400).json({ error: 'shop param required' });
    const data = await loadShop(shopId);
    const validTypes = ['jobs','employees','payroll','invoices','slabs','customers','expenses','financialSummary'];
    if (type === 'all') return res.status(200).json({ ok: true, shopId, ...data });
    if (validTypes.includes(type)) return res.status(200).json({ ok: true, shopId, [type]: data[type], updatedAt: data.updatedAt });
    return res.status(400).json({ error: 'Invalid type. Use: ' + validTypes.join('|') + '|all' });
  }

  // ── CONTEXT ──────────────────────────────────────────────────
  if (action === 'context' && req.method === 'GET') {
    if (!shopId) return res.status(400).json({ error: 'shop param required' });
    const data = await loadShop(shopId);
    const activeJobs    = data.jobs.filter(j => j.stage && j.stage !== 'complete').length;
    const completedJobs = data.jobs.filter(j => j.stage === 'complete').length;
    const totalRevenue  = data.jobs.reduce((s,j) => s + (j.estimatedRevenue||0), 0);
    const shopName      = data.financialSummary?.shopName || 'Stone Shop';
    const context = `
SHOP CONTEXT (from StoneDesk):
Shop: ${shopName}
Employees: ${data.employees.length} active team members
${data.employees.length ? 'Team: ' + data.employees.map(e=>e.name+' ('+(e.role||'crew')+')').join(', ') : ''}
Jobs: ${activeJobs} active, ${completedJobs} completed · Pipeline: $${totalRevenue.toLocaleString()}
Slabs in inventory: ${data.slabs.filter(s=>s.status==='in-stock').length}
Pending expenses: ${data.expenses.length}
${data.financialSummary ? `Financial: Revenue $${(data.financialSummary.monthlyRevenue||0).toLocaleString()} · Expenses $${(data.financialSummary.monthlyExpenses||0).toLocaleString()} · Net $${(data.financialSummary.netIncome||0).toLocaleString()}` : ''}
Last synced: ${data.updatedAt || 'not yet synced'}`.trim();
    return res.status(200).json({ ok: true, shopId, context, counts: { jobs: data.jobs.length, employees: data.employees.length }});
  }

  // ── CSV ───────────────────────────────────────────────────────
  if (action === 'csv' && req.method === 'GET') {
    if (!shopId) return res.status(400).json({ error: 'shop param required' });
    const data = await loadShop(shopId);
    if (type === 'jobs') {
      const rows = ['Job Number,Customer,Stage,Stone Type,Sq Ft,Est Revenue,Actual Revenue,Material Cost,Install Date,Sales Rep'];
      data.jobs.forEach(j => rows.push([j.jobNumber||'',j.customerName||'',j.stage||'',j.stoneType||'',j.totalSqft||0,j.estimatedRevenue||0,j.actualRevenue||0,j.materialCost||0,j.installDate||'',j.salesRep||''].join(',')));
      res.setHeader('Content-Type','text/csv');
      res.setHeader('Content-Disposition','attachment; filename="stonedesk_jobs.csv"');
      return res.status(200).send(rows.join('\r\n'));
    }
    if (type === 'payroll') {
      const rows = ['Employee,Role,Pay Period,Hours,Rate,Gross Pay'];
      data.payroll.forEach(p => { if(p.lines) p.lines.forEach(l => rows.push([l.employeeName||'',l.role||'',p.period||'',l.hours||0,l.rate||0,(l.hours||0)*(l.rate||0)].join(','))); });
      res.setHeader('Content-Type','text/csv');
      res.setHeader('Content-Disposition','attachment; filename="stonedesk_payroll.csv"');
      return res.status(200).send(rows.join('\r\n'));
    }
    if (type === 'gl') {
      const rows = ['Date,Account,Description,Debit,Credit,Reference'];
      data.jobs.filter(j=>j.stage==='complete'&&j.actualRevenue).forEach(j=>{
        const d=j.completionDate||j.installDate||new Date().toISOString().slice(0,10);
        rows.push([d,'1100','AR - '+(j.jobName||''),j.actualRevenue||0,0,j.jobNumber||''].join(','));
        rows.push([d,'4100','Revenue - '+(j.jobName||''),0,j.actualRevenue||0,j.jobNumber||''].join(','));
        if(j.materialCost){rows.push([d,'5100','Materials - '+(j.jobName||''),j.materialCost,0,j.jobNumber||''].join(','));rows.push([d,'2000','AP - Materials',0,j.materialCost,j.jobNumber||''].join(','));}
      });
      data.expenses.forEach(e=>{
        rows.push([e.date||'','5200','Expense - '+(e.payee||''),e.amount||0,0,e.memo||''].join(','));
        rows.push([e.date||'','2000','AP - '+(e.payee||''),0,e.amount||0,e.memo||''].join(','));
      });
      res.setHeader('Content-Type','text/csv');
      res.setHeader('Content-Disposition','attachment; filename="stonedesk_gl_import.csv"');
      return res.status(200).send(rows.join('\r\n'));
    }
    return res.status(400).json({ error: 'type must be jobs|payroll|gl' });
  }

  // ── CLEAR ─────────────────────────────────────────────────────
  if (action === 'clear' && req.method === 'POST') {
    if (!shopId) return res.status(400).json({ error: 'shopId required' });
    inMemory.delete(shopId);
    if (SUPABASE_KEY) {
      try { await fetch(`${SUPABASE_URL}/rest/v1/bridge_data?shop_id=eq.${encodeURIComponent(shopId)}`,{method:'DELETE',headers:{'apikey':SUPABASE_KEY,'Authorization':`Bearer ${SUPABASE_KEY}`}}); } catch(e){}
    }
    return res.status(200).json({ ok: true, message: 'Shop data cleared' });
  }

  // ── MAPS-OPTIMIZE ─────────────────────────────────────────────
  if (action === 'maps-optimize' && req.method === 'POST') {
    const { addresses } = req.body || {};
    if (!Array.isArray(addresses)||addresses.length<2) return res.status(400).json({error:'addresses (array, 2+) required'});
    if (!process.env.GOOGLE_MAPS_API_KEY) return res.status(500).json({error:'GOOGLE_MAPS_API_KEY not configured'});
    try {
      const points=addresses.map(a=>({waypoint:{address:a}}));
      const matrixRes=await fetch('https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix',{method:'POST',headers:{'Content-Type':'application/json','X-Goog-Api-Key':process.env.GOOGLE_MAPS_API_KEY,'X-Goog-FieldMask':'originIndex,destinationIndex,duration,condition'},body:JSON.stringify({origins:points,destinations:points,travelMode:'DRIVE'})});
      if(!matrixRes.ok) return res.status(502).json({error:'Route Matrix failed',status:matrixRes.status});
      const elements=await matrixRes.json();
      const n=addresses.length;
      const dur=Array.from({length:n},()=>Array(n).fill(Infinity));
      elements.forEach(e=>{if(e.condition==='ROUTE_EXISTS'&&e.duration){dur[e.originIndex][e.destinationIndex]=parseInt(String(e.duration).replace('s',''),10)||Infinity;}});
      const visited=new Set([0]);const order=[0];let totalOpt=0;
      while(order.length<n){const last=order[order.length-1];let bestNext=-1,bestDur=Infinity;for(let j=0;j<n;j++){if(!visited.has(j)&&dur[last][j]<bestDur){bestDur=dur[last][j];bestNext=j;}}if(bestNext===-1)bestNext=[...Array(n).keys()].find(j=>!visited.has(j));order.push(bestNext);visited.add(bestNext);totalOpt+=isFinite(bestDur)?bestDur:0;}
      let totalOrig=0;for(let i=0;i<n-1;i++){const d=dur[i][i+1];totalOrig+=isFinite(d)?d:0;}
      return res.status(200).json({ok:true,order,savedMinutes:Math.max(0,Math.round((totalOrig-totalOpt)/60))});
    } catch(err){return res.status(502).json({error:'maps-optimize failed',detail:String(err)});}
  }

  // ── MAPS-STATIC ───────────────────────────────────────────────
  if (action === 'maps-static' && req.method === 'POST') {
    const { addresses } = req.body || {};
    if (!Array.isArray(addresses)||!addresses.length) return res.status(400).json({error:'addresses (array) required'});
    if (!process.env.GOOGLE_MAPS_API_KEY) return res.status(500).json({error:'GOOGLE_MAPS_API_KEY not configured'});
    try {
      const labels='ABCDEFGHIJ';
      const markerParams=addresses.slice(0,10).map((a,i)=>'markers='+encodeURIComponent('color:0x1B3A6B|label:'+labels[i]+'|'+a)).join('&');
      const mapUrl='https://maps.googleapis.com/maps/api/staticmap?size=640x360&scale=2&'+markerParams+'&key='+process.env.GOOGLE_MAPS_API_KEY;
      const imgRes=await fetch(mapUrl);
      if(!imgRes.ok) return res.status(502).json({error:'Static Maps failed',status:imgRes.status});
      const buf=Buffer.from(await imgRes.arrayBuffer());
      const ct=imgRes.headers.get('content-type')||'image/png';
      return res.status(200).json({ok:true,imageUrl:'data:'+ct+';base64,'+buf.toString('base64')});
    } catch(err){return res.status(502).json({error:'maps-static failed',detail:String(err)});}
  }

  return res.status(404).json({ error: 'Unknown bridge action: ' + action });
}
