// Classic Worker: MediaPipe's WASM loader uses importScripts in this environment.
let landmarker;
self.onmessage = async ({ data }) => {
  if (data.type === 'init') {
    try {
      importScripts('../node_modules/@mediapipe/tasks-vision/vision_bundle.js');
      const files = await Vision.FilesetResolver.forVisionTasks(new URL('../node_modules/@mediapipe/tasks-vision/wasm', self.location).href);
      landmarker = await Vision.HandLandmarker.createFromOptions(files, {
        baseOptions: { modelAssetPath: new URL('../models/hand_landmarker.task', self.location).href, delegate: 'CPU' },
        runningMode: 'VIDEO', numHands: 2,
        minHandDetectionConfidence: 0.6, minHandPresenceConfidence: 0.6, minTrackingConfidence: 0.6,
      });
      self.postMessage({ type: 'ready' });
    } catch { self.postMessage({ type: 'error', code: 'MODEL' }); }
    return;
  }
  if (data.type !== 'frame') return;
  const { bitmap, timestamp } = data;
  try {
    const started = performance.now();
    const result = landmarker.detectForVideo(bitmap, timestamp);
    self.postMessage({ type: 'result', timestamp, landmarks: result.landmarks,
      inferenceMs: performance.now() - started });
  } catch { self.postMessage({ type: 'error', code: 'INFERENCE' }); }
  finally { bitmap.close(); }
};
