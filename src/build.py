#!/usr/bin/env python3
"""
등기부변환기 — 단일 스크립트 빌드
실행: python3 build.py

수행:
  1. 필요 패키지 자동 설치
  2. 앱 아이콘 생성
  3. PyInstaller로 컴파일
  4. dist/ 폴더에 결과물 생성
"""
import subprocess, sys, os, shutil, platform

HERE    = os.path.dirname(os.path.abspath(__file__))
DIST    = os.path.join(HERE, "dist")
BUILD   = os.path.join(HERE, "build_tmp")
APPNAME = "등기부변환기"

PACKAGES = ["pdfplumber","openpyxl","pillow","pyinstaller"]

def step(msg):
    print(f"\n{'─'*52}\n  {msg}\n{'─'*52}")

def run(cmd):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"  ✗ 실패 (code={r.returncode})")
        sys.exit(r.returncode)

# ── 1. 패키지 설치 ─────────────────────────────────────────────────
step("1/4  패키지 설치")
for pkg in PACKAGES:
    run([sys.executable,"-m","pip","install",pkg,"--quiet","--break-system-packages"])
    print(f"  ✓ {pkg}")

# ── 2. 아이콘 생성 ─────────────────────────────────────────────────
step("2/4  아이콘 생성")
sys.path.insert(0, HERE)
from make_icon import save_icon
icon_png = os.path.join(HERE, "icon.png")
save_icon(icon_png)

icon_file = icon_png
if platform.system() == "Darwin":
    iconset = os.path.join(HERE, "AppIcon.iconset")
    icns    = os.path.join(HERE, "icon.icns")
    try:
        os.makedirs(iconset, exist_ok=True)
        from PIL import Image
        src = Image.open(icon_png)
        for sz in [16,32,64,128,256,512]:
            src.resize((sz,sz),   Image.LANCZOS).save(os.path.join(iconset,f"icon_{sz}x{sz}.png"))
            src.resize((sz*2,sz*2),Image.LANCZOS).save(os.path.join(iconset,f"icon_{sz}x{sz}@2x.png"))
        r = subprocess.run(["iconutil","-c","icns",iconset,"-o",icns],capture_output=True)
        if r.returncode == 0 and os.path.exists(icns):
            icon_file = icns
            print("  ✓ .icns 생성")
        else:
            print("  ! iconutil 실패, .png 사용")
    except Exception as e:
        print(f"  ! 아이콘 변환 스킵: {e}")

# ── 3. PyInstaller 빌드 ────────────────────────────────────────────
step("3/4  PyInstaller 빌드")

spec = f"""# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['{os.path.join(HERE,"app.py")}'],
    pathex=['{HERE}'],
    binaries=[],
    datas=[
        ('{os.path.join(HERE,"parser.py")}',   '.'),
        ('{os.path.join(HERE,"exporter.py")}', '.'),
        ('{os.path.join(HERE,"make_icon.py")}','.'),
        ('{icon_png}', '.'),
    ],
    hiddenimports=[
        'pdfplumber','pdfminer','pdfminer.six',
        'pdfminer.high_level','pdfminer.layout',
        'openpyxl','openpyxl.styles','openpyxl.utils',
        'PIL','PIL.Image','PIL.ImageDraw','PIL.ImageTk',
        'tkinter','tkinter.ttk','tkinter.filedialog','tkinter.messagebox',
        'queue','threading','csv','re','os','sys','platform',
    ],
    excludes=['matplotlib','numpy','scipy','pandas'],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, [],
    exclude_binaries=True,
    name='{APPNAME}',
    debug=False, strip=False, upx=False,
    console=False, icon='{icon_file}',
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name='{APPNAME}',
)
"""

if platform.system() == "Darwin":
    spec += f"""
app = BUNDLE(coll,
    name='{APPNAME}.app',
    icon='{icon_file}',
    bundle_identifier='com.local.registry-ocr',
    info_plist={{
        'CFBundleDisplayName': '{APPNAME}',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    }},
)
"""

spec_path = os.path.join(HERE, f"{APPNAME}.spec")
with open(spec_path,"w",encoding="utf-8") as f:
    f.write(spec)

run([sys.executable,"-m","PyInstaller",
     "--clean","--noconfirm",
     "--distpath", DIST,
     "--workpath", BUILD,
     spec_path])

# ── 4. 정리 ────────────────────────────────────────────────────────
step("4/4  결과물 정리")

for tmp in ["build_tmp","AppIcon.iconset",f"{APPNAME}.spec","__pycache__"]:
    p = os.path.join(HERE,tmp)
    if os.path.exists(p): shutil.rmtree(p,ignore_errors=True)

if platform.system()=="Darwin":
    result = os.path.join(DIST,f"{APPNAME}.app")
    if os.path.exists(result):
        print(f"  ✓ macOS 앱: {result}")
        print(f"\n  실행:  open \"{result}\"")
    else:
        result = os.path.join(DIST,APPNAME)
        print(f"  ✓ 폴더 빌드: {result}")
elif platform.system()=="Windows":
    result = os.path.join(DIST,APPNAME,f"{APPNAME}.exe")
    print(f"  ✓ Windows: {result}")
else:
    result = os.path.join(DIST,APPNAME)
    print(f"  ✓ Linux: {result}")

print(f"""
╔══════════════════════════════════════════╗
║   ✅  빌드 완료!                          ║
║   위치: dist/{APPNAME:<24}║
╚══════════════════════════════════════════╝
""")
