# 그림 카드용 실제 사진 받기 (Pexels). 공룡은 실물 사진이 있을 수 없어서 공원·박물관의 실물 크기 모형이나
# 사실적인 피규어 사진으로 대신한다 (같은 Pexels라 출처 표시 방식이 다른 사진과 같다).
#
#   python photo_fetch.py search   항목마다 후보 검색 (결과는 _out/photo_cache/ 에 보관 → 끊겨도 이어서)
#   python photo_fetch.py build    고른 사진을 photos/ 로 줄여 저장 + 확인용 비교표 + 출처 목록
#
# 고르는 순서: photo_picks.json 에 적은 사진 id(사람이 눈으로 보고 바꾼 것) > 설명(alt) 점수 1등.
# Pexels 기본 한도는 시간당 200회이고 블로그 자동화와 같은 키를 쓰므로, 검색은 25초에 한 번만 한다
# (212항목 ≒ 90분). 사진 파일 자체를 받는 것은 한도에 들어가지 않는다.
import os, io, sys, json, time, pathlib, requests
from PIL import Image, ImageDraw, ImageFont

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
OUT = TOOLS / '_out'
CACHE = OUT / 'photo_cache'
PHOTOS = ROOT / 'photos'
PICKS = TOOLS / 'photo_picks.json'
CACHE.mkdir(parents=True, exist_ok=True)

NAMES = json.loads((TOOLS / 'photo_names.json').read_text(encoding='utf-8'))  # '카테고리/항목' → 영어 이름 (index.html 단어 데이터에서 뽑음)

HINT = {'과일': '{} fruit', '채소': '{} vegetable', '동물': '{} animal', '곤충': '{} insect', '바다생물': '{} ocean',
        '꽃과식물': '{}', '교통수단': '{}', '우주': '{}', '학용품장난감': '{}', '공룡': '{} dinosaur'}
# 영어 이름만으로는 엉뚱한 사진이 나오는 항목 (cricket=크리켓 경기, 배=pear/boat 등)
QUERY = {
    '동물/강아지': 'cute puppy dog', '교통수단/배': 'ship at sea', '교통수단/로켓': 'rocket launch', '교통수단/지하철': 'subway train', '교통수단/레미콘': 'concrete mixer truck',
    '교통수단/유조선': 'oil tanker ship', '교통수단/기차': 'train railway', '교통수단/자동차': 'red car', '교통수단/트럭': 'truck on road',
    '우주/별': 'starry night sky', '우주/금성': 'planet venus', '우주/수성': 'planet mercury', '우주/목성': 'planet jupiter', '우주/화성': 'planet mars',
    '우주/천왕성': 'uranus planet', '우주/해왕성': 'neptune planet', '우주/지구': 'earth from space', '우주/달': 'full moon', '우주/태양': 'sun in sky',
    '우주/외계인': 'alien figure', '우주/로켓': 'rocket launch', '우주/우주선': 'space shuttle', '우주/우주정거장': 'international space station',
    '우주/인공위성': 'satellite in space', '우주/운석': 'meteorite rock', '우주/혜성': 'comet night sky', '우주/은하': 'galaxy', '우주/별자리': 'constellation night sky',
    '바다생물/물고기': 'tropical fish underwater', '바다생물/조개': 'clam shell', '바다생물/소라': 'conch shell', '바다생물/산호': 'coral reef',
    '바다생물/물개': 'seal animal', '바다생물/오징어': 'squid', '바다생물/상어': 'shark underwater', '바다생물/펭귄': 'penguin',
    '곤충/귀뚜라미': 'cricket insect', '곤충/파리': 'housefly macro', '곤충/벌': 'honey bee', '곤충/나방': 'moth insect', '곤충/반딧불이': 'firefly insect',
    '곤충/물방개': 'water beetle', '곤충/집게벌레': 'earwig', '곤충/꿀벌집': 'beehive honeycomb', '곤충/달팽이': 'snail', '곤충/거미': 'spider web spider',
    '꽃과식물/무궁화': 'hibiscus syriacus', '꽃과식물/나무': 'big tree field', '꽃과식물/새싹': 'seedling sprout', '꽃과식물/이끼': 'moss',
    '꽃과식물/화분': 'potted plant', '꽃과식물/잎사귀': 'green leaf', '꽃과식물/코스모스': 'cosmos flower', '꽃과식물/데이지': 'daisy flower',
    '꽃과식물/국화': 'chrysanthemum flower', '꽃과식물/연꽃': 'lotus flower', '꽃과식물/진달래': 'azalea flower', '꽃과식물/클로버': 'clover leaf',
    '과일/배': 'asian pear fruit', '과일/감': 'persimmon', '과일/귤': 'tangerine', '채소/무': 'daikon radish', '채소/배추': 'napa cabbage',
    '채소/파': 'green onion', '채소/연근': 'lotus root', '채소/우엉': 'burdock root', '채소/콩': 'soybeans', '채소/고추': 'red chili pepper',
    '채소/호박': 'pumpkin', '채소/버섯': 'mushroom',
    '공룡/티라노사우루스': 'tyrannosaurus rex dinosaur', '공룡/공룡 알': 'dinosaur egg', '공룡/프테로닥틸루스': 'pterodactyl',
    '공룡/프테라노돈': 'pteranodon', '공룡/엘라스모사우루스': 'plesiosaur',
    '학용품장난감/가방': 'school backpack', '학용품장난감/가위': 'scissors', '학용품장난감/곰인형': 'teddy bear', '학용품장난감/공': 'colorful ball',
    '학용품장난감/그림책': 'children picture book', '학용품장난감/기차장난감': 'wooden toy train', '학용품장난감/로봇장난감': 'toy robot',
    '학용품장난감/블록': 'toy building blocks', '학용품장난감/비눗방울': 'soap bubbles', '학용품장난감/색종이': 'colored paper',
    '학용품장난감/시계': 'wall clock', '학용품장난감/연': 'kite in sky', '학용품장난감/연필': 'pencil', '학용품장난감/인형': 'doll toy',
    '학용품장난감/자': 'ruler', '학용품장난감/자동차장난감': 'toy car', '학용품장난감/지우개': 'eraser', '학용품장난감/책': 'stack of books',
    '학용품장난감/크레파스': 'crayons', '학용품장난감/팽이': 'spinning top toy', '학용품장난감/퍼즐': 'jigsaw puzzle', '학용품장난감/풀': 'glue stick',
    '학용품장난감/풍선': 'colorful party balloons', '학용품장난감/필통': 'pencil case',
}
# 장난감·외계인처럼 원래 만든 물건인 항목은 'toy' 같은 말이 들어가도 감점하지 않는다
TOY_OK = {'학용품장난감', '공룡'}
TOY_ITEMS = {'우주/외계인', '우주/UFO'}

BAD = ['person', 'people', ' man ', 'woman', 'child', 'girl', 'boy', 'hand', 'holding', 'kid', 'family', 'tourist']
MULTI = ['bowl', 'basket', 'pile', 'crate', 'market', 'stall', 'assorted', 'variety', 'group of', 'heap']
FAKE = ['toy', 'cartoon', 'illustration', 'drawing', 'figurine', 'plush', 'lego', 'sculpture', 'statue', 'painting', 'mural']
CLEAN = ['isolated', 'white background', 'white backdrop', 'plain background', 'close-up', 'close up', 'macro', 'single']

def score(alt, key, words):
    a = ' ' + (alt or '').lower() + ' '
    s = 3 * any(w in a for w in words)
    s += 2 * any(k in a for k in CLEAN)
    s -= 3 * any(k in a for k in BAD)
    s -= 2 * any(k in a for k in MULTI)
    if key.split('/')[0] not in TOY_OK and key not in TOY_ITEMS:
        s -= 2 * any(k in a for k in FAKE)
    return s

def cache_path(key):
    return CACHE / (key.replace('/', '__') + '.json')

def search():
    key_env = os.environ['PEXELS_API_KEY']
    todo = [k for k in NAMES if not cache_path(k).exists()]
    print(f'검색할 항목 {len(todo)}개', flush=True)
    for n, key in enumerate(todo, 1):
        cat = key.split('/')[0]
        q = QUERY.get(key) or HINT[cat].format(NAMES[key].lower())
        r = requests.get('https://api.pexels.com/v1/search', headers={'Authorization': key_env},
                         params={'query': q, 'per_page': 20}, timeout=30)
        if r.status_code == 429:
            print('한도 초과 → 10분 쉼', flush=True); time.sleep(600); continue
        r.raise_for_status()
        photos = [{'id': p['id'], 'alt': p.get('alt') or '', 'photographer': p.get('photographer'),
                   'url': p['url'], 'large': p['src']['large'], 'medium': p['src']['medium'],
                   'w': p['width'], 'h': p['height']} for p in r.json().get('photos', [])]
        cache_path(key).write_text(json.dumps({'query': q, 'photos': photos}, ensure_ascii=False), encoding='utf-8')
        print(f'[{n}/{len(todo)}] {key} "{q}" 후보 {len(photos)} (남은 월 한도 {r.headers.get("X-Ratelimit-Remaining")})', flush=True)
        time.sleep(25)

def ranked(key):
    data = json.loads(cache_path(key).read_text(encoding='utf-8'))
    words = [w for w in ((NAMES[key] or '').lower().split() + data['query'].lower().split()) if len(w) > 2]
    for p in data['photos']:
        p['score'] = score(p['alt'], key, words)
    return sorted(data['photos'], key=lambda p: -p['score'])

def build():
    picks = json.loads(PICKS.read_text(encoding='utf-8')) if PICKS.exists() else {}
    PHOTOS.mkdir(exist_ok=True)
    credits, sheet_rows = {}, []
    for key in NAMES:
        if not cache_path(key).exists():
            continue
        cands = ranked(key)
        if not cands:
            print('후보 없음', key); continue
        want = picks.get(key, 0)
        cat, item = key.split('/')
        dst = PHOTOS / f'{cat}_{item}.jpg'
        if want is None:  # 알맞은 사진이 없어 선그림을 그대로 쓰기로 한 항목
            dst.unlink(missing_ok=True)
            continue
        chosen = next((p for p in cands if p['id'] == want), cands[0])
        meta = OUT / 'photo_chosen' / (key.replace('/', '__') + '.txt')
        meta.parent.mkdir(exist_ok=True)
        if not dst.exists() or not meta.exists() or meta.read_text() != str(chosen['id']):
            im = Image.open(io.BytesIO(requests.get(chosen['large'], timeout=60).content)).convert('RGB')
            im.thumbnail((720, 720), Image.LANCZOS)  # 폰 화면 카드·퍼즐에 충분, 한 장 60KB 안팎
            im.save(dst, 'JPEG', quality=80, optimize=True, progressive=True)
            meta.write_text(str(chosen['id']))
        credits[key] = {'by': chosen['photographer'], 'url': chosen['url'], 'src': 'Pexels'}
        sheet_rows.append((key, dst, [c['id'] for c in cands[:8]].index(chosen['id']) if chosen in cands[:8] else -1))
    (OUT / 'photo_credits.json').write_text(json.dumps(credits, ensure_ascii=False, indent=0), encoding='utf-8')
    make_sheets(sheet_rows)
    print('저장', len(credits), '장')

def make_sheets(rows):
    TH, COLS = 170, 6
    font = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 15)
    for part in range(0, len(rows), 24):
        chunk = rows[part:part+24]
        nrow = (len(chunk)+COLS-1)//COLS
        sheet = Image.new('RGB', (COLS*(TH+8)+8, nrow*(TH+28)+8), 'white')
        dr = ImageDraw.Draw(sheet)
        for i, (key, path, _) in enumerate(chunk):
            x, y = 8 + (i % COLS)*(TH+8), 8 + (i//COLS)*(TH+28)
            im = Image.open(path); im.thumbnail((TH, TH))
            sheet.paste(im, (x + (TH-im.width)//2, y + (TH-im.height)//2))
            dr.text((x, y+TH+3), key.split('/')[1], fill='#c00', font=font)
        sheet.save(OUT / f'photo_sheet_{part//24+1:02d}.jpg', quality=82)

def candidates_sheet(key):
    """한 항목의 후보(최대 20장)를 번호와 함께 늘어놓는다 (사진을 눈으로 보고 바꿀 때 쓰는 용도)"""
    cands = ranked(key)[:20]
    TH, COLS = 150, 5
    font = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 14)
    nrow = (len(cands)+COLS-1)//COLS
    sheet = Image.new('RGB', (COLS*(TH+6)+6, nrow*(TH+22)+6), 'white')
    dr = ImageDraw.Draw(sheet)
    for i, c in enumerate(cands):
        x, y = 6 + (i % COLS)*(TH+6), 6 + (i//COLS)*(TH+22)
        im = Image.open(io.BytesIO(requests.get(c['medium'], timeout=60).content)).convert('RGB'); im.thumbnail((TH, TH))
        sheet.paste(im, (x + (TH-im.width)//2, y + (TH-im.height)//2))
        dr.text((x, y+TH+2), str(i), fill='#c00', font=font)
    out = OUT / 'cands' / (key.replace('/', '__') + '.jpg')
    out.parent.mkdir(exist_ok=True)
    sheet.save(out, quality=80)
    (out.with_suffix('.ids')).write_text(json.dumps([c['id'] for c in cands]))

def picks_from_index():
    """비교표 번호로 적어 둔 선택(_out/pick_idx.json, null=선그림 유지)을 사진 id로 바꿔 photo_picks.json에 합친다"""
    picks = json.loads(PICKS.read_text(encoding='utf-8')) if PICKS.exists() else {}
    for key, idx in json.loads((OUT / 'pick_idx.json').read_text(encoding='utf-8')).items():
        if idx is None:
            picks[key] = None; continue
        ids = json.loads((OUT / 'cands' / (key.replace('/', '__') + '.ids')).read_text())
        picks[key] = ids[idx]
    PICKS.write_text(json.dumps(dict(sorted(picks.items())), ensure_ascii=False, indent=0), encoding='utf-8')
    print('선택', len(picks))

def embed():
    """사진 출처를 index.html의 PHOTO_CREDITS 자리에 넣는다 (이 목록에 있는 항목만 사진으로 바뀐다)"""
    credits = json.loads((OUT / 'photo_credits.json').read_text(encoding='utf-8'))
    credits = {k: v for k, v in credits.items() if (PHOTOS / (k.replace('/', '_') + '.jpg')).exists()}
    body = ',\n'.join(f'    {json.dumps(k, ensure_ascii=False)}:{json.dumps([v["by"], v["url"]], ensure_ascii=False)}' for k, v in sorted(credits.items()))
    html_path = ROOT / 'index.html'
    html = html_path.read_text(encoding='utf-8')
    a, b = '/*PHOTO_CREDITS_START*/', '/*PHOTO_CREDITS_END*/'
    i, j = html.index(a) + len(a), html.index(b)
    html = html[:i] + '{\n' + body + '\n  }' + html[j:]
    html_path.write_text(html, encoding='utf-8')
    print('출처', len(credits), '건 반영')

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'search'
    if mode == 'search': search()
    elif mode == 'build': build()
    elif mode == 'picks': picks_from_index()
    elif mode == 'embed': embed()
    elif mode == 'cands':
        for k in sys.argv[2:]: candidates_sheet(k)
