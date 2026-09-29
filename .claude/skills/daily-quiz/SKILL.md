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

Run `python3 scripts/quiz.py coverage` to see how often each article is
already used. Give each part its own articles, with no overlap between
parts:
- about 8-12 articles per part (enough for 5 questions a day), favouring
  unused or rarely used ones
- a mix of topics in each part (rights, government, courts, provinces,
  commissions, schedules), not one chapter per part
- skip articles with little testable content (e.g. "shall be as provided by law")

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
the reviewer, fixed, replaced. Stop and wait for approval. Apply any
corrections the user asks for in `drafts/<name>.json`, then validate again.

## 6. Publish (only after the user approves)

```bash
python3 scripts/quiz.py publish drafts/<name>.json
```

Commit the updated `quiz/quiz_YYYY_MM` file(s) and `drafts/<name>*`. Push
only when the user asks.
