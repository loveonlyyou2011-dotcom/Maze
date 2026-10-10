# ✏️ 글자 따라쓰기 자동 점검 (헤드리스 크롬, 폰 화면 크기)
# - 모든 언어·단계의 글자가 획 데이터를 갖고 열리는지
# - 획을 손가락 대신 그어서(흔들림 포함) 보기→따라쓰기→혼자쓰기→보상까지 가는지
# - 반대 방향·순서 틀림을 제대로 잡아내는지, 별이 스티커판에 쌓이는지
# 실행: python tools/e2e_write.py  (스크린샷은 tools/_out/e2e/ 에 저장)
import pathlib, time, sys, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'tools' / '_out' / 'e2e'
OUT.mkdir(parents=True, exist_ok=True)

opt = Options()
for a in ['--headless=new', '--allow-file-access-from-files', '--autoplay-policy=no-user-gesture-required', '--window-size=390,844']:
    opt.add_argument(a)
opt.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
d = webdriver.Chrome(options=opt)
d.get((ROOT / 'index.html').as_uri())
time.sleep(1)

results = []
def check(name, ok, info=''):
    results.append((name, bool(ok)))
    print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info else ''), flush=True)

js = d.execute_script
js("""
window.__fire = function(type, x, y){
  const c = document.getElementById('writeCanvas');
  c.dispatchEvent(new PointerEvent(type, {clientX:x, clientY:y, pointerId:7, pointerType:'touch', bubbles:true, cancelable:true}));
};
// 0~100 좌표의 점 배열을 화면 좌표로 바꿔 촘촘하게 긋는다. jitter: 손떨림 크기(단위)
window.__draw = function(pts, jitter){
  const st = __writeTestState(), c = document.getElementById('writeCanvas'), r = c.getBoundingClientRect();
  const sc = r.width / st.S;
  const toC = p => [r.left + (st.pad + p[0]*st.k)*sc, r.top + (st.pad + p[1]*st.k)*sc];
  const dense = [pts[0]];
  for(let i=1;i<pts.length;i++){
    const a = pts[i-1], b = pts[i], n = Math.max(1, Math.ceil(Math.hypot(b[0]-a[0], b[1]-a[1])/2));
    for(let j=1;j<=n;j++) dense.push([a[0]+(b[0]-a[0])*j/n, a[1]+(b[1]-a[1])*j/n]);
  }
  const jit = dense.map((p,i)=> [p[0] + jitter*Math.sin(i*1.7), p[1] + jitter*Math.cos(i*1.3)]);
  const s = toC(jit[0]); __fire('pointerdown', s[0], s[1]);
  for(let i=1;i<jit.length;i++){ const q = toC(jit[i]); __fire('pointermove', q[0], q[1]); }
  const e = toC(jit[jit.length-1]); __fire('pointerup', e[0], e[1]);
};
""")

def state():
    return js('return window.__writeTestState && __writeTestState();')

def wait_ready(timeout=40):
    t = time.time()
    while time.time() - t < timeout:
        s = state()
        if s and s['step'] != 'watch' and not s['busy']:
            return s
        if s and s['finished']:
            return s
        time.sleep(0.15)
    return state()

def click_text(selector, text):
    return js("""
      const els = [...document.querySelectorAll(arguments[0])].filter(e => e.offsetParent !== null && e.textContent.includes(arguments[1]));
      if(!els.length) return false; els[0].click(); return true;""", selector, text)

def go_lang(label):
    js("document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));document.getElementById('screen-home').classList.add('active');")
    ok = click_text('#gameHubGrid .card, #gameHubGrid > *', '따라쓰기')
    ok2 = click_text('#writeLangGrid .card', label)
    return ok and ok2

def pick_level(i):
    js("document.querySelectorAll('#writeLevelSeg button')[arguments[0]].click();", i)

def write_all_strokes(jitter=3.0):
    """현재 단계의 모든 글자를 정답 획(흔들림 포함)으로 쓴다"""
    guard = 0
    while guard < 80:
        guard += 1
        s = wait_ready()
        if not s or s['finished'] or s['step'] == 'watch':
            return s
        step = s['step']
        if s['si'] >= len(s['strokes']):
            time.sleep(0.3); continue
        js("__draw(arguments[0], arguments[1]);", s['strokes'][s['si']], jitter)
        time.sleep(0.12)
        s2 = state()
        if s2 and s2['step'] != step:
            return s2
    return state()

def play_through(label, level_idx, text, shot=None):
    go_lang(label); pick_level(level_idx)
    if not click_text('#writeGrid .write-tile', text):
        check(f'{label} {text} 타일 열기', False); return
    time.sleep(0.6)
    if shot: d.save_screenshot(str(OUT / f'{shot}_watch.png'))
    s = wait_ready()
    check(f'{label} {text} 보기 끝나고 따라쓰기로', s and s['step'] == 'trace', s and s['step'])
    if shot:
        d.save_screenshot(str(OUT / f'{shot}_trace.png'))
    s = write_all_strokes()
    s = wait_ready()
    check(f'{label} {text} 따라쓰기 끝나고 혼자쓰기로', s and s['step'] == 'solo', s and s['step'])
    s = write_all_strokes(jitter=4.0)
    time.sleep(1.6)
    s = state()
    vis = js("return getComputedStyle(document.getElementById('writeReward')).display !== 'none';")
    word = js("return document.getElementById('writeRewardWord').textContent;")
    stars = js("return document.getElementById('writeRewardStars').textContent;")
    check(f'{label} {text} 보상 화면', s and s['finished'] and vis, f'{word} {stars} 실수 {s and s["mistakes"]}')
    if shot: d.save_screenshot(str(OUT / f'{shot}_reward.png'))

# 1) 모든 글자가 획 데이터를 갖고 열리는지
langs = js("return [...document.querySelectorAll('#gameHubGrid > *')].map(e=>e.textContent);")
check('홈에 따라쓰기 카드', any('따라쓰기' in t for t in langs))
total = 0; fails = []
for label in ['한글', '영어', '일본어', '중국어']:
    go_lang(label)
    nlev = js("return document.querySelectorAll('#writeLevelSeg button').length;")
    for li in range(nlev):
        pick_level(li)
        n = js("return document.querySelectorAll('#writeGrid .write-tile').length;")
        for i in range(n):
            js("document.querySelectorAll('#writeGrid .write-tile')[arguments[0]].click();", i)
            s = state()
            total += 1
            if not s or not s['strokes']:
                fails.append((label, li, i))
            js("document.getElementById('btnWritePlayBack').click();")
check(f'모든 글자 열림 ({total}자)', not fails and total > 190, fails[:5])
d.save_screenshot(str(OUT / 'list.png'))

# 2) 끝까지 써 보기 (자음, 받침 없는 낱말, 소문자 점, 히라가나, 상형문자 변신, 한자 낱말)
play_through('한글', 0, 'ㄱ', shot='ko_g')
play_through('한글', 3, '나무', shot='ko_word')
play_through('영어', 1, 'i')
play_through('영어', 0, 'S')
play_through('일본어', 0, 'あ', shot='ja_a')
play_through('중국어', 0, '山', shot='zh_san')
play_through('중국어', 1, '火山')

# 3) 반대 방향·순서 틀림 판정
go_lang('한글'); pick_level(0); click_text('#writeGrid .write-tile', 'ㅇ')
s = wait_ready()
js("__draw(arguments[0].slice().reverse(), 0);", s['strokes'][0])
time.sleep(0.2)
msg = js("return document.getElementById('writeMsg').textContent;")
check('ㅇ 반대 방향으로 돌리면 잡아냄', '반대' in msg and state()['si'] == 0, msg)
d.save_screenshot(str(OUT / 'reverse.png'))

go_lang('한글'); pick_level(0); click_text('#writeGrid .write-tile', 'ㅂ')
s = wait_ready()
js("__draw(arguments[0], 0);", s['strokes'][1])
time.sleep(0.2)
msg = js("return document.getElementById('writeMsg').textContent;")
check('ㅂ 2번 획을 먼저 그으면 순서 안내', '순서' in msg and state()['si'] == 0, msg)
js("__draw(arguments[0], 0);", s['strokes'][0])
time.sleep(0.2)
check('그다음 1번 획은 통과', state()['si'] == 1)

# 아무렇게나 그은 선은 통과하지 않아야 한다
js("__draw([[10,90],[90,10]], 0);")
time.sleep(0.2)
check('엉뚱한 선은 통과 못함', state()['si'] == 1, js("return document.getElementById('writeMsg').textContent;"))

# 4) 스티커판
js("document.getElementById('btnWritePlayBack').click();")
js("document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));document.getElementById('screen-home').classList.add('active');")
click_text('#gameHubGrid > *', '스티커')
time.sleep(0.4)
txt = js("return document.body.innerText;")
check('스티커판에 따라쓰기 칸', '✏️ 따라쓰기' in txt)
d.save_screenshot(str(OUT / 'sticker.png'))

logs = [l for l in d.get_log('browser') if l['level'] == 'SEVERE' and 'vibrate' not in l['message']]
check('콘솔 오류 없음', not logs, logs[:3])
d.quit()
ok = sum(1 for _, r in results if r)
print(f'\n{ok}/{len(results)} 통과')
sys.exit(0 if ok == len(results) else 1)
