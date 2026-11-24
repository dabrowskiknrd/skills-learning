# Skills

A personal collection of agentic skills — instructions and reference files that extend AI coding agents (e.g. Claude Code) with custom workflows and domain knowledge.

Created for my own use and learning; not intended as a general-purpose library.

## Contents

Each skill lives in its own folder with a `SKILL.md` describing when and how the agent should use it, plus any supporting text/JSON reference files.

| Skill | Use it when |
| --- | --- |
| [`formal-language`](formal-language/SKILL.md) | Formal, precise writing is wanted — chat responses, documents, reviews, commit messages. |
| [`source-access-honesty`](source-access-honesty/SKILL.md) | Citing, quoting, or verifying an external source, without overstating what was actually read. |
| [`writing-teaching-prose`](writing-teaching-prose/SKILL.md) | Writing or editing educational prose — explanations, derivations, tutorials, course notes. |

## Usage

Copy or symlink a skill folder into `~/.claude/skills/` (global) or a project's `.claude/skills/` directory; Claude Code picks it up on the next session.
