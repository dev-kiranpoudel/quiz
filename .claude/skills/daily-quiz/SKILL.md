---
name: daily-quiz
description: Write, verify and publish daily challenge questions for the Sambidhan app. Use when asked to create daily challenge or quiz questions for a date range, e.g. "/daily-quiz 2026-10-01 2026-10-08".
---

# Daily challenge questions

Arguments: start date and end date (inclusive), `YYYY-MM-DD`. If missing, ask.
Each day has exactly 5 questions. Work in batches of at most 10 days.

The app loads `quiz/quiz_YYYY_MM` from this repo's `main` branch on GitHub.
Nothing reaches users until it is merged and pushed to `main`.

## 1. Write the draft

Draft name: `<start>_<end>`, file `drafts/<start>_<end>.json`. The format is
in the docstring of `scripts/quiz.py`.

- Base every question on the article text from
  `python3 scripts/quiz.py article <keys>`, never on memory. The Nepali text
  is official; the English translation has errors.
- `source.quoteNe` must be copied exactly from the Nepali text (the validator
  checks this). `quoteEn` is the matching English sentence.
- Prefer articles not yet asked about. Spread topics across the constitution;
  no more than 2 questions from the same article per day.
- Mix difficulty in each day: 2 easy, 2 medium, 1 harder.
- Wrong options must be plausible (real numbers, bodies and terms from the
  constitution) but clearly wrong by the text. Avoid "all of the above",
  "none of the above", and negative questions ("which is NOT").
- Put the correct answer at any index; the app shuffles options.
- Write natural Nepali using the constitution's own terms (धारा, उपधारा,
  प्रतिनिधि सभा, राष्ट्रिय सभा, मन्त्रिपरिषद्). Use Nepali digits in Nepali text.

## 2. Validate (no AI)

```bash
python3 scripts/quiz.py validate drafts/<name>.json
```

Fix every failure and re-run until it passes.

## 3. Blind review

```bash
python3 scripts/quiz.py blind drafts/<name>.json
```

Then run the `quiz-reviewer` agent with only the blind file path:
"Review drafts/<name>.blind.json". Do not pass the draft or the answers.

```bash
python3 scripts/quiz.py compare drafts/<name>.json drafts/<name>.reviewer.json
```

## 4. Fix or drop

For each flagged question, re-read the article and decide:
- the reviewer is right: fix the question, or replace it with a new one
- the draft is right: note why in your summary for the user

Fixed or new questions go through validate and one more blind review (only
the changed ones may be reviewed; delete the old `.blind.json` and
`.reviewer.json` first). A question that fails twice is replaced, not argued.

## 5. Human review

```bash
python3 scripts/quiz.py sheet drafts/<name>.json
```

Give the user `drafts/<name>.review.md` and a short summary: how many
questions, how many the reviewer flagged, what changed. Stop and wait for
approval. Apply any corrections the user asks for, then validate again.

## 6. Publish (only after the user approves)

```bash
python3 scripts/quiz.py publish drafts/<name>.json
```

Commit the updated `quiz/quiz_YYYY_MM` file(s) and the draft files. Push only
when the user asks.
