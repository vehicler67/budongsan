# PDF 파싱·OCR·문서 자동화 기술 백서 (통합 최종)
작성일: 2026-06-12
프로젝트: budongsan_test (부동산등기부등본 PDF 발췌 자동화)
상태: 조사 완료 + 실행 경험 통합

---

# PDF 파싱·OCR·문서 자동화 기술 백서

작성일: 2026-06-11
프로젝트: budongsan_test (부동산등기부등본 PDF 발췌 자동화)
관리자: 한과장 (국인)
상태: 학습/조사 완료, 실행 대기

---

## 1. 문서 자동화 전체 맥락

### 1.1 문제 정의
- **대상 문서**: 한국 등기부등본 PDF
  - 고정 양식이지만 실제로는 여러 레이어가 혼합된 구조
  - CID 폰트(CFF/CID-Keyed Font) 사용으로 일반 텍스트 추출 불가
  - 표·격자·병합셀이 복잡하게 얽힌 레이아웃
- **목표**:
  - 원본 구조(표 위치, 셀 병합, 헤더/바디 구분)를 최대한 보존
  - 텍스트·표·격자를 구조화된 데이터(Excel/Markdown/JSON)로 변환
  - 자동화 파이프라인 구축: PDF → (전처리) → OCR/파싱 → 구조화 → 저장

### 1.2 현재 상태
- 기존 VB 확장플러그인(`HanaXellOcr0.7_fixed.xlam`)으로 PDF → Excel 변환 성공
  - 소스 공개 문의 중 연락 두절 → 원본 알고리즘 코드 보유 불확실
  - 형님께서 보유한 `output.xlsx`, `src_비교_*.xlsx`가 현재 가장 정확도 높은 레퍼런스
- Python 포팅 시도:
  - Gemini/Claude/Codex에게 위임 → 성실하지 못해 결과물 품질 낮음
  - `parser.py`, `exporter.py` 빌드 테스트 완료 (PDF→Excel 성공)
  - **핵심 미해결**: CID 폰트 PDF 텍스트 깨짐, OCR 정제 부족

### 1.3 작업 연습 원칙
- **산출물 최소화**: 불필요한 중간 파일(page별 TIFF, 템포러리 로그 등) 생성 금지
- 단일 결과물: `채판_all.tiff` (단일 멀티페이지 TIFF) + `채판_요약.md`
- 원본 PDF 삭제는 명시적 승인 후에만 실행

---

## 2. PDF 파싱 기법 분류

### 2.1 텍스트 기반 추출 (하드 파싱)
- PDF 내부 텍스트 레이어를 직접 읽어오는 방식
- 장점: 빠름, 원본 글자 그대로 보존
- 단점: CID 폰트·이미지 폰트에서 깨짐, 레이아웃 무시
- 대표 도구:
  - **PyMuPDF (fitz)**: C 기반 빠른 추출, 한국어 CID에서 자주 깨짐
  - **pypdf / pypdfium2**: 순수 파이썬, 안전하나 포맷 보존 약함
  - **pdfplumber**: 표 추출에 강함 (라인/컬럼 경계 탐지)

### 2.2 이미지 기반 OCR (소프트 파싱)
- PDF 페이지를 이미지로 렌더링 후 OCR로 텍스트 읽기
- 장점: CID 폰트 문제 해결, 스캔본도 처리 가능
- 단점: 처리 시간 김, 레이아웃 구조가 텍스트만 나옴
- 대표 도구:
  - **Tesseract OCR**: 오픈소스 표준, 한국어 `kor.traineddata` 필요
  - **EasyOCR**: 딥러닝 기반, 한국어 지원
  - **PaddleOCR**: 바이두 오픈소스, 한글 인식률 좋음
  - **한국딥러닝 DEEP OCR+**: 상용, 한국 정형 문서 특화

### 2.3 레이아웃/구조 인식 (지능 파싱)
- 문서를 시각적으로 분석하여 표·단락·제목·이미지 등을 **객체 단위로 분할**
- 장점: 격자 구조·병합셀·다중컬럼 보존
- 단점: 오픈소스는 GPU 권장, 설정 복잡
- 대표 도구:
  - **Docling** (IBM): 오픈소스, 테이블/수식/이미지 분할, Markdown/JSON 내보내기
  - **Marker**: GPU 가속, PDF→Markdown 고속 변환
  - **MinerU**: 다중 엔진 통합 (YOLO + PaddleOCR +叔叔)
  - **LiteParse** (LlamaIndex, 2026.03): 공간 좌표 기반 Grid Projection, 로컬·무료·GPU불필요
  - **Unstructured.io**: API/셀프호스트, 여러 파서 백엔드 통합

### 2.4 하이브리드 파이프라인
- 여러 기법을 조합하여 문서 특성에 맞게 처리
- 예: PyMuPDF로 텍스트 읽기 + Docling으로 표 보완 + Tesseract로 이미지 영역 OCR
- 프로덕션 환경에서 가장 많이 쓰이는 패턴

---

## 3. 등기부등본에 특화된 문제점과 대응

### 3.1 CID 폰트 문제
- **원인**: 등기부등본 PDF는 보통 CID(Character Identifier) 폰트를 사용
  - 글자 코드가 실제 Unicode와 매핑되지 않아 `pdftotext`, `PyMuPDF` 등에서 깨짐
  - 예: `(cid:123)` 형태로 출력되거나 전혀 다른 글자로 대체됨
- **대응 전략**:
  1. **우회**: PDF 페이지를 이미지로 렌더링 → GPU OCR (PaddleOCR/EasyOCR)
  2. **후처리**: OCR 결과를 LLM에 넣어 한글 오타·띄어쓰기·숫자 오인 정정
  3. **혼합**: 텍스트 레이어 정상 부분은 그대로 쓰고, 깨진 영역만 이미지 OCR로 보완

### 3.2 격자/표 구조 보존
- 등기부등본은 "토지·건물" 항목이 각각 **표 형태**로 되어 있고, 셀 병합·다중 헤더가 많음
- 단순 텍스트 추출 시 컬럼 구분이 사라져 의미를 잃음
- **필수 요구사항**:
  - 각 셀의 좌표(x, y) + 병합 영역 정보 보존
  - 헤더 행의 계층 구조(parent/child) 인식
  - 페이지 단위가 아니라 문서 전체 단위로 테이블 연결

### 3.3 한글·전문 인식 정확도
- 등기 용어는 일반 한글과 다름 (권리관계, 주소, 지번 등)
- 숫자·한글 혼합 구간에서 OCR이 자주 혼동:
  - "전용면적 84.59㎡" → "84.59m²" 또는 "84,59"
  - "지상 7층" → "지상7층" 띄어쓰기 문제
- **개선 방안**:
  - 도메인 사전 구축 (등기 용어 JSON)
  - LLM 후처리: `<전문>` + `<후보>` 형태로 검증 요청
  - 정규식으로 확정 패턴(지번, 동, 호수) 보정

---

## 4. 오픈소스 도구 비교

### 4.1 추출 엔진 비교
| 도구 | 언어 | 하드/소프트 | 레이아웃 | 테이블 | 한국어 | GPU | 비고 |
|------|------|-------------|----------|--------|--------|-----|------|
| PyMuPDF | C/Python | 하드 | 보통 | 보통 | ★★ | 불필요 | 빠름, CID 깨짐 |
| pdfplumber | Python | 하드 | 양호 | ★★★ | ★★★ | 불필요 | 표 강점 |
| Camelot | Python | 하드 | 한정 | ★★★ | ★★ | 불필요 | Java 의존 |
| Tabula | Java | 하드 | 한정 | ★★★ | ★★ | 불필요 | 스트림·래트 |
| Tesseract | C++ | 소프트 | 없음 | 없음 | ★★★ | 권장 | 한국어 팩 설치 필요 |
| EasyOCR | Python | 소프트 | 없음 | 없음 | ★★★ | 권장 | 설치 간편 |
| PaddleOCR | Python | 소프트 | 없음 | 없음 | ★★★★ | 권장 | 한글 인식률 좋음 |
| Docling | Python | 하이브리드 | ★★★★ | ★★★★ | ★★★ | 권장 | IBM, RAG용 |
| Marker | Python | 하이브리드 | ★★★ | ★★★ | ★★★ | 권장 | GPU가속 |
| LiteParse | TS/Python | 하이브리드 | ★★★★ | ★★★ | ★★★ | 불필요 | 2026.03 신규 |
| MinerU | Python | 하이브리드 | ★★★★ | ★★★★ | ★★★ | 권장 | 다중백엔드 |
| Unstructured | Python | 하이브리드 | ★★★ | ★★★ | ★★★ | 옵션 | API/셀프호스트 |

### 4.2 선택 가이드
- **테이블·격자 구조를 정확히**: Docling, LiteParse, MinerU
- **한국어 인식 정확도 최우선**: PaddleOCR + LLM 후처리
- **빠른 프로토타이핑**: pdfplumber + Tesseract (GPU 없이)
- **프로덕션 RAG**: Docling + Unstructured API
- **토큰 비용 절감**: LiteParse (로컬, 모델 불필요)

---

## 5. 상용·한국형 솔루션

### 5.1 DEEP OCR+ (한국딥러닝)
- 특화: 한국 정형·반정형 문서 OCR
- 기능:
  - 문서 시각 구조 + 언어 맥락 통합 해석
  - 금융권 여신서류 자동화 적용 사례 (2025~2026)
- 적용: 금융, 법률, 공공
- 한계: 상용 라이선스, 자체 호스트 불가 (SaaS/온프레미스 계약 필요)

### 5.2 등기브리핑 AI
- 기능: 등기부등본 PDF 업로드 → 권리관계 브리핑 자동 생성
- 출력: Markdown/HTML 형태의 읽기 쉬운 보고서
- 한계: 원본 구조 Excel 변환까지는 지원하지 않을 수 있음 (확인 필요)

### 5.3 위시켓 유사사례
- "등기부등본 파싱 프로그램": 지번주소/부동산번호 입력 → 대장 발급 → PDF 저장 → DB 파싱
- 참고: `https://www.wishket.com/project/similar-case-search/share/YaeaLMk0pcpYREmy/`

---

## 6. RAG·LLM 연계 파이프라인

### 6.1 일반 파이프라인
```
PDF → (렌더링) → OCR/파싱 → (청킹) → 임베딩 → Vector DB → LLM 검색
```

### 6.2 핵심 고려사항
- **청킹 전략**: 테이블 전체를 하나의 청크로 유지해야 함
  - 문장 단위/고정 길이 청크는 표 구조를 파괴
  - Docling/MinerU는 Markdown 테이블로 내보내므로 LLM이 이해하기 좋음
- **메타데이터 보존**: 페이지 번호, 좌표, 원본 링크를 함께 저장
- **재구성 vs 원본 보존**:
  - 재구성: Markdown/HTML로 사람이 읽기 좋게 변환
  - 원본 보존: JSON으로 x, y, width, height, text 모두 저장

### 6.3 추천 스택 (2026 기준)
| 용도 | 추천 도구 |
|------|-----------|
| 구조 보존 파싱 | Docling / LiteParse |
| 한국어 OCR | PaddleOCR / EasyOCR |
| 후처리 정제 | LLM (Claude/GPT/로컬LLM) |
| 저장 형식 | Markdown + JSON (병행) |
| 검색/QA | LanceDB / Chroma + RAG |

---

## 7. 등기부등본 자동화 로드맵

### Phase 1: 알고리즘 역공학 (1~2일)
- `HanaXellOcr0.7_fixed.xlam` 매크로 분석
- `src_비교_*.xlsx`, `output.xlsx` 비교 → 실제 적용 알고리즘 추론
- 목표: VB 코드의 표 인식·셀 매핑·필드 매칭 로직 이해

### Phase 2: 하이브리드 파이프라인 설계 (2~3일)
- 해상도 300 DPI로 PDF → PNG 렌더링
- PaddleOCR로 텍스트 박스 + 좌표 추출
- 동일 영역에 대해 pdfplumber로 텍스트 레이어도 함께 추출
- 충돌/깨짐 영역은 OCR 결과로 대체

### Phase 3: 구조 정제 (2~3일)
- 병합셀 영역 복원: 좌표 기반 병합 규칙 재구성
- 헤더-바디 매핑: 키워드 + 위치 기반으로 컬럼 헤더 찾기
- LLM으로 레이블 보정: "이 Cell은 '소유자' 컬럼입니다" 식의 검증

### Phase 4: 빌드·테스트 (1~2일)
- parser.py (이미지 렌더링 + OCR) 완성
- exporter.py (Excel/JSON/Markdown 변환) 완성
- `output.xlsx`와 정확도 비교 (정밀도/재현율 측정)

### Phase 5: 최적화 (지속)
- 토큰 사용량 최소화 (LLM 호출 줄이기)
- 20~30장 batch 처리 안정화
- CID 케이스 자동 감지 → 우회 전략 자동 선택

---

## 8. 참고 자료

### 논문·벤치마크
- arXiv 2603.18652v1: Benchmarking PDF Parsers on Table Extraction with LLM-based Semantic Evaluation
- arXiv 2410.09871v1: A Comparative Study of PDF Parsing Tools Across Diverse Document Categories
- Nature Sci Rep 16, 14954 (2026): SPARTAN - OpenCV + OCR 표 추출
- CVPR 2025: OmniDocBench benchmark

### 오픈소스
- LiteParse: `https://github.com/run-llama/liteparse`
- Docling: `https://github.com/docling-project/docling`
- Marker: `https://github.com/...` (조사 중)
- MinerU: `https://github.com/opendatalab/...` (조사 중)
- Unstructured: `https://github.com/Unstructured-IO/unstructured`
- pdfplumber: `https://github.com/jsvine/pdfplumber`
- Camelot: `https://camelot-py.readthedocs.io`
- PaddleOCR: `https://github.com/PaddlePaddle/PaddleOCR`

### 아티클·블로그
- LlamaIndex "Best AI for PDF Table Extraction (2026)"
- Firecrawl "Best PDF Parsers for AI and RAG Workflows in 2026"
- Medium "I Tested 7 Python PDF Extractors (2025 Edition)"
- Lido "PDF Parsing Techniques: A Complete Guide for 2026"
- NVIDIA Developer "Approaches to PDF Data Extraction for Information Retrieval"

### 한국어 자료
- 한국딥러닝 DEEP OCR+: `https://www.koreadeep.com/blog/category/ai-case`
- "등기부등본도 AI가 읽고 판단한다" (매일경제 2025.06.02)
- 위시켓 유사사례: 등기부등본 파싱 프로그램
- Tesseract + LLM OCR 보정: `https://news.hada.io/topic?id=16253`

---

## 9. 현재 프로젝트 위치

### 산출물
- `/Users/byeolgalam/Desktop/budongsan_test` 원본은 **이동 완료**
- 현재 위치: `/Volumes/T7/내 드라이브/myvolt/HanManager/AI-Sessions/raw/budongsan_test/`

### 파일 목록
1. `2849-2018-019318_25696174641_RIS.pdf` — 테스트 샘플 등기부등본
2. `HanaXellOcr0.7_fixed.xlam` — VB 확장플러그인 (알고리즘 레퍼런스)
3. `output.xlsx` — 현재 최고 정확도 결과물
4. `src_비교_수정할 참고용.xlsx` — 비교 원본
5. `src_비교_수정할 참고용.md` — 비교 설명
6. `등기부변환기_v1.0.2_src_*.xlsx` — 버전 관리된 소스

### 다음 실행 우선순위
1. 파일 2, 4, 5 분석 → 알고리즘 로드맵 작성
2. CID 폰트 감지 로직 추가
3. PaddleOCR + pdfplumber 하이브리드 파이프라인 PoC
4. `output.xlsx`와 정확도 비교

---

## 10. 메모

- 형님 지적: "품질 향상이 어려운 작업" → 추가 기술 학습 + 아이디어 + 고도 계획 필수
- 만만하게 접근하지 말 것. 실행보다 학습·분석 우선.
- 토큰 급증을 막기 위해 대화 컨텍스트를 체계적으로 기록.
- 이 문서는 총체적 지식 베이스로 활용.


---

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


---

## 부록: Git 저장소 위치

- `https://github.com/vehicler67/budongsan`
- 브랜치: `ocr-phase2`
- 루트 파일: `2026-06-12-pdf-document-parsing-tech-reference.md`
- 산출물: `parser.py`, `BACKLOG.md`, `TODO.md`, `experiments/pdf_multi.*`
