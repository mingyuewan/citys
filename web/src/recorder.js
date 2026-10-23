/* In-page recording (phase 4): the canvas (the composed picture, without the HTML labels) plus the synthesized
   sound, via MediaRecorder; MP4 where the browser can, WebM otherwise; saved as a download when stopped (or after
   two minutes). */
import { SOUND } from "./audio.js";

const $ = s => document.querySelector(s);
export const REC = { mr: null, chunks: [], t0: 0, timer: 0, mime: "" };

function pickMime() {
  if (!window.MediaRecorder) return null;
  for (const m of ["video/mp4;codecs=avc1", "video/mp4", "video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"]) if (MediaRecorder.isTypeSupported(m)) return m;
  return "";
}
export function recordingSupported() { return pickMime() !== null && !!HTMLCanvasElement.prototype.captureStream; }

export function toggleRecording(canvas) { if (REC.mr) stopRecording(); else startRecording(canvas); }
export function startRecording(canvas) {
  const mime = pickMime(); if (mime === null) return false;
  const stream = canvas.captureStream(30);
  if (SOUND.rec) for (const tr of SOUND.rec.stream.getAudioTracks()) stream.addTrack(tr);
  const mr = new MediaRecorder(stream, mime ? { mimeType: mime, videoBitsPerSecond: 12e6 } : undefined);
  REC.mr = mr; REC.chunks = []; REC.t0 = Date.now(); REC.mime = mr.mimeType || mime || "video/webm";
  mr.ondataavailable = e => { if (e.data && e.data.size) REC.chunks.push(e.data); };
  mr.onstop = save;
  mr.start(1000);
  $("#bRec").setAttribute("aria-pressed", "true"); document.body.classList.add("recording");
  REC.timer = setInterval(tick, 250); tick();
  return true;
}
export function stopRecording() { if (REC.mr && REC.mr.state !== "inactive") REC.mr.stop(); }
function tick() {
  const s = Math.floor((Date.now() - REC.t0) / 1000);
  $("#bRec").firstChild.textContent = `● ${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")} `;
  if (s >= 120) stopRecording();
}
function save() {
  clearInterval(REC.timer);
  const ext = REC.mime.includes("mp4") ? "mp4" : "webm";
  const blob = new Blob(REC.chunks, { type: REC.mime.split(";")[0] });
  const a = document.createElement("a"), d = new Date(), pad = n => String(n).padStart(2, "0");
  a.href = URL.createObjectURL(blob);
  a.download = `深圳湾空中之岛-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}.${ext}`;
  document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000);
  REC.mr = null; REC.chunks = [];
  $("#bRec").setAttribute("aria-pressed", "false"); $("#bRec").firstChild.textContent = "录屏 "; document.body.classList.remove("recording");
}
