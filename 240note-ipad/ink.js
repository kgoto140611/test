/* ============================================================
   ペンで書く（iPad用。浮かぶ計算用紙・画面分割の白紙で共通）
   ・ペンで書き、指ではスクロールする。ペンをまだ一度も使っていない間だけは指でも書ける
   ・線の太さは一定。書いた分だけ足して描く（1本ごとに全部を描き直さない）
   ・消しゴムは、なぞった線を1本まるごと消す
   ・2本指でトントン → 1つ戻す
   ============================================================ */
const INK = {pen: false, hist: {}};
try{ INK.pen = localStorage.getItem("inkPen") === "1"; }catch(e){}
const INK_W = 2.2;
function inkTouchAction(){ return INK.pen ? "pan-x pan-y" : "none"; }
function inkSeePen(){
  if(INK.pen) return;
  INK.pen = true;
  try{ localStorage.setItem("inkPen", "1"); }catch(e){}
  document.querySelectorAll("canvas[data-ink]").forEach(c => { c.style.touchAction = inkTouchAction(); });
}
function inkHist(k){ return INK.hist[k] || (INK.hist[k] = []); }
/* 1つ戻す。書いた線を消す／消しゴムで消した線を戻す。記録がなければ（開き直したあとなど）最後の線を消す */
function inkUndo(k, list){
  const op = inkHist(k).pop();
  if(!op) return list.pop() !== undefined;
  if(op.add){ const i = list.lastIndexOf(op.add); if(i >= 0) list.splice(i, 1); return true; }
  if(op.del){ for(let j = op.del.length - 1; j >= 0; j--){ const [i, st] = op.del[j]; list.splice(Math.min(i, list.length), 0, st); } return true; }
  return false;
}
/* 点 (x, y) から r 以内を線が通っているか。座標は紙の幅を 1 とした値 */
function inkHit(st, x, y, r){
  const p = st[2];
  if(!p || !p.length) return false;
  if(p.length === 2) return Math.hypot(p[0] - x, p[1] - y) <= r;
  for(let k = 2; k < p.length; k += 2){
    const ax = p[k - 2], ay = p[k - 1], dx = p[k] - ax, dy = p[k + 1] - ay, L = dx * dx + dy * dy;
    const t = L ? Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / L)) : 0;
    if(Math.hypot(ax + t * dx - x, ay + t * dy - y) <= r) return true;
  }
  return false;
}
/* o = {key(), list(), save(), redraw(), undo(), tool(), style(): {color, width(lw)}, ctx(): {g, w}} */
function inkHook(cv, o){
  cv.dataset.ink = "1";
  cv.style.touchAction = inkTouchAction();
  const at = e => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.width]; };
  let cur = null, er = null, last = null, tap = null;
  const fingers = new Map();
  /* iPadのSafariは、ペンで引いてもページが動いてしまう。ペンで触れている間だけスクロールを止める */
  const stylus = e => { for(const t of e.changedTouches) if(t.touchType === "stylus") return true; return false; };
  cv.addEventListener("touchstart", e => { if(stylus(e)) e.preventDefault(); }, {passive: false});
  cv.addEventListener("touchmove", e => { if(stylus(e)) e.preventDefault(); }, {passive: false});
  const seg = (x0, y0, x1, y1) => {
    const c = o.ctx(); if(!c) return;
    const g = c.g, w = c.w, s = o.style();
    g.globalCompositeOperation = "source-over";
    g.strokeStyle = s.color; g.lineWidth = s.width(INK_W); g.lineCap = "round"; g.lineJoin = "round";
    g.beginPath(); g.moveTo(x0 * w, y0 * w); g.lineTo(x1 * w + (x0 === x1 && y0 === y1 ? 0.1 : 0), y1 * w); g.stroke();
  };
  const erase = (x, y) => {
    const list = o.list(), r = 12 / Math.max(1, cv.clientWidth);
    let hit = false;
    for(let i = list.length - 1; i >= 0; i--){
      const st = list[i];
      if(st[0]) continue;                       /* 前の消しゴム（白で塗る方式）の跡は残す */
      if(inkHit(st, x, y, r)){ er.del.push([i, st]); list.splice(i, 1); hit = true; }
    }
    if(hit) o.redraw();
  };
  const drop = () => {                          /* 2本目の指が来たら、1本目の指で書きかけた線は取り消す */
    if(cur){ const l = o.list(), i = l.lastIndexOf(cur); if(i >= 0) l.splice(i, 1); cur = null; o.redraw(); }
    if(er){ for(let j = er.del.length - 1; j >= 0; j--){ const [i, st] = er.del[j]; o.list().splice(i, 0, st); } er = null; o.redraw(); }
  };
  const finish = () => {
    if(cur){ inkHist(o.key()).push({add: cur}); cur = null; o.save(); }
    if(er){ if(er.del.length){ inkHist(o.key()).push({del: er.del}); o.save(); } er = null; }
  };
  cv.addEventListener("pointerdown", e => {
    if(e.pointerType === "pen") inkSeePen();
    if(e.pointerType === "touch"){
      const now = Date.now();
      fingers.set(e.pointerId, {x: e.clientX, y: e.clientY});
      if(fingers.size === 1) tap = {t: now, n: 1, moved: false};
      else if(fingers.size === 2 && tap && now - tap.t < 250){ tap.n = 2; drop(); return; }
      else{ tap = null; return; }
      if(INK.pen) return;                       /* ペンを使ったあとは、指はスクロールだけ */
    }
    if(e.button > 0) return;
    e.preventDefault(); try{ cv.setPointerCapture(e.pointerId); }catch(x){}
    const [x, y] = at(e);
    if(o.tool() === "eraser"){ er = {del: []}; erase(x, y); return; }
    cur = [0, INK_W, [Math.round(x * 1e4) / 1e4, Math.round(y * 1e4) / 1e4]]; o.list().push(cur); last = [x, y];
    seg(x, y, x, y);
  });
  cv.addEventListener("pointermove", e => {
    if(e.pointerType === "touch" && fingers.has(e.pointerId)){
      const f = fingers.get(e.pointerId);
      if(tap && Math.hypot(e.clientX - f.x, e.clientY - f.y) > 10) tap.moved = true;
      if(INK.pen || (tap && tap.n === 2)) return;
    }
    if(!cur && !er) return;
    const evs = e.getCoalescedEvents ? e.getCoalescedEvents() : null;
    (evs && evs.length ? evs : [e]).forEach(v => {
      const [x, y] = at(v);
      if(er){ erase(x, y); return; }
      if(Math.abs(x - last[0]) < 1e-4 && Math.abs(y - last[1]) < 1e-4) return;
      cur[2].push(Math.round(x * 1e4) / 1e4, Math.round(y * 1e4) / 1e4);
      seg(last[0], last[1], x, y); last = [x, y];
    });
  });
  const up = e => {
    if(e.pointerType === "touch" && fingers.has(e.pointerId)){
      fingers.delete(e.pointerId);
      if(tap && tap.n === 2){
        if(fingers.size === 0){ if(e.type === "pointerup" && !tap.moved && Date.now() - tap.t < 450) o.undo(); tap = null; }
        return;
      }
      if(e.type === "pointercancel"){ tap = null; drop(); return; }
    }
    finish();
  };
  cv.addEventListener("pointerup", up);
  cv.addEventListener("pointercancel", up);
}
