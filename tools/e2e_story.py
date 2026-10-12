# 🎬 동화 극장 자동 점검 (헤드리스 크롬, 폰 화면 390×750)
# - 22편 × 4개 언어 글이 다 있는지, 장면 사진·영상 176장면이 전부 열리는지, 종류별 보기
# - 장면 넘기기·영상 재생·언어 바꾸기·끝 화면·문제 풀기·스티커판
# - 소리를 끈 상태에서도 자막을 따라가며 저절로 다음 장면으로 넘어가는지
# 실행: python tools/e2e_story.py  (장면 비교표는 tools/_out/e2e/story_scenes_*.png)
import pathlib, time, sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image, ImageDraw, ImageFont

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

# 데이터
n = js("return document.querySelectorAll('#gameHubGrid > *').length;")
js("[...document.querySelectorAll('#gameHubGrid > *')].find(e=>e.textContent.includes('동화')).click();"); time.sleep(.8)
cards = js("return document.querySelectorAll('#storyGrid .story-card').length;")
check('동화 22편 목록', cards == 22, cards)
counts = []
for gi in range(1, 4):
    js("document.querySelectorAll('#storyGroupRow button')[arguments[0]].click();", gi); time.sleep(.3)
    counts.append(js("return document.querySelectorAll('#storyGrid .story-card').length;"))
check('종류별 보기(이솝·세계·한국)', counts == [9, 6, 7], counts)
js("document.querySelectorAll('#storyGroupRow button')[0].click();"); time.sleep(.3)
NST = cards
d.save_screenshot(str(OUT / 'story_list.png'))
# 목록 그림이 다 열렸는지
time.sleep(1)
broken = js("return [...document.querySelectorAll('#storyGrid img')].filter(i=>!(i.complete && i.naturalWidth)).map(i=>i.src);")
check('목록 표지 그림', not broken, broken[:2])

missing_text = []; missing_media = []; shots = []
for si in range(NST):
    js("document.querySelectorAll('#storyGrid .story-card')[arguments[0]].click();", si); time.sleep(1.2)
    title = js("return document.getElementById('storyTitle').textContent;")
    total = int(js("return document.getElementById('storyProgress').textContent;").split('/')[1])
    for k in range(total):
        time.sleep(1.1 if k else 0.2)
        txt = js("return document.getElementById('storyText').textContent.trim();")
        if not txt: missing_text.append((si, k))
        st = js("""const i=document.getElementById('storyImg'), v=document.getElementById('storyVideo');
                   return {img: i.complete && i.naturalWidth>0, video: v.style.display==='block', vready: v.readyState, vt: v.currentTime};""")
        if not st['img']: missing_media.append((si, k, 'img'))
        if st['video']:
            time.sleep(1.2)
            if js("return document.getElementById('storyVideo').readyState;") < 2: missing_media.append((si, k, 'video'))
        p = OUT / f'_st_{si}_{k}.png'; d.save_screenshot(str(p)); shots.append((si, k, p))
        if k < total - 1: js("document.getElementById('btnStoryNext').click();")
    js("document.getElementById('btnStoryNext').click();"); time.sleep(.6)
    end = js("return document.getElementById('storyEnd').classList.contains('show');")
    if not end: missing_media.append((si, 'end'))
    # 언어 4개 글 확인 (마지막 장면에서)
    for li in range(4):
        js("document.querySelectorAll('#storyPlayLangSeg button')[arguments[0]].click();", li); time.sleep(.3)
        if not js("return document.getElementById('storyText').textContent.trim();"): missing_text.append((si, 'lang', li))
    js("document.querySelectorAll('#storyPlayLangSeg button')[0].click();"); time.sleep(.3)
    js("document.getElementById('btnStoryPlayBack').click();"); time.sleep(.5)
check(f'{NST*8}장면 글이 모두 있음(4개 언어)', not missing_text, missing_text[:5])
check(f'{NST*8}장면 사진·영상이 모두 열림, {NST}편 모두 끝 화면', not missing_media, missing_media[:5])

# 영상 장면 재생 확인
js("document.querySelectorAll('#storyGrid .story-card')[0].click();"); time.sleep(1)
for _ in range(3): js("document.getElementById('btnStoryNext').click();"); time.sleep(.5)
time.sleep(2)
v = js("const v=document.getElementById('storyVideo'); return [v.style.display, v.paused, v.currentTime];")
check('영상 장면이 실제로 재생됨', v[0] == 'block' and not v[1] and v[2] > 0.3, v)
d.save_screenshot(str(OUT / 'story_video.png'))

# 감정 낭독 파일 재생 (토끼와 거북이는 네 언어 모두 낭독 파일이 있다)
js("document.getElementById('btnStoryPrev').click();"); time.sleep(.3)
for _ in range(3): js("document.getElementById('btnStoryPrev').click();"); time.sleep(.3)
time.sleep(2.5)
a = js("const a=window.__storyAudio; return [decodeURIComponent(a.currentSrc||''), a.paused, Math.round(a.currentTime*10)/10];")
check('감정 낭독 파일을 재생함(기기 음성 대신)', a[0].endswith('_ko.m4a') and not a[1] and a[2] > 0.5, a)
js("document.querySelectorAll('#storyPlayLangSeg button')[1].click();"); time.sleep(2.5)
a = js("const a=window.__storyAudio; return [decodeURIComponent(a.currentSrc||''), a.paused, Math.round(a.currentTime*10)/10];")
check('언어를 바꾸면 그 언어 낭독으로', a[0].endswith('_en.m4a') and not a[1], a)
js("document.querySelectorAll('#storyPlayLangSeg button')[0].click();"); time.sleep(.5)

# 소리 끈 상태에서 저절로 넘어가기 (자막 따라가기)
js("if(!document.getElementById('btnMute').textContent.includes('🔇')) document.getElementById('btnMute').click();")
js("document.getElementById('btnStoryPrev').click();"); time.sleep(.6)
before = js("return document.getElementById('storyProgress').textContent;")
time.sleep(2.0)
on = js("return document.querySelectorAll('#storyText .w.on, #storyText .w.done').length;")
check('소리 꺼도 자막이 낱말을 따라감', on > 0, on)
t0 = time.time()
while time.time() - t0 < 25 and js("return document.getElementById('storyProgress').textContent;") == before: time.sleep(.5)
after = js("return document.getElementById('storyProgress').textContent;")
check('다 읽으면 다음 장면으로 저절로 넘어감', after != before, f'{before} → {after} ({time.time()-t0:.1f}초)')
js("document.getElementById('btnStoryAuto').click();"); time.sleep(.3)
paused_txt = js("return document.getElementById('btnStoryAuto').textContent;")
check('멈춤 버튼', '자동' in paused_txt, paused_txt)
js("document.getElementById('btnMute').click();")

# 끝 화면 → 문제 풀기
for _ in range(8): js("document.getElementById('btnStoryNext').click();"); time.sleep(.3)
time.sleep(.6)
d.save_screenshot(str(OUT / 'story_end.png'))
js("document.getElementById('btnStoryQuiz').click();"); time.sleep(.8)
check('문제 화면', active() == 'screen-pq', active())
d.save_screenshot(str(OUT / 'story_quiz.png'))
for _ in range(2):
    js("const e=document.querySelector('#pqOptions .pq-opt[data-ok=\"1\"]'); if(e) e.click();"); time.sleep(1.6)
time.sleep(1)
check('문제를 다 풀면 결과 화면', active() == 'screen-fun-result', active())
js("document.getElementById('btnFunBack').click();"); time.sleep(.5)
star = js("return document.querySelector('#storyGrid .story-card .sc-star') ? document.querySelector('#storyGrid .story-card .sc-star').textContent : '';")
check('목록에 별 표시', '⭐' in star, star)
js("document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));document.getElementById('screen-home').classList.add('active');")
js("[...document.querySelectorAll('#gameHubGrid > *')].find(e=>e.textContent.includes('스티커')).click();"); time.sleep(.4)
check('스티커판에 동화', '토끼와 거북이' in js("return document.body.innerText;"))

logs = [l for l in d.get_log('browser') if l['level'] == 'SEVERE' and 'vibrate' not in l['message']]
check('콘솔 오류 없음', not logs, [l['message'][:120] for l in logs[:3]])
d.quit()

# 장면 비교표 (동화 2편씩 한 장)
font = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 16)
for part in range(0, NST, 2):
    group = [s for s in shots if part <= s[0] < part+2]
    W, H = 195, 375
    sheet = Image.new('RGB', (8*(W+4), 2*(H+24)), 'white')
    dr = ImageDraw.Draw(sheet)
    for si, k, p in group:
        im = Image.open(p).convert('RGB').resize((W, H))
        x, y = k*(W+4), (si-part)*(H+24)
        sheet.paste(im, (x, y+22)); dr.text((x+2, y+2), f'{si}-{k}', fill='#c00', font=font)
        p.unlink()
    sheet.save(OUT / f'story_scenes_{part//2+1}.png')
print(f'\n{sum(results)}/{len(results)} 통과'); sys.exit(0 if all(results) else 1)
