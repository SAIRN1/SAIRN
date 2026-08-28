import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export default async function handler(req, res) {
  const origin = req.headers.origin;
  if (origin) res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { action, org_id, location_id, location_name, app_id, query, insight, category } = req.body || {};

  if (!org_id) return res.status(400).json({ error: 'org_id required' });

  try {
    if (action === 'save') {
      // Save an insight from this location
      if (!insight) return res.status(400).json({ error: 'insight required' });
      
      const { error } = await supabase
        .from('org_intelligence')
        .insert({
          org_id,
          location_id: location_id || null,
          app_id: app_id || 'unknown',
          category: category || 'general',
          insight: insight.slice(0, 500),
          created_by: location_name || 'Unknown Location'
        });

      if (error) throw error;
      return res.status(200).json({ success: true });
    }

    if (action === 'query') {
      // Get relevant insights from other locations
      const { data, error } = await supabase
        .from('org_intelligence')
        .select('insight, category, created_by, created_at')
        .eq('org_id', org_id)
        .eq('app_id', app_id || 'unknown')
        .neq('location_id', location_id || 'none')
        .order('created_at', { ascending: false })
        .limit(10);

      if (error) throw error;

      // Simple relevance filter — find insights mentioning query keywords
      const keywords = (query || '').toLowerCase().split(' ')
        .filter(w => w.length > 3)
        .slice(0, 5);

      let relevant = data || [];
      if (keywords.length > 0) {
        relevant = relevant.filter(r =>
          keywords.some(kw => r.insight.toLowerCase().includes(kw))
        );
      }

      // Fall back to most recent if no keyword matches
      if (relevant.length === 0) relevant = (data || []).slice(0, 3);

      return res.status(200).json({
        insights: relevant.slice(0, 5).map(r => ({
          insight: r.insight,
          location: r.created_by || 'Another location',
          category: r.category,
          date: r.created_at?.slice(0, 10)
        }))
      });
    }

    return res.status(400).json({ error: 'Invalid action' });

  } catch (err) {
    console.error('OIL error:', err);
    return res.status(500).json({ error: err.message });
  }
}
