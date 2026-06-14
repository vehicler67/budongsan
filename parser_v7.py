#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
budongsan_test PDF parser v7 (simplified)
OCR 전용 + CID 폰트 공백 정제 + 등기부등본 구조 파싱
목표: src_비교_수정할 참고용.md 대비 텍스트 100% + PDF 구조 100% 재현
"""

import re, json, sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import fitz
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

BASE = Path('/Volumes/T7/내 드라이브/myvolt/HanManager/AI-Sessions/raw/budongsan_test')
PDF_DEFAULT = BASE / '2849-2018-019318_25696174641_RIS.pdf'
GROUND_TRUTH = BASE / 'src_비교_수정할 참고용.md'
OUT_DIR = BASE / 'experiments'
OUT_DIR.mkdir(exist_ok=True)

# ====================================================================
# 1. 등기용어 교정 사전
# ====================================================================

TERM_REPLACE = {
    # CID 폰트 공백 포함 + 일반 표기
    '【 표 제 부 】': '【표제부】', '【 표제부 】': '【표제부】',
    '【 갑 구 】': '【갑구】', '【 갑구 】': '【갑구】',
    '【 을 구 】': '【을구】', '【 을구 】': '【을구】',
    '【 매 매 목 록 】': '【매매목록】', '【 매매목록 】': '【매매목록】',
    '【 공 동 담 보 목 록 】': '【공동담보목록】',
    '고 유 번 호': '고유번호', '소 재 지': '소재지',
    '부 동 산 종 류': '부동산종류', '열 람 일 시': '열람일시',
    '현 황': '현황', '소 유 권 이 전': '소유권이전',
    '근 저 당 권 설 정': '근저당권설정', '지 상 권 설 정': '지상권설정',
    '가 압 류': '가압류', '임 의 경 매 개 시 결 정': '임의경매개시결정',
    '매 매 목 록': '매매목록', '공 동 담 보 목 록': '공동담보목록',
    '등 기 사 항 전 부 증 명 서': '등기사항전부증명서',
    # 【 대신 [ 로 시작하는 경우
    '[표제부】': '【표제부】', '[갑구】': '【갑구】',
    '[을구】': '【을구】', '[매매목록】': '【매매목록】',
    '[공동담보목록】': '【공동담보목록】',
    '[ 토 지]': '[토지]', '[ 토 지 ]': '[토지]',
}

# ====================================================================
# 2. 정규식 패턴
# ====================================================================

PATTERNS = {
    'date': re.compile(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일'),
    'time': re.compile(r'(\d{1,2})\s*시\s*(\d{1,2})\s*분\s*(\d{1,2})\s*초'),
    'regno': re.compile(r'제\s*(\d{3,7})\s*호'),
    'money': re.compile(r'금\s*([\d,]+)\s*원'),
    'address': re.compile(r'(경\s*기\s*도|파\s*주\s*시|파\s*평\s*면|마\s*산\s*리|문\s*산\s*읍|사\s*임\s*당\s*로)'),
    'court': re.compile(r'(의\s*정\s*부\s*지\s*방\s*법\s*원|고\s*양\s*지\s*원|파\s*주\s*등\s*기\s*소)'),
    # OCR 노이즈 (영문+특수문자 패턴)
    'ocr_noise': re.compile(r'[@|)(A-Za-z0-9._#\-]{3,}(?:\s*[@|)(A-Za-z0-9._#\-]{1,})*'),
    # 한글 띄어쓰기 (CID 폰트)
    'hangul_spaces': re.compile(r'(?<=[가-힣0-9]) +(?=[가-힣])'),
    'digit_spaces': re.compile(r'(?<=\d) +(?=\d)'),
}

# ====================================================================
# 3. 섹션 헤더 목록
# ====================================================================

SECTION_KEYS = [
    '【표제부】', '【갑구】', '【을구】',
    '【매매목록】', '【공동담보목록】',
    '소유지분현황', '기본정보',
]

# ====================================================================
# 4. PDF → OCR 처리
# ====================================================================

def render_page(pdf_path, page_num, dpi=400):
    """단일 페이지를 이미지로 렌더링"""
    doc = fitz.open(str(pdf_path))
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = doc[page_num].get_pixmap(matrix=mat)
    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples).convert('L')
    doc.close()
    return img

def ocr_image(img):
    """이미지 OCR 처리 (전처리 포함)"""
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.point(lambda x: 0 if x < 175 else 255)
    return pytesseract.image_to_string(img, lang='kor+eng')

# ====================================================================
# 5. CID 폰트 정제 엔진
# ====================================================================

def fix_cid_spacing(text):
    """CID 폰트로 인한 한글/숫자 사이 공백 제거"""
    # "고 유 번 호 2849-2018-019318" → "고유번호 2849-2018-019318"
    # 1차: 한글 연속 사이 공백 제거
    text = re.sub(r'(?<=[가-힣0-9]) +(?=[가-힣])', '', text)
    # 2차: 한글-숫자 사이 공백 제거
    text = re.sub(r'(?<=[가-힣]) +(?=\d)', '', text)
    # 3차: 기호 주변 공백 제거
    for ch in '【】()[]':
        text = text.replace(f'{ch} ', ch)
        text = text.replace(f' {ch}', ch)
    # 4차: "제  107414  호" → "제107414호"
    text = re.sub(r'(?<=\d) +(?=\d)', '', text)
    return text

def fix_date(text):
    """날짜 포맷 통일"""
    def _fix(m):
        return f'{m.group(1)}년{m.group(2).zfill(2)}월{m.group(3).zfill(2)}일'
    return PATTERNS['date'].sub(_fix, text)

def fix_regno(text):
    """등기번호 포맷 통일"""
    def _fix(m):
        return f'제{m.group(1)}호'
    return PATTERNS['regno'].sub(_fix, text)

def fix_money(text):
    """금액 포맷 통일"""
    def _fix(m):
        return f'금{m.group(1)}원'
    return PATTERNS['money'].sub(_fix, text)

def fix_address(text):
    """주소 연속 공백 제거 (CID)"""
    def _fix(m):
        return m.group(0).replace(' ', '')
    return PATTERNS['address'].sub(_fix, text)

def fix_court(text):
    """법원명 연속 공백 제거 (CID)"""
    def _fix(m):
        return m.group(0).replace(' ', '')
    return PATTERNS['court'].sub(_fix, text)

def remove_ocr_noise(text):
    """OCR 노이즈 제거 (보수적)"""
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 진짜 노이즈만 제거: 특수문자+영문만 있고 의미 없는 줄
        if re.match(r'^[\s@|)(\-_.,:;!?\[\]{}#*※%\'\"ㅣ]+$', line):
            continue
        # 【, 【, 숫자, 한글이 포함된 줄은 보존
        # 내부 특수문자 정리
        line = line.replace('ㅣ', '|').replace('｜', '|').replace('∣', '|')
        line = re.sub(r'[\u2500-\u257F]', '', line)  # box drawing 제거
        line = re.sub(r'\s*[|]\s*', ' | ', line)  # 파이프 정리
        # 연속 공백 제거
        line = re.sub(r' +', ' ', line)
        if line:
            lines.append(line)
    return '\n'.join(lines)

def clean_text(text):
    """전체 정제 파이프라인"""
    text = text.replace('\r', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    # 1) CID 공백 정제
    text = fix_cid_spacing(text)

    # 2) 등기용어 교정
    for old, new in TERM_REPLACE.items():
        text = text.replace(old, new)

    # 3) 날짜/번호/금액/주소/법원 정제
    text = fix_date(text)
    text = fix_regno(text)
    text = fix_money(text)
    text = fix_address(text)
    text = fix_court(text)

    # 4) OCR 노이즈 제거
    text = remove_ocr_noise(text)

    # 5) 한글 또는 중요 데이터가 포함된 라인 보존
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.search(r'[가-힣]', line) or \
           re.search(r'\d{4}', line) or \
           re.search(r'금[\d,]+원', line) or \
           any(kw in line for kw in SECTION_KEYS + ['순위번호', '등기목적', '접수']) or \
           re.match(r'[\[【]', line):
            lines.append(line)

    # 6) 중복 제거
    seen = []
    for line in lines:
        if line not in seen:
            seen.append(line)

    return '\n'.join(seen)

# ====================================================================
# 6. 섹션 파서
# ====================================================================

def parse_sections(text):
    """등기부등본 섹션 자동 분할"""
    sections = {'raw': text, 'sections': {}}
    lines = text.split('\n')

    current_section = '__header__'
    sections['sections'][current_section] = []

    for line in lines:
        matched = None
        for key in SECTION_KEYS:
            if key in line:
                matched = key
                break
        if matched:
            current_section = matched
            sections['sections'][current_section] = []
        else:
            sections['sections'][current_section].append(line)

    # 빈 섹션 제거
    sections['sections'] = {k: v for k, v in sections['sections'].items() if v}
    return sections

# ====================================================================
# 7. 정확도 검증
# ====================================================================

def validate_accuracy(extracted_text, gt_text):
    """src_비교 기준 대비 정확도 측정"""
    if not gt_text:
        return {"error": "기준 파일 없음", "accuracy": 0.0}

    # 중요 키워드 목록
    keywords = [
        '고유번호', '2849-2018-019318', '소재지', '경기도 파주시 파평면 마산리 113-2',
        '토지', '열람일시', '2026년03월31일', '표제부', '갑구', '을구',
        '소유권이전', '근저당권설정', '지상권설정', '가압류', '임의경매개시결정',
        '이순옥', '강성원', '최영호', '이은', '파주농업협동조합', '북파주농업협동조합',
        '매매목록', '공동담보목록', '의정부지방법원', '고양지원', '파주등기소',
        '채권최고액', '금266,000,000원', '금221,000,000원',
    ]

    matched = 0
    for kw in keywords:
        if kw in extracted_text and kw in gt_text:
            matched += 1

    # 문자 정확도
    gt_clean = re.sub(r'\s+', '', gt_text)
    ex_clean = re.sub(r'\s+', '', extracted_text)
    common = sum(1 for c in gt_clean if c in ex_clean)
    char_acc = round(common / max(len(gt_clean), 1) * 100, 2)

    return {
        "char_accuracy_pct": char_acc,
        "keyword_matches": f"{matched}/{len(keywords)}",
        "keyword_pct": round(matched / len(keywords) * 100, 2),
    }

# ====================================================================
# 8. 출력 포맷
# ====================================================================

def save_markdown(sections, label='v7'):
    path = OUT_DIR / f'{label}_output.md'
    lines = ['# 등기부등본 파싱 결과 (v7)\n']
    for name, content in sections['sections'].items():
        lines.append(f'\n## {name}\n')
        lines.extend(content)
    path.write_text('\n'.join(lines), encoding='utf-8')
    return str(path)

def save_json(data, label='v7'):
    path = OUT_DIR / f'{label}_output.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(path)

def save_excel(sections, label='v7'):
    wb = Workbook()
    ws = wb.active
    ws.title = '전체'
    row = 1
    for name, content in sections['sections'].items():
        ws.cell(row=row, column=1, value=f'[{name}]').font = Font(bold=True, size=12)
        row += 1
        for line in content:
            ws.cell(row=row, column=1, value=line)
            row += 1
        row += 1
    path = OUT_DIR / f'{label}_output.xlsx'
    wb.save(str(path))
    return str(path)

# ====================================================================
# 9. 메인
# ====================================================================

def run(pdf_path=PDF_DEFAULT, label='v7', max_pages=None):
    print(f'[v7] {pdf_path.name} 파싱 시작...')

    # 기준 파일 로드
    gt_text = GROUND_TRUTH.read_text(encoding='utf-8') if GROUND_TRUTH.exists() else ''
    print(f'  기준 파일: {GROUND_TRUTH.name} ({len(gt_text)}자)')

    # OCR 추출
    doc = fitz.open(str(pdf_path))
    total = len(doc)
    pages_to_process = range(total) if max_pages is None else range(min(max_pages, total))

    all_raw = []
    for i in pages_to_process:
        img = render_page(pdf_path, i, dpi=400)
        raw = ocr_image(img)
        all_raw.append(raw)
        print(f'  페이지 {i+1}/{total} OCR 완료 ({len(raw)}자)')
    doc.close()

    # 병합 및 정제
    combined_raw = '\n\n'.join(all_raw)
    cleaned = clean_text(combined_raw)
    print(f'  정제 완료: {len(cleaned)}자 (원본 {len(combined_raw)}자)')

    # 섹션 파싱
    sections = parse_sections(cleaned)
    print(f'  감지된 섹션: {list(sections["sections"].keys())}')

    # 정확도 검증
    accuracy = validate_accuracy(cleaned, gt_text)
    print(f'  문자 정확도: {accuracy.get("char_accuracy_pct", 0):.1f}%')
    print(f'  키워드 매칭: {accuracy.get("keyword_matches", "N/A")}')

    # 출력 저장
    md_path = save_markdown(sections, label)
    json_path = save_json({
        'source': str(pdf_path),
        'pages': len(all_raw),
        'raw_text': combined_raw,
        'cleaned_text': cleaned,
        'sections': sections['sections'],
        'accuracy': accuracy,
    }, label)
    xlsx_path = save_excel(sections, label)

    # combined 텍스트 저장
    (OUT_DIR / f'{label}_combined.txt').write_text(cleaned, encoding='utf-8')

    print(f'\n  출력:')
    print(f'    Markdown: {md_path}')
    print(f'    JSON: {json_path}')
    print(f'    Excel: {xlsx_path}')
    print(f'    TXT: {OUT_DIR / f"{label}_combined.txt"}')

    print(f'\n{"="*50}')
    print(f'  정확도: {accuracy.get("char_accuracy_pct", 0):.1f}% / 키워드: {accuracy.get("keyword_matches", "N/A")}')
    print(f'{"="*50}')
    return accuracy

if __name__ == '__main__':
    run()
