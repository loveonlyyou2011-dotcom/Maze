# 모든 화면을 폰 크기(390×750)로 차례로 찍어 비교표로 묶는다 (화면 검토용)
# 실행: python tools/shots_all.py  → tools/_out/shots/*.png, sheet_*.png
import pathlib, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'tools' / '_out' / 'shots'; OUT.mkdir(parents=True, exist_ok=True)
o = Options()
for a in ['--headless=new', '--allow-file-access-from-files', '--autoplay-policy=no-user-gesture-required']: o.add_argument(a)
o.add_experimental_option('mobileEmulation', {'deviceMetrics': {'width': 390, 'height': 750, 'pixelRatio': 1}})
d = webdriver.Chrome(options=o)
d.get((ROOT / 'index.html').as_uri()); time.sleep(1)
js = d.execute_script
shots = []
def shot(name, wait=0.6):
    time.sleep(wait); p = OUT / f'{len(shots):02d}_{name}.png'; d.save_screenshot(str(p)); shots.append((name, p))
def home():
    js("document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));document.getElementById('screen-home').classList.add('active');")
def click(sel, t=''):
    return js("const e=[...document.querySelectorAll(arguments[0])].filter(x=>x.offsetParent!==null&&x.textContent.includes(arguments[1]));if(!e.length)return false;e[0].click();return true;", sel, t)
def hub(t): home(); click('#gameHubGrid > *', t); time.sleep(0.3)

shot('home')
# 미로
hub('미로'); shot('maze_theme'); click('#themeGrid > *'); shot('maze_level'); click('#levelList > *'); shot('maze_game', 1)
# 숫자
hub('숫자'); shot('math_op'); click('#mathOpGrid > *'); shot('math_level'); click('#mathLevelList > *'); shot('math_game')
click('#mathChoiceArea > *'); shot('math_after_tap', 0.4)
js("document.getElementById('btnMathInputMode').click();"); shot('math_pad')
# 단어
hub('단어'); shot('word_lang'); click('#wordLangGrid .card', '한글'); shot('word_topic')
click('#wordTopicGrid .card', '동물'); shot('word_mode'); click('#wordModeGrid > *', '카드'); shot('word_card', 1)
hub('단어'); click('#wordLangGrid .card', '영어'); click('#wordTopicGrid .card', '과일'); click('#wordModeGrid > *', '퀴즈'); shot('word_quiz', 1)
hub('단어'); click('#wordLangGrid .card', '일본어'); click('#wordTopicGrid .card', '교통'); click('#wordModeGrid > *', '짝'); shot('word_match', 1)
js("const c=document.querySelectorAll('#screen-word-match .match-card, #wordMatchGrid > *'); if(c[0]) c[0].click(); if(c[1]) c[1].click();"); shot('word_match_flip', 0.5)
hub('단어'); click('#wordLangGrid .card', '중국어'); click('#wordTopicGrid .card', '바다'); click('#wordModeGrid > *', '줄긋기'); shot('word_connect', 1)
# 스티커·여행
hub('스티커'); shot('stickers')
hub('여행'); shot('travel_lang'); click('#travelLangGrid > *'); shot('travel_situation'); click('#screen-travel-situation .card, #screen-travel-situation .grid > *'); shot('travel_list')
# 색칠
hub('색칠'); shot('color_cat'); click('#colorCategoryGrid > *'); shot('color_items', 1); click('#colorItemsGrid > *'); shot('color_canvas', 1.5)
# 퍼즐
hub('퍼즐'); shot('puzzle_select', 1); click('#puzzleThumbGrid > *'); shot('puzzle_game', 1.5)
# 그림자
hub('그림자'); shot('shadow_select'); click('#shadowCatGrid > *'); shot('shadow_game', 3)
# 그림책
hub('그림책'); shot('book_list'); click('#bookGrid > *'); shot('book_read', 1.2)
# 따라쓰기
hub('따라쓰기'); shot('write_lang'); click('#writeLangGrid .card', '한글'); shot('write_list'); click('#writeGrid .write-tile'); shot('write_watch', 1.5)
# 출처
home(); js("document.getElementById('lnkCredits').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));"); shot('parent', 1.9)
d.quit()

# 3장씩 묶기
font = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 18)
for i in range(0, len(shots), 3):
    group = shots[i:i+3]
    ims = [Image.open(p).convert('RGB') for _, p in group]
    w, h = ims[0].size
    sheet = Image.new('RGB', (w*3 + 20, h + 30), 'white')
    dr = ImageDraw.Draw(sheet)
    for j, ((name, _), im) in enumerate(zip(group, ims)):
        sheet.paste(im, (j*(w+10), 30)); dr.text((j*(w+10)+4, 4), name, fill='#c00', font=font)
    sheet.save(OUT / f'sheet_{i//3+1:02d}.png')
print(len(shots), '화면')
