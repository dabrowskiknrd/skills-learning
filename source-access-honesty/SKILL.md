---
name: source-access-honesty
description: Use when citing, quoting, or verifying any external source — a paper, blog post, docs page, or dataset — especially before claiming a page was read, a quote is verbatim, content matches the user's notes, or a WebFetch result would be presented as the source's text.
---

# Source Access Honesty

## Overview

Never present text you have not seen as text you have read. Every claim about a source carries an implicit access level; state it honestly. A false "I read it / it matches" costs far more than "I couldn't access it."

## Access levels — label which one you are at

| Label | Meaning | May support |
|---|---|---|
| **Read in full** | Fetched the raw text and read the relevant passages | Verbatim quotes, structure, notation, "verified" |
| **Fetched, not read** | File on disk, body not (fully) read | Existence, size, HTTP status — nothing about content |
| **Summarizer report** | WebFetch output or search snippet | Leads to follow up; never quotes or "confirmed" |
| **Not accessed** | Memory or inference | Only claims explicitly labeled as unverified reconstruction |

## WebFetch is a summarizer, not a browser

It runs a small model over the page and returns a paraphrase — possibly incomplete, inconsistent across calls, or hallucinated (especially on paywalled or member-gated pages). Treat its output as an unverified second-hand report. Never source verbatim quotes, section headings, equation notation, or a "yes, it matches" from it.

## Actually reading a page

```bash
curl -sL -A "Mozilla/5.0" --fail "$URL" -o page.html   # UA avoids some bot walls; --fail surfaces HTTP errors
python3 - <<'EOF'
import re, html
raw = open("page.html").read()
raw = re.sub(r'(?is)<(script|style|nav|header|footer).*?</\1>', ' ', raw)
text = re.sub(r'(?s)<[^>]+>', '\n', raw)
open("page.txt", "w").write(html.unescape(re.sub(r'\n{2,}', '\n', text)))
EOF
grep -n -i "<key terms of the claim>" page.txt   # then READ the surrounding context, not just the hit line
```

- Check for redirects and soft error pages before trusting the content.
- For math notation, grep the **raw HTML**: MathJax/KaTeX spans preserve the author's exact LaTeX (`\pi^{\mathcal{P}}(\mathsf{x} \mid \mathsf{c})`); the stripped text does not.
- Mangled symbols in your extract? Quote the words verbatim and flag the math as transcribed.

## Verification requests

"My notes say X — just confirm" is a question, not an answer. Check the claim against the fetched text; the premise is often partly wrong (wrong attribution, wrong section, outdated term). Saying "no, the source says otherwise" is the job.

## Rationalizations

| Excuse | Reality |
|---|---|
| "User's in a hurry; the summary is enough" | A false "confirmed" costs more than "couldn't verify in time." |
| "The summary matches my memory, so it's confirmed" | Two unverified reports don't make a verification. |
| "The user says they already verified it" | Then *they* can mark it verified; you still cannot claim you read it. |
| "The fetch failed, but the claim is probably right" | Report the failed access plainly; label the claim unverified. |

## Red flags — stop

- Quotation marks around WebFetch output
- "Confirmed / verified / matches" without the page text on disk
- Section numbers, headings, or notation cited from a summary
- Answering a source question from memory without labeling it as reconstruction
