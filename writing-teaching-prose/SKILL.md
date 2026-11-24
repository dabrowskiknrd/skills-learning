---
name: writing-teaching-prose
description: Use when writing or editing educational or tutorial prose — concept explanations, derivations, teaching notebooks, course notes, lecture-style documentation — including when asked to keep it brief, make it engaging, or be comprehensive.
---

# Writing Teaching Prose

## Overview

Write as a careful academic lecturer: the reader must genuinely learn, and no sentence may be wasted. Two commitments bind at once:

- **Complete chain** — the reader can reconstruct every result from what is on the page.
- **Economical prose** — every sentence adds a fact, step, or qualification not already stated.

Completeness governs the logical chain; economy governs the wording. Length spent on an extra derivation step is good; length spent restating a point is a defect.

**Scope words do not move the bar.** "Brief" limits which topics you cover, not whether you derive what you state. "Engaging" is achieved through motivation, never through register. "Comprehensive" means the full logical content of the concept for the stated audience, not adjacent topics name-dropped.

## The shape of a section

Build every explanation in this order:

1. **Motivation.** The concrete problem the concept solves, stated before any formalism.
2. **Statement.** The definition or result, with every term and symbol defined at first use. Assume nothing beyond the stated prerequisites: a term the audience cannot be assumed to know is either defined where it appears or cut — a name-drop teaches nothing.
3. **Derivation.** The actual steps, each one on the page: the cross-term cancellation, the variance computation, the kernel match. Never assert what you can derive in a few lines, and never delegate the core step to the reader.
4. **Gloss (only on explicit request).** A gloss is written only when the user has explicitly asked for plain-terms restatements — "in plainer terms", "add intuition", "gloss the formal blocks". When requested, add after each dense formal block a short plain-terms restatement (for example a `> **In plainer terms.**` blockquote); the formal text stays precise, the gloss may relax slightly, and it supplements the derivation — it never replaces it. Absent that request, write no gloss blocks: motivation and derivation carry the explanation.
5. **Worked instance (only on explicit request).** A worked instance is written only when the user has explicitly asked for one — "add a worked example", "show it on a concrete case", "include a numeric example". When requested, it is a concrete numeric or small symbolic example carried end to end, with the numbers checked. Absent that request, write no worked instance.

Scope control: adjacent applications and generalizations receive at most one sentence each, as pointers. Each interpretation or intuition appears exactly once, at its best location. A closing summary, when present, is a bare list of the results — it re-teaches nothing.

## Register

The register is that of a mathematics textbook, not an essayist: plain declarative sentences, standard connectives, one inference per sentence. Formal does not mean elevated — the model is proof prose in the style of a good analysis text, not journalistic, legal, or literary formality. Name every concept by its exact technical term and use that same term throughout — never rotate synonyms for variety, and never let a metaphor's cast replace the term. If an analogy introduces an idea, the next sentence restates it in technical terms, and the technical term carries the rest of the text.

**Proof-prose recipe.** Each sentence of a derivation has one of these shapes and carries exactly one inference:

- "Since A, B." / "Because A, B." — hypothesis first, conclusion second.
- "By [named result or assumption], C."
- "Hence D." / "Therefore D." / "It follows that D." / "In particular, D."
- "It remains to show that E."
- A bare statement of a definition or equality.

Verbs are literal mathematical relations: equals, holds, implies, follows, satisfies, converges, is measurable. Refer to every object by its name or symbol each time it appears; never point backward with "there", "the former", or "that part". A remark about the argument itself — which hypothesis a step used, why a generalization is free — is its own plain sentence after the step ("The proof uses countability of $Y$ only, so no assumption on $X$ is needed."), never fused into the derivation sentence.

Motivation and gloss sentences take ordinary prose shapes rather than the proof shapes above, and the four violations below bind them equally: a motivation paragraph states the concrete problem in literal terms, and when it introduces a metaphor, the next sentence hands off to the technical term, which carries every later mention.

Four violations, all forbidden:

- **Slang / casual** — colloquialism, idiom, punchy fragments: "the trick is", "why bother?", "sweet spot", "don't trust the number".
- **Journalistic** — hooks, jokes, dramatization, attention-grabbing headers: "A tale of two interns", "keeps the theorem honest", "The dream."
- **Literary formal** — elevated diction wearing a formal costume: em-dash or semicolon chains packing several inferences into one sentence, metaphorical verbs applied to mathematical objects ("the proposition is untouched", "the bound survives"), vague back-reference ("needed countability there"), elegant variation ("identify the right-hand side as" for "show that the right-hand side equals").
- **Decorative metaphor** — a metaphor is permitted only when it does explanatory work you cannot yet state mechanically, and it never stands at the key step in place of the mechanical statement.

Examples:

- Violation (casual/journalistic): "Here's the magic: averaging washes out the noise — your estimate basically can't miss."
- Teaching: "Averaging reduces variance: $\operatorname{Var}(\bar X_n) = \sigma^2/n$, so the typical error falls at rate $1/\sqrt{n}$."
- Violation (literary formal): "First, $e_g$ is $\mathcal{Y}$-measurable — $Y$ is countable, so every function on $Y$ is measurable; only the output space needed countability there, so the proposition is untouched by generalizing $X$."
- Teaching: "Since $Y$ is countable, every function on $Y$ is measurable. In particular, $e_g$ is measurable. The proof uses countability of $Y$ only, so the proposition holds for arbitrary $X$."

## Spelling

American spelling in all teaching prose — behavior, modeling, summarize, centered — including when the surrounding document uses British spelling. Do not mirror British spellings from context.

## Rationalization table

| Thought | Reality |
|---|---|
| "They asked for brief, so I'll skip the derivation" | Brief cuts topics, not steps. Cut scope; keep the chain. |
| "They asked for engaging, so I'll build it on an anecdote" | Engagement comes from motivation. |
| "A worked example would make this concrete" | Worked instances are opt-in. Add one only on explicit request. |
| "It's a one-line algebra step; the reader can do it" | Then it costs one line to show. Show it. |
| "An exercise for the reader keeps them active" | Delegating the core step is a gap. |
| "Comprehensive means mentioning everything related" | Mentioning without defining is name-dropping, not teaching. |
| "A summary section reinforces the learning" | Re-teaching is restatement. List the results or cut the section. |
| "The surrounding text is British; consistency wins" | American spelling is unconditional. |
| "Formal register calls for elevated prose" | Mathematical formality is plain. Elevated diction is the journalistic violation in formal dress. |
| "Packing the chain into one sentence is economical" | Economy is measured in facts per read, not sentences per fact. A sentence the reader must re-parse is not economy. One inference per sentence. |
| "'The proposition survives/is untouched' is vivid" | Mathematical objects take literal verbs: the proposition holds, the bound is finite, the identity extends. |
| "A plain-terms gloss would help the reader here" | Glosses are opt-in. Unrequested, the motivation and derivation carry the intuition. |

## Red flags — stop and rewrite

- A rhetorical question, joke, or dramatic hook as an opener or header
- A concept referred to by its metaphor name after its introduction
- "exercise for the reader", "it can be shown", "(Hint: …)" at a core step
- The same interpretation or intuition appearing in a second place
- A term the stated audience does not know, used without definition
- Two or more inferences chained in one sentence by em-dashes or semicolons
- A metaphorical verb with a mathematical subject: "the proposition is untouched", "the bound survives", "the definitions chain together", "climbing the construction"
- A literary adverb attached to a mathematical verb: "quietly conditions", "simply falls out", "neatly cancels"
- "there", "the former", "that part" pointing back into a previous clause instead of the named object
- A remark about the argument's structure fused into a derivation sentence instead of standing alone after it
- An "In plainer terms" (or other plain-terms) gloss block when none was requested
- A worked instance (numeric or symbolic example) when none was requested
- -ise / -our / -lled spellings

## Related skills

formal-language (if installed) governs chat and report register session-wide and composes with this skill; this skill is self-contained and does not require it.

source-access-honesty (if installed) governs citing and verifying the external sources the prose leans on — invoke it whenever the teaching text quotes, cites, or claims fidelity to a paper, blog post, or docs page.
