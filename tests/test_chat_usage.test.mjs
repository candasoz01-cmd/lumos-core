import assert from 'node:assert/strict';
import test from 'node:test';
import handler from '../api/bridge/chat.js';
import { sealSession } from '../api/_lib/lumos_session.js';

const envKeys = ['LUMOS_AUTH_STATE_SECRET','LUMOS_AXIOM_TOKEN','LUMOS_AXIOM_DATASET','OPENAI_API_KEY','LUMOS_GOOGLE_GEMINI_API_KEY','BRIDGE_UPSTREAM_URL','KANDO_BRIDGE_SECRET','LUMOS_MEMORY_LOOKUP_URL','LUMOS_MEMORY_SERVICE_TOKEN','SENTRY_DSN'];
function response() { return {statusCode:0, setHeader(){}, status(code){this.statusCode=code;return this;}, json(payload){this.payload=payload;return this;}, end(){return this;}}; }
async function scenario({message='Private request content',mode='hosted_chat',status=200,auth=true,fallback=false,modelFailure=false,axiomFailure=false,invalid=false,axiomStatus=200,axiomConfigured=true,axiomPending=false,axiomTimeout=false}) {
 const saved=Object.fromEntries(envKeys.map(k=>[k,process.env[k]])); const originalFetch=globalThis.fetch; const events=[];
 const contextKey=Symbol.for('@vercel/request-context'); const savedContext=globalThis[contextKey];
 const background=[]; let releaseAxiom; let axiomSettled=false; let axiomSignal;
 globalThis[contextKey]={get:()=>({waitUntil(promise){background.push(promise);}})};
 try {
  for(const k of envKeys) delete process.env[k];
  process.env.LUMOS_AUTH_STATE_SECRET='test-only-secret-32-characters-minimum';
  if(axiomConfigured) process.env.LUMOS_AXIOM_TOKEN='test-only-axiom-token';
  process.env.LUMOS_AXIOM_DATASET='lumos-test';
  process.env.OPENAI_API_KEY='test-only-openai-token';
  if(fallback) process.env.LUMOS_GOOGLE_GEMINI_API_KEY='test-only-gemini-token';
  const sealed=sealSession({sid:'private-session',sub:'private-subject',name:'Private Name',email:'private@example.test',provider:'google_web',exp:Math.floor(Date.now()/1000)+60});
  globalThis.fetch=async(url,init)=>{
   if(String(url).includes('api.axiom.co')) {
    assert.equal(String(url),'https://api.axiom.co/v1/datasets/lumos-test/ingest');
    assert.equal(init.headers.Authorization,'Bearer test-only-axiom-token');
    events.push(...JSON.parse(init.body));
    if(axiomPending || axiomTimeout) {
     axiomSignal=init.signal;
     await new Promise((resolve,reject)=>{
      releaseAxiom=()=>axiomFailure?reject(new Error('simulated transport failure')):resolve();
      init.signal.addEventListener('abort',()=>reject(new Error('simulated timeout')),{once:true});
     }).finally(()=>{axiomSettled=true;});
    }
    if(axiomFailure) throw new Error('simulated transport failure');
    return {ok:axiomStatus===200,status:axiomStatus};
   }
   if(modelFailure || (fallback && String(url).includes('api.openai.com'))) return {ok:false,status:503};
   if(String(url).includes('api.openai.com')) return {ok:true,json:async()=>({output:[{content:[{type:'output_text',text:'Private generated answer'}]}]})};
   return {ok:true,json:async()=>({candidates:[{content:{parts:[{text:'Private generated answer'}]}}]})};
  };
  const req={method:'POST',headers:auth?{cookie:`lumos_session=${sealed}`}:{},body:invalid?{message:''}:{message}};
  const res=response();
  let responseDeadline;
  try {
   await Promise.race([
    handler(req,res),
    new Promise((_,reject)=>{responseDeadline=setTimeout(()=>reject(new Error('chat waited for pending telemetry')),500);}),
   ]);
  } finally {clearTimeout(responseDeadline);}
  assert.equal(res.statusCode,status);
  if(status===200) {
   assert.equal(background.length,1,'telemetry is registered with the Vercel request lifetime');
   if(axiomPending || axiomTimeout) {
    assert.equal(axiomSettled,false,'the response is ready while Axiom is still pending');
    assert.equal(axiomSignal.aborted,false);
    if(axiomPending) releaseAxiom();
   }
   await Promise.all(background);
   if(axiomTimeout) assert.equal(axiomSignal.aborted,true,'existing transport timeout remains active');
   assert.equal(res.statusCode,200,'background failure cannot replace the response');
   assert.equal(res.payload.mode,mode);assert.equal(events.length,axiomConfigured?1:0);
   if(axiomConfigured) {
   const {_time,...metadata}=events[0];assert.ok(Number.isFinite(Date.parse(_time)));
   assert.deepEqual(metadata,{event:`chat.reply.${mode}.success`,route:'bridge_chat',status:200});
   }
   assert.equal('provider' in res.payload,false);assert.equal('model' in res.payload,false);
  } else assert.equal(events.filter(e=>e.event.startsWith('chat.reply.')).length,0);
  assert.doesNotMatch(JSON.stringify(events),/Private|private@example|private-session|private-subject|test-only/);
 } finally {
  releaseAxiom?.();
  await Promise.allSettled(background);
  if(savedContext===undefined)delete globalThis[contextKey];else globalThis[contextKey]=savedContext;
  globalThis.fetch=originalFetch;
  for(const k of envKeys) {if(saved[k]===undefined)delete process.env[k];else process.env[k]=saved[k];}
 }
}
test('model reply emits exactly one content-free success event',()=>scenario({}));
test('fallback reply counts once after provider failure',()=>scenario({fallback:true}));
test('local replies have a separate counter',()=>scenario({message:'Saat kaç?',mode:'hosted_local'}));
test('identity replies have a separate counter without identity metadata',()=>scenario({message:'Beni tanıyor musun?',mode:'hosted_identity_status'}));
test('memory status replies have a separate counter without memory content',()=>scenario({message:'Bunu hatırla: Private preference',mode:'hosted_memory_status'}));
test('unauthenticated request does not count',()=>scenario({auth:false,status:401}));
test('invalid request does not count',()=>scenario({invalid:true,status:400}));
test('model failure does not count',()=>scenario({modelFailure:true,status:502}));
test('telemetry outage preserves a successful chat response',()=>scenario({axiomFailure:true}));
test('slow telemetry completes in the background after the model reply',()=>scenario({axiomPending:true}));
test('slow telemetry does not delay local replies',()=>scenario({message:'Saat kaç?',mode:'hosted_local',axiomPending:true}));
test('a delayed telemetry rejection preserves the response',()=>scenario({axiomPending:true,axiomFailure:true}));
test('telemetry timeout runs after the response without changing it',()=>scenario({axiomTimeout:true}));
test('missing telemetry configuration preserves the response without a network event',()=>scenario({axiomConfigured:false}));
for(const axiomStatus of [401,429,500]) {
 test(`Axiom HTTP ${axiomStatus} preserves the chat response`,()=>scenario({axiomStatus}));
}
