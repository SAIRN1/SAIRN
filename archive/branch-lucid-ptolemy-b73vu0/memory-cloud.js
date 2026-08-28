// ============================================================
// SAIRN Cloud Memory API
// Supabase-backed persistent memory across all devices
// Michael L. Dibert · SAIRN Technologies · 2026
// ============================================================

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL || '',
  process.env.SUPABASE_SERVICE_ROLE_KEY || ''
);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-User-ID, X-App-ID');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const userId = req.headers['x-user-id'] || req.body?.user_id || 'anonymous';
  const appId  = req.headers['x-app-id']  || req.body?.app_id  || 'general';

  // ── GET — load memory for user + app ──────────────────────
  if (req.method === 'GET') {
    try {
      if (!process.env.SUPABASE_URL) {
        // Fallback — no Supabase configured
        return res.status(200).json({ entries: [], source: 'none' });
      }
      const { data, error } = await supabase
        .from('sairn_memory')
        .select('id, content, created_at, app_id')
        .eq('user_id', userId)
        .eq('app_id', appId)
        .order('created_at', { ascending: false })
        .limit(50);

      if (error) throw error;
      return res.status(200).json({ entries: data || [], source: 'supabase' });
    } catch (err) {
      return res.status(200).json({ entries: [], source: 'error', error: err.message });
    }
  }

  // ── POST — save a memory entry ────────────────────────────
  if (req.method === 'POST') {
    const { content, metadata } = req.body || {};
    if (!content) return res.status(400).json({ error: 'Content required' });

    try {
      if (!process.env.SUPABASE_URL) {
        return res.status(200).json({ saved: false, source: 'none' });
      }
      const { data, error } = await supabase
        .from('sairn_memory')
        .insert([{
          user_id: userId,
          app_id: appId,
          content: content.slice(0, 500),
          metadata: metadata || {},
          created_at: new Date().toISOString(),
        }])
        .select();

      if (error) throw error;
      return res.status(200).json({ saved: true, id: data?.[0]?.id, source: 'supabase' });
    } catch (err) {
      return res.status(200).json({ saved: false, error: err.message });
    }
  }

  // ── DELETE — clear memory for user + app ─────────────────
  if (req.method === 'DELETE') {
    try {
      if (!process.env.SUPABASE_URL) {
        return res.status(200).json({ cleared: false, source: 'none' });
      }
      const { error } = await supabase
        .from('sairn_memory')
        .delete()
        .eq('user_id', userId)
        .eq('app_id', appId);

      if (error) throw error;
      return res.status(200).json({ cleared: true, source: 'supabase' });
    } catch (err) {
      return res.status(200).json({ cleared: false, error: err.message });
    }
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
