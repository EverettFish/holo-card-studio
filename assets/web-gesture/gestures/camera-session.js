export function cameraError(error) {
  const messages = {
    NotAllowedError: '摄像头权限被拒绝。请在 Chrome 地址栏的网站设置中允许摄像头，然后重试。',
    NotFoundError: '没有找到摄像头。请连接或启用摄像头后重试。',
    NotReadableError: '摄像头无法读取，可能正被其他程序占用。关闭占用程序后重试。',
    OverconstrainedError: '摄像头不支持当前画面设置，请换用其他摄像头。',
    SecurityError: '浏览器限制了摄像头，请用 Chrome 打开本地入口。',
    MODEL: '手部模型加载失败。请确认已安装依赖和模型，然后重试。',
    WORKER: '浏览器无法启动手部识别，请用 Chrome 打开本地入口。',
    TIMEOUT: '手部识别响应超时，已关闭摄像头。请重试。',
    VIDEO: '摄像头画面没有就绪，已关闭摄像头。请重试。',
    ENDED: '摄像头已断开或权限已撤销，请检查设备后重试。',
    INFERENCE: '手部识别中断，已关闭摄像头。请重试。',
  };
  return messages[error?.code] || messages[error?.name] || '手势控制启动失败，请用 Chrome 重试。';
}

export class CameraSession {
  constructor({ video, onState, onResult, createWorker, getMedia, makeBitmap, now, setTimer, clearTimer }) {
    this.video = video; this.onState = onState; this.onResult = onResult;
    this.createWorker = createWorker || (() => new Worker(new URL('./hand-worker.js', import.meta.url)));
    this.getMedia = getMedia || (c => navigator.mediaDevices.getUserMedia(c));
    this.makeBitmap = makeBitmap || (v => createImageBitmap(v));
    this.now = now || (() => performance.now());
    this.setTimer = setTimer || ((fn, ms) => setTimeout(fn, ms));
    this.clearTimer = clearTimer || (id => clearTimeout(id));
    this.token = 0; this.state = 'off'; this.worker = null; this.stream = null;
  }
  emit(state, message) { this.state = state; this.onState({ state, message }); }
  async start() {
    if (['loading', 'permission', 'starting', 'active'].includes(this.state)) return;
    const token = ++this.token;
    const current = () => token === this.token;
    this.emit('loading', '正在加载手部模型…');
    try {
      this.worker = this.createWorker();
      await new Promise((resolve, reject) => {
        this.cancelStart = () => reject({ code: 'CANCELLED' });
        this.deadline = this.setTimer(() => reject({ code: 'MODEL' }), 20000);
        this.worker.onerror = () => reject({ code: 'WORKER' });
        this.worker.onmessage = ({ data }) => {
          if (data.type === 'ready') resolve();
          if (data.type === 'error') reject(data);
        };
        this.worker.postMessage({ type: 'init' });
      });
      if (!current()) return;
      this.clearTimer(this.deadline); this.cancelStart = null;
      this.worker.onmessage = ({ data }) => this.handleMessage(data, token);
      this.worker.onerror = () => { if (current()) this.fail({ code: 'WORKER' }); };
      this.emit('permission', '请允许摄像头访问；只在本机处理。');
      const stream = await this.getMedia({ audio: false, video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30, max: 30 } } });
      if (!current()) { stream.getTracks().forEach(t => t.stop()); return; }
      this.stream = stream;
      stream.getTracks().forEach(t => t.addEventListener('ended', () => { if (current()) this.fail({ code: 'ENDED' }); }));
      this.video.srcObject = stream;
      this.emit('starting', '正在准备摄像头画面…');
      await new Promise((resolve, reject) => {
        this.cancelStart = () => reject({ code: 'CANCELLED' });
        this.deadline = this.setTimer(() => reject({ code: 'VIDEO' }), 10000);
        this.video.play().then(resolve, reject);
      });
      if (!current()) return;
      this.clearTimer(this.deadline); this.cancelStart = null;
      this.busy = false; this.lastVideoTime = -1; this.lastFrame = -Infinity; this.lastResult = this.now();
      this.emit('active', '摄像头已开启');
      this.schedule(token);
    } catch (error) { if (current()) this.fail(error); }
  }
  schedule(token) {
    if (token !== this.token || this.state !== 'active') return;
    this.timer = this.setTimer(() => { void this.frame(token); }, 1000 / 24);
  }
  async frame(token) {
    if (token !== this.token || this.state !== 'active') return;
    const now = this.now();
    if (now - this.lastResult > 5000) { this.fail({ code: 'TIMEOUT' }); return; }
    this.schedule(token);
    if (this.busy || this.video.readyState < 2 || this.video.currentTime === this.lastVideoTime) return;
    this.busy = true; this.lastVideoTime = this.video.currentTime;
    try {
      const bitmap = await this.makeBitmap(this.video);
      if (token !== this.token) { bitmap.close(); return; }
      this.lastFrame = now;
      this.worker.postMessage({ type: 'frame', bitmap, timestamp: now }, [bitmap]);
    } catch { if (token === this.token) this.fail({ code: 'VIDEO' }); }
  }
  handleMessage(data, token) {
    if (token !== this.token) return;
    if (data.type === 'error') { this.fail(data); return; }
    if (data.type !== 'result' || this.state !== 'active') return;
    this.busy = false; this.lastResult = this.now();
    this.onResult(data, this.video.videoWidth / this.video.videoHeight || 4 / 3);
  }
  stop(message = '摄像头未开启') {
    ++this.token;
    this.clearTimer(this.timer); this.clearTimer(this.deadline);
    this.cancelStart?.(); this.cancelStart = null;
    this.worker?.terminate(); this.worker = null;
    this.stream?.getTracks().forEach(t => t.stop()); this.stream = null;
    this.video.pause(); this.video.srcObject = null; this.busy = false;
    this.emit('off', message);
  }
  fail(error) { this.stop(); this.emit('error', cameraError(error)); }
}
