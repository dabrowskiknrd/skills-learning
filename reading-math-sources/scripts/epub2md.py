# /// script
# requires-python = ">=3.10"
# dependencies = ["beautifulsoup4>=4.12", "lxml>=5", "pypandoc-binary>=1.13"]
# ///
"""Convert EPUB chapters to Markdown with the maths as LaTeX.

  uv run epub2md.py BOOK.epub                 list chapters + how each stores maths
  uv run epub2md.py BOOK.epub --find REGEX    which chapters mention REGEX
  uv run epub2md.py BOOK.epub --doc 5 [6 ..]  convert chapters, print the .md paths
  uv run epub2md.py BOOK.epub --all           convert every chapter

Maths provenance, best first:
  tex     the publisher's own LaTeX (MathML alttext, <annotation>, or image alt)
  mathml  MathML converted to LaTeX by pandoc (faithful structure, not the author's source)
  image   an equation or figure stored only as a picture: written as
          ⟦IMAGE: /abs/path⟧ -- it must be VIEWED (Read the file) before quoting
"""
import argparse, hashlib, html, os, posixpath, re, sys, zipfile
from pathlib import Path
from urllib.parse import unquote

CACHE = Path(os.environ.get("READING_MATH_CACHE", Path.home() / ".cache" / "reading-math-sources"))
TEX_HINT = re.compile(r"\$\$|\\\(|\\\[|\\begin\{|\\[a-zA-Z]{2,}|[_^]\{")
DOC_EXT = (".xhtml", ".html", ".htm")


def spine(z):
    """Ordered list of (zip_path, title) for the reading-order documents."""
    names = set(z.namelist())
    opf = None
    try:
        c = z.read("META-INF/container.xml").decode("utf-8", "replace")
        m = re.search(r'full-path="([^"]+)"', c)
        opf = m.group(1) if m else None
    except KeyError:
        pass
    if not opf or opf not in names:
        docs = sorted(n for n in names if n.lower().endswith(DOC_EXT))
        return [(n, "") for n in docs]
    base = posixpath.dirname(opf)
    o = z.read(opf).decode("utf-8", "replace")
    items = {}
    for tag in re.findall(r"<(?:\w+:)?item\b[^>]*>", o):
        i = re.search(r'\bid="([^"]+)"', tag)
        h = re.search(r'\bhref="([^"]+)"', tag)
        if i and h:
            items[i.group(1)] = posixpath.normpath(posixpath.join(base, unquote(h.group(1))))
    order = [items[r] for r in re.findall(r'<(?:\w+:)?itemref\b[^>]*\bidref="([^"]+)"', o) if r in items]
    order = [p for p in order if p in names]
    # titles from the navigation document / NCX
    titles = {}
    for n in names:
        low = n.lower()
        if low.endswith(".ncx"):
            t = z.read(n).decode("utf-8", "replace")
            for lab, src in re.findall(r"<navLabel>\s*<text>(.*?)</text>\s*</navLabel>\s*<content[^>]*src=\"([^\"]+)\"", t, flags=re.S):
                p = posixpath.normpath(posixpath.join(posixpath.dirname(n), unquote(src.split("#")[0])))
                titles.setdefault(p, html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", lab))).strip())
    return [(p, titles.get(p, "")) for p in order]


def census(raw):
    """Cheap regex count of how one document stores maths."""
    math = len(re.findall(r"<(?:\w+:)?math[\s>]", raw))
    tex_attr = len(re.findall(r'alttext="[^"]*[\\$][^"]*"', raw)) + len(re.findall(r"<(?:\w+:)?annotation[^>]*x-tex", raw))
    img_tex = len(re.findall(r'<img\b[^>]*\balt="[^"]*(?:\$\$|\\\(|\\begin\{|\\[a-zA-Z]{3,})[^"]*"', raw))
    img_mml = len(re.findall(r'<img\b[^>]*\balt="\s*&lt;(?:\w+:)?math', raw))
    img = len(re.findall(r"<img\b", raw))
    tex = min(math, tex_attr + img_tex) if math else img_tex
    tex = max(tex, tex_attr)
    mathml = max(0, math - tex) + img_mml
    image = max(0, img - img_tex - img_mml) if not math else max(0, img - img_tex - img_mml)
    if math and img_tex:  # Springer "both": fallback images live inside <math>
        image = max(0, img - img_tex - img_mml)
    return tex, mathml, image


def first_heading(raw):
    m = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", raw, flags=re.S)
    if not m:
        m = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1)))).strip()[:70] if m else ""


def cache_dir(epub):
    st = epub.stat()
    key = hashlib.sha1(f"{epub.resolve()}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:8]
    slug = re.sub(r"[^A-Za-z0-9]+", "-", epub.stem)[:60].strip("-")
    return CACHE / "epub" / f"{slug}-{key}"


def clean_tex(s):
    s = html.unescape(s).strip()
    s = re.sub(r"^\$\$?|\$\$?$", "", s).strip()
    s = re.sub(r"^\\[\(\[]|\\[\)\]]$", "", s).strip()
    return s


def convert(z, path, outdir, idx, title):
    import warnings
    from bs4 import BeautifulSoup, NavigableString, XMLParsedAsHTMLWarning
    import pypandoc

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    raw = z.read(path).decode("utf-8", "replace")
    soup = BeautifulSoup(raw, "lxml")
    body = soup.body or soup
    for t in body.find_all(["script", "style"]):
        t.decompose()
    slots, stats = [], {"tex": 0, "mathml": 0, "image": 0}
    imgdir = outdir / "img"

    def is_math(tag):
        return tag.name and tag.name.split(":")[-1] == "math"

    def displayed(tag):
        if tag.get("display") == "block" or tag.get("mode") == "display":
            return True
        for a in tag.parents:
            cls = " ".join(a.get("class", [])) if hasattr(a, "get") else ""
            if "InlineEquation" in cls or "inline" in cls.lower():
                return False
            if re.search(r"\bEquation\b|NumberedEquation|display", cls):
                return True
        return False

    def slot(kind, payload, disp):
        slots.append((kind, payload, disp))
        return NavigableString(f"ZQXSLOT{len(slots) - 1}ZQX")

    def image_marker(img, disp):
        src = img.get("src") or ""
        zp = posixpath.normpath(posixpath.join(posixpath.dirname(path), unquote(src)))
        local = None
        try:
            data = z.read(zp)
            imgdir.mkdir(parents=True, exist_ok=True)
            local = imgdir / f"{idx:03d}-{posixpath.basename(zp)}"
            local.write_bytes(data)
        except KeyError:
            pass
        stats["image"] += 1
        return slot("image", str(local) if local else f"(missing in EPUB: {src})", disp)

    for m in [t for t in body.find_all(True) if is_math(t)]:
        if m.parent is None:
            continue
        disp = displayed(m)
        tex = None
        if TEX_HINT.search(m.get("alttext", "") or ""):
            tex = m.get("alttext")
        if tex is None:
            for a in m.find_all(True):
                if a.name.split(":")[-1] == "annotation" and "tex" in (a.get("encoding", "").lower()):
                    tex = a.get_text()
                    break
        if tex is None:
            im = m.find("img")
            if im is not None and TEX_HINT.search(im.get("alt", "") or ""):
                tex = im.get("alt")
        if tex is not None:
            stats["tex"] += 1
            m.replace_with(slot("tex", clean_tex(tex), disp))
        else:
            for a in m.find_all(True):
                if a.name.split(":")[-1] in ("annotation", "annotation-xml"):
                    a.decompose()
            if disp:
                m["display"] = "block"
            stats["mathml"] += 1

    for im in body.find_all("img"):
        if any(is_math(p) for p in im.parents if getattr(p, "name", None)):
            continue
        alt = im.get("alt", "") or ""
        disp = displayed(im)
        if re.match(r"\s*<(?:\w+:)?math\b", alt):
            frag = re.sub(r"(</?)\w+:", r"\1", alt)
            frag = re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", frag)
            node = BeautifulSoup(frag, "lxml").find("math")
            if node is not None:
                if 'display="block"' in alt or disp:
                    node["display"] = "block"
                im.replace_with(node)
                stats["mathml"] += 1
                continue
        if TEX_HINT.search(alt) and not re.match(r"\s*<", alt):
            stats["tex"] += 1
            im.replace_with(slot("tex", clean_tex(alt), disp))
        else:
            im.replace_with(image_marker(im, disp))

    # pandoc has no plain-text subscript: it would write ∫ _(A) and f ₁. Keep the structure explicit instead.
    for t in body.find_all(["sub", "sup"]):
        t.insert_before(NavigableString(f"ZQX{t.name.upper()}OZQX"))
        t.insert_after(NavigableString(f"ZQX{t.name.upper()}CZQX"))
        t.unwrap()

    md = pypandoc.convert_text(
        str(body), "gfm-tex_math_gfm+tex_math_dollars-raw_html", format="html", extra_args=["--wrap=none", "--quiet"]
    )

    def fill(mo):
        kind, payload, disp = slots[int(mo.group(1))]
        if kind == "image":
            return f"\n\n⟦IMAGE: {payload}⟧\n\n" if disp else f" ⟦IMAGE: {payload}⟧ "
        return f"\n\n$$\n{payload}\n$$\n\n" if disp else f"${payload}$"

    # pandoc escapes characters that only matter to a Markdown renderer; a reader wants |x| and [0,1)
    md = "\n".join(
        l if l.lstrip().startswith("|") else re.sub(r"\\([<>\[\]|~^])", r"\1", l) for l in md.split("\n")
    )
    # Springer sets theorem text as <i>Let</i><math/><i>be ...</i> with no spaces: restore them around the maths
    md = re.sub(r"(?<=[^\s*])(\*+)(ZQXSLOT\d+ZQX)", r"\1 \2", md)
    md = re.sub(r"(ZQXSLOT\d+ZQX)(\*+)(?=\w)", r"\1 \2", md)
    md = re.sub(r"ZQXSLOT(\d+)ZQX", fill, md)
    md = re.sub(r"ZQX(SUB|SUP)([OC])ZQX", lambda mo: ("<" if mo.group(2) == "O" else "</") + mo.group(1).lower() + ">", md)
    md = md.replace("\u00a0", " ").replace("\u200b", "")  # so that grep 'Theorem 4.2.2' matches
    md = re.sub(r"^\\\((\w[\w.]*)\\\)$", r"(\1)", md, flags=re.M)  # equation number on its own line: \(1\) -> (1)
    md = re.sub(r"\n{3,}", "\n\n", md)
    name = re.sub(r"[^A-Za-z0-9]+", "-", title or posixpath.basename(path))[:50].strip("-")
    out = outdir / f"{idx:03d}-{name}.md"
    head = (
        f"<!-- {path} | maths: {stats['tex']} publisher-TeX, {stats['mathml']} MathML->TeX (pandoc), "
        f"{stats['image']} image-only (⟦IMAGE: ...⟧ = view the file before quoting) -->\n\n"
    )
    out.write_text(head + md, encoding="utf-8")
    return out, stats, len(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("epub", type=Path)
    ap.add_argument("--find", metavar="REGEX", help="report chapters whose text matches (case-insensitive)")
    ap.add_argument("--doc", type=int, nargs="+", metavar="N", help="chapter numbers to convert")
    ap.add_argument("--all", action="store_true", help="convert every chapter")
    ap.add_argument("--out", type=Path, help="output directory (default: cache)")
    a = ap.parse_args()
    if not a.epub.is_file():
        sys.exit(f"not a file: {a.epub}")
    z = zipfile.ZipFile(a.epub)
    sp = spine(z)
    outdir = a.out or cache_dir(a.epub)

    if a.find:
        rx = re.compile(a.find, re.I)
        boxed = False
        for i, (p, _) in enumerate(sp, 1):
            raw = z.read(p).decode("utf-8", "replace")
            txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<img\b[^>]*>", " ▢ ", raw))))
            hits = list(rx.finditer(txt))
            if hits:
                print(f"[{i}] {posixpath.basename(p)}  {len(hits)} hit(s)")
                for h in hits[:3]:
                    print("     …" + txt[max(0, h.start() - 70): h.end() + 110] + "…")
                boxed = boxed or "▢" in txt
        if boxed:
            print("▢ = a formula or picture stored as an image element (its TeX, if any, appears after --doc N).")
        return

    if a.doc or a.all:
        want = range(1, len(sp) + 1) if a.all else a.doc
        outdir.mkdir(parents=True, exist_ok=True)
        for i in want:
            if not 1 <= i <= len(sp):
                print(f"[{i}] out of range 1..{len(sp)}")
                continue
            p, t = sp[i - 1]
            title = t or first_heading(z.read(p).decode("utf-8", "replace"))
            out, st, n = convert(z, p, outdir, i, title)
            print(f"[{i}] {out}  ({n // 1000} k chars; tex={st['tex']} mathml={st['mathml']} image={st['image']})")
        print("Next: grep -n the .md for the passage, then Read that line range. View every ⟦IMAGE: …⟧ you quote.")
        return

    tot = [0, 0, 0]
    print(f"{a.epub.name}\n  #  {'kB':>5} {'tex':>6} {'mathml':>6} {'image':>6}  title")
    for i, (p, t) in enumerate(sp, 1):
        raw = z.read(p).decode("utf-8", "replace")
        c = census(raw)
        tot = [x + y for x, y in zip(tot, c)]
        print(f"{i:3d}  {len(raw) // 1000:5d} {c[0]:6d} {c[1]:6d} {c[2]:6d}  {(t or first_heading(raw))[:60]}  ({posixpath.basename(p)})")
    tex, mml, img = tot
    print(f"TOTAL maths: {tex} publisher-TeX, {mml} MathML, {img} images without TeX")
    if tex + mml == 0:
        verdict = "IMAGES ONLY - use this EPUB for prose and structure; read every formula from the PDF page (or the image file)."
    else:
        verdict = "MACHINE-READABLE - convert the chapter you need with --doc N and quote the LaTeX from the .md."
        if img:
            verdict += f" {img} items are image-only (often display equations or figures): each appears as ⟦IMAGE: path⟧ and must be viewed before quoting."
    print("VERDICT:", verdict)


if __name__ == "__main__":
    main()
