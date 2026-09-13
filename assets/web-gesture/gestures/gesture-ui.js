import { GestureEngine } from './gesture-engine.js';
import { CameraSession } from './camera-session.js';

const EDGES = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];
export function setupGestures({ motion, onZoom, onHoldZoom, onActivity, onMotionChange, isDragging }) {
  const $ = id => document.getElementById(id);
  const engine = new GestureEngine();
  const video = $('camera-video'), overlay = $('hand-overlay'), ctx = overlay.getContext('2d');
  const toggle = $('gesture-toggle'), status = $('camera-status'), hint = $('gesture-hint');
  let manualUntil = 0, lastSnap = -Infinity;
  const session = new CameraSession({ video, onState, onResult });
  function clearPreview() { ctx.clearRect(0, 0, overlay.width, overlay.height); }
  function onState({ state, message }) {
    const on = ['loading', 'permission', 'starting', 'active'].includes(state);
    onActivity(on);
    toggle.textContent = state === 'active' ? '关闭手势控制' : on ? '取消开启' : state === 'error' ? '重试手势控制' : '开启手势控制';
    toggle.setAttribute('aria-pressed', String(on));
    status.textContent = message; status.dataset.state = state;
    $('camera-preview').hidden = !['starting', 'active'].includes(state);
    $('hand-count').textContent = '0 / 2 只手';
    if (!on) {
      clearPreview(); engine.reset(); onHoldZoom();
      hint.textContent = '拉开回正并放大，靠拢缩小整张卡。';
      $('snap-status').textContent='准备响指：拇指与中指贴合，看到“就绪”后弹开';
      if (motion.mode === 'spin') { motion.pause(); onMotionChange(); }
    }
  }
  function onResult(data, aspect) {
    clearPreview();
    const w = overlay.width, h = overlay.height;
    for (const [i, points] of data.landmarks.entries()) {
      ctx.strokeStyle = ctx.fillStyle = i ? '#237d9b' : '#9b7024'; ctx.lineWidth = 2;
      ctx.beginPath();
      for (const [a,b] of EDGES) { ctx.moveTo(points[a].x*w,points[a].y*h); ctx.lineTo(points[b].x*w,points[b].y*h); }
      ctx.stroke();
      for (const p of points) { ctx.beginPath(); ctx.arc(p.x*w,p.y*h,2.5,0,Math.PI*2); ctx.fill(); }
    }
    $('hand-count').textContent = `${data.landmarks.length} / 2 只手`;
    if (isDragging() || data.timestamp < manualUntil) {
      engine.rebase(); hint.textContent = '手动调整中，稍后重新建立双手基准。'; return;
    }
    // Stale results must not resume an old gesture after a manual interruption.
    const result = engine.update(data.landmarks, data.timestamp, motion.zoom, aspect);
    if (result.phase !== 'tracking') onHoldZoom();
    else if (result.zoom !== motion.zoom) onZoom(result.zoom);
    if (result.enlarging) { motion.faceFront(); onMotionChange(); }
    if (result.snap && !result.enlarging) {
      motion.toggleSpin(); onMotionChange(); lastSnap = data.timestamp;
      $('snap-status').textContent = motion.mode === 'spin' ? '识别到响指候选 · 已开始转动' : '识别到响指候选 · 已暂停转动';
    } else if (data.timestamp - lastSnap > 700) {
      const snapMessages={
        idle:'准备响指：拇指与中指贴合',contact:'已看到贴合 · 保持一瞬',
        armed:'响指已就绪 · 快速弹开中指',cooldown:'响指冷却中 · 稍等再试',
        'index-pinch':'请用拇指与中指，食指捏合不会触发',
        'contact-missed':'没捕捉到贴合 · 请稍停一下再弹开',
        'release-missed':'没捕捉到快速弹开 · 保持手掌入镜再试',
        retry:'请松开手指，重新准备响指',
      };
      $('snap-status').textContent=snapMessages[result.snapPhase];
    }
    const messages = {
      tracking: '基准已建立 · 拉开回正并放大，靠拢缩小',
      calibrating: '双手保持片刻，正在建立距离基准…',
      waiting: '让两只手完整入镜；当前大小保持。',
      overlap: '双手稍微分开；当前大小保持。',
      unstable: '手部移动过快，请保持片刻重新定位。',
      'snap-hold': '响指已响应 · 暂时保持大小，避免误回正',
    };
    hint.textContent = messages[result.phase];
  }
  toggle.onclick = () => {
    if (['loading', 'permission', 'starting', 'active'].includes(session.state)) session.stop();
    else if (!isSecureContext || !navigator.mediaDevices?.getUserMedia || !window.Worker || !window.createImageBitmap) {
      session.fail({ code: 'WORKER' });
    } else { engine.reset(); void session.start(); }
  };
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && !['off','error'].includes(session.state)) session.stop('页面已离开前台，摄像头已关闭。');
    if (document.hidden && motion.mode === 'spin') { motion.pause(); onMotionChange(); }
  });
  window.addEventListener('pagehide', () => session.stop());
  return {
    manual() { manualUntil = performance.now() + 450; engine.rebase(); },
    stop: () => session.stop(),
    get state() { return session.state; },
  };
}
