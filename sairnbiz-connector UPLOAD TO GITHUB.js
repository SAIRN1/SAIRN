/**
 * SAIRNbiz Connector v1.0
 * Drop-in module for all 11 SAIRN B2B apps.
 * Paste one <script> tag into any app to connect it to the SAIRNbiz backbone.
 *
 * Usage:
 *   SAIRNbiz.sendEvent('stonedesk', 'job_completed', { job_id: 'J-001', revenue: 4200 });
 *   SAIRNbiz.getEmployees();
 *   SAIRNbiz.getPayrollSummary();
 *   SAIRNbiz.getFinancialSummary();
 *   SAIRNbiz.renderPanel('container-id', '#16C762');
 */

const SAIRNbiz = (() => {

  // === CONFIG ===
  const BRIDGE_URL = 'https://sairn.vercel.app/api/bridge';
  const STORAGE_KEY = 'sairnbiz_data';
  const VERSION = '1.0';

  // === LOCAL STORE (same-device fallback) ===
  function lsGet(key) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const store = JSON.parse(raw);
      return key ? store[key] : store;
    } catch(e) { return null; }
  }

  function lsSet(key, value) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const store = raw ? JSON.parse(raw) : {};
      store[key] = value;
      store._updated = new Date().toISOString();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
      return true;
    } catch(e) { return false; }
  }

  // === BRIDGE (cross-device) ===
  async function bridgePost(action, payload) {
    try {
      const res = await fetch(BRIDGE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, payload, version: VERSION, ts: Date.now() })
      });
      if (!res.ok) throw new Error('Bridge ' + res.status);
      return await res.json();
    } catch(e) {
      // Silent fallback to localStorage
      return null;
    }
  }

  async function bridgeGet(action, params) {
    try {
      const qs = new URLSearchParams({ action, ...params }).toString();
      const res = await fetch(BRIDGE_URL + '?' + qs);
      if (!res.ok) throw new Error('Bridge ' + res.status);
      return await res.json();
    } catch(e) {
      return null;
    }
  }

  // === DEMO DATA (used when bridge is unavailable) ===
  const DEMO_EMPLOYEES = [
    { id: 'EMP-001', name: 'Maria Santos', role: 'Project Manager', dept: 'Operations', pay_type: 'salary', pay_rate: 72000, status: 'active' },
    { id: 'EMP-002', name: 'James Lee',    role: 'Sales Rep',       dept: 'Sales',      pay_type: 'salary_commission', pay_rate: 55000, commission: 0.10, status: 'onboarding' },
    { id: 'EMP-003', name: 'Tom Nguyen',   role: 'Lead Installer',  dept: 'Operations', pay_type: 'hourly', pay_rate: 28, status: 'active' },
    { id: 'EMP-004', name: 'Sarah Kim',    role: 'Office Manager',  dept: 'Admin',      pay_type: 'salary', pay_rate: 52000, status: 'active' }
  ];

  const DEMO_PAYROLL = {
    period: 'June 2025 - Period 2',
    gross_pay: 71240,
    net_pay: 52320,
    taxes_withheld: 18920,
    employer_taxes: 6180,
    next_run: '2025-06-28',
    employees: [
      { name: 'Maria Santos', gross: 3000.00, net: 2125.50, status: 'approved' },
      { name: 'James Lee',    gross: 4200.00, net: 2975.70, status: 'pending'  },
      { name: 'Tom Nguyen',   gross: 2240.00, net: 1587.04, status: 'approved' },
      { name: 'Sarah Kim',    gross: 2166.67, net: 1535.09, status: 'approved' }
    ]
  };

  const DEMO_FINANCIALS = {
    cash_position: 284120,
    accounts_receivable: 94000,
    accounts_payable: 41000,
    monthly_revenue: 187000,
    monthly_payroll: 142000,
    gross_margin: 0.38,
    gl_last_entry: '2025-06-14',
    overdue_invoices: 2,
    overdue_amount: 3200
  };

  // === PUBLIC API ===

  /**
   * Send an event from a vertical app to SAIRNbiz.
   * Tries bridge first, falls back to localStorage.
   *
   * @param {string} app_id   - e.g. 'stonedesk', 'sairnbuild'
   * @param {string} event    - e.g. 'job_completed', 'invoice_created'
   * @param {object} data     - event payload
   */
  async function sendEvent(app_id, event, data) {
    const payload = { app_id, event, data, ts: new Date().toISOString() };

    // Try bridge
    const bridgeResult = await bridgePost('event', payload);
    if (bridgeResult) return bridgeResult;

    // Fallback: localStorage event log
    const log = lsGet('events') || [];
    log.unshift(payload);
    if (log.length > 200) log.length = 200;
    lsSet('events', log);
    return { ok: true, source: 'localStorage' };
  }

  /**
   * Get employee roster from SAIRNbiz.
   * Returns live bridge data or demo data.
   */
  async function getEmployees() {
    const bridge = await bridgeGet('employees', {});
    if (bridge && bridge.employees) return bridge.employees;
    const local = lsGet('employees');
    if (local) return local;
    return DEMO_EMPLOYEES;
  }

  /**
   * Get current payroll summary.
   */
  async function getPayrollSummary() {
    const bridge = await bridgeGet('payroll', {});
    if (bridge && bridge.payroll) return bridge.payroll;
    const local = lsGet('payroll');
    if (local) return local;
    return DEMO_PAYROLL;
  }

  /**
   * Get financial summary (cash, AR, AP, revenue, margin).
   */
  async function getFinancialSummary() {
    const bridge = await bridgeGet('financials', {});
    if (bridge && bridge.financials) return bridge.financials;
    const local = lsGet('financials');
    if (local) return local;
    return DEMO_FINANCIALS;
  }

  /**
   * Render the SAIRNbiz mini-panel into a container element.
   * Shows live people + money KPIs and a sync button.
   *
   * @param {string} containerId  - DOM element ID to render into
   * @param {string} accentColor  - app's brand color (e.g. '#16C762')
   */
  async function renderPanel(containerId, accentColor) {
    const el = document.getElementById(containerId);
    if (!el) { console.warn('SAIRNbiz: container not found:', containerId); return; }

    const [employees, payroll, financials] = await Promise.all([
      getEmployees(), getPayrollSummary(), getFinancialSummary()
    ]);

    const accent = accentColor || '#14B8A6';
    const teal = '#14B8A6';
    const tealDark = '#0F766E';
    const tealLight = '#F0FDFA';

    el.innerHTML = `
      <div style="background:${tealLight};border:1px solid #CCFBF1;border-radius:10px;padding:16px;font-family:'Segoe UI',system-ui,sans-serif;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
          <div style="font-size:13px;font-weight:800;color:${tealDark};">
            <span style="background:${tealDark};color:white;border-radius:6px;padding:3px 8px;font-size:11px;font-weight:700;margin-right:6px;-webkit-print-color-adjust:exact;print-color-adjust:exact;">SB</span>
            SAIRNbiz Backbone
          </div>
          <button onclick="SAIRNbiz.syncAll()" style="background:${teal};color:white;border:none;border-radius:6px;padding:4px 10px;font-size:11px;font-weight:700;cursor:pointer;">Sync All</button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;">
          <div style="background:white;border-radius:8px;padding:10px;border:1px solid #E2E8F0;text-align:center;">
            <div style="font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.4px;">Employees</div>
            <div style="font-size:20px;font-weight:900;color:#1E293B;">${employees.length || 47}</div>
          </div>
          <div style="background:white;border-radius:8px;padding:10px;border:1px solid #E2E8F0;text-align:center;">
            <div style="font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.4px;">Payroll/Mo</div>
            <div style="font-size:20px;font-weight:900;color:#1E293B;">$${Math.round((payroll.gross_pay||71240)/1000)}K</div>
          </div>
          <div style="background:white;border-radius:8px;padding:10px;border:1px solid #E2E8F0;text-align:center;">
            <div style="font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.4px;">Cash</div>
            <div style="font-size:20px;font-weight:900;color:#1E293B;">$${Math.round((financials.cash_position||284120)/1000)}K</div>
          </div>
        </div>
        <div style="font-size:11px;color:#64748B;text-align:right;">
          Last sync: ${new Date().toLocaleTimeString()} &mdash;
          <a href="#" style="color:${tealDark};font-weight:700;text-decoration:none;" onclick="SAIRNbiz.openHub()">Open SAIRNbiz &rarr;</a>
        </div>
      </div>`;
  }

  /**
   * Sync all data from this app to SAIRNbiz bridge.
   */
  async function syncAll() {
    await bridgePost('sync_all', { ts: new Date().toISOString() });
    console.log('SAIRNbiz: sync_all sent');
  }

  /**
   * Open SAIRNbiz in a new tab (if hosted on same domain/Vercel).
   */
  function openHub() {
    window.open('/sairnbiz.html', '_blank');
  }

  /**
   * Standard GL post — send a financial transaction to SAIRNbiz.
   * Called automatically when a job is completed, invoice paid, etc.
   *
   * @param {string} app_id
   * @param {object} entry  - { date, description, account, debit, credit }
   */
  async function postToGL(app_id, entry) {
    return sendEvent(app_id, 'gl_entry', entry);
  }

  /**
   * Get a single employee by ID or name.
   */
  async function getEmployee(identifier) {
    const employees = await getEmployees();
    return employees.find(e =>
      e.id === identifier ||
      e.name.toLowerCase().includes(identifier.toLowerCase())
    ) || null;
  }

  // Expose public API
  return {
    sendEvent,
    getEmployees,
    getEmployee,
    getPayrollSummary,
    getFinancialSummary,
    renderPanel,
    syncAll,
    openHub,
    postToGL,
    version: VERSION
  };

})();

// Auto-announce on load
console.log('SAIRNbiz Connector v' + SAIRNbiz.version + ' loaded. Bridge: https://sairn.vercel.app/api/bridge');
