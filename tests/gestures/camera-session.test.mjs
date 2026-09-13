import test from 'node:test';
import assert from 'node:assert/strict';
import {CameraSession,cameraError} from '../../assets/web-gesture/gestures/camera-session.js';
const flush = async()=>{for(let i=0;i<8;i++)await Promise.resolve();};
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve};};
function rig(options={}){
  let now=0;const timers=new Map(),workers=[],states=[],results=[],requests=[];let timerId=0;
  const track={stops:0,stop(){this.stops++;},addEventListener(name,cb){this[name]=cb;}};
  const stream={getTracks:()=>[track]};
  const video={srcObject:null,readyState:3,currentTime:1,videoWidth:640,videoHeight:480,play:()=>Promise.resolve(),pause(){}};
  const session=new CameraSession({video,onState:s=>states.push(s),onResult:r=>results.push(r),
    now:()=>now,setTimer:(fn,ms)=>{timers.set(++timerId,{fn,ms});return timerId;},clearTimer:id=>timers.delete(id),
    getMedia:constraints=>{requests.push(constraints);return options.media?options.media(stream):Promise.resolve(stream);},
    createWorker:()=>{const w={messages:[],terminated:false,postMessage(m){this.messages.push(m);if(m.type==='init'&&!options.holdModel)queueMicrotask(()=>this.onmessage({data:{type:'ready'}}));},terminate(){this.terminated=true;}};workers.push(w);return w;},
    makeBitmap:options.makeBitmap||(()=>Promise.resolve({close(){}})),
  });
  return{session,video,track,workers,states,results,requests,timers,setNow:t=>now=t};
}
test('默认关闭；明确启动才请求摄像头且 audio=false；关闭全部资源',async()=>{
  const r=rig();assert.equal(r.requests.length,0);await r.session.start();assert.equal(r.session.state,'active');assert.equal(r.requests[0].audio,false);
  r.session.stop();assert.equal(r.track.stops,1);assert.equal(r.video.srcObject,null);assert.ok(r.workers[0].terminated);assert.equal(r.timers.size,0);
});
test('加载期间重复启动不会创建多份 Worker，取消清理',async()=>{
  const r=rig({holdModel:true});const pending=r.session.start();await r.session.start();assert.equal(r.workers.length,1);
  r.session.stop();await pending;assert.equal(r.requests.length,0);assert.equal(r.session.state,'off');assert.equal(r.timers.size,0);
});
test('等待摄像头授权时取消，迟到的媒体流立即停止',async()=>{
  const d=deferred();const r=rig({media:s=>{r.stream=s;return d.promise;}});const pending=r.session.start();await flush();assert.equal(r.session.state,'permission');
  r.session.stop();d.resolve(r.stream);await pending;assert.equal(r.track.stops,1);assert.equal(r.session.state,'off');assert.equal(r.video.srcObject,null);
});
test('拒绝授权及模型失败均回收 Worker 并给中文错误',async()=>{
  const r=rig({media:()=>Promise.reject({name:'NotAllowedError'})});await r.session.start();assert.equal(r.session.state,'error');assert.match(r.states.at(-1).message,/权限被拒绝/);assert.ok(r.workers[0].terminated);
  const q=rig({holdModel:true});const pending=q.session.start();q.workers[0].onmessage({data:{type:'error',code:'MODEL'}});await pending;assert.equal(q.session.state,'error');assert.equal(q.requests.length,0);
});
test('摄像头断开释放资源；迟到的识别结果不能控制卡片',async()=>{
  const r=rig();await r.session.start();const w=r.workers[0];r.track.ended();assert.equal(r.session.state,'error');assert.equal(r.track.stops,1);
  w.onmessage({data:{type:'result',landmarks:[]}});assert.equal(r.results.length,0);
});
test('只允许一帧在途，关闭时释放尚未转交的位图',async()=>{
  const d=deferred();let closed=0;const r=rig({makeBitmap:()=>d.promise});await r.session.start();
  const p=r.session.frame(r.session.token);r.video.currentTime=2;await r.session.frame(r.session.token);
  assert.equal(r.workers[0].messages.filter(m=>m.type==='frame').length,0);r.session.stop();d.resolve({close(){closed++;}});await p;assert.equal(closed,1);
});
test('推理超时自动关闭；错误类别都有对应提示',async()=>{
  const r=rig();await r.session.start();r.setNow(5100);await r.session.frame(r.session.token);assert.equal(r.session.state,'error');assert.equal(r.track.stops,1);
  for(const name of ['NotFoundError','NotReadableError','OverconstrainedError','SecurityError'])assert.ok(cameraError({name}).length>10);
});
