"""coloring/ 폴더의 시트 기반 이미지들을, 원본 시트에서 격자선(테두리)과 라벨 텍스트를
확실히 제외하고 다시 정밀하게 잘라 덮어쓴다.

각 항목이 원본 시트의 어느 칸(row,col)에서 왔는지는 이번 세션에서 직접 눈으로 확인하며
정리했던 매핑을 그대로 사용한다(자동 매칭 없음 - 오매칭 위험을 없애기 위함).
"""
import os
import numpy as np
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE, "image")
COLORING_DIR = os.path.join(BASE, "coloring")


def find_bands(frac, thresh=0.7):
    bands = []
    in_band = False
    start = 0
    for i, f in enumerate(frac):
        if f > thresh and not in_band:
            in_band = True
            start = i
        elif f <= thresh and in_band:
            in_band = False
            bands.append((start, i - 1))
    if in_band:
        bands.append((start, len(frac) - 1))
    return bands


def snap_positions(bands, expected, total):
    """감지된 격자선(bands)을 등간격 기준 위치에 최대한 가깝게 매칭하고,
    빠진 자리는 이웃한 확정 위치로부터 보간한다."""
    centers = [(b[0] + b[1]) / 2 for b in bands]
    prior_step = total / (expected - 1)
    slots = [None] * expected
    for center in centers:
        idx = round(center / prior_step)
        idx = max(0, min(expected - 1, idx))
        # 같은 자리에 이미 배정된 값이 있으면 prior에 더 가까운 쪽을 채택
        if slots[idx] is None or abs(center - idx * prior_step) < abs(slots[idx] - idx * prior_step):
            slots[idx] = center
    # 빈 자리는 확정된 이웃들 사이를 선형 보간(또는 바깥쪽은 등간격으로 외삽)
    known_idx = [i for i, v in enumerate(slots) if v is not None]
    for i in range(expected):
        if slots[i] is not None:
            continue
        left = max([k for k in known_idx if k < i], default=None)
        right = min([k for k in known_idx if k > i], default=None)
        if left is not None and right is not None:
            slots[i] = slots[left] + (slots[right] - slots[left]) * (i - left) / (right - left)
        elif left is not None:
            slots[i] = slots[left] + (i - left) * prior_step
        elif right is not None:
            slots[i] = slots[right] - (right - i) * prior_step
        else:
            slots[i] = i * prior_step
    return slots


def detect_lines(sheet_gray, cols, rows):
    """격자선 위치를 감지. 부족하면 등간격 추정치로 보완한다."""
    arr = np.array(sheet_gray)
    H, W = arr.shape
    dark = arr < 210
    rbands = find_bands(dark.mean(axis=1))
    cbands = find_bands(dark.mean(axis=0))

    row_lines = snap_positions(rbands, rows + 1, H)
    col_lines = snap_positions(cbands, cols + 1, W)
    return row_lines, col_lines


def find_icon_bottom(gray_arr, top, bottom, left, right):
    """셀 안에서 그림(아이콘) 내용이 끝나는 y좌표를 찾는다.
    시트는 보통 [그림] - [빈 공백] - [라벨 텍스트] - [빈 여백] 순서라서,
    내용이 있는 구간 다음에 나오는 첫 '연속된 공백 구간'을 그림의 아래쪽 경계로 본다."""
    sub = gray_arr[top:bottom, left:right] < 210
    row_frac = sub.mean(axis=1)
    NOISE = 0.02
    MIN_GAP = 6
    started = False
    blank_run = 0
    for i, f in enumerate(row_frac):
        is_content = f > NOISE
        if is_content:
            if blank_run >= MIN_GAP and started:
                return top + i - blank_run
            started = True
            blank_run = 0
        else:
            if started:
                blank_run += 1
    return bottom  # 못 찾으면 원래 경계 그대로


def crop_cell(sheet_rgb, sheet_gray_arr, row_lines, col_lines, r, c, pad=10, has_label=False):
    top = row_lines[r] + pad
    bottom = row_lines[r + 1] - pad
    left = col_lines[c] + pad
    right = col_lines[c + 1] - pad
    if has_label:
        icon_bottom = find_icon_bottom(sheet_gray_arr, int(top), int(bottom), int(left), int(right))
        bottom = min(bottom, icon_bottom + 4)
    left, top, right, bottom = int(left), int(top), int(right), int(bottom)
    if right <= left or bottom <= top:
        raise ValueError(f"bad box {(left, top, right, bottom)}")
    cell = sheet_rgb.crop((left, top, right, bottom))
    arr = np.array(cell)
    BORDER = 3
    arr[:BORDER, :, :] = 255
    arr[-BORDER:, :, :] = 255
    arr[:, :BORDER, :] = 255
    arr[:, -BORDER:, :] = 255
    return Image.fromarray(arr)


def process(cat, filename, cols, rows, mapping, has_label=False):
    path = os.path.join(IMAGE_DIR, filename)
    sheet_rgb = Image.open(path).convert("RGB")
    sheet_gray = sheet_rgb.convert("L")
    sheet_gray_arr = np.array(sheet_gray)
    row_lines, col_lines = detect_lines(sheet_gray, cols, rows)

    saved = 0
    for (r, c), name in mapping.items():
        cell = crop_cell(sheet_rgb, sheet_gray_arr, row_lines, col_lines, r, c, pad=10, has_label=has_label)
        out_path = os.path.join(COLORING_DIR, f"{cat}_{name}.png")
        cell.save(out_path)
        saved += 1
    print(cat, "saved", saved)


# ---------------------------------------------------------------------
# 각 시트의 (row, col) -> 항목 이름 매핑 (이번 세션에서 직접 확인한 내용)
# ---------------------------------------------------------------------

SEA = {
    (0,0):'물고기', (0,1):'상어', (0,2):'돌고래', (0,3):'고래', (0,4):'오징어',
    (1,0):'게', (1,1):'새우', (1,2):'불가사리', (1,3):'해파리', (1,4):'바다거북',
    (2,0):'복어', (2,1):'흰동가리', (2,2):'해마', (2,3):'랍스터', (2,4):'가오리',
    (3,1):'물개', (3,2):'바다사자', (3,3):'조개', (3,4):'소라',
    (4,0):'펭귄', (4,2):'수달', (4,3):'산호', (4,4):'나비고기',
}

DINO = {
    (0,0):'티라노사우루스', (0,1):'트리케라톱스', (0,2):'브라키오사우루스', (0,3):'스테고사우루스', (0,4):'벨로키랍토르',
    (1,0):'안킬로사우루스', (1,1):'파라사우롤로푸스', (1,2):'딜로포사우루스', (1,3):'스피노사우루스', (1,4):'이구아노돈',
    (2,0):'알로사우루스', (2,1):'카르노타우루스', (2,2):'아파토사우루스', (2,3):'프테라노돈', (2,4):'디플로도쿠스',
    (3,0):'마이아사우라', (3,1):'코리토사우루스', (3,2):'프테로닥틸루스', (3,3):'오비랍토르', (3,4):'파키케팔로사우루스',
    (4,0):'테리지노사우루스', (4,2):'엘라스모사우루스', (4,4):'공룡 알',
}

VEHICLE = {
    (0,0):'자동차', (0,1):'버스', (0,2):'택시', (0,3):'소방차', (0,4):'구급차',
    (1,0):'트럭', (1,1):'오토바이', (1,2):'자전거', (1,3):'기차', (1,4):'경찰차',
    (2,3):'지하철', (2,4):'비행기',
    (3,0):'헬리콥터', (3,1):'배', (3,2):'요트', (3,3):'잠수함',
    (4,3):'로켓', (4,4):'열기구',
    (5,0):'트랙터', (5,1):'굴착기', (5,2):'레미콘', (5,3):'견인차', (5,4):'유조선',
}

FRUIT = {
    (0,0):'사과', (0,1):'바나나', (0,2):'딸기', (0,3):'포도', (0,4):'오렌지',
    (1,0):'레몬', (1,1):'파인애플', (1,2):'복숭아', (1,3):'배', (1,4):'자두',
    (2,0):'키위', (2,1):'망고', (2,2):'멜론', (2,3):'석류', (2,4):'체리',
    (3,0):'귤', (3,3):'감', (3,4):'무화과',
    (4,0):'블루베리', (4,1):'코코넛', (4,2):'아보카도', (4,3):'용과', (4,4):'파파야',
}

VEG_ROWS = [
    ['당근','감자','고구마','양파','마늘','토마토'],
    ['오이','가지','호박','브로콜리','양배추','배추'],
    ['상추','시금치','파','무','옥수수','피망'],
    ['고추','콩','완두콩','버섯','연근','우엉'],
]
VEG = {(r, c): name for r, row in enumerate(VEG_ROWS) for c, name in enumerate(row)}

INSECT = {
    (0,0):'나비', (0,1):'벌', (0,2):'무당벌레', (0,3):'개미', (0,4):'잠자리',
    (1,0):'사슴벌레', (1,1):'장수풍뎅이', (1,2):'메뚜기', (1,3):'귀뚜라미', (1,4):'매미',
    (2,0):'지네', (2,1):'달팽이', (2,2):'반딧불이', (2,3):'파리', (2,4):'거미',
    (3,0):'나방', (3,1):'하늘소', (3,2):'딱정벌레', (3,3):'애벌레', (3,4):'사마귀',
    (4,1):'물방개', (4,3):'집게벌레', (4,4):'꿀벌집',
}

SPACE_ROWS = [
    ['로켓','우주선','우주비행사','태양','달','지구'],
    ['화성','토성','목성','금성','수성','천왕성'],
    ['해왕성','별','별자리','혜성','인공위성','우주정거장'],
    ['UFO','외계인','망원경','우주복','은하','운석'],
]
SPACE = {(r, c): name for r, row in enumerate(SPACE_ROWS) for c, name in enumerate(row)}

FLOWER_ROWS = [
    ['장미','해바라기','튤립','벚꽃','코스모스','나팔꽃'],
    ['무궁화','데이지','카네이션','국화','민들레','진달래'],
    ['연꽃','수선화','라벤더','선인장','나무','새싹'],
    ['잎사귀','클로버','대나무','야자수','화분','이끼'],
]
FLOWER = {(r, c): name for r, row in enumerate(FLOWER_ROWS) for c, name in enumerate(row)}

SUPPLY_ROWS = [
    ['연필','지우개','크레파스','가위','풀','색종이'],
    ['책','가방','필통','자','시계','공'],
    ['풍선','블록','인형','곰인형','팽이','로봇장난감'],
    ['자동차장난감','기차장난감','연','비눗방울','퍼즐','그림책'],
]
SUPPLY = {(r, c): name for r, row in enumerate(SUPPLY_ROWS) for c, name in enumerate(row)}


if __name__ == "__main__":
    process("바다생물", "Generated Image August 16, 2026 - 6_54PM.jpg", 5, 5, SEA)
    process("공룡", "Generated Image August 16, 2026 - 6_56PM.jpg", 5, 5, DINO)
    process("교통수단", "Generated Image August 16, 2026 - 7_07PM.jpg", 5, 6, VEHICLE, has_label=True)
    process("과일", "Generated Image August 16, 2026 - 7_08PM.jpg", 5, 5, FRUIT)
    process("채소", "Generated Image August 16, 2026 - 7_09PM.jpg", 6, 4, VEG, has_label=True)
    process("곤충", "Generated Image August 16, 2026 - 7_11PM.jpg", 5, 5, INSECT)
    process("우주", "Generated Image August 16, 2026 - 7_41PM.jpg", 6, 4, SPACE, has_label=True)
    process("꽃과식물", "Generated Image August 16, 2026 - 7_13PM.jpg", 6, 4, FLOWER, has_label=True)
    process("학용품장난감", "Generated Image August 16, 2026 - 7_14PM.jpg", 6, 4, SUPPLY, has_label=True)
    print("done")
