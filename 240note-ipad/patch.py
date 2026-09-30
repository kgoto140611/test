import re
s = open('orig.html', encoding='utf-8').read()
def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:90])
    s = s.replace(a, b)
def cut(start, end, new, keep_end=True):
    """start..end の間（start を含む。end は keep_end なら残す）を new に置き換える"""
    global s
    i = s.index(start); assert s.count(start) == 1, start[:80]
    j = s.index(end, i)
    s = s[:i] + new + (s[j:] if keep_end else s[j+len(end):])

# ---- 1. 共通のペン書き・テンキー ----
ink = open('ink.js', encoding='utf-8').read()
rep('function padDraw(){', ink + 'function padDraw(){')
kp = open('kpad.js', encoding='utf-8').read()
kcss = open('kpad.css', encoding='utf-8').read()

# ---- 2. 浮かぶ計算用紙：くっきり（画面の細かさに合わせる） ----
rep('''  cv.style.height = h + "px";
  cv.width = w; cv.height = h;
  const g = cv.getContext("2d");
  g.clearRect(0, 0, w, h);''', '''  cv.style.height = h + "px";
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  if(cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)){ cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  cv._dpr = dpr;
  const g = cv.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);''')

# ---- 3. 浮かぶ計算用紙：ペンで書く部分を共通のものに ----
cut('  let cur = null;\n  const at = e => {\n    const r = cv.getBoundingClientRect();',
    '  win.querySelector("#padimg").addEventListener("load", padDraw);',
    '''  inkHook(cv, {
    key: () => padKey(PAD.book, PAD.page),
    list: () => padLoad(padKey(PAD.book, PAD.page)),
    save: () => padSave(padKey(PAD.book, PAD.page)),
    redraw: () => padDraw(),
    undo: () => { const k = padKey(PAD.book, PAD.page); if(inkUndo(k, padLoad(k))){ padSave(k); padDraw(); } },
    tool: () => PAD.tool,
    style: () => ({color: "#16324A", width: lw => lw}),
    ctx: () => { const g = cv.getContext("2d"), d = cv._dpr || 1; g.setTransform(d, 0, 0, d, 0, 0); return {g, w: cv.clientWidth}; }
  });
''')
rep('''    const ink = padLoad(padKey(PAD.book, PAD.page));
    ink.pop(); padSave(padKey(PAD.book, PAD.page)); padDraw(); return;''',
    '''    const k = padKey(PAD.book, PAD.page);
    if(inkUndo(k, padLoad(k))){ padSave(k); padDraw(); } return;''')
rep('''    PADINK[padKey(PAD.book, PAD.page)] = [];''', '''    PADINK[padKey(PAD.book, PAD.page)] = []; INK.hist[padKey(PAD.book, PAD.page)] = [];''')

# ---- 4. 画面分割の白紙：同じくペンは共通のものに。「動かす」はなくす（指でそのまま動かせる） ----
rep('<button type="button" data-t="hand">✋ 動かす</button>', '')
rep('''    box.querySelectorAll("canvas").forEach(cv => { cv.style.touchAction = (WSPAD.tool === "hand" || WSPAD.pen) ? "pan-y" : "none"; });\n''', '')
cut('      let cur = null;\n      const at = e => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.width]; };',
    '      cv.addEventListener("pointerup", end); cv.addEventListener("pointercancel", end);\n',
    '''      inkHook(cv, {
        key: () => key + ":" + i,
        list: () => (data.s[i] = data.s[i] || []),
        save, redraw: () => draw(cv, i),
        undo: () => { if(inkUndo(key + ":" + i, data.s[i] || [])){ save(); draw(cv, i); } },
        tool: () => WSPAD.tool,
        style: () => ({color: ink(), width: lw => lw * (cv.clientWidth / 600)}),
        ctx: () => { const g = cv.getContext("2d"), w = cv.clientWidth, d = cv.width / Math.max(1, w); g.setTransform(d, 0, 0, d, 0, 0); return {g, w}; }
      });
''', keep_end=False)
rep('''    if(b.dataset.a === "undo"){ (data.s[i] || []).pop(); save(); draw(vis.querySelector("canvas"), i); return; }''',
    '''    if(b.dataset.a === "undo"){ if(inkUndo(key + ":" + i, data.s[i] || [])){ save(); draw(vis.querySelector("canvas"), i); } return; }''')
rep('''data.s[i] = []; save(); draw(vis.querySelector("canvas"), i); }''', '''data.s[i] = []; INK.hist[key + ":" + i] = []; save(); draw(vis.querySelector("canvas"), i); }''')

# ---- 5. 浮かぶ窓：縦向き・横向きに合わせた初めの位置。向きごとに位置を覚える。向きを変えたら収め直す ----
geo = '''/* iPadの縦向き（と狭い画面）は、窓を画面の下半分に出して、開いた方でないほうをたたむ */
function NARROW(){ return window.innerWidth < 700 || window.innerHeight > window.innerWidth; }
function winOri(){ return window.innerHeight > window.innerWidth ? "p" : "l"; }
function winFits(p){ const W = window.innerWidth, H = window.innerHeight; return !!(p && p.x < W - 80 && p.y < H - 60 && p.w <= W + 4 && p.h <= H + 4 && p.x + p.w > 60); }
/* 初めの位置。横向きは右側に上下に並べる（上が採点、下が計算用紙）。左側に問題のページが残る */
function padGeo(){
  const W = window.innerWidth, H = window.innerHeight;
  if(NARROW()){ const h = Math.max(260, Math.round(H * 0.5)); return {w: W - 12, h, x: 6, y: Math.max(0, H - h - 6)}; }
  const w = Math.round(W * 0.44), y = Math.round(64 + (H - 72) * 0.5 + 8);
  return {w, h: H - y - 8, x: W - w - 8, y};
}
function trainGeo(){
  const W = window.innerWidth, H = window.innerHeight;
  if(NARROW()){ const h = Math.round(H * 0.5); return {w: W - 12, h, x: 6, y: H - h - 6}; }
  const w = Math.round(W * 0.44);
  return {w, h: Math.round((H - 72) * 0.5), x: W - w - 8, y: 64};
}
let WINORI = winOri();
function winFit(){
  const o = winOri(), turned = o !== WINORI;
  WINORI = o;
  const W = window.innerWidth, H = window.innerHeight;
  [["padwin", padGeo], ["trainwin", trainGeo]].forEach(([id, geo]) => {
    const w = document.getElementById(id); if(!w) return;
    if(w.dataset.full === "1"){ w.style.left = "8px"; w.style.top = "8px"; w.style.width = (W - 16) + "px"; w.style.height = (H - 16) + "px"; return; }
    const min = w.dataset.min === "1";
    let g = null;
    if(turned){ try{ g = JSON.parse(localStorage.getItem(id + ":" + o) || "null"); }catch(e){} if(!winFits(g)) g = geo(); }
    else g = {x: parseInt(w.style.left) || 0, y: parseInt(w.style.top) || 0, w: w.offsetWidth, h: min ? (parseInt(w.dataset.h) || 300) : w.offsetHeight};
    g.w = Math.min(g.w, W - 8); g.h = Math.min(g.h, H - 8);
    g.x = Math.max(4 - g.w + 120, Math.min(W - 120, g.x)); g.y = Math.max(0, Math.min(H - 40, g.y));
    w.style.left = g.x + "px"; w.style.top = g.y + "px"; w.style.width = g.w + "px";
    if(min) w.dataset.h = g.h + "px"; else w.style.height = g.h + "px";
  });
  padDraw();
  readerAvoid();
}
window.addEventListener("resize", () => { clearTimeout(winFit._t); winFit._t = setTimeout(winFit, 150); });
'''
rep('function padClose(){', geo + 'function padClose(){')
rep('''  try{ pos = JSON.parse(localStorage.getItem("padwin") || "null"); }catch(e){}''',
    '''  try{ pos = JSON.parse(localStorage.getItem("padwin:" + winOri()) || "null"); }catch(e){}''')
rep('''  const small = W < 700;''', '''  const small = NARROW();''')
cut('  const w = (!small && fits) ? pos : small\n', '  const win = document.createElement("div");\n  win.id = "padwin";',
    '  const w = fits ? pos : padGeo();\n')
rep('''  const keep = () => { try{ localStorage.setItem("padwin", JSON.stringify(''', '''  const keep = () => { try{ localStorage.setItem("padwin:" + winOri(), JSON.stringify(''')
rep('''  try{ pos = JSON.parse(localStorage.getItem("trainwin") || "null"); }catch(e){}''',
    '''  try{ pos = JSON.parse(localStorage.getItem("trainwin:" + winOri()) || "null"); }catch(e){}''')
cut('  const g = pos || (W < 700\n', '  if(W < 700) padFold(true);', '  const g = pos || trainGeo();\n')
rep('  if(W < 700) padFold(true);', '  if(NARROW()) padFold(true);')
rep('''  const keep = () => { try{ localStorage.setItem("trainwin", JSON.stringify(''', '''  const keep = () => { try{ localStorage.setItem("trainwin:" + winOri(), JSON.stringify(''')
rep('''  if(window.innerWidth < 700){
    /* 狭い画面では、たたんだ帯もひらいた窓も画面の下にそろえる''', '''  if(NARROW()){
    /* 狭い画面では、たたんだ帯もひらいた窓も画面の下にそろえる''')
rep('''if(window.innerWidth < 700){ trainFold(true); toast(''', '''if(NARROW()){ trainFold(true); toast(''')
rep('''    if(!fold && window.innerWidth < 700) padFold(true);''', '''    if(!fold && NARROW()) padFold(true);''')
rep('''    if(on && window.innerWidth < 700) trainFold(true);''', '''    if(on && NARROW()) trainFold(true);''')
# 右下のつまみを大きく
rep('.padgrip{position:absolute; right:0; bottom:0; width:22px; height:22px;', '.padgrip{position:absolute; right:0; bottom:0; width:36px; height:36px;')

# ---- 6. 画面分割：縦向きは上下を基本に。並べ方は向きごとに覚える。境目は2回タップで半分ずつ ----
rep("""  function save() { try { localStorage.setItem('ws:' + O.key, JSON.stringify(""", """  function wsOri() { return window.innerHeight > window.innerWidth ? ':p' : ''; }
  function save() { try { localStorage.setItem('ws:' + O.key + wsOri(), JSON.stringify(""")
rep("""    try { return JSON.parse(localStorage.getItem('ws:' + O.key) || 'null'); } catch (e) { return null; }""",
    """    try { return JSON.parse(localStorage.getItem('ws:' + O.key + wsOri()) || 'null'); } catch (e) { return null; }""")
rep("""preset(opts.def || 'l2'))""", """preset(wsOri() ? ({ l2: 't2', lr: 'tb' }[opts.def || 'l2'] || opts.def) : (opts.def || 'l2')))""")
rep("""    dv.title = '引っぱると大きさが変わります（ダブルクリックで半分ずつ）';""", """    dv.title = '引っぱると大きさが変わります（2回タップで半分ずつ）';""")
rep("""    dv.addEventListener('dblclick', function () { n.r = 0.5; setR(); save(); });""",
    """    var tapT = 0, tapD = null;
    dv.addEventListener('pointerdown', function (e) { tapD = { x: e.clientX, y: e.clientY }; });
    dv.addEventListener('pointerup', function (e) {
      if (!tapD) return;
      var mv = Math.abs(e.clientX - tapD.x) + Math.abs(e.clientY - tapD.y); tapD = null;
      if (mv > 8) { tapT = 0; return; }
      var now = Date.now();
      if (now - tapT < 350) { tapT = 0; n.r = 0.5; setR(); save(); } else tapT = now;
    });""")

# ---- 7. キーボード・マウス用の操作をなくす ----
cut('  ins.forEach(i => i.addEventListener("keydown", ev => {', '/* ---------- 進み具合 ---------- */', '}\n\n', keep_end=True)
# 上の cut で afterMod の閉じ括弧も消えるので、直後を確かめる
cut('/* Esc で1つ前に戻る。', 'document.addEventListener("change", ev => {', '')
rep('''document.addEventListener("keydown", e => { if(e.key === "Escape") acHide(); });\n''', '')
cut('  /* ホイール・トラックパッドはひと続きの操作で1ページ */', '  /* 画像をタップしたら上の帯とスライダーを出し入れする', '')
cut('  strip.addEventListener("wheel", e => {\n    if(!e.ctrlKey && !e.metaKey && PVZOOM <= 1.02) return;', '  const hint = box.querySelector("#rhint");', '\n')

# ---- 8. マウスを乗せたときの色は、マウスのある機器だけ（iPadでタップ後に色が残らない） ----
def split_sel(p):
    out, d, cur = [], 0, ''
    for ch in p:
        if ch in '([': d += 1
        if ch in ')]': d -= 1
        if ch == ',' and d == 0: out.append(cur); cur = ''
        else: cur += ch
    out.append(cur); return out
def css(t):
    o, i, n = [], 0, len(t)
    start = 0
    while i < n:
        if t.startswith('/*', i):
            j = t.index('*/', i) + 2; i = j; continue
        ch = t[i]
        if ch == '{':
            pre = t[start:i]
            # 先頭のコメント・空白は分けて残す
            m = re.match(r'((?:\s|/\*.*?\*/)*)(.*)$', pre, re.S)
            lead, sel = m.group(1), m.group(2)
            d, j = 1, i + 1
            while d:
                if t.startswith('/*', j): j = t.index('*/', j) + 2; continue
                if t[j] == '{': d += 1
                elif t[j] == '}': d -= 1
                j += 1
            body = t[i+1:j-1]
            if sel.lstrip().startswith('@'):
                inner = css(body) if re.match(r'\s*@(media|supports)', sel) else body
                o.append(pre + '{' + inner + '}')
            elif ':hover' in sel:
                parts = split_sel(sel)
                hv = [p for p in parts if ':hover' in p]; nh = [p for p in parts if ':hover' not in p]
                r = lead
                if nh: r += ','.join(nh).strip() + '{' + body + '}'
                r += '@media (hover:hover){' + ','.join(hv).strip() + '{' + body + '}}'
                o.append(r)
            else:
                o.append(pre + '{' + body + '}')
            i = j; start = j; continue
        i += 1
    o.append(t[start:])
    return ''.join(o)
blocks = list(re.finditer(r'(<style[^>]*>)(.*?)(</style>)', s, re.S))
for m in reversed(blocks):
    s = s[:m.start(2)] + css(m.group(2)) + s[m.end(2):]
# テンキー・つまみのスタイルは最初の自前スタイルの最後に足す
last = list(re.finditer(r'</style>', s))
k = [m for m in last][1] if len(last) > 1 else last[0]
s = s[:k.start()] + kcss + s[k.start():]

# ---- 9. テンキーは本体のスクリプトの最後に ----
idx = s.rindex('</script>')
s = s[:idx] + '\n' + kp + '\n' + s[idx:]
open('new.html', 'w', encoding='utf-8').write(s)
print('ok', len(s))
