# 🎬 동화 극장 감정 낭독 음성 만들기 (Gemini TTS)
#
# 기기 내장 음성은 글자를 그대로 읽어 감정이 없다는 의견(2026-10-12)에 따라, Gemini TTS에
# "다정한 이야기꾼 + 등장인물별 목소리 연기"를 지시해 음성을 미리 만들어 둔다.
#   python story_tts.py           빠진 이야기·언어를 만든다 (만든 것은 건너뜀 → 날마다 실행하면 이어서)
#   python story_tts.py --resplit 받아 둔 원본 음성을 TTS 한도를 쓰지 않고 다시 확인해 자른다
#   python story_tts.py --verify   잘린 장면을 하나씩 받아써서 원문과 대조 (기본 실행 때도 끝에 자동으로)
#
# 실측(2026-10-12)으로 정한 것:
# - 무료 등급은 TTS 모델마다 하루 10번만 부를 수 있다. 장면마다 만들면 704번이 필요해서,
#   한 편(8장면)을 한 번에 읽힌 뒤 장면별로 자른다 → 22편 × 4개 언어 = 88번.
# - 3.1-flash-tts / 2.5 TTS는 "지시: 본문" 형식에서 본문만 읽고 연기한다.
#   3.8 TTS는 그 형식이면 지시문까지 소리 내어 읽고 system_instruction도 거절해서, 지시를 [대괄호 태그]로 준다.
#   3.8-flash는 가끔 원문에 없는 말을 지어 넣는다("방긋 웃으며 말했죠") → 받아쓰기로 원문과 대조해 걸러 낸다.
# - 장면 사이 쉼이 1~3초로 들쭉날쭉해 쉼만으로는 7곳 중 3곳을 잘못 잘랐다. 그래서 Gemini에 음성을 들려
#   각 장면이 시작하는 시각과 받아쓰기를 받고, 그 근처의 쉼에 맞춰 자른다(tts_split.py).
#   받아쓰기·시각 확인은 블로그 자동화가 쓰는 lite 모델(3.1-flash-lite, 3.5-flash-lite) 대신 preview 모델을 쓴다.
# - TTS 모델은 블로그가 쓰는 글쓰기 모델과 한도가 따로라 블로그 작업에는 영향이 없다.
import os, sys, json, time, wave, pathlib, random, re, difflib
from google import genai
from google.genai import types, errors
import tts_split

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
RAW = TOOLS / '_out' / 'tts_wav'; RAW.mkdir(parents=True, exist_ok=True)
MANIFEST = TOOLS / 'story_tts.json'   # 장면별로 어떤 모델로 만들었는지 (저장소에 남긴다)
STORIES = json.loads((TOOLS / 'stories.json').read_text(encoding='utf-8'))
# (모델, 지시 방식) — 앞에서부터 쓰고, 그날 한도가 차면 다음 모델로
MODELS = [('gemini-3.1-flash-tts-preview', 'prompt'), ('gemini-2.5-flash-preview-tts', 'prompt'),
          ('gemini-2.5-pro-preview-tts', 'prompt'), ('gemini-3.8-flash-lite-tts', 'tags'), ('gemini-3.8-flash-tts', 'tags')]
CHECK_MODEL = 'gemini-3.1-flash-lite-preview'
VOICE = 'Sulafat'   # 따뜻한 목소리. 네 언어 모두 같은 이야기꾼이 읽도록 하나로 통일
LANG_NAME = {'ko': '한국어', 'en': '영어', 'ja': '일본어', 'zh': '중국어'}
LANGS = ['ko', 'en', 'ja', 'zh']

NARRATOR = ("유치원 아이들에게 잠자리 동화를 들려주는 다정한 이야기꾼처럼 읽어 줘. 천천히 또박또박, "
            "장면의 감정(신남, 긴장, 무서움, 슬픔, 졸림, 놀람, 감동)에 맞춰 목소리 크기와 빠르기, 높낮이를 바꾸고, "
            "등장인물의 대사는 그 인물이 되어 실감 나게 연기해 줘. 무서운 장면도 아이가 놀라 울 만큼 무섭지는 않게. ")
TAG = '[warm, expressive bedtime storyteller for little kids, slow and clear; give each character their own voice and feeling]'
CAST = {
    'tortoise': '토끼는 장난스럽고 잘난 척하는 빠른 말투, 거북이는 느릿하고 차분하고 착한 목소리.',
    'sunwind': '해는 따뜻하고 부드러운 목소리, 바람은 거칠고 큰소리치는 목소리, 나그네는 추울 땐 덜덜 떨고 더울 땐 지친 목소리.',
    'ant': '개미는 부지런하고 씩씩한 목소리, 베짱이는 느긋하게 흥얼거리다가 겨울엔 배고프고 추운 목소리.',
    'mouse': '시골쥐는 수줍고 순박한 목소리, 서울쥐는 으스대는 말투, 고양이가 나올 땐 긴장감 있게.',
    'sunmoon': '호랑이는 굵고 무서운 목소리(엄마 흉내 낼 땐 어색하게 부드러운 척), 오누이는 겁먹었지만 용감한 목소리, 하늘로 올라갈 땐 신비롭게.',
    'heungbu': '흥부는 착하고 다정한 목소리, 놀부는 욕심 많고 심술궂은 목소리, 보물이 쏟아질 땐 신나게, 도깨비 장면은 무섭지만 우스꽝스럽게.',
    'magpie': '선비는 점잖고 침착한 목소리, 구렁이는 쉬익거리는 음흉한 목소리, 종소리 장면은 긴장했다가 감동적으로.',
    'pigs': '아기 돼지들은 귀엽고 높은 목소리, 늑대는 크고 거친 목소리로 "후~" 하고 세게 부는 소리를 살려서.',
    'lionmouse': '사자는 크고 우렁찬 목소리, 생쥐는 작고 높고 떨리는 목소리, 그물을 갉아 구해 줄 땐 씩씩하게.',
    'crow': '까마귀는 목마르고 고민하는 목소리, 방법을 찾았을 땐 신나는 목소리, 물을 마실 땐 시원하게.',
    'foxstork': '여우는 능청스럽고 얄미운 목소리, 두루미는 점잖고 우아한 목소리, 마지막엔 서로 미안해하는 따뜻한 말투.',
    'wolfboy': '소년은 장난꾸러기 목소리, "늑대다!"는 다급하게 외치고, 진짜 늑대가 나왔을 땐 정말 겁에 질린 목소리, 마지막은 반성하는 말투.',
    'axe': '나무꾼은 착하고 정직한 목소리, 산신령은 신비롭고 깊게 울리는 목소리.',
    'duckling': '미운 아기 오리는 외롭고 슬픈 목소리였다가 백조가 된 걸 알 땐 벅차게 기쁜 목소리, 놀리는 친구들은 얄밉게.',
    'bremen': '당나귀는 늙고 느긋한 목소리, 개는 씩씩하게 "멍멍", 고양이는 새침하게 "야옹", 수탉은 우렁차게 "꼬끼오", 도둑을 놀래킬 땐 다 같이 크게.',
    'turnip': '할아버지는 허허 다정한 목소리, "영차영차"는 힘을 꽉 주며, 한 명씩 늘어날수록 점점 긴장되게, 쑥 뽑힐 땐 신나게.',
    'bears': '아빠 곰은 굵은 목소리, 엄마 곰은 부드러운 목소리, 아기 곰은 작고 귀여운 목소리, 금발 소녀는 호기심 많고 밝은 목소리.',
    'beanstalk': '잭은 호기심 많고 용감한 목소리, 엄마는 화났다가 마지막엔 기쁜 목소리, 구름 위 성과 거인 장면은 웅장하게.',
    'rabbitliver': '자라는 느릿하고 공손한 목소리, 토끼는 처음엔 들뜨고 겁먹었다가 꾀를 낼 땐 능청스럽고 재치 있게.',
    'brothers': '형과 아우는 다정하고 따뜻한 목소리, 밤에 몰래 볏단을 나를 땐 속삭이듯, 마주쳤을 땐 감동적으로.',
    'redbean': '호랑이는 무섭지만 우스꽝스러운 목소리, 할머니는 엉엉 슬프다가 마지막엔 기쁜 목소리, 알밤·자라 친구들은 씩씩하고 귀엽게.',
    'lump': '착한 할아버지는 흥겹게 노래하듯, 도깨비들은 신나고 우스꽝스럽게, 욕심쟁이 영감은 심술궂게.',
}

def media_path(sid, n, lang): return ROOT / 'stories' / sid / f'{n}_{lang}.m4a'

def load_manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {}

def save_manifest(m):
    MANIFEST.write_text(json.dumps(dict(sorted(m.items())), ensure_ascii=False, indent=0), encoding='utf-8')

def tts_input(st, lang, mode):
    paras = [sc['t'][lang] for sc in st['scenes']]
    if mode == 'prompt':
        return (NARRATOR + CAST.get(st['id'], '') +
                f" 마지막 문단은 따뜻하게 마무리해 줘. 문단 하나를 다 읽으면 2초 동안 완전히 쉬었다가 다음 문단을 읽어. "
                f"본문은 {LANG_NAME[lang]}이니 {LANG_NAME[lang]}로만, 아래 본문만 읽어 줘:\n\n" + "\n\n".join(paras))
    return TAG + ' ' + "\n\n[pause]\n\n".join(paras)

def norm(s):
    return re.sub(r'[\s\W_]+', '', s or '').lower()

def align(client, wav, paras):
    """음성을 들려주고 문단별 시작 시각과 받아쓰기를 받는다"""
    q = ("This audio is a narration of the following numbered paragraphs, read in order. For each paragraph give the time in seconds "
         "(one decimal) when its FIRST word starts, and transcribe exactly what is spoken for that paragraph. "
         "Answer only JSON: {\"starts\": [..], \"spoken\": [..]}\n\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(paras)))
    for _ in range(4):
        try:
            r = client.models.generate_content(model=CHECK_MODEL, contents=[types.Part.from_bytes(data=wav.read_bytes(), mime_type='audio/wav'), q],
                                               config=types.GenerateContentConfig(response_mime_type='application/json'))
            j = json.loads(r.text)
            if len(j.get('starts', [])) == len(paras): return j
        except errors.APIError as e:
            if e.code == 429: time.sleep(60); continue
            time.sleep(15)
        except Exception:
            time.sleep(5)
    return None

def make_unit(client, st, lang, model, mode, voice):
    paras = [sc['t'][lang] for sc in st['scenes']]
    wav = RAW / f'{st["id"]}_{lang}.wav'
    meta = wav.with_suffix('.json')
    if wav.exists() and meta.exists():
        # 지난번에 받아 두고 자르기만 못 한 음성은 다시 요청하지 않는다 (하루 10번 한도가 아까워서)
        model = json.loads(meta.read_text(encoding='utf-8'))['model']
    else:
        r = client.models.generate_content(model=model, contents=tts_input(st, lang, mode),
            config=types.GenerateContentConfig(response_modalities=['AUDIO'], speech_config=voice))
        pcm = r.candidates[0].content.parts[0].inline_data.data
        with wave.open(str(wav), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
        meta.write_text(json.dumps({'model': model}), encoding='utf-8')
    ok, info = split_unit(client, st, lang, wav)
    if not ok and info.startswith('받아쓰기'):
        wav.unlink(missing_ok=True); meta.unlink(missing_ok=True)   # 다음에 새로 만들도록
    return ok, info, model

def split_unit(client, st, lang, wav, tries=3):
    """받아 둔 한 편 음성을 장면별로 자른다. Gemini가 알려주는 시작 시각은 요청마다 조금씩 달라
    가끔 한 곳이 틀리므로(실측: 일본어 2번째 장면이 1.8초로 잘림), 잘린 길이가 글자 수 비율의
    절반~두 배를 벗어나면 시각을 다시 받아 자른다."""
    paras = [sc['t'][lang] for sc in st['scenes']]
    sil, total = tts_split.silences(wav)
    lens = [len(norm(t)) or 1 for t in paras]
    last = '시각 확인 실패'
    for _ in range(tries):
        j = align(client, wav, paras)
        if not j: continue
        # 받아쓰기 대조: 지시문을 읽었거나 말을 지어 넣었으면 버린다
        sims = [difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() for a, b in zip(paras, j.get('spoken', []))]
        if len(sims) < len(paras) or min(sims) < 0.75:
            return False, f'받아쓰기가 원문과 다름 (최저 {min(sims or [0]):.2f})'
        pts, ratio = best_split(paras, sil, total, lens, [float(x) for x in j['starts']])
        if pts is None: last = '장면 경계를 쉼에 맞추지 못함'; continue
        if min(ratio) < 0.5 or max(ratio) > 2.0:
            last = f'잘린 길이가 글자 수와 안 맞음 ({min(ratio):.2f}~{max(ratio):.2f})'; continue
        tts_split.cut(wav, pts, total, [media_path(st['id'], n, lang) for n in range(len(paras))])
        return True, f'{total:.0f}초, 받아쓰기 일치 최저 {min(sims):.2f}, 길이 비율 {min(ratio):.2f}~{max(ratio):.2f}'
    return False, last

def best_split(paras, sil, total, lens, gem):
    """장면 경계 어림값 세 가지(Gemini 시각, 둘의 평균, 글자 수 비율)로 차례로 잘라 본다. Gemini 시각은 요청마다 한 곳씩
    틀리기도 하고(실측: 일본어 토끼와 거북이 3번 연속), 글자 수 비율만으로는 한국어에서 3곳이 틀려서
    둘을 함께 쓴다."""
    acc, prop = 0, [0.0]
    for L in lens[:-1]:
        acc += L; prop.append(total * acc / sum(lens))
    mean = [(a + b) / 2 for a, b in zip(gem, prop)]
    # Gemini 시각을 먼저 믿고, 그 결과가 길이 확인(절반~두 배)을 못 넘을 때만 평균·글자 수 비율로.
    # "가장 고른 것"을 고르게 했더니 Gemini 시각으로 맞게 잘린 것을 두고 글자 수 쪽을 골라
    # 다음 장면 첫 낱말이 붙어 들어간 적이 있다(시골쥐 한국어 3번째 장면, 2026-10-12).
    fallback = (None, None)
    for est in (gem, mean, prop):
        pts, _ = tts_split.split_points_guided(paras, sil, total, est)
        if not pts: continue
        seg = [b - a for a, b in zip([0] + pts, pts + [total])]
        ratio = [sg / (total * L / sum(lens)) for sg, L in zip(seg, lens)]
        if 0.5 <= min(ratio) and max(ratio) <= 2.0: return pts, ratio
        if fallback[0] is None: fallback = (pts, ratio)
    return fallback

def resplit():
    """이미 받아 둔 원본 음성을 (TTS 한도를 쓰지 않고) 다시 확인해 자른다"""
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    man = load_manifest()
    for st in STORIES:
        for lang in LANGS:
            wav = RAW / f'{st["id"]}_{lang}.wav'
            if not wav.exists(): continue
            ok, info = split_unit(client, st, lang, wav)
            print(('✓' if ok else '✗'), f'{st["id"]}/{lang}', info, flush=True)
            if ok:
                for n in range(len(st['scenes'])):
                    k = f'{st["id"]}/{n}/{lang}'
                    man[k] = {**man.get(k, {}), 'sec': round(tts_split.duration(media_path(st['id'], n, lang)), 2)}
                save_manifest(man)
            time.sleep(4)

def generate():
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    man = load_manifest()
    voice = types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)))
    def needs(st, lang):
        missing = not all(media_path(st['id'], n, lang).exists() for n in range(len(st['scenes'])))
        # 받아쓰기 확인에서 떨어진 장면이 있으면(발음이 뭉개진 낱말 등) 그 이야기·언어를 새로 만든다
        failed = any(man.get(f'{st["id"]}/{n}/{lang}', {}).get('ok') is False for n in range(len(st['scenes'])))
        if failed and not missing:
            for f in (RAW / f'{st["id"]}_{lang}.wav', RAW / f'{st["id"]}_{lang}.json'): f.unlink(missing_ok=True)
        return missing or failed
    units = [(st, lang) for st in STORIES for lang in LANGS if needs(st, lang)]
    print('만들 이야기·언어', len(units), '개', flush=True)
    mi, done, fails = 0, 0, {}
    queue = list(units)
    while queue:
        st, lang = queue.pop(0)
        if mi >= len(MODELS):
            print('모든 TTS 모델의 오늘 한도가 찼습니다. 내일 다시 실행하면 이어서 만듭니다.', flush=True); break
        model, mode = MODELS[mi]
        key = f'{st["id"]}/{lang}'
        try:
            ok, info, model = make_unit(client, st, lang, model, mode, voice)
        except errors.APIError as e:
            msg = str(e)
            if e.code == 429 and ('PerDay' in msg or 'per day' in msg.lower()):
                print(f'  {model} 오늘 한도 소진 → 다음 모델', flush=True); mi += 1; queue.insert(0, (st, lang)); continue
            if e.code == 429:
                print('  분당 한도 → 60초 쉼', flush=True); time.sleep(60); queue.insert(0, (st, lang)); continue
            if e.code in (500, 503, 504):
                print(f'  {model} 일시 오류({e.code}) → 30초 뒤 다시', flush=True); time.sleep(30)
                fails[key] = fails.get(key, 0) + 1
                if fails[key] < 3: queue.insert(0, (st, lang))
                continue
            print(f'  {model} 사용 불가({e.code}) → 다음 모델', flush=True); mi += 1; queue.insert(0, (st, lang)); continue
        except (AttributeError, IndexError, TypeError) as e:
            ok, info = False, f'빈 응답 ({type(e).__name__})'
        if ok:
            for n in range(len(st['scenes'])):
                man[f'{key.split("/")[0]}/{n}/{lang}'] = {'model': model, 'voice': VOICE, 'sec': round(tts_split.duration(media_path(st['id'], n, lang)), 2)}
            save_manifest(man)
            done += 1
            print(f'[{done}] {key} 완료 — {info} ({model})', flush=True)
        else:
            fails[key] = fails.get(key, 0) + 1
            print(f'  ✗ {key} {info} ({model}) — {"나중에 다시" if fails[key] < 2 else "오늘은 건너뜀"}', flush=True)
            if fails[key] < 2: queue.append((st, lang))
        time.sleep(8)
    print('끝 — 이번에 만든 것', done, '개', flush=True)

def judge(client, f, want):
    q = ("Expected text of this audio clip:\n" + want + "\n\nDoes the clip say this text and nothing else? Ignore differences in writing system "
         "(kanji/kana, simplified spelling), punctuation, and how sound effects/onomatopoeia are spelled or stretched. "
         "Answer false only if words are missing, or extra words from another sentence are spoken at the start or end. "
         "Answer only JSON: {\"match\": true/false, \"extra\": \"...\", \"missing\": \"...\"}")
    for _ in range(3):
        try:
            r = client.models.generate_content(model=CHECK_MODEL, contents=[types.Part.from_bytes(data=f.read_bytes(), mime_type='audio/mp4'), q],
                                               config=types.GenerateContentConfig(response_mime_type='application/json'))
            j = json.loads(r.text)
            if not j.get('match'): print('   판단:', j, flush=True)
            return bool(j.get('match'))
        except errors.APIError as e:
            time.sleep(60 if e.code == 429 else 10)
        except Exception:
            time.sleep(3)
    return False

def verify(only_new=True):
    """잘린 장면 파일을 하나씩 받아써서 원문과 대조한다(앞뒤 장면 낱말이 붙어 들어가지 않았는지).
    통과하면 manifest에 ok를 남기고, 실패한 이야기·언어는 다시 자르게 표시한다."""
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    man = load_manifest()
    bad = set()
    for key in sorted(man):
        if only_new and man[key].get('ok'): continue
        sid, n, lang = key.split('/')
        st = next(x for x in STORIES if x['id'] == sid)
        f = media_path(sid, int(n), lang)
        if not f.exists(): continue
        want = st['scenes'][int(n)]['t'][lang]
        got = ''
        for _ in range(3):
            try:
                r = client.models.generate_content(model=CHECK_MODEL, contents=[types.Part.from_bytes(data=f.read_bytes(), mime_type='audio/mp4'),
                    'Transcribe exactly what is spoken, in the original language and script. Output only the transcript.'])
                got = r.text or ''; break
            except errors.APIError as e:
                time.sleep(60 if e.code == 429 else 10)
        a, b = norm(want), norm(got)
        sim = difflib.SequenceMatcher(None, a, b).ratio()
        # 받아쓰기는 한자·가나 표기가 원문과 달라질 수 있어(일본어·중국어) 길이 비율도 함께 본다
        longer = len(b) / max(1, len(a))
        ok = (sim >= 0.6 and longer <= 1.3) if lang in ('ja', 'zh') else (sim >= 0.8 and longer <= 1.2)
        if not ok:
            # 글자 대조가 어긋나도 한자/가나 표기나 의성어 표기 차이일 수 있다(실측: あつい→暑い, 휘이잉→휭).
            # 이때는 같은 내용인지, 앞뒤 장면 말이 붙거나 빠졌는지를 직접 판단하게 한다
            ok = judge(client, f, want)
        man[key]['ok'] = ok
        save_manifest(man)
        detail = '' if ok else f'\n   원문: {want}\n   음성: {got.strip()}'
        print(('✓' if ok else '✗'), key, f'{sim:.2f} x{longer:.2f}', detail, flush=True)
        if not ok: bad.add(f'{sid}/{lang}')
        time.sleep(2)
    print('확인 끝, 다시 볼 것:', sorted(bad) or '없음', flush=True)
    return bad

if __name__ == '__main__':
    if '--resplit' in sys.argv: resplit()
    elif '--verify' in sys.argv: verify(only_new='--all' not in sys.argv)
    else:
        generate(); resplit_failed = verify()
