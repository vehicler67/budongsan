#!/bin/bash
# ==============================================================
# 등기부등본 PDF → Excel 변환 (맥용 실행기)
# 사용법: 이 파일을 더블클릭하면 PDF 선택 → 자동 파싱 → Excel 열기
# ==============================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  등기부등본 PDF → Excel 변환 (Mac)"
echo "  HanaXellOcr0.7 대체 — parser_v7 기반"
echo "============================================"
echo ""

# PDF 선택 (osascript로 네이티브 파일 다이얼로그)
PDF_PATH=$(osascript -e '
set theFile to choose file of type "pdf" with prompt "등기부등본 PDF를 선택하세요:"
POSIX path of theFile
' 2>/dev/null)

if [ -z "$PDF_PATH" ]; then
    echo "취소되었습니다."
    exit 0
fi

echo "선택된 파일: $PDF_PATH"
echo ""
echo "OCR 파싱 시작..."
echo ""

# Python 파서 실행 (openpyxl로 xlsx 생성)
/usr/local/bin/python3 "$SCRIPT_DIR/parser_addin.py" "$PDF_PATH"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 오류가 발생했습니다."
    read -p "아무 키나 누르면 종료됩니다..."
    exit 1
fi

echo ""
echo "✅ 변환 완료!"
echo ""

# 결과 Excel 파일 열기
OUT_DIR="$SCRIPT_DIR/experiments"
PDF_NAME=$(basename "$PDF_PATH" .pdf)
XLSX_FILE="$OUT_DIR/addin_${PDF_NAME}.xlsx"

if [ -f "$XLSX_FILE" ]; then
    echo "Excel 파일 열기: $XLSX_FILE"
    open "$XLSX_FILE"
else
    echo "Excel 파일을 찾을 수 없습니다: $XLSX_FILE"
fi

echo ""
read -p "아무 키나 누르면 종료됩니다..."
