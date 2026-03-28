# zrktex

A LaTeX editor that runs in two modes from the same file: a **GUI** with a live PDF preview panel, and a **TUI** that works like Vim. Write your documents, embed `\plot` commands for inline graphs, and compile straight to PDF — no config required.

---

## Modes

| | GUI | TUI |
|---|---|---|
| Launch | `python zrktex.py file.tex` | `python zrktex.py --tui file.tex` |
| Interface | tkinter window, split editor + PDF panel | Terminal (curses), vim-like modal editing |
| PDF preview | Live, rendered in the side panel | Opens with system viewer on `:wq` |
| Best for | General use, exploring plots | SSH sessions, minimal environments |

---

## Features

- **`\plot` command** — embed any graph directly in your document: real functions, parametric curves, 3-D surfaces, complex domain colouring, vector fields. Plots are generated with matplotlib at compile time and included as PDF figures.
- **GUI editor** — syntax-highlighted editor with line numbers, autocomplete popup, auto-pairs, auto-indent, split PDF preview, find dialog, and compile output panel
- **TUI editor** — full vim keybindings (Normal / Insert / Command / Visual modes), live search, 300-level undo, autocomplete popup
- **LaTeX autocomplete** — type `\` and get a filtered list of 200+ commands; navigate with Tab / arrows
- **Auto-pairs** — `{`, `[`, `(`, `$` close themselves and position the cursor inside
- **Smart indent** — Enter preserves indentation and adds a level after `\begin{...}` or `{`
- **Compiler detection** — tries `pdflatex` → `latexmk` → `tectonic`, uses whatever is installed
- **Boilerplate template** — new files open with a ready-to-use preamble

---

## Requirements

**Python 3.8+**

```
pip install -r requirements.txt
```

```
pygments
matplotlib
numpy
Pillow
PyMuPDF
windows-curses   # Windows only, for TUI
```

**tkinter** (GUI mode) — usually bundled with Python. On Linux you may need:

```bash
sudo apt-get install python3-tk      # Debian / Ubuntu
sudo dnf install python3-tkinter     # Fedora
sudo pacman -S tk                    # Arch
```

**A LaTeX compiler** — any one of:

| Compiler | How to get it |
|----------|---------------|
| `pdflatex` | [MiKTeX](https://miktex.org/) (Windows) · [TeX Live](https://tug.org/texlive/) (all) |
| `latexmk` | Included with TeX Live |
| `tectonic` | [tectonic-typesetting.io](https://tectonic-typesetting.io) |

---

## Installation

### Windows / macOS

```bash
git clone https://github.com/nlzrk/zrktex
cd zrktex
pip install -r requirements.txt
python zrktex.py
```

### Linux — user install (no sudo)

```bash
git clone https://github.com/nlzrk/zrktex
cd zrktex
bash install.sh
```

This installs `zrktex.py` to `~/.local/share/zrktex/`, drops a launcher at `~/.local/bin/zrktex`, and installs all Python dependencies. It also offers to add `~/.local/bin` to your PATH automatically.

### Linux — system-wide install

```bash
sudo bash install.sh
```

Installs to `/usr/local/`. After this, `zrktex` works for all users.

### Manual Linux launcher

If you just want to drop two files into `/usr/local/bin/`:

```bash
sudo cp zrktex.py zrktex /usr/local/bin/
sudo chmod +x /usr/local/bin/zrktex
```

---

## Usage

```bash
zrktex file.tex           # GUI
zrktex --tui file.tex     # TUI
zrktex --tui              # TUI with no file (use :w <name> to save)

# Without install.sh:
python zrktex.py file.tex
python zrktex.py --tui file.tex
```

---

## `\plot` command

Write `\plot` anywhere in your document. When you compile, each command is replaced with a properly-sized `\includegraphics` pointing to a matplotlib-generated PDF figure in `_zrkplots/`.

```latex
% 2-D functions (comma-separate for multiple curves)
\plot[xmin=-5, xmax=5, legend=sin;cos]{sin(x), cos(x)}

% Parametric curve
\plot[type=parametric, tmin=0, tmax=6.283]{cos(t), sin(t)}

% 3-D surface
\plot[type=3d, xmin=-3, xmax=3, ymin=-3, ymax=3]{sin(x)*cos(y)}

% Complex domain colouring (hue = argument, brightness = modulus)
\plot[type=complex, xmin=-2, xmax=2, ymin=-2, ymax=2]{z**2 - 1}

% Vector field — quiver or streamlines
\plot[type=vector, style=stream, xmin=-3, xmax=3, ymin=-3, ymax=3]{-y, x}

% 3-D parametric curve
\plot[type=curve3d, tmin=0, tmax=12.566]{cos(t), sin(t), t/4}
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `type` | `2d` | `2d` · `parametric` · `3d` · `complex` · `vector` · `curve3d` |
| `xmin` / `xmax` | `-5` / `5` | x-axis bounds (supports `pi`, `e`) |
| `ymin` / `ymax` | auto | y-axis bounds |
| `zmin` / `zmax` | auto | z-axis bounds (3-D only) |
| `tmin` / `tmax` | `0` / `2π` | parameter range for parametric types |
| `title` | — | plot title |
| `xlabel` / `ylabel` / `zlabel` | — | axis labels |
| `legend` | — | semicolon-separated labels: `sin;cos` |
| `figwidth` / `figheight` | `5.5` / `4.0` | figure size in inches |
| `width` | `0.8\linewidth` | width passed to `\includegraphics` |
| `resolution` | `80` / `500` | grid density for surfaces / complex plots |
| `density` | `20` | arrow grid density for quiver |
| `style` | `quiver` | `quiver` or `stream` (vector fields only) |

### Available math functions

```
sin cos tan sec csc cot  sinh cosh tanh
arcsin arccos arctan arctan2
exp log log2 log10 ln sqrt abs sign floor ceil
pi e inf  real imag re im conj angle arg
np  (full numpy access, e.g. np.sinc(x))
```

For complex plots, `z` is the complex grid and `i` is the imaginary unit.

---

## GUI keybindings

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| `Ctrl+F` | Find |
| `F5` | Compile |
| `F6` | Compile and open PDF externally |
| `F7` | Toggle PDF preview panel |
| `F8` | Toggle compile output panel |
| `Ctrl+N` | New file |
| `Ctrl+O` | Open file |
| `Ctrl+Q` | Quit |

---

## TUI keybindings

### Normal mode — movement

| Key | Action |
|-----|--------|
| `h` `j` `k` `l` | Left · Down · Up · Right |
| `w` / `b` / `e` | Word forward / backward / end |
| `0` / `$` / `^` | Line start / end / first non-blank |
| `gg` / `G` | File start / end |
| `Ctrl+D` / `Ctrl+U` | Half-page down / up |
| `{n}{motion}` | Repeat motion n times (`5j`, `3w`, …) |

### Normal mode — editing

| Key | Action |
|-----|--------|
| `i` / `I` | Insert before cursor / line start |
| `a` / `A` | Append after cursor / line end |
| `o` / `O` | New line below / above |
| `x` | Delete character under cursor |
| `D` | Delete to end of line |
| `dd` / `{n}dd` | Delete line(s) |
| `yy` / `Y` | Yank line |
| `p` / `P` | Paste below / above |
| `J` | Join line with next |
| `u` / `Ctrl+R` | Undo / Redo |
| `/pattern` | Search (highlights update live) |
| `n` / `N` | Next / previous match |
| `v` | Visual line mode |
| `:` | Command mode |

### Insert mode

| Key | Action |
|-----|--------|
| `Esc` | Back to Normal mode |
| `Tab` | Autocomplete (if `\` prefix) or insert 4 spaces |
| `Enter` | New line with auto-indent |
| `{` `[` `(` `$` | Insert with closing pair |

### Command mode

| Command | Action |
|---------|--------|
| `:w` | Save |
| `:w <file>` | Save to different file |
| `:q` | Quit (blocked if unsaved) |
| `:q!` | Force quit |
| `:wq` / `:x` | Save → compile → open PDF → quit |
| `:pdf` | Save and compile (stay in editor) |
| `:e <file>` | Open file |

---

## Syntax highlighting

| Element | GUI color | TUI color |
|---------|-----------|-----------|
| `\commands` | Teal | Cyan |
| `% comments` | Green | Green |
| `{braces}` | Gold | Yellow |
| `$math$` | Peach | — |
| Numbers | Sage | Magenta |
| Search matches | Green background | Yellow background |

---

## Platform notes

| Platform | Notes |
|----------|-------|
| Windows | `windows-curses` required for TUI. GUI works out of the box. |
| macOS | `curses` is in stdlib. GUI requires tkinter (bundled with python.org installer). |
| Linux | Install `python3-tk` for GUI. `curses` is in stdlib. Use `install.sh` to set up a system command. |

---

## Building a standalone executable

```bash
# PyInstaller — bundles Python runtime
pip install pyinstaller
pyinstaller --onefile zrktex.py

# Nuitka — compiles to native binary (smaller, faster startup)
pip install nuitka
python -m nuitka --onefile zrktex.py
```

---

## License

MIT
