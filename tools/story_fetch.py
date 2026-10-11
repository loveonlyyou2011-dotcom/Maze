# 🎬 동화 극장 장면 사진·영상 받기 (Pexels)
#
#   python story_fetch.py search   장면마다 사진 후보(+ 표시한 장면은 영상 후보) 검색 → _out/story_cache/
#   python story_fetch.py sheets   동화별 후보 비교표 → _out/story_sheets/
#   python story_fetch.py vsheets  영상 후보마다 앞·중간·뒤 3장면 비교표 (움직임 확인용)
#   python story_fetch.py build    story_picks.json에 고른 대로 stories/ 에 저장(사진 960px, 영상 7초·640px·소리 없음)
#   python story_fetch.py embed    이야기 글·장면 파일·출처를 index.html 의 STORIES 자리에 넣는다
#
# 이야기 글과 검색어는 stories.json 한 곳에서 관리한다.
# Pexels 기본 한도(시간당 200회)를 블로그 자동화와 나눠 쓰므로 검색은 25초에 한 번만 한다.
import os, io, sys, json, time, pathlib, subprocess, requests
from PIL import Image, ImageDraw, ImageFont

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
OUT = TOOLS / '_out'
CACHE = OUT / 'story_cache'; CACHE.mkdir(parents=True, exist_ok=True)
SHEETS = OUT / 'story_sheets'; SHEETS.mkdir(parents=True, exist_ok=True)
MEDIA = ROOT / 'stories'
PICKS = TOOLS / 'story_picks.json'
STORIES = json.loads((TOOLS / 'stories.json').read_text(encoding='utf-8'))

def api(path, params):
    for _ in range(3):
        r = requests.get('https://api.pexels.com/' + path, headers={'Authorization': os.environ['PEXELS_API_KEY']}, params=params, timeout=30)
        if r.status_code == 429:
            print('한도 초과 → 10분 쉼', flush=True); time.sleep(600); continue
        r.raise_for_status()
        return r.json(), r.headers.get('X-Ratelimit-Remaining')
    raise RuntimeError('검색 실패')

def cache_file(sid, n, kind): return CACHE / f'{sid}_{n}_{kind}.json'

def search():
    jobs = []
    for st in STORIES:
        for n, sc in enumerate(st['scenes']):
            if not cache_file(st['id'], n, 'photo').exists(): jobs.append((st['id'], n, 'photo', sc['q']))
            if sc.get('v') and not cache_file(st['id'], n, 'video').exists(): jobs.append((st['id'], n, 'video', sc['v']))
    print('검색할 것', len(jobs), '건', flush=True)
    for k, (sid, n, kind, q) in enumerate(jobs, 1):
        if kind == 'photo':
            data, left = api('v1/search', {'query': q, 'per_page': 15})
            items = [{'id': p['id'], 'by': p['photographer'], 'url': p['url'], 'large': p['src']['large2x'], 'medium': p['src']['medium'],
                      'alt': p.get('alt') or ''} for p in data.get('photos', [])]
        else:
            data, left = api('videos/search', {'query': q, 'per_page': 12, 'size': 'medium'})
            items = []
            for v in data.get('videos', []):
                files = [f for f in v.get('video_files', []) if f.get('width') and f.get('link') and (f.get('file_type') or '').endswith('mp4')]
                files.sort(key=lambda f: f['width'])
                pick = next((f for f in files if f['width'] >= 640), files[-1] if files else None)
                if not pick: continue
                items.append({'id': v['id'], 'by': (v.get('user') or {}).get('name', ''), 'url': v['url'], 'thumb': v.get('image'),
                              'duration': v.get('duration'), 'file': pick['link'], 'w': pick['width'], 'h': pick['height']})
        cache_file(sid, n, kind).write_text(json.dumps({'query': q, 'items': items}, ensure_ascii=False), encoding='utf-8')
        print(f'[{k}/{len(jobs)}] {sid} {n} {kind} "{q}" 후보 {len(items)} (남은 월 한도 {left})', flush=True)
        time.sleep(25)

def load(sid, n, kind):
    f = cache_file(sid, n, kind)
    return json.loads(f.read_text(encoding='utf-8'))['items'] if f.exists() else []

def sheets():
    font = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 14)
    TH, COLS = 140, 8
    for st in STORIES:
        rows = len(st['scenes'])
        sheet = Image.new('RGB', (60 + COLS*(TH+6), rows*(TH+22) + 6), 'white')
        dr = ImageDraw.Draw(sheet)
        for n, sc in enumerate(st['scenes']):
            y = 6 + n*(TH+22)
            dr.text((6, y+TH//2-8), f'#{n}', fill='black', font=font)
            cands = [('P', i, c['medium']) for i, c in enumerate(load(st['id'], n, 'photo')[:6])]
            cands += [('V', i, c['thumb']) for i, c in enumerate(load(st['id'], n, 'video')[:4]) if c.get('thumb')]
            for ci, (kind, i, url) in enumerate(cands[:COLS]):
                x = 60 + ci*(TH+6)
                try:
                    im = Image.open(io.BytesIO(requests.get(url, timeout=60).content)).convert('RGB'); im.thumbnail((TH, TH))
                    sheet.paste(im, (x + (TH-im.width)//2, y + (TH-im.height)//2))
                except Exception: pass
                dr.text((x, y+TH+2), f'{kind}{i}', fill='#c00' if kind == 'P' else '#06c', font=font)
        sheet.save(SHEETS / f'{st["id"]}.jpg', quality=80)
        print('비교표', st['id'], flush=True)

def build():
    picks = json.loads(PICKS.read_text(encoding='utf-8')) if PICKS.exists() else {}
    built_f = OUT / 'story_built.json'   # 장면별로 어떤 사진·영상으로 만들었는지 (고른 것이 바뀌면 다시 받는다)
    built = json.loads(built_f.read_text(encoding='utf-8')) if built_f.exists() else {}
    credits = {}
    for st in STORIES:
        d = MEDIA / st['id']; d.mkdir(parents=True, exist_ok=True)
        for n, sc in enumerate(st['scenes']):
            key = f'{st["id"]}/{n}'
            pk = picks.get(key, {})
            was = built.get(key, {})
            photos = load(st['id'], n, 'photo')
            p = photos[pk.get('p', 0)] if photos else None
            dst = d / f'{n}.jpg'
            if p and (not dst.exists() or was.get('p') != p['id']):
                im = Image.open(io.BytesIO(requests.get(p['large'], timeout=60).content)).convert('RGB')
                im.thumbnail((960, 960), Image.LANCZOS)
                im.save(dst, 'JPEG', quality=80, optimize=True, progressive=True)
            entry = {'photo': [p['by'], p['url']] if p else None}
            now = {'p': p['id'] if p else None}
            vdst = d / f'{n}.mp4'
            if pk.get('v') is not None:
                v = load(st['id'], n, 'video')[pk['v']]
                start = pk.get('ss', 0)
                if not vdst.exists() or was.get('v') != v['id'] or was.get('ss', 0) != start:
                    raw = OUT / 'story_raw.mp4'
                    raw.write_bytes(requests.get(v['file'], timeout=180).content)
                    # 7초만, 폭 640px, 소리 없이, 웹에서 바로 재생되게(faststart) — 장면 하나 200~500KB (crf 30은 100KB대였지만 뭉개져 보여 26으로 올림)
                    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(start), '-i', str(raw), '-t', '7', '-an',
                                    '-vf', 'scale=640:-2', '-c:v', 'libx264', '-preset', 'slow', '-crf', '26',
                                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(vdst)], check=True)
                entry['video'] = [v['by'], v['url']]
                now.update({'v': v['id'], 'ss': start})
            elif vdst.exists():
                vdst.unlink()
            credits[key] = entry
            built[key] = now
    built_f.write_text(json.dumps(built, indent=0), encoding='utf-8')
    (OUT / 'story_credits.json').write_text(json.dumps(credits, ensure_ascii=False, indent=0), encoding='utf-8')
    total = sum(f.stat().st_size for f in MEDIA.rglob('*') if f.is_file())
    print('저장 완료', len(credits), '장면,', round(total/1e6, 1), 'MB')

def vsheets():
    """영상 후보는 썸네일 한 장으로는 움직임을 알 수 없어서, 앞·중간·뒤 3장면을 뽑아 나란히 본다"""
    font = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 14)
    TH = 150
    rows = []
    for st in STORIES:
        for n, sc in enumerate(st['scenes']):
            for i, v in enumerate(load(st['id'], n, 'video')[:4]):
                rows.append((f'{st["id"]}/{n} V{i} ({v.get("duration")}s)', v))
    for part in range(0, len(rows), 8):
        chunk = rows[part:part+8]
        sheet = Image.new('RGB', (230 + 3*(TH*16//9+6), len(chunk)*(TH+8) + 8), 'white')
        dr = ImageDraw.Draw(sheet)
        for r, (label, v) in enumerate(chunk):
            y = 8 + r*(TH+8)
            dr.text((6, y+TH//2-8), label, fill='black', font=font)
            raw = OUT / 'vs_raw.mp4'
            try: raw.write_bytes(requests.get(v['file'], timeout=180).content)
            except Exception: continue
            dur = max(1, v.get('duration') or 6)
            for k, t in enumerate([0.5, dur*0.4, dur*0.8]):
                fr = OUT / 'vs_frame.jpg'
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(t), '-i', str(raw), '-frames:v', '1', '-vf', f'scale=-2:{TH}', str(fr)])
                if fr.exists():
                    im = Image.open(fr).convert('RGB'); im.thumbnail((TH*16//9, TH))
                    sheet.paste(im, (230 + k*(TH*16//9+6), y))
                    fr.unlink()
        sheet.save(SHEETS / f'video_{part//8+1:02d}.jpg', quality=80)
        print('영상 비교표', part//8+1, flush=True)

def embed():
    credits = json.loads((OUT / 'story_credits.json').read_text(encoding='utf-8'))
    data = []
    for st in STORIES:
        scenes = []
        for n, sc in enumerate(st['scenes']):
            c = credits.get(f'{st["id"]}/{n}', {})
            scenes.append({'t': sc['t'], 'fx': sc.get('fx', ''), 'video': bool(c.get('video')),
                           'credit': [x for x in [c.get('photo'), c.get('video')] if x]})
        data.append({'id': st['id'], 'group': st.get('group', ''), 'emoji': st['emoji'], 'gradient': st['gradient'], 'title': st['title'],
                     'moral': st['moral'], 'scenes': scenes, 'quiz': st['quiz']})
    html_path = ROOT / 'index.html'
    html = html_path.read_text(encoding='utf-8')
    a, b = '/*STORIES_START*/', '/*STORIES_END*/'
    i, j = html.index(a) + len(a), html.index(b)
    html = html[:i] + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + html[j:]
    html_path.write_text(html, encoding='utf-8')
    print('동화', len(data), '편 반영')

if __name__ == '__main__':
    {'search': search, 'sheets': sheets, 'vsheets': vsheets, 'build': build, 'embed': embed}[sys.argv[1] if len(sys.argv) > 1 else 'search']()
