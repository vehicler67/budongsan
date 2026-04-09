"""
등기부등본 PDF 파서 v7 — 완전판
공동담보목록 컬럼: 일련번호(~73) | 부동산표시(73~260) | 필지(260~262) | 관할등기소(262~362) | 순위번호(362~412) | 생성(412~496) | 소멸(496~)
"""
import pdfplumber, re
from typing import Dict, List, Optional, Tuple


# ── CID 폰트 감지 ─────────────────────────────────────────────────────────────
def _has_cid(words: list, threshold: float = 0.4) -> bool:
    """단어 중 CID 코드 비율이 threshold 이상이면 True (ToUnicode 맵 없는 폰트)"""
    if not words:
        return False
    cid_count = sum(1 for w in words if "(cid:" in w.get("text", ""))
    return (cid_count / len(words)) >= threshold


# ── OCR 폴백 텍스트 추출 (pytesseract + PyMuPDF) ──────────────────────────────
def _ocr_extract_words(pdf_path: str) -> list:
    """
    CID 폰트 PDF를 PyMuPDF로 렌더링 후 pytesseract로 OCR.
    반환 형식: pdfplumber extract_words()와 동일한 딕셔너리 리스트
    {"x0", "top", "x1", "bottom", "text", "page"}
    """
    try:
        import fitz
        import pytesseract
        from PIL import Image, ImageEnhance
        import io
    except ImportError as e:
        raise RuntimeError(f"OCR 폴백 실패 — 필요 패키지 없음: {e}")

    # PyInstaller 번들 환경은 시스템 PATH 미포함 → tesseract 경로 직접 지정
    import shutil, os
    _tess = (
        pytesseract.pytesseract.tesseract_cmd
        if pytesseract.pytesseract.tesseract_cmd != "tesseract"
        else None
    )
    if not _tess or not shutil.which(_tess):
        for _candidate in [
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/usr/bin/tesseract",
        ]:
            if os.path.isfile(_candidate):
                pytesseract.pytesseract.tesseract_cmd = _candidate
                break

    # TESSDATA_PREFIX 명시 설정 — 앱 번들 환경에서 언어팩 경로 고정
    for _tdata in [
        "/opt/homebrew/share/tessdata",
        "/usr/local/share/tessdata",
        "/usr/share/tessdata",
    ]:
        if os.path.isdir(_tdata) and os.path.isfile(os.path.join(_tdata, "kor.traineddata")):
            os.environ.setdefault("TESSDATA_PREFIX", _tdata)
            break

    try:
        from PIL import ImageEnhance
    except ImportError as e:
        raise RuntimeError(f"OCR 폴백 실패 — 필요 패키지 없음: {e}")

    SCALE = 3.0          # 렌더 해상도 배율 (216 DPI — 한글 인식률 향상)
    all_words = []

    doc = fitz.open(pdf_path)
    for pi, page in enumerate(doc):
        # 페이지 → 이미지 (고해상도 렌더)
        pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        # 전처리: 흑백 + 대비 강화 + 이진화 (OCR 인식률 개선)
        gray = img.convert("L")
        enhanced = ImageEnhance.Contrast(gray).enhance(2.0)
        binary = enhanced.point(lambda x: 0 if x < 160 else 255, '1').convert('L')

        # Tesseract OCR — PSM 4: 단일 컬럼, 가변 세로 크기 (표 레이아웃에 적합)
        data = pytesseract.image_to_data(
            binary, lang="kor+eng",
            config="--psm 4 --oem 1",
            output_type=pytesseract.Output.DICT,
        )

        n = len(data["text"])
        for i in range(n):
            txt = data["text"][i].strip()
            if not txt or int(data["conf"][i]) < 20:
                continue
            # 이미지 픽셀 좌표 → PDF 포인트 좌표
            x0  = data["left"][i]   / SCALE
            top = data["top"][i]    / SCALE
            x1  = (data["left"][i] + data["width"][i])  / SCALE
            bot = (data["top"][i]  + data["height"][i]) / SCALE
            all_words.append({
                "x0": x0, "top": top, "x1": x1, "bottom": bot,
                "text": txt, "page": pi + 1,
            })
    doc.close()
    return all_words


def _ocr_clean(text: str) -> str:
    """OCR 결과 후처리 — 음절 사이 공백 제거, 노이즈 정리"""
    import re as _re
    t = text
    # 한글 음절 사이 단일 공백 제거: '소 유 권' → '소유권'
    t = _re.sub(r'(?<=[\uac00-\ud7a3]) (?=[\uac00-\ud7a3])', '', t)
    # 숫자+한글/한글+숫자 사이 공백 정리: '1997 년' → '1997년', '제 99956 호' → '제99956호'
    t = _re.sub(r'(\d) (년|월|일|호|번|분|초|원)', r'\1\2', t)
    t = _re.sub(r'(제|제\s*) (\d)', r'제\2', t)
    # 연속 공백 → 단일 공백
    t = _re.sub(r'  +', ' ', t)
    return t.strip()

WMARK_X = (180, 375)

C_PJE = [73,155,290,332,425];   N_PJE = ["표시번호","접수","소재지번","지목","면적","등기원인및기타사항"]
C_GAP = [73,175,255,338];       N_GAP = ["순위번호","등기목적","접수","등기원인","권리자및기타사항"]

# 매매목록: 일련번호|부동산표시(~356)|순위번호(366)|등기원인(417)|경정원인
C_MAE = [73,356,412,496];       N_MAE = ["일련번호","부동산표시","순위번호","등기원인","경정원인"]

# 공동담보목록 실측: 일련번호|부동산표시(80~220)|필지(after 220)|관할등기소(264)|순위번호(366)|생성원인(417)|변경소멸(499)
C_GD  = [73,260,362,412,496];   N_GD  = ["일련번호","부동산표시_관할","순위번호","생성원인","변경소멸"]

C_SUM1= [116,197,263,532];      N_SUM1= ["등기명의인","주민등록번호","최종지분","주소","순위번호"]
C_SUM2= [79,192,268,518];      N_SUM2= ["순위번호","등기목적","접수정보","주요등기사항","대상소유자"]

RE_SEC = [
    ("표제부",       re.compile(r"【\s*표\s*제\s*부\s*】")),
    ("갑구",         re.compile(r"【\s*갑\s*구\s*】")),
    ("을구",         re.compile(r"【\s*을\s*구\s*】")),
    ("매매목록",     re.compile(r"【\s*매\s*매\s*목\s*록\s*】")),
    ("공동담보목록", re.compile(r"【\s*공\s*동\s*담\s*보\s*목\s*록\s*】")),
    ("요약",         re.compile(r"주요\s*등기사항\s*요약")),
]
# OCR 모드용 — 브래킷 없이도 인식 (【】 오인식 보정)
# 매매목록/공동담보목록은 '목록번호' 라인으로만 감지 (갑구 내 '매매목록 제XXXX호' 오인식 방지)
RE_SEC_OCR = [
    ("표제부",       re.compile(r"표\s*제\s*부|제\s*부\s*[】\])]")),
    ("갑구",         re.compile(r"갑\s*구")),
    ("을구",         re.compile(r"을\s*구|소유권이외")),  # 【을구】가 '= 구 】'로 OCR될 때 '소유권이외' 로 감지
    ("공동담보목록", re.compile(r"[【\[]\s*공\s*동\s*(?:\s*담\s*)?보\s*목\s*(?:록\s*)?\s*[】\]]")),  # 【공동보목】/【공동담보목록】 등 OCR 변형, 셀 데이터와 구분 위해 양쪽 브래킷 필수
    ("요약",         re.compile(r"요약.{0,6}(?:용|참고|참\s*고)|주요.{0,20}요약")),
]
RE_SUBSEC_OCR = re.compile(r"^(\d+)[.\s]\s*(?:소\s*유\s*지\s*분\s*현\s*황|소\s*유\s*지\s*분\s*을|저\s*당\s*권|전\s*세\s*권|\(?\s*근\s*\)?)")
RE_SKIP   = re.compile(r"열람일시\s*:|^\d+/\d+$|^1/1$|본\s*등기사항증명서는\s*열람용|실선으로\s*그어진|증명서는\s*컬러|이\s*하\s*여\s*백|출력일시\s*:|관할등기소\s*의정부")
RE_TOOJI  = re.compile(r"^\[토지\]\s*경기도")
RE_HDR    = re.compile(r"^(순위번호|표시번호|일련번호|등기명의인)(등기목적|부동산|최종|접수|소재)?")
RE_SUBSEC = re.compile(r"^(\d+)\.\s*(소유지분현황|소유지분을\s*제외|저당권|전세권|\(근\))")
RE_LISTNO = re.compile(r"^목록번호\s+(\S+)")

def _wm(w): return w["text"] in ("열","람","용") and WMARK_X[0]<w["x0"]<WMARK_X[1]
def _ci(x,b): return next((i for i,v in enumerate(b) if x<v), len(b))
def _cl(s): return re.sub(r"\s{2,}"," ",str(s)).strip()
def _cl_ocr(s): return _ocr_clean(re.sub(r"\s{2,}"," ",str(s)).strip())

def _cols(words, bounds):
    g={}
    for w in words:
        if _wm(w): continue
        ci=_ci(w["x0"],bounds)
        g.setdefault(ci,[]).append(w)
    return {ci:_cl(" ".join(w["text"] for w in sorted(ws,key=lambda w:w["x0"]))) for ci,ws in g.items()}

def _make(cols,names): return {names[i]:cols.get(i,"") for i in range(len(names))}

def _app(rec,cols,names):
    for ci,val in cols.items():
        if ci<len(names) and val:
            nm=names[ci]; ex=rec.get(nm,"")
            rec[nm]=(ex+" "+val).strip() if ex else val

def _gd_row(words):
    """공동담보목록 한 행 파싱:
    일련번호 | [토지] 경기도...마산리 | 필지명(젤44-7 등) | 관할등기소 | 순위번횀 | 생성원인 | 변경소멸
    콜럼 경계는 C_GD 고마 스케일 모듈 변수 사용 (Mac 자동 보정)
    """
    rec = {"일련번호":"","부동산표시":"","관할등기소":"","순위번호":"","생성원인":"","변경소멸":""}
    for w in words:
        if _wm(w): continue
        x = w["x0"]
        t = w["text"]
        if x < C_GD[0]:    rec["일련번호"]  = (rec["일련번호"]+" "+t).strip()
        elif x < C_GD[1]:  rec["부동산표시"] = (rec["부동산표시"]+" "+t).strip()
        elif x < C_GD[2]:  rec["관할등기소"] = (rec["관할등기소"]+" "+t).strip()
        elif x < C_GD[3]:  rec["순위번호"]  = (rec["순위번호"]+" "+t).strip()
        elif x < C_GD[4]:  rec["생성원인"]  = (rec["생성원인"]+" "+t).strip()
        else:               rec["변경소멸"]  = (rec["변경소멸"]+" "+t).strip()
    return {k:_cl(v) for k,v in rec.items() if _cl(v)}

def _mae_row(words):
    """매매목록 행 파싱 — 컬럼 경계는 C_MAE 글로벌 사용 (Mac 자동 보정)"""
    rec = {"일련번호":"","부동산표시":"","순위번호":"","등기원인":"","경정원인":""}
    for w in words:
        if _wm(w): continue
        x,t = w["x0"], w["text"]
        if x < C_MAE[0]:    rec["일련번호"]   = (rec["일련번호"]+" "+t).strip()
        elif x < C_MAE[1]:  rec["부동산표시"] = (rec["부동산표시"]+" "+t).strip()
        elif x < C_MAE[2]:  rec["순위번호"]   = (rec["순위번호"]+" "+t).strip()
        elif x < C_MAE[3]:  rec["등기원인"]   = (rec["등기원인"]+" "+t).strip()
        else:                rec["경정원인"]   = (rec["경정원인"]+" "+t).strip()
    return {k:_cl(v) for k,v in rec.items() if _cl(v)}

def parse_registry(pdf_path:str)->Dict[str,list]:
    raw=[]
    use_ocr = False
    with pdfplumber.open(pdf_path) as pdf:
        total=len(pdf.pages)
        # 페이지 너비 자동 스케일 (A4=595.28pt 기준)
        _pw = pdf.pages[0].width if pdf.pages else 595.28
        _sc = _pw / 595.28
        if abs(_sc - 1.0) > 0.01:
            def _scale(lst): return [round(v*_sc) for v in lst]
            globals().update(dict(
                C_PJE=_scale([73,155,290,332,425]),
                C_GAP=_scale([73,175,255,338]),
                C_MAE=_scale([73,356,412,496]),
                C_GD =_scale([73,260,362,412,496]),
                C_SUM1=_scale([116,197,263,532]),
                C_SUM2=_scale([79,192,268,518]),
                WMARK_X=(round(180*_sc), round(375*_sc)),
            ))
        for pi,pg in enumerate(pdf.pages):
            ws=pg.extract_words(x_tolerance=3,y_tolerance=3,keep_blank_chars=False,use_text_flow=False)
            for w in ws: w["page"]=pi+1
            raw.extend(ws)

    # CID 폰트 감지 → OCR 폴백
    if _has_cid(raw):
        use_ocr = True
        raw = _ocr_extract_words(pdf_path)

    buckets={}
    for w in raw: buckets.setdefault((w["page"],int(w["top"]/5)),[]).append(w)

    res={s:[] for s in ["표제부","갑구","을구","매매목록","공동담보목록","요약_소유지분","요약_갑구","요약_을구"]}
    cur_sec=None; cur_sub=None; cur_rec=None
    cur_b=C_GAP; cur_n=N_GAP; cur_listno=""
    _re_sec = RE_SEC_OCR if use_ocr else RE_SEC  # OCR 모드: 브래킷 없는 유연한 패턴
    _clean  = _cl_ocr if use_ocr else _cl         # OCR 모드: 음절 공백 제거 추가

    def flush(target=None):
        nonlocal cur_rec
        sec=target or cur_sec
        if cur_rec and sec in res:
            cl={k:_clean(v) for k,v in cur_rec.items() if _clean(str(v))}
            if cl: res[sec].append(cl)
        cur_rec=None

    for k in sorted(buckets):
        words_all=sorted(buckets[k],key=lambda w:w["x0"])
        words=[w for w in words_all if not _wm(w)]
        if not words: continue
        txt=_clean(" ".join(w["text"] for w in words))
        if not txt: continue
        if RE_SKIP.search(txt): continue
        if RE_TOOJI.match(txt): continue
        if re.match(r"^\d+/\d+$",txt) or txt=="1/1": continue
        if re.match(r"^[가나다라]\.\s",txt): continue

        # OCR 모드: 목록번호 라인 → 매매목록/공동담보목록 섹션 자동 전환
        # 갑구 내 '매매목록 제XXXX호' 텍스트와 분리하기 위해 RE_SEC_OCR에서 제외하고 여기서 처리
        if use_ocr and cur_sec not in ('매매목록','공동담보목록'):
            m_ln = RE_LISTNO.match(txt)
            if m_ln:
                flush()
                if not res['매매목록']:
                    cur_sec='매매목록'; cur_b,cur_n=C_MAE,N_MAE
                else:
                    cur_sec='공동담보목록'; cur_b,cur_n=C_GD,N_GD
                cur_listno=m_ln.group(1); cur_sub=None; cur_rec=None; continue

        # 섹션 전환 — 순방향 전진만 허용 (이미 지나친 섹션으로 역행 방지)
        _SEC_ORDER = ["표제부","갑구","을구","매매목록","공동담보목록","요약"]
        _cur_ord = _SEC_ORDER.index(cur_sec) if cur_sec in _SEC_ORDER \
            else (5 if cur_sec and cur_sec.startswith("요약_") else -1)  # 요약_* 서브섹션은 order=5로 취급
        hit=None
        for sname,pat in _re_sec:
            if pat.search(txt):
                _hit_ord = _SEC_ORDER.index(sname) if sname in _SEC_ORDER else 99
                if _hit_ord > _cur_ord:  # 순방향일 때만 전환
                    hit=sname; break
        if hit:
            flush(); cur_sec=hit; cur_sub=None; cur_rec=None; cur_listno=""
            if hit=="표제부":        cur_b,cur_n=C_PJE,N_PJE
            elif hit in("갑구","을구"): cur_b,cur_n=C_GAP,N_GAP
            elif hit=="요약":        cur_b,cur_n=C_SUM2,N_SUM2
            continue
        if cur_sec is None: continue

        # ── 요약 ──────────────────────────────────────────────────
        if cur_sec=="요약":
            if re.match(r"^\[\s*주\s*의|^\[\s*참\s*고",txt): continue
            if re.match(r"^고유번호|^\[토지\]",txt): continue
            if re.match(r"^[가나다라]\.",txt): continue
            if txt.strip() in ("바랍니다.",""): continue
            _re_subsec = RE_SUBSEC_OCR if use_ocr else RE_SUBSEC
            m=_re_subsec.match(txt)
            if m:
                flush(cur_sub); n=m.group(2) if len(m.groups())>1 else txt
                nsp=n.replace(" ","")
                if re.search(r"소유지분현황|소지분현황|지분현황",nsp):  cur_sub="요약_소유지분"; cur_b,cur_n=C_SUM1,N_SUM1
                elif re.search(r"소유지분을|소지분을",nsp):             cur_sub="요약_갑구";     cur_b,cur_n=C_SUM2,N_SUM2
                else:                                                    cur_sub="요약_을구";     cur_b,cur_n=C_SUM2,N_SUM2
                cur_rec=None; continue
            if cur_sub is None: continue
            cols=_cols(words,cur_b)
            col0=cols.get(0,"").strip()
            nsp=txt.replace(" ","")
            if RE_HDR.match(nsp): continue
            if re.match(r"^\d",col0):
                flush(cur_sub); cur_rec=_make(cols,cur_n); cur_sec=cur_sub
            elif cur_rec: _app(cur_rec,cols,cur_n)
            else: cur_rec=_make(cols,cur_n)
            continue

        # ── 매매목록 ──────────────────────────────────────────────
        if cur_sec=="매매목록":
            m=RE_LISTNO.match(txt)
            if m: cur_listno=m.group(1); flush(); cur_rec=None; continue
            if txt.startswith("거래가액"):
                res["매매목록"].append({"구분":"거래가액","목록번호":cur_listno,"내용":txt}); continue
            nsp=txt.replace(" ","")
            if re.search(r"예비란|일련번호.*부동산|등기원인.*경정",nsp): continue
            col0=_cl(words[0]["text"]) if words else ""
            if re.match(r"^\d",col0):
                flush(); cur_rec=_mae_row(words); cur_rec["목록번호"]=cur_listno
            elif cur_rec:
                extra=_mae_row(words)
                for fk,fv in extra.items():
                    if fk!="일련번호" and fv:
                        ex=cur_rec.get(fk,""); cur_rec[fk]=(ex+" "+fv).strip() if ex else fv
            continue

        # ── 공동담보목록 ──────────────────────────────────────────
        if cur_sec=="공동담보목록":
            m=RE_LISTNO.match(txt)
            if m: cur_listno=m.group(1); flush(); cur_rec=None; continue
            nsp=txt.replace(" ","")
            if re.search(r"기타사항|일련번호.*부동산|생성원인.*변경",nsp): continue
            col0=_cl(words[0]["text"]) if words else ""
            if re.match(r"^\d",col0):
                flush(); cur_rec=_gd_row(words); cur_rec["목록번호"]=cur_listno
            elif cur_rec:
                extra=_gd_row(words)
                for fk,fv in extra.items():
                    if fk!="일련번호" and fv:
                        ex=cur_rec.get(fk,""); cur_rec[fk]=(ex+" "+fv).strip() if ex else fv
            continue

        # ── 표제부 / 갑구 / 을구 ─────────────────────────────────
        cols=_cols(words,cur_b)
        if not any(cols.values()): continue
        nsp=txt.replace(" ","")
        if RE_HDR.match(nsp): continue
        if re.search(r"(순위번호|표시번호).*(등기목적|접수|소재지번)",nsp): continue
        col0=cols.get(0,"").strip()
        if re.match(r"^\d",col0): flush(); cur_rec=_make(cols,cur_n)
        elif cur_rec: _app(cur_rec,cols,cur_n)

    flush()

    # 기본정보
    p1=[w for w in raw if w["page"]==1 and not _wm(w)]
    s1=" ".join(w["text"] for w in p1)
    info={}
    for pat,k in [(r"고유번호\s*([\d\-]+)","고유번호"),(r"열람일시\s*:\s*([\d년월일\s시분초]+?)(?=\s*\d+/|\s*$)","열람일시")]:
        m=re.search(pat,s1); info[k]=_cl(m.group(1)) if m else ""
    m=re.search(r"\[토지\]\s*(경기도[\w\s]+?[\d\-]+)(?=\s)",s1)
    info["소재지"]=_cl(m.group(1)) if m else ""
    m=re.search(r"-\s*(토지|건물|집합건물)\s*-",s1)
    info["부동산종류"]=m.group(1) if m else ""
    plast=[w for w in raw if w["page"]==total and not _wm(w)]
    slast=" ".join(w["text"] for w in plast)
    m=re.search(r"\[토지\]\s*(.+?(?:임야|대|전|답)\s*[\d,]+㎡)",slast)
    if m: info["현황"]=_cl(m.group(1))

    # 공동담보목록: 일련번호 없는 이어붙이기 행을 직전 레코드에 합침
    if res.get("공동담보목록"):
        merged = []
        for row in res["공동담보목록"]:
            if row.get("일련번호"):
                merged.append(row)
            elif merged:
                prev = merged[-1]
                for fk, fv in row.items():
                    if fk in ("목록번호",): continue
                    if fk == "부동산표시":
                        ex = prev.get(fk, "")
                        # 필지번호를 부동산표시에 이어붙임
                        prev[fk] = (ex + " " + fv).strip() if ex else fv
                    elif fk in ("관할등기소", "생성원인", "변경소멸"):
                        ex = prev.get(fk, "")
                        prev[fk] = (ex + " " + fv).strip() if ex else fv
        res["공동담보목록"] = merged

    # 요약 섹션 노이즈 행 제거 (소섹션 전환행, 참고사항 섞임)
    for sec in ("요약_갑구","요약_을구","요약_소유지분"):
        clean = []
        for row in res.get(sec,[]):
            sn = str(row.get("순위번호",""))
            # "3. (근)저당권..." 소섹션 전환 잔류 행
            if re.match(r"^\d+\.\s*(근|소유|저당)", sn): continue
            # "[ 참 고 사 항" 등 노이즈
            if re.search(r"참\s*고\s*사\s*항|바랍니다|주\s*의\s*사\s*항", sn): continue
            # 실제 데이터 없는 행
            vals = [v for k,v in row.items() if v]
            if not vals: continue
            res[sec] = clean
            clean.append(row)
        res[sec] = clean

    out={k:v for k,v in res.items() if v}
    out["기본정보"]=[info]; out["_meta"]=[{"총페이지":total,**info}]
    return out
