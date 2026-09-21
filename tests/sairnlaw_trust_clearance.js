
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
  // ── FIDELITY FIX 2026-09-21, AND EVERY TWO-DEVICE ARM DEPENDS ON IT ──────
  // This returned `store.law_trusttx` BY REFERENCE. The real one is
  // `ld('law_trusttx',[])`, which reads localStorage and JSON.parses it, so
  // every call hands back a FRESH array. With a shared reference the whole
  // stale-snapshot class is invisible: the array a function captured before an
  // await and the array in storage are the same object, so writing the stale
  // one back cannot lose anything and no arm can ever see that it would.
  // A deep copy is what `ld` does.
  trustTransactions:()=>JSON.parse(JSON.stringify(store.law_trusttx)),
  rTrust:()=>{},toast:(m)=>calls.toasts.push(m),
  fdate:(d)=>String(d||'--'),
  lawWriteFailText:(r,f)=>f,
  prompt:(m,d)=>o.promptValue===undefined?d:o.promptValue,
  // `duringWrite` is THE SECOND DEVICE. It runs while the caller is awaiting
  // the server, which is the only window in which the defects below exist --
  // a fixture with one device in play cannot open it. It is handed the store
  // so it can do what a hydration or another browser's write really does:
  // replace what is in localStorage under this session's feet.
  sdnData:async(a,r,rec)=>{calls.writes.push({a,r,id:rec.id});
    if(o.duringWrite)o.duringWrite(store);
    return o.syncFails?null:{ok:true};},
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

// ═══════════════════════════════════════════════════════════════════════════
// TWO DEVICES. Every arm above has exactly one, and the three defects below
// only exist in the window where a SECOND one writes -- which is why the
// negative control could plant a half-rollback and a missing rollback and
// never plant these. confirmVoid() thirty lines up was hardened against this
// class on 2026-09-02 "by driving this function overlapped, not by reading
// it"; lawSetClearance was not, and this is the overlap.
// ═══════════════════════════════════════════════════════════════════════════

await t('THE HARNESS ITSELF: trustTransactions() hands back a FRESH array every call',()=>{
  // PINNED BECAUSE THE THREE ARMS BELOW DEPEND ON IT AND WOULD PASS VACUOUSLY
  // WITHOUT IT. The real one is ld('law_trusttx',[]), which JSON.parses
  // localStorage on every call. If this stub ever goes back to returning the
  // store by reference, the array a function captured before an await and the
  // array in storage become the same object -- writing the stale one back can
  // no longer lose anything, and "a failed revert does not write away what
  // landed during the round trip" becomes a sentence that cannot fail.
  const c=harness({rows:[ROW()]});
  const a=c.trustTransactions(), b=c.trustTransactions();
  assert.notStrictEqual(a,b,'two calls returned the SAME array object');
  a[0].description='mutated through the first handle';
  assert.strictEqual(c.trustTransactions()[0].description,undefined,
    'mutating what one call returned changed what the next call sees -- this is '
    + 'a shared reference wearing the shape of a read');
});

await t('TWO DEVICES: a failed revert does not write away what landed during the round trip',async()=>{
  // The sharp one. The old code captured `list` BEFORE the await and called
  // st('law_trusttx', list) in the revert -- so a hydration landing mid-flight
  // was overwritten WHOLESALE. Not the one row: the entire array.
  const c=harness({rows:[ROW(),ROW({id:'T2',description:'before'})],
    promptValue:'2026-09-20',syncFails:true,
    duringWrite:(store)=>{
      // What lawHydrateAll actually does now that it is SERVER-WINS: replaces
      // the stored array with the server's, which has a row this device has
      // never seen and a change to one it has.
      store.law_trusttx=JSON.parse(JSON.stringify(store.law_trusttx));
      store.law_trusttx[1].description='changed by the other device';
      store.law_trusttx.push({id:'T3',client_id:'CL-1',type:'Deposit',amount:100,
        date:'2026-09-15',status:'Posted'});
    }});
  await c.lawMarkCleared('T1');
  const rows=c.__store.law_trusttx;
  assert.ok(rows.find(x=>x.id==='T3'),
    'the row that arrived during the round trip was ERASED -- the revert wrote back '
    + 'the array it captured before the await, so an entire hydration was lost to a '
    + 'failed single-row write');
  assert.strictEqual(rows.find(x=>x.id==='T2').description,'changed by the other device',
    'a change to an UNRELATED row was reverted along with this one');
  assert.strictEqual(rows.find(x=>x.id==='T1').cleared_on,undefined,
    'and the clearance itself still has to be rolled back');
});

await t('TWO DEVICES: the revert does not ERASE a clearance another device recorded',async()=>{
  // The review asked whether the revert could RESURRECT another device's
  // clearance. It cannot. It could ERASE one: prevOn/prevFlag were restored
  // unconditionally, so this device's pre-action "not tracked" was written
  // over a clearance that is genuinely on the server. That puts an item the
  // bank HAS taken back into the outstanding set, which moves the expected
  // bank balance by its amount.
  const c=harness({rows:[ROW()],syncFails:true,
    duringWrite:(store)=>{
      store.law_trusttx[0].cleared=true;
      store.law_trusttx[0].cleared_on='2026-09-19';
      store.law_trusttx[0].cleared_at='2026-09-21T11:00:00.000Z'; // NOT this call's stamp
    }});
  await c.lawMarkOutstanding('T1');
  const r=c.__store.law_trusttx[0];
  assert.strictEqual(r.cleared_on,'2026-09-19',
    "the other device's clearance was ERASED by this device's rollback");
  assert.strictEqual(r.cleared,true);
  assert.match(c.__calls.toasts.join(' '),/changed on another device/,
    'the user is not told their change was left alone -- silence here reads as success');
});

await t('TWO DEVICES: the stamp is what tells the two apart, and it is cleaned up',async()=>{
  // The mechanism, asserted directly so it cannot be removed while the two
  // arms above keep passing for some other reason.
  const ok=harness({rows:[ROW()],promptValue:'2026-09-20'});
  await ok.lawMarkCleared('T1');
  assert.match(ok.__store.law_trusttx[0].cleared_at||'',/^\d{4}-\d\d-\d\dT/,
    'a successful clearance carries no stamp, so a later rollback has no way to '
    + 'tell its own change from anybody else\'s');
  const rb=harness({rows:[ROW()],promptValue:'2026-09-20',syncFails:true});
  await rb.lawMarkCleared('T1');
  assert.strictEqual(rb.__store.law_trusttx[0].cleared_at,undefined,
    'the stamp outlived the change it stamped -- a row left carrying a stamp for a '
    + 'clearance that was rolled back would make the NEXT failed write think the '
    + 'record still held its own change');
});

await t('ALREADY IN THE TARGET STATE sends nothing -- and Re-date still does',async()=>{
  const already=harness({rows:[ROW({cleared:false})]});
  await already.lawMarkOutstanding('T1');
  assert.strictEqual(already.__calls.writes.length,0,
    'a no-op re-sent the record, which can only lose: it risks a failure whose '
    + 'revert has nothing to revert, and toasts a change nobody made');
  const same=harness({rows:[ROW({cleared:true,cleared_on:'2026-09-20'})],promptValue:'2026-09-20'});
  await same.lawMarkCleared('T1');
  assert.strictEqual(same.__calls.writes.length,0);
  // THE REFUSAL IS SCOPED, and this is the arm that keeps it scoped. The UI
  // labels the button "Re-date" on an already-cleared row, so a DIFFERENT date
  // is a real edit and must still go.
  const redate=harness({rows:[ROW({cleared:true,cleared_on:'2026-09-20'})],promptValue:'2026-09-22'});
  await redate.lawMarkCleared('T1');
  assert.strictEqual(redate.__calls.writes.length,1,
    'Re-date was refused as a no-op -- the guard is too wide and the button lies');
  assert.strictEqual(redate.__store.law_trusttx[0].cleared_on,'2026-09-22');
});

console.log('\n'+pass+' passed, '+fail+' failed');process.exit(fail?1:0);
})();
