#!/usr/bin/env python3
"""
Naver Clova OCR vs Tesseract 비교
──────────────────────────────────
실행: python3 clova_test.py
"""
import json, base64, time, io, urllib.request
import fitz; from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

# ── 설정 (여기만 수정) ──
CLOVA_URL  = 'https://141p3021uk.apigw.ntruss.com/custom/v1/54220/b635567d476eecdb9421613e6b6e73c47d30695a2d503049175ed27b7fe47f55/general'
CLOVA_KEY  = 'Zk5o...wenu='  # ← Secret Key 전체를 여기에 붙여넣기
PDF        = '2849-2018-019318_25696174641_RIS.pdf'

print(f'Clova URL: {CLOVA_URL[-50:]}')
print(f'Secret:    {CLOVA_KEY[:10]}...')
print()

# ── Tesseract ──
doc = fitz.open(PDF)
mat = fitz.Matrix(400/72, 400/72)
pix = doc[0].get_pixmap(matrix=mat)
img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples).convert('L')
t_img = img.filter(ImageFilter.SHARPEN)
t_img = ImageEnhance.Contrast(t_img).enhance(2.0)
t_img = t_img.point(lambda x: 0 if x < 175 else 255)
t = pytesseract.image_to_string(t_img, lang='kor+eng').strip()
print(f'[Tesseract] {len(t)}자')

# ── Clova ──
mat2 = fitz.Matrix(200/72, 200/72)
pix2 = doc[0].get_pixmap(matrix=mat2)
img2 = Image.frombytes('RGB', (pix2.width, pix2.height), pix2.samples)
buf = io.BytesIO(); img2.save(buf, format='JPEG', quality=85)
data = base64.b64encode(buf.getvalue()).decode()
body = json.dumps({
    'version':'V2','requestId':'x','timestamp':int(time.time()*1000),
    'lang':'ko','images':[{'format':'jpg','name':'p1','data':data}]
}).encode()

try:
    req = urllib.request.Request(CLOVA_URL, data=body,
        headers={'Content-Type':'application/json','X-OCR-SECRET':CLOVA_KEY})
    resp = urllib.request.urlopen(req, timeout=60)
    r = json.loads(resp.read())
    lines=[f['inferText'] for img in r['images'] for f in img.get('fields',[])]
    c = '\n'.join(lines)
    print(f'[Clova]     {len(c)}자')
    print('\n=== Clova ===\n'+c[:400])
except Exception as e:
    print(f'Clova 오류: {e}')
    if hasattr(e,'read'):
        print(e.read().decode()[:500])

print('\n=== Tesseract ===\n'+t[:400])
doc.close()
