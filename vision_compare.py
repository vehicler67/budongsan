#!/usr/bin/env python3
"""
Google Vision OCR vs Tesseract 비교 PoC
─────────────────────────────────────────
사용법:
  1. Google Cloud Vision API 활성화 → API 키 발급
  2. 아래 명령으로 실행:
     GOOGLE_API_KEY=your_key python3 vision_compare.py [PDF경로]

발급 방법: https://console.cloud.google.com/apis/credentials
  - 'API 키 만들기' 클릭
  - Vision API 사용 제한 설정 (선택)
  - 무료 티어: 월 1,000건
"""

import os, sys, json, base64
from pathlib import Path
import urllib.request

import fitz
from PIL import Image

PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else '2849-2018-019318_25696174641_RIS.pdf'
API_KEY = os.environ.get('GOOGLE_API_KEY', '')

if not API_KEY:
    print('[오류] GOOGLE_API_KEY 환경변수가 필요합니다.')
    print('  export GOOGLE_API_KEY=your_key_here')
    print('  발급: https://console.cloud.google.com/apis/credentials')
    sys.exit(1)

# ── Google Vision OCR ─────────────────────────────────────
def google_ocr(image_bytes):
    """Google Vision API로 OCR (DOCUMENT_TEXT_DETECTION)"""
    content = base64.b64encode(image_bytes).decode('utf-8')
    body = json.dumps({
        'requests': [{
            'image': {'content': content},
            'features': [{'type': 'DOCUMENT_TEXT_DETECTION'}]
        }]
    }).encode('utf-8')

    url = f'https://vision.googleapis.com/v1/images:annotate?key={API_KEY}'
    req = urllib.request.Request(url, data=body,
        headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode('utf-8'))

    text = result['responses'][0].get('fullTextAnnotation', {}).get('text', '')
    return text

# ── Tesseract OCR ─────────────────────────────────────────
def tesseract_ocr(pdf_path, page_num):
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(400/72, 400/72)
    pix = doc[page_num].get_pixmap(matrix=mat)
    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples).convert('L')
    doc.close()

    from PIL import ImageEnhance, ImageFilter
    import pytesseract
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.point(lambda x: 0 if x < 175 else 255)
    return pytesseract.image_to_string(img, lang='kor+eng').strip()

# ── 비교 실행 ─────────────────────────────────────────────
print(f'[비교 PoC] Google Vision vs Tesseract')
print(f'  파일: {PDF_PATH}')
print(f'  페이지: 1페이지만 비교\n')

# Tesseract
print('[Tesseract] OCR 중...')
t_text = tesseract_ocr(PDF_PATH, 0)
print(f'  → {len(t_text)}자')

# Google Vision (PDF를 이미지로 변환 후 전송)
print('[Google Vision] OCR 중...')
doc = fitz.open(PDF_PATH)
mat = fitz.Matrix(400/72, 400/72)
pix = doc[0].get_pixmap(matrix=mat)
img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
doc.close()

import io
buf = io.BytesIO()
img.save(buf, format='PNG')
img_bytes = buf.getvalue()

try:
    g_text = google_ocr(img_bytes)
    print(f'  → {len(g_text)}자')
except Exception as e:
    print(f'  ❌ Vision API 오류: {e}')
    sys.exit(1)

# ── 결과 비교 ─────────────────────────────────────────────
print(f'\n{"="*60}')
print('결과 비교')
print(f'{"="*60}')

print(f'\n─── Google Vision (처음 500자) ───')
print(g_text[:500])
print(f'\n─── Tesseract (처음 500자) ───')
print(t_text[:500])

print(f'\n─── 통계 ───')
print(f'  Google Vision: {len(g_text)}자')
print(f'  Tesseract:     {len(t_text)}자')
print(f'  차이:          {len(g_text) - len(t_text):+d}자')
