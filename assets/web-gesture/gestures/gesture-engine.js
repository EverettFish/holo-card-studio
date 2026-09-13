// All gesture thresholds live here. No camera, DOM, or renderer dependencies.
export const SETTINGS = Object.freeze({
  minZoom: 0.70, maxZoom: 1.18, calibrationMs: 250, stableRatio: 0.07,
  deadZone: 0.025, smoothingMs: 120, maxGapMs: 220,
  minDistance: 0.13, maxDistanceStep: 0.20, maxHandStep: 0.16,
  contact: 0.40, release: 0.65, contactMs: 35, contactFrames: 2, maxContactMs: 2500,
  releaseMs: 220, releaseSpeed: 3.0, middleTravel: 0.22,
  indexSeparation: 0.28, cooldownMs: 1200, snapScaleHoldMs: 450,
});
export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const relative = (a, b) => ({ x: a.x - b.x, y: a.y - b.y });

function describe(points, aspect) {
  if (points?.length !== 21 || !points.every(p => Number.isFinite(p.x) && Number.isFinite(p.y))) return null;
  const p = points.map(v => ({ x: v.x * aspect, y: v.y }));
  const center = [0, 5, 9, 13, 17].reduce((a, i) => ({ x: a.x + p[i].x / 5, y: a.y + p[i].y / 5 }), { x: 0, y: 0 });
  const size = distance(p[0], p[9]);
  if (size < 0.035 || size > 0.8) return null;
  return { center, size, gap: distance(p[4], p[12]) / size,
    indexGap: distance(p[4], p[8]) / size, middle: relative(p[12], p[0]) };
}

export class GestureEngine {
  constructor(settings = {}) {
    this.settings = { ...SETTINGS, ...settings };
    this.cooldownUntil = -Infinity;
    this.scaleHoldUntil = -Infinity;
    this.lastTime = null;
    this.rebase();
  }
  rebase() {
    this.pair = null;
    this.calibration = null;
    this.lastDistance = null;
    this.tracks = [];
  }
  reset() { this.rebase(); this.lastTime = null; this.cooldownUntil = this.scaleHoldUntil = -Infinity; }

  update(landmarks, timestamp, zoom, aspect = 4 / 3) {
    const s = this.settings;
    const result = { zoom, handCount: 0, phase: 'waiting', snap: false, enlarging: false, snapPhase: 'idle' };
    if (!Number.isFinite(timestamp) || (this.lastTime !== null && timestamp <= this.lastTime)) return result;
    const dt = this.lastTime === null ? 0 : timestamp - this.lastTime;
    if (dt > s.maxGapMs) this.rebase();
    this.lastTime = timestamp;
    const hands = (landmarks || []).slice(0, 2).map(p => describe(p, aspect)).filter(Boolean);
    result.handCount = hands.length;
    const d = hands.length === 2 ? distance(hands[0].center, hands[1].center) : null;
    const overlap = d !== null && d < Math.max(s.minDistance, (hands[0].size + hands[1].size) * 0.6);
    if (overlap) {
      this.rebase();
      result.phase = 'overlap';
      return result;
    }
    // Spatial matching is independent of array order and handedness labels.
    let old = this.tracks;
    if (hands.length === 2 && old.length === 2) {
      const same = distance(hands[0].center, old[0].hand.center) + distance(hands[1].center, old[1].hand.center);
      const swap = distance(hands[0].center, old[1].hand.center) + distance(hands[1].center, old[0].hand.center);
      if (Math.abs(same - swap) < 0.035) old = [];
      else if (swap < same) old = [old[1], old[0]];
    } else if (hands.length === 1 && old.length === 2) {
      const a=distance(hands[0].center,old[0].hand.center),b=distance(hands[0].center,old[1].hand.center);
      old=Math.abs(a-b)<.035?[]:[old[a<b?0:1]];
    } else if (hands.length === 2 && old.length === 1) {
      const a=distance(hands[0].center,old[0].hand.center),b=distance(hands[1].center,old[0].hand.center);
      old=Math.abs(a-b)<.035?[]:a<b?[old[0],null]:[null,old[0]];
    } else if (hands.length !== old.length) old = [];
    let fired = false;
    this.tracks = hands.map((hand, i) => {
      let track = old[i];
      if (!track || distance(hand.center, track.hand.center) > s.maxHandStep) track = { state: 'idle' };
      if (timestamp < this.cooldownUntil) { track.state = 'idle'; track.reason = ''; }
      else if (this.updateSnap(track, hand, timestamp)) fired = true;
      track.hand = hand;
      return track;
    });
    if (fired) {
      result.snap = true;
      this.cooldownUntil = timestamp + s.cooldownMs;
      this.scaleHoldUntil = timestamp + s.snapScaleHoldMs;
      this.tracks.forEach(t => { t.state = 'idle'; t.reason = ''; });
    }
    result.snapPhase=timestamp<this.cooldownUntil?'cooldown':
      this.tracks.some(t=>t.state==='contact'&&t.armed)?'armed':
      this.tracks.some(t=>t.state==='contact')?'contact':
      this.tracks.find(t=>t.reason)?.reason||'idle';
    // A snap is a stronger intent than incidental palm separation. Discard the
    // old zoom baseline so its smoothing tail cannot immediately stop rotation.
    if(timestamp<this.scaleHoldUntil){
      this.pair=null;this.calibration=null;this.lastDistance=null;
      result.phase='snap-hold';return result;
    }
    if (d === null) {
      this.pair = null; this.calibration = null; this.lastDistance = null;
      return result;
    }
    if (this.lastDistance !== null && Math.abs(d - this.lastDistance) > s.maxDistanceStep) {
      this.rebase(); result.phase = 'unstable'; this.lastDistance = d;
      return result;
    }
    this.lastDistance = d;
    if (!this.pair) {
      result.phase = 'calibrating';
      if (!this.calibration || Math.abs(d / this.calibration.distance - 1) > s.stableRatio) {
        this.calibration = { since: timestamp, distance: d };
      } else if (timestamp - this.calibration.since >= s.calibrationMs) {
        this.pair = { distance: d, zoom, accepted: d, filtered: d };
        this.calibration = null;
        result.phase = 'tracking';
      }
      return result;
    }
    result.phase = 'tracking';
    const pair = this.pair;
    result.enlarging = d > pair.accepted * (1 + s.deadZone);
    if (Math.abs(d / pair.accepted - 1) > s.deadZone) pair.accepted = d;
    pair.filtered += (pair.accepted - pair.filtered) * (1 - Math.exp(-dt / s.smoothingMs));
    const desired = pair.zoom * pair.filtered / pair.distance;
    result.enlarging ||= desired > zoom + 0.00001;
    result.zoom = clamp(desired, s.minZoom, s.maxZoom);
    // Re-anchor at a limit to avoid accumulating invisible travel beyond it.
    if (desired < s.minZoom || desired > s.maxZoom) {
      this.pair = { distance: d, zoom: result.zoom, accepted: d, filtered: d };
    }
    return result;
  }

  updateSnap(track, hand, now) {
    const s = this.settings;
    if (track.state === 'idle') {
      if (hand.gap <= s.contact) {
        // Entering the camera already prepared for a snap is valid. A static
        // contact alone never fires: two observations and a fast release follow.
        Object.assign(track, { state: 'contact', start: now, lastContact: now, middle: hand.middle, gap: hand.gap, armed: false, frames:1, reason:'' });
      } else if (hand.indexGap < s.indexSeparation) {
        track.reason='index-pinch';
      }
      return false;
    }
    if (now - track.start > s.maxContactMs) { track.state = 'idle'; track.reason='retry'; return false; }
    if (hand.gap <= s.contact) {
      track.lastContact = now; track.middle = hand.middle; track.gap = hand.gap;
      track.frames++;
      track.armed = now - track.start >= s.contactMs && track.frames >= s.contactFrames;
      return false;
    }
    const releaseTime = now - track.lastContact;
    if (!track.armed || releaseTime > s.releaseMs) {
      track.state = 'idle'; track.reason=track.armed?'release-missed':'contact-missed'; return false;
    }
    if (hand.gap < s.release) return false;
    const speed = (hand.gap - track.gap) / (releaseTime / 1000);
    const travel = distance(hand.middle, track.middle) / hand.size;
    track.state = 'idle';
    const fired=speed >= s.releaseSpeed && travel >= s.middleTravel;
    track.reason=fired?'':'release-missed';
    return fired;
  }
}
