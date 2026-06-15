#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  등기부등본 PDF 발췌 v7 — 수동 실행기 (Mac)                   ║
# ║  더블클릭 → PDF 선택 → MD/JSON/Excel/TXT 자동 생성             ║
# ╚══════════════════════════════════════════════════════════════╝
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║    등기부등본 PDF 발췌 v7 (99.0% 정확도)                ║"
echo "  ║    제1 도구 — MD/JSON/Excel/TXT 출력                   ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""

# PDF 선택
PDF=$(osascript -e '
set theFile to choose file of type "pdf" with prompt "등기부등본 PDF를 선택하세요:"
POSIX path of theFile
' 2>/dev/null)

if [ -z "$PDF" ]; then
    echo "취소되었습니다."
    read -p "아무 키나 누르면 종료됩니다..."
    exit 0
fi

echo "선택: $(basename "$PDF")"
echo ""

# v7 파서 실행
/usr/local/bin/python3 -c "
import sys; sys.path.insert(0, '$SCRIPT_DIR')
from pathlib import Path
from parser_v7 import run
run(Path('$PDF'))
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 완료! 결과는 experiments/ 폴더를 확인하세요."
    open "$SCRIPT_DIR/experiments"
fi

echo ""
read -p "아무 키나 누르면 종료됩니다..."
