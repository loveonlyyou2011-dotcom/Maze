# 유치원 기초 놀이 자동 점검 (헤드리스 크롬, 폰 화면 390×750)
# 듣고 고르기·수 세기·한글 블록·생각 놀이·마음·안전·그림책 질문·보호자 화면·쉬는 시간을
# 실제로 눌러서 끝까지 해 보고, 별이 스티커판에 모이는지 확인한다.
# 실행: python tools/e2e_edu.py  (스크린샷은 tools/_out/e2e/edu_*.png)
import pathlib, time, sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'tools' / '_out' / 'e2e'; OUT.mkdir(parents=True, exist_ok=True)
o = Options()
for a in ['--headless=new', '--allow-file-access-from-files', '--autoplay-policy=no-user-gesture-required']: o.add_argument(a)
o.add_experimental_option('mobileEmulation', {'deviceMetrics': {'width': 390, 'height': 750, 'pixelRatio': 1}})
o.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
d = webdriver.Chrome(options=o)
d.get((ROOT / 'index.html').as_uri()); time.sleep(1)
js = d.execute_script
results = []
def check(name, ok, info=''):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('  ' + str(info) if info else ''), flush=True)
def active(): return js("return document.querySelector('.screen.active').id;")
def home(): js("document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));document.getElementById('screen-home').classList.add('active');")
def click(sel, t=''):
    return js("const e=[...document.querySelectorAll(arguments[0])].filter(x=>x.offsetParent!==null&&x.textContent.includes(arguments[1]));if(!e.length)return false;e[0].click();return true;", sel, t)
def shot(name): d.save_screenshot(str(OUT / f'edu_{name}.png'))

def solve_pq(name, wrong_first=True, shot_name=None):
    """그림 퀴즈를 끝까지 푼다. 첫 문제는 일부러 한 번 틀려 본다."""
    t0 = time.time(); n = 0; shot_done = False
    while time.time() - t0 < 120:
        scr = active()
        if scr == 'screen-fun-result': break
        if scr != 'screen-pq': time.sleep(0.2); continue
        if shot_name and not shot_done: time.sleep(0.4); shot(shot_name); shot_done = True
        order = js("return [...document.querySelectorAll('#pqOptions .pq-opt')].some(e=>e.dataset.order!==undefined);")
        prog = js("return document.getElementById('pqProgress').textContent;")
        if wrong_first and n == 0:
            js("const w=[...document.querySelectorAll('#pqOptions .pq-opt')].find(e=>e.dataset.ok!=='1' && (e.dataset.order===undefined || e.dataset.order!=='0')); if(w) w.click();")
            time.sleep(0.45)
        if order:
            for k in range(6):
                js("const e=document.querySelector('#pqOptions .pq-opt[data-order=\"'+arguments[0]+'\"]'); if(e) e.click();", k); time.sleep(0.15)
        else:
            js("const e=document.querySelector('#pqOptions .pq-opt[data-ok=\"1\"]'); if(e) e.click();")
        n += 1
        # 다음 문제로 넘어갈 때까지 기다린다
        t1 = time.time()
        while time.time() - t1 < 5 and active() == 'screen-pq' and js("return document.getElementById('pqProgress').textContent;") == prog:
            time.sleep(0.15)
    time.sleep(0.6)
    ok = active() == 'screen-fun-result'
    stars = js("return document.getElementById('funResultStars').textContent;")
    check(f'{name} 끝까지 풀기', ok and n >= 2, f'{n}문제 · {stars}')
    return ok

# 홈
cards = js("return [...document.querySelectorAll('#gameHubGrid > *')].map(e=>e.textContent);")
check('홈에 새 카드 3개(한글 블록·생각 놀이·마음·안전)', all(any(x in c for c in cards) for x in ['한글 블록','생각 놀이','마음·안전']), len(cards))
shot('home')

# 1) 듣고 고르기
home(); click('#gameHubGrid > *', '단어'); time.sleep(.3); click('#wordLangGrid .card', '영어'); time.sleep(.3)
click('#wordTopicGrid .card', '동물'); time.sleep(.3)
check('단어놀이에 듣고 고르기', click('#wordModeGrid > *', '듣고 고르기'))
solve_pq('듣고 고르기', shot_name='listen')

# 2) 수 세기 5단계
home(); click('#gameHubGrid > *', '숫자'); time.sleep(.3)
check('숫자놀이에 수 세기 카드', click('#mathOpGrid > *', '수 세기')); time.sleep(.3)
shot('count_menu')
for i, lv in enumerate(['1~5', '1~10', '많을까', '덧셈', '뺄셈']):
    click('#funMenuGrid > *', lv); time.sleep(.3)
    solve_pq('수 세기 '+lv, shot_name='count_'+str(i))
    js("document.getElementById('btnFunBack').click();"); time.sleep(.3)

# 3) 한글 블록: 글자 만들기
home(); click('#gameHubGrid > *', '한글 블록'); time.sleep(.3)
click('#funMenuGrid > *', '글자 만들기'); time.sleep(.5)
shot('hangul_build')
CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'; JUNG = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
made = 0
for r in range(8):
    if active() != 'screen-hangul-build': break
    t = js("return document.getElementById('hbTarget').textContent;")
    c = ord(t) - 0xAC00; cho = CHO[c // 588]; jung = JUNG[(c % 588) // 28]
    if r == 0:  # 일부러 틀린 모음 먼저
        js("const b=[...document.querySelectorAll('#hbJungRow .hb-key')].find(x=>x.textContent!==arguments[0]); b.click();", jung)
        js("[...document.querySelectorAll('#hbChoRow .hb-key')].find(x=>x.textContent===arguments[0]).click();", cho); time.sleep(.6)
    js("[...document.querySelectorAll('#hbChoRow .hb-key')].find(x=>x.textContent===arguments[0]).click();", cho)
    js("[...document.querySelectorAll('#hbJungRow .hb-key')].find(x=>x.textContent===arguments[0]).click();", jung)
    res = js("return document.getElementById('hbResult').textContent;")
    if res == t: made += 1
    if r == 1: time.sleep(.3); shot('hangul_build_ok')
    t1 = time.time()
    while time.time() - t1 < 4 and active() == 'screen-hangul-build' and js("return document.getElementById('hbTarget').textContent;") == t and r < 7:
        time.sleep(.15)
time.sleep(3)
check('글자 만들기 8글자', made == 8 and active() == 'screen-fun-result', f'{made}글자 · {active()}')
js("document.getElementById('btnFunBack').click();"); time.sleep(.3)
click('#funMenuGrid > *', '첫소리'); time.sleep(.3)
solve_pq('첫소리 찾기', shot_name='first_sound')

# 4) 생각 놀이
home(); click('#gameHubGrid > *', '생각 놀이'); time.sleep(.3); shot('think_menu')
for i, label in enumerate(['과일', '동물', '곤충', '교통수단']):
    js("document.querySelectorAll('#funMenuGrid > *')[arguments[0]].click();", i); time.sleep(.3)
    solve_pq('분류하기 '+label, shot_name='classify' if i == 0 else None)
    js("document.getElementById('btnFunBack').click();"); time.sleep(.3)
click('#funMenuGrid > *', '규칙'); time.sleep(.3); solve_pq('규칙 찾기', shot_name='pattern')
js("document.getElementById('btnFunBack').click();"); time.sleep(.3)
click('#funMenuGrid > *', '순서'); time.sleep(.3); solve_pq('순서 맞추기', shot_name='order')

# 5) 마음·안전
home(); click('#gameHubGrid > *', '마음'); time.sleep(.3)
click('#funMenuGrid > *', '기분'); time.sleep(.3); solve_pq('기분 카드', shot_name='feeling')
js("document.getElementById('btnFunBack').click();"); time.sleep(.3)
click('#funMenuGrid > *', '안전'); time.sleep(.3); solve_pq('안전 놀이', shot_name='safety')

# 6) 그림책: 낱말 색칠 → 끝까지 넘기고 질문
home(); click('#gameHubGrid > *', '그림책'); time.sleep(.3)
js("document.querySelector('#bookGrid > *').click();"); time.sleep(.8)
words = js("return document.querySelectorAll('#bookTextMain .w').length;")
check('그림책 문장이 낱말 단위로 나뉨(읽는 낱말 색칠용)', words >= 3, words)
check('따라 읽기 버튼', js("return !!document.getElementById('btnBookRec').offsetParent;"))
for _ in range(5): js("document.getElementById('btnBookNext').click();"); time.sleep(.3)
check('마지막 장 버튼이 문제 풀기', '문제' in js("return document.getElementById('btnBookNext').textContent;"))
shot('book_last')
js("document.getElementById('btnBookNext').click();"); time.sleep(.5)
solve_pq('그림책 질문', shot_name='book_quiz')

# 7) 보호자 화면·쉬는 시간
home(); js("document.getElementById('lnkCredits').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));"); time.sleep(1.8)
check('보호자 메뉴 열림(꾹 누르기)', active() == 'screen-parent', active())
bars = js("return document.querySelectorAll('#parentWeek .day').length;")
segs = js("return document.querySelectorAll('#parentRestSeg button').length;")
check('주간 막대 7개, 알림 설정 5개', bars == 7 and segs == 5, (bars, segs))
js("[...document.querySelectorAll('#parentRestSeg button')].find(b=>b.textContent==='15분').click();")
check('알림 15분 저장', js("return localStorage.getItem('fingerMazeRestMinutes');") == '15')
shot('parent')
js("window.__eduTest.showRest();"); time.sleep(.5)
check('쉬는 시간 화면', js("return document.getElementById('restOverlay').classList.contains('show');"))
shot('rest')
js("document.getElementById('btnRestDone').click();")

# 8) 스티커판
home(); click('#gameHubGrid > *', '스티커'); time.sleep(.4)
txt = js("return document.body.innerText;")
check('스티커판에 배움 놀이·듣고 고르기', '🌱 배움 놀이' in txt and '듣고 고르기' in txt)
shot('stickers')

logs = [l for l in d.get_log('browser') if l['level'] == 'SEVERE' and 'vibrate' not in l['message']]
check('콘솔 오류 없음', not logs, logs[:3])
d.quit()
print(f'\n{sum(results)}/{len(results)} 통과'); sys.exit(0 if all(results) else 1)
