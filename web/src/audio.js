/* Sound (phase 4), all synthesized with WebAudio — no recordings: wind (stronger high up and fast), the city's low
   hum (close to the streets), the waterfalls' roar (by the distance to the nearest fall), the seaplane's engine
   (flight mode, pitch with speed), birds by day and crickets at night (low over the island), a rush of water when
   flying through a fall and a thump on a crash. Starts on the first user gesture (browsers require one). */
import { clamp, lerp, smooth, inIsle } from "./world.js";
import { FALLS } from "./island.js";

export const SOUND = { ctx: null, on: true, master: null, rec: null, nodes: {}, nextBird: 0, nextCricket: 0, lastFalls: 0, lastCrash: null };

function noiseBuffer(ctx, sec = 4) {
  const b = ctx.createBuffer(1, ctx.sampleRate * sec, ctx.sampleRate), d = b.getChannelData(0);
  let last = 0;
  for (let i = 0; i < d.length; i++) { const w = Math.random() * 2 - 1; last = (last + 0.02 * w) / 1.02; d[i] = w * 0.5 + last * 3.5; }   // white with a little brown
  return b;
}
function loop(ctx, buf) { const s = ctx.createBufferSource(); s.buffer = buf; s.loop = true; s.loopStart = Math.random() * 2; s.start(); return s; }

export function startSound() {
  if (SOUND.ctx) { if (SOUND.ctx.state === "suspended") SOUND.ctx.resume(); return; }
  const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
  const ctx = new AC(), N = SOUND.nodes; SOUND.ctx = ctx;
  SOUND.master = ctx.createGain(); SOUND.master.gain.value = SOUND.on ? 0.9 : 0;
  SOUND.master.connect(ctx.destination);
  SOUND.rec = ctx.createMediaStreamDestination(); SOUND.master.connect(SOUND.rec);   // for the in-page recording
  const nb = noiseBuffer(ctx);
  const chain = (src, ...fx) => { let n = src; for (const f of fx) { n.connect(f); n = f; } const g = ctx.createGain(); g.gain.value = 0; n.connect(g); g.connect(SOUND.master); return g; };
  const filt = (type, f, q = 0.7) => { const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q; return b; };
  N.windF = filt("bandpass", 500, 0.5); N.wind = chain(loop(ctx, nb), N.windF);
  N.city = chain(loop(ctx, nb), filt("lowpass", 230, 0.4));
  N.waterF = filt("bandpass", 700, 0.35); N.water = chain(loop(ctx, nb), N.waterF, filt("lowpass", 2600));
  const saw = ctx.createOscillator(); saw.type = "sawtooth"; const sub = ctx.createOscillator(); sub.type = "square";
  N.engF = filt("lowpass", 600, 2); N.engSaw = saw; N.engSub = sub;
  const eg = ctx.createGain(); eg.gain.value = 0.5; saw.connect(N.engF); sub.connect(eg); eg.connect(N.engF);
  N.engine = chain(N.engF); saw.start(); sub.start();
}
export function setSoundOn(on) {
  SOUND.on = on;
  if (SOUND.master) SOUND.master.gain.setTargetAtTime(on ? 0.9 : 0, SOUND.ctx.currentTime, 0.2);
}

function chirp(ctx, t, f0, f1, dur, vol) {
  const o = ctx.createOscillator(), g = ctx.createGain();
  o.type = "sine"; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur);
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + dur * 0.2); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g); g.connect(SOUND.master); o.start(t); o.stop(t + dur + 0.05);
}
function burst(ctx, t, freq, dur, vol, type = "lowpass") {
  const s = ctx.createBufferSource(); s.buffer = noiseBuffer(ctx, Math.max(0.2, dur));
  const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq;
  const g = ctx.createGain(); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  s.connect(f); f.connect(g); g.connect(SOUND.master); s.start(t); s.stop(t + dur);
}

// per frame: eye (camera), flight state, light L (sky(tod))
export function updateSound(eye, FLY, L) {
  const ctx = SOUND.ctx; if (!ctx || ctx.state !== "running") return;
  const t = ctx.currentTime, N = SOUND.nodes, set = (g, v, tc = 0.25) => g.gain.setTargetAtTime(v, t, tc);
  const alt = eye[1], overIsle = inIsle(eye[0], eye[2], -200), low = 1 - smooth(60, 900, Math.abs(alt));
  const speed = FLY.on ? FLY.speed : 0;
  // wind: high up, fast, gusting
  const gust = 0.75 + 0.25 * Math.sin(t * 0.37) * Math.sin(t * 0.11 + 1);
  set(N.wind, clamp(0.05 + 0.18 * smooth(100, 2500, alt) + speed / 900, 0, 0.5) * gust);
  N.windF.frequency.setTargetAtTime(380 + speed * 3 + 200 * gust, t, 0.3);
  // the city
  set(N.city, overIsle ? 0.05 + 0.32 * low * (L.night > 0.5 ? 0.8 : 1) : 0.02);
  // waterfalls: nearest fall's distance
  let df = 1e9; for (const G of FALLS.groups) df = Math.min(df, Math.hypot(eye[0] - G.x, (eye[1] - (G.y - G.H * 0.4)) * 0.6, eye[2] - G.z) - G.w * 0.35);
  set(N.water, 0.42 * (1 - smooth(80, 2600, Math.max(df, 0))));
  // engine
  set(N.engine, FLY.on && !FLY.crash ? 0.07 + speed / 2600 : 0, 0.15);
  N.engSaw.frequency.setTargetAtTime(55 + speed * 0.42, t, 0.2); N.engSub.frequency.setTargetAtTime(27 + speed * 0.21, t, 0.2);
  N.engF.frequency.setTargetAtTime(380 + speed * 5, t, 0.2);
  // birds by day, crickets at night, low over the island
  if (overIsle && low > 0.3 && L.night < 0.4 && t > SOUND.nextBird) {
    SOUND.nextBird = t + 0.6 + Math.random() * 2.6;
    const n = 1 + (Math.random() * 3 | 0), f = 2600 + Math.random() * 2400;
    for (let k = 0; k < n; k++) chirp(ctx, t + k * 0.13, f, f * (0.7 + Math.random() * 0.6), 0.09 + Math.random() * 0.06, 0.05 * low);
  }
  if (overIsle && low > 0.4 && L.night > 0.6 && t > SOUND.nextCricket) {
    SOUND.nextCricket = t + 0.35 + Math.random() * 0.8;
    for (let k = 0; k < 3; k++) chirp(ctx, t + k * 0.05, 4400, 4300, 0.03, 0.02 * low);
  }
  // events
  if (FLY.falls > SOUND.lastFalls) burst(ctx, t, 1400, 1.4, 0.5, "bandpass");
  SOUND.lastFalls = FLY.falls;
  if (FLY.crash && SOUND.lastCrash !== FLY.crash) { burst(ctx, t, 260, 0.9, 0.9); chirp(ctx, t, 110, 38, 0.6, 0.5); }
  SOUND.lastCrash = FLY.crash;
}
