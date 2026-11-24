# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf>=1.24"]
# ///
"""Probe a PDF (or EPUB) and say which source to read its maths from.

  uv run probe.py FILE.pdf                 facts + ROUTE (best source first)
  uv run probe.py FILE.pdf --find REGEX [--pages A-B]
                                           PDF pages whose text layer matches (locating only), one line
                                           per page; case-insensitive, whitespace collapsed, fi/fl
                                           ligatures and line-break hyphens undone, so type plain words
  uv run probe.py FILE.pdf --toc           full outline with PDF page numbers
  uv run probe.py FILE.pdf --zoom N --part top|middle|bottom   300-dpi PNG of part of page N

All page numbers are 1-based PDF page indices (what `Read(pages=...)` and
`pdftotext -f/-l` use); printed page numbers are given beside them when known.
"""
import argparse, collections, os, re, sys, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from epub2md import census, spine  # stdlib-only at import time

HERE = Path(sys.argv[0]).absolute().parent
ARXIV = re.compile(r"arXiv:\s?((?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)")


def ranges(nums):
    out, start, prev = [], None, None
    for n in nums:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append(f"{start}-{prev}" if prev > start else str(start))
            start = prev = n
    if start is not None:
        out.append(f"{start}-{prev}" if prev > start else str(start))
    return ", ".join(out)


def epub_summary(epub):
    z = zipfile.ZipFile(epub)
    tot = [0, 0, 0]
    for p, _ in spine(z):
        tot = [a + b for a, b in zip(tot, census(z.read(p).decode("utf-8", "replace")))]
    tex, mml, img = tot
    kind = "IMAGES ONLY" if tex + mml == 0 else "MACHINE-READABLE"
    what = "publisher's LaTeX" if tex >= mml else "publisher's MathML, converted to LaTeX by pandoc"
    return kind, f"{tex} publisher-TeX, {mml} MathML, {img} image-only", what


# pdfTeX and InDesign store "fi", "fl", "ffi" as single ligature glyphs: "Definition" is "De\ufb01nition" in the text layer
LIGATURES = str.maketrans({"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st"})
DAMAGED = ("FILE IS DAMAGED: {why}\n"
           "ROUTE\n 1. Tell the user to get a fresh copy of this file. Do not dig through the bytes;\n"
           "    until then no formula or page number can be taken from it.")


def searchable(text):
    """Page text as --find matches it: (as typeset, with words broken over a line end rejoined)."""
    t = text.translate(LIGATURES)
    # no ToUnicode map (Distiller-era PDFs): the fi and fl ligatures come out as the symbols at their byte codes
    t = re.sub(r"\u00ae(?=[a-z])", "fi", t)
    t = re.sub(r"\u00af(?=[a-z])", "fl", t)
    flat = re.sub(r"\s+", " ", t)
    return flat, re.sub(r"(\w)- (\w)", r"\1\2", flat)


HEAD_NUM = [re.compile(r"^(\d{1,4})$"), re.compile(r"^(\d{1,4})\s+\D"), re.compile(r"\D\s+(\d{1,4})$")]


def head_candidates(text):
    """Numbers standing alone at the start or end of a page's first/last lines."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = set()
    for l in lines[:2] + lines[-2:]:
        for rx in HEAD_NUM:
            m = rx.search(l)
            if m and int(m.group(1)) > 0:
                out.add(int(m.group(1)))
    return out


def head_numbers(texts):
    """Printed number per page, kept only where a neighbouring page continues the sequence."""
    cand = [head_candidates(t) for t in texts]
    out = []
    for i, cs in enumerate(cand):
        nxt = cand[i + 1] if i + 1 < len(cand) else set()
        prv = cand[i - 1] if i > 0 else set()
        ok = sorted(c for c in cs if c + 1 in nxt or c - 1 in prv)
        out.append(ok[0] if len(ok) == 1 else None)
    return out


class Printed:
    """Per-page printed numbers. Offsets drift inside books, so nothing here is global."""

    def __init__(self, doc, texts):
        n = len(texts)
        self.heads = head_numbers(texts)
        self.labels = [None] * n
        try:
            if doc.get_page_labels():
                for i in range(n):
                    lab = doc[i].get_label()
                    self.labels[i] = int(lab) if lab.isdigit() else None
        except Exception:
            pass
        both = [(h, l) for h, l in zip(self.heads, self.labels) if h is not None and l is not None]
        agree = sum(h == l for h, l in both) / len(both) if both else None
        have_labels = any(l is not None for l in self.labels)
        have_heads = sum(h is not None for h in self.heads) >= max(3, n // 10)
        if have_labels and (agree is None or agree >= 0.7):
            self.mode = "labels"
            self.how = "from the PDF's page labels" + (f" (match the running heads on {agree:.0%} of pages)" if agree is not None else " (no running heads to check them against)")
        elif have_heads:
            self.mode = "heads"
            self.how = "from running heads" + ("; the PDF's page labels are WRONG for this file" if have_labels else "")
        else:
            self.mode = None
            self.how = "not detected"

    def of(self, i):
        """Printed number of 1-based PDF page i as text, '' if unknown."""
        k = i - 1
        if self.mode == "labels":
            return str(self.labels[k]) if self.labels[k] is not None else ""
        if self.mode == "heads":
            if self.heads[k] is not None:
                return str(self.heads[k])
            for d in range(1, 6):  # nearest page that shows a number
                for j in (k - d, k + d):
                    if 0 <= j < len(self.heads) and self.heads[j] is not None:
                        return f"~{self.heads[j] + (k - j)}"
        return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("--find", metavar="REGEX")
    ap.add_argument("--pages", metavar="A-B", help="with --find: only search these PDF pages")
    ap.add_argument("--toc", action="store_true")
    ap.add_argument("--zoom", type=int, metavar="N", help="render PDF page N at 300 dpi for small print")
    ap.add_argument("--part", choices=["top", "middle", "bottom", "full"], default="full", help="with --zoom: which part of the page")
    a = ap.parse_args()
    f = a.file
    if not f.is_file():
        sys.exit(f"not a file: {f}")

    if f.suffix.lower() == ".epub":
        kind, detail, _ = epub_summary(f)
        print(f"{f.name}\nEPUB maths: {kind} ({detail})")
        twin = f.with_suffix(".pdf")
        print(f"Twin PDF: {twin if twin.is_file() else 'none'} (needed for page citations and image-only formulas)")
        print(f'ROUTE\n 1. uv run "{HERE / "epub2md.py"}" "{f}"   # chapters, then --find / --doc N')
        return

    import pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    try:
        doc = pymupdf.open(f)
        n = len(doc)
    except Exception:
        sys.exit(f"{f.name}\n" + DAMAGED.format(why="it does not open as a PDF (truncated or corrupt download)."))
    texts = []
    for i in range(n):
        try:
            texts.append(doc[i].get_text())
        except Exception:
            texts.append("")
    damaged = "error" in (pymupdf.TOOLS.mupdf_warnings() or "").lower()
    if n == 0 or (damaged and not any(t.strip() for t in texts)):
        sys.exit(f"{f.name}\n" + DAMAGED.format(why="structural errors, and no page of it can be read."))
    pr = Printed(doc, texts)

    def printed(i):
        p = pr.of(i) if 1 <= i <= n else ""
        return f" (printed {p})" if p else ""

    def page_set(spec):
        lo, _, hi = spec.partition("-")
        return range(int(lo), int(hi or lo) + 1)

    if a.find:
        rx = re.compile(a.find, re.I)
        hits = 0
        only = page_set(a.pages) if a.pages else None
        pages = 0
        for i, t in enumerate(texts, 1):
            if only is not None and i not in only:
                continue
            flat, joined = searchable(t)
            found = list(rx.finditer(flat))
            if not found:  # a word broken over a line end ("dur- ing"); real hyphens were tried first
                flat = joined
                found = list(rx.finditer(flat))
            if not found:
                continue
            hits += len(found)
            pages += 1
            if pages <= 25:
                m = found[0]
                extra = f"  (+{len(found) - 1} more on this page)" if len(found) > 1 else ""
                print(f"PDF p{i}{printed(i)}: …{flat[max(0, m.start() - 60): m.end() + 100]}…{extra}")
        more = " (first 25 pages shown; narrow with --pages A-B)" if pages > 25 else ""
        if not hits and not any(t.strip() for t in texts):
            more = " - this PDF has no text layer, so nothing can match; use --toc or view pages"
        print(f"{hits} hit(s) on {pages} page(s){more}. Text layer = locating only: it never tells you what a formula says.\n"
              "Printed numbers are a hint; cite the one you see on the page when you view it.")
        return

    if a.zoom:
        if not 1 <= a.zoom <= n:
            sys.exit(f"page out of range 1..{n}")
        page = doc[a.zoom - 1]
        r = page.rect
        h = r.height
        clip = {"full": r, "top": pymupdf.Rect(r.x0, r.y0, r.x1, r.y0 + 0.45 * h),
                "middle": pymupdf.Rect(r.x0, r.y0 + 0.28 * h, r.x1, r.y0 + 0.73 * h),
                "bottom": pymupdf.Rect(r.x0, r.y0 + 0.55 * h, r.x1, r.y1)}[a.part]
        out = Path(os.environ.get("READING_MATH_CACHE", Path.home() / ".cache" / "reading-math-sources")) / "zoom"
        out.mkdir(parents=True, exist_ok=True)
        png = out / f"{re.sub(r'[^A-Za-z0-9]+', '-', f.stem)[:40]}-p{a.zoom}-{a.part}.png"
        pix = page.get_pixmap(dpi=300 if a.part != "full" else 200, clip=clip)
        pix.save(png)
        if pix.is_unicolor:
            print(f"BLANK: PDF p{a.zoom} ({a.part}) renders as an empty area - nothing to read there"
                  + (". This file is damaged: the page is lost." if damaged else " (try --part full, or the page is blank)."))
            return
        print(f"{png}\nRead that file to view PDF p{a.zoom}{printed(a.zoom)} ({a.part}).")
        return

    toc = doc.get_toc(simple=True)
    if a.toc:
        for lvl, title, page in toc:
            print(f"{'  ' * (lvl - 1)}{title}  -> PDF p{page}{printed(page)}")
        if not toc:
            print("no outline in this PDF; use --find on a chapter title")
        return

    meta = doc.metadata or {}
    print(f"{f.name}\nPages: {n}   Producer: {(meta.get('producer') or '?')[:40]}   Creator: {(meta.get('creator') or '?')[:40]}")
    mid = [i for i in (n // 4, n // 2, 3 * n // 4) if i >= 1 and pr.of(i)]
    eg = "; e.g. " + ", ".join(f"PDF p{i} = printed {pr.of(i)}" for i in mid) if mid else ""
    empty = [i for i, t in enumerate(texts, 1) if len(t.strip()) < 40]
    no_text = len(empty) > 0.8 * n
    if no_text:
        print("Printed page numbers: not detected (no text layer): read the number off each page you view.")
    else:
        print(f"Printed page numbers: {pr.how}{eg}. The offset can drift between chapters: use --find or --toc for a\n"
              "  specific page, and cite the number visible on the page when you view it.")
    scanned = 0
    sample = list(range(0, n, max(1, n // 25)))
    for i in sample:
        pg = doc[i]
        area = abs(pg.rect) or 1
        try:
            big = any(abs(pymupdf.Rect(im["bbox"])) > 0.8 * area for im in pg.get_image_info())
        except Exception:
            big = False
        scanned += bool(big)
    if no_text:
        print("Text layer: NONE (scanned) - nothing to grep; view pages, use the outline to navigate")
    elif scanned > 0.5 * len(sample):
        print("Text layer: OCR over page scans - good enough to locate, wrong for symbols")
    else:
        print("Text layer: present - good for locating; formulas in it are unreliable")
    if empty and len(empty) <= 0.8 * n:
        print(f"  PDF pages with no text (--find cannot see them): p{ranges(empty)}")

    if toc:
        top = [t for t in toc if t[0] == 1]
        show = toc if len(toc) <= 40 else top[:40]
        print(f"Outline: {len(toc)} entries" + ("" if show is toc else f", top level shown (--toc for all)"))
        for lvl, title, page in show:
            print(f"  {'  ' * (lvl - 1)}{title[:70]}  -> PDF p{page}{printed(page)}")
    else:
        print("Outline: none (" + ("view the contents page to navigate" if no_text else "use --find on a heading") + ")")

    print("ROUTE (best source first)")
    k = 1
    if damaged:
        lost = f"p{ranges(empty)}" if empty else "some pages"
        print(f" {k}. FILE IS DAMAGED: structural errors; {lost} cannot be read (unreadable, not scanned), and other tools\n"
              "    (pdftotext, pdftoppm) may number the pages differently. Tell the user to get a fresh copy and which\n"
              "    pages are lost; the routes below serve the remaining pages only. For those, Read(pages=N) can be\n"
              "    shifted by the lost pages: view page N with --zoom N --part full, and check the printed number on it.\n"
              "    A page that still renders may be cut short: do not quote a statement whose end you cannot see.")
        k += 1
    front = " ".join(texts[:2])
    stamps = list(ARXIV.finditer(front))  # a footer may repeat the id without its version
    m = next((x for x in stamps if re.search(r"v\d+$", x.group(1))), stamps[0] if stamps else None)
    if m:
        bare = "" if re.search(r"v\d+$", m.group(1)) else (" (no version on the stamp: this fetches the latest one, which may be newer than the PDF;\n"
                                                             "    say so, and view the PDF page for any formula whose exact form matters)")
        date = re.match(r"\s*\[[\w.\-]+\]\s*(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})", front[m.end():])
        when = f" ({date.group(1)})" if date else ""
        print(f" {k}. arXiv:{m.group(1)}{when} is stamped on this PDF: the file is that preprint, whatever year its name carries,\n"
              f"    so its equation and page numbers are that arXiv version's, not a journal printing's\n"
              f'    -> author\'s TeX:  uv run "{HERE / "arxiv_src.py"}" {m.group(1)}{bare}')
        k += 1
    twin = f.with_suffix(".epub")
    if twin.is_file():
        kind, detail, what = epub_summary(twin)
        if kind == "MACHINE-READABLE":
            print(f' {k}. Twin EPUB is MACHINE-READABLE ({detail}) -> {what}:  uv run "{HERE / "epub2md.py"}" "{twin}"')
        else:
            print(f' {k}. Twin EPUB is IMAGES ONLY ({detail}) -> no gain for formulas; skip it  ("{twin}")')
        k += 1
    if not m and not twin.is_file():
        print(f' {k}. No arXiv stamp, no twin EPUB. If this is a paper or lecture notes (not a published book), look for an arXiv version:  uv run "{HERE / "arxiv_src.py"}" --title "<paper title>" --author <surname>')
        k += 1
    print(f' {k}. Page images: Read(file_path=<pdf>, pages="N") - the fallback for every formula not covered above, and the check for anything that looks off')


if __name__ == "__main__":
    main()
