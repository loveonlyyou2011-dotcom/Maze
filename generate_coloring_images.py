"""색칠놀이용 코로링북 이미지를 Gemini API(gemini-3.1-flash-lite-image)로 일괄 생성한다.

사용법:
    python generate_coloring_images.py 동물              # 동물 카테고리만
    python generate_coloring_images.py 동물 바다생물       # 여러 카테고리
    python generate_coloring_images.py --all             # 전체 10개 카테고리(240장)

이미 생성된 파일(coloring/카테고리_이름.png)이 있으면 건너뛰므로, 중간에 실패해도
같은 명령을 다시 실행하면 이어서 생성된다.
"""
import os
import sys
import time
import base64
import json
import pathlib
import requests

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise SystemExit("환경변수 GEMINI_API_KEY가 설정되어 있지 않습니다.")

MODEL = "gemini-3.1-flash-lite-image"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

TEMPLATE = (
    "Children's coloring book page, black and white line art only. "
    "Subject: a single cute, friendly {subject}, centered on the page, "
    "simple rounded cartoon style for kindergarten and elementary school kids. "
    "Thick, smooth, fully closed black outlines with no gaps. No shading, no gradients, "
    "no crosshatching, no color, no background scene — plain white background only. "
    "Large clean shapes, minimal small details, not scary or realistic. Square 1:1 composition."
)

# 카테고리 하나를 통째로 한 장에 담는 프롬프트 (항목별 개별 생성 대신 사용)
CATEGORY_TEMPLATE = (
    "Children's coloring book page, black and white line art only. "
    "Show {count} different {theme} items neatly arranged in a clean grid layout, evenly spaced, "
    "one per cell, not overlapping: {item_list}. "
    "Each item drawn in a simple, rounded cartoon style for kindergarten and elementary school kids, "
    "with its own thick, smooth, fully closed black outline. No shading, no gradients, no crosshatching, "
    "no color, no background scene, no scene composition — plain white background only. "
    "Large clean shapes, minimal small details, not scary or realistic. Square 1:1 composition."
)

CATEGORY_THEMES = {
    "바다생물": "sea creature",
    "공룡": "dinosaur",
    "교통수단": "vehicle",
    "과일": "fruit",
    "채소": "vegetable",
    "곤충": "insect",
    "우주": "space object",
    "꽃과 식물": "flower or plant",
    "학용품·장난감": "school supply or toy",
}

# (한글 이름, 영어 프롬프트용 이름)
CATEGORIES = {
    "동물": [
        ("강아지", "dog"), ("고양이", "cat"), ("토끼", "rabbit"), ("곰", "bear"), ("사자", "lion"), ("호랑이", "tiger"),
        ("코끼리", "elephant"), ("기린", "giraffe"), ("원숭이", "monkey"), ("판다", "panda"), ("코알라", "koala"), ("여우", "fox"),
        ("늑대", "wolf"), ("다람쥐", "squirrel"), ("사슴", "deer"), ("캥거루", "kangaroo"), ("하마", "hippo"), ("코뿔소", "rhinoceros"),
        ("얼룩말", "zebra"), ("양", "sheep"), ("염소", "goat"), ("소", "cow"), ("말", "horse"), ("돼지", "pig"),
    ],
    "바다생물": [
        ("물고기", "fish"), ("상어", "shark"), ("돌고래", "dolphin"), ("고래", "whale"), ("문어", "octopus"), ("오징어", "squid"),
        ("게", "crab"), ("새우", "shrimp"), ("불가사리", "starfish"), ("해파리", "jellyfish"), ("바다거북", "sea turtle"), ("가오리", "stingray"),
        ("복어", "pufferfish"), ("흰동가리", "clownfish"), ("해마", "seahorse"), ("랍스터", "lobster"), ("조개", "clam"), ("소라", "conch shell"),
        ("펭귄", "penguin"), ("물개", "seal"), ("바다사자", "sea lion"), ("수달", "otter"), ("산호", "coral"), ("나비고기", "butterflyfish"),
    ],
    "공룡": [
        ("티라노사우루스", "T-Rex dinosaur"), ("트리케라톱스", "Triceratops dinosaur"), ("브라키오사우루스", "Brachiosaurus dinosaur"), ("스테고사우루스", "Stegosaurus dinosaur"),
        ("벨로키랍토르", "Velociraptor dinosaur"), ("프테라노돈", "Pteranodon dinosaur"), ("안킬로사우루스", "Ankylosaurus dinosaur"), ("파라사우롤로푸스", "Parasaurolophus dinosaur"),
        ("딜로포사우루스", "Dilophosaurus dinosaur"), ("스피노사우루스", "Spinosaurus dinosaur"), ("이구아노돈", "Iguanodon dinosaur"), ("디플로도쿠스", "Diplodocus dinosaur"),
        ("알로사우루스", "Allosaurus dinosaur"), ("카르노타우루스", "Carnotaurus dinosaur"), ("아파토사우루스", "Apatosaurus dinosaur"), ("케찰코아틀루스", "Quetzalcoatlus dinosaur"),
        ("마이아사우라", "Maiasaura dinosaur"), ("코리토사우루스", "Corythosaurus dinosaur"), ("오비랍토르", "Oviraptor dinosaur"), ("파키케팔로사우루스", "Pachycephalosaurus dinosaur"),
        ("프테로닥틸루스", "Pterodactyl dinosaur"), ("엘라스모사우루스", "Elasmosaurus dinosaur"), ("테리지노사우루스", "Therizinosaurus dinosaur"), ("공룡 알", "dinosaur egg"),
    ],
    "교통수단": [
        ("자동차", "car"), ("버스", "bus"), ("택시", "taxi"), ("소방차", "fire truck"), ("구급차", "ambulance"), ("경찰차", "police car"),
        ("트럭", "truck"), ("오토바이", "motorcycle"), ("자전거", "bicycle"), ("기차", "train"), ("지하철", "subway train"), ("비행기", "airplane"),
        ("헬리콥터", "helicopter"), ("배", "boat"), ("요트", "yacht"), ("잠수함", "submarine"), ("로켓", "rocket"), ("열기구", "hot air balloon"),
        ("트랙터", "tractor"), ("굴착기", "excavator"), ("레미콘", "cement mixer truck"), ("스쿨버스", "school bus"), ("견인차", "tow truck"), ("유조선", "tanker ship"),
    ],
    "과일": [
        ("사과", "apple"), ("바나나", "banana"), ("딸기", "strawberry"), ("포도", "grapes"), ("수박", "watermelon"), ("오렌지", "orange"),
        ("레몬", "lemon"), ("파인애플", "pineapple"), ("복숭아", "peach"), ("배", "pear"), ("자두", "plum"), ("체리", "cherries"),
        ("키위", "kiwi fruit"), ("망고", "mango"), ("멜론", "melon"), ("석류", "pomegranate"), ("감", "persimmon"), ("무화과", "fig"),
        ("블루베리", "blueberries"), ("코코넛", "coconut"), ("아보카도", "avocado"), ("귤", "tangerine"), ("용과", "dragon fruit"), ("파파야", "papaya"),
    ],
    "채소": [
        ("당근", "carrot"), ("감자", "potato"), ("고구마", "sweet potato"), ("양파", "onion"), ("마늘", "garlic"), ("토마토", "tomato"),
        ("오이", "cucumber"), ("가지", "eggplant"), ("호박", "pumpkin"), ("브로콜리", "broccoli"), ("양배추", "cabbage"), ("배추", "napa cabbage"),
        ("상추", "lettuce"), ("시금치", "spinach"), ("파", "green onion"), ("무", "radish"), ("옥수수", "corn"), ("피망", "bell pepper"),
        ("고추", "chili pepper"), ("콩", "beans"), ("완두콩", "peas"), ("버섯", "mushroom"), ("연근", "lotus root"), ("우엉", "burdock root"),
    ],
    "곤충": [
        ("나비", "butterfly"), ("벌", "bee"), ("무당벌레", "ladybug"), ("개미", "ant"), ("잠자리", "dragonfly"), ("딱정벌레", "beetle"),
        ("사슴벌레", "stag beetle"), ("장수풍뎅이", "rhinoceros beetle"), ("메뚜기", "grasshopper"), ("귀뚜라미", "cricket"), ("매미", "cicada"), ("거미", "spider"),
        ("지네", "centipede"), ("달팽이", "snail"), ("반딧불이", "firefly"), ("파리", "fly"), ("애벌레", "caterpillar"), ("사마귀", "praying mantis"),
        ("나방", "moth"), ("하늘소", "longhorn beetle"), ("물방개", "diving beetle"), ("소금쟁이", "water strider"), ("집게벌레", "earwig"), ("꿀벌집", "beehive"),
    ],
    "우주": [
        ("로켓", "rocket ship"), ("우주선", "spaceship"), ("우주비행사", "astronaut"), ("태양", "sun"), ("달", "moon"), ("지구", "planet Earth"),
        ("화성", "planet Mars"), ("토성", "planet Saturn with rings"), ("목성", "planet Jupiter"), ("금성", "planet Venus"), ("수성", "planet Mercury"), ("천왕성", "planet Uranus"),
        ("해왕성", "planet Neptune"), ("별", "star"), ("별자리", "constellation"), ("혜성", "comet"), ("인공위성", "satellite"), ("우주정거장", "space station"),
        ("UFO", "UFO flying saucer"), ("외계인", "friendly alien"), ("망원경", "telescope"), ("우주복", "space suit helmet"), ("은하", "galaxy"), ("운석", "meteor"),
    ],
    "꽃과 식물": [
        ("장미", "rose flower"), ("해바라기", "sunflower"), ("튤립", "tulip flower"), ("벚꽃", "cherry blossom"), ("코스모스", "cosmos flower"), ("나팔꽃", "morning glory flower"),
        ("무궁화", "rose of sharon flower"), ("데이지", "daisy flower"), ("카네이션", "carnation flower"), ("국화", "chrysanthemum flower"), ("민들레", "dandelion flower"), ("진달래", "azalea flower"),
        ("연꽃", "lotus flower"), ("수선화", "daffodil flower"), ("라벤더", "lavender flower"), ("선인장", "cactus"), ("나무", "tree"), ("새싹", "sprout"),
        ("잎사귀", "leaf"), ("클로버", "clover"), ("대나무", "bamboo"), ("야자수", "palm tree"), ("화분", "potted plant"), ("이끼", "moss"),
    ],
    "학용품·장난감": [
        ("연필", "pencil"), ("지우개", "eraser"), ("크레파스", "crayon"), ("가위", "scissors"), ("풀", "glue stick"), ("색종이", "origami paper"),
        ("책", "book"), ("가방", "backpack"), ("필통", "pencil case"), ("자", "ruler"), ("시계", "clock"), ("공", "ball"),
        ("풍선", "balloon"), ("블록", "building blocks"), ("인형", "doll"), ("곰인형", "teddy bear"), ("팽이", "spinning top toy"), ("로봇 장난감", "toy robot"),
        ("자동차 장난감", "toy car"), ("기차 장난감", "toy train"), ("연", "kite"), ("비눗방울", "bubbles"), ("퍼즐", "jigsaw puzzle"), ("그림책", "picture book"),
    ],
}

OUT_DIR = pathlib.Path(__file__).parent / "coloring"
OUT_DIR.mkdir(exist_ok=True)


def generate_image(prompt):
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    resp = requests.post(
        ENDPOINT,
        params={"key": API_KEY},
        headers={"Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"응답에 candidates가 없습니다: {data}")
    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])
    raise RuntimeError(f"응답에 이미지 데이터가 없습니다: {data}")


def safe_filename(category, ko):
    name = f"{category}_{ko}".replace("/", "-").replace("\\", "-")
    return name + ".png"


def run(category_names):
    log = []
    total = sum(len(CATEGORIES[c]) for c in category_names)
    done = 0
    for cat in category_names:
        items = CATEGORIES[cat]
        for ko, en in items:
            done += 1
            out_path = OUT_DIR / safe_filename(cat, ko)
            prefix = f"[{done}/{total}]"
            if out_path.exists():
                print(f"{prefix} 건너뜀 (이미 있음): {out_path.name}")
                continue
            prompt = TEMPLATE.format(subject=en)
            print(f"{prefix} 생성 중: {cat} / {ko} ({en}) ...")
            try:
                img_bytes = generate_image(prompt)
                out_path.write_bytes(img_bytes)
                print(f"    저장됨: {out_path.name} ({len(img_bytes)} bytes)")
                log.append({"category": cat, "ko": ko, "en": en, "status": "ok", "file": out_path.name})
            except Exception as e:
                print(f"    실패: {e}")
                log.append({"category": cat, "ko": ko, "en": en, "status": "error", "error": str(e)})
            time.sleep(1.2)  # API 속도 제한을 배려

    log_path = OUT_DIR / "_generation_log.json"
    existing_log = []
    if log_path.exists():
        try:
            existing_log = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            existing_log = []
    existing_log.extend(log)
    log_path.write_text(json.dumps(existing_log, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_count = sum(1 for l in log if l["status"] == "ok")
    err_count = sum(1 for l in log if l["status"] == "error")
    skipped = total - len(log)
    print(f"\n완료. 성공 {ok_count}개, 실패 {err_count}개, 건너뜀 {skipped}개. 로그: {log_path}")


def run_category_sheets(category_names):
    """카테고리 하나당 이미지 한 장에 전체 항목을 몰아서 그린다 (개별 생성 대신)."""
    log = []
    for cat in category_names:
        if cat == "동물":
            print("동물 카테고리는 제외합니다.")
            continue
        items = CATEGORIES[cat]
        theme = CATEGORY_THEMES.get(cat, cat)
        item_list = ", ".join(en for _, en in items)
        out_path = OUT_DIR / f"{cat}_전체.png"
        if out_path.exists():
            print(f"건너뜀 (이미 있음): {out_path.name}")
            continue
        prompt = CATEGORY_TEMPLATE.format(count=len(items), theme=theme, item_list=item_list)
        print(f"생성 중: {cat} (항목 {len(items)}개 한 장에) ...")
        try:
            img_bytes = generate_image(prompt)
            out_path.write_bytes(img_bytes)
            print(f"    저장됨: {out_path.name} ({len(img_bytes)} bytes)")
            log.append({"category": cat, "status": "ok", "file": out_path.name, "item_count": len(items)})
        except Exception as e:
            print(f"    실패: {e}")
            log.append({"category": cat, "status": "error", "error": str(e)})
        time.sleep(1.2)

    log_path = OUT_DIR / "_generation_log.json"
    existing_log = []
    if log_path.exists():
        try:
            existing_log = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            existing_log = []
    existing_log.extend(log)
    log_path.write_text(json.dumps(existing_log, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_count = sum(1 for l in log if l["status"] == "ok")
    err_count = sum(1 for l in log if l["status"] == "error")
    print(f"\n완료. 성공 {ok_count}개, 실패 {err_count}개. 로그: {log_path}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("사용법:")
        print("  python generate_coloring_images.py <카테고리...>        # 항목별 개별 이미지")
        print("  python generate_coloring_images.py --all                # 전체 카테고리, 항목별 개별 이미지")
        print("  python generate_coloring_images.py --sheets             # 동물 제외 나머지 카테고리, 카테고리당 1장")
        print("  python generate_coloring_images.py --sheets 바다생물 공룡  # 지정한 카테고리만 1장씩")
        print("사용 가능한 카테고리:", ", ".join(CATEGORIES.keys()))
        sys.exit(1)
    if args[0] == "--sheets":
        rest = args[1:]
        cats = rest if rest else [c for c in CATEGORIES.keys() if c != "동물"]
        unknown = [a for a in cats if a not in CATEGORIES]
        if unknown:
            print("알 수 없는 카테고리:", unknown)
            sys.exit(1)
        run_category_sheets(cats)
    elif args == ["--all"]:
        run(list(CATEGORIES.keys()))
    else:
        unknown = [a for a in args if a not in CATEGORIES]
        if unknown:
            print("알 수 없는 카테고리:", unknown)
            print("사용 가능한 카테고리:", ", ".join(CATEGORIES.keys()))
            sys.exit(1)
        run(args)
