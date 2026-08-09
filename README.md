# 손가락 미로 탐험

유치원~초등학생을 위한 모바일 미로 게임입니다. 손가락으로 길을 따라 쭉 그으면서 출발점에서 도착점까지 이동합니다.

## 특징
- 테마 4종: 우주 🚀 · 바다 🐠 · 공룡 🦕 · 동물농장 🐮
- 난이도 6단계 (유치원 ~ 초등 고학년)
- 시간 제한 없음, 완료 기록은 별점(⭐)과 최고 기록으로 저장 (브라우저 localStorage)
- 칸 이동이 아닌 선형 드래그(터치) 방식으로 미로 통과
- 빌드 도구 없이 `index.html` 파일 하나로 동작

## 로컬에서 확인하기
`index.html` 파일을 더블클릭하거나, 모바일 화면 크기로 브라우저에서 열어 확인하세요.

## GitHub Pages로 배포하기
1. GitHub에 새 저장소를 만듭니다 (예: `maze-game`).
2. 이 폴더 내용을 저장소에 올립니다.

```bash
git init
git add index.html README.md
git commit -m "손가락 미로 탐험 게임 추가"
git branch -M main
git remote add origin https://github.com/<사용자명>/<저장소명>.git
git push -u origin main
```

3. GitHub 저장소 페이지에서 **Settings → Pages**로 이동합니다.
4. **Source**를 `main` 브랜치, 폴더는 `/ (root)`로 설정하고 저장합니다.
5. 잠시 후 `https://<사용자명>.github.io/<저장소명>/` 주소로 접속하면 게임이 실행됩니다.

## 커스터마이징
- `index.html` 안의 `THEMES` 배열에서 이모지/색상을 바꾸거나 테마를 추가할 수 있습니다.
- `LEVELS` 배열에서 각 단계의 미로 크기(`cols`, `rows`)를 조절해 난이도를 바꿀 수 있습니다.
