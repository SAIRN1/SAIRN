// ================================================================
// SAIRN B2B Database API — api/db.js
// Handles all Supabase reads/writes for B2B apps
// StoneDesk · SAIRNbuild · SAIRNtrade · SAIRNscape
// Michael L. Dibert · SAIRN Technologies · 2026
// ================================================================

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

function setCors(res, req) {
  const allowed = [
    'https://sairn.vercel.app',
    'https://stonedesk.io',
    'https://fabricor-production.up.railway.app',
    'http://localhost:3000',
    'http://localhost:5173'
  ];
  const origin = req.headers.origin || '';
  const o = allowed.includes(origin) ? origin : 'https://sairn.vercel.app';
  res.setHeader('Access-Control-Allow-Origin', o);
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Shop-Id');
}

// Verify shop exists. Returns { shop } on success or { error } on failure.
// Used by all write endpoints that operate on an existing shop.
async function getShop(req) {
  const shopId = req.headers['x-shop-id'] || req.body?.shop_id || req.query?.shop_id;

  if (!shopId) return { error: 'shop_id required' };

  const { data: shop, error } = await supabase
    .from('shops')
    .select('*')
    .eq('id', shopId)
    .single();

  if (error || !shop) return { error: 'Shop not found' };
  return { shop };
}

// Guard for admin-only endpoints (create_shop) that have no existing shop_id.
// Set SAIRN_INTERNAL_KEY in Vercel to enforce; skips when env var not configured.
function checkInternalKey(req) {
  const configured = process.env.SAIRN_INTERNAL_KEY;
  if (!configured) return true;
  return req.headers['x-sairn-key'] === configured;
}

export default async function handler(req, res) {
  setCors(res, req);
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { action } = req.query;
  if (!action) return res.status(400).json({ error: 'action required' });

  try {
    // -- SHOP MANAGEMENT -----------------------------------------

    if (action === 'create_shop') {
      if (!checkInternalKey(req)) return res.status(401).json({ error: 'Missing or invalid X-SAIRN-Key header' });
      const { app_id, shop_name, owner_email, plan = 'starter' } = req.body;
      if (!app_id || !shop_name || !owner_email) {
        return res.status(400).json({ error: 'app_id, shop_name, owner_email required' });
      }
      // Get or create profile
      let { data: profile } = await supabase
        .from('profiles').select('id').eq('email', owner_email).maybeSingle();
      
      const { data: shop, error } = await supabase.from('shops').insert({
        app_id, shop_name, plan,
        billing_email: owner_email,
        owner_id: profile?.id || null,
        status: 'active'
      }).select().single();

      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, shop });
    }

    if (action === 'get_shop') {
      const shopId = req.query.shop_id;
      if (!shopId) return res.status(400).json({ error: 'shop_id required' });
      const { data, error } = await supabase
        .from('shops').select('*').eq('id', shopId).single();
      if (error) return res.status(404).json({ error: 'Shop not found' });
      return res.status(200).json({ ok: true, shop: data });
    }

    if (action === 'dashboard') {
      const shopId = req.query.shop_id;
      if (!shopId) return res.status(400).json({ error: 'shop_id required' });
      const { data, error } = await supabase.rpc('shop_dashboard', { p_shop_id: shopId });
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, dashboard: data });
    }

    // -- CUSTOMERS -----------------------------------------------

    if (action === 'get_customers') {
      const { shop_id, search, limit = 50, offset = 0 } = req.query;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
      
      let q = supabase.from('customers').select('*').eq('shop_id', shop_id);
      if (search) {
        const s = String(search).replace(/[^a-zA-Z0-9 @._\-]/g, '').slice(0, 100);
        q = q.or(`first_name.ilike.%${s}%,last_name.ilike.%${s}%,company_name.ilike.%${s}%,phone.ilike.%${s}%`);
      }
      q = q.order('updated_at', { ascending: false }).range(+offset, +offset + +limit - 1);
      const { data, error, count } = await q;
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, customers: data, count });
    }

    if (action === 'save_customer') {
      const { shop_id, id, ...fields } = req.body;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
      
      let result;
      if (id) {
        result = await supabase.from('customers').update(fields).eq('id', id).eq('shop_id', shop_id).select().single();
      } else {
        result = await supabase.from('customers').insert({ shop_id, ...fields }).select().single();
      }
      if (result.error) return res.status(500).json({ error: result.error.message });
      return res.status(200).json({ ok: true, customer: result.data });
    }

    // -- JOBS ----------------------------------------------------

    if (action === 'get_jobs') {
      const { shop_id, status, date, tech_id, limit = 100, offset = 0 } = req.query;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

      let q = supabase.from('jobs')
        .select('*, customers(first_name,last_name,company_name,phone), shop_users(full_name,trade)')
        .eq('shop_id', shop_id);
      if (status) q = q.eq('status', status);
      if (date)   q = q.eq('scheduled_date', date);
      if (tech_id) q = q.eq('assigned_to', tech_id);
      q = q.order('scheduled_date', { ascending: false }).range(+offset, +offset + +limit - 1);

      const { data, error } = await q;
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, jobs: data });
    }

    if (action === 'save_job') {
      const { shop_id, id, ...fields } = req.body;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

      // Auto-generate job number if new job
      if (!id && !fields.job_number) {
        const { count } = await supabase.from('jobs').select('*', { count: 'exact', head: true }).eq('shop_id', shop_id);
        const prefix = { stonedesk:'SD', sairntrade:'WO', sairnbuild:'PR', sairnscape:'LJ' }[fields.app_id] || 'JB';
        fields.job_number = `${prefix}-${String((count||0) + 1001).padStart(4,'0')}`;
      }

      let result;
      if (id) {
        result = await supabase.from('jobs').update(fields).eq('id', id).eq('shop_id', shop_id).select().single();
      } else {
        result = await supabase.from('jobs').insert({ shop_id, ...fields }).select().single();
      }
      if (result.error) return res.status(500).json({ error: result.error.message });

      // Auto-post GL entry on completion
      if (fields.status === 'complete' && fields.actual_revenue) {
        await supabase.from('gl_entries').insert({
          shop_id, date: new Date().toISOString().slice(0,10),
          account_code: '4000', description: `Revenue - ${fields.title || 'Job'}`,
          credit: fields.actual_revenue, source_app: fields.app_id, source_id: result.data.id
        }).catch(() => {});
      }

      return res.status(200).json({ ok: true, job: result.data });
    }

    if (action === 'update_job_status') {
      const { job_id, status, notes } = req.body;
      if (!job_id || !status) return res.status(400).json({ error: 'job_id and status required' });
      const { shop, error: shopErr } = await getShop(req);
      if (shopErr) return res.status(400).json({ error: shopErr });
      const shop_id = shop.id;
      const updates = { status };
      if (status === 'in_progress' && !req.body.started_at) updates.started_at = new Date().toISOString();
      if (status === 'complete') updates.completed_at = new Date().toISOString();
      if (notes) updates.notes = notes;

      const { data, error } = await supabase.from('jobs')
        .update(updates).eq('id', job_id).eq('shop_id', shop_id).select().single();
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, job: data });
    }

    // -- INVOICES ------------------------------------------------

    if (action === 'get_invoices') {
      const { shop_id, status, customer_id, limit = 50, offset = 0 } = req.query;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

      let q = supabase.from('invoices')
        .select('*, customers(first_name,last_name,company_name,email)')
        .eq('shop_id', shop_id);
      if (status) q = q.eq('status', status);
      if (customer_id) q = q.eq('customer_id', customer_id);
      q = q.order('created_at', { ascending: false }).range(+offset, +offset + +limit - 1);

      const { data, error } = await q;
      if (error) return res.status(500).json({ error: error.message });

      // Auto-flag overdue
      const today = new Date().toISOString().slice(0,10);
      const processed = (data||[]).map(inv => ({
        ...inv,
        status: inv.status === 'sent' && inv.due_date && inv.due_date < today ? 'overdue' : inv.status
      }));
      return res.status(200).json({ ok: true, invoices: processed });
    }

    if (action === 'create_invoice') {
      const { shop_id, job_id, customer_id, line_items, notes, payment_terms = 'net30' } = req.body;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

      const subtotal = (line_items||[]).reduce((s,i) => s + (i.qty * i.unit_price), 0);
      const tax_rate = req.body.tax_rate || 0;
      const tax_amount = subtotal * tax_rate;
      const total = subtotal + tax_amount;

      const { count } = await supabase.from('invoices').select('*', { count:'exact', head:true }).eq('shop_id', shop_id);
      const invoice_number = `INV-${String((count||0) + 1001).padStart(4,'0')}`;

      const due_date = new Date();
      const daysMap = { net15:15, net30:30, net60:60, due_on_receipt:0 };
      due_date.setDate(due_date.getDate() + (daysMap[payment_terms] || 30));

      const { data, error } = await supabase.from('invoices').insert({
        shop_id, job_id, customer_id, invoice_number, line_items,
        subtotal, tax_rate, tax_amount, total, payment_terms, notes,
        due_date: due_date.toISOString().slice(0,10),
        status: 'draft'
      }).select().single();

      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, invoice: data });
    }

    // -- PARTS / INVENTORY ----------------------------------------

    if (action === 'get_parts') {
      const { shop_id, low_stock } = req.query;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });
      
      let q = supabase.from('parts').select('*').eq('shop_id', shop_id);
      if (low_stock === 'true') q = q.lte('quantity', supabase.raw('reorder_at'));
      q = q.order('name');

      const { data, error } = await q;
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, parts: data });
    }

    if (action === 'save_part') {
      const { shop, error: shopErr } = await getShop(req);
      if (shopErr) return res.status(400).json({ error: shopErr });
      const shop_id = shop.id;
      const { id, ...fields } = req.body;
      let result;
      if (id) {
        result = await supabase.from('parts').update(fields).eq('id', id).eq('shop_id', shop_id).select().single();
      } else {
        result = await supabase.from('parts').insert({ shop_id, ...fields }).select().single();
      }
      if (result.error) return res.status(500).json({ error: result.error.message });
      return res.status(200).json({ ok: true, part: result.data });
    }

    // -- SLABS (StoneDesk) ----------------------------------------

    if (action === 'get_slabs') {
      const { shop_id, status, material } = req.query;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

      let q = supabase.from('slabs').select('*').eq('shop_id', shop_id);
      if (status) q = q.eq('status', status);
      if (material) q = q.ilike('material', `%${material}%`);
      q = q.order('created_at', { ascending: false });

      const { data, error } = await q;
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, slabs: data });
    }

    if (action === 'save_slab') {
      const { shop, error: shopErr } = await getShop(req);
      if (shopErr) return res.status(400).json({ error: shopErr });
      const shop_id = shop.id;
      const { id, ...fields } = req.body;
      let result;
      if (id) {
        result = await supabase.from('slabs').update(fields).eq('id', id).eq('shop_id', shop_id).select().single();
      } else {
        result = await supabase.from('slabs').insert({ shop_id, ...fields }).select().single();
      }
      if (result.error) return res.status(500).json({ error: result.error.message });
      return res.status(200).json({ ok: true, slab: result.data });
    }

    // -- PROJECTS (SAIRNbuild) ------------------------------------

    if (action === 'get_projects') {
      const { shop_id, status } = req.query;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

      let q = supabase.from('projects')
        .select('*, customers(first_name,last_name,company_name)')
        .eq('shop_id', shop_id);
      if (status) q = q.eq('status', status);
      q = q.order('updated_at', { ascending: false });

      const { data, error } = await q;
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, projects: data });
    }

    if (action === 'save_project') {
      const { shop, error: shopErr } = await getShop(req);
      if (shopErr) return res.status(400).json({ error: shopErr });
      const shop_id = shop.id;
      const { id, ...fields } = req.body;
      let result;
      if (id) {
        result = await supabase.from('projects').update(fields).eq('id', id).eq('shop_id', shop_id).select().single();
      } else {
        result = await supabase.from('projects').insert({ shop_id, ...fields }).select().single();
      }
      if (result.error) return res.status(500).json({ error: result.error.message });
      return res.status(200).json({ ok: true, project: result.data });
    }

    // -- GL ENTRIES -----------------------------------------------

    if (action === 'get_gl') {
      const { shop_id, month, posted } = req.query;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

      let q = supabase.from('gl_entries').select('*').eq('shop_id', shop_id);
      if (month) q = q.gte('date', month + '-01').lte('date', month + '-31');
      if (posted !== undefined) q = q.eq('posted', posted === 'true');
      q = q.order('date', { ascending: false }).limit(500);

      const { data, error } = await q;
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, entries: data });
    }

    if (action === 'post_gl') {
      const { shop_id, entries } = req.body;
      if (!shop_id || !entries?.length) return res.status(400).json({ error: 'shop_id and entries required' });

      const { data, error } = await supabase.from('gl_entries')
        .insert(entries.map(e => ({ ...e, shop_id }))).select();
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, posted: data.length });
    }

    // -- SHOP USERS (TECHS) ---------------------------------------

    if (action === 'get_techs') {
      const { shop_id } = req.query;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

      const { data, error } = await supabase.from('shop_users')
        .select('*').eq('shop_id', shop_id).eq('status', 'active').order('full_name');
      if (error) return res.status(500).json({ error: error.message });
      return res.status(200).json({ ok: true, techs: data });
    }

    if (action === 'save_tech') {
      const { shop, error: shopErr } = await getShop(req);
      if (shopErr) return res.status(400).json({ error: shopErr });
      const shop_id = shop.id;
      const { id, ...fields } = req.body;
      let result;
      if (id) {
        result = await supabase.from('shop_users').update(fields).eq('id', id).eq('shop_id', shop_id).select().single();
      } else {
        result = await supabase.from('shop_users').insert({ shop_id, ...fields }).select().single();
      }
      if (result.error) return res.status(500).json({ error: result.error.message });
      return res.status(200).json({ ok: true, tech: result.data });
    }

    // -- REPORTS -------------------------------------------------

    if (action === 'revenue_by_period') {
      const { shop_id, period = 'month' } = req.query;
      if (!shop_id) return res.status(400).json({ error: 'shop_id required' });

      const truncFn = { day:'day', week:'week', month:'month', year:'year' }[period] || 'month';
      const { data, error } = await supabase.rpc('revenue_by_period', {
        p_shop_id: shop_id, p_period: truncFn
      }).catch(() => ({ data: null, error: { message: 'Function not available' } }));

      // Fallback: manual query
      if (error) {
        const { data: jobs } = await supabase.from('jobs')
          .select('completed_at, actual_revenue, trade')
          .eq('shop_id', shop_id)
          .eq('status', 'complete')
          .not('actual_revenue', 'is', null)
          .gte('completed_at', new Date(Date.now() - 90*86400000).toISOString());

        return res.status(200).json({ ok: true, jobs: jobs || [] });
      }
      return res.status(200).json({ ok: true, data });
    }

    return res.status(400).json({ error: `Unknown action: ${action}` });

  } catch (err) {
    console.error('[DB API Error]', err.message);
    return res.status(500).json({ error: err.message });
  }
}
