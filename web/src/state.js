/* Scene state shared by the modules; exposed as window.S for tools/record.py and tools/webgl_check.py. */
export const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
export const S = {
  osm: null, R: 3200, rise: 0, riseStart: 0, ready: false, showGen: true, showClouds: true, lmIdx: 0,
  tod: 15.5, todTarget: 15.5, orbit: false, sel: -1, tour: null, follow: null,
  cam: { tx: 0, tz: 0, yaw: -0.8, pitch: 1.35, dist: 9000 }, fly: null, labels: [], tallest: -1, wind: [0, 0],
  eyeNow: null, tgtNow: null,
};
