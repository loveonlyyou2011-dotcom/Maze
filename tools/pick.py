# 고른 사진 번호를 story_picks.json에 적는다
#   python pick.py <동화 id> "2 5 4/v1@1 3 5 1 1 3"   (장면 순서대로, 사진번호[/v영상번호@시작초])
import sys, json, pathlib
sid, spec = sys.argv[1], sys.argv[2].split()
p = pathlib.Path(__file__).with_name('story_picks.json')
d = json.loads(p.read_text(encoding='utf-8'))
for n, s in enumerate(spec):
    e = {}
    photo, _, vid = s.partition('/v')
    e['p'] = int(photo)
    if vid:
        v, _, ss = vid.partition('@')
        e['v'] = int(v); e['ss'] = float(ss or 0)
    d[f'{sid}/{n}'] = e
p.write_text(json.dumps(dict(sorted(d.items())), ensure_ascii=False, indent=0), encoding='utf-8')
print(sid, len(spec), '장면 기록, 전체', len(d))
