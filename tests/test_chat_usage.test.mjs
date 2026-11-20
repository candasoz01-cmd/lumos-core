import assert from 'node:assert/strict';
import test from 'node:test';
import handler from '../api/bridge/chat.js';
import { sealSession } from '../api/_lib/lumos_session.js';

const envKeys = ['LUMOS_AUTH_STATE_SECRET','LUMOS_AXIOM_TOKEN','LUMOS_AXIOM_DATASET','OPENAI_API_KEY','LUMOS_GOOGLE_GEMINI_API_KEY','BRIDGE_UPSTREAM_URL','KANDO_BRIDGE_SECRET','LUMOS_MEMORY_LOOKUP_URL','LUMOS_MEMORY_SERVICE_TOKEN','SENTRY_DSN'];
function response() { return {statusCode:0, setHeader(){}, status(code){this.statusCode=code;return this;}, json(payload){this.payload=payload;return this;}, end(){return this;}}; }
async function scenario({message='Private request content',mode='hosted_chat',status=200,auth=true,fallback=false,modelFailure=false,axiomFailure=false,invalid=false}) {
 const saved=Object.fromEntries(envKeys.map(k=>[k,process.env[k]])); const originalFetch=globalThis.fetch; const events=[];
 try {
  for(const k of envKeys) delete process.env[k];
  process.env.LUMOS_AUTH_STATE_SECRET='test-only-secret-32-characters-minimum';
  process.env.LUMOS_AXIOM_TOKEN='test-only-axiom-token'; process.env.LUMOS_AXIOM_DATASET='lumos-test';
  process.env.OPENAI_API_KEY='test-only-openai-token';
  if(fallback) process.env.LUMOS_GOOGLE_GEMINI_API_KEY='test-only-gemini-token';
  const sealed=sealSession({sid:'private-session',sub:'private-subject',name:'Private Name',email:'private@example.test',provider:'google_web',exp:Math.floor(Date.now()/1000)+60});
  globalThis.fetch=async(url,init)=>{
   if(String(url).includes('api.axiom.co')) {
    assert.equal(String(url),'https://api.axiom.co/v1/datasets/lumos-test/ingest');
    assert.equal(init.headers.Authorization,'Bearer test-only-axiom-token');
    events.push(...JSON.parse(init.body));
    if(axiomFailure) throw new Error('simulated transport failure');
    return {ok:true};
   }
   if(modelFailure || (fallback && String(url).includes('api.openai.com'))) return {ok:false,status:503};
   if(String(url).includes('api.openai.com')) return {ok:true,json:async()=>({output:[{content:[{type:'output_text',text:'Private generated answer'}]}]})};
   return {ok:true,json:async()=>({candidates:[{content:{parts:[{text:'Private generated answer'}]}}]})};
  };
  const req={method:'POST',headers:auth?{cookie:`lumos_session=${sealed}`}:{},body:invalid?{message:''}:{message}};
  const res=response();await handler(req,res);assert.equal(res.statusCode,status);
  if(status===200) {
   assert.equal(res.payload.mode,mode);assert.equal(events.length,1);
   const {_time,...metadata}=events[0];assert.ok(Number.isFinite(Date.parse(_time)));
   assert.deepEqual(metadata,{event:`chat.reply.${mode}.success`,route:'bridge_chat',status:200});
   assert.equal('provider' in res.payload,false);assert.equal('model' in res.payload,false);
  } else assert.equal(events.filter(e=>e.event.startsWith('chat.reply.')).length,0);
  assert.doesNotMatch(JSON.stringify(events),/Private|private@example|private-session|private-subject|test-only/);
 } finally {
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
