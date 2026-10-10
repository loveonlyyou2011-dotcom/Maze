# 줄긋기 화면 크기 점검: 실제 폰 화면 크기를 흉내 내서 그림·글씨 크기, 화면 넘침, 5쌍 끝까지 잇기를 확인한다
# 실행: python tools/e2e_connect.py  (스크린샷은 tools/_out/e2e/connect_*.png)
import pathlib, time, sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'tools' / '_out' / 'e2e'; OUT.mkdir(parents=True, exist_ok=True)
results = []
def check(name, ok, info=''):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('  ' + str(info) if info else ''), flush=True)

def run(w, h, lang, topic, tag):
    o = Options()
    for a in ['--headless=new', '--allow-file-access-from-files']: o.add_argument(a)
    o.add_experimental_option('mobileEmulation', {'deviceMetrics': {'width': w, 'height': h, 'pixelRatio': 2}})
    d = webdriver.Chrome(options=o); d.get((ROOT / 'index.html').as_uri()); time.sleep(1)
    js = d.execute_script
    def click(sel, t): return js("const e=[...document.querySelectorAll(arguments[0])].filter(x=>x.offsetParent!==null&&x.textContent.includes(arguments[1]));if(!e.length)return false;e[0].click();return true;", sel, t)
    click('#gameHubGrid > *', '단어놀이'); time.sleep(.3); click('#wordLangGrid .card', lang); time.sleep(.3)
    click('#wordTopicGrid .card', topic); time.sleep(.3); click('#wordModeGrid > *', '줄긋기'); time.sleep(1.5)
    m = js("""const a=document.getElementById('connectArea').getBoundingClientRect();
      const L=document.querySelector('#connectLeftCol .connect-tile').getBoundingClientRect();
      const im=document.querySelector('#connectLeftCol img');
      const t=document.querySelector('#connectRightCol .connect-tile');
      return {vw:innerWidth, vh:innerHeight, bottom:Math.round(a.bottom), tile:[Math.round(L.width),Math.round(L.height)],
              img: im?[Math.round(im.getBoundingClientRect().width),Math.round(im.getBoundingClientRect().height)]:null,
              font:Math.max(...[...document.querySelectorAll('#connectRightCol .connect-tile')].map(x=>parseFloat(getComputedStyle(x).fontSize))),
              minFont:Math.min(...[...document.querySelectorAll('#connectRightCol .connect-tile')].map(x=>parseFloat(getComputedStyle(x).fontSize))),
              sw:document.documentElement.scrollWidth,
              n:document.querySelectorAll('#connectLeftCol .connect-tile').length,
              overflowWord:[...document.querySelectorAll('#connectRightCol .connect-tile')].some(x=>x.scrollWidth>x.clientWidth+1||x.scrollHeight>x.clientHeight+1)};""")
    d.save_screenshot(str(OUT / f'connect_{tag}.png'))
    check(f'{tag} 5쌍, 화면 안에 다 들어옴', m['n'] == 5 and m['bottom'] <= m['vh'] and m['sw'] <= m['vw'], m)
    check(f'{tag} 그림 칸 높이 72px 이상', m['tile'][1] >= 72, m['tile'])
    check(f'{tag} 글씨 크게(짧은 낱말 21px, 긴 낱말도 12px 이상(Pachycephalosaurus 같은 18글자는 360px 폰에서 12px)), 칸 밖으로 안 넘침', m['font'] >= 20 and m['minFont'] >= 12 and not m['overflowWord'], (m['font'], m['minFont']))
    # 손가락으로 5쌍 모두 잇기
    for _ in range(5):
        js("""const L=[...document.querySelectorAll('#connectLeftCol .connect-tile:not(.matched)')][0]; if(!L) return;
              const R=document.querySelector('#connectRightCol .connect-tile[data-pair-id="'+L.dataset.pairId+'"]');
              const a=L.getBoundingClientRect(), b=R.getBoundingClientRect();
              const ev=(el,type,x,y)=>el.dispatchEvent(new PointerEvent(type,{clientX:x,clientY:y,bubbles:true,pointerId:3}));
              ev(L,'pointerdown',a.left+a.width/2,a.top+a.height/2);
              ev(document,'pointermove',b.left+b.width/2,b.top+b.height/2);
              ev(document,'pointerup',b.left+b.width/2,b.top+b.height/2);""")
        time.sleep(0.2)
    time.sleep(1.5)
    active = js("return document.querySelector('.screen.active').id;")
    check(f'{tag} 5쌍 다 이으면 결과 화면', active == 'screen-word-result', active)
    d.quit()

run(390, 750, '한글', '공룡', '390x750')
run(360, 640, '한글', '과일', '360x640')
run(390, 750, '영어', '음식', 'emoji')
run(412, 860, '일본어', '동물', '412x860')
run(360, 640, '영어', '공룡', 'en_dino')
print(f'\n{sum(results)}/{len(results)} 통과'); sys.exit(0 if all(results) else 1)
