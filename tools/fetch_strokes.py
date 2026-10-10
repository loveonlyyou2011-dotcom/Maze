# 일본어 히라가나(KanjiVG)와 중국어 상형문자(Make Me a Hanzi → hanzi-writer-data)의
# 획 중심선 데이터를 받아, 0~100 좌표의 꺾은선(획 순서대로)으로 바꿔 JSON으로 저장한다.
import re, json, math, os, pathlib, urllib.parse, requests

OUT = pathlib.Path(__file__).parent / '_out' / 'strokes.json'
OUT.parent.mkdir(parents=True, exist_ok=True)
HIRA = list('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん')
HANZI = list('一二三人口日月山水火木大小上下手目耳田雨')

NUM = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')
TOK = re.compile(r'[MmLlHhVvCcSsQqTtZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')

def cubic(p0, p1, p2, p3, n=10):
    out = []
    for i in range(1, n+1):
        t = i/n; mt = 1-t
        out.append((mt**3*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t**3*p3[0],
                    mt**3*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t**3*p3[1]))
    return out

def parse_path(d):
    toks = TOK.findall(d)
    i = 0; cmd = None; cur = (0.0, 0.0); start = cur; last_c2 = None; pts = []
    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v
    while i < len(toks):
        if re.fullmatch(r'[A-Za-z]', toks[i]):
            cmd = toks[i]; i += 1
            if cmd in 'Zz':
                pts.append(start); cur = start; continue
        rel = cmd.islower(); c = cmd.upper()
        ox, oy = cur if rel else (0.0, 0.0)
        if c == 'M':
            cur = (ox+num(), oy+num()); start = cur; pts.append(cur); cmd = 'l' if rel else 'L'; last_c2 = None
        elif c == 'L':
            cur = (ox+num(), oy+num()); pts.append(cur); last_c2 = None
        elif c == 'H':
            cur = ((cur[0] if rel else 0)+num(), cur[1]); pts.append(cur); last_c2 = None
        elif c == 'V':
            cur = (cur[0], (cur[1] if rel else 0)+num()); pts.append(cur); last_c2 = None
        elif c == 'C':
            p1 = (ox+num(), oy+num()); p2 = (ox+num(), oy+num()); p3 = (ox+num(), oy+num())
            pts += cubic(cur, p1, p2, p3); last_c2 = p2; cur = p3
        elif c == 'S':
            p1 = (2*cur[0]-last_c2[0], 2*cur[1]-last_c2[1]) if last_c2 else cur
            p2 = (ox+num(), oy+num()); p3 = (ox+num(), oy+num())
            pts += cubic(cur, p1, p2, p3); last_c2 = p2; cur = p3
        else:
            raise ValueError('지원하지 않는 명령 ' + cmd)
    return pts

def rdp(pts, eps):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2-x1, y2-y1; L = math.hypot(dx, dy) or 1e-9
    best, idx = 0, 0
    for k in range(1, len(pts)-1):
        x, y = pts[k]
        dist = abs(dy*x - dx*y + x2*y1 - y2*x1)/L
        if dist > best: best, idx = dist, k
    if best > eps:
        return rdp(pts[:idx+1], eps)[:-1] + rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]

def flat(pts):
    return [round(v, 1) for p in pts for v in p]

data = {}
s = requests.Session()
for ch in HIRA:
    url = f'https://raw.githubusercontent.com/KanjiVG/kanjivg/master/kanji/{ord(ch):05x}.svg'
    svg = s.get(url, timeout=30).text
    paths = re.findall(r'<path[^>]*id="kvg:[0-9a-f]+-s(\d+)"[^>]*\sd="([^"]+)"', svg)
    if not paths:
        paths = re.findall(r'<path[^>]*\sd="([^"]+)"[^>]*id="kvg:[0-9a-f]+-s(\d+)"', svg)
        paths = [(n, d) for d, n in paths]
    paths.sort(key=lambda t: int(t[0]))
    strokes = []
    for _, d in paths:
        pts = [(x*100/109, y*100/109) for x, y in parse_path(d)]
        strokes.append(flat(rdp(pts, 0.7)))
    data[ch] = strokes
    print(ch, len(strokes), '획', flush=True)

for ch in HANZI:
    url = 'https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0/' + urllib.parse.quote(ch) + '.json'
    j = s.get(url, timeout=30).json()
    strokes = []
    for med in j['medians']:
        pts = [(x/1024*100, (900-y)/1024*100) for x, y in med]
        strokes.append(flat(rdp(pts, 0.7)))
    data[ch] = strokes
    print(ch, len(strokes), '획', flush=True)

OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('저장', OUT, len(json.dumps(data, ensure_ascii=False, separators=(',', ':'))), 'bytes')
