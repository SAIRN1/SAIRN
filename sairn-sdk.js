// ═══════════════════════════════════════════════════════════════════
//  SAIRN Technologies — sairn-sdk.js  (v3 Production)
//  Drop-in for every SAIRN app. Handles everything:
//    auth · sessions · subscriptions · claude calls
//    storage · conversation history · style memory · privacy
//  Michael L. Dibert · HONEY COMB Platform · 2026
// ═══════════════════════════════════════════════════════════════════

(function(global) {
'use strict';

const BASE = 'https://sairn.vercel.app';
const SK   = 'sairn_v3_session';
const STK  = 'sairn_style_v3';

function ls_get(k)    { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } }
function ls_set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }
function ls_del(k)    { try { localStorage.removeItem(k); } catch {} }
function isExpired(e) { return !e || (Date.now()/1000) > (e - 90); }

function saveSession(s, u, subs) {
  ls_set(SK, { access_token: s.access_token, refresh_token: s.refresh_token, expires_at: s.expires_at, user: u, subscriptions: subs||[] });
}

class SAIRNClient {
  constructor({ appId, accentColor }={}) {
    if (!appId) throw new Error('SAIRNClient: appId required');
    this.appId  = appId;
    this.accent = accentColor || '#38BDF8';
    this._s     = null;  // session
    this._u     = null;  // user
    this._subs  = [];
    this._cid   = null;  // conversation_id
    this._hist  = [];    // message history
    this._style = ls_get(STK) || {};
    this._ev    = {};
  }

  // ── INIT ─────────────────────────────────────────────────────────
  async init() {
    const stored = ls_get(SK);
    if (!stored) return { authenticated: false };
    if (isExpired(stored.expires_at)) {
      const ok = await this._refresh(stored.refresh_token);
      if (!ok) { ls_del(SK); return { authenticated: false }; }
    } else {
      this._s    = { access_token: stored.access_token, refresh_token: stored.refresh_token };
      this._u    = stored.user;
      this._subs = stored.subscriptions || [];
    }
    this._emit('auth', { authenticated: true, user: this._u });
    return { authenticated: true, user: this._u, subscriptions: this._subs };
  }

  // ── AUTH ──────────────────────────────────────────────────────────
  async signUp(email, password, fullName) {
    const d = await this._post('/api/auth', { action:'signup', email, password, full_name:fullName });
    if (!d.success) throw new Error(d.error);
    return d;
  }

  async signIn(email, password) {
    const d = await this._post('/api/auth', { action:'signin', email, password });
    if (!d.success) throw new Error(d.error);
    saveSession(d.session, d.user, d.subscriptions);
    this._s = d.session; this._u = d.user; this._subs = d.subscriptions||[];
    if (d.user?.style_data) { this._style = {...this._style, ...d.user.style_data}; ls_set(STK, this._style); }
    this._emit('auth', { authenticated:true, user:this._u });
    return d;
  }

  async signOut() {
    try { await this._post('/api/auth', { action:'signout' }, true); } catch {}
    ls_del(SK); this._s=null; this._u=null; this._subs=[]; this._cid=null; this._hist=[];
    this._emit('auth', { authenticated:false });
  }

  async forgotPassword(email) { return this._post('/api/auth', { action:'forgot', email }); }

  async deleteAccount() {
    if (!confirm('Permanently delete your account and ALL data? Cannot be undone.')) return;
    const d = await this._post('/api/auth', { action:'delete_account' }, true);
    if (d.success) { ls_del(SK); ls_del(STK); location.reload(); }
    return d;
  }

  // ── STATE ─────────────────────────────────────────────────────────
  isAuthenticated()   { return !!this._s?.access_token; }
  hasSubscription(id) { return this._subs.some(s => s.app_id === (id||this.appId)); }
  getUser()           { return this._u; }
  getSubscriptions()  { return this._subs; }

  // ── CLAUDE ────────────────────────────────────────────────────────
  async ask({ userMessage, system, isDemo, maxTokens, resetThread }) {
    if (resetThread) { this._cid=null; this._hist=[]; }
    this._hist.push({ role:'user', content:userMessage });

    const headers = { 'Content-Type':'application/json' };
    if (this.isAuthenticated() && !isDemo) headers['Authorization'] = `Bearer ${this._s.access_token}`;

    const body = {
      model: 'claude-haiku-4-5-20251001',
      max_tokens: Math.min(maxTokens||1000, 2000),
      messages: this._hist.slice(-24),
      app_id: this.appId,
      is_demo: !!isDemo,
      conversation_id: this._cid||undefined
    };
    if (system) body.system = this._buildSys(system);

    const r    = await fetch(`${BASE}/api/claude`, { method:'POST', headers, body:JSON.stringify(body) });
    const data = await r.json();

    if (r.status === 401) {
      const ok = await this._refresh(ls_get(SK)?.refresh_token);
      if (ok) return this.ask({ userMessage, system, isDemo, maxTokens });
      this._emit('session_expired'); throw new Error('SESSION_EXPIRED');
    }
    if (r.status === 402) { this._emit('subscription_required', { appId:this.appId }); throw new Error('SUBSCRIPTION_REQUIRED'); }
    if (r.status === 429) throw new Error('RATE_LIMITED');
    if (!r.ok) throw new Error(data.error?.message || 'Claude error');

    const text = data.content?.[0]?.text || '';
    this._hist.push({ role:'assistant', content:text });
    if (data.conversation_id) this._cid = data.conversation_id;
    this._learn(userMessage, text);
    return { text, conversation_id:this._cid };
  }

  // ── STORAGE ───────────────────────────────────────────────────────
  async store(key, value) {
    this._auth();
    await this._post('/api/storage', { app_id:this.appId, key, value }, true);
  }

  async retrieve(key) {
    this._auth();
    const r = await fetch(`${BASE}/api/storage?app_id=${this.appId}&key=${encodeURIComponent(key)}`, { headers:this._ah() });
    const d = (await r.json()).data;
    const v = d?.value;
    return v?.data !== undefined ? v.data : v;
  }

  async retrieveAll(prefix) {
    this._auth();
    const url = `${BASE}/api/storage?app_id=${this.appId}${prefix?`&prefix=${encodeURIComponent(prefix)}`:''}`;
    return (await (await fetch(url, { headers:this._ah() })).json()).data || [];
  }

  async remove(key) {
    this._auth();
    await fetch(`${BASE}/api/storage`, { method:'DELETE', headers:{...this._ah(),'Content-Type':'application/json'}, body:JSON.stringify({ app_id:this.appId, key }) });
  }

  async clearAll() {
    this._auth();
    await this._post('/api/storage', { app_id:this.appId, action:'clear_all' }, true);
    this._cid=null; this._hist=[];
  }

  // ── CONVERSATIONS ─────────────────────────────────────────────────
  async getConversations() {
    this._auth();
    return (await (await fetch(`${BASE}/api/storage?app_id=${this.appId}&action=get_conversations`, { headers:this._ah() })).json()).data || [];
  }

  async loadConversation(id) {
    this._auth();
    const msgs = (await (await fetch(`${BASE}/api/storage?app_id=${this.appId}&action=get_messages&key=${id}`, { headers:this._ah() })).json()).data || [];
    this._cid  = id;
    this._hist = msgs.map(m => ({ role:m.role, content:m.content }));
    return msgs;
  }

  async deleteConversation(id) {
    this._auth();
    await this._post('/api/storage', { app_id:this.appId, action:'delete_conversation', key:id }, true);
    if (this._cid === id) { this._cid=null; this._hist=[]; }
  }

  newThread() { this._cid=null; this._hist=[]; }

  // ── STYLE MEMORY ─────────────────────────────────────────────────
  _buildSys(base) {
    const ctx = this._styleCtx();
    return ctx ? `${base}\n\n${ctx}` : base;
  }

  _styleCtx() {
    const s = this._style;
    if (!s.count || s.count < 8) return '';
    const p = [];
    if (s.formal)    p.push('prefers formal language');
    else if (s.casual) p.push('prefers casual language');
    if (s.detailed)  p.push('prefers detailed responses');
    else if (s.brief) p.push('prefers concise responses');
    if (s.technical) p.push('has technical background');
    return p.length ? `HONEY COMB style memory: User ${p.join(', ')}.` : '';
  }

  _learn(u, _a) {
    const s = this._style;
    s.count = (s.count||0) + 1;
    if (/\b(furthermore|pursuant|regarding|aforementioned)\b/i.test(u)) s.formal    = true;
    else if (/\b(hey|yeah|lol|btw|gonna|tbh)\b/i.test(u))              s.casual    = true;
    if (u.length > 200)     s.detailed  = true;
    else if (u.length < 35) s.brief     = true;
    if (/\b(api|function|code|schema|deploy|query)\b/i.test(u))        s.technical = true;
    ls_set(STK, s);
    if (s.count % 10 === 0 && this.isAuthenticated()) {
      this._post('/api/auth', { action:'update_profile', style_data:s }, true).catch(()=>{});
    }
  }

  // ── AUTH MODAL ────────────────────────────────────────────────────
  showAuthModal(appName) {
    let m = document.getElementById('_sm');
    if (m) { m.style.display='flex'; return; }
    m = document.createElement('div');
    m.id = '_sm';
    m.style.cssText = 'position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.82);backdrop-filter:blur(10px);font-family:system-ui,sans-serif';
    const a = this.accent;
    m.innerHTML = `<div style="background:#111;border:1px solid rgba(255,255,255,0.11);border-radius:18px;padding:36px;width:100%;max-width:400px;margin:16px;position:relative">
      <button onclick="document.getElementById('_sm').style.display='none'" style="position:absolute;top:14px;right:16px;background:none;border:none;color:rgba(255,255,255,0.3);font-size:18px;cursor:pointer">✕</button>
      <div style="text-align:center;margin-bottom:22px">
        <div style="font-size:21px;font-weight:600;color:#fff;margin-bottom:5px">${appName||'SAIRN'}</div>
        <div style="font-size:13px;color:rgba(255,255,255,0.38)">Sign in to save your work across devices</div>
      </div>
      <div id="_sm_e" style="display:none;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.28);border-radius:8px;padding:10px 14px;font-size:13px;color:#f87171;margin-bottom:12px"></div>
      <div id="_sm_o" style="display:none;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.22);border-radius:8px;padding:10px 14px;font-size:13px;color:#34d399;margin-bottom:12px"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;border:1px solid rgba(255,255,255,0.09);border-radius:8px;overflow:hidden;margin-bottom:18px">
        <button id="_sm_ti" onclick="_smc.tab('in')" style="padding:9px;font-size:13px;font-weight:500;background:${a};color:#000;border:none;cursor:pointer">Sign In</button>
        <button id="_sm_tu" onclick="_smc.tab('up')" style="padding:9px;font-size:13px;font-weight:500;background:transparent;color:rgba(255,255,255,0.38);border:none;cursor:pointer">Sign Up</button>
      </div>
      <div id="_sm_nw" style="display:none;margin-bottom:11px"><input id="_sm_n" type="text" placeholder="Full name" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.09);border-radius:8px;padding:12px 14px;color:#fff;font-size:14px;outline:none;box-sizing:border-box"></div>
      <input id="_sm_em" type="email" placeholder="your@email.com" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.09);border-radius:8px;padding:12px 14px;color:#fff;font-size:14px;outline:none;margin-bottom:11px;box-sizing:border-box">
      <input id="_sm_pw" type="password" placeholder="Password (min 8 characters)" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.09);border-radius:8px;padding:12px 14px;color:#fff;font-size:14px;outline:none;margin-bottom:16px;box-sizing:border-box">
      <button id="_sm_b" onclick="_smc.submit()" style="width:100%;padding:14px;background:${a};color:#000;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer">Sign In</button>
      <div style="text-align:center;margin-top:11px"><button onclick="_smc.forgot()" style="font-size:12px;color:rgba(255,255,255,0.22);background:none;border:none;cursor:pointer">Forgot password?</button></div>
      <div style="margin-top:14px;padding-top:14px;border-top:1px solid rgba(255,255,255,0.06);font-size:11px;color:rgba(255,255,255,0.18);text-align:center;line-height:1.6">🔒 Supabase encrypted · HONEY COMB Privacy Firewall<br>Your conversations are yours. SAIRN Technologies.</div>
    </div>`;
    document.body.appendChild(m);
    m.addEventListener('click', e => { if (e.target===m) m.style.display='none'; });
    const cl = this;
    window._smc = {
      mode:'in',
      tab(mode) {
        this.mode=mode; const u=mode==='up';
        document.getElementById('_sm_ti').style.cssText=`padding:9px;font-size:13px;font-weight:500;background:${u?'transparent':a};color:${u?'rgba(255,255,255,0.38)':'#000'};border:none;cursor:pointer`;
        document.getElementById('_sm_tu').style.cssText=`padding:9px;font-size:13px;font-weight:500;background:${u?a:'transparent'};color:${u?'#000':'rgba(255,255,255,0.38)'};border:none;cursor:pointer`;
        document.getElementById('_sm_nw').style.display=u?'block':'none';
        document.getElementById('_sm_b').textContent=u?'Create Account':'Sign In';
        document.getElementById('_sm_e').style.display='none';
      },
      async submit() {
        const em=document.getElementById('_sm_em').value.trim(), pw=document.getElementById('_sm_pw').value, nm=document.getElementById('_sm_n').value.trim();
        const btn=document.getElementById('_sm_b'), err=document.getElementById('_sm_e'), ok=document.getElementById('_sm_o');
        err.style.display='none'; ok.style.display='none'; btn.disabled=true; btn.style.opacity='0.5';
        btn.textContent=this.mode==='up'?'Creating...':'Signing in...';
        try {
          if (this.mode==='up') { await cl.signUp(em,pw,nm); ok.textContent='✓ Account created! Check your email, then sign in.'; ok.style.display='block'; this.tab('in'); }
          else { await cl.signIn(em,pw); document.getElementById('_sm').style.display='none'; window.dispatchEvent(new CustomEvent('sairn:signed_in',{detail:{user:cl.getUser()}})); }
        } catch(e) { err.textContent=e.message; err.style.display='block'; }
        btn.disabled=false; btn.style.opacity='1'; btn.textContent=this.mode==='up'?'Create Account':'Sign In';
      },
      async forgot() {
        const em=document.getElementById('_sm_em').value.trim();
        if (!em) { document.getElementById('_sm_e').textContent='Enter your email first.'; document.getElementById('_sm_e').style.display='block'; return; }
        await cl.forgotPassword(em);
        document.getElementById('_sm_o').textContent='If that account exists, a reset link was sent.'; document.getElementById('_sm_o').style.display='block';
      }
    };
  }

  showAccountBar() {
    if (!this.isAuthenticated()) return;
    document.getElementById('_sab')?.remove();
    const bar = document.createElement('div');
    bar.id='_sab';
    bar.style.cssText=`position:fixed;bottom:14px;right:14px;z-index:9000;display:flex;align-items:center;gap:8px;background:rgba(17,17,17,0.96);border:1px solid rgba(255,255,255,0.09);border-radius:100px;padding:7px 14px;font-family:system-ui,sans-serif;font-size:12px;color:rgba(255,255,255,0.5);backdrop-filter:blur(12px)`;
    const pro = this.hasSubscription();
    bar.innerHTML=`<span style="width:6px;height:6px;border-radius:50%;background:${pro?'#10b981':'#6b7280'}"></span><span>${(this._u?.email||'').split('@')[0]}</span>${pro?`<span style="color:${this.accent};font-weight:500;font-size:11px">PRO</span>`:''}<button onclick="window._sc.signOut().then(()=>location.reload())" style="background:none;border:none;color:rgba(255,255,255,0.2);cursor:pointer;font-size:11px;padding:0;margin-left:2px">out</button>`;
    window._sc=this;
    document.body.appendChild(bar);
  }

  // ── INTERNALS ─────────────────────────────────────────────────────
  _auth() { if (!this.isAuthenticated()) throw new Error('Authentication required'); }
  _ah()   { return { 'Content-Type':'application/json', 'Authorization':`Bearer ${this._s.access_token}` }; }

  async _post(path, body, auth) {
    const h = { 'Content-Type':'application/json' };
    if (auth && this._s?.access_token) h['Authorization'] = `Bearer ${this._s.access_token}`;
    return (await fetch(`${BASE}${path}`, { method:'POST', headers:h, body:JSON.stringify(body) })).json();
  }

  async _refresh(rt) {
    if (!rt) return false;
    try {
      const d = await this._post('/api/auth', { action:'refresh', refresh_token:rt });
      if (!d.success) return false;
      const me = await this._post('/api/auth', { action:'me' }, false);
      saveSession(d.session, me.user, me.subscriptions);
      this._s=d.session; this._u=me.user; this._subs=me.subscriptions||[];
      return true;
    } catch { return false; }
  }

  on(e,cb) { (this._ev[e]=this._ev[e]||[]).push(cb); return ()=>{this._ev[e]=(this._ev[e]||[]).filter(l=>l!==cb)}; }
  _emit(e,d) { (this._ev[e]||[]).forEach(cb=>{try{cb(d)}catch{}}); }
}

SAIRNClient.create = (appId, accent) => new SAIRNClient({ appId, accentColor:accent });
global.SAIRNClient = SAIRNClient;

})(typeof window !== 'undefined' ? window : global);
