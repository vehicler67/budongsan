"""
등기부등본 OCR → Excel 변환 앱
tkinter 기반 — 외부 의존 없음
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import queue

# PyInstaller 번들 실행 시 내부 모듈 경로 등록
if getattr(sys, 'frozen', False):
    # .app 번들 또는 PyInstaller 실행 파일
    _base = sys._MEIPASS
else:
    # 일반 python 실행
    _base = os.path.dirname(os.path.abspath(__file__))
if _base not in sys.path:
    sys.path.insert(0, _base)

# 아이콘 생성
try:
    from make_icon import make_icon
    HAS_ICON = True
except ImportError:
    HAS_ICON = False

from parser import parse_registry
from exporter import export_xlsx, export_csv


# ─────────────────────────── 색상 / 폰트 ───────────────────────────
BG        = "#0F1923"
BG2       = "#1A2744"
BG3       = "#243556"
ACCENT    = "#4A90D9"
ACCENT2   = "#5BA4E8"
GREEN     = "#2ECC71"
RED       = "#E74C3C"
TEXT      = "#E8EDF5"
TEXT_DIM  = "#8899BB"
BORDER    = "#2E4A8B"

FONT_TITLE  = ("Apple SD Gothic Neo", 22, "bold")
FONT_BODY   = ("Apple SD Gothic Neo", 11)
FONT_SMALL  = ("Apple SD Gothic Neo", 9)
FONT_MONO   = ("Menlo", 9)

# fallback fonts for non-mac
import platform
if platform.system() != "Darwin":
    FONT_TITLE = ("맑은 고딕", 22, "bold")
    FONT_BODY  = ("맑은 고딕", 11)
    FONT_SMALL = ("맑은 고딕", 9)
    FONT_MONO  = ("Courier New", 9)


class RoundedFrame(tk.Canvas):
    """둥근 모서리 프레임"""
    def __init__(self, parent, radius=16, bg=BG2, border_color=BORDER,
                 border_width=1, **kwargs):
        super().__init__(parent, bg=BG, highlightthickness=0, **kwargs)
        self.radius = radius
        self._bg = bg
        self._border_color = border_color
        self._border_width = border_width
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event=None):
        self.delete("bg")
        w, h = self.winfo_width(), self.winfo_height()
        r = self.radius
        if w < 2 * r or h < 2 * r:
            return
        bw = self._border_width
        for offset, color in [(0, self._border_color), (bw, self._bg)]:
            x0, y0 = offset, offset
            x1, y1 = w - offset, h - offset
            self.create_arc(x0, y0, x0 + 2*r, y0 + 2*r,
                            start=90, extent=90, fill=color, outline=color, tags="bg")
            self.create_arc(x1 - 2*r, y0, x1, y0 + 2*r,
                            start=0, extent=90, fill=color, outline=color, tags="bg")
            self.create_arc(x0, y1 - 2*r, x0 + 2*r, y1,
                            start=180, extent=90, fill=color, outline=color, tags="bg")
            self.create_arc(x1 - 2*r, y1 - 2*r, x1, y1,
                            start=270, extent=90, fill=color, outline=color, tags="bg")
            self.create_rectangle(x0 + r, y0, x1 - r, y1,
                                  fill=color, outline=color, tags="bg")
            self.create_rectangle(x0, y0 + r, x1, y1 - r,
                                  fill=color, outline=color, tags="bg")


class LogBox(tk.Text):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.tag_config("info",    foreground=TEXT_DIM)
        self.tag_config("ok",      foreground=GREEN)
        self.tag_config("err",     foreground=RED)
        self.tag_config("section", foreground=ACCENT)
        self.tag_config("header",  foreground=TEXT, font=FONT_BODY)

    def log(self, msg: str, tag="info"):
        self.config(state="normal")
        self.insert("end", msg + "\n", tag)
        self.see("end")
        self.config(state="disabled")

    def clear(self):
        self.config(state="normal")
        self.delete("1.0", "end")
        self.config(state="disabled")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("등기부등본 변환기")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(720, 580)

        # 창 중앙 배치
        self.geometry("820x660")
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 820) // 2
        y = (self.winfo_screenheight() - 660) // 2
        self.geometry(f"820x660+{x}+{y}")

        # 아이콘 설정
        if HAS_ICON:
            try:
                icon_img = make_icon(64)
                from PIL import ImageTk
                self._icon_photo = ImageTk.PhotoImage(icon_img)
                self.iconphoto(True, self._icon_photo)
            except Exception:
                pass

        self.pdf_paths: list[str] = []
        self.out_dir = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        self.fmt_var = tk.StringVar(value="xlsx")
        self.q: queue.Queue = queue.Queue()

        self._build_ui()
        self._poll_queue()

    # ─────────────── UI 구성 ───────────────
    def _build_ui(self):
        root = self

        # ── 상단 헤더 ──
        hdr = tk.Frame(root, bg=BG2, height=72)
        hdr.pack(fill="x", padx=0, pady=0)
        hdr.pack_propagate(False)

        tk.Label(hdr, text="📋", bg=BG2, font=("", 26)).pack(side="left", padx=18, pady=12)
        title_frame = tk.Frame(hdr, bg=BG2)
        title_frame.pack(side="left", pady=14)
        tk.Label(title_frame, text="등기부등본 변환기",
                 bg=BG2, fg=TEXT, font=FONT_TITLE).pack(anchor="w")
        tk.Label(title_frame, text="PDF → Excel / CSV  ·  외부 API 없음  ·  완전 로컬",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SMALL).pack(anchor="w")

        # ── 메인 컨텐츠 ──
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # 왼쪽 패널
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # PDF 선택 카드
        self._pdf_card(left)

        # 출력 설정 카드
        self._output_card(left)

        # 변환 버튼
        self._action_card(left)

        # 오른쪽 로그
        self._log_card(body)

    def _pdf_card(self, parent):
        card = tk.LabelFrame(parent, text="  📄 등기부 PDF 선택  ",
                             bg=BG, fg=ACCENT, font=FONT_BODY,
                             labelanchor="nw", bd=0,
                             highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 10))

        # 드롭존 (클릭으로 선택)
        self.drop_frame = tk.Frame(card, bg=BG3, height=110, cursor="hand2")
        self.drop_frame.pack(fill="x", padx=12, pady=10)
        self.drop_frame.pack_propagate(False)

        self.drop_label = tk.Label(
            self.drop_frame,
            text="클릭하여 PDF 파일 선택\n(여러 파일 동시 선택 가능)",
            bg=BG3, fg=TEXT_DIM, font=FONT_BODY,
            justify="center"
        )
        self.drop_label.pack(expand=True)

        for w in (self.drop_frame, self.drop_label):
            w.bind("<Button-1>", lambda e: self._pick_pdf())
            w.bind("<Enter>", lambda e: self.drop_frame.config(bg="#2A3F6B"))
            w.bind("<Leave>", lambda e: self.drop_frame.config(bg=BG3))

        # 파일 목록
        list_frame = tk.Frame(card, bg=BG)
        list_frame.pack(fill="x", padx=12, pady=(0, 10))

        self.file_listbox = tk.Listbox(
            list_frame, bg=BG2, fg=TEXT, font=FONT_MONO,
            selectbackground=ACCENT, selectforeground=TEXT,
            bd=0, highlightthickness=0, height=4,
            activestyle="none"
        )
        self.file_listbox.pack(side="left", fill="x", expand=True)

        sb = tk.Scrollbar(list_frame, command=self.file_listbox.yview, bg=BG2)
        sb.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=sb.set)

        btn_row = tk.Frame(card, bg=BG)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))
        self._btn(btn_row, "파일 추가", self._pick_pdf, ACCENT).pack(side="left", padx=(0,6))
        self._btn(btn_row, "목록 지우기", self._clear_files, "#555").pack(side="left")
        self.count_label = tk.Label(btn_row, text="0개 선택됨",
                                    bg=BG, fg=TEXT_DIM, font=FONT_SMALL)
        self.count_label.pack(side="right")

    def _output_card(self, parent):
        card = tk.LabelFrame(parent, text="  💾 출력 설정  ",
                             bg=BG, fg=ACCENT, font=FONT_BODY,
                             labelanchor="nw", bd=0,
                             highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 10))

        # 출력 폴더
        row = tk.Frame(card, bg=BG)
        row.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(row, text="저장 폴더", bg=BG, fg=TEXT_DIM, font=FONT_SMALL,
                 width=8, anchor="w").pack(side="left")
        self.out_entry = tk.Entry(row, textvariable=self.out_dir,
                                  bg=BG2, fg=TEXT, font=FONT_SMALL,
                                  insertbackground=TEXT, bd=0,
                                  highlightbackground=BORDER, highlightthickness=1)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self._btn(row, "찾아보기", self._pick_outdir, "#444").pack(side="right")

        # 포맷 선택
        fmt_row = tk.Frame(card, bg=BG)
        fmt_row.pack(fill="x", padx=12, pady=(4, 10))
        tk.Label(fmt_row, text="출력 형식", bg=BG, fg=TEXT_DIM, font=FONT_SMALL,
                 width=8, anchor="w").pack(side="left")

        for val, label, color in [
            ("xlsx", "📊  Excel (.xlsx)", GREEN),
            ("csv",  "📄  CSV (구글시트 호환)", ACCENT),
            ("both", "둘 다", TEXT_DIM),
        ]:
            rb = tk.Radiobutton(
                fmt_row, text=label, variable=self.fmt_var, value=val,
                bg=BG, fg=TEXT, selectcolor=BG2, activebackground=BG,
                activeforeground=TEXT, font=FONT_SMALL
            )
            rb.pack(side="left", padx=8)

    def _action_card(self, parent):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="x")

        self.run_btn = self._btn(frame, "🚀  변환 시작", self._run, ACCENT,
                                  font=("Apple SD Gothic Neo", 13, "bold"), pad=14)
        self.run_btn.pack(fill="x", ipady=6)

        self.progress = ttk.Progressbar(frame, mode="indeterminate",
                                        style="TProgressbar")
        self.progress.pack(fill="x", pady=(8, 0))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=BG2,
                        background=ACCENT, bordercolor=BG2)

    def _log_card(self, parent):
        card = tk.LabelFrame(parent, text="  🔍 변환 로그  ",
                             bg=BG, fg=ACCENT, font=FONT_BODY,
                             labelanchor="nw", bd=0,
                             highlightbackground=BORDER, highlightthickness=1,
                             width=280)
        card.pack(side="right", fill="both", padx=(0, 0))
        card.pack_propagate(False)

        self.log = LogBox(
            card, bg=BG2, fg=TEXT_DIM, font=FONT_MONO,
            bd=0, highlightthickness=0,
            wrap="word", state="disabled",
            insertbackground=TEXT,
        )
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

        self.log.log("준비됨. PDF를 선택하고 변환을 시작하세요.", "info")

    # ─────────────── 유틸 ───────────────
    def _btn(self, parent, text, cmd, color=ACCENT,
             font=None, pad=8):
        f = font or FONT_SMALL
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=color, fg=TEXT, activebackground=ACCENT2,
            activeforeground=TEXT, font=f, bd=0,
            padx=pad, pady=4, cursor="hand2",
            relief="flat"
        )
        return b

    def _pick_pdf(self):
        paths = filedialog.askopenfilenames(
            title="등기부등본 PDF 선택",
            filetypes=[("PDF 파일", "*.pdf"), ("모든 파일", "*.*")]
        )
        for p in paths:
            if p not in self.pdf_paths:
                self.pdf_paths.append(p)
                self.file_listbox.insert("end", os.path.basename(p))
        self.count_label.config(text=f"{len(self.pdf_paths)}개 선택됨")

    def _clear_files(self):
        self.pdf_paths.clear()
        self.file_listbox.delete(0, "end")
        self.count_label.config(text="0개 선택됨")

    def _pick_outdir(self):
        d = filedialog.askdirectory(title="저장 폴더 선택",
                                    initialdir=self.out_dir.get())
        if d:
            self.out_dir.set(d)

    # ─────────────── 변환 실행 ───────────────
    def _run(self):
        if not self.pdf_paths:
            messagebox.showwarning("파일 없음", "PDF 파일을 먼저 선택해주세요.")
            return
        out_dir = self.out_dir.get()
        os.makedirs(out_dir, exist_ok=True)

        self.run_btn.config(state="disabled", text="변환 중...")
        self.progress.start(12)
        self.log.clear()
        self.log.log(f"총 {len(self.pdf_paths)}개 파일 변환 시작", "header")

        fmt = self.fmt_var.get()
        paths = list(self.pdf_paths)

        def worker():
            ok = 0
            for i, pdf_path in enumerate(paths, 1):
                name = os.path.basename(pdf_path)
                self.q.put(("log", f"\n[{i}/{len(paths)}] {name}", "section"))
                try:
                    self.q.put(("log", "  └ 텍스트 추출 중...", "info"))
                    # PDF 유효성 사전 확인
                    try:
                        import pdfplumber as _plb
                        from parser import _has_cid as _hc
                        with _plb.open(pdf_path) as _pdf:
                            _pg0 = _pdf.pages[0]
                            _words = _pg0.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False, use_text_flow=False)
                            _pg_cnt = len(_pdf.pages)
                        self.q.put(("log", f"  └ PDF 확인: {_pg_cnt}페이지, 1페이지 단어수={len(_words)}", "info"))
                        if len(_words) == 0:
                            raise ValueError("PDF에서 텍스트를 추출할 수 없습니다. 스캔 이미지 PDF이거나 보호된 파일일 수 있습니다.")
                        if _hc(_words):
                            self.q.put(("log", "  └ CID 폰트 감지 → OCR 모드로 전환합니다...", "info"))
                    except Exception as _pre_e:
                        raise ValueError(f"PDF 열기 실패: {_pre_e}")

                    data = parse_registry(pdf_path)
                    meta = data.get("_meta", [{}])[0]
                    pages = meta.get("총페이지", "?")
                    # 파싱 결과 검증
                    sec_count = sum(1 for k,v in data.items() if k not in ("_meta","기본정보") and v)
                    self.q.put(("log", f"  └ {pages}페이지 파싱 완료 (섹션 {sec_count}개)", "ok"))
                    if sec_count == 0:
                        self.q.put(("log", "  ⚠ 경고: 파싱된 섹션이 없습니다. 등기부등본 PDF가 맞는지 확인해주세요.", "err"))

                    stem = os.path.splitext(name)[0]

                    if fmt in ("xlsx", "both"):
                        out = os.path.join(out_dir, stem + ".xlsx")
                        export_xlsx(data, out)
                        self.q.put(("log", f"  └ Excel 저장: {os.path.basename(out)}", "ok"))

                    if fmt in ("csv", "both"):
                        csv_dir = os.path.join(out_dir, stem + "_csv")
                        os.makedirs(csv_dir, exist_ok=True)
                        csvs = export_csv(data, csv_dir)
                        self.q.put(("log", f"  └ CSV {len(csvs)}개 저장: {stem}_csv/", "ok"))

                    ok += 1
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    self.q.put(("log", f"  ✗ 오류: {e}", "err"))
                    self.q.put(("log", f"{tb}", "err"))

            self.q.put(("done", ok, len(paths)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "log":
                    self.log.log(item[1], item[2])
                elif item[0] == "done":
                    ok, total = item[1], item[2]
                    self.progress.stop()
                    self.run_btn.config(state="normal", text="🚀  변환 시작")
                    if ok == total:
                        self.log.log(f"\n✅ 완료! {ok}개 파일 변환 성공", "ok")
                        out = self.out_dir.get()
                        if sys.platform == "darwin":
                            os.system(f'open "{out}"')
                        elif sys.platform == "win32":
                            os.startfile(out)
                    else:
                        self.log.log(
                            f"\n⚠ {ok}/{total}개 성공 ({total-ok}개 실패)", "err")
        except queue.Empty:
            pass
        self.after(80, self._poll_queue)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
