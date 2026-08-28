/**
 * SAIRNbiz Connector v2.0
 * ========================
 * SAIRNbiz is the People + Money backbone for the entire SAIRN B2B suite.
 *
 * ARCHITECTURE:
 *   - SAIRNbiz is sold as a standalone product (HR + Accounting in one app)
 *   - SAIRNbiz is included FREE with every SAIRN B2B subscription
 *   - All 11 B2B verticals connect to SAIRNbiz for HR and Money data
 *   - SAIRNhr and SAIRNacc no longer exist as standalones -- merged into SAIRNbiz
 *
 * CONNECTED APPS (all get SAIRNbiz free):
 *   StoneDesk, SAIRNbuild, SAIRNlaw, SAIRNscape, SAIRNdesign,
 *   SAIRNcode, SAIRNcare, SAIRNvet, SAIRNfuneral, SAIRNmechanical
 *   + any future B2B vertical
 *
 * USAGE:
 *   SAIRNbiz.sendEvent('stonedesk', 'job_completed', { job_id: 'J-001', revenue: 4200 });
 *   SAIRNbiz.getEmployees();
 *   SAIRNbiz.getPayrollSummary();
 *   SAIRNbiz.getFinancialSummary();
 *   SAIRNbiz.renderPanel('container-id', '#AppColor');
 *   SAIRNbiz.postToGL('stonedesk', { description: 'Job J-001', debit: 4200, credit: 0 });
 */

const SAIRNbiz = (() => {

  const BRIDGE_URL = 'https://sairn.vercel.app/api/bridge';
  const STORAGE_KEY = 'sairnbiz_data';
  const VERSION = '2.0';

  // All B2B apps that get SAIRNbiz free
  const B2B_APPS = [
    'stonedesk', 'sairnbuild', 'sairnlaw', 'sairnscape', 'sairndesign',
    'sairncode', 'sairncare', 'sairnvet', 'sairnfuneral', 'sairnmechanical'
  ];

  // localStorage helpers
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

  // Bridge API (cross-device sync)
  async function bridgePost(action, payload) {
    try {
      const res = await fetch(BRIDGE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, payload, version: VERSION, ts: Date.now() })
      });
      if (!res.ok) throw new Error('Bridge ' + res.status);
      return await res.json();
    } catch(e) { return null; }
  }

  async function bridgeGet(action, params) {
    try {
      const qs = new URLSearchParams({ action, ...params }).toString();
      const res = await fetch(BRIDGE_URL + '?' + qs);
      if (!res.ok) throw new Error('Bridge ' + res.status);
      return await res.json();
    } catch(e) { return null; }
  }

  // Demo data (fallback when bridge unavailable)
  const DEMO_EMPLOYEES = [
    { id: 'EMP-001', name: 'Maria Santos',  role: 'Project Manager', dept: 'Operations', pay_type: 'salary',            pay_rate: 72000, status: 'active'     },
    { id: 'EMP-002', name: 'James Lee',     role: 'Sales Rep',       dept: 'Sales',      pay_type: 'salary_commission', pay_rate: 55000, status: 'onboarding' },
    { id: 'EMP-003', name: 'Tom Nguyen',    role: 'Lead Installer',  dept: 'Operations', pay_type: 'hourly',            pay_rate: 28,    status: 'active'     },
    { id: 'EMP-004', name: 'Sarah Kim',     role: 'Office Manager',  dept: 'Admin',      pay_type: 'salary',            pay_rate: 52000, status: 'active'     }
  ];

  const DEMO_PAYROLL = {
    period: 'June 2025 - Period 2',
    gross_pay: 71240, net_pay: 52320, taxes_withheld: 18920, employer_taxes: 6180,
    next_run: '2025-06-28',
    employees: [
      { name: 'Maria Santos', gross: 3000.00, net: 2125.50, status: 'approved' },
      { name: 'James Lee',    gross: 4200.00, net: 2975.70, status: 'pending'  },
      { name: 'Tom Nguyen',   gross: 2240.00, net: 1587.04, status: 'approved' },
      { name: 'Sarah Kim',    gross: 2166.67, net: 1535.09, status: 'approved' }
    ]
  };

  const DEMO_FINANCIALS = {
    cash_position: 284120, accounts_receivable: 94000, accounts_payable: 41000,
    monthly_revenue: 187000, monthly_payroll: 142000, gross_margin: 0.38,
    gl_last_entry: '2025-06-14', overdue_invoices: 2, overdue_amount: 3200
  };

  // PUBLIC API

  async function sendEvent(app_id, event, data) {
    const payload = { app_id, event, data, ts: new Date().toISOString() };
    const result = await bridgePost('event', payload);
    if (result) return result;
    const log = lsGet('events') || [];
    log.unshift(payload);
    if (log.length > 200) log.length = 200;
    lsSet('events', log);
    return { ok: true, source: 'localStorage' };
  }

  async function getEmployees() {
    const bridge = await bridgeGet('employees', {});
    if (bridge && bridge.employees) return bridge.employees;
    return lsGet('employees') || DEMO_EMPLOYEES;
  }

  async function getEmployee(identifier) {
    const employees = await getEmployees();
    return employees.find(e =>
      e.id === identifier || e.name.toLowerCase().includes(identifier.toLowerCase())
    ) || null;
  }

  async function getPayrollSummary() {
    const bridge = await bridgeGet('payroll', {});
    if (bridge && bridge.payroll) return bridge.payroll;
    return lsGet('payroll') || DEMO_PAYROLL;
  }

  async function getFinancialSummary() {
    const bridge = await bridgeGet('financials', {});
    if (bridge && bridge.financials) return bridge.financials;
    return lsGet('financials') || DEMO_FINANCIALS;
  }

  async function postToGL(app_id, entry) {
    return sendEvent(app_id, 'gl_entry', {
      ...entry, app_id, ts: new Date().toISOString()
    });
  }

  async function syncAll(app_id) {
    const result = await bridgePost('sync_all', { app_id, ts: new Date().toISOString() });
    console.log('SAIRNbiz: sync_all sent from ' + app_id);
    return result;
  }

  async function renderPanel(containerId, accentColor) {
    const el = document.getElementById(containerId);
    if (!el) { console.warn('SAIRNbiz: container not found:', containerId); return; }

    const [employees, payroll, financials] = await Promise.all([
      getEmployees(), getPayrollSummary(), getFinancialSummary()
    ]);

    const tealDark = '#0F766E';
    const tealLight = '#F0FDFA';
    const tealMid = '#CCFBF1';

    el.innerHTML =
      '<div style="background:' + tealLight + ';border:1px solid ' + tealMid + ';border-radius:10px;padding:16px;font-family:Segoe UI,system-ui,sans-serif;">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">' +
          '<div style="font-size:13px;font-weight:800;color:' + tealDark + ';">' +
            '<span style="background:' + tealDark + ';color:white;border-radius:6px;padding:3px 8px;font-size:11px;font-weight:700;margin-right:6px;">SB</span>' +
            'SAIRNbiz Backbone' +
          '</div>' +
          '<button onclick="SAIRNbiz.syncAll()" style="background:#14B8A6;color:white;border:none;border-radius:6px;padding:4px 10px;font-size:11px;font-weight:700;cursor:pointer;">Sync</button>' +
        '</div>' +
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">' +
          '<div style="background:white;border-radius:8px;padding:10px;border:1px solid #E2E8F0;text-align:center;">' +
            '<div style="font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;">Employees</div>' +
            '<div style="font-size:20px;font-weight:900;color:#1E293B;">' + (employees.length || 47) + '</div>' +
          '</div>' +
          '<div style="background:white;border-radius:8px;padding:10px;border:1px solid #E2E8F0;text-align:center;">' +
            '<div style="font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;">Payroll</div>' +
            '<div style="font-size:20px;font-weight:900;color:#1E293B;">$' + Math.round((payroll.gross_pay || 71240) / 1000) + 'K</div>' +
          '</div>' +
          '<div style="background:white;border-radius:8px;padding:10px;border:1px solid #E2E8F0;text-align:center;">' +
            '<div style="font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;">Cash</div>' +
            '<div style="font-size:20px;font-weight:900;color:#1E293B;">$' + Math.round((financials.cash_position || 284120) / 1000) + 'K</div>' +
          '</div>' +
        '</div>' +
        '<div style="font-size:11px;color:#64748B;text-align:right;">' +
          'SAIRNbiz -- included free with your subscription -- ' +
          '<a href="/sairnbiz.html" target="_blank" style="color:' + tealDark + ';font-weight:700;text-decoration:none;">Open SAIRNbiz</a>' +
        '</div>' +
      '</div>';
  }

  function openHub() { window.open('/sairnbiz.html', '_blank'); }

  return {
    sendEvent, getEmployees, getEmployee,
    getPayrollSummary, getFinancialSummary,
    postToGL, syncAll, renderPanel, openHub,
    B2B_APPS, VERSION
  };

})();

console.log('SAIRNbiz Connector v' + SAIRNbiz.version + ' loaded -- People + Money backbone for SAIRN B2B suite');
