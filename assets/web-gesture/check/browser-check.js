import { CameraSession } from '../gestures/camera-session.js';
const $ = id => document.getElementById(id);
const wait = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, timeout=15000) {
  const start=performance.now();
  while(!fn()){if(performance.now()-start>timeout)throw Error('等待条件超时');await wait(50);}
}
const lines=[];
function check(name,condition){if(!condition)throw Error(name);lines.push('通过 · '+name);$('result').textContent=lines.join('\n');}
async function sampleFrames(win) {
  return new Promise(resolve=>{
    const values=[];let start,last;
    function frame(t){
      start??=t;if(last!==undefined)values.push(t-last);last=t;
      if(t-start<1500){win.requestAnimationFrame(frame);return;}
      const sorted=[...values].sort((a,b)=>a-b);
      resolve({fps:(values.length*1000/(t-start)).toFixed(1),p95:sorted[Math.floor(sorted.length*.95)].toFixed(1)});
    }
    win.requestAnimationFrame(frame);
  });
}
$('run').onclick=async()=>{
  $('run').disabled=true;lines.length=0;
  lines.push('浏览器：'+navigator.userAgent,'验证输入：生成的空白视频帧与受控页面事件；真实摄像头：未开启');
  $('result').textContent=lines.join('\n');
  let session,stream,paint,lockedFrame;
  try{
    const iframe=$('app');await until(()=>iframe.contentWindow.__holo?.ready);
    const win=iframe.contentWindow,doc=iframe.contentDocument,h=win.__holo;
    const stage=doc.getElementById('stage'),button=id=>doc.getElementById(id);
    check('项目卡面配置与 GLB 已加载',Boolean(h.config.title)&&h.root.children.length>0);
    lines.push('当前卡片：'+h.config.title);
    check('默认摄像头关闭且没有媒体流',h.gestures.state==='off'&&!button('camera-video').srcObject);
    // Keep human input out of controlled assertions; the return link stays usable.
    iframe.inert=true;lockedFrame=iframe;
    const subject=h.uniforms.uScale.value,view=h.camera.top;
    stage.dispatchEvent(new win.WheelEvent('wheel',{deltaY:100,cancelable:true}));
    await until(()=>h.camera.top>view);
    check('滚轮改变整卡视野，主体材质比例保持',h.motion.zoom<1&&h.camera.top>view&&h.uniforms.uScale.value===subject);
    button('scale').value='1.3';button('scale').dispatchEvent(new win.Event('input',{bubbles:true}));
    check('主体滑块与整卡大小独立',h.uniforms.uScale.value===1.3&&Math.abs(h.motion.zoom-.9)<1e-8);
    button('scale').value=String(subject);button('scale').dispatchEvent(new win.Event('input',{bubbles:true}));button('reset').click();
    button('spin').click();check('持续转动可以明确启动',h.motion.mode==='spin');
    await until(()=>h.motion.back,8500);check('实际渲染循环转到背面',h.motion.back);
    await until(()=>!h.motion.back,8500);check('继续转动返回正面',!h.motion.back);
    button('spin').click();const paused=h.motion.y;await wait(250);
    check('暂停后角度保持不回弹',Math.abs(h.motion.y-paused)<1e-8);
    button('spin').click();button('auto').click();check('自动赏卡和持续转动互斥',h.motion.mode==='sway');
    button('spin').click();button('flip').click();check('翻面停止持续转动',h.motion.mode==='paused');
    button('spin').click();stage.dispatchEvent(new win.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));
    check('方向键接管并停止持续转动',h.motion.mode==='paused');
    button('reset').click();
    check('复位恢复 100% 和暂停状态',h.motion.zoom===1&&h.motion.mode==='paused');
    button('flip').click();await until(()=>h.motion.back);button('spin').click();button('spin').click();
    stage.dispatchEvent(new win.WheelEvent('wheel',{deltaY:-80,cancelable:true}));
    await until(()=>Math.abs(Math.atan2(Math.sin(h.motion.y+.13),Math.cos(h.motion.y+.13)))<.01);
    check('暂停在背面后再次放大，自动回到原正面角度',!h.motion.back&&h.motion.mode==='paused'&&h.motion.zoom>1);
    button('reset').click();
    const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
    const context=canvas.getContext('2d');context.fillStyle='#eee';context.fillRect(0,0,640,480);
    stream=canvas.captureStream(24);
    paint=setInterval(()=>{context.fillRect(0,0,640,480);},1000/24);
    let frames=0,error='',inference=[];
    session=new CameraSession({video:$('synthetic-video'),getMedia:async()=>stream,
      onState:s=>{if(s.state==='error')error=s.message;},
      onResult:r=>{frames++;inference.push(r.inferenceMs);if(r.landmarks.length)error='空白帧出现意外手部结果';},
    });
    await session.start();if(error)throw Error(error);
    await until(()=>frames>=4||error,12000);if(error)throw Error(error);
    check('本地 MediaPipe 1.0.1 模型在 Worker 中完成真实推理',frames>=4);
    lines.push('空白帧推理耗时：'+inference.map(t=>t.toFixed(1)+' ms').join(' / '));
    const fullWidth=h.renderer.domElement.width;
    const fullFrames=await sampleFrames(win);
    h.setGestureActive(true);
    const gestureWidth=h.renderer.domElement.width;
    const gestureFrames=await sampleFrames(win);
    check('手势模式降低绘制像素，保持卡片与相机大小',gestureWidth<=fullWidth&&h.motion.zoom===1);
    lines.push('同一画布的绘制宽度：普通 '+fullWidth+' px / 手势 '+gestureWidth+' px');
    lines.push('短时绘制采样（同时运行空白帧推理）：普通 '+fullFrames.fps+' fps / p95 '+fullFrames.p95+' ms；手势 '+gestureFrames.fps+' fps / p95 '+gestureFrames.p95+' ms');
    $('performance').textContent=lines.slice(-2).join('\n');
    h.setGestureActive(false);
    session.stop();
    check('停止后所有合成媒体轨道 ended，视频与 Worker 已释放',stream.getTracks().every(t=>t.readyState==='ended')&&!session.worker&&!$('synthetic-video').srcObject);
    const resources=win.performance.getEntriesByType('resource');
    check('卡片资源请求均来自当前本地服务',resources.every(r=>new URL(r.name).origin===location.origin));
    lines.push('本轮受控浏览器验证全部通过。真人手感需要另行试用。');
  }catch(error){lines.push('失败 · '+error.message);}
  finally{session?.stop();stream?.getTracks().forEach(t=>t.stop());clearInterval(paint);if(lockedFrame)lockedFrame.inert=false;$('result').textContent=lines.join('\n');$('run').disabled=false;}
};
