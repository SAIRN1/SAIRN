// ================================================================
// SAIRN DB SDK — sairn-db-sdk.js
// Drop this script tag into any SAIRN B2B app.
// Gives every app: persist(), load(), saveJob(), loadJobs(),
// saveCustomer(), loadCustomers(), createInvoice(), chargeCard()
// Michael L. Dibert · SAIRN Technologies · 2026
// ================================================================

(function(global) {
'use strict';

const API = 'https://sairn.vercel.app/api';

class SAIRNDb {
  constructor({ shopId, appId }) {
    if (!shopId) throw new Error('SAIRNDb: shopId required');
    this.shopId = shopId;
    this.appId  = appId;
    this._offlineQueue = [];
    this._online = navigator.onLine;

    // Track online/offline
    window.addEventListener('online',  () => { this._online = true;  this._flushQueue(); });
    window.addEventListener('offline', () => { this._online = false; });
  }

  // ── CORE REQUEST ──────────────────────────────────────────────
  async _req(action, method = 'GET', body = null, queueOffline = false) {
    const url = `${API}/db?action=${action}`;
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', 'X-Shop-Id': this.shopId }
    };
    if (body) opts.body = JSON.stringify({ shop_id: this.shopId, ...body });

    try {
      const r = await fetch(url, opts);
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        throw new Error(e.error || `HTTP ${r.status}`);
      }
      return r.json();
    } catch (err) {
      if (!this._online && queueOffline) {
        this._queueOffline(action, method, body);
        return { ok: true, offline: true, queued: true };
      }
      throw err;
    }
  }

  // ── OFFLINE QUEUE ─────────────────────────────────────────────
  _queueOffline(action, method, body) {
    const item = { action, method, body, ts: Date.now() };
    this._offlineQueue.push(item);
    try {
      const stored = JSON.parse(localStorage.getItem('sairn_offline_queue') || '[]');
      stored.push(item);
      localStorage.setItem('sairn_offline_queue', JSON.stringify(stored.slice(-100)));
    } catch {}
  }

  async _flushQueue() {
    const stored = JSON.parse(localStorage.getItem('sairn_offline_queue') || '[]');
    const remaining = [];
    for (const item of stored) {
      try {
        await this._req(item.action, item.method, item.body);
      } catch {
        remaining.push(item);
      }
    }
    localStorage.setItem('sairn_offline_queue', JSON.stringify(remaining));
    if (stored.length > remaining.length) {
      console.log(`[SAIRNDb] Synced ${stored.length - remaining.length} offline items`);
    }
  }

  // ── DASHBOARD ─────────────────────────────────────────────────
  async dashboard() {
    const r = await this._req(`dashboard&shop_id=${this.shopId}`);
    return r.dashboard;
  }

  // ── CUSTOMERS ─────────────────────────────────────────────────
  async loadCustomers(search = '', limit = 50) {
    const r = await this._req(`get_customers&shop_id=${this.shopId}&search=${encodeURIComponent(search)}&limit=${limit}`);
    return r.customers || [];
  }

  async saveCustomer(data) {
    const r = await this._req('save_customer', 'POST', { app_id: this.appId, ...data }, true);
    return r.customer;
  }

  // ── JOBS ──────────────────────────────────────────────────────
  async loadJobs({ status, date, techId, limit = 100 } = {}) {
    let qs = `get_jobs&shop_id=${this.shopId}&limit=${limit}`;
    if (status) qs += `&status=${status}`;
    if (date)   qs += `&date=${date}`;
    if (techId) qs += `&tech_id=${techId}`;
    const r = await this._req(qs);
    return r.jobs || [];
  }

  async loadTodayJobs() {
    return this.loadJobs({ date: new Date().toISOString().slice(0,10) });
  }

  async saveJob(data) {
    const r = await this._req('save_job', 'POST', { app_id: this.appId, ...data }, true);
    return r.job;
  }

  async updateJobStatus(jobId, status, notes = '') {
    const r = await this._req('update_job_status', 'POST', {
      job_id: jobId, status, notes
    }, true);
    return r.job;
  }

  // ── INVOICES ──────────────────────────────────────────────────
  async loadInvoices({ status, customerId } = {}) {
    let qs = `get_invoices&shop_id=${this.shopId}`;
    if (status)     qs += `&status=${status}`;
    if (customerId) qs += `&customer_id=${customerId}`;
    const r = await this._req(qs);
    return r.invoices || [];
  }

  async createInvoice(data) {
    const r = await this._req('create_invoice', 'POST', data);
    return r.invoice;
  }

  // ── PAYMENTS ──────────────────────────────────────────────────
  async setupCard(customerId, customerName, customerEmail) {
    const r = await fetch(`${API}/pay?action=setup_card`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: customerId, shop_id: this.shopId, customer_name: customerName, customer_email: customerEmail })
    });
    return r.json();
  }

  async getCard(customerId) {
    const r = await fetch(`${API}/pay?action=get_card&customer_id=${customerId}`);
    return r.json();
  }

  async chargeCard(invoiceId, amountCents, description = '') {
    const r = await fetch(`${API}/pay?action=charge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ invoice_id: invoiceId, shop_id: this.shopId, amount_cents: amountCents, description })
    });
    return r.json();
  }

  async paymentLink(invoiceId) {
    const r = await fetch(`${API}/pay?action=payment_link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ invoice_id: invoiceId, shop_id: this.shopId })
    });
    return r.json();
  }

  // ── PARTS ─────────────────────────────────────────────────────
  async loadParts(lowStockOnly = false) {
    const qs = `get_parts&shop_id=${this.shopId}${lowStockOnly ? '&low_stock=true' : ''}`;
    const r = await this._req(qs);
    return r.parts || [];
  }

  async savePart(data) {
    const r = await this._req('save_part', 'POST', data, true);
    return r.part;
  }

  // ── SLABS (StoneDesk) ─────────────────────────────────────────
  async loadSlabs({ status, material } = {}) {
    let qs = `get_slabs&shop_id=${this.shopId}`;
    if (status)   qs += `&status=${status}`;
    if (material) qs += `&material=${encodeURIComponent(material)}`;
    const r = await this._req(qs);
    return r.slabs || [];
  }

  async saveSlab(data) {
    const r = await this._req('save_slab', 'POST', data, true);
    return r.slab;
  }

  // ── PROJECTS (SAIRNbuild) ─────────────────────────────────────
  async loadProjects(status = null) {
    const qs = `get_projects&shop_id=${this.shopId}${status ? `&status=${status}` : ''}`;
    const r = await this._req(qs);
    return r.projects || [];
  }

  async saveProject(data) {
    const r = await this._req('save_project', 'POST', data, true);
    return r.project;
  }

  // ── TECHS ─────────────────────────────────────────────────────
  async loadTechs() {
    const r = await this._req(`get_techs&shop_id=${this.shopId}`);
    return r.techs || [];
  }

  async saveTech(data) {
    const r = await this._req('save_tech', 'POST', data);
    return r.tech;
  }

  // ── GL / REPORTING ────────────────────────────────────────────
  async postGL(entries) {
    const r = await this._req('post_gl', 'POST', { entries });
    return r;
  }

  async loadGL(month = null) {
    const qs = `get_gl&shop_id=${this.shopId}${month ? `&month=${month}` : ''}`;
    const r = await this._req(qs);
    return r.entries || [];
  }

  // ── SUBSCRIBE (B2B checkout) ──────────────────────────────────
  async subscribe(plan = 'starter', email, shopName) {
    const r = await fetch(`${API}/pay?action=b2b_checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id: this.appId, plan, email, shop_name: shopName })
    });
    const data = await r.json();
    if (data.url) window.location.href = data.url;
    return data;
  }

  // ── UTILITY ───────────────────────────────────────────────────
  isOnline() { return this._online; }
  getQueueSize() {
    return JSON.parse(localStorage.getItem('sairn_offline_queue') || '[]').length;
  }
}

// Factory: SAIRNDb.connect({ shopId, appId })
SAIRNDb.connect = ({ shopId, appId }) => new SAIRNDb({ shopId, appId });

// Quick shop setup — prompts for shop name and creates it
SAIRNDb.firstRun = async (appId, ownerEmail) => {
  const shopId = localStorage.getItem(`sairn_shop_${appId}`);
  if (shopId) return new SAIRNDb({ shopId, appId });

  const shopName = prompt(`Welcome to ${appId.toUpperCase()}!\n\nEnter your business name:`) || 'My Shop';
  const r = await fetch(`https://sairn.vercel.app/api/db?action=create_shop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app_id: appId, shop_name: shopName, owner_email: ownerEmail || 'demo@sairn.com' })
  });
  const data = await r.json();
  if (data.ok && data.shop?.id) {
    localStorage.setItem(`sairn_shop_${appId}`, data.shop.id);
    return new SAIRNDb({ shopId: data.shop.id, appId });
  }
  throw new Error('Could not create shop: ' + (data.error || 'unknown'));
};

global.SAIRNDb = SAIRNDb;
})(typeof window !== 'undefined' ? window : global);
