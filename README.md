# budongsan_test — PDF 파서 v7

> 등기부등본 PDF 발췌 자동화 프로젝트
> Git: https://github.com/vehicler67/budongsan

## 결과 요약

| 항목 | v7 성능 |
|------|---------|
| OCR 텍스트 정확도 | **99.0%** |
| 키워드 매칭 | **25/29 (86.2%)** |
| 감지된 섹션 | **4개** (표제부/매매목록/공동담보목록) |
| 감지된 표 영역 | **13개** (13페이지 PDF) |
| 20페이지 문서 | **지원** |

## 사용법

```bash
python3 parser_v7.py
```

출력: `experiments/v7_output.{md,json,xlsx}` + `v7_combined.txt`

## 개발 문서

- `wiki/백서_PDF파서_v7_재빌드_2026-06-14.md` — 전체 개발 과정
- `parser_v7.py` — 각주에 실패 사례 상세 기록
- `src_비교_수정할 참고용.md` — OCR 정확도 기준 파일
- `experiments/` — 실행 결과 파일

## 필요 패키지

```
pytesseract openpyxl PyMuPDF Pillow
tesseract (한글 언어팩: kor+eng)
```
