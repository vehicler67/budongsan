# 상용 OCR API 총정리 비교
상용 OCR API `Naver Clova OCR` vs `Google Vision API` 를 대상으로,  
한국어 문서·부동산등기부 등 **한글 PDF/이미지 OCR** 적용 적합성을 기준으로 정리한다.

## 1. 대상 서비스 개요
- **Naver Clova OCR**  
  네이버 클라우드 플랫폼 제공, 한국어 특화가 강점으로 알려짐. 문서·명함·영수증·일반 텍스트 등 여러 도메인을 제공.

- **Google Cloud Vision OCR**  
  Google Cloud 제공, 전 세계 언어 커버리지가 넓고 DOCUMENT_TEXT_DETECTION 으로 다량 텍스트 문서에 강함.

## 2. 가격 비교 (2026 기준 개요)
가격은 월별 사용량·리전·포렉식 등에 따라 변동이 크므로 정확한 단가는 각 포털 공식 문서로 확인하는 게 맞다.
여기서는 특징적인 구조만 정리한다.

- **Google Vision API**  
  - 무료 티어: 월 1,000 유닛까지 무료  
  - 유료: 1,000 유닛 초과부터 과금  
  - 다만 OCR 특정 기능에 따라 단가 차이가 있으므로 `TEXT_DETECTION` / `DOCUMENT_TEXT_DETECTION` 구분 필요  
  - 참고 페이지: https://cloud.google.com/vision/pricing

- **Naver Clova OCR**  
  - 종량제  
  - 한국어 인식 성능에 특화된 만큼 한글 문서 OCR 비용 대비 효율이 좋을 수 있음  
  - 정확한 요금표: https://www.ncloud.com/product/aiService/ocr

## 3. 인식 품질 비교
### 3.1 한국어 정확도
- **Clova OCR**: 한국어 커버리지가 매우 넓고, 실제 서비스를 통한 검증이 많음. 서식문서·양식 문서 인식에서 높은 평가.
- **Google Vision OCR**: 언어 지원은 50개 이상이지만, 한국어 특화 모델은 아님. 한글 문서에서 약간의 오인식이 보고됨.

### 3.2 문서/스캔 문서 OCR
- **Clova OCR**: 읽기 순서·방향 추정, 곡선 배열·기울인 글자·필기체 인식이 강점으로 소개됨.
- **Google Vision OCR**: `DOCUMENT_TEXT_DETECTION` 으로 복잡한 레이아웃에서 텍스트 덩어리 추출이 강함. 많은 페이지 문서에는 안정적.

### 3.3 속도
- **Clova OCR**: 평균 응답이 1~2초 대 (네이버 클라우드 리전 기준)
- **Google Vision OCR**: 벤치마크에 따라 다르나 일반적으로 수 초 내 응답

## 4. 개발·적용 측면
- **Clova OCR**  
  - 국내 서비스라 API 문서·지원이 한글로 되어 적용이 쉬움  
  - 네이버 클라우드 계정 필요

- **Google Vision OCR**  
  - 글로벌 서비스로 문서와 예제가 방대함  
  - GCP 프로젝트·결제 설정 필요  
  - 다양한 언어를 동시에 요청하기 좋음

## 5. budongsan 등기부 OCR 적용시 고려사항
- 핵심은 **한글 인식 정확도** 와 **양식 서식 구조 인식** 이다.
- Naver Clova OCR은 실제 한글 서식·부동산 문서에서 검증된 사례가 많을 가능성이 높다.
- Google Vision OCR은 문서 구조가 복잡한 20~30page 대용량 PDF를 레이아웃 단위로 처리하기에 검증된 안정성이 있음.

## 6. 결론 및 추천 방향
- **1순위**: `Naver Clova OCR` 을 기본으로 시도. 한국어 특화 성능이 가장 중요할 때 유리하다.
- **2순위**: 정확도 만족이 어렵거나 비용이 크면 `Google Vision OCR` 으로 전환 검토.
- **추가**: 두 API를 실제 샘플 1~2page 로 직접 테스트해 정확도·응답속도·가성비를 검증하는 게 가장 빠른 판단 기준이다.

---
작성일: 2026-06-12  
작성자: 한과장 (국인)
