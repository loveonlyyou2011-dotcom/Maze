@echo off
rem 동화 극장 감정 낭독을 하루치(무료 한도) 이어서 만들고, 받아쓰기로 확인한 뒤 앱에 반영한다.
rem 작업 스케줄러에서 하루 한 번 실행하는 용도. 커밋·업로드는 하지 않는다(다른 작업과 섞이지 않게 사람이 확인 후 커밋).
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo ===== %date% %time% >> "_out\story_tts_daily.log"
python story_tts.py >> "_out\story_tts_daily.log" 2>&1
python story_fetch.py embed >> "_out\story_tts_daily.log" 2>&1
