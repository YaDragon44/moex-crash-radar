const assert=require('assert');
const S=require('./sanctions-regulatory-registry.js');

let r=S.get('SBER');
assert.equal(r.verified,true);
assert.equal(r.material,true);
assert.equal(r.designated,true);
assert.equal(r.status,'DESIGNATED');
assert.equal(r.critical,undefined);

r=S.get('MOEX');
assert.equal(r.verified,true);
assert.equal(r.material,true);
assert.equal(r.designated,true);
assert.equal(r.critical,undefined);

r=S.get('YDEX');
assert.equal(r.verified,false);
assert.equal(r.status,'LOCK');
assert.equal(r.material,false);
assert.equal(r.designated,false);

let v=S.validate({verified:true,material:true,designated:true,status:'DESIGNATED'});
assert.equal(v.ok,true);
v=S.validate({verified:true,critical:true,material:true,designated:true,status:'DESIGNATED'});
assert.equal(v.ok,false);
assert(v.errors.includes('legacy_critical_field_forbidden'));
v=S.validate({verified:true,material:false,designated:true,status:'DESIGNATED'});
assert.equal(v.ok,false);
assert(v.errors.includes('designated_must_be_material'));

const audit=S.audit();
assert.equal(audit.ok,true);
assert.deepEqual(audit.errors,[]);
console.log('R1.8.26 sanctions regulatory semantics tests: PASS');
