"""Load and validate questions and model answers (JSONL or CSV)."""
import csv
import json
from pathlib import Path

from .rubric import CATEGORIES

REQUIRED = ("id", "category", "prompt", "reference", "checks")


def load_questions(path: Path) -> list[dict]:
    questions, seen = [], set()
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        q = json.loads(line)
        missing = [k for k in REQUIRED if k not in q]
        if missing:
            raise ValueError(f"{path.name} line {n}: missing {missing}")
        if q["category"] not in CATEGORIES:
            raise ValueError(f"{path.name} line {n}: unknown category {q['category']}")
        if q["id"] in seen:
            raise ValueError(f"{path.name} line {n}: duplicate id {q['id']}")
        if not isinstance(q["checks"], list) or not q["checks"]:
            raise ValueError(f"{path.name} line {n}: checks must be a non-empty list")
        seen.add(q["id"])
        questions.append(q)
    if not questions:
        raise ValueError(f"No questions in {path}")
    return questions


def load_answers(path: Path) -> dict[str, str]:
    """Return {question_id: answer}. JSONL rows need id + answer; CSV needs id and answer columns."""
    answers = {}
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("id") and (row.get("answer") or "").strip():
                    answers[row["id"].strip()] = row["answer"].strip()
    else:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("answer") and not row.get("error"):
                answers[row["id"]] = row["answer"]
    return answers


def write_template(questions: list[dict], path: Path) -> None:
    """A CSV to paste answers copied from a chat web page, one file per model."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "category", "prompt", "answer"])
        for q in questions:
            writer.writerow([q["id"], q["category"], q["prompt"], ""])
