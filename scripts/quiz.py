#!/usr/bin/env python3
"""Daily challenge question tooling.

Workflow (see .claude/skills/daily-quiz/SKILL.md):
  article   print the official text of articles, to write and review from
  validate  mechanical checks on a draft (no AI)
  blind     make a copy of a draft without answers, options shuffled
  compare   check the reviewer's blind answers against the draft's key
  sheet     write the human review list (markdown)
  publish   merge an approved draft into quiz/quiz_YYYY_MM

A draft lives in drafts/<name>.json:
{
  "days": [
    {"date": "2026-09-30", "questions": [
      {"questionEn": "...", "questionNe": "...",
       "options": [{"textEn": "...", "textNe": "..."}, x4],
       "correctAnswerIndex": 0,
       "source": {"article": "76", "clause": "9",
                  "quoteNe": "exact sentence from the Nepali text",
                  "quoteEn": "matching English sentence"}}
    ]}
  ]
}
Article is a number as a string, "P" for the Preamble, or "S1".."S9" for
Schedules. Ids and titles are assigned at publish time.
"""
import argparse
import datetime
import glob
import json
import os
import random
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSTITUTION = os.path.join(ROOT, "constitution", "constitution.json")
QUIZ_DIR = os.path.join(ROOT, "quiz")
QUESTIONS_PER_DAY = 5
START_DATE = datetime.date(2026, 3, 1)  # DailyChallengeUtils.startDate in the app

NE_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


# ---------------------------------------------------------------- helpers

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    # Matches the existing monthly files: 2-space indent, no trailing newline.
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))


def norm(text):
    text = unicodedata.normalize("NFC", text or "").lower()
    return re.sub(r"[\W_]+", " ", text).strip()


def articles():
    """Map article key -> {titleNe, titleEn, textNe, textEn}."""
    data = load_json(CONSTITUTION)
    out = {}
    for part in data["detailList"]:
        for a in part["list"]:
            if part["id"] == 0:
                key = "P"
            elif part["id"] >= 1001:
                key = f"S{part['id'] - 1000}"
            else:
                m = re.match(r"\s*([0-9]+)", a.get("title", "").translate(NE_DIGITS))
                if not m:
                    continue
                key = m.group(1)
            entry = out.setdefault(key, {"titleNe": a.get("title", ""),
                                         "titleEn": a.get("englishTitle", ""),
                                         "textNe": "", "textEn": ""})
            entry["textNe"] += a.get("description", "")
            entry["textEn"] += a.get("englishDescription", "")
    return out


def monthly_files():
    return sorted(p for p in glob.glob(os.path.join(QUIZ_DIR, "quiz_*"))
                  if re.search(r"quiz_\d{4}_\d{2}$", p))


def existing_questions():
    """All published questions: (normalized English text, date)."""
    seen = {}
    for path in monthly_files():
        for date, day in load_json(path).items():
            for q in day["questions"]:
                seen[norm(q["questionEn"])] = date
    return seen


def challenge_number(date_str):
    date = datetime.date.fromisoformat(date_str)
    return (date - START_DATE).days + 1


# --------------------------------------------------------------- commands

def cmd_article(args):
    table = articles()
    for key in args.keys:
        a = table.get(key)
        if not a:
            print(f"== {key}: not found\n")
            continue
        print(f"== Article {key}")
        print(f"-- Nepali (official): {a['titleNe']}\n{a['textNe'].strip()}")
        if not args.ne_only:
            print(f"-- English (translation, may contain errors): {a['titleEn']}\n{a['textEn'].strip()}")
        print()


def validate(draft):
    errors = []
    table = articles()
    published = existing_questions()
    published_dates = {d for p in monthly_files() for d in load_json(p)}
    seen_in_draft = {}
    days = draft.get("days", [])
    if not days:
        errors.append("draft has no days")
    prev = None
    for day in days:
        date = day.get("date", "")
        where = date or "?"
        try:
            parsed = datetime.date.fromisoformat(date)
        except ValueError:
            errors.append(f"{where}: bad date")
            continue
        if prev and parsed != prev + datetime.timedelta(days=1):
            errors.append(f"{where}: dates must be consecutive (previous {prev})")
        prev = parsed
        if date in published_dates:
            errors.append(f"{where}: date already published")
        qs = day.get("questions", [])
        if len(qs) != QUESTIONS_PER_DAY:
            errors.append(f"{where}: {len(qs)} questions, expected {QUESTIONS_PER_DAY}")
        for i, q in enumerate(qs, 1):
            at = f"{where} Q{i}"
            for field in ("questionEn", "questionNe"):
                if not str(q.get(field, "")).strip():
                    errors.append(f"{at}: missing {field}")
            if q.get("questionNe") and not DEVANAGARI.search(q["questionNe"]):
                errors.append(f"{at}: questionNe is not Nepali")
            opts = q.get("options", [])
            if len(opts) != 4:
                errors.append(f"{at}: {len(opts)} options, expected 4")
            for o in opts:
                if not str(o.get("textEn", "")).strip() or not str(o.get("textNe", "")).strip():
                    errors.append(f"{at}: option missing English or Nepali text")
            if len({norm(o.get("textEn")) for o in opts}) != len(opts):
                errors.append(f"{at}: duplicate English options")
            if len({norm(o.get("textNe")) for o in opts}) != len(opts):
                errors.append(f"{at}: duplicate Nepali options")
            idx = q.get("correctAnswerIndex")
            if not isinstance(idx, int) or not 0 <= idx < len(opts):
                errors.append(f"{at}: correctAnswerIndex out of range")
            key = norm(q.get("questionEn"))
            if key in published:
                errors.append(f"{at}: same question already published on {published[key]}")
            if key in seen_in_draft:
                errors.append(f"{at}: same question as {seen_in_draft[key]}")
            seen_in_draft[key] = at
            src = q.get("source") or {}
            art = str(src.get("article", ""))
            if art not in table:
                errors.append(f"{at}: source article '{art}' not found")
            elif not src.get("quoteNe"):
                errors.append(f"{at}: missing source quoteNe")
            elif norm(src["quoteNe"]) not in norm(table[art]["textNe"]):
                errors.append(f"{at}: quoteNe is not an exact quote from article {art}")
    return errors


def cmd_validate(args):
    errors = validate(load_json(args.draft))
    for e in errors:
        print("FAIL", e)
    print(f"{len(errors)} problem(s)" if errors else "OK: all checks passed")
    sys.exit(1 if errors else 0)


def blind_path(draft_path):
    return draft_path.replace(".json", ".blind.json")


def cmd_blind(args):
    draft = load_json(args.draft)
    rng = random.Random(args.draft)
    items = []
    for day in draft["days"]:
        for i, q in enumerate(day["questions"], 1):
            opts = [o["textEn"] for o in q["options"]]
            order = list(range(len(opts)))
            rng.shuffle(order)
            items.append({
                "ref": f"{day['date']}#{i}",
                "article": q["source"]["article"],
                "questionEn": q["questionEn"],
                "questionNe": q["questionNe"],
                "options": {"ABCD"[n]: {"textEn": q["options"][k]["textEn"],
                                        "textNe": q["options"][k]["textNe"]}
                            for n, k in enumerate(order)},
            })
    out = blind_path(args.draft)
    write_json(out, {"questions": items})
    print(f"wrote {out} ({len(items)} questions)")


def cmd_compare(args):
    draft = load_json(args.draft)
    blind = {q["ref"]: q for q in load_json(blind_path(args.draft))["questions"]}
    review = {r["ref"]: r for r in load_json(args.review)["results"]}
    flagged = 0
    for day in draft["days"]:
        for i, q in enumerate(day["questions"], 1):
            ref = f"{day['date']}#{i}"
            r = review.get(ref)
            if not r:
                print(f"FLAG {ref}: not reviewed")
                flagged += 1
                continue
            key_text = q["options"][q["correctAnswerIndex"]]["textEn"]
            letter = r.get("answer")
            chosen = blind[ref]["options"].get(letter, {}).get("textEn")
            problems = []
            if chosen != key_text:
                problems.append(f"reviewer chose {letter} '{chosen}', key is '{key_text}'")
            if r.get("verdict") != "pass":
                problems.append(f"verdict {r.get('verdict')}")
            problems += r.get("issues", [])
            if problems:
                flagged += 1
                print(f"FLAG {ref}: " + " | ".join(problems))
    total = sum(len(d["questions"]) for d in draft["days"])
    print(f"{total - flagged}/{total} passed, {flagged} flagged")
    sys.exit(1 if flagged else 0)


def cmd_sheet(args):
    draft = load_json(args.draft)
    lines = [f"# Review: {os.path.basename(args.draft)}", "",
             "Check each answer against the quoted text. The Nepali text is official.", ""]
    for day in draft["days"]:
        lines.append(f"## {day['date']}  (Challenge #{challenge_number(day['date'])})")
        lines.append("")
        for i, q in enumerate(day["questions"], 1):
            src = q["source"]
            clause = f"({src['clause']})" if src.get("clause") else ""
            lines.append(f"**Q{i}. {q['questionEn']}**  ")
            lines.append(f"{q['questionNe']}")
            lines.append("")
            for n, o in enumerate(q["options"]):
                mark = "✅" if n == q["correctAnswerIndex"] else "▫️"
                lines.append(f"- {mark} {o['textEn']} / {o['textNe']}")
            lines.append("")
            lines.append(f"> Article {src['article']}{clause}: {src.get('quoteNe', '')}  ")
            if src.get("quoteEn"):
                lines.append(f"> {src['quoteEn']}")
            lines.append("")
    out = args.draft.replace(".json", ".review.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


def cmd_publish(args):
    draft = load_json(args.draft)
    errors = validate(draft)
    if errors:
        for e in errors:
            print("FAIL", e)
        sys.exit("not published: fix the draft first")
    next_id = 1 + max((q["id"] for p in monthly_files()
                       for day in load_json(p).values() for q in day["questions"]),
                      default=0)
    by_month = {}
    for day in draft["days"]:
        date = day["date"]
        questions = []
        for q in day["questions"]:
            questions.append({
                "id": next_id,
                "questionEn": q["questionEn"],
                "questionNe": q["questionNe"],
                "options": [{"textEn": o["textEn"], "textNe": o["textNe"]} for o in q["options"]],
                "correctAnswerIndex": q["correctAnswerIndex"],
            })
            next_id += 1
        by_month.setdefault(date[:7], {})[date] = {
            "id": date,
            "title": f"Challenge #{challenge_number(date)}",
            "questionsCount": str(len(questions)),
            "duration": str(len(questions)),
            "questions": questions,
        }
    for month, days in sorted(by_month.items()):
        path = os.path.join(QUIZ_DIR, "quiz_" + month.replace("-", "_"))
        current = load_json(path) if os.path.exists(path) else {}
        current.update(days)
        write_json(path, dict(sorted(current.items())))
        print(f"updated {os.path.relpath(path, ROOT)}: +{len(days)} day(s)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("article", help="print article text")
    a.add_argument("keys", nargs="+", help="article numbers, P, or S1..S9")
    a.add_argument("--ne-only", action="store_true")
    a.set_defaults(func=cmd_article)
    for name, func in (("validate", cmd_validate), ("blind", cmd_blind),
                       ("sheet", cmd_sheet), ("publish", cmd_publish)):
        s = sub.add_parser(name)
        s.add_argument("draft")
        s.set_defaults(func=func)
    c = sub.add_parser("compare")
    c.add_argument("draft")
    c.add_argument("review", help="reviewer output JSON")
    c.set_defaults(func=cmd_compare)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
