# 등기부변환기

PDF 등기부등본 → Excel / CSV 자동 변환  
외부 API 없음 · 완전 로컬 · macOS M1/M2/M4 / Intel / Windows

## 버전 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|-----------|
| v1.0.3 | 2026-04 | 요약 갑구/을구 컬럼 분리 정확화, PDF 진단 로그 |
| v1.0.2 | 2026-04 | 매매/공동담보목록 목록번호 행 구분, 요약 소유지분 분리 |
| v1.0.1 | 2026-04 | A열 공백 여백, 자동줄바꿈 적용 |
| v1.0.0 | 2026-04 | 초기 릴리스 |

## 실행
```
실행.command 더블클릭
```
또는
```bash
python3 build.py   # .app 번들 빌드
```

## 파일 구성
- `src/app.py` — GUI 메인
- `src/parser.py` — PDF 파싱 엔진
- `src/exporter.py` — Excel/CSV 출력
- `src/make_icon.py` — 앱 아이콘
- `src/build.py` — 빌드 스크립트
