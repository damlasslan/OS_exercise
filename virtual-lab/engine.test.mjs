import test from 'node:test';
import assert from 'node:assert/strict';
import {CASES,workload,scheduling,replacement,allocation} from './engine.mjs';
test('five deterministic cases',()=>{assert.equal(CASES.length,5);for(let c=1;c<=5;c++){const w=workload('test-123',c);assert.deepEqual(w,workload('test-123',c));assert.equal(w.processes.length,4);assert.equal(w.pages.length,14);assert.equal(w.caseNo,c);}});
const jobs=[{id:'P1',arrival:0,burst:5,priority:2},{id:'P2',arrival:1,burst:3,priority:1}];
test('FCFS reference',()=>{const r=scheduling(jobs,'FCFS');assert.deepEqual(r.metrics.map(x=>x.completion),[5,8]);assert.equal(r.averageWaiting,2);assert.equal(r.utilization,100);});
test('RR reference',()=>{const r=scheduling(jobs,'RR',2);assert.deepEqual(r.timeline.map(x=>x.id),['P1','P2','P1','P2','P1']);assert.deepEqual(r.metrics.map(x=>x.completion),[8,7]);assert.equal(r.averageWaiting,3);});
test('idle period',()=>{const r=scheduling([{id:'P1',arrival:2,burst:2,priority:1}],'FCFS');assert.equal(r.utilization,50);assert.equal(r.timeline[0].id,'IDLE');});
test('priority nonpreemptive',()=>{const r=scheduling([...jobs,{id:'P3',arrival:1,burst:1,priority:0}],'PRIORITY');assert.deepEqual(r.timeline.map(x=>x.id),['P1','P3','P2']);});
const refs=[1,2,3,4,1,2,5,1,2,3,4,5];
test('Belady anomaly',()=>{assert.equal(replacement(refs,3,'FIFO').faults,9);assert.equal(replacement(refs,4,'FIFO').faults,10);});
test('OPT reference',()=>{assert.equal(replacement(refs,3,'OPT').faults,7);});
test('LRU reference',()=>{assert.equal(replacement(refs,3,'LRU').faults,10);});
test('Clock pointer and bits',()=>{const r=replacement([1,2,3,1,4],3,'CLOCK');assert.equal(r.faults,4);assert.deepEqual(r.steps.at(-1).frames,[4,2,3]);assert.deepEqual(r.steps.at(-1).bits,[1,0,0]);assert.equal(r.steps.at(-1).pointer,1);});
test('allocation overhead',()=>{const r=allocation(9,4,[1,2,3,8]);assert.equal(r.blocks,3);assert.equal(r.internalWasteKiB,3);assert.deepEqual(r.contiguous,[1,2,3]);assert.deepEqual(r.indexed,{index:1,data:[2,3,8]});});
test('fragmented free blocks',()=>{assert.equal(allocation(12,4,[1,3,5,7]).contiguous,null);});
test('all cases invariants',()=>{for(let c=1;c<=5;c++){const w=workload('student-test',c);for(const a of ['FCFS','RR','PRIORITY']){const s=scheduling(w.processes,a,w.quantum);assert.equal(s.metrics.length,4);assert.ok(s.metrics.every(m=>m.waiting>=0));}for(const a of ['FIFO','LRU','OPT','CLOCK']){const r=replacement(w.pages,w.frames,a);assert.equal(r.faults+r.hits,w.pages.length);assert.ok(r.steps.every(s=>s.frames.length===w.frames));}}});

import {synchronization,fileLocking} from './engine.mjs';
test('mutex prevents lost updates for every case and either order',()=>{
  for(let c=1;c<=5;c++){
    const {sync}=workload('synthetic-mutex',c);
    for(const reverse of [false,true]){
      const last=reverse?'P1':'P2';
      const unlocked=synchronization(sync,false,reverse);
      const locked=synchronization(sync,true,reverse);
      assert.deepEqual(unlocked.steps.map(s=>s.action),['Read','Read','Write','Write']);
      assert.equal(unlocked.counter,sync.initial+sync.increments[last]);
      assert.equal(locked.counter,sync.initial+sync.increments.P1+sync.increments.P2);
    }
  }
});
test('file locking makes the writer wait until the reader finishes',()=>{
  assert.match(fileLocking(false).at(-1),/mixed version/);
  assert.match(fileLocking(true)[1],/Writer waits/);
  assert.match(fileLocking(true).at(-1),/exclusive lock/);
});

test('workloads differ between students for every exercise', () => {
  const seen = { sync: new Set(), answers: new Set(), cpu: new Set(), pages: new Set(), file: new Set() };
  for (let s = 0; s < 1000; s++) {
    const w = workload('variety-' + s, 1 + (s % 5));
    seen.sync.add(JSON.stringify(w.sync));
    seen.answers.add(synchronization(w.sync, false).counter);
    seen.cpu.add(JSON.stringify(w.processes.map(p => [p.arrival, p.burst])) + w.quantum);
    seen.pages.add(w.pages.join(','));
    seen.file.add(w.fileKiB);
  }
  assert.ok(seen.sync.size >= 40, 'synchronization setups: ' + seen.sync.size);
  assert.ok(seen.answers.size >= 6, 'synchronization answers: ' + seen.answers.size);
  assert.ok(seen.cpu.size >= 900 && seen.pages.size >= 990 && seen.file.size >= 40);
});

test('every value of a small range is generated with a similar frequency', () => {
  const counts = [0, 0, 0, 0];
  for (let s = 0; s < 4000; s++) counts[workload('uniform-' + s, 1).sync.initial]++;
  assert.ok(counts.every(c => c > 800 && c < 1200), counts.join(','));
});
