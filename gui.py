#!/usr/bin/env python3
"""
zrktex GUI — Graphical LaTeX editor with live PDF preview.
Usage: python gui.py [file.tex]
"""

import subprocess, sys, os, threading, re, shutil
from pathlib import Path

# ── Auto-install ───────────────────────────────────────────────────────────────
def _ensure(pkg, imp=None):
    try:
        __import__(imp or pkg)
    except ImportError:
        print(f"Installing {pkg}…", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg],
                              stdout=subprocess.DEVNULL)

_ensure("pygments")
_ensure("Pillow", "PIL")
_ensure("PyMuPDF", "fitz")
_ensure("matplotlib")
_ensure("numpy")

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from pygments.lexers import TexLexer as _TexLex
    _LEX = _TexLex()
    HAS_PYG = True
except Exception:
    HAS_PYG = False

try:
    import fitz
    HAS_FITZ = True
except Exception:
    HAS_FITZ = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except Exception:
    HAS_PIL = False

try:
    import matplotlib
    matplotlib.use("Agg")           # non-interactive, must come first
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from mpl_toolkits.mplot3d import Axes3D   # noqa: F401 — registers projection
    import numpy as np
    HAS_MPL = True
except Exception:
    HAS_MPL = False

# ── LaTeX completions (from editor.py) ────────────────────────────────────────
COMPLETIONS = sorted(set([
    r"\begin", r"\end", r"\documentclass", r"\usepackage",
    r"\textbf", r"\textit", r"\texttt", r"\textrm", r"\textsf",
    r"\emph", r"\underline", r"\text", r"\mbox",
    r"\section", r"\subsection", r"\subsubsection",
    r"\paragraph", r"\subparagraph", r"\chapter", r"\part", r"\appendix",
    r"\label", r"\ref", r"\eqref", r"\pageref", r"\nameref",
    r"\cite", r"\citep", r"\citet", r"\bibliography", r"\bibliographystyle",
    r"\includegraphics", r"\caption", r"\centering",
    r"\frac", r"\dfrac", r"\tfrac", r"\sqrt",
    r"\sum", r"\int", r"\iint", r"\iiint", r"\oint",
    r"\prod", r"\lim", r"\sup", r"\inf", r"\max", r"\min",
    r"\alpha", r"\beta", r"\gamma", r"\delta", r"\epsilon", r"\varepsilon",
    r"\zeta", r"\eta", r"\theta", r"\vartheta", r"\iota", r"\kappa",
    r"\lambda", r"\mu", r"\nu", r"\xi", r"\pi", r"\varpi",
    r"\rho", r"\sigma", r"\tau", r"\upsilon", r"\phi", r"\varphi",
    r"\chi", r"\psi", r"\omega",
    r"\Gamma", r"\Delta", r"\Theta", r"\Lambda", r"\Xi",
    r"\Pi", r"\Sigma", r"\Upsilon", r"\Phi", r"\Psi", r"\Omega",
    r"\left", r"\right", r"\middle",
    r"\big", r"\Big", r"\bigg", r"\Bigg",
    r"\vspace", r"\hspace", r"\noindent", r"\par", r"\hline",
    r"\item", r"\maketitle", r"\tableofcontents",
    r"\newpage", r"\clearpage", r"\pagebreak",
    r"\title", r"\author", r"\date", r"\today", r"\abstract",
    r"\mathbf", r"\mathrm", r"\mathit", r"\mathcal", r"\mathbb", r"\mathfrak",
    r"\overline", r"\hat", r"\bar", r"\vec", r"\tilde", r"\dot", r"\ddot",
    r"\leq", r"\geq", r"\neq", r"\approx", r"\equiv", r"\sim",
    r"\cdot", r"\times", r"\div", r"\pm", r"\mp",
    r"\infty", r"\partial", r"\nabla", r"\forall", r"\exists",
    r"\in", r"\notin", r"\subset", r"\supset", r"\subseteq",
    r"\cup", r"\cap", r"\setminus", r"\emptyset",
    r"\rightarrow", r"\leftarrow", r"\leftrightarrow",
    r"\Rightarrow", r"\Leftarrow", r"\Leftrightarrow",
    r"\mapsto", r"\to", r"\gets",
    r"\uparrow", r"\downarrow",
    r"\ldots", r"\cdots", r"\vdots", r"\ddots", r"\qquad", r"\quad",
    r"\newcommand", r"\renewcommand", r"\newenvironment",
    r"\footnote", r"\input", r"\include",
    r"\tiny", r"\scriptsize", r"\footnotesize", r"\small",
    r"\normalsize", r"\large", r"\Large", r"\LARGE", r"\huge", r"\Huge",
    r"\color", r"\textcolor", r"\colorbox",
    r"\hfill", r"\vfill",
    r"\sin", r"\cos", r"\tan", r"\log", r"\ln", r"\exp",
    r"\binom", r"\pmod", r"\gcd",
    r"\verb", r"\index", r"\centering", r"\raggedleft", r"\raggedright",
    r"\plot",
]))

# ── Dark theme colours ─────────────────────────────────────────────────────────
T = {
    "bg":      "#1e1e1e",
    "fg":      "#d4d4d4",
    "ln_bg":   "#252526",
    "ln_fg":   "#858585",
    "sel":     "#264f78",
    "cmd":     "#4ec9b0",   # \commands  — teal
    "cmt":     "#6a9955",   # % comments — green
    "brc":     "#ffd700",   # {} [] braces — gold
    "num":     "#b5cea8",   # numbers — sage
    "mth":     "#ce9178",   # $math$ — peach
    "err_bg":  "#5a1d1d",
    "tbar":    "#2d2d2d",
    "stat":    "#007acc",
    "stat_fg": "#ffffff",
    "ac_bg":   "#252526",
    "ac_sel":  "#094771",
    "ac_fg":   "#d4d4d4",
    "sash":    "#3c3c3c",
    "out_bg":  "#1e1e1e",
    "ok":      "#4ec9b0",
    "err":     "#f48771",
}

FONT    = ("Consolas", 12)
FONT_SM = ("Consolas", 10)
FONT_UI = ("Segoe UI", 9)


# ── Line number gutter ────────────────────────────────────────────────────────
class LineNumbers(tk.Canvas):
    """Synced line-number gutter for a Text widget."""

    WIDTH = 52

    def __init__(self, master, text: tk.Text, **kw):
        kw.setdefault("bg", T["ln_bg"])
        kw.setdefault("bd", 0)
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("width", self.WIDTH)
        super().__init__(master, **kw)
        self._text = text
        # Proxy yview so scrolling redraws line numbers too
        self._text.bind("<<Modified>>", self._redraw, add=True)
        self._text.bind("<Configure>",  self._redraw, add=True)
        self._text.bind("<KeyRelease>", self._redraw, add=True)
        self._text.bind("<ButtonRelease>", self._redraw, add=True)

    def _redraw(self, *_):
        self.delete("all")
        # Separator line
        self.create_line(self.WIDTH - 1, 0, self.WIDTH - 1, self.winfo_height(),
                         fill="#3c3c3c")
        idx = self._text.index("@0,0")
        while True:
            dline = self._text.dlineinfo(idx)
            if dline is None:
                break
            y = dline[1]
            lineno = int(str(idx).split(".")[0])
            self.create_text(self.WIDTH - 8, y, anchor="ne",
                             text=str(lineno),
                             fill=T["ln_fg"], font=FONT_SM)
            nxt = self._text.index(f"{idx}+1line")
            if nxt == idx:
                break
            idx = nxt


# ── Autocomplete popup ────────────────────────────────────────────────────────
class AutoComplete:
    """Floating completion list anchored near the cursor."""

    MAX = 10

    def __init__(self, editor: tk.Text, root: tk.Tk):
        self._ed   = editor
        self._root = root
        self._win: tk.Toplevel | None = None
        self._lb:  tk.Listbox  | None = None
        self._items: list[str] = []
        self._prefix = ""

    # ── public ──

    def update(self):
        prefix = self._get_prefix()
        if not prefix:
            self.hide()
            return
        matches = [c for c in COMPLETIONS if c.startswith(prefix)]
        if matches:
            self._show(matches, prefix)
        else:
            self.hide()

    def visible(self) -> bool:
        return self._win is not None

    def move(self, delta: int):
        if not self._lb:
            return
        sel = self._lb.curselection()
        idx = (sel[0] if sel else 0) + delta
        idx = max(0, min(idx, len(self._items) - 1))
        self._lb.selection_clear(0, tk.END)
        self._lb.selection_set(idx)
        self._lb.see(idx)

    def apply(self) -> bool:
        if not self._lb:
            return False
        sel = self._lb.curselection()
        if not sel:
            return False
        chosen = self._items[sel[0]]
        ins = self._ed.index(tk.INSERT)
        start = f"{ins} -{len(self._prefix)}c"
        self._ed.delete(start, ins)
        self._ed.insert(tk.INSERT, chosen)
        self.hide()
        return True

    def hide(self):
        if self._win:
            self._win.destroy()
            self._win = None
            self._lb  = None
        self._items  = []
        self._prefix = ""

    # ── private ──

    def _get_prefix(self) -> str:
        line = self._ed.get("insert linestart", "insert")
        m = re.search(r"\\[a-zA-Z]*$", line)
        return m.group(0) if m else ""

    def _show(self, items: list[str], prefix: str):
        self._items  = items[: self.MAX]
        self._prefix = prefix
        if self._win is None:
            self._win = tk.Toplevel(self._root)
            self._win.overrideredirect(True)
            self._win.attributes("-topmost", True)
            self._lb = tk.Listbox(
                self._win,
                bg=T["ac_bg"], fg=T["ac_fg"],
                selectbackground=T["ac_sel"],
                selectforeground=T["ac_fg"],
                font=FONT_SM, bd=0,
                highlightthickness=1,
                highlightbackground="#007acc",
                activestyle="none",
            )
            self._lb.pack(fill=tk.BOTH, expand=True)
            self._lb.bind("<ButtonRelease-1>", lambda _: self.apply())
        self._lb.delete(0, tk.END)
        for it in self._items:
            self._lb.insert(tk.END, it)
        self._lb.selection_set(0)
        self._place()

    def _place(self):
        try:
            bbox = self._ed.bbox(tk.INSERT)
        except Exception:
            return
        if bbox is None:
            return
        x = self._ed.winfo_rootx() + bbox[0]
        y = self._ed.winfo_rooty() + bbox[1] + bbox[3] + 2
        h = len(self._items) * 19 + 4
        w = 230
        self._win.geometry(f"{w}x{h}+{x}+{y}")


# ── PDF viewer ────────────────────────────────────────────────────────────────
class PDFViewer(tk.Frame):
    """Scrollable canvas that renders a PDF via PyMuPDF."""

    def __init__(self, master, **kw):
        kw.setdefault("bg", T["tbar"])
        super().__init__(master, **kw)
        self._zoom   = 1.0
        self._path:  str | None = None
        self._imgs:  list = []   # keep refs alive

        # ── header bar ──
        hdr = tk.Frame(self, bg=T["tbar"], height=28)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="PDF Preview", bg=T["tbar"], fg=T["ln_fg"],
                 font=FONT_UI).pack(side=tk.LEFT, padx=8)
        tk.Button(hdr, text="+", command=self._zoom_in,
                  bg=T["tbar"], fg=T["fg"], relief=tk.FLAT,
                  font=("Consolas", 11), padx=4, pady=0).pack(side=tk.RIGHT, padx=2, pady=3)
        self._zlbl = tk.Label(hdr, text="100%", bg=T["tbar"], fg=T["fg"],
                               font=FONT_UI, width=5)
        self._zlbl.pack(side=tk.RIGHT)
        tk.Button(hdr, text="−", command=self._zoom_out,
                  bg=T["tbar"], fg=T["fg"], relief=tk.FLAT,
                  font=("Consolas", 11), padx=4, pady=0).pack(side=tk.RIGHT, padx=2, pady=3)

        # ── scrollable canvas ──
        inner = tk.Frame(self, bg=T["bg"])
        inner.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(inner, bg="#3a3a3a", bd=0,
                                  highlightthickness=0)
        vsb = ttk.Scrollbar(inner, orient=tk.VERTICAL,
                             command=self._canvas.yview)
        hsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL,
                             command=self._canvas.xview)
        self._canvas.configure(yscrollcommand=vsb.set,
                                xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._canvas.bind("<MouseWheel>",
                          lambda e: self._canvas.yview_scroll(
                              -1 * (e.delta // 120), "units"))
        self._placeholder()

    def _placeholder(self):
        self._canvas.delete("all")
        self._canvas.create_text(
            140, 100,
            text="No PDF yet.\n\nPress F5 to compile.",
            fill="#666", font=("Consolas", 11), justify=tk.CENTER,
        )

    def load(self, path: str):
        self._path = path
        self._render()

    def _render(self):
        if not HAS_FITZ or not HAS_PIL:
            return
        if not self._path or not os.path.exists(self._path):
            return
        try:
            doc = fitz.open(self._path)
        except Exception:
            return

        self._canvas.delete("all")
        self._imgs.clear()
        mat = fitz.Matrix(self._zoom * 1.5, self._zoom * 1.5)
        y   = 12
        max_w = 0

        for page in doc:
            pix   = page.get_pixmap(matrix=mat, alpha=False)
            img   = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            photo = ImageTk.PhotoImage(img)
            self._imgs.append(photo)
            # shadow
            self._canvas.create_rectangle(
                14, y + 3, 14 + pix.width + 1, y + pix.height + 1,
                fill="#111", outline="",
            )
            self._canvas.create_image(12, y, anchor="nw", image=photo)
            y     += pix.height + 18
            max_w  = max(max_w, pix.width)

        doc.close()
        self._canvas.configure(scrollregion=(0, 0, max_w + 24, y))

    def _zoom_in(self):
        self._zoom = min(3.0, self._zoom + 0.25)
        self._zlbl.config(text=f"{int(self._zoom * 100)}%")
        self._render()

    def _zoom_out(self):
        self._zoom = max(0.25, self._zoom - 0.25)
        self._zlbl.config(text=f"{int(self._zoom * 100)}%")
        self._render()


# ── Plot preprocessor ────────────────────────────────────────────────────────
class PlotProcessor:
    """
    Finds every  \\plot[options]{expression}  in a .tex document,
    renders a matplotlib figure for each one, saves it as a PDF in
    ./_zrkplots/, and returns the modified tex content with the command
    replaced by \\includegraphics{...}.

    Supported plot types (type= option):
      2d          — one or more real functions of x  (default)
      parametric  — x(t), y(t)
      parametric3d / curve3d — x(t), y(t), z(t)
      3d / surface — f(x, y) surface plot
      complex     — domain-colouring of f(z)
      vector / field — 2-D vector field u(x,y), v(x,y)
                        use style=stream for stream-lines

    Common options:
      xmin, xmax, ymin, ymax, zmin, zmax   — axis limits
      tmin, tmax                            — parameter range
      title, xlabel, ylabel, zlabel         — labels
      figwidth, figheight                   — figure size in inches
      legend                                — semicolon-separated labels
      resolution                            — grid density (default 80/400)
      density                               — quiver grid points (default 20)
      style                                 — quiver | stream (vector only)
      width                                 — LaTeX image width (default 0.8\\linewidth)

    Examples:
      \\plot{sin(x)}
      \\plot[xmin=-pi, xmax=pi, title=Sine]{sin(x), cos(x)}
      \\plot[type=parametric, tmin=0, tmax=6.283]{cos(t), sin(t)}
      \\plot[type=3d, xmin=-3, xmax=3, ymin=-3, ymax=3]{sin(x)*cos(y)}
      \\plot[type=complex, xmin=-2, xmax=2, ymin=-2, ymax=2]{z**2 - 1}
      \\plot[type=vector, style=stream]{-y, x}
      \\plot[type=curve3d, tmin=0, tmax=12.566]{cos(t), sin(t), t/4}
    """

    # Safe namespace for eval
    _NS: dict = {}   # filled lazily after HAS_MPL is known

    @classmethod
    def _build_ns(cls):
        if cls._NS or not HAS_MPL:
            return
        cls._NS = {
            "__builtins__": {},
            "pi": np.pi, "e": np.e, "inf": np.inf, "nan": np.nan,
            "i": 1j,
            # trig
            "sin": np.sin, "cos": np.cos, "tan": np.tan,
            "sec": lambda x: 1.0 / np.cos(x),
            "csc": lambda x: 1.0 / np.sin(x),
            "cot": lambda x: np.cos(x) / np.sin(x),
            "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
            "arcsin": np.arcsin, "arccos": np.arccos,
            "arctan": np.arctan, "arctan2": np.arctan2,
            # exp / log
            "exp": np.exp, "log": np.log, "log2": np.log2,
            "log10": np.log10, "ln": np.log,
            # misc
            "sqrt": np.sqrt, "abs": np.abs, "sign": np.sign,
            "floor": np.floor, "ceil": np.ceil,
            "real": np.real, "imag": np.imag,
            "re": np.real,   "im": np.imag,
            "conj": np.conj, "angle": np.angle, "arg": np.angle,
            "norm": np.linalg.norm,
            "np": np,
        }

    def __init__(self, tex_path: str):
        self._build_ns()
        self.tex_path  = Path(tex_path)
        self.plots_dir = self.tex_path.parent / "_zrkplots"
        self.plots_dir.mkdir(exist_ok=True)
        self.counter   = 0

    # ── public ──

    def process(self, content: str) -> str:
        """Replace all \\plot calls and return the modified content."""
        spans = self._find_all(content)
        if not spans:
            return content
        out = []
        prev = 0
        for start, end, opts_raw, expr_raw in spans:
            out.append(content[prev:start])
            out.append(self._render_one(opts_raw, expr_raw))
            prev = end
        out.append(content[prev:])
        return "".join(out)

    # ── parser ──

    def _find_all(self, src: str):
        """Return list of (start, end, opts_str, expr_str) for every \\plot."""
        results = []
        i = 0
        while True:
            pos = src.find(r"\plot", i)
            if pos == -1:
                break
            j = pos + 5
            # skip whitespace
            while j < len(src) and src[j] in " \t":
                j += 1
            # optional [options]
            opts_raw = ""
            if j < len(src) and src[j] == "[":
                depth, k = 0, j
                while k < len(src):
                    if src[k] == "[":
                        depth += 1
                    elif src[k] == "]":
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                opts_raw = src[j + 1 : k]
                j = k + 1
            # skip whitespace
            while j < len(src) and src[j] in " \t\n":
                j += 1
            if j >= len(src) or src[j] != "{":
                i = pos + 1
                continue
            # brace-match the expression
            depth, k = 0, j
            while k < len(src):
                if src[k] == "{":
                    depth += 1
                elif src[k] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            expr_raw = src[j + 1 : k]
            results.append((pos, k + 1, opts_raw, expr_raw))
            i = k + 1
        return results

    def _parse_opts(self, s: str) -> dict[str, str]:
        """Split 'key=value, key=value' respecting parentheses depth."""
        opts: dict[str, str] = {}
        depth, cur = 0, []
        for ch in s:
            if ch == "(":
                depth += 1; cur.append(ch)
            elif ch == ")":
                depth -= 1; cur.append(ch)
            elif ch == "," and depth == 0:
                self._store_kv(opts, "".join(cur))
                cur = []
            else:
                cur.append(ch)
        self._store_kv(opts, "".join(cur))
        return opts

    @staticmethod
    def _store_kv(d: dict, s: str):
        s = s.strip()
        if "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()

    def _fval(self, opts: dict, key: str, default: float) -> float:
        v = opts.get(key)
        if v is None:
            return default
        try:
            return float(eval(v, {"pi": np.pi, "e": np.e, "__builtins__": {}}))
        except Exception:
            return default

    # ── figure dispatch ──

    def _render_one(self, opts_raw: str, expr_raw: str) -> str:
        self.counter += 1
        opts = self._parse_opts(opts_raw)
        ptype = opts.get("type", "2d").lower().replace("-", "").replace("_", "")
        fw = self._fval(opts, "figwidth",  5.5)
        fh = self._fval(opts, "figheight", 4.0)

        out_path = str(self.plots_dir / f"zrkplot_{self.counter:03d}.pdf")
        err_msg  = None
        try:
            self._set_style()
            if ptype in ("2d", "real"):
                self._plot_2d(opts, expr_raw, fw, fh)
            elif ptype in ("parametric", "param"):
                self._plot_parametric(opts, expr_raw, fw, fh)
            elif ptype in ("parametric3d", "param3d", "curve3d"):
                self._plot_param3d(opts, expr_raw, fw, fh)
            elif ptype in ("3d", "surface"):
                self._plot_3d(opts, expr_raw, fw, fh)
            elif ptype == "complex":
                self._plot_complex(opts, expr_raw, fw, fh)
            elif ptype in ("vector", "field", "quiver"):
                self._plot_vector(opts, expr_raw, fw, fh)
            else:
                self._plot_2d(opts, expr_raw, fw, fh)
            plt.tight_layout()
            plt.savefig(out_path, format="pdf", bbox_inches="tight", dpi=150)
        except Exception as ex:
            err_msg = str(ex)
        finally:
            plt.close("all")

        if err_msg:
            safe = re.sub(r"[{}\\]", lambda m: {"\\": r"\textbackslash{}",
                                                  "{": r"\{", "}": r"\}"}[m.group()],
                          err_msg)
            return r"\fbox{\texttt{\small Plot error: " + safe + "}}"

        rel = os.path.relpath(out_path, self.tex_path.parent).replace("\\", "/")
        width = opts.get("width", r"0.8\linewidth")
        return f"\\includegraphics[width={width}]{{{rel}}}"

    # ── style ──

    @staticmethod
    def _set_style():
        for name in ("seaborn-v0_8-whitegrid", "seaborn-whitegrid"):
            try:
                plt.style.use(name)
                return
            except OSError:
                pass

    # ── eval helper ──

    def _ev(self, expr: str, local_vars: dict):
        env = {**self._NS, **local_vars}
        return eval(expr, env)  # type: ignore[arg-type]

    # ── 2-D real ──

    def _plot_2d(self, opts, expr, fw, fh):
        xmin = self._fval(opts, "xmin", -5.0)
        xmax = self._fval(opts, "xmax",  5.0)
        x    = np.linspace(xmin, xmax, 1200)

        exprs   = [e.strip() for e in expr.split(",") if e.strip()]
        legends = [l.strip() for l in opts.get("legend", "").split(";") if l.strip()]

        fig, ax = plt.subplots(figsize=(fw, fh))
        for idx, e in enumerate(exprs):
            with np.errstate(all="ignore"):
                y = self._ev(e, {"x": x})
            y = np.where(np.isfinite(y.astype(float)), y, np.nan)
            lbl = legends[idx] if idx < len(legends) else f"${e}$"
            ax.plot(x, y, label=lbl, linewidth=1.8)

        self._set_lims(ax, opts, axis="y")
        ax.set_xlabel(opts.get("xlabel", "$x$"))
        ax.set_ylabel(opts.get("ylabel", "$y$"))
        if "title" in opts:
            ax.set_title(opts["title"])
        if len(exprs) > 1 or legends:
            ax.legend(fontsize=9)
        ax.axhline(0, color="k", linewidth=0.5, zorder=0)
        ax.axvline(0, color="k", linewidth=0.5, zorder=0)

    # ── parametric 2-D ──

    def _plot_parametric(self, opts, expr, fw, fh):
        tmin = self._fval(opts, "tmin", 0.0)
        tmax = self._fval(opts, "tmax", 2 * np.pi)
        t    = np.linspace(tmin, tmax, 2000)

        parts = [p.strip() for p in self._split_top(expr)]
        if len(parts) < 2:
            raise ValueError("Parametric 2-D needs two expressions: x(t), y(t)")
        xv = np.asarray(self._ev(parts[0], {"t": t}), float)
        yv = np.asarray(self._ev(parts[1], {"t": t}), float)

        fig, ax = plt.subplots(figsize=(fw, fh))
        ax.plot(xv, yv, linewidth=1.8)
        self._set_lims(ax, opts, axis="both")
        ax.set_xlabel(opts.get("xlabel", "$x$"))
        ax.set_ylabel(opts.get("ylabel", "$y$"))
        if "title" in opts:
            ax.set_title(opts["title"])
        ax.set_aspect("equal", adjustable="datalim")
        ax.axhline(0, color="k", linewidth=0.5, zorder=0)
        ax.axvline(0, color="k", linewidth=0.5, zorder=0)

    # ── parametric 3-D curve ──

    def _plot_param3d(self, opts, expr, fw, fh):
        tmin = self._fval(opts, "tmin", 0.0)
        tmax = self._fval(opts, "tmax", 2 * np.pi)
        t    = np.linspace(tmin, tmax, 3000)

        parts = [p.strip() for p in self._split_top(expr)]
        if len(parts) < 3:
            raise ValueError("3-D curve needs three expressions: x(t), y(t), z(t)")
        xv = np.asarray(self._ev(parts[0], {"t": t}), float)
        yv = np.asarray(self._ev(parts[1], {"t": t}), float)
        zv = np.asarray(self._ev(parts[2], {"t": t}), float)

        fig = plt.figure(figsize=(fw, fh))
        ax  = fig.add_subplot(111, projection="3d")
        # colour by arc-length parameter
        ax.plot(xv, yv, zv, linewidth=1.5)
        ax.set_xlabel(opts.get("xlabel", "$x$"))
        ax.set_ylabel(opts.get("ylabel", "$y$"))
        ax.set_zlabel(opts.get("zlabel", "$z$"))
        if "title" in opts:
            ax.set_title(opts["title"])

    # ── 3-D surface ──

    def _plot_3d(self, opts, expr, fw, fh):
        xmin = self._fval(opts, "xmin", -5.0)
        xmax = self._fval(opts, "xmax",  5.0)
        ymin = self._fval(opts, "ymin", -5.0)
        ymax = self._fval(opts, "ymax",  5.0)
        N    = int(self._fval(opts, "resolution", 80))

        xi = np.linspace(xmin, xmax, N)
        yi = np.linspace(ymin, ymax, N)
        X, Y = np.meshgrid(xi, yi)

        with np.errstate(all="ignore"):
            Z = np.asarray(self._ev(expr.strip(), {"x": X, "y": Y}), float)
        Z = np.where(np.isfinite(Z), Z, np.nan)

        fig = plt.figure(figsize=(fw, fh))
        ax  = fig.add_subplot(111, projection="3d")
        surf = ax.plot_surface(X, Y, Z, cmap="viridis",
                               linewidth=0, antialiased=True, alpha=0.92)
        fig.colorbar(surf, ax=ax, shrink=0.5, pad=0.08)
        ax.set_xlabel(opts.get("xlabel", "$x$"))
        ax.set_ylabel(opts.get("ylabel", "$y$"))
        ax.set_zlabel(opts.get("zlabel", "$z$"))
        if opts.get("zmin") and opts.get("zmax"):
            ax.set_zlim(self._fval(opts, "zmin", None),
                        self._fval(opts, "zmax", None))
        if "title" in opts:
            ax.set_title(opts["title"])

    # ── complex domain colouring ──

    def _plot_complex(self, opts, expr, fw, fh):
        xmin = self._fval(opts, "xmin", -3.0)
        xmax = self._fval(opts, "xmax",  3.0)
        ymin = self._fval(opts, "ymin", -3.0)
        ymax = self._fval(opts, "ymax",  3.0)
        N    = int(self._fval(opts, "resolution", 500))

        xi = np.linspace(xmin, xmax, N)
        yi = np.linspace(ymin, ymax, N)
        Xg, Yg = np.meshgrid(xi, yi)
        Z = Xg + 1j * Yg

        with np.errstate(all="ignore"):
            W = np.asarray(self._ev(expr.strip(), {"z": Z}), complex)

        # Domain colouring: hue = arg(W), brightness shaped by |W|
        arg  = np.angle(W)                             # −π … π
        mod  = np.abs(W)
        hue  = (arg + np.pi) / (2 * np.pi)            # 0 … 1
        val  = 1.0 - 0.5 * np.exp(-mod)               # asymptotes to 1
        # log-sawtooth contour lines (show poles/zeros)
        log_m   = np.log2(np.where(mod > 0, mod, 1e-12))
        contour = 0.5 + 0.15 * np.sign(np.cos(2 * np.pi * log_m))
        val     = np.clip(val * contour, 0, 1)
        sat     = np.full_like(hue, 0.85)

        rgb = mcolors.hsv_to_rgb(np.stack([hue, sat, val], axis=-1))

        fig, ax = plt.subplots(figsize=(fw, fh))
        ax.imshow(rgb, extent=[xmin, xmax, ymin, ymax],
                  origin="lower", aspect="equal", interpolation="bilinear")
        ax.set_xlabel(opts.get("xlabel", r"$\mathrm{Re}(z)$"))
        ax.set_ylabel(opts.get("ylabel", r"$\mathrm{Im}(z)$"))
        title = opts.get("title", f"Domain colouring:  $f(z) = {expr.strip()}$")
        ax.set_title(title)

    # ── 2-D vector field ──

    def _plot_vector(self, opts, expr, fw, fh):
        xmin = self._fval(opts, "xmin", -5.0)
        xmax = self._fval(opts, "xmax",  5.0)
        ymin = self._fval(opts, "ymin", -5.0)
        ymax = self._fval(opts, "ymax",  5.0)
        dens = int(self._fval(opts, "density", 20))

        parts = [p.strip() for p in self._split_top(expr)]
        if len(parts) < 2:
            raise ValueError("Vector field needs two expressions: u(x,y), v(x,y)")

        style = opts.get("style", "quiver").lower()
        fig, ax = plt.subplots(figsize=(fw, fh))

        if style == "stream":
            # high-res grid for stream-lines
            N  = max(dens * 10, 200)
            xi = np.linspace(xmin, xmax, N)
            yi = np.linspace(ymin, ymax, N)
            Xg, Yg = np.meshgrid(xi, yi)
            with np.errstate(all="ignore"):
                U = np.asarray(self._ev(parts[0], {"x": Xg, "y": Yg}), float)
                V = np.asarray(self._ev(parts[1], {"x": Xg, "y": Yg}), float)
            spd = np.sqrt(U**2 + V**2)
            ax.streamplot(xi, yi, U, V, color=spd,
                          cmap="viridis", density=1.5, linewidth=1.2)
        else:
            xi = np.linspace(xmin, xmax, dens)
            yi = np.linspace(ymin, ymax, dens)
            Xg, Yg = np.meshgrid(xi, yi)
            with np.errstate(all="ignore"):
                U = np.asarray(self._ev(parts[0], {"x": Xg, "y": Yg}), float)
                V = np.asarray(self._ev(parts[1], {"x": Xg, "y": Yg}), float)
            mag  = np.sqrt(U**2 + V**2)
            safe = np.where(mag == 0, 1.0, mag)
            q = ax.quiver(Xg, Yg, U / safe, V / safe, mag,
                          cmap="viridis", pivot="mid", scale=dens * 1.5)
            plt.colorbar(q, ax=ax, label="magnitude")

        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel(opts.get("xlabel", "$x$"))
        ax.set_ylabel(opts.get("ylabel", "$y$"))
        ax.set_aspect("equal")
        if "title" in opts:
            ax.set_title(opts["title"])
        ax.axhline(0, color="k", linewidth=0.5, zorder=0)
        ax.axvline(0, color="k", linewidth=0.5, zorder=0)

    # ── helpers ──

    @staticmethod
    def _split_top(s: str) -> list[str]:
        """Split on commas at paren-depth 0."""
        parts, depth, cur = [], 0, []
        for ch in s:
            if ch == "(":
                depth += 1; cur.append(ch)
            elif ch == ")":
                depth -= 1; cur.append(ch)
            elif ch == "," and depth == 0:
                parts.append("".join(cur)); cur = []
            else:
                cur.append(ch)
        if cur:
            parts.append("".join(cur))
        return parts

    @staticmethod
    def _set_lims(ax, opts: dict, axis: str = "both"):
        xmin = opts.get("xmin"); xmax = opts.get("xmax")
        ymin = opts.get("ymin"); ymax = opts.get("ymax")
        if axis in ("x", "both") and xmin and xmax:
            try:
                ax.set_xlim(float(eval(xmin, {"pi": np.pi, "e": np.e, "__builtins__": {}})),
                            float(eval(xmax, {"pi": np.pi, "e": np.e, "__builtins__": {}})))
            except Exception:
                pass
        if axis in ("y", "both") and ymin and ymax:
            try:
                ax.set_ylim(float(eval(ymin, {"pi": np.pi, "e": np.e, "__builtins__": {}})),
                            float(eval(ymax, {"pi": np.pi, "e": np.e, "__builtins__": {}})))
            except Exception:
                pass


# ── Main application ──────────────────────────────────────────────────────────
class App:
    def __init__(self):
        self.filepath: str | None = None
        self.dirty = False
        self._hl_job = None

        # ── window ──
        self.root = tk.Tk()
        self.root.title("zrktex")
        self.root.geometry("1280x800")
        self.root.configure(bg=T["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self._apply_style()

        # ── layout ──
        self._build_menu()
        self._build_toolbar()

        # centre paned area
        self._paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self._paned.pack(fill=tk.BOTH, expand=True)

        ed_frame = tk.Frame(self._paned, bg=T["bg"])
        self._paned.add(ed_frame, weight=3)

        self._build_editor(ed_frame)

        self.pdf = PDFViewer(self._paned)
        self._paned.add(self.pdf, weight=2)
        self._pdf_visible = True

        self._build_statusbar()
        self._build_output()

        # ── autocomplete ──
        self._ac = AutoComplete(self.editor, self.root)

        # ── keybindings ──
        self._bind()

        # ── initial content ──
        if len(sys.argv) > 1:
            self._open_file(sys.argv[1])
        else:
            self._new_template()

    # ── style ─────────────────────────────────────────────────────────────────

    def _apply_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame",        background=T["bg"])
        s.configure("TPanedwindow",  background=T["sash"])
        s.configure("Sash",          sashthickness=5, sashpad=2)
        for orient in ("Vertical", "Horizontal"):
            s.configure(f"{orient}.TScrollbar",
                        troughcolor=T["bg"], background=T["tbar"],
                        arrowcolor=T["ln_fg"])

    # ── menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        def menu(parent):
            return tk.Menu(parent, bg=T["tbar"], fg=T["fg"],
                           activebackground=T["sel"],
                           activeforeground=T["fg"],
                           bd=0, tearoff=False)

        mb = menu(self.root)
        self.root.config(menu=mb)

        # File
        fm = menu(mb)
        mb.add_cascade(label="File", menu=fm)
        fm.add_command(label="New             Ctrl+N",      command=self._new)
        fm.add_command(label="Open…           Ctrl+O",      command=self._open_dialog)
        fm.add_command(label="Save            Ctrl+S",      command=self._save)
        fm.add_command(label="Save As…        Ctrl+Shift+S", command=self._save_as)
        fm.add_separator()
        fm.add_command(label="Quit            Ctrl+Q",      command=self._quit)

        # Edit
        em = menu(mb)
        mb.add_cascade(label="Edit", menu=em)
        em.add_command(label="Undo   Ctrl+Z", command=lambda: self.editor.event_generate("<<Undo>>"))
        em.add_command(label="Redo   Ctrl+Y", command=lambda: self.editor.event_generate("<<Redo>>"))
        em.add_separator()
        em.add_command(label="Find   Ctrl+F", command=self._find_dialog)

        # LaTeX
        lm = menu(mb)
        mb.add_cascade(label="LaTeX", menu=lm)
        lm.add_command(label="Compile           F5", command=self._compile)
        lm.add_command(label="Compile & View    F6", command=self._compile_view)
        lm.add_separator()
        lm.add_command(label="Insert \\begin{}",         command=self._insert_begin)
        lm.add_command(label="Insert equation",         command=self._insert_equation)
        lm.add_command(label="Insert \\frac{}{}",        command=self._insert_frac)
        lm.add_separator()
        lm.add_command(label="Insert \\plot — 2-D",        command=lambda: self._insert_plot("2d"))
        lm.add_command(label="Insert \\plot — parametric", command=lambda: self._insert_plot("parametric"))
        lm.add_command(label="Insert \\plot — 3-D surface", command=lambda: self._insert_plot("3d"))
        lm.add_command(label="Insert \\plot — complex",    command=lambda: self._insert_plot("complex"))
        lm.add_command(label="Insert \\plot — vector field", command=lambda: self._insert_plot("vector"))

        # View
        vm = menu(mb)
        mb.add_cascade(label="View", menu=vm)
        vm.add_command(label="Toggle PDF panel   F7",    command=self._toggle_pdf)
        vm.add_command(label="Toggle output      F8",    command=self._toggle_output)

    # ── toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=T["tbar"], height=34)
        tb.pack(fill=tk.X, side=tk.TOP)
        tb.pack_propagate(False)

        def tbtn(text, cmd):
            b = tk.Button(
                tb, text=text, command=cmd,
                bg=T["tbar"], fg=T["fg"],
                activebackground=T["sel"], activeforeground=T["fg"],
                relief=tk.FLAT, font=FONT_UI, padx=10, pady=5, bd=0,
            )
            b.pack(side=tk.LEFT, padx=1, pady=2)
            return b

        tbtn("New",              self._new)
        tbtn("Open",             self._open_dialog)
        tbtn("Save",             self._save)
        tk.Frame(tb, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        tbtn("▶  Compile",        self._compile)
        tbtn("▶▶ Compile + View", self._compile_view)

        self._compile_lbl = tk.Label(tb, text="", bg=T["tbar"], fg=T["ok"],
                                      font=FONT_UI)
        self._compile_lbl.pack(side=tk.LEFT, padx=10)

    # ── editor ────────────────────────────────────────────────────────────────

    def _build_editor(self, parent):
        wrap = tk.Frame(parent, bg=T["bg"])
        wrap.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(wrap, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(parent, orient=tk.HORIZONTAL)

        self.editor = tk.Text(
            wrap,
            bg=T["bg"], fg=T["fg"],
            insertbackground=T["fg"],
            selectbackground=T["sel"],
            font=FONT,
            wrap=tk.NONE,
            undo=True, maxundo=-1,
            bd=0, highlightthickness=0,
            padx=8, pady=6,
            spacing1=1, spacing3=1,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        vsb.config(command=self._yview_proxy)
        hsb.config(command=self.editor.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.lnum = LineNumbers(wrap, self.editor)
        self.lnum.pack(side=tk.LEFT, fill=tk.Y)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Syntax tags (lower priority → higher priority: last configured wins on conflict)
        self.editor.tag_configure("num", foreground=T["num"])
        self.editor.tag_configure("brc", foreground=T["brc"])
        self.editor.tag_configure("mth", foreground=T["mth"])
        self.editor.tag_configure("cmd", foreground=T["cmd"])
        self.editor.tag_configure("cmt", foreground=T["cmt"])
        self.editor.tag_configure("match",     background="#2d4f1e", foreground=T["fg"])
        self.editor.tag_configure("match_cur", background=T["sel"],  foreground="#ffffff")
        # tag priority: cmt > cmd > mth > brc > num
        self.editor.tag_raise("cmt")

    def _yview_proxy(self, *args):
        self.editor.yview(*args)
        self.lnum._redraw()

    # ── status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=T["stat"], height=22)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        sb.pack_propagate(False)

        self._lbl_file = tk.Label(sb, text="untitled.tex",
                                   bg=T["stat"], fg=T["stat_fg"],
                                   font=FONT_UI, padx=10)
        self._lbl_file.pack(side=tk.LEFT)

        self._lbl_dirty = tk.Label(sb, text="",
                                    bg=T["stat"], fg=T["stat_fg"],
                                    font=FONT_UI, padx=4)
        self._lbl_dirty.pack(side=tk.LEFT)

        self._lbl_pos = tk.Label(sb, text="Ln 1, Col 1",
                                  bg=T["stat"], fg=T["stat_fg"],
                                  font=FONT_UI, padx=10)
        self._lbl_pos.pack(side=tk.RIGHT)

    # ── output pane ───────────────────────────────────────────────────────────

    def _build_output(self):
        self._out_frame = tk.Frame(self.root, bg=T["out_bg"])
        self._out_frame.pack(fill=tk.X, side=tk.BOTTOM)

        hdr = tk.Frame(self._out_frame, bg=T["tbar"], height=20)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Compile Output", bg=T["tbar"], fg=T["ln_fg"],
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=8)
        tk.Button(hdr, text="×", command=self._toggle_output,
                  bg=T["tbar"], fg=T["ln_fg"], relief=tk.FLAT,
                  font=("Segoe UI", 8), padx=3, pady=0).pack(side=tk.RIGHT, padx=3)

        self._out_text = tk.Text(
            self._out_frame,
            bg=T["out_bg"], fg="#9cdcfe",
            font=("Consolas", 9), height=7,
            state=tk.DISABLED, bd=0,
            highlightthickness=0,
            padx=8, pady=4,
        )
        self._out_text.tag_configure("ok",  foreground=T["ok"])
        self._out_text.tag_configure("err", foreground=T["err"])
        self._out_text.pack(fill=tk.X)
        self._out_visible = True

    def _toggle_output(self, *_):
        if self._out_visible:
            self._out_frame.pack_forget()
        else:
            # re-insert above the status bar
            self._out_frame.pack(fill=tk.X, side=tk.BOTTOM,
                                  before=self._paned)
        self._out_visible = not self._out_visible

    def _toggle_pdf(self, *_):
        panes = list(self._paned.panes())
        pdf_id = str(self.pdf)
        if pdf_id in panes:
            self._paned.forget(self.pdf)
            self._pdf_visible = False
        else:
            self._paned.add(self.pdf, weight=2)
            self._pdf_visible = True

    # ── keybindings ───────────────────────────────────────────────────────────

    def _bind(self):
        r, e = self.root, self.editor

        r.bind("<Control-n>", lambda _: self._new())
        r.bind("<Control-o>", lambda _: self._open_dialog())
        r.bind("<Control-s>", lambda _: self._save())
        r.bind("<Control-S>", lambda _: self._save_as())
        r.bind("<Control-q>", lambda _: self._quit())
        r.bind("<Control-f>", lambda _: self._find_dialog())
        r.bind("<F5>",        lambda _: self._compile())
        r.bind("<F6>",        lambda _: self._compile_view())
        r.bind("<F7>",        lambda _: self._toggle_pdf())
        r.bind("<F8>",        lambda _: self._toggle_output())

        # Text change tracking
        e.bind("<<Modified>>",    self._on_modified)
        e.bind("<ButtonRelease>", self._update_pos)

        # Autocomplete navigation (add=True so default motion still works)
        e.bind("<Tab>",    self._on_tab,    add=True)
        e.bind("<Escape>", self._on_escape, add=True)
        e.bind("<Down>",   self._on_down,   add=True)
        e.bind("<Up>",     self._on_up,     add=True)
        e.bind("<Return>", self._on_return)   # override to add auto-indent

        # Trigger autocomplete while typing
        e.bind("<KeyRelease>", self._on_keyrelease, add=True)

        # Auto-pairs
        e.bind("{", lambda _: self._pair("{", "}"))
        e.bind("(", lambda _: self._pair("(", ")"))
        e.bind("[", lambda _: self._pair("[", "]"))
        e.bind("$", lambda _: self._pair("$", "$"))

    # ── event handlers ────────────────────────────────────────────────────────

    def _on_modified(self, _=None):
        if self.editor.edit_modified():
            if not self.dirty:
                self.dirty = True
                self._update_title()
            self._schedule_highlight()
            self.editor.edit_modified(False)

    def _on_keyrelease(self, event):
        self._update_pos()
        if event.keysym in ("BackSlash", "BackSpace") or (
            event.char and event.char.isalpha()
        ):
            self._ac.update()

    def _on_tab(self, _):
        if self._ac.visible():
            self._ac.apply()
            return "break"

    def _on_escape(self, _):
        if self._ac.visible():
            self._ac.hide()
            return "break"

    def _on_down(self, _):
        if self._ac.visible():
            self._ac.move(1)
            return "break"

    def _on_up(self, _):
        if self._ac.visible():
            self._ac.move(-1)
            return "break"

    def _on_return(self, _):
        if self._ac.visible():
            self._ac.apply()
            return "break"
        self._auto_indent()
        return "break"

    # ── auto-pair / auto-indent ───────────────────────────────────────────────

    def _pair(self, open_c: str, close_c: str):
        self.editor.insert(tk.INSERT, open_c + close_c)
        self.editor.mark_set(tk.INSERT,
                              f"{self.editor.index(tk.INSERT)}-1c")
        return "break"

    def _auto_indent(self):
        line    = self.editor.get("insert linestart", "insert lineend")
        indent  = len(line) - len(line.lstrip())
        stripped = line.rstrip()
        extra = 4 if (stripped.endswith("{") or
                       re.search(r"\\begin\{[^}]*\}\s*$", stripped)) else 0
        self.editor.insert(tk.INSERT, "\n" + " " * (indent + extra))
        self.editor.see(tk.INSERT)

    # ── file ops ──────────────────────────────────────────────────────────────

    def _new(self):
        if self.dirty and not self._confirm_discard():
            return
        self.editor.delete("1.0", tk.END)
        self.filepath = None
        self.dirty    = False
        self._new_template()

    def _new_template(self):
        tmpl = (
            r"\documentclass{article}" "\n"
            r"\usepackage[utf8]{inputenc}" "\n"
            r"\usepackage{amsmath}" "\n"
            r"\usepackage{amssymb}" "\n"
            "\n"
            r"\title{Untitled}" "\n"
            r"\author{}" "\n"
            r"\date{\today}" "\n"
            "\n"
            r"\begin{document}" "\n"
            r"\maketitle" "\n"
            "\n"
            r"\end{document}" "\n"
        )
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", tmpl)
        self.editor.edit_reset()
        self.dirty = False
        self._update_title()
        self._highlight()

    def _open_dialog(self):
        path = filedialog.askopenfilename(
            filetypes=[("LaTeX files", "*.tex"), ("All files", "*.*")]
        )
        if path:
            self._open_file(path)

    def _open_file(self, path: str):
        if self.dirty and not self._confirm_discard():
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except Exception as ex:
            messagebox.showerror("Open error", str(ex))
            return
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", text)
        self.editor.edit_reset()
        self.filepath = path
        self.dirty    = False
        self._update_title()
        self._highlight()
        # Load existing PDF if present
        pdf = str(Path(path).with_suffix(".pdf"))
        if os.path.exists(pdf) and HAS_FITZ and HAS_PIL:
            self.pdf.load(pdf)

    def _save(self):
        if self.filepath is None:
            return self._save_as()
        self._do_save(self.filepath)

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".tex",
            filetypes=[("LaTeX files", "*.tex"), ("All files", "*.*")],
        )
        if path:
            self.filepath = path
            self._do_save(path)

    def _do_save(self, path: str):
        content = self.editor.get("1.0", "end-1c")
        try:
            Path(path).write_text(content, encoding="utf-8")
        except Exception as ex:
            messagebox.showerror("Save error", str(ex))
            return
        self.dirty = False
        self._update_title()

    def _confirm_discard(self) -> bool:
        return messagebox.askyesno("Unsaved changes",
                                    "Discard unsaved changes?")

    def _quit(self):
        if self.dirty and not self._confirm_discard():
            return
        self.root.destroy()

    # ── compile ───────────────────────────────────────────────────────────────

    def _compile(self, open_pdf=False):
        if self.filepath is None:
            messagebox.showinfo("Save first", "Save the file before compiling.")
            if not self._save_as_and_return():
                return
        self._save()
        self._set_out("Compiling…\n")
        self._compile_lbl.config(text="Compiling…", fg="#ffd700")
        t = threading.Thread(target=self._run_compile,
                              args=(self.filepath, open_pdf), daemon=True)
        t.start()

    def _compile_view(self):
        self._compile(open_pdf=True)

    def _save_as_and_return(self) -> bool:
        path = filedialog.asksaveasfilename(
            defaultextension=".tex",
            filetypes=[("LaTeX files", "*.tex"), ("All files", "*.*")],
        )
        if not path:
            return False
        self.filepath = path
        self._do_save(path)
        return True

    def _run_compile(self, path: str, open_pdf: bool):
        compiler = next(
            (c for c in ("pdflatex", "latexmk", "tectonic") if shutil.which(c)),
            None,
        )
        if compiler is None:
            self._append_out("No LaTeX compiler found.\n"
                              "Install pdflatex, latexmk, or tectonic.\n", "err")
            self.root.after(0, lambda: self._compile_lbl.config(
                text="No compiler", fg=T["err"]))
            return

        # ── \plot preprocessing ───────────────────────────────────────────────
        content   = Path(path).read_text(encoding="utf-8")
        proc_tex  = None          # path to the _processed.tex, if created
        final_pdf = str(Path(path).with_suffix(".pdf"))

        if r"\plot" in content and HAS_MPL:
            try:
                proc = PlotProcessor(path)
                processed = proc.process(content)
                if r"\usepackage{graphicx}" not in processed:
                    processed = processed.replace(
                        r"\begin{document}",
                        r"\usepackage{graphicx}" + "\n" + r"\begin{document}",
                        1,
                    )
                stem     = Path(path).stem
                proc_tex = str(Path(path).parent / f"{stem}_processed.tex")
                Path(proc_tex).write_text(processed, encoding="utf-8")
                self._append_out(
                    f"Preprocessed {proc.counter} plot(s) → {stem}_processed.tex\n",
                    "ok",
                )
                compile_path = proc_tex
            except Exception as ex:
                self._append_out(f"Plot preprocessing error: {ex}\n", "err")
                compile_path = path
        elif r"\plot" in content and not HAS_MPL:
            self._append_out(
                "Warning: \\plot found but matplotlib/numpy unavailable — "
                "skipping plot generation.\n", "err"
            )
            compile_path = path
        else:
            compile_path = path
        # ─────────────────────────────────────────────────────────────────────

        cwd = str(Path(path).parent)
        cmd = {
            "latexmk":  ["latexmk", "-pdf", "-interaction=nonstopmode", compile_path],
            "tectonic": ["tectonic", compile_path],
        }.get(compiler, ["pdflatex", "-interaction=nonstopmode", compile_path])

        try:
            res = subprocess.run(cmd, cwd=cwd, capture_output=True,
                                  text=True, timeout=120)
        except subprocess.TimeoutExpired:
            self._append_out("Compilation timed out.\n", "err")
            return
        except Exception as ex:
            self._append_out(f"Error: {ex}\n", "err")
            return

        out = res.stdout + res.stderr
        self._append_out(out)

        # If we compiled a _processed file, copy the PDF back to the original name
        # and clean up auxiliary _processed.* files.
        if proc_tex:
            proc_pdf = str(Path(proc_tex).with_suffix(".pdf"))
            if os.path.exists(proc_pdf):
                shutil.copy2(proc_pdf, final_pdf)
            for ext in (".tex", ".pdf", ".aux", ".log", ".out", ".fls", ".fdb_latexmk"):
                tmp = str(Path(proc_tex).with_suffix(ext))
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except OSError:
                    pass

        pdf_path = final_pdf
        ok = res.returncode == 0 or os.path.exists(pdf_path)
        if ok:
            self._append_out("\n✓ Compiled successfully.\n", "ok")
            self.root.after(0, lambda: self._compile_lbl.config(
                text="✓ Compiled", fg=T["ok"]))
            self.root.after(0, lambda: self.pdf.load(pdf_path))
            if open_pdf:
                self.root.after(0, lambda: self._open_pdf_external(pdf_path))
        else:
            errs = [l for l in out.splitlines() if l.startswith("!")]
            msg  = errs[0] if errs else "Compilation failed."
            self._append_out(f"\n✗ {msg}\n", "err")
            self.root.after(0, lambda: self._compile_lbl.config(
                text="✗ Error", fg=T["err"]))

    def _open_pdf_external(self, path: str):
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    # ── syntax highlighting ───────────────────────────────────────────────────

    def _schedule_highlight(self):
        if self._hl_job:
            self.root.after_cancel(self._hl_job)
        self._hl_job = self.root.after(250, self._highlight)

    def _highlight(self):
        self._hl_job = None
        text = self.editor.get("1.0", "end-1c")
        for tag in ("cmd", "cmt", "brc", "num", "mth"):
            self.editor.tag_remove(tag, "1.0", tk.END)

        def apply(pattern: str, tag: str, flags: int = 0):
            for m in re.finditer(pattern, text, flags):
                s, e = m.start(), m.end()
                self.editor.tag_add(tag, f"1.0+{s}c", f"1.0+{e}c")

        apply(r"\b\d+\.?\d*\b",   "num")
        apply(r"[{}\[\]]",        "brc")
        apply(r"\$\$[\s\S]*?\$\$|\$[^$\n]*\$", "mth")
        apply(r"\\[a-zA-Z@]+\*?", "cmd")
        apply(r"%[^\n]*",         "cmt")   # applied last; tag_raise ensures priority
        self.editor.tag_raise("cmt")

    # ── LaTeX helpers ─────────────────────────────────────────────────────────

    def _insert_begin(self):
        self.editor.insert(tk.INSERT, "\\begin{}\n\n\\end{}")
        # leave cursor inside first {}
        pos = self.editor.search("{}", "insert-25c", "insert+1c")
        if pos:
            self.editor.mark_set(tk.INSERT, f"{pos}+1c")

    def _insert_equation(self):
        self.editor.insert(
            tk.INSERT,
            "\\begin{equation}\n    \n\\end{equation}",
        )

    def _insert_frac(self):
        self.editor.insert(tk.INSERT, "\\frac{}{}")

    def _insert_plot(self, ptype: str):
        snippets = {
            "2d":          r"\plot[xmin=-5, xmax=5]{sin(x)}",
            "parametric":  r"\plot[type=parametric, tmin=0, tmax=6.283]{cos(t), sin(t)}",
            "3d":          r"\plot[type=3d, xmin=-3, xmax=3, ymin=-3, ymax=3]{sin(x)*cos(y)}",
            "complex":     r"\plot[type=complex, xmin=-2, xmax=2, ymin=-2, ymax=2]{z**2 - 1}",
            "vector":      r"\plot[type=vector, xmin=-3, xmax=3, ymin=-3, ymax=3]{-y, x}",
        }
        self.editor.insert(tk.INSERT, snippets.get(ptype, r"\plot{}"))

    # ── find dialog ───────────────────────────────────────────────────────────

    def _find_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Find")
        dlg.geometry("340x38")
        dlg.configure(bg=T["tbar"])
        dlg.resizable(False, False)
        dlg.transient(self.root)

        tk.Label(dlg, text="Find:", bg=T["tbar"], fg=T["fg"],
                 font=FONT_UI).pack(side=tk.LEFT, padx=8)
        ent = tk.Entry(dlg, bg=T["bg"], fg=T["fg"],
                       insertbackground=T["fg"],
                       font=FONT_SM, relief=tk.FLAT, bd=2)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)

        self._find_idx = 0
        self._find_ranges: list = []

        def do_find(*_):
            pat = ent.get()
            self.editor.tag_remove("match",     "1.0", tk.END)
            self.editor.tag_remove("match_cur", "1.0", tk.END)
            self._find_ranges = []
            if not pat:
                return
            start = "1.0"
            while True:
                pos = self.editor.search(pat, start, tk.END, regexp=True)
                if not pos:
                    break
                end = f"{pos}+{len(pat)}c"
                self.editor.tag_add("match", pos, end)
                self._find_ranges.append((pos, end))
                start = end
            if self._find_ranges:
                self._find_idx = 0
                p, e2 = self._find_ranges[0]
                self.editor.tag_add("match_cur", p, e2)
                self.editor.mark_set(tk.INSERT, p)
                self.editor.see(p)

        def do_next(*_):
            if not self._find_ranges:
                do_find()
                return
            self.editor.tag_remove("match_cur", "1.0", tk.END)
            self._find_idx = (self._find_idx + 1) % len(self._find_ranges)
            p, e2 = self._find_ranges[self._find_idx]
            self.editor.tag_add("match_cur", p, e2)
            self.editor.mark_set(tk.INSERT, p)
            self.editor.see(p)

        tk.Button(dlg, text="Find", command=do_find,
                  bg=T["tbar"], fg=T["fg"], relief=tk.FLAT,
                  font=FONT_UI, padx=8).pack(side=tk.LEFT, padx=2)
        tk.Button(dlg, text="Next", command=do_next,
                  bg=T["tbar"], fg=T["fg"], relief=tk.FLAT,
                  font=FONT_UI, padx=8).pack(side=tk.LEFT, padx=2)
        ent.bind("<Return>", do_find)
        ent.focus_set()

    # ── output helpers ────────────────────────────────────────────────────────

    def _set_out(self, text: str, tag: str = ""):
        def _do():
            self._out_text.config(state=tk.NORMAL)
            self._out_text.delete("1.0", tk.END)
            self._out_text.insert(tk.END, text, tag)
            self._out_text.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _append_out(self, text: str, tag: str = ""):
        def _do():
            self._out_text.config(state=tk.NORMAL)
            self._out_text.insert(tk.END, text, tag)
            self._out_text.config(state=tk.DISABLED)
            self._out_text.see(tk.END)
        self.root.after(0, _do)

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _update_title(self):
        name   = Path(self.filepath).name if self.filepath else "untitled.tex"
        marker = " ●" if self.dirty else ""
        self.root.title(f"zrktex — {name}{marker}")
        self._lbl_file.config(text=name)
        self._lbl_dirty.config(text="●" if self.dirty else "")

    def _update_pos(self, *_):
        row, col = self.editor.index(tk.INSERT).split(".")
        self._lbl_pos.config(text=f"Ln {row}, Col {int(col)+1}")

    # ── run ───────────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


def main():
    App().run()


if __name__ == "__main__":
    main()
