# 한 편을 통째로 읽은 음성을 장면별로 자른다.
# 무료 등급 TTS 한도가 모델마다 하루 10번이라(2026-10-12 실측) 장면마다 만들면 704번이 필요해서,
# 한 편(8장면)을 한 번에 읽힌 뒤 자르는 방식으로 바꿨다. 장면 사이 쉼은 1~3초로 들쭉날쭉해서
# "가장 긴 쉼 7개"로는 못 자른다. 대신 글자 수 비율로 장면 경계가 올 자리를 어림하고, 그 근처의
# 쉼 가운데 (쉼 길이 − 어림 위치와의 거리)가 가장 좋은 것을 순서대로 고른다(동적 계획법).
import subprocess, re

def silences(wav, noise='-38dB', min_d=0.25):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(wav), '-af', f'silencedetect=noise={noise}:d={min_d}', '-f', 'null', '-'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', out)]
    ends = [float(x) for x in re.findall(r'silence_end: ([0-9.]+)', out)]
    h, mi, se = re.search(r'Duration: (\d+):(\d+):([0-9.]+)', out).groups()
    dur = int(h)*3600 + int(mi)*60 + float(se)
    return [(s, e) for s, e in zip(starts, ends)], dur

def split_points(texts, sil, total):
    """texts: 장면 글 목록, sil: [(시작,끝)], total: 전체 길이(초) → 장면 경계 시각 len(texts)-1개, 신뢰도"""
    lens = [max(1, len(t)) for t in texts]
    acc, est = 0, []
    for L in lens[:-1]:
        acc += L; est.append(total * acc / sum(lens))
    cands = [((s + e) / 2, e - s) for s, e in sil if s > 0.3 and e < total - 0.3]
    k, m = len(est), len(cands)
    if m < k: return None, 0
    NEG = -1e9
    # best[i][j]: 경계 i개를 정했고 i번째 경계가 후보 j일 때 최고 점수
    best = [[NEG]*m for _ in range(k)]; back = [[-1]*m for _ in range(k)]
    def score(i, j):
        t, d = cands[j]
        return d * 2.0 - abs(t - est[i]) / max(2.0, total * 0.04)
    for j in range(m): best[0][j] = score(0, j)
    for i in range(1, k):
        run, arg = NEG, -1
        for j in range(m):
            if j - 1 >= 0 and best[i-1][j-1] > run: run, arg = best[i-1][j-1], j-1
            if arg >= 0: best[i][j] = run + score(i, j); back[i][j] = arg
    j = max(range(m), key=lambda x: best[k-1][x])
    pts = []
    for i in range(k-1, -1, -1):
        pts.append(cands[j][0]); j = back[i][j]
    pts.reverse()
    # 신뢰도: 잘린 조각 길이가 글자 수 비율과 얼마나 비슷한가 (1이면 완벽)
    seg = [b - a for a, b in zip([0] + pts, pts + [total])]
    ratio = [s / (total * L / sum(lens)) for s, L in zip(seg, lens)]
    conf = min(min(ratio), 1 / max(ratio))
    return pts, conf

def cut(wav, pts, total, outs):
    edges = [0] + pts + [total]
    for (a, b), dst in zip(zip(edges, edges[1:]), outs):
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-i', str(wav),
                        '-af', 'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,apad=pad_dur=0.25',
                        '-c:a', 'aac', '-b:a', '40k', '-ac', '1', '-ar', '24000', '-movflags', '+faststart', str(dst)], check=True)

def split_points_guided(texts, sil, total, starts):
    """Gemini가 알려준 문단 시작 시각(starts) 근처의 쉼에 맞춘다.
    점수 = 쉼 길이 − 어림 시각과의 거리/1.5초 (실측: 3초 쉼과 0.9초 쉼이 비슷한 거리일 때 3초 쪽이 맞았다).
    고른 경계가 어림 시각에서 2.5초 넘게 떨어지면 실패로 본다."""
    est = starts[1:len(texts)]
    cands = [((s + e) / 2, e - s) for s, e in sil if s > 0.3 and e < total - 0.3]
    k, m = len(est), len(cands)
    if m < k: return None, False
    NEG = -1e9
    best = [[NEG]*m for _ in range(k)]; back = [[-1]*m for _ in range(k)]
    def score(i, j):
        t, d = cands[j]
        return d - abs(t - est[i]) / 1.5
    for j in range(m): best[0][j] = score(0, j)
    for i in range(1, k):
        run, arg = NEG, -1
        for j in range(m):
            if j - 1 >= 0 and best[i-1][j-1] > run: run, arg = best[i-1][j-1], j-1
            if arg >= 0: best[i][j] = run + score(i, j); back[i][j] = arg
    j = max(range(m), key=lambda x: best[k-1][x])
    pts = []
    for i in range(k-1, -1, -1):
        pts.append(cands[j][0]); j = back[i][j]
    pts.reverse()
    ok = all(abs(p - e) <= 2.5 for p, e in zip(pts, est))
    return pts, ok

def duration(f):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    return float(out.strip() or 0)
