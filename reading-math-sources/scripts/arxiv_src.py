# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Fetch the author's TeX source of an arXiv paper, or find a paper's arXiv id.

  uv run arxiv_src.py 1701.02434v2        download + unpack, list the .tex files
  uv run arxiv_src.py --title "Riemann manifold Langevin and Hamiltonian Monte Carlo methods" --author Calderhead

Give the versioned id stamped on the PDF (v2, not the bare id) so the source
matches the pages being cited. Files are unpacked, never executed.
"""
import argparse, gzip, io, os, re, sys, tarfile, time, urllib.parse, urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("READING_MATH_CACHE", Path.home() / ".cache" / "reading-math-sources")) / "arxiv"
UA = {"User-Agent": "reading-math-sources/1.0 (personal reading tool)"}
ID = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?$")


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def search(title, author=None):
    import difflib

    words = [w for w in re.findall(r"[A-Za-z]{4,}", title)][:6]
    queries = [f'ti:"{title}"', " AND ".join(f"ti:{w}" for w in words)]
    if author:  # preprints are often retitled: same author, any title word
        queries.append(f"au:{author.split()[-1]} AND (" + " OR ".join(f"ti:{w}" for w in words) + ")")
    found = {}
    for q in queries:
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": q, "max_results": 15})
        xml = get(url).decode("utf-8", "replace")
        for e in re.findall(r"<entry>(.*?)</entry>", xml, flags=re.S):
            g = lambda tag: re.sub(r"\s+", " ", (re.search(rf"<{tag}>(.*?)</{tag}>", e, flags=re.S) or [0, ""])[1]).strip()
            aid = g("id").rsplit("/abs/", 1)[-1]
            sim = difflib.SequenceMatcher(None, title.lower(), g("title").lower()).ratio()
            found[aid] = (sim, g("published")[:10], g("title"), ", ".join(re.findall(r"<name>(.*?)</name>", e)))
        time.sleep(3)
    if not found:
        print("No arXiv match for that title. Treat the paper as PDF-only: view pages for formulas.")
        return 3
    for aid, (sim, date, t, authors) in sorted(found.items(), key=lambda kv: -kv[1][0])[:5]:
        print(f"{aid:18} {date}  match={sim:.2f}  {t[:90]}\n{'':18} {authors[:90]}")
    print("Use one only if title AND authors match. A journal PDF can differ from the arXiv version:\n"
          "name the version you quote, and view the PDF page for any formula whose exact form matters.")
    return 0


def unpack(aid):
    dest = CACHE / aid.replace("/", "_")
    src = dest / "src"
    if not src.is_dir() or not any(src.iterdir()):
        dest.mkdir(parents=True, exist_ok=True)
        data = get(f"https://arxiv.org/e-print/{aid}")
        if data[:4] == b"%PDF":
            print(f"arXiv:{aid} was submitted as PDF only - no TeX source exists. View pages for formulas.")
            return 3
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        src.mkdir(exist_ok=True)
        try:
            tf = tarfile.open(fileobj=io.BytesIO(data))
        except tarfile.TarError:
            (src / "main.tex").write_bytes(data)  # single-file submission
        else:
            for m in tf.getmembers():
                target = (src / m.name).resolve()
                if not m.isfile() or src.resolve() not in target.parents:
                    continue  # skip links, devices and anything escaping the folder
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tf.extractfile(m).read())
        time.sleep(1)
    tex = sorted(src.rglob("*.tex"))
    if not tex:
        print(f"arXiv:{aid} source has no .tex file ({len(list(src.rglob('*')))} files in {src}). View pages for formulas.")
        return 3
    print(f"arXiv:{aid} source in {src}")
    macros = 0
    for t in tex:
        s = t.read_text("utf-8", "replace")
        main = "  <- main file" if "\\documentclass" in s or "\\documentstyle" in s else ""
        macros += len(re.findall(r"\\(?:re)?newcommand|\\def\\|\\DeclareMathOperator", s))
        print(f"  {s.count(chr(10)) + 1:6d} lines  {t.relative_to(src)}{main}")
    for extra in sorted(list(src.rglob("*.sty")) + list(src.rglob("*.cls"))):
        print(f"         (style)  {extra.relative_to(src)}")
    print(f"{macros} author macro definitions found. Next: grep -n for the section or a phrase beside the formula,\n"
          "Read that line range, and expand author macros (grep -n 'newcommand\\|\\\\def') before quoting.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id", nargs="?", help="arXiv id, with the version stamped on the PDF")
    ap.add_argument("--title", help="search arXiv by title instead")
    ap.add_argument("--author", help="with --title: an author surname, catches retitled preprints")
    a = ap.parse_args()
    if a.title:
        sys.exit(search(a.title, a.author))
    if not a.id or not ID.match(a.id.replace("arXiv:", "")):
        sys.exit("give an arXiv id such as 1701.02434v2 or math/0308286v1, or --title")
    sys.exit(unpack(a.id.replace("arXiv:", "")))


if __name__ == "__main__":
    main()
