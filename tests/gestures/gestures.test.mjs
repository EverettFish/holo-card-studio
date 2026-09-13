import test from 'node:test';
import assert from 'node:assert/strict';
import {GestureEngine,SETTINGS} from '../../assets/web-gesture/gestures/gesture-engine.js';
import {CardMotion} from '../../assets/web-gesture/gestures/card-motion.js';
import {hand,pair} from './fixtures.mjs';
const close = (a,b,tolerance=1e-9) => assert.ok(Math.abs(a-b)<tolerance, `${a} != ${b}`);
function rig(zoom=1) {
  const engine=new GestureEngine();let time=-50;
  return {engine,get zoom(){return zoom;},get time(){return time;},step(hands,ms=50){time+=ms;const r=engine.update(hands,time,zoom,1);zoom=r.zoom;return r;},stable(d=.5,n=7){for(let i=0;i<n;i++)this.step(pair(d));}};
}
function snap(r, x=.3) {
  r.step([hand(x)]);r.step([hand(x,'contact')]);r.step([hand(x,'contact')]);r.step([hand(x,'contact')]);return r.step([hand(x)]);
}
test('双手拉开放大、靠拢缩小，作用于当前比例',()=>{
  const r=rig(.9);r.stable();close(r.zoom,.9);r.stable(.6,5);assert.ok(r.zoom>.99);r.stable(.5,2);r.stable(.4,7);assert.ok(r.zoom<.8);
});
test('微小抖动落在死区，尺寸不漂移',()=>{
  const r=rig();r.stable();for(let i=0;i<30;i++)r.step(pair(i%2?.505:.495));close(r.zoom,1);
});
test('上下限饱和后反向移动立刻回到可控范围',()=>{
  const r=rig();r.stable();for(const d of [.6,.7,.8,.9])r.stable(d,8);close(r.zoom,SETTINGS.maxZoom);r.stable(.75,5);assert.ok(r.zoom<1.15);
  for(const d of [.6,.5,.4,.3])r.stable(d,8);close(r.zoom,SETTINGS.minZoom);r.stable(.4,5);assert.ok(r.zoom>.72);
});
test('丢失任意一只手立即保持，新距离重建基准不回跳',()=>{
  const r=rig();r.stable();r.stable(.56,6);const held=r.zoom;
  r.step([hand(.2)]);close(r.zoom,held);r.step([]);close(r.zoom,held);
  r.stable(.30,7);close(r.zoom,held);r.stable(.33,4);assert.ok(r.zoom>held);
});
test('两手输出次序和左右标签交换不影响比例或误触发',()=>{
  const r=rig();r.stable();for(let i=0;i<20;i++){const result=r.step(pair(.5,i%2===0));close(r.zoom,1);assert.equal(result.snap,false);}
});
test('重叠、距离突跳、长时间停帧都保持并重建基准',()=>{
  const r=rig();r.stable();assert.equal(r.step(pair(.08)).phase,'overlap');close(r.zoom,1);
  r.stable(.6);close(r.zoom,1);assert.equal(r.step(pair(.95)).phase,'unstable');close(r.zoom,1);
  r.step(pair(.3),500);r.stable(.3);close(r.zoom,1);
});
test('无效关键点及乱序时间戳不改变尺寸',()=>{
  const r=rig();r.stable();const bad=hand(.2);bad[4].x=NaN;
  assert.equal(r.step([bad,hand(.8)]).handCount,1);close(r.zoom,1);
  const old=r.engine.update(pair(.8),r.time-10,r.zoom,1);close(old.zoom,1);
});
test('手动缩放后重新建立当前比例基准',()=>{
  const e=new GestureEngine();for(let t=0;t<=300;t+=50)e.update(pair(.5),t,1,1);
  e.rebase();for(let t=350;t<=700;t+=50)close(e.update(pair(.8),t,.8,1).zoom,.8);
});
test('合格的中指贴合再快速弹开只触发一次',()=>{
  const r=rig();assert.equal(snap(r).snap,true);for(let i=0;i<10;i++)assert.equal(r.step([hand(.3)]).snap,false);
});
test('静态贴合、单帧接触、普通食指捏合不触发',()=>{
  for(const pose of ['contact','index-pinch']){const r=rig();for(let i=0;i<30;i++)assert.equal(r.step([hand(.3,pose)]).snap,false);}
  const r=rig();r.step([hand(.3)]);r.step([hand(.3,'contact')]);assert.equal(r.step([hand(.3)]).snap,false);
});
test('缓慢松开及仅移动拇指的动作不触发',()=>{
  const r=rig();r.step([hand(.3)]);for(let i=0;i<3;i++)r.step([hand(.3,'contact')]);
  for(let i=1;i<=8;i++){const p=hand(.3,'contact');p[12].x+=i*.02;assert.equal(r.step([p]).snap,false);}
  const q=rig();q.step([hand(.3)]);for(let i=0;i<3;i++)q.step([hand(.3,'contact')]);
  const p=hand(.3,'contact');p[4].x+=.18;assert.equal(q.step([p]).snap,false);
});
test('响指全局冷却阻止连触发，结束后需要完整新动作',()=>{
  const r=rig();assert.equal(snap(r).snap,true);assert.equal(snap(r,.7).snap,false);
  for(let i=0;i<25;i++)r.step([hand(.3)]);assert.equal(snap(r).snap,true);
});
test('两手同帧响指最多切换一次；次序交换保持动作归属',()=>{
  const r=rig();r.step([hand(.2),hand(.8)]);
  for(let i=0;i<3;i++)r.step([hand(.2,'contact'),hand(.8,'contact')].reverse());
  assert.equal(r.step([hand(.2),hand(.8)]).snap,true);assert.equal(r.step([hand(.8),hand(.2)]).snap,false);
});
test('接触后丢手或身份跳变不能拼成响指',()=>{
  for(const lose of [true,false]){const r=rig();r.step([hand(.3)]);for(let i=0;i<3;i++)r.step([hand(.3,'contact')]);
  if(lose)r.step([]);assert.equal(r.step([hand(lose?.3:.75)]).snap,false);}
});
test('持续转动展示两面，暂停角度保持，恢复后可继续',()=>{
  const m=new CardMotion();m.toggleSpin();let front=0,back=0;
  for(let i=0;i<750;i++){m.tick(1/60);m.back?back++:front++;}assert.ok(front>100&&back>100);
  m.toggleSpin();const y=m.y;for(let i=0;i<100;i++)m.tick(1/60);close(m.y,y);
  m.toggleSpin();m.tick(.1);assert.notEqual(m.y,y);
});
test('持续转动与赏卡互斥，翻面和复位停止，低动态下可明确启停',()=>{
  const m=new CardMotion();m.toggleSpin();m.toggleSway();assert.equal(m.mode,'sway');m.toggleSpin();assert.equal(m.mode,'spin');
  m.flip();assert.equal(m.mode,'paused');m.tick(1,true);assert.equal(m.back,true);m.toggleSpin();m.tick(.1,true);m.pause();assert.equal(m.mode,'paused');
  m.setZoom(.75);m.reset();close(m.zoom,1);assert.equal(m.mode,'paused');
});
test('放大从暂停的背面或侧面回到原正面角度，保留目标大小',()=>{
  for(const angle of [Math.PI,Math.PI/2,-Math.PI/2]){
    const m=new CardMotion();m.y=m.targetY=angle;m.x=m.targetX=.2;m.setZoom(1.12);
    m.tick(1,true);close(Math.atan2(Math.sin(m.y+.13),Math.cos(m.y+.13)),0);close(m.x,.025);close(m.zoom,1.12);assert.equal(m.mode,'paused');
  }
});
test('放大接管转动；单纯暂停与缩小仍保持当前朝向',()=>{
  const m=new CardMotion();m.toggleSpin();m.tick(1);m.setZoom(1.1);assert.equal(m.mode,'paused');
  m.y=m.targetY=2.2;m.pause();m.setZoom(.9);m.tick(.1);close(m.y,2.2);
});
test('缩放在绘制帧间连续插值，失去跟踪时冻结可见大小',()=>{
  const m=new CardMotion();m.setZoom(.75);m.tick(1/60);assert.ok(m.displayZoom<1&&m.displayZoom>.75);
  const first=m.displayZoom;m.tick(1/60);assert.ok(m.displayZoom<first);
  m.holdZoom();const held=m.displayZoom;for(let i=0;i<30;i++)m.tick(1/60);close(m.displayZoom,held);close(m.zoom,held);
});
test('已达放大上限时仍识别放大意图，用于回正面',()=>{
  const r=rig(SETTINGS.maxZoom);r.stable();const result=r.step(pair(.55));
  assert.equal(result.enlarging,true);close(result.zoom,SETTINGS.maxZoom);
  const m=new CardMotion();m.zoom=m.displayZoom=SETTINGS.maxZoom;m.y=m.targetY=2.2;
  m.setZoom(1.3);m.tick(1,true);assert.equal(m.back,false);close(m.zoom,SETTINGS.maxZoom);
});
test('手以贴合姿势入镜，两帧接触后可以触发；静态本身不触发',()=>{
  const r=rig();assert.equal(r.step([hand(.3,'contact')]).snap,false);
  const ready=r.step([hand(.3,'contact')],40);assert.equal(ready.snapPhase,'armed');assert.equal(ready.snap,false);
  assert.equal(r.step([hand(.3)],40).snap,true);
});
test('中指已贴合时，食指自然弯曲靠近拇指不会废弃整个候选',()=>{
  const r=rig();const bent=pose=>{const p=hand(.3,pose);p[8]={x:p[4].x+.02,y:p[4].y,z:0};return p;};
  r.step([bent('contact')]);r.step([bent('contact')]);assert.equal(r.step([bent('open')]).snap,true);
});
test('另一只手出画，仍跟踪中的响指手保持动作归属',()=>{
  const r=rig();r.step([hand(.2,'contact'),hand(.8)]);r.step([hand(.2,'contact')]);
  assert.equal(r.step([hand(.2)]).snap,true);
});
test('漏掉一个释放中间帧时，仍允许足够快速的中指位移',()=>{
  const r=rig();r.step([hand(.3,'contact')]);r.step([hand(.3,'contact')]);
  assert.equal(r.step([hand(.3)],180).snap,true);
});
test('响指同帧的掌心拉开不触发放大回正，随后重新建立缩放基准',()=>{
  const r=rig();r.stable();r.step([hand(.25,'contact'),hand(.75)]);r.step([hand(.25,'contact'),hand(.75)]);
  const fired=r.step([hand(.19),hand(.75)]);assert.equal(fired.snap,true);assert.equal(fired.enlarging,false);assert.equal(fired.phase,'snap-hold');close(r.zoom,1);
  assert.equal(r.step(pair(.65),100).phase,'snap-hold');r.stable(.65,15);close(r.zoom,1);
  r.stable(.72,5);assert.ok(r.zoom>1);
});
