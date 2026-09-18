
'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),vm=require('vm');
const html=fs.readFileSync(process.env.LAW_HTML||path.join(__dirname,'..','sairnlaw.html'),'utf8').replace(/\r\n/g,'\n');
let pass=0,fail=0;
function t(n,f){try{const r=f();if(r&&r.then)return r.then(()=>{pass++;console.log('PASS '+n);},e=>{fail++;console.log('FAIL '+n+' -- '+e.message);});pass++;console.log('PASS '+n);}catch(e){fail++;console.log('FAIL '+n+' -- '+e.message);}}
function grab(sig,term){const a=html.indexOf(sig);assert.ok(a>0,'not found: '+sig);const e=html.indexOf(term,a);assert.ok(e>a);return html.slice(a,e+term.length);}
function harness(o){o=o||{};const store={law_trusttx:JSON.parse(JSON.stringify(o.rows||[]))};const calls={writes:[],toasts:[]};
 const ctx={console:{warn(){},error(){}},
  ld:(k,d)=>(store[k]===undefined?d:JSON.parse(JSON.stringify(store[k]))),
  st:(k,v)=>{store[k]=JSON.parse(JSON.stringify(v));return true;},
  trustTransactions:()=>store.law_trusttx,
  rTrust:()=>{},toast:(m)=>calls.toasts.push(m),
  fdate:(d)=>String(d||'--'),
  lawWriteFailText:(r,f)=>f,
  prompt:(m,d)=>o.promptValue===undefined?d:o.promptValue,
  sdnData:async(a,r,rec)=>{calls.writes.push({a,r,id:rec.id});return o.syncFails?null:{ok:true};},
  __store:store,__calls:calls};
 vm.createContext(ctx);
 vm.runInContext([grab('async function lawSetClearance(','\n}\n'),
   grab('function lawMarkCleared(','\n}\n'),
   grab('function lawMarkOutstanding(','\n')].join('\n'),ctx);
 return ctx;}
const ROW=(o)=>Object.assign({id:'T1',client_id:'CL-1',type:'Disbursement',amount:40,date:'2026-09-14',status:'Posted'},o||{});
(async()=>{
await t('marking cleared stores a DATE the engine can read',async()=>{
  const c=harness({rows:[ROW()],promptValue:'2026-09-20'});
  await c.lawMarkCleared('T1');
  const r=c.__store.law_trusttx[0];
  assert.strictEqual(r.cleared_on,'2026-09-20');
  assert.strictEqual(r.cleared,true);
  assert.strictEqual(c.__calls.writes.length,1,'the clearance never reached the server');
});
await t('a bad date changes NOTHING and says so',async()=>{
  const c=harness({rows:[ROW()],promptValue:'last Tuesday'});
  await c.lawMarkCleared('T1');
  assert.strictEqual(c.__store.law_trusttx[0].cleared_on,undefined);
  assert.strictEqual(c.__calls.writes.length,0,'a bad date was sent to the server');
  assert.match(c.__calls.toasts.join(' '),/YYYY-MM-DD/);
});
await t('marking outstanding is cleared:false, NOT a missing field',async()=>{
  const c=harness({rows:[ROW()]});
  await c.lawMarkOutstanding('T1');
  const r=c.__store.law_trusttx[0];
  assert.strictEqual(r.cleared,false,'outstanding must be STATED, not implied by absence');
  assert.strictEqual(r.cleared_on,undefined);
});
await t('a clearance that did NOT sync is REVERTED, not left looking saved',async()=>{
  const c=harness({rows:[ROW()],promptValue:'2026-09-20',syncFails:true});
  await c.lawMarkCleared('T1');
  const r=c.__store.law_trusttx[0];
  assert.strictEqual(r.cleared_on,undefined,
    'this device would adjust its reconciliation for an item no other device knows about');
  // ── THE FLAG HALF OF THE ROLLBACK, ADDED 2026-09-18 ──────────────────────
  // FOUND BY tests/sairnlaw_trust_clearance_probe.py, which planted a
  // HALF-ROLLBACK -- cleared_on restored, `cleared` left true -- and this
  // suite stayed GREEN. The arm above checks one of the two fields
  // lawSetClearance() sets and one of the two it restores.
  //
  // WHAT THE HALF-ROLLBACK ACTUALLY LEAVES BEHIND, because "both fields" is
  // not a reason: the record ends up `cleared:true` with no `cleared_on`.
  // sairnlaw.html:3533 branches on cleared_on FIRST and on `cleared===false`
  // second, so the badge shows neither "cleared" nor "outstanding" -- it shows
  // "not tracked", and the Outstanding button reappears. Worse, the stale
  // `true` is still in the row: the next write of that transaction for ANY
  // other reason pushes a clearance to the server that nobody ever
  // successfully applied.
  assert.strictEqual(r.cleared,undefined,
    'the FLAG was not rolled back with the date -- the row is left cleared:true '
    + 'with no cleared_on, which renders as "not tracked" and pushes a '
    + 'clearance nobody applied on the next unrelated write');
  assert.match(c.__calls.toasts.join(' '),/did NOT reach the server/);
});
await t('a VOIDED transaction cannot clear the bank',async()=>{
  const c=harness({rows:[ROW({status:'Voided'})],promptValue:'2026-09-20'});
  await c.lawMarkCleared('T1');
  assert.strictEqual(c.__store.law_trusttx[0].cleared_on,undefined);
  assert.strictEqual(c.__calls.writes.length,0);
});
console.log('\n'+pass+' passed, '+fail+' failed');process.exit(fail?1:0);
})();
