#!/usr/bin/env python3
"""
Naver Clova OCR vs Tesseract 비교 PoC
사용법:
  1. Naver Cloud Platform → CLOVA OCR 도메인 생성
  2. API Gateway 연동 → Invoke URL + Secret Key 발급
  3. 실행:
     CLOVA_URL="https://..." CLOVA_SECRET="..." python3 clova_compare.py [PDF경로]
발급: https://console.ncloud.com → AI·NAVER API → CLOVA OCR
무료 티어: 월 100건
"""

import os, sys, json, base64, time, io
from pathlib import Path
import urllib.request
import fitz
from PIL import Image

PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else '2849-2018-019318_25696174641_RIS.pdf'
CLOVA_URL = os.environ.get('CLOVA_URL', '')
CLOVA_SECRET = os.environ.get('CLOVA_SECRET', '')

if not CLOVA_URL or not CLOVA_SECRET:
    print('[오류] 환경변수가 필요합니다.')
    print('  export CLOVA_URL="https://..."')
    print('  export CLOVA_SECRET="..."')
    print('  발급: https://console.ncloud.com → CLOVA OCR')
    sys.exit(1)

def clova_ocr(image_bytes, fmt='png'):
    """Naver Clova General OCR (V2)"""
    data = base64.b64encode(image_bytes).decode('utf-8')
    body = json.dumps({
        'version': 'V2',
        'requestId': str(int(time.time() * 1000)),
        'timestamp': int(time.time() * 1000),
        'lang': 'ko',
        'images': [{'format': fmt, 'name': 'page', 'data': data}]
    }).encode('utf-8')

    req = urllib.request.Request(CLOVA_URL, data=body,
        headers={'Content-Type': 'application/json', 'X-OCR-SECRET': CLOVA_SECRET})
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode('utf-8'))

    texts = []
    for img in result.get('images', []):
        if img.get('inferResult') != 'SUCCESS':
            print(f"  [경고] OCR 실패: {img.get('message', '')}")
            continue
        for field in img.get('fields', []):
            texts.append(field.get('inferText', ''))
    return '\n'.join(texts)

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

print(f'[비교 PoC] Naver Clova vs Tesseract')
print(f'  파일: {PDF_PATH}\n')

print('[Tesseract] OCR 중...')
t_text = tesseract_ocr(PDF_PATH, 0)
print(f'  → {len(t_text)}자')

print('[Clova OCR] 처리 중...')
doc = fitz.open(PDF_PATH)
mat = fitz.Matrix(400/72, 400/72)
pix = doc[0].get_pixmap(matrix=mat)
img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
doc.close()
buf = io.BytesIO()
img.save(buf, format='PNG')

try:
    c_text = clova_ocr(buf.getvalue())
    print(f'  → {len(c_text)}자')
except Exception as e:
    print(f'  ❌ Clova API 오류: {e}')
    sys.exit(1)

print(f'\n{"="*60}')
print('─── Naver Clova (처음 500자) ───')
print(c_text[:500])
print(f'\n─── Tesseract (처음 500자) ───')
print(t_text[:500])
print(f'\n통계: Clova={len(c_text)}자, Tesseract={len(t_text)}자')
