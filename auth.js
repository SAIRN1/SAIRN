// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — /api/auth
//  signup · signin · signout · refresh · me · forgot · update_profile
//  Privacy: passwords never stored by SAIRN (Supabase handles hashing)
//  Michael L. Dibert · HONEY COMB Platform · 2026
// ═══════════════════════════════════════════════════════════════════

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', process.env.SITE_URL || '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST')    return res.status(405).json({ error: 'Method not allowed' });

  const { action, email, password, full_name, refresh_token, new_password } = req.body || {};

  try {
    switch (action) {

      // ── SIGN UP ────────────────────────────────────────────────
      case 'signup': {
        if (!email?.includes('@')) return res.status(400).json({ error: 'Valid email required' });
        if (!password || password.length < 8) return res.status(400).json({ error: 'Password must be at least 8 characters' });
        const { data, error } = await supabase.auth.signUp({
          email: email.toLowerCase().trim(), password,
          options: { data: { full_name: full_name?.trim() || '' } }
        });
        if (error) return res.status(400).json({ error: error.message });
        return res.status(200).json({
          success: true,
          user: { id: data.user?.id, email: data.user?.email },
          session: data.session,
          message: 'Account created. Check your email to confirm.'
        });
      }

      // ── SIGN IN ────────────────────────────────────────────────
      case 'signin': {
        if (!email || !password) return res.status(400).json({ error: 'Email and password required' });
        const { data, error } = await supabase.auth.signInWithPassword({
          email: email.toLowerCase().trim(), password
        });
        if (error) return res.status(401).json({ error: 'Incorrect email or password' });

        // Fetch subscriptions
        const { data: subs } = await supabase.from('subscriptions')
          .select('app_id, status, current_period_end')
          .eq('user_id', data.user.id).in('status', ['active', 'trialing']);

        // Fetch profile
        const { data: profile } = await supabase.from('profiles')
          .select('full_name, style_data, preferred_language').eq('id', data.user.id).maybeSingle();

        return res.status(200).json({
          success: true,
          user: { id: data.user.id, email: data.user.email, full_name: profile?.full_name, style_data: profile?.style_data, preferred_language: profile?.preferred_language },
          session: { access_token: data.session.access_token, refresh_token: data.session.refresh_token, expires_at: data.session.expires_at },
          subscriptions: subs || []
        });
      }

      // ── REFRESH ────────────────────────────────────────────────
      case 'refresh': {
        if (!refresh_token) return res.status(400).json({ error: 'Refresh token required' });
        const { data, error } = await supabase.auth.refreshSession({ refresh_token });
        if (error) return res.status(401).json({ error: 'Session expired. Please sign in again.' });
        return res.status(200).json({
          success: true,
          session: { access_token: data.session.access_token, refresh_token: data.session.refresh_token, expires_at: data.session.expires_at }
        });
      }

      // ── ME ─────────────────────────────────────────────────────
      case 'me': {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!token) return res.status(401).json({ error: 'No session' });
        const { data: { user }, error } = await supabase.auth.getUser(token);
        if (error || !user) return res.status(401).json({ error: 'Invalid session' });
        const [{ data: profile }, { data: subs }] = await Promise.all([
          supabase.from('profiles').select('*').eq('id', user.id).maybeSingle(),
          supabase.from('subscriptions').select('app_id, status, current_period_end').eq('user_id', user.id).in('status', ['active', 'trialing'])
        ]);
        return res.status(200).json({
          user: { id: user.id, email: user.email, full_name: profile?.full_name, avatar_url: profile?.avatar_url, style_data: profile?.style_data, preferred_language: profile?.preferred_language, created_at: profile?.created_at },
          subscriptions: subs || []
        });
      }

      // ── FORGOT PASSWORD ────────────────────────────────────────
      case 'forgot': {
        if (!email) return res.status(400).json({ error: 'Email required' });
        await supabase.auth.resetPasswordForEmail(email.toLowerCase().trim(), { redirectTo: `${process.env.SITE_URL}/reset` });
        return res.status(200).json({ success: true, message: 'If that account exists, a reset link was sent.' });
      }

      // ── UPDATE PASSWORD ────────────────────────────────────────
      case 'update_password': {
        if (!new_password || new_password.length < 8) return res.status(400).json({ error: 'Password must be at least 8 characters' });
        const { error } = await supabase.auth.updateUser({ password: new_password });
        if (error) return res.status(400).json({ error: error.message });
        return res.status(200).json({ success: true });
      }

      // ── UPDATE PROFILE ─────────────────────────────────────────
      case 'update_profile': {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!token) return res.status(401).json({ error: 'No session' });
        const { data: { user }, error: authErr } = await supabase.auth.getUser(token);
        if (authErr || !user) return res.status(401).json({ error: 'Invalid session' });
        const updates = {};
        if (req.body.full_name !== undefined) updates.full_name = req.body.full_name;
        if (req.body.preferred_language !== undefined) updates.preferred_language = req.body.preferred_language;
        if (req.body.style_data !== undefined) updates.style_data = req.body.style_data;
        await supabase.from('profiles').update({ ...updates, updated_at: new Date().toISOString() }).eq('id', user.id);
        return res.status(200).json({ success: true });
      }

      // ── SIGN OUT ───────────────────────────────────────────────
      case 'signout': {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (token) {
          try { await supabase.auth.admin.signOut(token); } catch {}
        }
        return res.status(200).json({ success: true });
      }

      // ── DELETE ACCOUNT (PRIVACY) ───────────────────────────────
      case 'delete_account': {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!token) return res.status(401).json({ error: 'No session' });
        const { data: { user }, error: authErr } = await supabase.auth.getUser(token);
        if (authErr || !user) return res.status(401).json({ error: 'Invalid session' });
        // Delete all user data — cascades to messages, storage, subscriptions
        await supabase.auth.admin.deleteUser(user.id);
        return res.status(200).json({ success: true, message: 'Account and all data permanently deleted.' });
      }

      default:
        return res.status(400).json({ error: `Unknown action: ${action}` });
    }
  } catch (err) {
    console.error('[SAIRN Auth]', err.message);
    return res.status(500).json({ error: 'Auth service error' });
  }
}
