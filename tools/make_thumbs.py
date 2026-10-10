# 색칠놀이 동물 선그림(.jpg)은 1000px·한 장 200KB 안팎이라 24장을 한꺼번에 띄우는 목록·그림자 찾기에는 무겁다.
# 320px(한 장 15KB 안팎) 작은 그림을 thumbs/ 에 만들어 두고 목록·그림자 찾기에서는 이것을 쓴다 (색칠 화면은 원본).
# 다른 카테고리 선그림(.png)은 이미 170px 안팎이라 그대로 쓴다.
import pathlib
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parent.parent
dst = ROOT / 'thumbs'; dst.mkdir(exist_ok=True)
n = 0
for f in sorted((ROOT / 'coloring').glob('동물_*.jpg')):
    im = Image.open(f).convert('RGB'); im.thumbnail((320, 320), Image.LANCZOS)
    im.save(dst / f.name, 'JPEG', quality=82, optimize=True); n += 1
print('썸네일', n, '장')
