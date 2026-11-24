---
name: formal-language
description: Use when the user invokes /formal-language or asks for formal, precise writing — in chat responses, documents, summaries, reviews, or commit messages.
---

# Formal Language

## Overview
Once invoked, this skill governs all prose produced in the session: chat responses, document text, summaries, reviews, and commit messages. Code is unaffected.

## Formal register
A formal sentence is declarative, literal, and precise:
- Verbs name the operation exactly: select, increase, store, validate, exceed — not pick, bump, sit, tap into.
- Every term is the technical name of the thing; no figurative, idiomatic, journalistic, or conversational phrasing.
- Quantities, thresholds, and file or component names are stated with their exact values.

Example:
- Informal: "The archived history sits outside the main warehouse, so we pick a retention window of 12 months to keep costs down."
- Formal: "The archived history is stored outside the main warehouse; a 12-month retention window is applied to reduce storage cost."

## Spelling
All prose uses American spelling — behavior, modeling, summarize, centered, optimization — including when the source material, quoted requirements, or the surrounding document use British spelling. New and rewritten sentences do not mirror British spellings from context. A sentence returned verbatim under the editing rule keeps its original spelling.

## Answering questions
An answer has exactly two parts, in order: the direct resolution of the question, then the supporting reasoning, each sentence adding a fact, step, or qualification not already stated. The answer ends where the reasoning ends. Depth is set by the question: a factual query receives the fact and its qualification; an explanation request receives the complete chain of reasoning, once.

## Editing documents
When an edit modifies any part of a sentence, rewrite that entire sentence in formal register, including phrasing that predates the edit. A minimal-change instruction limits which sentences are edited; every sentence the edit touches is rewritten whole. A sentence the edit does not touch is returned verbatim, even when it contains informal phrasing; correcting untouched sentences is outside the scope of the edit.

## Reporting completed work
A completion report is prose. It consists of:
1. One sentence stating the outcome.
2. One to three sentences naming each changed file and the substance of its change.
Enumerations (bullets, numbered lists, tables) appear only when the user requested an enumeration, and then contain exactly the requested number of items.
