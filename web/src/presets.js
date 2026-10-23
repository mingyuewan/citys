/* Time-of-day presets (phase 4): four tuned moods in place of the old continuous clock — each a time of day plus
   the air (fog, the morning's mist layer, how full the clouds are) and the grade. Switching eases over 2.5 s. */
import { S } from "./state.js";
import { LOOK } from "./post.js";
import { lerp, smooth } from "./world.js";

export const PRESETS = {
  mist: { name: "晨雾", key: "1", tod: 6.95, fog: 1.5, mist: 1.0, clouds: 1.2, warm: [1.04, 1.0, 0.97], sat: 1.06, lift: [0.05, 0.04, 0.07], hint: "云海最厚，岛半隐半现" },
  day: { name: "白昼", key: "2", tod: 14.6, fog: 1.0, mist: 0.0, clouds: 1.0, warm: [1.03, 1.0, 0.96], sat: 1.16, lift: [0.035, 0.025, 0.06], hint: "晴空下的沙盘" },
  dusk: { name: "黄昏", key: "3", tod: 17.7, fog: 1.25, mist: 0.12, clouds: 1.0, warm: [1.07, 0.99, 0.9], sat: 1.22, lift: [0.04, 0.02, 0.06], hint: "金色侧光，华灯初上" },
  night: { name: "夜", key: "4", tod: 20.8, fog: 1.0, mist: 0.0, clouds: 0.9, warm: [1.0, 1.0, 1.02], sat: 1.15, lift: [0.01, 0.012, 0.03], hint: "灯光秀与孔明灯" },
};
export const ORDER = ["mist", "day", "dusk", "night"];

// the live values (eased), read by main.js each frame
export const MOOD = { id: "day", fog: 1, mist: 0, clouds: 1, from: null, to: null, t0: 0 };
const KEYS = ["fog", "mist", "clouds"];

// which preset fits a clock time (Shenzhen local hours)
export function presetForHour(h) { return h >= 5 && h < 8.5 ? "mist" : h >= 8.5 && h < 17 ? "day" : h >= 17 && h < 19 ? "dusk" : "night"; }

// setTod: the page's clock setter (ui.js), passed in to avoid an import cycle
export function setPreset(id, setTod, now, animate = true) {
  const P = PRESETS[id]; if (!P) return;
  MOOD.from = { fog: MOOD.fog, mist: MOOD.mist, clouds: MOOD.clouds, warm: LOOK.warm.slice(), sat: LOOK.sat, lift: LOOK.lift.slice() };
  MOOD.to = P; MOOD.id = id; MOOD.t0 = now; MOOD.ms = animate ? 2500 : 0;
  S.preset = id;
  setTod(P.tod, animate);
  if (!animate) stepPreset(now);
  for (const b of document.querySelectorAll("[data-preset]")) b.setAttribute("aria-pressed", String(b.dataset.preset === id));
}
export function stepPreset(now) {
  if (!MOOD.to) return;
  const k = MOOD.ms ? smooth(0, 1, (now - MOOD.t0) / MOOD.ms) : 1, F = MOOD.from, T = MOOD.to;
  for (const key of KEYS) MOOD[key] = lerp(F[key], T[key], k);
  for (let i = 0; i < 3; i++) { LOOK.warm[i] = lerp(F.warm[i], T.warm[i], k); LOOK.lift[i] = lerp(F.lift[i], T.lift[i], k); }
  LOOK.sat = lerp(F.sat, T.sat, k); LOOK.mist = MOOD.mist;
  if (k >= 1) MOOD.to = null;
}
