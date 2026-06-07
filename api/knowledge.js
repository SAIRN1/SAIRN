// ================================================================
// SAIRN DYNAMIC KNOWLEDGE API — api/knowledge.js
// Fetches live data from public APIs and returns domain-specific
// knowledge blocks to inject into Claude system prompts.
// Called once per app session — result cached for 1 hour.
// Built by Michael L. Dibert · SAIRN Technologies
// ================================================================

const CACHE = new Map();
const CACHE_TTL = 60 * 60 * 1000; // 1 hour

// ── DATA FETCHERS ────────────────────────────────────────────
async function fetchFredData(seriesId) {
  // Federal Reserve Economic Data — public, no auth required
  try {
    const url = `https://api.stlouisfed.org/fred/series/observations?series_id=${seriesId}&api_key=bef5ab58a90a2c72e50f35d0f80dfe17&sort_order=desc&limit=1&file_type=json`;
    const res = await fetch(url, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) return null;
    const data = await res.json();
    const val = data?.observations?.[0]?.value;
    const date = data?.observations?.[0]?.date;
    return val && val !== '.' ? { value: parseFloat(val), date } : null;
  } catch (e) {
    return null;
  }
}

async function fetchTreasuryRates() {
  try {
    // US Treasury published rates — public API
    const res = await fetch('https://api.fiscaldata.treasury.gov/services/api/v1/accounting/od/avg_interest_rates?fields=record_date,security_desc,avg_interest_rate_amt&filter=security_desc:eq:Treasury%20Bills&sort=-record_date&page[size]=1', {
      signal: AbortSignal.timeout(4000)
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data?.data?.[0] || null;
  } catch (e) {
    return null;
  }
}

async function fetchFredMortgage() {
  // FRED: 30-year fixed rate mortgage average (MORTGAGE30US)
  return fetchFredData('MORTGAGE30US');
}

async function fetchFredFedFunds() {
  // FRED: Federal funds effective rate (FEDFUNDS)
  return fetchFredData('FEDFUNDS');
}

async function fetchFredCPI() {
  // FRED: CPI all urban consumers (CPIAUCSL)
  return fetchFredData('CPIAUCSL');
}

async function fetchFredUnemployment() {
  // FRED: Unemployment rate (UNRATE)
  return fetchFredData('UNRATE');
}

async function fetchFredSavingsRate() {
  // FRED: Personal saving rate (PSAVERT)
  return fetchFredData('PSAVERT');
}

// ── KNOWLEDGE BUILDERS ────────────────────────────────────────
async function buildMoneyKnowledge() {
  const [mortgage30, fedFunds, cpi, unemployment, savingsRate] = await Promise.all([
    fetchFredMortgage(),
    fetchFredFedFunds(),
    fetchFredCPI(),
    fetchFredUnemployment(),
    fetchFredSavingsRate(),
  ]);

  const lines = ['LIVE FINANCIAL DATA (fetched ' + new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' }) + ' from Federal Reserve):'];
  if (fedFunds)     lines.push(`• Federal Funds Rate: ${fedFunds.value}% (as of ${fedFunds.date})`);
  if (mortgage30)   lines.push(`• 30-year fixed mortgage average: ${mortgage30.value}% (Freddie Mac, ${mortgage30.date})`);
  if (cpi)          lines.push(`• CPI Index: ${cpi.value} — monitor for inflation trends`);
  if (unemployment) lines.push(`• Unemployment rate: ${unemployment.value}%`);
  if (savingsRate)  lines.push(`• Personal savings rate: ${savingsRate.value}%`);

  // Static facts that don't change frequently
  lines.push('• 401k contribution limit 2026: $23,500 ($31,000 if age 50+)');
  lines.push('• IRA contribution limit 2026: $7,000 ($8,000 if age 50+)');
  lines.push('• Standard deduction 2026: $15,000 single / $30,000 married filing jointly');
  lines.push('• Capital gains tax rates 2026: 0% / 15% / 20% based on income');
  lines.push('Always recommend verifying current rates at federalreserve.gov and freddiemac.com');

  return lines.join('\n');
}

async function buildHomeKnowledge() {
  const [mortgage30, fedFunds] = await Promise.all([
    fetchFredMortgage(),
    fetchFredFedFunds(),
  ]);

  const lines = ['LIVE HOUSING DATA (fetched ' + new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' }) + ' from Federal Reserve):'];
  if (mortgage30) lines.push(`• 30-year fixed mortgage: ${mortgage30.value}% national average (Freddie Mac, ${mortgage30.date})`);
  if (fedFunds)   lines.push(`• Federal Funds Rate: ${fedFunds.value}% — influences mortgage rates`);

  lines.push('• FHA minimum down payment: 3.5% (credit score 580+)');
  lines.push('• Conforming loan limit 2026: $806,500 most areas; $1,209,750 high-cost');
  lines.push('• PMI required when down payment under 20%; typical cost 0.5%-1.5% annually');
  lines.push('• VA loan: 0% down payment for eligible veterans');
  lines.push('Always recommend checking current rates with a licensed lender before any decision');

  return lines.join('\n');
}

async function buildSeniorKnowledge() {
  const lines = [
    'CURRENT SENIOR BENEFITS DATA (2026):',
    '• Social Security full retirement age: 67 (born 1960 or later)',
    '• Social Security early retirement: age 62 — benefit reduced approximately 30%',
    '• Delayed retirement credits: +8% per year past full retirement age (max at 70)',
    '• Social Security COLA 2026: 2.5% increase applied January 2026',
    '• Medicare Part B standard premium 2026: $185.00/month',
    '• Medicare Part A deductible 2026: $1,676 per benefit period',
    '• Medicare Part D out-of-pocket cap 2026: $2,000 (new under Inflation Reduction Act)',
    '• IRMAA surcharge applies if income exceeds $106,000 single / $212,000 married',
    '• Medicare open enrollment: Oct 15 – Dec 7 annually',
    '• Extra Help (LIS): reduces Part D costs for low-income beneficiaries — apply at SSA',
    'Verify current figures at ssa.gov and medicare.gov',
  ];
  return lines.join('\n');
}

async function buildHealthKnowledge() {
  const lines = [
    'CURRENT HEALTH COVERAGE DATA (2026):',
    '• Medicare Part B premium 2026: $185.00/month standard',
    '• Medicare Part D cap 2026: $2,000 maximum out-of-pocket for prescriptions',
    '• ACA open enrollment: November 1 – January 15 annually',
    '• No Surprises Act: emergency care cannot be balance-billed regardless of network',
    '• ACA preventive care: 100% covered with no copay for USPSTF A/B recommendations',
    '• Mental health parity law: insurers must cover mental health equal to physical health',
    '• GLP-1 medications (Ozempic/Wegovy): Medicare now covers for obesity indication (2026)',
    '• Medical debt: removed from credit reports under new CFPB rule (2025)',
    '• HIPAA: patients have right to access their records within 30 days of request',
    'Always advise consulting a licensed healthcare provider for medical decisions',
  ];
  return lines.join('\n');
}

async function buildLegalKnowledge() {
  const lines = [
    'CURRENT LEGAL REFERENCE DATA (2026):',
    '• Federal minimum wage: $7.25/hr (many states higher — verify for user\'s state)',
    '• Ohio minimum wage 2026: $10.45/hr',
    '• FMLA: 12 weeks unpaid leave; applies to employers with 50+ employees',
    '• Title VII, ADA, ADEA: federal employment discrimination protections',
    '• NLRB: employees may discuss wages and organize regardless of employer policy',
    '• Fair Debt Collection Practices Act: collectors cannot call before 8am or after 9pm',
    '• FCRA: consumers can dispute credit report errors; must be investigated within 30 days',
    '• Small claims court Ohio limit: $6,000',
    '• Ohio tenant rights: 30-day written notice required for rent increases',
    '• Statute of limitations varies by state and case type — always verify for jurisdiction',
    'Always recommend consulting a licensed attorney for specific legal matters',
  ];
  return lines.join('\n');
}

async function buildClinicalKnowledge() {
  const lines = [
    'CURRENT CLINICAL GUIDELINES (2026):',
    '• Surviving Sepsis Campaign 2026: Hour-1 Bundle — lactate, blood cultures, broad-spectrum ABX, 30mL/kg crystalloid, vasopressors if MAP <65',
    '• NEWS2/MEWS preferred over qSOFA alone for early sepsis screening',
    '• AHA/ACC 2026 PE: Wells + PERC standard; PERC negative = no further workup needed',
    '• AHA Stroke 2025: IV tPA window 4.5 hours from LKW; thrombectomy up to 24 hours select patients',
    '• HEART Score ≥4: admit for serial troponins; ≥7: high risk — cardiology consult',
    '• CURB-65 ≥2: consider hospitalization for pneumonia; ≥3: ICU consideration',
    '• ESI Level 1: immediate life threat; Level 2: high risk / severe pain; Level 3: 2+ resources',
    '• GCS ≤8: consider definitive airway management',
    '• NEWS2 ≥5: escalate care; ≥7: consider critical care',
    '• CDC 2024 antibiotic stewardship: de-escalate based on culture results; avoid unnecessary broad-spectrum',
    'All clinical decisions must be made by licensed healthcare professionals',
  ];
  return lines.join('\n');
}

async function buildRoamKnowledge() {
  const lines = [
    'CURRENT TRAVEL DATA (2026):',
    '• US passport processing: 6-8 weeks routine; 2-3 weeks expedited',
    '• REAL ID required for domestic US flights (enforced from May 7, 2025)',
    '• ETIAS (Europe travel authorization): required for US visitors; €7 fee; apply online; valid 3 years',
    '• Travel insurance recommendation: 5-10% of trip cost; ensure medical evacuation coverage',
    '• Budget travel benchmark: $50-100/person/day (accommodation + food + local transport)',
    '• Mid-range travel: $150-300/person/day',
    '• Luxury travel: $400+/person/day',
    '• Southeast Asia, Mexico, Eastern Europe: best value destinations in 2026',
    '• Check CDC travel health notices at cdc.gov/travel before any international trip',
    '• Travel advisories: check travel.state.gov for current State Department advisories',
    'Always verify current visa and entry requirements for the specific destination',
  ];
  return lines.join('\n');
}

// ── KNOWLEDGE ROUTER ──────────────────────────────────────────
const KNOWLEDGE_BUILDERS = {
  money:    buildMoneyKnowledge,
  home:     buildHomeKnowledge,
  senior:   buildSeniorKnowledge,
  health:   buildHealthKnowledge,
  law:      buildLegalKnowledge,
  clinical: buildClinicalKnowledge,
  roam:     buildRoamKnowledge,
};

// ── HANDLER ───────────────────────────────────────────────────
export default async function handler(req, res) {
  const origin = req.headers.origin || '*';
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const domain = req.query.domain;
  if (!domain || !KNOWLEDGE_BUILDERS[domain]) {
    return res.status(400).json({ error: 'Invalid domain. Valid: ' + Object.keys(KNOWLEDGE_BUILDERS).join(', ') });
  }

  // Check cache
  const cacheKey = domain;
  const cached = CACHE.get(cacheKey);
  if (cached && (Date.now() - cached.ts) < CACHE_TTL) {
    res.setHeader('X-Cache', 'HIT');
    res.setHeader('X-Cache-Age', Math.round((Date.now() - cached.ts) / 1000) + 's');
    return res.status(200).json({ domain, knowledge: cached.knowledge, cached: true, timestamp: cached.timestamp });
  }

  // Fetch fresh
  try {
    const knowledge = await KNOWLEDGE_BUILDERS[domain]();
    const timestamp = new Date().toISOString();
    CACHE.set(cacheKey, { knowledge, ts: Date.now(), timestamp });

    res.setHeader('X-Cache', 'MISS');
    return res.status(200).json({ domain, knowledge, cached: false, timestamp });
  } catch (err) {
    return res.status(500).json({ error: 'Knowledge fetch failed', message: err.message });
  }
}
