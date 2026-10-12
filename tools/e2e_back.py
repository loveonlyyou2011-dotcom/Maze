# 폰·태블릿 뒤로가기 점검 (헤드리스 크롬, 폰 390×750 / 태블릿 820×1180)
# - 실제 탭(WebDriver 클릭)으로 화면을 열고, 브라우저 뒤로가기(= 폰 뒤로 버튼)를 여러 번 연달아 눌러도
#   앱 밖으로 나가지 않고 한 화면씩 돌아오는지, 홈에서 한 번 더 누를 때만 앱을 나가는지
# - 폰 크롬은 "사용자가 화면을 누르지 않은 순간에 추가된 기록"을 뒤로가기 때 건너뛴다.
#   WebDriver의 뒤로가기는 이 건너뛰기를 하지 않아서, 대신 기록을 추가한 순간마다
#   화면을 한 번 누를 때마다 한 칸만 추가할 수 있다는 규칙을 흉내 내서, 모든 칸이 그 안에서 추가됐는지 본다.
#   (2026-10-12: 뒤로가기 처리 중에 기록을 다시 채우던 첫 구현이 이것 때문에 폰에서 두 번째에 앱을 나갔다)
# - 모든 화면의 "◀ 뒤로" 버튼이 같은 자리·같은 글자인지
# 실행: python tools/e2e_back.py
import pathlib, time, sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

ROOT = pathlib.Path(__file__).resolve().parent.parent
results = []
def check(name, ok, info=''):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('  ' + str(info) if info else ''), flush=True)

SPY = """
// 폰 크롬의 규칙 흉내: 화면을 한 번 누르면(신뢰된 입력) 기록을 한 칸 추가할 "권한"이 생기고,
// 기록을 추가하면 그 권한을 써 버린다. 권한 없이 추가된 칸은 뒤로가기 때 건너뛰어진다.
window.__pushes = [];
let __histAct = false;
['pointerdown','mousedown','keydown','touchend','pointerup'].forEach(t=>
  addEventListener(t, e=>{ if(e.isTrusted) __histAct = true; }, true));
const _push = history.pushState.bind(history);
history.pushState = function(st, t, u){
  window.__pushes.push({depth: st && st.kidsDepth, active: __histAct});
  __histAct = false;
  return _push(st, t, u);
};"""

def start(w, h):
    o = Options()
    for a in ['--headless=new', '--allow-file-access-from-files', '--autoplay-policy=no-user-gesture-required']: o.add_argument(a)
    o.add_experimental_option('mobileEmulation', {'deviceMetrics': {'width': w, 'height': h, 'pixelRatio': 1}})
    o.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    d = webdriver.Chrome(options=o)
    d.get('about:blank')  # 앱을 열기 전 페이지 (여기로 돌아가면 "앱 밖으로 나감")
    d.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': SPY})
    d.get((ROOT / 'index.html').as_uri()); time.sleep(1)
    return d

d = start(390, 750)
js = d.execute_script
def active(): return js("return document.querySelector('.screen.active') ? document.querySelector('.screen.active').id : null;")
def tap(css, text=''):
    """실제 탭: 보이는 요소 중 글자가 맞는 것을 WebDriver로 클릭 (사용자 활성화가 생긴다)"""
    for el in d.find_elements(By.CSS_SELECTOR, css):
        if el.is_displayed() and text in el.text:
            el.click(); time.sleep(0.5); return True
    return False
def back():
    d.back(); time.sleep(0.6)
def in_app(): return d.current_url.startswith('file:')

# 1) 단어놀이 5단계 깊이 → 뒤로가기 5번 연달아
tap('#gameHubGrid > *', '단어놀이'); tap('#wordLangGrid .card', '영어'); tap('#wordTopicGrid .card', '과일')
tap('#wordModeGrid > *', '카드')
tap('#btnFlashNext'); tap('#btnFlashNext')
path = [active()]
for _ in range(4):
    back(); path.append(active() if in_app() else 'OUT')
check('단어놀이: 뒤로가기 4번 연달아 한 칸씩', path == ['screen-word-card', 'screen-word-mode', 'screen-word-topic', 'screen-word-lang', 'screen-home'], path)
check('홈까지 와도 앱 안', in_app())
back()
check('홈에서 한 번 더 누르면 앱을 나감', not in_app(), d.current_url[:30])
d.forward(); time.sleep(1.2)
if not in_app(): d.get((ROOT / 'index.html').as_uri()); time.sleep(1)

# 2) 앱 버튼과 폰 뒤로가기를 섞어 쓰기
tap('#gameHubGrid > *', '동화'); tap('#storyGrid .story-card'); time.sleep(1)
tap('#btnStoryPlayBack')                 # 앱 버튼으로 목록
tap('#storyGrid .story-card'); time.sleep(1)
seq = []
for _ in range(2):
    back(); seq.append(active() if in_app() else 'OUT')
check('동화: 앱 버튼과 섞어 써도 재생 → 목록 → 홈', seq == ['screen-story-list', 'screen-home'], seq)
back()
check('홈에서 뒤로가기 한 번이면 앱을 나감(남은 기록 없음)', not in_app(), d.current_url[:30])
d.get((ROOT / 'index.html').as_uri()); time.sleep(1)

# 3) 미로: 테마 → 난이도 → 게임, 앱 안 뒤로 버튼으로 홈 → 다시 들어가 뒤로가기
tap('#gameHubGrid > *', '미로'); tap('#themeGrid > *'); tap('#levelList > *'); time.sleep(.5)
b = []
for _ in range(3):
    back(); b.append(active() if in_app() else 'OUT')
check('미로: 게임 → 난이도 → 테마 → 홈', b == ['screen-level', 'screen-theme', 'screen-home'], b)
tap('#gameHubGrid > *', '숫자'); tap('#mathOpGrid > *', '덧셈'); tap('#mathLevelList > *')
tap('#btnMathHome'); tap('#btnMathLevelBack'); tap('#btnMathOpBack')   # 앱 버튼으로 홈까지
check('앱 버튼으로 홈에 돌아옴', active() == 'screen-home')
tap('#gameHubGrid > *', '그림책'); tap('#bookGrid > *'); time.sleep(.5)
c = []
for _ in range(2):
    back(); c.append(active() if in_app() else 'OUT')
check('그림책: 읽기 → 목록 → 홈', c == ['screen-book-list', 'screen-home'], c)

pushes = js("return window.__pushes;")
inactive = [p for p in pushes if not p['active']]
check(f'기록 {len(pushes)}칸 모두 사용자가 누른 순간에 추가됨(폰 크롬이 건너뛰지 않음)', pushes and not inactive, inactive[:5])

# 4) 홈의 모든 놀이: 탭으로 최대 3단계 들어갔다가 폰 뒤로가기로 홈까지
PICK = ['.story-card', '.write-tile', '.thumb-card', '.color-subject-card', '#levelList > *', '#mathLevelList > *',
        '#funMenuGrid > *', '#writeLangGrid .card', '#wordLangGrid .card', '#wordTopicGrid .card', '#wordModeGrid > *',
        '#themeGrid > *', '#mathOpGrid > *', '#travelLangGrid > *', '.grid .card', '#bookGrid > *', '#shadowCatGrid > *']
hub = js("return [...document.querySelectorAll('#gameHubGrid > *')].map(e=>e.innerText.trim());")
bad = []
for label in hub:
    d.get((ROOT / 'index.html').as_uri()); time.sleep(.8)
    tap('#gameHubGrid > *', label)
    path = [active()]
    for _ in range(3):
        sc = active(); moved = False
        for sel in PICK:
            els = [e for e in d.find_elements(By.CSS_SELECTOR, '#' + sc + ' ' + sel) if e.is_displayed()]
            if els:
                els[0].click(); time.sleep(.7); moved = active() != sc
                break
        if not moved: break
        path.append(active())
    trail = []
    for _ in range(len(path)):
        back(); trail.append(active() if in_app() else 'OUT')
    if trail[-1] != 'screen-home' or 'OUT' in trail:
        bad.append((label, path, trail))
    allp = js("return window.__pushes.filter(p=>!p.active);")
    if allp: bad.append((label, 'skippable push', allp))
check(f'홈의 놀이 {len(hub)}개 모두: 깊이 들어갔다가 뒤로가기로 홈까지(앱 밖으로 안 나감)', not bad, bad[:3])

# 4-2) 문제를 끝까지 풀어 결과 화면이 저절로 뜬 뒤 뒤로가기 (결과 화면 기록도 탭 직후에 쌓이는지)
d.get((ROOT / 'index.html').as_uri()); time.sleep(.8)
tap('#gameHubGrid > *', '생각'); tap('#funMenuGrid > *', '규칙')
for _ in range(12):
    if active() != 'screen-pq': break
    prog = js("return document.getElementById('pqProgress').textContent;")
    ok = [e for e in d.find_elements(By.CSS_SELECTOR, '#pqOptions .pq-opt[data-ok="1"]') if e.is_displayed()]
    if ok: ok[0].click()
    t0 = time.time()
    while time.time() - t0 < 4 and active() == 'screen-pq' and js("return document.getElementById('pqProgress').textContent;") == prog: time.sleep(.15)
time.sleep(1)
r = [active()]
for _ in range(2):
    back(); r.append(active() if in_app() else 'OUT')
skp = js("return window.__pushes.filter(p=>!p.active);")
check('결과 화면 → 메뉴 → 홈 (뒤로가기)', r[0] == 'screen-fun-result' and r[-1] == 'screen-home' and 'OUT' not in r and not skp, (r, skp))

d.get((ROOT / 'index.html').as_uri()); time.sleep(.8)

# 5) 모든 화면의 뒤로 버튼 자리·글자
def collect(dd):
    return dd.execute_script("""
      const out = [];
      document.querySelectorAll('.screen').forEach(sc=>{
        if(sc.id==='screen-home') return;
        document.querySelectorAll('.screen').forEach(x=>x.classList.remove('active'));
        sc.classList.add('active');
        const b = sc.querySelector('.topbar button');
        if(!b){ out.push([sc.id, null]); return; }
        const r = b.getBoundingClientRect();
        out.push([sc.id, b.textContent.trim(), Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]);
      });
      return out;""")
for (w, h, name) in [(390, 750, '폰'), (820, 1180, '태블릿')]:
    dd = d if name == '폰' else start(w, h)
    rows = collect(dd)
    missing = [r[0] for r in rows if r[1] is None]
    labels = {r[1] for r in rows if r[1]}
    pos = {(r[2], r[3], r[4], r[5]) for r in rows if r[1]}
    check(f'{name}: 모든 화면에 왼쪽 위 뒤로 버튼', not missing, missing)
    check(f'{name}: 글자 모두 "◀ 뒤로"', labels == {'◀ 뒤로'}, labels)
    check(f'{name}: 모두 같은 자리·같은 크기', len(pos) == 1, sorted(pos)[:4])
    mute = dd.execute_script("const r=document.getElementById('btnMute').getBoundingClientRect(); return [Math.round(r.top), Math.round(r.height)];")
    top = next(iter(pos))[1] if pos else -1
    check(f'{name}: 뒤로 버튼과 🔊 버튼 높이가 같음', abs(top - mute[0]) <= 2, (top, mute))
    if name == '태블릿': dd.quit()

logs = [l for l in d.get_log('browser') if l['level'] == 'SEVERE' and 'vibrate' not in l['message']]
check('콘솔 오류 없음', not logs, [l['message'][:120] for l in logs[:3]])
d.quit()
print(f'\n{sum(results)}/{len(results)} 통과'); sys.exit(0 if all(results) else 1)
