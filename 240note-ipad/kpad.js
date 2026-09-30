/* ============================================================
   数字のテンキー（iPad用）
   解答欄など数字を入れる欄では、iPadのキーボードを出さずにこのテンキーを出す。
   上の帯を引っぱると好きな場所に動かせる（縦向き・横向きごとに位置を覚える）
   ============================================================ */
(function(){
  const NUM = 'input[inputmode="numeric"], input[inputmode="decimal"]';
  let pad = null, cur = null, touching = 0;
  const ori = () => window.innerHeight > window.innerWidth ? "p" : "l";
  /* 数字の欄は、iPadのキーボードを出さない印を付ける */
  const mark = root => {
    if(!root || !root.querySelectorAll) return;
    if(root.matches && root.matches(NUM)){ root.dataset.kp = root.getAttribute("inputmode"); root.setAttribute("inputmode", "none"); }
    root.querySelectorAll(NUM).forEach(i => { i.dataset.kp = i.getAttribute("inputmode"); i.setAttribute("inputmode", "none"); });
  };
  mark(document);
  new MutationObserver(ms => ms.forEach(m => m.addedNodes.forEach(n => { if(n.nodeType === 1) mark(n); })))
    .observe(document.documentElement, {childList: true, subtree: true});
  const isKp = t => !!(t && t.matches && t.matches("input[data-kp]"));

  const KEYS = [["7"],["8"],["9"],["⌫","fn"],["4"],["5"],["6"],["C","fn"],["1"],["2"],["3"],["−","fn"],["0"],["00"],["000"],["次へ","next"]];
  function build(){
    pad = document.createElement("div");
    pad.id = "kpad"; pad.className = "kpad"; pad.hidden = true;
    pad.innerHTML = '<div class="kpbar"><span>テンキー</span><button type="button" data-k="prev">◀ 前へ</button><button type="button" data-k="close">閉じる</button></div>' +
      '<div class="kpkeys">' + KEYS.map(([k, c]) => '<button type="button" data-k="' + (c === "next" ? "next" : k) + '"' + (c ? ' class="' + (c === "next" ? "kpnext" : "fn") + '"' : '') + '>' + k + '</button>').join("") + '</div>';
    document.body.appendChild(pad);
    /* キーを押しても欄から外れないように、押した瞬間に処理する */
    pad.addEventListener("touchstart", e => { if(e.target.closest("button")) e.preventDefault(); }, {passive: false});
    pad.addEventListener("pointerdown", e => {
      const b = e.target.closest("button");
      touching = Date.now();
      if(!b) return;
      e.preventDefault();
      act(b.dataset.k);
    });
    /* 上の帯を引っぱって動かす */
    const bar = pad.querySelector(".kpbar");
    let dg = null;
    bar.addEventListener("pointerdown", e => {
      if(e.target.closest("button")) return;
      e.preventDefault(); try{ bar.setPointerCapture(e.pointerId); }catch(x){}
      dg = {x: e.clientX - pad.offsetLeft, y: e.clientY - pad.offsetTop};
    });
    bar.addEventListener("pointermove", e => { if(dg) put(e.clientX - dg.x, e.clientY - dg.y); });
    const end = () => { if(!dg) return; dg = null; try{ localStorage.setItem("kpad:" + ori(), JSON.stringify({x: pad.offsetLeft, y: pad.offsetTop})); }catch(x){} };
    bar.addEventListener("pointerup", end); bar.addEventListener("pointercancel", end);
  }
  function put(x, y){
    const W = window.innerWidth, H = window.innerHeight;
    pad.style.left = Math.max(0, Math.min(W - pad.offsetWidth, x)) + "px";
    pad.style.top = Math.max(0, Math.min(H - pad.offsetHeight, y)) + "px";
  }
  function place(){
    let p = null;
    try{ p = JSON.parse(localStorage.getItem("kpad:" + ori()) || "null"); }catch(e){}
    if(p) put(p.x, p.y);
    else put(window.innerWidth - pad.offsetWidth - 12, window.innerHeight - pad.offsetHeight - 12);
  }
  function show(){
    if(!pad) build();
    if(pad.hidden){ pad.hidden = false; place(); }
    /* 入れている欄がテンキーの下に隠れていたら、見える所まで動かす */
    requestAnimationFrame(() => {
      if(!cur) return;
      const a = cur.getBoundingClientRect(), b = pad.getBoundingClientRect();
      if(a.bottom > b.top && a.top < b.bottom && a.right > b.left && a.left < b.right) cur.scrollIntoView({block: "center", inline: "nearest"});
    });
  }
  function hide(){ if(pad) pad.hidden = true; }
  function move(dir){
    const box = cur.closest(".trainwin, .ws-pane, .padwin, .panel, main") || document;
    const all = [...box.querySelectorAll("input:not([disabled]):not([readonly]):not([type=hidden]), textarea")].filter(x => x.offsetParent !== null);
    const nx = all[all.indexOf(cur) + dir];
    if(nx){ nx.focus(); if(isKp(nx) && nx.select) try{ nx.setSelectionRange(nx.value.length, nx.value.length); }catch(x){} }
  }
  function act(k){
    if(k === "close"){ const c = cur; cur = null; hide(); if(c) c.blur(); return; }
    if(!cur) return;
    if(document.activeElement !== cur) cur.focus({preventScroll: true});
    if(k === "next" || k === "prev"){ move(k === "next" ? 1 : -1); return; }
    const num = cur.type === "number";
    let v = cur.value, s = num ? v.length : cur.selectionStart, e = num ? v.length : cur.selectionEnd;
    if(s == null || e == null){ s = e = v.length; }
    if(k === "C"){ v = ""; s = 0; }
    else if(k === "⌫"){ if(s === e && s > 0) s--; v = v.slice(0, s) + v.slice(e); }
    else if(k === "−"){ v = v.charAt(0) === "-" ? v.slice(1) : "-" + v; s = v.length; }
    else{ v = v.slice(0, s) + k + v.slice(e); s += k.length; }
    cur.value = v;
    if(!num) try{ cur.setSelectionRange(s, s); }catch(x){}
    cur.dispatchEvent(new Event("input", {bubbles: true}));
  }
  document.addEventListener("focusin", e => {
    const t = e.target;
    if(isKp(t)){ cur = t; t._kv = t.value; show(); return; }
    if(pad && pad.contains(t)) return;
    cur = null; hide();
  });
  document.addEventListener("focusout", e => {
    const t = e.target;
    if(!isKp(t)) return;
    if(t.value !== t._kv){ t._kv = t.value; t.dispatchEvent(new Event("change", {bubbles: true})); }
    setTimeout(() => {
      const a = document.activeElement;
      if(isKp(a)) return;
      if(cur === t && Date.now() - touching < 400){ t.focus({preventScroll: true}); return; }   /* テンキーを押したときに外れたら戻す */
      if(cur === t){ cur = null; hide(); }
    }, 60);
  });
  window.addEventListener("resize", () => { if(pad && !pad.hidden) place(); });
})();
