---
name: reading-math-sources
description: Use when reading, quoting, summarising, taking notes from, or extracting equations, theorems, definitions or algorithms from a mathematics, statistics, physics, machine-learning or other technical paper, book, thesis or lecture notes held as a PDF or EPUB, from any publisher or arXiv — especially when formulas must be exact LaTeX, a page must be cited, a whole section is needed, or the PDF looks scanned, garbled or damaged.
---

# Reading Math Sources

## Overview

The PDF is usually the worst copy of a formula you have. **Before transcribing maths from page images, find out whether the author's TeX (arXiv) or the publisher's LaTeX (the EPUB beside the PDF) exists, and quote from that.** Page images are the fallback. The PDF text layer only locates.

**REQUIRED BACKGROUND:** source-access-honesty, for how to label what was and was not read.

Without this skill, agents handed a PDF never looked for another source: in five of twelve test tasks exact LaTeX was one command away. Their transcriptions by eye were mathematically right but guessed the macros, e.g. `\mathscr` where the publisher's source says `\mathcal`.

## Step 1: probe (always first)

```bash
S=~/.claude/skills/reading-math-sources/scripts
uv run $S/probe.py "FILE.pdf"      # uv not found? export PATH="/opt/homebrew/bin:$PATH"
```

It prints page count, how printed page numbers map to PDF pages, text-layer quality, outline, and a `ROUTE` list, best source first. Follow the first route that covers what you need.

## Step 2: read from the route

| Probe says | Read the maths from | Commands |
|---|---|---|
| `arXiv:<id>` stamped | Author's TeX | `uv run $S/arxiv_src.py <id-with-version>`, `grep -n` the `.tex`, `Read` the lines. Expand author macros before quoting. |
| Twin EPUB `MACHINE-READABLE` | Publisher's LaTeX or MathML | `uv run $S/epub2md.py BOOK.epub --find "REGEX"` names the chapter; `--doc N` writes a `.md`; `grep -n` it, `Read` the lines. |
| `⟦IMAGE: path⟧` in that `.md` | That image | `Read` the image file. Usual for display equations in older Springer books. Take macro names from the LaTeX around it (`grep` the `.md`) and say the equation itself was transcribed. |
| Twin EPUB `IMAGES ONLY`, no twin, OCR or scanned | Page image | `uv run $S/probe.py FILE.pdf --find "REGEX"` names the page (too many hits: add `--pages A-B`, or use `--toc`); `Read(file_path, pages="N")`. Small print: `uv run $S/probe.py FILE.pdf --zoom N --part top` (or `middle`, `bottom`), then `Read` the PNG it names. |
| Paper, no stamp | Possibly arXiv | `uv run $S/arxiv_src.py --title "…" --author Surname`. Quote it as the paper only if title **and** authors match. Same authors under another title is an earlier preprint: offer it to the user as a different version. |
| `FILE IS DAMAGED` | Another copy | Tell the user to re-download and which pages are lost. Do not dig through the bytes. |

After quoting from TeX or EPUB, one `Read(file_path, pages="N")` of the PDF page confirms the passage, its equation numbers and the printed page number. A `--find` hit can be the lead-in sentence: if the statement is not on that page, view the next one. No crops are needed for this.

In a converted EPUB chapter the equation number sits on its own line after the `$$` block, and Springer's LaTeX carries wrappers (`\begin{aligned}`, `&{}`, `\displaystyle`) that you may drop if you say so.

## Rules

- **Locate with text, quote from source.** `--find`, `pdftotext` and `grep` output tells you where a formula is, never what it says.
- **Say where each formula came from:** author's TeX (arXiv vN), publisher's LaTeX (EPUB), publisher's MathML converted by pandoc, or transcribed from a page image. In a converted EPUB chapter, simple inline maths is often plain Unicode text (`μ(A) = 0`, `ν ≪ μ`): the symbols are exact, but any LaTeX you write for it is your own, so say so.
- **Macro and font claims** (`\mathcal` vs `\mathscr`) need source markup. From an image, say "looks like".
- **Versions differ.** arXiv TeX matches the PDF only if the PDF carries that stamp. For a journal PDF, name the arXiv version you used and view the PDF page for any formula whose exact form matters.
- **Page citations** give the PDF page and the printed page. The probe's printed numbers are a hint: cite the number you see on the page. An EPUB has no pages, so find the page with `probe.py FILE.pdf --find "<distinctive phrase>"`.
- **Keyword counts and library scans** need none of this: `pdftotext -q FILE - | grep -oi word | wc -l`.

## Common mistakes

| Mistake | Fix |
|---|---|
| Rendering pages when the probe lists a source route | Take route 1; view the page once to confirm. |
| Dumping the whole book with `pdftotext` to find one theorem | `probe.py --find` or `epub2md.py --find`. |
| Fetching `1701.02434` when the PDF says `v2` | Use the stamped version. |
| Citing a printed page computed from a fixed offset | Offsets drift between chapters; read the number off the page. |
