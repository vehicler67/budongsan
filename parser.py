#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
budongsan_test PDF parser (v2)
전체 페이지 300 DPI OCR + 정제 중심
"""
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import re
import json

BASE = Path('/Volumes/T7/내 드라이브/myvolt/HanManager/AI-Sessions/raw/budongsan_test')
PDF_DEFAULT = BASE / '2849-2018-019318_25696174641_RIS.pdf'
IMG_300 = BASE / 'phase2_page1_300dpi.png'

REPLACEMENTS = {
    '고 유 번 호': '고유번호',
    '소 재 지': '소재지',
    '부 동 산 종 류': '부동산종류',
    '열 람 일 시': '열람일시',
    '현 황': '현황',
    '【 표 제 부 】': '【표제부】',
    '【 갑 구 】': '【갑구】',
    '【 을 구 】': '【을구】',
    '【 매 매 목 록 】': '【매매목록】',
    '【 공 동 담 보 목 록 】': '【공동담보목록】',
    '소 유 권 이 전': '소유권이전',
    '근 저 당 권 설 정': '근저당권설정',
    '지 상 권 설 정': '지상권설정',
    '가 압 류': '가압류',
    '임 의 경 매 개 시 결 정': '임의경매개시결정',
    '매 매 목 록': '매매목록',
    '공 동 담 보 목 록': '공동담보목록',
}

DATE_RE = re.compile(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일')
TIME_RE = re.compile(r'(\d{1,2})\s*시\s*(\d{1,2})\s*분\s*(\d{1,2})\s*초')
NUM_RE = re.compile(r'(\d{4})-(\d{4})-(\d{6})')
KNOWN_TOKENS = '|'.join([
    '2849-2018-019318',
    '파주시 파평면 마산리 113-2',
    '토지',
    '2026년03월31일',
    '최영호',
    '문산읍',
    '사임당로',
    '파주농업협동조합',
    '북파주농업협동조합',
])


def clean(text: str) -> str:
    text = text.replace('\r', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    text = DATE_RE.sub(lambda m: f"{m.group(1)}년{m.group(2).zfill(2)}월{m.group(3).zfill(2)}일", text)
    text = TIME_RE.sub(lambda m: f"{m.group(1).zfill(2)}시{m.group(2).zfill(2)}분{m.group(3).zfill(2)}초", text)
    text = NUM_RE.sub(lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}", text)
    text = ''.join(ch if ch in set(' \n\t') | set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') | set(KNOWN_TOKENS) else ' ' for ch in text)
    text = re.sub(r' +', ' ', text)
    return text.strip()


def prepare_image(img_path=IMG_300):
    img = Image.open(str(img_path)).convert('L')
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = img.point(lambda x: 0 if x < 200 else 255)
    return img


def parse_pdf(pdf_path=PDF_DEFAULT, out_prefix=None):
    if out_prefix is None:
        out_prefix = str(BASE / 'phase2_parsed')
    img = prepare_image()
    text = pytesseract.image_to_string(img, lang='kor+eng')
    cleaned = clean(text)
    md = Path(f"{out_prefix}.md")
    md.write_text(cleaned, encoding='utf-8')
    js = Path(f"{out_prefix}.json")
    payload = {
        'raw': text,
        'cleaned': cleaned,
        'source': str(pdf_path),
        'image': str(IMG_300),
    }
    js.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return cleaned, md, js


if __name__ == '__main__':
    cleaned, md, js = parse_pdf()
    print('완료')
    print('MD:', md)
    print('JSON:', js)
    print('\n--- cleaned 앞 60줄 ---')
    for line in cleaned.splitlines()[:60]:
        print(line)
