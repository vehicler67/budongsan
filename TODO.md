# budongsan_test 작업 계획서

기준일: 2026-06-12
프로젝트: 부동산등기부등본 PDF 발췌 자동화
위치: /Volumes/T7/내 드라이브/myvolt/HanManager/AI-Sessions/raw/budongsan_test
참고: wiki/sources/2026-06-11-pdf-document-parsing-tech-reference.md
      wiki/sources/2026-06-11-pdf-land-registry-parsing-research.md

---

## 1. 현재 위치 확정 (변경 금지)

- 원본 Desktop 위치는 삭제 / 이동 완료.
- 기준 경로: `AI-Sessions/raw/budongsan_test`
- 이 계획서도 동일 폴더에 둔다. 이 폴더를 벗어나는 작업은 규정 위반.

---

## 2. 업데이트 규칙

1. 작업 시작 전 이 계획서 하단 `작업 로그`에 시작 기록을 남긴다.
2. 단계 완료 후 상태를 `대기` → `완료`로 바꾼다.
3. 새 아이디어나 이슈는 `메모`에만 기록하고, 계획 흐름은 바꾸지 않는다.
4. 원본 샘플 삭제는 최종 단계에서만 허용한다.

---

## 3. Phase별 실행 계획

### Phase 1: 기존 VB 알고리즘 역공학 (1~2일)
- 대상: `HanaXellOcr0.7_fixed.xlam`, `src_비교_수정할 참고용.xlsx`, `output.xlsx`
- 작업:
  - 매크로 코드 열거 및 흐름 파악
  - 표 인식 → 셀 분할 → 필드 매칭 → Excel 출력 단계 추출
  - 정확도가 높은 부분/낮은 부분 색적
- 산출: `phase1_vb_algo_notes.md`
- **검증 기준**:
  - 역공학 노트의 흐름도가 실제 xlam 실행 결과와 일치하는지 확인
  - output.xlsx와 비교해서 알고리즘 단계별 출력이 맞는지 검증
- 상태: 진행 중

### Phase 2: CID 폰트 대응 전략 확정 (1일)
- 대상: `2849-2018-019318_25696174641_RIS.pdf`
- 작업:
  - pdfplumber / PyMuPDF로 직접 텍스트 추출 비교
  - CID 깨짐 구간 샘플링
  - 렌더링 이미지 OCR 엔진 평가 (PaddleOCR / EasyOCR)
  - 각 엔진별 정확도 측정 (정밀도/재현율)
- 산출: `phase2_cid_strategy.md`
- **검증 기준**:
  - OCR 결과가 `src_비교_수정할 참고용.md` 내용과 최대한 일치하는지 샘플 3페이지 검증
  - 깨진 텍스트 비율 < 5% 목표
- 상태: 대기

### Phase 3: 하이브리드 파이프라인 PoC (2~3일)
- 작업:
  - PDF → PNG 렌더링 (300 DPI)
  - PaddleOCR 좌표 기반 텍스트 박스 추출
  - pdfplumber 텍스트 레이어 병합
  - 깨진 영역만 OCR로 대체하는 분기 로직
- 산출: `parser.py`, 테스트 결과 비교표
- **검증 기준**:
  - parser.py 출력이 `src_비교_수정할 참고용.md`와 90% 이상 일치
  - 문서 구조가 원본 PDF와 95% 이상 일치 (좌표·셀 병합 보존율)
- 상태: 대기

### Phase 4: 구조 정제·내보내기 (2~3일)
- 작업:
  - 좌표 기반 병합셀 복원
  - 헤더-바디 매핑 규칙 구현
  - Markdown / Excel / JSON 동시 내보내기 기능
- 산출: `exporter.py`, `output_test.xlsx`
- **검증 기준**:
  - output_test.xlsx와 output.xlsx의 셀별 비교 → 98% 이상 일치
  - 구조 일치율 100% 목표
- 상태: 대기

### Phase 5: 통합 테스트·최적화 (1~2일)
- 작업:
  - 20~30장 batch 처리 테스트
  - LLM 후처리(정확도 보정) 제한 적용
  - 토큰 사용량 측정·최적화
- 산출: `phase5_test_report.md`
- **검증 기준**:
  - 전체 문서 OCR 정확도 95% 이상
  - 구조 보존율 100%
  - LlamaIndex LiteParse와의 정확도 비교 문서 포함
- 상태: 대기

---

## 4. 사용 도구·의사결정

- 기본 언어: Python
- 레이아웃: pdfplumber 우선, Docling/LiteParse 평가용으로 병행
- OCR: PaddleOCR (한글 강점)
- 후처리 정제: LLM 최소 호출 (전체 텍스트 일괄 전송 금지)
- 저장 형식: 단일 결과물 원칙 (중간 TIFF page별 생성 금지)

---

## 5. 위험요소·주의

- CID 폰트는 100% 복원 불가능할 수 있음 → 우회 전략 병행 필수
- VB 알고리즘 없이 독자 개발 시 정확도 하락 가능성 큼
- 토큰 사용량 급증 방지: 큰 파일 전체를 LLM에 넣지 않는다
- 원본 PDF는 최종 검증 완료 전 삭제 금지

---

## 6. 작업 로그

### 2026-06-12
- 계획서 초안 작성 (한과장)
- Phase 1 시작 대기 중
- 목표 명확화:
  - OCR 정확도 기준: `src_비교_수정할 참고용.md` 100%
  - 구조 보존 기준: 원본 PDF 2849-2018-019318_25696174641_RIS.pdf 100%

---

## 7. 메모

- 형님 지적: "품질 향상은 쉽지 않다, 학습과 계획이 우선이다"
- 현재 `output.xlsx`가 정확도 기준점이다.
- VB 소스코드 상태 불확실 → 우선 확보가 최우선
- 싱크로율 검증을 매 Phase마다 실행하여 품질 게이트 확보
