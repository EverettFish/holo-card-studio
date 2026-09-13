import { clamp, SETTINGS } from './gesture-engine.js';
const TAU = Math.PI * 2;
export const normalizeAngle = a => Math.atan2(Math.sin(a), Math.cos(a));

export class CardMotion {
  constructor() { this.reset(); }
  reset() {
    this.x = this.targetX = 0.025; this.y = this.targetY = -0.13;
    this.zoom = this.displayZoom = 1; this.mode = 'paused'; this.time = 0;
  }
  get back() { return Math.cos(this.y) < 0; }
  setZoom(value) {
    const next = clamp(value, SETTINGS.minZoom, SETTINGS.maxZoom);
    if (value > this.zoom + 0.00001) this.faceFront();
    this.zoom = next;
  }
  holdZoom() { this.zoom = this.displayZoom; }
  faceFront() {
    this.mode = 'paused';
    this.targetX = 0.025;
    this.targetY = this.y + normalizeAngle(-0.13 - this.y);
  }
  pause() {
    this.mode = 'paused';
    this.targetX = this.x; this.targetY = this.y = normalizeAngle(this.y);
  }
  toggleSpin() {
    if (this.mode === 'spin') this.pause();
    else { this.pause(); this.mode = 'spin'; }
  }
  toggleSway() {
    if (this.mode === 'sway') this.pause();
    else { this.pause(); this.mode = 'sway'; this.targetY = 0; }
  }
  flip() {
    const next = this.back ? 0 : Math.PI;
    this.pause(); this.targetY = this.y + normalizeAngle(next - this.y); this.targetX = 0;
  }
  nudge(dx, dy) {
    this.mode = 'paused';
    this.targetX = clamp(this.targetX + dx, -0.43, 0.43);
    this.targetY += dy;
  }
  tick(dt, reduced = false) {
    this.time += dt;
    // Paint zoom at display cadence even when hand inference runs more slowly.
    this.displayZoom += (this.zoom - this.displayZoom) * (reduced ? 1 : 1 - Math.exp(-dt * 20));
    if (this.mode === 'spin') {
      // Direct angular integration makes pause exact, with no easing tail.
      this.y = this.targetY = normalizeAngle(this.y + dt * TAU / 12);
      this.targetX = 0;
    } else if (this.mode === 'sway') {
      this.targetY = Math.sin(this.time * 0.65) * 0.38;
      this.targetX = Math.sin(this.time * 0.85) * 0.12;
    }
    const ease = reduced ? 1 : 1 - Math.exp(-dt * 8);
    this.x += (this.targetX - this.x) * ease;
    if (this.mode !== 'spin') this.y += (this.targetY - this.y) * ease;
  }
}
