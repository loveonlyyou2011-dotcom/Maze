# 한 편의 검색이 끝날 때까지 기다렸다가 사진 비교표와 영상 장면 비교표를 만든다 (사진 고르기용)
#   python story_sheet_one.py <동화 id>
import sys, time, json, pathlib
import story_fetch as sf

sid = sys.argv[1]
st = next(s for s in sf.STORIES if s['id'] == sid)
need = [sf.cache_file(sid, n, 'photo') for n in range(len(st['scenes']))]
need += [sf.cache_file(sid, n, 'video') for n, sc in enumerate(st['scenes']) if sc.get('v')]
while not all(f.exists() for f in need):
    time.sleep(10)
sf.STORIES = [st]
sf.sheets()
if any(sc.get('v') for sc in st['scenes']):
    sf.SHEETS = sf.SHEETS / (sid + '_v'); sf.SHEETS.mkdir(exist_ok=True)
    sf.vsheets()
