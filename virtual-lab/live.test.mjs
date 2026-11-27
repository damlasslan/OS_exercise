const u=process.env.LAB_URL;
async function call(route,b,cookie='',origin=new URL(u).origin){const r=await fetch(u+'api/'+route,{method:'POST',headers:{origin,'content-type':'application/json',cookie},body:JSON.stringify(b)});const json=await r.json();return {status:r.status,j:json,c:r.headers.get('set-cookie')?.split(';')[0]};}
const accounts=JSON.parse(process.env.LAB_TEST_ACCOUNTS);
async function sign(i){const f=accounts[i],r=await call('login',{email:f.email,password:f.p});if(r.status!==200)throw Error('login '+r.status+' '+JSON.stringify(r.j));return r.c;}
import assert from 'node:assert/strict';
const sessions=[]; for(let i=0;i<accounts.length;i++){sessions.push(await sign(i));await new Promise(resolve=>setTimeout(resolve,13000));};
async function check(route,b,c,expected=200){const r=await call(route,b,c);assert.equal(r.status,expected,route+' '+JSON.stringify(r.j.error));return r.j;}
await check('home',{},'',401);
assert.equal((await call('home',{},sessions[0],'https://example.invalid')).status,403);
await check('dashboard',{},sessions[0],403);
for(let i=0;i<5;i++){
 const c=sessions[i],home=await check('home',{},c);
 const id=home.attempts[0]?.id||(await check('start',{caseNo:i+1},c)).id;
 await check('read',{id},sessions[(i+1)%5],404);
 await check('save',{id,version:0,draft:{}},sessions[(i+1)%5],404);
 let d=await check('read',{id},c);
 if(!d.attempt.submitted_at){
 const version=d.attempt.version;
 const draft={architecture:'Synthetic diagram',processes:'Worker thread',evaluation:'Baseline compared with load',cpuCorrection:'QA',vmCorrection:'QA',fsCorrection:'QA',syncCorrection:'QA'};
 const saved=await check('save',{id,version,draft},c);
 await check('save',{id,version,draft:{}},c,409);
 const resumed=await check('read',{id},await sign(i));assert.equal(resumed.attempt.draft.evaluation,draft.evaluation);
 for(const key of ['cpu','sync','vm','fs']){await check('run',{id,key,prediction:0},c);await check('run',{id,key,prediction:999},c);}
 d=await check('read',{id},c);assert.equal(d.predictions.length,4);assert.ok(d.predictions.every(p=>p.answers.value===0));
 for(const kind of ['diagram','baseline','load'])await check('upload',{id,kind,image:'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a4XkAAAAASUVORK5CYII='},c);
 await check('submit',{id,version:saved.version},c);
 }
 await check('save',{id,version:0,draft:{}},c,403);await check('submit',{id,version:0},c,403);
 await check('grade',{id,score:31,feedback:'Synthetic rubric review'},sessions[5]);
 const final=await check('read',{id},c);assert.equal(Number(final.grade.manual_score),31);assert.equal(final.evidence.length,3);
 console.log('PASS case',i+1);
}
await check('dashboard',{},sessions[5]);await check('logout',{},sessions[0]);await check('home',{},sessions[0],401);
console.log('PASS instructor dashboard, session invalidation and access checks');
