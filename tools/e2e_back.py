# 폰·태블릿 뒤로가기 점검 (헤드리스 크롬, 폰 390×750 / 태블릿 820×1180)
# - 브라우저 뒤로가기(driver.back = 폰의 뒤로 버튼)를 누르면 앱 밖으로 나가지 않고 한 화면씩 돌아오는지
# - 홈에서 누르는 뒤로가기만 앱을 나가는지
# - 모든 화면의 "◀ 뒤로" 버튼이 같은 자리·같은 글자인지
# 실행: python tools/e2e_back.py
import pathlib, time, sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = pathlib.Path(__file__).resolve().parent.parent
results = []
def check(name, ok, info=''):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('  ' + str(info) if info else ''), flush=True)

def start(w, h):
    o = Options()
    for a in ['--headless=new', '--allow-file-access-from-files', '--autoplay-policy=no-user-gesture-required']: o.add_argument(a)
    o.add_experimental_option('mobileEmulation', {'deviceMetrics': {'width': w, 'height': h, 'pixelRatio': 1}})
    o.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    d = webdriver.Chrome(options=o)
    d.get('about:blank')  # 앱을 열기 전 페이지 (여기로 돌아가면 "앱 밖으로 나감")
    d.get((ROOT / 'index.html').as_uri()); time.sleep(1)
    return d

d = start(390, 750)
js = d.execute_script
def active(): return js("return document.querySelector('.screen.active') ? document.querySelector('.screen.active').id : null;")
def click(sel, t=''):
    return js("const e=[...document.querySelectorAll(arguments[0])].filter(x=>x.offsetParent!==null&&x.textContent.includes(arguments[1]));if(!e.length)return false;e[0].click();return true;", sel, t)
def back():
    d.back(); time.sleep(0.6)

# 단어놀이 깊숙이 들어갔다가 폰 뒤로가기로 한 칸씩
click('#gameHubGrid > *', '단어놀이'); time.sleep(.3)
click('#wordLangGrid .card', '영어'); time.sleep(.3)
click('#wordTopicGrid .card', '과일'); time.sleep(.3)
click('#wordModeGrid > *', '퀴즈'); time.sleep(.6)
path = [active()]
for _ in range(4):
    back(); path.append(active())
check('단어놀이: 뒤로가기로 한 칸씩 돌아옴', path == ['screen-word-quiz', 'screen-word-mode', 'screen-word-topic', 'screen-word-lang', 'screen-home'], path)
check('홈까지 와도 앱 안에 있음', d.current_url.startswith('file:'), d.current_url[:40])

# 다시 들어가기 (덫이 다시 놓이는지)
click('#gameHubGrid > *', '동화'); time.sleep(.5)
js("document.querySelector('#storyGrid .story-card').click();"); time.sleep(1.5)
back(); a1 = active()
back(); a2 = active()
check('동화 극장: 재생 → 목록 → 홈', (a1, a2) == ('screen-story-list', 'screen-home'), (a1, a2))
check('동화 읽어주기 멈춤', js("return !window.speechSynthesis.speaking;"))

# 앱 안 "◀ 뒤로" 버튼으로 홈에 온 뒤 폰 뒤로가기 → 앱을 나감 (덫이 남아 있지 않아야 함)
click('#gameHubGrid > *', '숫자'); time.sleep(.3)
js("document.getElementById('btnMathOpBack').click();"); time.sleep(.6)
check('앱 버튼으로 홈에 돌아옴', active() == 'screen-home')
back()
check('홈에서 뒤로가기 한 번이면 앱을 나감', not d.current_url.startswith('file:'), d.current_url[:40])
d.get((ROOT / 'index.html').as_uri()); time.sleep(1)

# 결과 화면·게임 화면에서도
click('#gameHubGrid > *', '미로'); time.sleep(.3)
js("document.querySelector('#themeGrid > *').click();"); time.sleep(.3)
js("document.querySelector('#levelList > *').click();"); time.sleep(.8)
back(); b1 = active(); back(); b2 = active(); back(); b3 = active()
check('미로: 게임 → 난이도 → 테마 → 홈', (b1, b2, b3) == ('screen-level', 'screen-theme', 'screen-home'), (b1, b2, b3))

# 모든 화면의 뒤로 버튼 자리·글자
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
