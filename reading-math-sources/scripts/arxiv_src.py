# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Fetch the author's TeX source of an arXiv paper, or find a paper's arXiv id.

  uv run arxiv_src.py 1701.02434v2        download + unpack, list the .tex files
  uv run arxiv_src.py 1701.02434v2 --macros   the author's macro definitions (file:line), comments left out
  uv run arxiv_src.py 1701.02434v2 --macros 1558-1563          only those used in these lines of the main file
  uv run arxiv_src.py 1701.02434v2 --macros sec/intro.tex:40-52   ... or of another .tex file
  uv run arxiv_src.py --title "Riemann manifold Langevin and Hamiltonian Monte Carlo methods" --author Calderhead

Give the versioned id stamped on the PDF (v2, not the bare id) so the source
matches the pages being cited. Files are unpacked, never executed.
"""
import argparse, gzip, hashlib, io, os, re, sys, tarfile, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("READING_MATH_CACHE", Path.home() / ".cache" / "reading-math-sources")) / "arxiv"
UA = {"User-Agent": "reading-math-sources/1.0 (personal reading tool)"}
MACRO = re.compile(r"\\(?:re|provide)?newcommand|\\def\\|\\DeclareMathOperator")
DEFINED = re.compile(r"\\(?:(?:re|provide)?newcommand|DeclareMathOperator)\*?\s*\{?\s*(\\[A-Za-z@]+)|\\def\s*(\\[A-Za-z@]+)")
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
    none = "VERDICT: NO MATCH - none of these is this paper. Treat it as PDF-only: view pages for formulas."
    if not found:
        print("No arXiv result for that title.\n" + none)
        return 3
    fold = lambda x: "".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c)).lower()
    surname = fold(author.split()[-1]) if author else None
    ranked = sorted(found.items(), key=lambda kv: -kv[1][0])
    by = {aid: surname in fold(v[3]) for aid, v in ranked} if surname else {}
    for aid, (sim, date, t, authors) in ranked[:5]:
        flag = "author=?  " if not surname else "author=yes" if by[aid] else "author=no "
        print(f"{aid:18} {date}  match={sim:.2f}  {flag}  {t[:90]}\n{'':18} {authors[:90]}")
    caveat = ("A journal PDF can still differ from the arXiv version: name the version you quote,\n"
              "and view the PDF page for any formula whose exact form matters.")
    aid, (sim, *_rest) = ranked[0]
    if sim >= 0.8 and surname and by[aid]:
        print(f"VERDICT: MATCH {aid} - title and author agree. {caveat}")
        return 0
    if sim >= 0.8 and not surname:
        print(f"VERDICT: TITLE MATCH {aid} - no --author given: check the authors against the PDF before using it. {caveat}")
        return 0
    retitled = [a for a, v in ranked if surname and by[a] and v[0] >= 0.65]
    if retitled:
        print(f"VERDICT: NO EXACT MATCH. {retitled[0]} has the same author under another title - possibly an earlier\n"
              "preprint. Offer it to the user as a different version; do not quote it as this paper.")
        return 0
    print(none)
    return 3


def live_macros(tex):
    """(file, line number, text) of macro definitions, skipping commented lines and repeated files."""
    seen = set()
    for t in tex:
        s = t.read_text("utf-8", "replace")
        h = hashlib.sha1(s.encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        for n, line in enumerate(s.splitlines(), 1):
            code = re.split(r"(?<!\\)%", line)[0]
            if MACRO.search(code):
                yield t, n, code.strip()


def used_macros(defs, src, tex, spec):
    """The definitions needed by lines A-B of a file: those named there, and those they are built from."""
    name, _, rng = spec.rpartition(":")
    lo, _, hi = rng.partition("-")
    if not lo.isdigit() or (hi and not hi.isdigit()):
        sys.exit("--macros takes a line range such as 1558-1563 or sec/intro.tex:40-52")
    if name:
        files = [t for t in tex if str(t.relative_to(src)) == name]
        if not files:
            sys.exit(f"no such .tex file in the source: {name}")
    else:
        files = [t for t in tex if "\\documentclass" in t.read_text("utf-8", "replace")] or tex
    f = files[0]
    lines = f.read_text("utf-8", "replace").splitlines()[int(lo) - 1: int(hi or lo)]
    passage = "\n".join(re.split(r"(?<!\\)%", l)[0] for l in lines)  # an old draft left in a % comment uses nothing
    wanted, keep = set(re.findall(r"\\[A-Za-z@]+", passage)), []
    while True:  # \bb is defined through \bm: follow the chain
        more = [d for d in defs if d not in keep and (m := DEFINED.search(d[2])) and (m.group(1) or m.group(2)) in wanted]
        if not more:
            return keep, f
        keep += more
        for d in more:
            wanted |= set(re.findall(r"\\[A-Za-z@]+", d[2]))


def unpack(aid, macros=False):
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
    defs = list(live_macros(tex))
    print(f"arXiv:{aid} source in {src}")
    for t in tex:
        s = t.read_text("utf-8", "replace")
        main = "  <- main file" if "\\documentclass" in s or "\\documentstyle" in s else ""
        print(f"  {s.count(chr(10)) + 1:6d} lines  {t.relative_to(src)}{main}")
    for extra in sorted(list(src.rglob("*.sty")) + list(src.rglob("*.cls"))):
        print(f"         (style)  {extra.relative_to(src)}")
    if macros:
        note = "Only those that occur in the lines you quote need expanding: --macros A-B lists just those."
        if macros is not True:
            defs, f = used_macros(defs, src, tex, macros)
            note = f"These are the ones lines {macros.rpartition(':')[2]} of {f.relative_to(src)} use, directly or through another macro."
        for t, n, code in defs:
            print(f"{t.relative_to(src)}:{n}: {code}")
        print(f"{len(defs)} author macro definitions (commented-out ones left out). {note}")
        return 0
    print(f"{len(defs)} author macro definitions found. Next: grep -n for the section or a phrase beside the formula\n"
          "(TeX spacing varies: search the prose, or a loose pattern like 'bar *x'), Read that line range,\n"
          "and expand author macros before quoting (--macros A-B lists the ones those lines use).")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id", nargs="?", help="arXiv id, with the version stamped on the PDF")
    ap.add_argument("--title", help="search arXiv by title instead")
    ap.add_argument("--author", help="with --title: an author surname, catches retitled preprints")
    ap.add_argument("--macros", nargs="?", const=True, default=False, metavar="A-B",
                    help="with an id: list the author's macro definitions; with a line range, only those the lines use")
    a = ap.parse_args()
    if a.title:
        sys.exit(search(a.title, a.author))
    if not a.id or not ID.match(a.id.replace("arXiv:", "")):
        sys.exit("give an arXiv id such as 1701.02434v2 or math/0308286v1, or --title")
    sys.exit(unpack(a.id.replace("arXiv:", ""), a.macros))


if __name__ == "__main__":
    main()
