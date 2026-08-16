"""한 장에 여러 항목이 격자로 들어있는 이미지를 항목별로 잘라서 개별 파일로 저장한다.

사용법 (코드 맨 아래 CATEGORY_SHEETS에 항목을 추가한 뒤):
    python split_category_sheet.py 바다생물

격자 칸 수(cols, rows)와 항목 순서(왼쪽→오른쪽, 위→아래)는 실제 이미지를 보고
CATEGORY_SHEETS에 직접 지정해야 한다. 이미지에 여백이 있으면 margin으로 보정한다.
"""
import sys
import pathlib
from PIL import Image

BASE_DIR = pathlib.Path(__file__).parent
COLORING_DIR = BASE_DIR / "coloring"
COLORING_DIR.mkdir(exist_ok=True)

# category -> {"file": 원본 시트 이미지 경로, "cols": 열 수, "rows": 행 수,
#              "items": [항목 순서(왼쪽->오른쪽, 위->아래)], "margin": 바깥 여백 비율(0~1, 선택)}
CATEGORY_SHEETS = {
    # 예시. 실제 파일을 받으면 여기에 채운다.
    # "바다생물": {
    #     "file": BASE_DIR / "image" / "sea_sheet.jpg",
    #     "cols": 6, "rows": 4,
    #     "items": ["물고기","상어","돌고래","고래","문어","오징어",
    #               "게","새우","불가사리","해파리","바다거북","가오리",
    #               "복어","흰동가리","해마","랍스터","조개","소라",
    #               "펭귄","물개","바다사자","수달","산호","나비고기"],
    # },
}


def split_sheet(category):
    spec = CATEGORY_SHEETS[category]
    img = Image.open(spec["file"])
    W, H = img.size
    cols, rows = spec["cols"], spec["rows"]
    items = spec["items"]
    if len(items) != cols * rows:
        print(f"경고: 항목 수({len(items)})가 격자 칸 수({cols*rows})와 다릅니다.")

    margin = spec.get("margin", 0.0)
    mx, my = int(W * margin), int(H * margin)
    usable_w, usable_h = W - 2 * mx, H - 2 * my
    cell_w, cell_h = usable_w / cols, usable_h / rows

    saved = 0
    for idx, name in enumerate(items):
        r, c = divmod(idx, cols)
        left = mx + c * cell_w
        top = my + r * cell_h
        box = (int(left), int(top), int(left + cell_w), int(top + cell_h))
        cell_img = img.crop(box)
        out_path = COLORING_DIR / f"{category}_{name}.png"
        cell_img.save(out_path)
        print(f"저장됨: {out_path.name}  (영역 {box})")
        saved += 1
    print(f"\n완료: {saved}개 저장")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CATEGORY_SHEETS:
        print("사용법: python split_category_sheet.py <카테고리명>")
        print("등록된 카테고리:", ", ".join(CATEGORY_SHEETS.keys()) or "(없음 - 먼저 CATEGORY_SHEETS를 채워주세요)")
        sys.exit(1)
    split_sheet(sys.argv[1])
