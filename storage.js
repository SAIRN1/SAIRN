// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/storage
//  Per-user, per-app key-value + conversation history
//  Privacy: RLS enforced at DB level — users can only read own data
//  Michael L. Dibert · SAIRN NEXUS Platform · 2026
// ═══════════════════════════════════════════════════════════════════

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

async function getUser(req) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) return null;
  const { data: { user }, error } = await supabase.auth.getUser(token);
  return error ? null : user;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', process.env.SITE_URL || '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const user = await getUser(req);
  if (!user) return res.status(401).json({ error: 'Authentication required' });

  const { app_id, key, value, prefix, action } = req.method === 'GET' ? req.query : (req.body || {});
  if (!app_id) return res.status(400).json({ error: 'app_id required' });

  try {

    // ── KEY-VALUE STORE ──────────────────────────────────────────
    if (req.method === 'GET' && !action) {
      if (key) {
        const { data } = await supabase.from('user_storage').select('key, value, updated_at').eq('user_id', user.id).eq('app_id', app_id).eq('key', key).maybeSingle();
        return res.status(200).json({ data: data || null });
      }
      const q = supabase.from('user_storage').select('key, value, updated_at').eq('user_id', user.id).eq('app_id', app_id).order('updated_at', { ascending: false }).limit(200);
      if (prefix) q.like('key', `${prefix}%`);
      const { data } = await q;
      return res.status(200).json({ data: data || [] });
    }

    if (req.method === 'POST' && !action) {
      if (!key) return res.status(400).json({ error: 'key required' });
      const { error } = await supabase.from('user_storage').upsert({ user_id: user.id, app_id, key, value: typeof value === 'string' ? { data: value } : value, updated_at: new Date().toISOString() }, { onConflict: 'user_id,app_id,key' });
      if (error) throw error;
      return res.status(200).json({ success: true });
    }

    if (req.method === 'DELETE') {
      if (!key) return res.status(400).json({ error: 'key required' });
      await supabase.from('user_storage').delete().eq('user_id', user.id).eq('app_id', app_id).eq('key', key);
      return res.status(200).json({ success: true });
    }

    // ── CONVERSATIONS ────────────────────────────────────────────
    if (action === 'get_conversations') {
      const { data } = await supabase.from('conversations').select('id, title, mode, updated_at').eq('user_id', user.id).eq('app_id', app_id).eq('is_archived', false).order('updated_at', { ascending: false }).limit(50);
      return res.status(200).json({ data: data || [] });
    }

    if (action === 'get_messages') {
      if (!key) return res.status(400).json({ error: 'conversation_id required as key' });
      // Verify ownership
      const { data: conv } = await supabase.from('conversations').select('id').eq('id', key).eq('user_id', user.id).maybeSingle();
      if (!conv) return res.status(403).json({ error: 'Not found' });
      const { data } = await supabase.from('messages').select('role, content, created_at').eq('conversation_id', key).order('created_at', { ascending: true }).limit(100);
      return res.status(200).json({ data: data || [] });
    }

    if (action === 'delete_conversation') {
      if (!key) return res.status(400).json({ error: 'conversation_id required as key' });
      await supabase.from('conversations').delete().eq('id', key).eq('user_id', user.id);
      return res.status(200).json({ success: true });
    }

    if (action === 'clear_all') {
      // Privacy: nuke all user data for this app on request
      await Promise.all([
        supabase.from('user_storage').delete().eq('user_id', user.id).eq('app_id', app_id),
        supabase.from('conversations').delete().eq('user_id', user.id).eq('app_id', app_id)
      ]);
      return res.status(200).json({ success: true });
    }

    return res.status(405).json({ error: 'Method not allowed' });

  } catch (err) {
    console.error('[SAIRN Storage]', err.message);
    return res.status(500).json({ error: 'Storage error' });
  }
}
