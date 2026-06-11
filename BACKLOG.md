# budongsan_test 진행 백서
버전: v0.1 (초기 진행)
날짜: 2026-06-12

## 배경
- 부동산등기부등본 PDF 발췌 자동화 프로젝트
- 기존 VB 확장플러그인 소스 확보, 파이썬 포팅 시도 중
- PDF 내 CID 폰트 문제로 일반 텍스트 추출 불가

## 진행 이력
1. oletools로 xlam 매크로 추출 시도 → 암호화/컴파일 상태로 실패
2. pdfplumber로 텍스트 추출 → CID 코드만 인식, 한글 불가
3. PaddleOCR 테스트 → 환경 이슈 + 메모리 부족으로 실패
4. Tesseract OCR 테스트 → 1페이지 75~80% 정확도 확인
5. pdfplumber 표 좌표 기반 영역 crop 시도 → 표 구조 단독 인식은 한계
6. 전체 페이지 기반 OCR + 정제 규칙 적용 → 핵심 필드 90% 인식 확인
7. pdfplumber extract_table() 테스트 → CID 텍스트라 구조만 있고 내용 불가

## 현재 산출물
- PDF: 2849-2018-019318_25696174641_RIS.pdf
- 참고: src_비교_수정할 참고용.md, src_비교_수정할 참고용.xlsx
- OCR 결과: phase2_ocr_result.md, phase2_ocr_cleaned.md, phase2_hybrid_result.md
- 파서: parser.py (v2)
- 파싱 산출물: phase2_parsed.md, phase2_parsed.json
- 이미지: phase2_page1_300dpi.png, phase2_page1_150dpi.png, phase2_page1_prepared.png
- 타일: phase2_tiles/*.png

## 추가 필요 작업
- Tesseract 정제 규칙 보강으로 정확도 95% 이상 목표
- 2페이지 이후 페이지 처리
- Excel 출력 기능 추가
- 테스트 자동화
