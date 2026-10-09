---
name: daily-quiz
description: Write, verify and publish daily challenge questions for the Sambidhan app. Use when asked to create daily challenge or quiz questions for a month or date range, e.g. "/daily-quiz 2026-11" or "/daily-quiz 2026-10-01 2026-10-31".
---

# Daily challenge questions

Arguments: a month (`YYYY-MM`) or a start and end date (`YYYY-MM-DD`,
inclusive). If missing, ask. Each day has exactly 5 questions.

The app loads `quiz/quiz_YYYY_MM` from this repo's `main` branch on GitHub.
Nothing reaches users until it is merged and pushed to `main`.

Draft name `<name>`: the month (`2026-11`) or `<start>_<end>`. Files:
- parts: `drafts/<name>.partN.json` (+ `.blind.json`, `.reviewer.json`)
- merged: `drafts/<name>.json` and the review list `drafts/<name>.review.md`

## 1. Plan the parts

Split the range into parts of about 10 days (a 30-day month: 3 parts).

The daily challenge is an easy daily habit: 3 easy + 2 medium questions a
day, themed by weekday (table in `.claude/agents/quiz-writer.md`, checked by
the validator). Aim for an average score of about 4 out of 5.

Build an article pool for each theme, choosing articles for how useful and
well known their facts are, not for being unused. Good sources:
- nepal-basics: P, 1-9, S1-S4
- fundamental-rights: 16-48
- president-government: 61-82
- parliament-elections: 83-89, 91-92
- courts-commissions: 126-129, 238-265
- provinces-local: 56-58, 162-176, 214-222
- weekly-review: facts from that week's other themes

Skip articles with little testable content ("shall be as provided by law")
and heavy procedure (sessions, quorum, bill passage, budget steps).
`python3 scripts/quiz.py coverage` shows how often each article is used;
prefer less-used ones among the useful ones, but well-known facts may be
asked again in new wording.

Split each theme's pool between the parts, so parts do not share articles.
Every part needs articles for every theme, because it covers every weekday.

## 2. Write, in parallel

Start one `quiz-writer` agent per part, all in the same message, each with
its date range, article keys and output path `drafts/<name>.partN.json`.

When they finish, run `python3 scripts/quiz.py validate` on each part and
fix anything still failing.

## 3. Blind review, in parallel

For each part: `python3 scripts/quiz.py blind drafts/<name>.partN.json`.
Then start one `quiz-reviewer` agent per part, all in the same message, each
given only "Review drafts/<name>.partN.blind.json". Never pass the draft or
the answers.

Then, for each part:

```bash
python3 scripts/quiz.py compare drafts/<name>.partN.json drafts/<name>.partN.reviewer.json
```

## 4. Fix or drop

For each flagged question, read the article yourself and decide:
- the reviewer is right: fix the question, or replace it with a new one
- the draft is right: note why for the user
- rated hard: make it easier (a better-known fact, or clearly different
  options), or replace it

Re-validate. Put fixed or new questions through one more blind review (a
small draft with just those days is fine). A question that fails twice is
replaced, not argued.

## 5. Merge and human review

```bash
python3 scripts/quiz.py merge drafts/<name>.json drafts/<name>.part*.json
python3 scripts/quiz.py validate drafts/<name>.json
python3 scripts/quiz.py sheet drafts/<name>.json
```

Validate on the merged draft catches repeats across parts. Give the user
`drafts/<name>.review.md` and a short summary: questions written, flagged by
the reviewer, fixed, replaced, and the reviewer's easy/medium split. Stop and wait for approval. Apply any
corrections the user asks for in `drafts/<name>.json`, then validate again.

## 6. Publish (only after the user approves)

```bash
python3 scripts/quiz.py publish drafts/<name>.json
```

Commit only the updated `quiz/quiz_YYYY_MM` file(s). Drafts are local
working files: `drafts/` is in `.gitignore`, never commit them. Push
only when the user asks.
