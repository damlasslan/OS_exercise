import {randomUUID} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {workload,scheduling,synchronization,replacement,allocation} from './engine.mjs';

const files=new Map([['/','index.html'],['/app.mjs','app.mjs'],['/practice','preview.html'],['/engine.mjs','engine.mjs'],['/drafts.mjs','drafts.mjs']]);
const json=(value,status=200,headers={})=>Response.json(value,{status,headers:{'Cache-Control':'no-store',...headers}});
function fail(status,message,details={}){throw Object.assign(new Error(message),{status,details});}
const domain='@example.invalid';
async function query(query,params=[]){
  const connection=new URL(process.env.DATABASE_URL);
  connection.pathname='/os_virtual_lab';
  const reply=await fetch('https://'+connection.hostname+'/sql',{method:'POST',headers:{'Content-Type':'application/json','Neon-Connection-String':connection.href,'Neon-Raw-Text-Output':'false'},body:JSON.stringify({query,params})});
  if(!reply.ok)fail(409,'The operation could not be saved. Refresh and check your attempt and deadline.');
  return (await reply.json()).rows;
}
async function identity(req){
  const token=/\boslab=([A-Za-z0-9_-]{16,512})(?:;|$)/.exec(req.headers.get('cookie')||'')?.[1];
  if(!token)fail(401,'Please sign in.');
  const [person]=await query(`select u.id,lab.verified_student(u.id) as student,exists(select from lab.instructors i where i.auth_id=u.id::text) as instructor
  from neon_auth.session s join neon_auth."user" u on u.id=s."userId" where s.token=$1 and s."expiresAt">now() and u."emailVerified" and not coalesce(u.banned,false) and right(lower(u.email),16)='@example.invalid'`,[token]);
  if(!person)fail(401,'Your session has expired. Please sign in again.');
  if(!person.student&&!person.instructor)fail(403,'A verified synthetic roster or instructor account is required.');
  return person;
}
function experiment(w,key){
  switch(key){
    case 'cpu':return scheduling(w.processes,'RR',w.quantum).averageWaiting;
    case 'sync':return synchronization(w.sync,false).counter;
    case 'vm':return replacement(w.pages,w.frames,'LRU').faults;
    case 'fs':return allocation(w.fileKiB,w.blockKiB,w.freeBlocks).blocks;
    default:fail(400,'Unknown experiment.');
  }
}
async function api(req,route){
  if(req.method!=='POST'||req.headers.get('origin')!==new URL(req.url).origin||!req.headers.get('content-type')?.startsWith('application/json'))fail(403,'Same-origin JSON required.');
  let bytes=0;const chunks=[];
  for await(const chunk of req.body){bytes+=chunk.length;if(bytes>1800000)fail(413,'Upload a smaller image.');chunks.push(chunk);}
  let b;try{b=JSON.parse(Buffer.concat(chunks).toString())}catch{fail(400,'Invalid request.')}
  if(!b||typeof b!=='object')fail(400,'Invalid request.');
  if(route==='login'){
    if(typeof b.email!=='string'||!b.email.toLowerCase().endsWith(domain)||typeof b.password!=='string')fail(403,'Only synthetic test accounts are enabled.');
    const reply=await fetch("https://ep-frosty-union-bg1pefd8.neonauth.c-9.eu-central-1.aws.neon.tech/os_virtual_lab/auth/sign-in/email",{method:'POST',headers:{'Content-Type':'application/json',Origin:"https://br-withered-thunder-bgnp8v2a-oslab.compute.c-9.eu-central-1.aws.neon.tech"},body:JSON.stringify({email:b.email,password:b.password})});
    const data=await reply.json();if(!reply.ok||!data.user?.emailVerified||!data.token||!/^[A-Za-z0-9_-]{16,512}$/.test(data.token))fail(401,'Sign-in failed.');
    return json({ok:true},200,{'Set-Cookie':'oslab='+data.token+'; Path=/; HttpOnly; Secure; SameSite=Strict'});
  }
  if(route==='logout'){
    const token=/\boslab=([A-Za-z0-9_-]{16,512})(?:;|$)/.exec(req.headers.get('cookie')||'')?.[1];
    if(token)await query('delete from neon_auth.session where token=$1',[token]);
    return json({},200,{'Set-Cookie':'oslab=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Strict'});
  }
  const p=await identity(req);
  if(route==='home')return json({student:p.student,instructor:p.instructor,attempts:await query('select id,case_no,attempt_no,submitted_at from lab.attempts where student_id=$1 order by attempt_no',[p.student])});
  if(route==='start'){
    if(!p.student||!Number.isInteger(b.caseNo)||b.caseNo<1||b.caseNo>5)fail(400,'Choose a case.');
    const id=randomUUID();const rows=await query(`insert into lab.attempts(id,assignment_id,student_id,attempt_no,case_no,workload)
    select $1,s.id,$2,1+(select count(*) from lab.attempts a where a.student_id=$2 and a.assignment_id=s.id),$3,$4::jsonb from lab.assignments s where title='Synthetic OS Lab' and now() between opens_at and closes_at order by opens_at desc limit 1 returning id`,[id,p.student,b.caseNo,JSON.stringify(workload(id,b.caseNo))]);
    if(!rows.length)fail(409,'No open synthetic assignment.');return json(rows[0]);
  }
  if(route==='dashboard'){
    if(!p.instructor)fail(403,'Instructor access required.');
    return json(await query(`select a.id,a.student_id,a.case_no,a.submitted_at,g.auto_score,g.manual_score from lab.attempts a join lab.roster r using(student_id) left join lab.grades g on g.attempt_id=a.id where right(lower(r.email),16)='@example.invalid' order by a.updated_at desc`));
  }
  const [a]=await query(`select a.* from lab.attempts a join lab.roster r using(student_id) where a.id=$1 and (a.student_id=$2 or $3::boolean) and right(lower(r.email),16)='@example.invalid'`,[b.id,p.student,p.instructor===true]);
  if(!a)fail(404,'Attempt unavailable.');
  if(route==='read')return json({attempt:a,predictions:await query('select experiment,answers from lab.predictions where attempt_id=$1',[a.id]),runs:await query('select experiment,results from lab.experiment_runs where attempt_id=$1 order by id',[a.id]),evidence:await query("select kind,encode(png,'base64') as image from lab.evidence where attempt_id=$1",[a.id]),grade:(await query('select auto_score,manual_score,feedback from lab.grades where attempt_id=$1',[a.id]))[0]});
  if(route==='reopen'||route==='second'){
    if(!p.instructor)fail(403,'Instructor access required.');
    if(route==='reopen'){const [r]=await query('select lab.reopen_synthetic($1,$2) as ok',[p.id,a.id]);if(!r.ok)fail(409,'Attempt could not be reopened.');}
    else await query('update lab.roster set allowed_attempts=2 where student_id=$1',[a.student_id]);
    return json({ok:true});
  }
  if(route==='grade'){
    if(!p.instructor||!a.submitted_at)fail(403,'A submitted attempt and instructor role are required.');
    if(!Number.isInteger(b.score)||b.score<0||b.score>40||typeof b.feedback!=='string'||b.feedback.length>4000)fail(400,'Enter a score from 0 to 40 and feedback.');
    await query('update lab.grades set manual_score=$2,feedback=$3,updated_at=now() where attempt_id=$1',[a.id,b.score,b.feedback]);return json({ok:true});
  }
  if(a.student_id!==p.student||a.submitted_at)fail(403,'Attempt is read-only.');
  if(route==='upload'){
    if(!['diagram','baseline','load'].includes(b.kind)||typeof b.image!=='string'||!b.image.startsWith('iVBORw0KGgo')||b.image.length>1600000)fail(400,'Choose a PNG image under 1.2 MB.');
    const rows=await query(`with gate as (select a.id from lab.attempts a join lab.assignments s on s.id=a.assignment_id where a.id=$1 and a.submitted_at is null and now() between s.opens_at and s.closes_at for update of a)
    insert into lab.evidence(attempt_id,kind,png) select id,$2,decode($3,'base64') from gate on conflict(attempt_id,kind) do update set png=excluded.png returning kind`,[a.id,b.kind,b.image]);
    if(!rows.length)fail(409,'Attempt closed.');return json({ok:true});
  }
  if(route==='save'){
    const [row]=await query('select lab.save_draft($1,$2,$3,$4::jsonb) as version',[p.id,a.id,b.version,JSON.stringify(b.draft)]);
    if(row.version==null)fail(409,'Draft conflict: another device or tab saved a newer draft.',{conflict:true});return json(row);
  }
  if(route==='run'){
    const answer=experiment(a.workload,b.key);
    if(typeof b.prediction!=='number'||!Number.isFinite(b.prediction))fail(400,'Enter a numeric prediction.');
    const rows=await query(`with gate as (select a.id from lab.attempts a join lab.assignments s on s.id=a.assignment_id where a.id=$1 and a.submitted_at is null and now() between s.opens_at and s.closes_at for update of a),
    locked as (insert into lab.predictions(attempt_id,experiment,answers) select id,$2,jsonb_build_object('value',$3::numeric) from gate on conflict do nothing returning experiment)
    select id from gate`,[a.id,b.key,b.prediction]);
    if(!rows.length)fail(409,'Attempt closed.');
    const saved=await query(`insert into lab.experiment_runs(attempt_id,experiment,results) select a.id,$2,jsonb_build_object('value',$3::numeric) from lab.attempts a join lab.assignments s on s.id=a.assignment_id where a.id=$1 and a.submitted_at is null and now() between s.opens_at and s.closes_at for update of a returning results`,[a.id,b.key,answer]);
    if(!saved.length)fail(409,'Attempt closed.');return json(saved[0]);
  }
  if(route==='submit'){
    const weights={cpu:15,sync:10,vm:20,fs:15};
    const predictions=await query('select experiment,answers from lab.predictions where attempt_id=$1',[a.id]);
    if(predictions.length!==4)fail(409,'Complete all four experiments.');
    const score=predictions.reduce((sum,row)=>sum+(Math.abs(row.answers.value-experiment(a.workload,row.experiment))<0.005?weights[row.experiment]:0),0);
    const rows=await query(`with done as (update lab.attempts set version=version+1,submitted_at=now() where id=$1 and version=$2 and submitted_at is null
    and length(trim(draft->>'architecture'))>0 and length(trim(draft->>'evaluation'))>0 and length(trim(draft->>'processes'))>0
    and length(trim(draft->>'cpuCorrection'))>0 and length(trim(draft->>'vmCorrection'))>0 and length(trim(draft->>'fsCorrection'))>0 and length(trim(draft->>'syncCorrection'))>0 and (select count(*) from lab.evidence where attempt_id=$1)=3 and (select count(distinct experiment) from lab.experiment_runs where attempt_id=$1)=4 returning *),
    report as (insert into lab.reports(attempt_id,version,snapshot,final) select id,version,to_jsonb(done)||jsonb_build_object('predictions',(select jsonb_object_agg(experiment,answers) from lab.predictions where attempt_id=$1),'runs',(select jsonb_agg(results order by id) from lab.experiment_runs where attempt_id=$1),'evidence',(select jsonb_object_agg(kind,encode(png,'base64')) from lab.evidence where attempt_id=$1)),true from done)
    insert into lab.grades(attempt_id,auto_score) select id,$3 from done on conflict(attempt_id) do update set auto_score=excluded.auto_score,manual_score=null,feedback=null,updated_at=now() returning auto_score`,[a.id,b.version,score]);
    if(!rows.length)fail(409,'Complete all four experiments, corrections, written sections and three image uploads. Sync your draft before submitting.');return json(rows[0]);
  }
  fail(404,'Unknown action.');
}
export default {async fetch(req){
  try{
    const pathname=new URL(req.url).pathname;
    if(pathname.startsWith('/api/'))return await api(req,pathname.slice(5));
    if(!files.has(pathname))return new Response('Not found',{status:404});
    const name=files.get(pathname);return new Response(await readFile(new URL(name,import.meta.url)),{headers:{'Content-Type':name.endsWith('.html')?'text/html; charset=utf-8':'text/javascript','X-Content-Type-Options':'nosniff','Cache-Control':'no-cache'}});
  }catch(e){return json({error:e.status?e.message:'Service unavailable.',...(e.status?e.details:{})},e.status||503);}
}};
