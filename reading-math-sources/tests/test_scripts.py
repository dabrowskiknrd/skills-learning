"""Regression tests for the reading-math-sources scripts.

  cd reading-math-sources && uv run --with pytest --with pymupdf pytest tests -q

Every fixture is built here, so the tests need no library files and no network.
"""
import importlib.util, os, subprocess, sys, zipfile
from pathlib import Path

import pymupdf
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def run(script, *args, cache=None):
    env = dict(os.environ)
    if cache:
        env["READING_MATH_CACHE"] = str(cache)
    r = subprocess.run(["uv", "run", str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def make_pdf(path, pages):
    """pages: list of lists of lines. A font with real fi/fl ligature glyphs is embedded."""
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page()
        page.insert_font(fontname="F0", fontbuffer=pymupdf.Font("tiro").buffer)
        for k, line in enumerate(lines):
            page.insert_text((72, 90 + 16 * k), line, fontname="F0", fontsize=11)
    doc.save(path)
    return path


# ---------------------------------------------------------------- probe.py --find

@pytest.fixture(scope="module")
def lig_pdf(tmp_path_factory):
    d = tmp_path_factory.mktemp("lig")
    return make_pdf(d / "lig.pdf", [
        ["De\ufb01nition 1.1. A measure is \u03c3-\ufb01nite when the space is a countable union.",
         "The in\ufb02uence of the step size is studied dur-",
         "ing the burn-in phase of the chain."],
        ["Remark. Nothing to see on this page."],
        ["Dual averaging appears here. Dual averaging again. And dual averaging a third time."],
    ])


def test_fixture_really_has_ligature_glyphs(lig_pdf):
    text = pymupdf.open(lig_pdf)[0].get_text()
    assert "\ufb01" in text and "\ufb02" in text, "fixture lost its ligatures; the tests below would prove nothing"


@pytest.mark.parametrize("query", ["Definition 1", "finite", "influence"])
def test_find_matches_words_typeset_with_ligatures(lig_pdf, query):
    code, out = run("probe.py", lig_pdf, "--find", query)
    assert "PDF p1" in out, out


def test_find_matches_word_hyphenated_over_a_line_break(lig_pdf):
    code, out = run("probe.py", lig_pdf, "--find", "during the burn-in")
    assert "PDF p1" in out, out


def test_find_keeps_real_hyphens_searchable(lig_pdf):
    code, out = run("probe.py", lig_pdf, "--find", "burn-in phase")
    assert "PDF p1" in out, out


def test_find_prints_one_line_per_page(lig_pdf):
    code, out = run("probe.py", lig_pdf, "--find", "dual averaging")
    assert sum(l.startswith("PDF p3") for l in out.splitlines()) == 1, out
    assert "+2 more on this page" in out, out
    assert "3 hit(s) on 1 page(s)" in out, out


# ---------------------------------------------------------------- probe.py routing

def test_versioned_arxiv_stamp_wins_over_bare_id(tmp_path):
    pdf = make_pdf(tmp_path / "stamp.pdf", [[
        "arXiv: arXiv:1601.08057",
        "On the Geometric Ergodicity of Hamiltonian Monte Carlo",
        "arXiv:1601.08057v5 [stat.CO] 8 Sep 2026",
    ]])
    code, out = run("probe.py", pdf)
    assert "arXiv:1601.08057v5 (8 Sep 2026) is stamped" in out, out


def test_stamp_line_gives_date_and_says_numbers_are_the_preprints(tmp_path):
    pdf = make_pdf(tmp_path / "The No-U-Turn Sampler - Hoffman, Gelman, 2014.pdf", [[
        "The No-U-Turn Sampler: Adaptively Setting Path Lengths in Hamiltonian Monte Carlo",
        "arXiv:1111.4246v1 [stat.CO] 18 Nov 2011",
    ]])
    code, out = run("probe.py", pdf)
    route = out.split("ROUTE")[1]
    assert "18 Nov 2011" in route, out
    assert "preprint" in route and "equation and page numbers" in route, out


def test_bare_arxiv_id_is_reported_as_unversioned(tmp_path):
    pdf = make_pdf(tmp_path / "bare.pdf", [["arXiv: arXiv:1601.08057", "A paper whose only arXiv mark is a footer without any version number."]])
    code, out = run("probe.py", pdf)
    assert "arXiv:1601.08057 " in out and "no version" in out, out


@pytest.mark.parametrize("keep", [0.5, 0.0])
def test_unreadable_pdf_reports_damage_and_no_page_route(tmp_path, lig_pdf, keep):
    data = Path(lig_pdf).read_bytes()
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(data[: int(len(data) * keep)] if keep else b"this is not a pdf at all")
    code, out = run("probe.py", bad)
    assert "FILE IS DAMAGED" in out, out
    assert "Traceback" not in out, out
    assert "Text layer: present" not in out and "Page images" not in out, out
    assert code != 0


@pytest.fixture(scope="module")
def half_damaged_pdf(tmp_path_factory):
    """30 pages; the bytes holding the middle pages are wiped, the cross-reference table survives."""
    d = tmp_path_factory.mktemp("dmg")
    good = make_pdf(d / "good.pdf", [[f"Page {i} of the paper. " + "Lorem ipsum dolor sit amet. " * 3] * 12 for i in range(1, 31)])
    data = bytearray(Path(good).read_bytes())
    a, b = int(len(data) * 0.40), int(len(data) * 0.55)
    data[a:b] = b"\0" * (b - a)
    bad = d / "half.pdf"
    bad.write_bytes(bytes(data))
    return bad


def test_partly_damaged_pdf_warns_about_page_numbering_and_cut_pages(half_damaged_pdf):
    code, out = run("probe.py", half_damaged_pdf)
    route = out.split("ROUTE")[1]
    assert "FILE IS DAMAGED" in route, out
    assert "--zoom" in route and "shifted" in route, out   # Read(pages=N) skips lost pages
    assert "cut short" in route, out                       # a page that renders may be incomplete
    assert "Page images" in route, out                     # the rest of the file is still usable


def test_zoom_says_when_the_page_is_blank(tmp_path):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 90), "A page with some text on it, long enough to count as text.")
    doc.new_page()
    pdf = tmp_path / "blank2.pdf"
    doc.save(pdf)
    code, out = run("probe.py", pdf, "--zoom", "2", cache=tmp_path)
    assert "BLANK" in out, out
    code, out = run("probe.py", pdf, "--zoom", "1", cache=tmp_path)
    assert "BLANK" not in out, out


def test_scan_without_text_does_not_suggest_find(tmp_path, lig_pdf):
    src = pymupdf.open(lig_pdf)
    out_doc = pymupdf.open()
    for page in src:
        p = out_doc.new_page(width=page.rect.width, height=page.rect.height)
        p.insert_image(p.rect, pixmap=page.get_pixmap(dpi=72))
    scan = tmp_path / "scan.pdf"
    out_doc.save(scan)
    code, out = run("probe.py", scan)
    assert "Text layer: NONE" in out, out
    assert "use --find" not in out, out


# ---------------------------------------------------------------- epub2md.py

CHAPTER = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Ch</title></head><body>
<h1>4 Signed Measures</h1>
<p>Theorem&#160;4.2.2 (Radon&#8211;Nikodym Theorem).&#160;Let <math alttext="$(X,\\mathcal{A})$"><mi>X</mi></math> be a space; see Sect.&#160;10.&#8203;2.</p>
<div class="Equation"><math display="block" alttext="$$\\int g\\,d\\mu =\\sup \\mathcal{F}$$"><mi>g</mi></math></div>
<div class="EquationNumber">(1)</div>
<p><i class="EmphasisTypeItalic ">Let</i><span class="InlineEquation"><math display="inline" alttext="$$M\\subset \\mathbb {R}^2$$"><mi>M</mi></math></span><i class="EmphasisTypeItalic ">be a compact domain having k components.</i></p>
<p>Then ν(A) = ∫<sub>A</sub> g dμ, where f<sub>1</sub> lies in L<sup>p</sup> and A<sub>k<sub>n</sub></sub> is nested.</p>
<p>and then more text.</p>
</body></html>"""


@pytest.fixture(scope="module")
def epub_md(tmp_path_factory):
    d = tmp_path_factory.mktemp("epub")
    epub = d / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>')
        z.writestr("OEBPS/content.opf", '<package><manifest><item id="c1" href="ch1.xhtml"/></manifest><spine><itemref idref="c1"/></spine></package>')
        z.writestr("OEBPS/ch1.xhtml", CHAPTER)
    code, out = run("epub2md.py", epub, "--doc", "1", "--out", d / "out")
    assert code == 0, out
    return next((d / "out").glob("*.md")).read_text("utf-8")


def test_epub_markdown_is_greppable_with_plain_spaces(epub_md):
    assert "Theorem 4.2.2 (Radon" in epub_md, epub_md
    assert "Sect. 10.2" in epub_md, epub_md
    assert "\u00a0" not in epub_md and "\u200b" not in epub_md


def test_epub_keeps_publisher_tex(epub_md):
    assert "$(X,\\mathcal{A})$" in epub_md
    assert "\\int g\\,d\\mu =\\sup \\mathcal{F}" in epub_md


def test_epub_italic_text_does_not_swallow_the_spaces_around_inline_maths(epub_md):
    assert "*Let* $M\\subset \\mathbb {R}^2$ *be a compact domain" in epub_md, epub_md


def test_epub_subscripts_and_superscripts_stay_explicit(epub_md):
    assert "∫<sub>A</sub> g dμ" in epub_md, epub_md
    assert "f<sub>1</sub>" in epub_md and "L<sup>p</sup>" in epub_md, epub_md
    assert "A<sub>k<sub>n</sub></sub>" in epub_md, epub_md
    assert "_(" not in epub_md and "^(" not in epub_md and "₁" not in epub_md, epub_md


def test_epub_equation_number_is_plain(epub_md):
    assert "\n(1)\n" in epub_md, epub_md
    assert "\\(1\\)" not in epub_md


# ---------------------------------------------------------------- arxiv_src.py

def load_arxiv(monkeypatch, feed):
    spec = importlib.util.spec_from_file_location("arxiv_src", SCRIPTS / "arxiv_src.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "get", lambda url: feed.encode())
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    return mod


def entry(aid, title, *authors):
    names = "".join(f"<author><name>{a}</name></author>" for a in authors)
    return f"<entry><id>http://arxiv.org/abs/{aid}</id><published>2010-01-01T00:00:00Z</published><title>{title}</title>{names}</entry>"


def test_search_reports_exact_match(monkeypatch, capsys):
    feed = "<feed>" + entry("1206.1901v1", "MCMC using Hamiltonian dynamics", "Radford M. Neal") + "</feed>"
    mod = load_arxiv(monkeypatch, feed)
    assert mod.search("MCMC using Hamiltonian dynamics", "Neal") == 0
    out = capsys.readouterr().out
    assert "VERDICT: MATCH 1206.1901v1" in out, out


def test_search_says_no_match_when_nothing_fits(monkeypatch, capsys):
    feed = "<feed>" + entry("2508.00617v1", "Constructive Disintegration and Conditional Modes", "N. Da Costa") \
        + entry("2304.14963v1", "Flow Away your Differences", "Chris Pollard") + "</feed>"
    mod = load_arxiv(monkeypatch, feed)
    assert mod.search("Conditioning as disintegration", "Pollard") == 3
    out = capsys.readouterr().out
    assert "VERDICT: NO MATCH" in out, out


def test_search_separates_retitled_preprint_from_other_peoples_paper(monkeypatch, capsys):
    feed = "<feed>" \
        + entry("1011.0834v1", 'Discussions on "Riemann manifold Langevin and Hamiltonian Monte Carlo methods"', "Simon Barthelme", "Nicolas Chopin") \
        + entry("0907.1100v3", "Riemannian Manifold Hamiltonian Monte Carlo", "Mark Girolami", "Ben Calderhead", "Siu A. Chin") \
        + "</feed>"
    mod = load_arxiv(monkeypatch, feed)
    assert mod.search("Riemann manifold Langevin and Hamiltonian Monte Carlo methods", "Girolami") == 0
    out = capsys.readouterr().out
    assert "VERDICT: NO EXACT MATCH" in out and "0907.1100v3" in out.split("VERDICT")[1], out
    assert "1011.0834v1" not in out.split("VERDICT")[1], out
    rows = {l.split()[0]: l for l in out.splitlines() if l[:1].isdigit()}
    assert "author=no" in rows["1011.0834v1"] and "author=yes" in rows["0907.1100v3"], out


TEX = r"""\documentclass{article}
\newcommand{\E}{\mathbb{E}}
%% \newcommand{\bm}[1]{\mbox{\boldmath$#1$}}
  % \def\old{x}
\def\LF{\mathrm{Leapfrog}}
\DeclareMathOperator{\Var}{Var}
\newcommand{\bb}{\bm{b}}
\newcommand{\bm}[1]{\boldsymbol{#1}}
\begin{document}
First $\E[x]$ here.
Then $\bb$ there.
Last $x$ %% an old draft used \Var and \LF here
\end{document}
"""


@pytest.fixture()
def tex_cache(tmp_path):
    src = tmp_path / "arxiv" / "1111.4246v1" / "src"
    (src / "copy").mkdir(parents=True)
    (src / "main.tex").write_text(TEX)
    (src / "copy" / "main.tex").write_text(TEX)  # some tarballs ship the same file twice
    return tmp_path


def test_macro_count_ignores_comments_and_duplicate_files(tex_cache):
    code, out = run("arxiv_src.py", "1111.4246v1", cache=tex_cache)
    assert code == 0, out
    assert "5 author macro definitions" in out, out


def test_macros_flag_lists_live_definitions(tex_cache):
    code, out = run("arxiv_src.py", "1111.4246v1", "--macros", cache=tex_cache)
    assert code == 0, out
    assert r"\newcommand{\E}{\mathbb{E}}" in out and r"\def\LF" in out and r"\DeclareMathOperator{\Var}" in out, out
    assert "boldmath" not in out and r"\def\old" not in out, out
    assert "<- main file" in out, "--macros on the first call must still name the .tex files:\n" + out


def test_macros_with_a_line_range_lists_only_the_macros_those_lines_use(tex_cache):
    code, out = run("arxiv_src.py", "1111.4246v1", "--macros", "10-10", cache=tex_cache)
    assert code == 0, out
    assert r"\newcommand{\E}" in out, out
    assert r"\def\LF" not in out and r"\Var" not in out and r"\newcommand{\bb}" not in out, out


def test_macros_line_range_follows_macros_defined_through_other_macros(tex_cache):
    code, out = run("arxiv_src.py", "1111.4246v1", "--macros", "main.tex:11-11", cache=tex_cache)
    assert code == 0, out
    assert r"\newcommand{\bb}{\bm{b}}" in out and r"\newcommand{\bm}[1]" in out, out
    assert r"\newcommand{\E}" not in out, out


# ---------------------------------------------------------------- late additions

def load_probe():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("probe", SCRIPTS / "probe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_search_text_undoes_standard_encoding_ligatures_shown_as_symbols():
    # Distiller-era PDFs without a ToUnicode map: fi is byte 0xAE, fl is 0xAF, extracted as (R) and macron
    flat, _ = load_probe().searchable("each sigma-\u00aenite; De\u00aenition 1; in\u00afuence. Acrobat\u00ae Distiller")
    assert "sigma-finite" in flat and "Definition 1" in flat and "influence" in flat, flat
    assert "Acrobat\u00ae Distiller" in flat, flat


def test_epub_find_explains_the_box_placeholder(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>')
        z.writestr("OEBPS/content.opf", '<package><manifest><item id="c1" href="ch1.xhtml"/></manifest><spine><itemref idref="c1"/></spine></package>')
        z.writestr("OEBPS/ch1.xhtml", '<html><body><p>Theorem 1. Let <img src="a.gif" alt="$$X$$"/> be a space.</p></body></html>')
    code, out = run("epub2md.py", epub, "--find", "Theorem 1")
    assert "\u25a2" in out and "\u25a2 = " in out, out


def test_macros_line_range_ignores_commented_out_text_in_the_passage(tex_cache):
    code, out = run("arxiv_src.py", "1111.4246v1", "--macros", "12-12", cache=tex_cache)
    assert code == 0, out
    assert "0 author macro definitions" in out and r"\Var" not in out and r"\def\LF" not in out, out
