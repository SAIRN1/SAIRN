// ============================================================
// SAIRN Data Bridge — api/bridge.js
// Real-time data relay between StoneDesk, SAIRNacc, SAIRNhr
// 
// Architecture:
//   StoneDesk (Railway/PostgreSQL) → POST /api/bridge/push
//   SAIRNacc (Vercel/localStorage) → GET  /api/bridge/pull?shop=&type=
//   SAIRNhr  (Vercel/chat)         → GET  /api/bridge/context?shop=
//
// Data types relayed:
//   jobs      — completed jobs with revenue, cost, labor
//   employees — team member roster from StoneDesk team table
//   payroll   — payroll periods with hours per employee
//   invoices  — job invoices for AR tracking in SAIRNacc
//
// Storage: In-memory per session (Vercel serverless)
//   For production: swap Map for Redis/KV store
// ============================================================

// In-memory store (survives within a single Vercel function instance)
// Key: shopId, Value: { jobs:[], employees:[], payroll:[], invoices:[], updatedAt }
const store = new Map();

function getShopData(shopId) {
  if (!store.has(shopId)) {
    store.set(shopId, {
      jobs: [],
      employees: [],
      payroll: [],
      invoices: [],
      financialSummary: null,
      updatedAt: null
    });
  }
  return store.get(shopId);
}

function setCors(res, origin) {
  const allowed = [
    'https://sairn.vercel.app',
    'https://stonedesk.io',
    'https://fabricor-production.up.railway.app',
    'http://localhost:3000',
    'http://localhost:5173'
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
  // FIX: there's no vercel.json rewrite for /api/bridge/* sub-paths -- a flat
  // api/bridge.js file only matches /api/bridge exactly on Vercel, so the
  // path-based action below (used by push/pull/context/csv/clear) actually
  // 404s before this file ever runs, unless called as literally /api/bridge.
  // New actions use a query param instead so they don't depend on a rewrite
  // that doesn't exist; not touching the pre-existing actions' calling
  // convention since other apps may already call them some other way.
  const pathAction = url.pathname.replace('/api/bridge', '').replace(/^\//, '');
  const action = pathAction || url.searchParams.get('action') || 'status';
  const shopId  = url.searchParams.get('shop') || (req.body && req.body.shopId) || null;
  const type    = url.searchParams.get('type') || 'all';

  // ── STATUS ──────────────────────────────────────────────────
  if (action === 'status' || action === '') {
    return res.status(200).json({
      bridge: 'SAIRN Data Bridge v1.0',
      status: 'active',
      shops: store.size,
      endpoints: {
        push: 'POST /api/bridge/push — StoneDesk pushes data',
        pull: 'GET  /api/bridge/pull?shop=SHOPID&type=jobs|employees|payroll|invoices|all',
        context: 'GET  /api/bridge/context?shop=SHOPID — SAIRNhr shop context for AI',
        csv: 'GET  /api/bridge/csv?shop=SHOPID&type=jobs|payroll — download CSV',
        clear: 'POST /api/bridge/clear — clear shop data (auth required)',
        'maps-optimize': 'POST /api/bridge?action=maps-optimize { addresses: string[] } — Field Map route ordering',
        'maps-static': 'POST /api/bridge?action=maps-static { addresses: string[] } — Field Map preview image'
      }
    });
  }

  // ── PUSH (StoneDesk → Bridge) ────────────────────────────────
  if (action === 'push' && req.method === 'POST') {
    if (!shopId) return res.status(400).json({ error: 'shopId required' });
    const body = req.body || {};
    const data = getShopData(shopId);

    // Merge each data type
    if (body.jobs && Array.isArray(body.jobs)) {
      // Upsert by job ID
      body.jobs.forEach(job => {
        const idx = data.jobs.findIndex(j => j.id === job.id);
        if (idx >= 0) data.jobs[idx] = { ...data.jobs[idx], ...job };
        else data.jobs.push(job);
      });
    }
    if (body.employees && Array.isArray(body.employees)) {
      body.employees.forEach(emp => {
        const idx = data.employees.findIndex(e => e.id === emp.id);
        if (idx >= 0) data.employees[idx] = { ...data.employees[idx], ...emp };
        else data.employees.push(emp);
      });
    }
    if (body.payroll && Array.isArray(body.payroll)) {
      body.payroll.forEach(p => {
        const idx = data.payroll.findIndex(r => r.id === p.id);
        if (idx >= 0) data.payroll[idx] = { ...data.payroll[idx], ...p };
        else data.payroll.push(p);
      });
    }
    if (body.invoices && Array.isArray(body.invoices)) {
      body.invoices.forEach(inv => {
        const idx = data.invoices.findIndex(i => i.id === inv.id);
        if (idx >= 0) data.invoices[idx] = { ...data.invoices[idx], ...inv };
        else data.invoices.push(inv);
      });
    }
    if (body.financialSummary) {
      data.financialSummary = body.financialSummary;
    }

    data.updatedAt = new Date().toISOString();
    store.set(shopId, data);

    return res.status(200).json({
      ok: true,
      shopId,
      counts: {
        jobs: data.jobs.length,
        employees: data.employees.length,
        payroll: data.payroll.length,
        invoices: data.invoices.length
      },
      updatedAt: data.updatedAt
    });
  }

  // ── PULL (SAIRNacc/SAIRNhr ← Bridge) ────────────────────────
  if (action === 'pull' && req.method === 'GET') {
    if (!shopId) return res.status(400).json({ error: 'shop param required' });
    const data = getShopData(shopId);

    if (type === 'all') {
      return res.status(200).json({ ok: true, shopId, ...data });
    }
    if (['jobs','employees','payroll','invoices','financialSummary'].includes(type)) {
      return res.status(200).json({ ok: true, shopId, [type]: data[type], updatedAt: data.updatedAt });
    }
    return res.status(400).json({ error: 'Invalid type. Use: jobs|employees|payroll|invoices|all' });
  }

  // ── CONTEXT (SAIRNhr AI context) ─────────────────────────────
  if (action === 'context' && req.method === 'GET') {
    if (!shopId) return res.status(400).json({ error: 'shop param required' });
    const data = getShopData(shopId);

    const activeJobs    = data.jobs.filter(j => j.stage && j.stage !== 'complete').length;
    const completedJobs = data.jobs.filter(j => j.stage === 'complete').length;
    const totalRevenue  = data.jobs.reduce((s, j) => s + (j.estimatedRevenue || 0), 0);
    const employees     = data.employees.length;
    const shopName      = data.financialSummary?.shopName || 'Stone Shop';

    // Build rich context string for SAIRNhr AI
    const context = `
SHOP CONTEXT (from StoneDesk):
Shop: ${shopName}
Employees: ${employees} active team members
${data.employees.length ? 'Team: ' + data.employees.map(e => e.name + ' (' + (e.role || 'crew') + ')').join(', ') : ''}

Jobs:
- Active jobs: ${activeJobs}
- Completed jobs: ${completedJobs}  
- Pipeline revenue: $${totalRevenue.toLocaleString()}

${data.financialSummary ? `Financial (from SAIRNacc):
- Monthly revenue: $${(data.financialSummary.monthlyRevenue || 0).toLocaleString()}
- Monthly expenses: $${(data.financialSummary.monthlyExpenses || 0).toLocaleString()}
- Net: $${(data.financialSummary.netIncome || 0).toLocaleString()}` : ''}

This is a stone fabrication and installation business. HR advice should be specific to this industry.
Last synced: ${data.updatedAt || 'not yet synced'}
`.trim();

    return res.status(200).json({ ok: true, shopId, context, counts: {
      jobs: data.jobs.length,
      employees: data.employees.length
    }});
  }

  // ── CSV EXPORT (for Path B) ───────────────────────────────────
  if (action === 'csv' && req.method === 'GET') {
    if (!shopId) return res.status(400).json({ error: 'shop param required' });
    const data = getShopData(shopId);

    if (type === 'jobs') {
      const rows = ['Job Number,Customer,Job Name,Stage,Stone Type,Sq Ft,Est Revenue,Actual Revenue,Material Cost,Labor Hours,Install Date,Sales Rep'];
      data.jobs.forEach(j => rows.push([
        j.jobNumber || '', j.customerName || '', j.jobName || '',
        j.stage || '', j.stoneType || '', j.totalSqft || 0,
        j.estimatedRevenue || 0, j.actualRevenue || 0,
        j.materialCost || 0, j.actualTime || 0,
        j.installDate || '', j.salesRep || ''
      ].join(',')));
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename="stonedesk_jobs.csv"');
      return res.status(200).send(rows.join('\r\n'));
    }

    if (type === 'payroll') {
      const rows = ['Employee,Role,Pay Period,Hours,Rate,Gross Pay'];
      data.payroll.forEach(p => {
        if (p.lines) p.lines.forEach(l => rows.push([
          l.employeeName || '', l.role || '',
          p.period || '', l.hours || 0, l.rate || 0,
          (l.hours || 0) * (l.rate || 0)
        ].join(',')));
      });
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename="stonedesk_payroll.csv"');
      return res.status(200).send(rows.join('\r\n'));
    }

    if (type === 'gl') {
      // SAIRNacc-ready GL import format
      const rows = ['Date,Account,Description,Debit,Credit,Reference'];
      data.jobs.filter(j => j.stage === 'complete' && j.actualRevenue).forEach(j => {
        const date = j.completionDate || j.installDate || new Date().toISOString().slice(0,10);
        rows.push([date, '1100', 'AR - ' + j.jobName, j.actualRevenue || 0, 0, j.jobNumber || ''].join(','));
        rows.push([date, '4100', 'Revenue - ' + j.jobName, 0, j.actualRevenue || 0, j.jobNumber || ''].join(','));
        if (j.materialCost) {
          rows.push([date, '5100', 'Materials - ' + j.jobName, j.materialCost, 0, j.jobNumber || ''].join(','));
          rows.push([date, '2000', 'AP - Materials', 0, j.materialCost, j.jobNumber || ''].join(','));
        }
      });
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename="stonedesk_gl_import.csv"');
      return res.status(200).send(rows.join('\r\n'));
    }

    return res.status(400).json({ error: 'type must be jobs|payroll|gl' });
  }

  // ── CLEAR ─────────────────────────────────────────────────────
  if (action === 'clear' && req.method === 'POST') {
    if (!shopId) return res.status(400).json({ error: 'shopId required' });
    store.delete(shopId);
    return res.status(200).json({ ok: true, message: 'Shop data cleared' });
  }

  // ── MAPS-OPTIMIZE (Field Map -- StoneDesk route ordering) ────
  // Server-side only: GOOGLE_MAPS_API_KEY never reaches the browser.
  // Uses the standard (always-available) Route Matrix endpoint rather than
  // the experimental optimizeWaypointOrder feature, which Google gates
  // behind a manual Support enablement request -- a nearest-neighbor
  // ordering computed from real drive times is solid and doesn't depend
  // on a feature that might not be turned on for this project.
  if (action === 'maps-optimize' && req.method === 'POST') {
    const { addresses } = req.body || {};
    if (!Array.isArray(addresses) || addresses.length < 2) {
      return res.status(400).json({ error: 'addresses (array, 2+) required' });
    }
    if (!process.env.GOOGLE_MAPS_API_KEY) {
      return res.status(500).json({ error: 'GOOGLE_MAPS_API_KEY not configured' });
    }
    try {
      const points = addresses.map(a => ({ waypoint: { address: a } }));
      const matrixRes = await fetch('https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': process.env.GOOGLE_MAPS_API_KEY,
          'X-Goog-FieldMask': 'originIndex,destinationIndex,duration,condition'
        },
        body: JSON.stringify({ origins: points, destinations: points, travelMode: 'DRIVE' })
      });
      if (!matrixRes.ok) {
        return res.status(502).json({ error: 'Route Matrix request failed', status: matrixRes.status });
      }
      const elements = await matrixRes.json();

      const n = addresses.length;
      const dur = Array.from({ length: n }, () => Array(n).fill(Infinity));
      elements.forEach(e => {
        if (e.condition === 'ROUTE_EXISTS' && e.duration) {
          dur[e.originIndex][e.destinationIndex] = parseInt(String(e.duration).replace('s', ''), 10) || Infinity;
        }
      });

      // Nearest-neighbor heuristic starting from stop 0 (the day's first stop)
      const visited = new Set([0]);
      const order = [0];
      let totalOptimized = 0;
      while (order.length < n) {
        const last = order[order.length - 1];
        let bestNext = -1, bestDur = Infinity;
        for (let j = 0; j < n; j++) {
          if (!visited.has(j) && dur[last][j] < bestDur) { bestDur = dur[last][j]; bestNext = j; }
        }
        if (bestNext === -1) { // unreachable pair -- fall back to first unvisited
          bestNext = [...Array(n).keys()].find(j => !visited.has(j));
          bestDur = 0;
        }
        order.push(bestNext);
        visited.add(bestNext);
        totalOptimized += isFinite(bestDur) ? bestDur : 0;
      }

      // Original (as-given) order total, for the "saves X minutes" figure
      let totalOriginal = 0;
      for (let i = 0; i < n - 1; i++) {
        const d = dur[i][i + 1];
        totalOriginal += isFinite(d) ? d : 0;
      }

      const savedMinutes = Math.max(0, Math.round((totalOriginal - totalOptimized) / 60));
      return res.status(200).json({ ok: true, order, savedMinutes });
    } catch (err) {
      return res.status(502).json({ error: 'maps-optimize failed', detail: String(err) });
    }
  }

  // ── MAPS-STATIC (Field Map -- route preview image) ────────────
  // Fetches the image server-side and returns it as a data URL so the
  // API key never appears in any URL the browser sees or could copy.
  if (action === 'maps-static' && req.method === 'POST') {
    const { addresses } = req.body || {};
    if (!Array.isArray(addresses) || !addresses.length) {
      return res.status(400).json({ error: 'addresses (array) required' });
    }
    if (!process.env.GOOGLE_MAPS_API_KEY) {
      return res.status(500).json({ error: 'GOOGLE_MAPS_API_KEY not configured' });
    }
    try {
      const labels = 'ABCDEFGHIJ';
      const markerParams = addresses.slice(0, 10).map((a, i) =>
        'markers=' + encodeURIComponent('color:0x1B3A6B|label:' + labels[i] + '|' + a)
      ).join('&');
      const mapUrl = 'https://maps.googleapis.com/maps/api/staticmap?size=640x360&scale=2'
        + '&' + markerParams + '&key=' + process.env.GOOGLE_MAPS_API_KEY;
      const imgRes = await fetch(mapUrl);
      if (!imgRes.ok) {
        return res.status(502).json({ error: 'Static Maps request failed', status: imgRes.status });
      }
      const buf = Buffer.from(await imgRes.arrayBuffer());
      const contentType = imgRes.headers.get('content-type') || 'image/png';
      return res.status(200).json({ ok: true, imageUrl: 'data:' + contentType + ';base64,' + buf.toString('base64') });
    } catch (err) {
      return res.status(502).json({ error: 'maps-static failed', detail: String(err) });
    }
  }

  return res.status(404).json({ error: 'Unknown bridge action: ' + action });
}
