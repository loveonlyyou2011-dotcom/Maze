# 실제 사진 교체 전, 샘플 10개 항목의 Pexels 후보 사진을 받아 항목별로 한 줄씩 늘어놓은
# 비교표(컨택트 시트)를 만든다. 아이용 카드에는 "주인공 하나 + 깔끔한 배경" 사진이 좋아서,
# 설명(alt)에 사람·여러 개·장난감이 보이면 감점해 순서를 정한다.
# Pexels 키는 블로그 자동화와 같은 환경변수 PEXELS_API_KEY를 쓴다.
import os, io, json, time, pathlib, requests
from PIL import Image, ImageDraw, ImageFont

KEY = os.environ['PEXELS_API_KEY']
OUT = pathlib.Path(__file__).parent / '_out' / 'photo_sample'
OUT.mkdir(parents=True, exist_ok=True)

SAMPLE = [
    ('과일', '사과', 'apple', ['red apple isolated white background', 'red apple fruit']),
    ('동물', '사자', 'lion', ['lion portrait', 'lion animal']),
    ('교통수단', '소방차', 'fire truck', ['red fire truck', 'fire engine truck']),
    ('꽃과식물', '해바라기', 'sunflower', ['sunflower flower close up', 'sunflower']),
    ('곤충', '무당벌레', 'ladybug', ['ladybug macro', 'ladybird insect']),
    ('바다생물', '돌고래', 'dolphin', ['dolphin', 'dolphin jumping']),
    ('채소', '브로콜리', 'broccoli', ['broccoli isolated white background', 'fresh broccoli']),
    ('우주', '토성', 'saturn', ['planet saturn rings', 'saturn planet']),
    ('공룡', '티라노사우루스', 'dinosaur', ['tyrannosaurus rex', 't rex dinosaur']),
    ('학용품장난감', '연필', 'pencil', ['pencil isolated white background', 'yellow pencil']),
]

BAD = ['person', 'people', ' man ', 'woman', 'child', 'girl', 'boy', 'hand', 'holding', 'kid', 'family']
MULTI = ['bowl', 'basket', 'pile', 'crate', 'market', 'stall', 'assorted', 'variety', 'group of']
FAKE = ['toy', 'cartoon', 'illustration', 'drawing', 'figurine', 'plush', 'lego', 'sculpture', 'statue', 'painting']
CLEAN = ['isolated', 'white background', 'white backdrop', 'plain background', 'close-up', 'close up', 'macro']

def score(alt, noun):
    a = ' ' + (alt or '').lower() + ' '
    s = 3 * (noun.split()[0] in a)
    s += 2 * any(k in a for k in CLEAN)
    s -= 3 * any(k in a for k in BAD)
    s -= 2 * any(k in a for k in MULTI)
    s -= 2 * any(k in a for k in FAKE)
    return s

def search(q, n=10):
    r = requests.get('https://api.pexels.com/v1/search', headers={'Authorization': KEY},
                     params={'query': q, 'per_page': n}, timeout=30)
    r.raise_for_status()
    return r.json().get('photos', []), r.headers.get('X-Ratelimit-Remaining')

report = {}
for cat, ko, noun, queries in SAMPLE:
    seen, cands = set(), []
    remaining = None
    for q in queries:
        photos, remaining = search(q)
        for p in photos:
            if p['id'] in seen: continue
            seen.add(p['id'])
            cands.append({'id': p['id'], 'alt': p.get('alt') or '', 'photographer': p.get('photographer'),
                          'url': p['url'], 'medium': p['src']['medium'], 'large': p['src']['large'],
                          'w': p['width'], 'h': p['height'], 'query': q, 'score': score(p.get('alt'), noun)})
        time.sleep(1.0)
    cands.sort(key=lambda c: -c['score'])
    report[ko] = {'cat': cat, 'cands': cands[:6]}
    print(f'{cat}/{ko}: 후보 {len(cands)}장, 상위 점수 {[c["score"] for c in cands[:6]]} (남은 한도 {remaining})', flush=True)

(OUT / 'candidates.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')

TH = 150
font = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 20)
small = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 14)
rows = list(report.items())
for part in range(0, len(rows), 5):
    chunk = rows[part:part+5]
    sheet = Image.new('RGB', (130 + 6*(TH+10), len(chunk)*(TH+30) + 10), 'white')
    dr = ImageDraw.Draw(sheet)
    for ri, (ko, info) in enumerate(chunk):
        y = 10 + ri*(TH+30)
        dr.text((8, y+TH//2-12), ko, fill='black', font=font)
        for ci, c in enumerate(info['cands']):
            try:
                im = Image.open(io.BytesIO(requests.get(c['medium'], timeout=30).content)).convert('RGB')
            except Exception:
                continue
            im.thumbnail((TH, TH))
            x = 130 + ci*(TH+10)
            sheet.paste(im, (x + (TH-im.width)//2, y + (TH-im.height)//2))
            dr.text((x+2, y+TH+2), f'{ci+1} ({c["score"]:+d})', fill='#c00', font=small)
    sheet.save(OUT / f'sheet_{part//5+1}.jpg', quality=85)
print('시트 저장 완료')
