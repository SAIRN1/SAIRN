// RE-VERIFY THE FILE, NOT THE GENERATOR. The literals are parsed back out of
// the committed SQL and round-tripped through the platform's own verifyPin, so
// a transcription slip between generating and writing cannot survive.
const fs = require('fs');
const auth = require('C:/Users/marsh/Documents/SAIRN-hank/api/_lib/auth.js');
const lic  = require('C:/Users/marsh/Documents/SAIRN-hank/api/_lib/license.js');
const p = 'C:/Users/marsh/Documents/SAIRN-hank/sql/sairnfreedom_demo_owner_credential_2026-10-13.sql';
const src = fs.readFileSync(p, 'utf8');
const ins = src.slice(src.indexOf('insert into public.sairnfreedom_employee_auth'), src.indexOf('on conflict'));
const lits = (ins.match(/'[^']*'/g) || []).map(s => s.replace(/'/g, ''));
const [license_hash, employee_id, display_name, role, pin_hash, pin_salt] = lits;
const PIN = (src.match(/PIN (\d{8})/) || [])[1];
const CURL = (src.match(/"pin":"(\d{8})"/) || [])[1];
(async () => {
  const checks = [
    ['license_hash is hashLicense(SF-PINNACLE-2026)', license_hash === lic.hashLicense('SF-PINNACLE-2026')],
    ['employee_id is sairn-demo-owner', employee_id === 'sairn-demo-owner'],
    ['role is in ROLES_BY_APP.sairnfreedom', auth.ROLES_BY_APP.sairnfreedom.indexOf(role) !== -1],
    ['role is a PROVISIONING_ROLE', ['post.govern','post.govern.deputy'].indexOf(role) !== -1],
    ['role is in the employee_auth CHECK', fs.readFileSync('C:/Users/marsh/Documents/SAIRN-hank/sql/sairnfreedom_employee_auth_schema.sql','utf8').indexOf("'"+role+"'") !== -1],
    ['the header PIN and the curl PIN are the same', PIN === CURL && !!PIN],
    ['verifyPin(correct PIN) === true', await auth.verifyPin(PIN, pin_hash, pin_salt) === true],
    ['verifyPin(wrong PIN)  === false', await auth.verifyPin('00000000', pin_hash, pin_salt) === false],
    ['the guard salt literal matches the inserted salt', (src.match(/pin_salt = '([0-9a-f]+)'/)||[])[1] === pin_salt]
  ];
  let bad = 0;
  for (const [name, ok] of checks) { console.log((ok ? '  ok   ' : '  FAIL ') + name); if (!ok) bad++; }
  console.log('display_name:', JSON.stringify(display_name), ' role:', role, ' PIN:', PIN);
  console.log(bad ? 'FILE ROUND TRIP FAILED (' + bad + ')' : 'FILE ROUND TRIP PASS -- all ' + checks.length + ' checks');
  process.exit(bad ? 1 : 0);
})();
