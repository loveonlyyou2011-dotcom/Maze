# 실제 사진 교체 점검 (헤드리스 크롬, 폰 화면 크기)
# - 퍼즐 그림 목록의 사진·선그림이 전부 깨지지 않고 열리는지 (235장)
# - 사진이 있는 항목은 photos/, 없는 항목은 coloring/ 선그림을 쓰는지
# - 그림자 찾기는 선그림을 쓰는지, 퍼즐·그림책이 사진으로 열리는지, 출처 화면에 작가가 다 나오는지
# 실행: python tools/e2e_photos.py  (스크린샷은 tools/_out/e2e/ 에 저장)
import pathlib, time, sys
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
js = d.execute_script
results = []
def check(name, ok, info=''):
    results.append(bool(ok))
    print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info else ''), flush=True)

def home():
    js("document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));document.getElementById('screen-home').classList.add('active');")
def click_text(sel, text):
    return js("""const e=[...document.querySelectorAll(arguments[0])].filter(x=>x.offsetParent!==null&&x.textContent.includes(arguments[1]));
                 if(!e.length) return false; e[0].click(); return true;""", sel, text)

# 1) 퍼즐 목록으로 모든 카테고리 그림 열어 보기
home(); click_text('#gameHubGrid > *', '퍼즐'); time.sleep(0.5)
ncat = js("return document.querySelectorAll('#puzzleCatRow > *').length;")
total = photos = 0; broken = []
for i in range(ncat):
    js("document.querySelectorAll('#puzzleCatRow > *')[arguments[0]].click();", i)
    t = time.time()
    while time.time() - t < 20:
        st = js("""const im=[...document.querySelectorAll('#puzzleThumbGrid img')];
                   im.forEach(x=>x.loading='eager');
                   return im.map(x=>[x.complete, x.naturalWidth, decodeURIComponent(x.getAttribute('src'))]);""")
        if st and all(s[0] for s in st): break
        time.sleep(0.3)
    for done, w, src in st:
        total += 1
        photos += src.startswith('photos/')
        if not w: broken.append(src)
    if i == 0: d.save_screenshot(str(OUT / 'photo_puzzle_list.png'))
check(f'퍼즐 목록 그림 {total}장 모두 열림', total >= 230 and not broken, broken[:5])
check('사진으로 바뀐 그림 수', photos >= 220, f'사진 {photos}장 / 선그림 {total-photos}장')

# 2) 퍼즐 한 판 열기 → 사진으로 시작하는지
js("document.querySelectorAll('#puzzleCatRow > *')[0].click();"); time.sleep(0.5)
js("document.querySelector('#puzzleThumbGrid .thumb-card, #puzzleThumbGrid > *').click();"); time.sleep(2)
n = js("return document.querySelectorAll('#puzzleBoard .puzzle-piece').length;")
check('사진 퍼즐 조각 만들어짐', n >= 12, n)
d.save_screenshot(str(OUT / 'photo_puzzle_game.png'))

# 3) 그림자 찾기는 선그림
home(); click_text('#gameHubGrid > *', '그림자'); time.sleep(0.4)
js("document.querySelector('#shadowCatGrid > *').click();"); time.sleep(3)
srcs = js("return [...document.querySelectorAll('#shadowOptions img')].map(x=>decodeURIComponent(x.getAttribute('src')));")
check('그림자 찾기는 선그림 사용', srcs and all('/coloring/' in s or s.startswith('coloring/') for s in srcs), srcs[:2])

# 4) 그림책
home(); click_text('#gameHubGrid > *', '그림책'); time.sleep(0.4)
js("document.querySelector('#bookGrid > *').click();"); time.sleep(1.2)
b = js("const x=document.getElementById('bookImg'); return [decodeURIComponent(x.getAttribute('src')), x.naturalWidth];")
check('그림책 사진 표시', b[0].startswith('photos/') and b[1] > 0, b)
d.save_screenshot(str(OUT / 'photo_book.png'))

# 5) 단어 카드 (과일)
home(); click_text('#gameHubGrid > *', '단어놀이'); time.sleep(0.3)
click_text('#wordLangGrid .card', '한글'); time.sleep(0.3)
click_text('#screen-word-topic .card', '과일'); time.sleep(0.3)
click_text('#screen-word-mode .card, #screen-word-mode button', '카드'); time.sleep(1.2)
d.save_screenshot(str(OUT / 'photo_wordcard.png'))
wimg = js("const x=document.querySelector('.screen.active img'); return x ? [decodeURIComponent(x.getAttribute('src')), x.naturalWidth] : null;")
check('단어 카드 사진 표시', wimg and wimg[0].startswith('photos/') and wimg[1] > 0, wimg)

# 6) 출처 화면
home(); js("document.getElementById('lnkCredits').click();"); time.sleep(0.4)
n = js("return document.querySelectorAll('#creditsList li').length;")
badge = js("return document.querySelector('.pexels-badge').href;")
check('출처 화면에 사진작가 목록', n == photos, f'{n}명 / 사진 {photos}장')
check('Pexels 링크 표시', 'pexels.com' in badge)
d.save_screenshot(str(OUT / 'photo_credits.png'))

logs = [l for l in d.get_log('browser') if l['level'] == 'SEVERE' and 'vibrate' not in l['message']]
check('콘솔 오류 없음', not logs, logs[:3])
d.quit()
print(f'\n{sum(results)}/{len(results)} 통과')
sys.exit(0 if all(results) else 1)
