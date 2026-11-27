// Pure deterministic simulation helpers. No student records or credentials.
export const CASES = [
  {name:"Online Gaming System",tasks:["Game engine","Rendering","Network receiver","Asset loading"],file:"Game asset",goal:"Minimize interaction latency"},
  {name:"Smart Security Camera System",tasks:["Camera capture","Video encoding","Motion detection","Disk recording"],file:"Camera recording",goal:"Maintain continuous recording"},
  {name:"Hospital Patient Monitoring System",tasks:["Sensor reading","Critical alarm","Data analysis","Patient logging"],file:"Patient log (synthetic)",goal:"Prioritize critical alerts"},
  {name:"Video Streaming Platform",tasks:["Video decoding","Buffer management","Network receiver","Cache writing"],file:"Video segment",goal:"Reduce playback interruptions"},
  {name:"Autonomous Farm Robot",tasks:["Camera processing","Navigation","Sensor reading","Data logging"],file:"Sensor log",goal:"Keep navigation responsive"}
];
function rng(seed){let x=2166136261; for(const c of seed){x=Math.imul(x^c.charCodeAt(0),16777619)>>>0;} return n=>{x=(Math.imul(x,1664525)+1013904223)>>>0;return Math.floor(x/4294967296*n);};}
export function workload(seed,caseNo){
 if(!Number.isInteger(caseNo)||caseNo<1||caseNo>5)throw Error("Invalid case");
 const r=rng(String(seed)+":"+caseNo),c=CASES[caseNo-1];
 const syncRandom = rng(String(seed) + ':sync:' + caseNo);
 const sync = { initial: syncRandom(4), increments: { P1: 1 + syncRandom(4), P2: 2 + syncRandom(4) } };
 return {caseNo,sync,quantum:2+r(3),processes:c.tasks.map((task,i)=>({id:"P"+(i+1),task,arrival:i===0?0:i+r(3),burst:3+r(7),priority:i+1})),pages:Array.from({length:14},()=>r(7)),frames:3,blockKiB:4,fileKiB:17+r(48),freeBlocks:[2,3,4,7,8,11,12,13,14,18,19,22,23,24,25,26,28,30,31,33]};
}
export function scheduling(processes,algorithm,quantum=2){
 if(!["FCFS","RR","PRIORITY"].includes(algorithm)||!Number.isInteger(quantum)||quantum<1)throw Error("Invalid scheduler");
 if(!processes.length||new Set(processes.map(p=>p.id)).size!==processes.length||processes.some(p=>!Number.isInteger(p.arrival)||p.arrival<0||!Number.isInteger(p.burst)||p.burst<1||!Number.isFinite(p.priority)))throw Error("Invalid workload");
 const list=processes.map((p,i)=>({...p,i,left:p.burst})).sort((a,b)=>a.arrival-b.arrival||a.i-b.i);
 let t=0,k=0,q=[],timeline=[],metrics=[];
 const admit=()=>{while(k<list.length&&list[k].arrival<=t)q.push(list[k++]);};
 while(k<list.length||q.length){admit();if(!q.length){const end=list[k].arrival;timeline.push({id:"IDLE",start:t,end});t=end;admit();}
 if(algorithm==="PRIORITY")q.sort((a,b)=>a.priority-b.priority||a.arrival-b.arrival||a.i-b.i);
 const p=q.shift(),d=algorithm==="RR"?Math.min(quantum,p.left):p.left;
 timeline.push({id:p.id,start:t,end:t+d});t+=d;p.left-=d;admit();
 if(p.left)q.push(p);else metrics.push({id:p.id,completion:t,turnaround:t-p.arrival,waiting:t-p.arrival-p.burst});
 }
 const busy=processes.reduce((a,p)=>a+p.burst,0);
 return {timeline,metrics:metrics.sort((a,b)=>a.id.localeCompare(b.id)),averageWaiting:metrics.reduce((a,p)=>a+p.waiting,0)/metrics.length,averageTurnaround:metrics.reduce((a,p)=>a+p.turnaround,0)/metrics.length,utilization:100*busy/t};
}
export function replacement(pages,capacity,algorithm){
 if(!["FIFO","LRU","OPT","CLOCK"].includes(algorithm)||!Number.isInteger(capacity)||capacity<1||!pages.length||pages.some(p=>!Number.isInteger(p)||p<0))throw Error("Invalid reference string");
 const f=Array(capacity).fill(null),loaded=Array(capacity).fill(-1),last=Array(capacity).fill(-1),bits=Array(capacity).fill(0);let pointer=0,faults=0;
 const steps=pages.map((p,i)=>{let j=f.indexOf(p),hit=j!==-1,evicted=null;
 if(!hit){faults++;j=f.indexOf(null);
 if(algorithm==="CLOCK"){while(f[pointer]!==null&&bits[pointer]===1){bits[pointer]=0;pointer=(pointer+1)%capacity;}j=pointer;pointer=(pointer+1)%capacity;}
 else if(j===-1){if(algorithm==="OPT"){let best=-1;for(let n=0;n<capacity;n++){const at=pages.indexOf(f[n],i+1),dist=at<0?Infinity:at;if(dist>best){best=dist;j=n;}}}else{const a=algorithm==="FIFO"?loaded:last;j=a.indexOf(Math.min(...a));}}
 evicted=f[j];f[j]=p;loaded[j]=i;
 }last[j]=i;bits[j]=1;
 return {page:p,hit,evicted,frames:[...f],...(algorithm==="CLOCK"?{bits:[...bits],pointer}: {})};});
 return {steps,faults,hits:pages.length-faults,hitRatio:(pages.length-faults)/pages.length};
}
export function allocation(fileKiB,blockKiB,freeBlocks){
 if(!Number.isFinite(fileKiB)||fileKiB<=0||!Number.isFinite(blockKiB)||blockKiB<=0||freeBlocks.some(b=>!Number.isInteger(b)||b<0))throw Error("Invalid storage input");
 const free=[...new Set(freeBlocks)].sort((a,b)=>a-b),blocks=Math.ceil(fileKiB/blockKiB);
 let contiguous=null;for(let i=0;i+blocks<=free.length;i++){if(free[i+blocks-1]-free[i]===blocks-1){contiguous=free.slice(i,i+blocks);break;}}
 return {blocks,internalWasteKiB:blocks*blockKiB-fileKiB,contiguous,linked:free.length>=blocks?free.slice(0,blocks):null,indexed:free.length>=blocks+1?{index:free[0],data:free.slice(1,blocks+1)}:null};
}

export function synchronization({ initial, increments }, useMutex, reverseOrder = false) {
  const [first, second] = reverseOrder ? ['P2', 'P1'] : ['P1', 'P2'];
  let counter = initial;
  const steps = [];
  const read = task => {
    steps.push({ task, action: 'Read', counter });
    return counter;
  };
  const write = (task, value) => {
    counter = value + increments[task];
    steps.push({ task, action: 'Write', counter });
  };
  const firstValue = read(first);
  if (useMutex) {
    write(first, firstValue);
    write(second, read(second));
  } else {
    const secondValue = read(second);
    write(first, firstValue);
    write(second, secondValue);
  }
  return { counter, steps };
}

export function fileLocking(useLock) {
  return useLock
    ? ['Reader acquires a shared lock and reads the first block.',
       'Writer waits for the reader to release its lock.',
       'Reader reads the second block and releases its lock.',
       'Writer acquires an exclusive lock and updates both blocks.']
    : ['Reader reads the original first block.',
       'Writer updates both blocks.',
       'Reader reads the updated second block and sees a mixed version.'];
}
