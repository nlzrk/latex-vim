# latex-vim

A vim-like TUI text editor built specifically for LaTeX. Write your documents in a modal editor with syntax highlighting and command autocomplete, then compile straight to PDF without leaving the terminal.

---

## Features

- **Modal editing** — Normal, Insert, Command, and Visual modes, just like Vim
- **Vim keybindings** — movement, operators, text objects, registers, counts, and more
- **LaTeX syntax highlighting** — commands, comments, math, and braces are all color-coded
- **Command autocomplete** — type `\` and get a filtered popup of 200+ LaTeX commands navigable with Tab
- **Auto-pairs** — `{`, `[`, `(`, and `$` automatically insert their closing counterpart
- **Auto-indent** — Enter preserves indentation and adds a level after `\begin{...}` or `{`
- **PDF compilation** — `:wq` saves, compiles with `pdflatex`, opens the PDF, and exits
- **Live search** — `/pattern` updates match highlights as you type
- **Undo / Redo** — full history with up to 300 snapshots
- **Boilerplate template** — new `.tex` files open with a ready-to-use preamble
- **Zero config** — single Python file, two pip packages

---

## Requirements

**Python** 3.8 or newer.

**Python packages:**

```
windows-curses   (Windows only)
pygments
```

**A LaTeX compiler** — one of:

| Compiler | How to get it |
|----------|---------------|
| `pdflatex` | [MiKTeX](https://miktex.org/) (Windows) · [TeX Live](https://tug.org/texlive/) (all platforms) |
| `latexmk` | Included with TeX Live · available via MiKTeX package manager |
| `tectonic` | [tectonic-typesetting.io](https://tectonic-typesetting.io) |

The editor tries `pdflatex` first, then `latexmk`, then `tectonic`. Any one of them is enough.

---

## Installation

**1. Clone the repo**

```bash
git clone https://github.com/nlzrk/latex-vim
cd latex-vim
```

**2. Install Python dependencies**

```bash
pip install -r requirements.txt
```

That's it. No build step, no config file.

---

## Usage

```bash
# Open an existing file
python editor.py paper.tex

# Create a new file (opens with boilerplate preamble)
python editor.py new_document.tex
```

When you open a file that doesn't exist yet, the editor pre-fills it with a minimal LaTeX preamble and positions the cursor inside `\begin{document}` ready to write:

```latex
\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{hyperref}
\geometry{margin=1in}

\begin{document}
← cursor starts here

\end{document}
```

---

## Key Bindings

### Normal Mode

#### Movement

| Key | Action |
|-----|--------|
| `h` `j` `k` `l` | Left · Down · Up · Right |
| `w` | Forward one word |
| `b` | Backward one word |
| `e` | Forward to end of word |
| `0` | Beginning of line |
| `$` | End of line |
| `^` | First non-blank character of line |
| `gg` | First line of file |
| `G` | Last line of file |
| `Ctrl+D` | Half-page down |
| `Ctrl+U` | Half-page up |
| `PgDn` | Page down |
| `PgUp` | Page up |
| `{count}{motion}` | Repeat motion *count* times (e.g. `5j`, `3w`) |

#### Entering Insert Mode

| Key | Action |
|-----|--------|
| `i` | Insert before cursor |
| `I` | Insert at first non-blank character of line |
| `a` | Append after cursor |
| `A` | Append at end of line |
| `o` | Open new line below and insert |
| `O` | Open new line above and insert |

#### Editing (Normal Mode)

| Key | Action |
|-----|--------|
| `x` | Delete character under cursor |
| `D` | Delete from cursor to end of line |
| `dd` | Delete current line |
| `{n}dd` | Delete *n* lines |
| `J` | Join current line with the next (adds a space) |
| `yy` or `Y` | Yank (copy) current line |
| `{n}yy` | Yank *n* lines |
| `p` | Paste yanked content below / after cursor |
| `P` | Paste yanked content above / before cursor |
| `u` | Undo |
| `Ctrl+R` | Redo |

#### Search

| Key | Action |
|-----|--------|
| `/pattern` | Search forward (highlights update live as you type) |
| `n` | Jump to next match |
| `N` | Jump to previous match |

Patterns are regular expressions. Use `\/` to search for a literal `/`.

#### Other

| Key | Action |
|-----|--------|
| `v` | Enter Visual mode |
| `:` | Enter Command mode |

---

### Insert Mode

| Key | Action |
|-----|--------|
| `ESC` | Return to Normal mode |
| `Tab` | Trigger autocomplete (if `\` prefix exists) or insert 4 spaces |
| `Backspace` | Delete character to the left; join lines when at column 0 |
| `Delete` | Delete character under cursor |
| `Enter` | New line with auto-indent |
| Arrow keys | Move cursor without leaving Insert mode |
| `{` `[` `(` `$` | Insert character and its closing pair |

#### Autocomplete

Autocomplete activates automatically while you type a `\command`. The popup shows up to 10 matching commands.

| Key | Action |
|-----|--------|
| `Tab` or `↓` | Select next suggestion |
| `↑` | Select previous suggestion |
| `Enter` | Accept selected suggestion |
| `ESC` | Dismiss popup |

If no `\` prefix is present, `Tab` inserts four spaces instead.

---

### Visual Mode

Visual mode selects whole lines between the anchor point and the cursor.

| Key | Action |
|-----|--------|
| `h` `j` `k` `l` | Extend selection |
| `w` `b` | Extend selection by word |
| `0` `$` `G` | Extend selection to line start / end / file end |
| `d` or `x` | Delete selected lines (cut into register) |
| `y` | Yank selected lines |
| `v` or `ESC` | Cancel and return to Normal mode |

---

### Command Mode

Enter Command mode by pressing `:` in Normal mode.

| Command | Action |
|---------|--------|
| `:w` | Save the current file |
| `:w <filename>` | Save to a different file |
| `:q` | Quit (refused if there are unsaved changes) |
| `:q!` | Force quit, discarding unsaved changes |
| `:wq` or `:x` | Save → compile → open PDF → quit |
| `:pdf` | Save and compile to PDF (stay in editor) |
| `:e <filename>` | Open a different file |

---

## PDF Compilation

`:wq` (and `:pdf`) run the following pipeline:

1. Save the file
2. Detect the available compiler (`pdflatex` → `latexmk` → `tectonic`)
3. Run with `-interaction=nonstopmode` so compilation doesn't wait for input
4. If successful, open the PDF with the system default viewer and exit
5. If compilation fails, stay in the editor and show the first `!`-prefixed error line from the log on the status bar

The `.log` file produced by the compiler is left on disk so you can inspect the full error output if needed.

---

## Syntax Highlighting

Colors are applied using [Pygments](https://pygments.org/) `TexLexer`. The color scheme:

| Element | Color |
|---------|-------|
| `\commands` | Cyan |
| `% comments` | Green |
| `{braces}` / strings | Yellow |
| Numbers | Magenta |
| Operators / punctuation | Red |
| Search matches | Black on Yellow |
| Visual selection | Reversed |
| Line numbers | Yellow (dimmed) |

---

## Status Bar

The bottom two rows of the terminal are reserved:

```
 INSERT  paper.tex*                                          12:34
 E212: No file name — use :w <name>
```

- **Row 1** — current mode · filename (`*` if unsaved) · line:column
- **Row 2** — command input (when in Command mode) or the most recent status/error message

---

## Building a Standalone Executable

### Nuitka (compiles to C, then to a native binary)

```bash
pip install nuitka
python -m nuitka --onefile --include-package=pygments editor.py
```

Produces `editor.exe` on Windows or `editor` on Linux/macOS. No Python installation required to run it.

> Requires a C compiler. On Windows, install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) or MinGW.

### PyInstaller (bundles Python runtime)

```bash
pip install pyinstaller
pyinstaller --onefile editor.py
# output → dist/editor.exe
```

Simpler than Nuitka but the resulting binary is larger since it packages the Python interpreter alongside the script.

---

## Platform Notes

| Platform | Notes |
|----------|-------|
| Windows | Requires `windows-curses` (`pip install windows-curses`). PDF opens with `os.startfile`. |
| macOS | `curses` is in stdlib. PDF opens with `open`. |
| Linux | `curses` is in stdlib. PDF opens with `xdg-open`. |

---

## License

MIT
