"""Collect answers from any OpenAI-compatible chat completions endpoint (DeepSeek, Kimi, Qwen, OpenAI ...)."""
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

REQUIRED_MODEL_KEYS = ("name", "base_url", "model", "api_key_env")


def load_models(path: Path) -> list[dict]:
    models = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(models, list) or not models:
        raise ValueError("models file must be a non-empty JSON array")
    names = set()
    for m in models:
        missing = [k for k in REQUIRED_MODEL_KEYS if not m.get(k)]
        if missing:
            raise ValueError(f"model entry missing {missing}: {m}")
        if m["name"] in names or "/" in m["name"]:
            raise ValueError(f"model names must be unique and contain no '/': {m['name']}")
        names.add(m["name"])
    return models


def chat(model: dict, prompt: str, timeout: float = 120, temperature: float = 0.7) -> dict:
    key = os.environ.get(model["api_key_env"])
    if not key:
        raise RuntimeError(f"environment variable {model['api_key_env']} is not set")
    body = json.dumps({"model": model["model"], "temperature": temperature,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    request = urllib.request.Request(model["base_url"].rstrip("/") + "/chat/completions", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {"answer": data["choices"][0]["message"]["content"].strip(),
            "latency_ms": round((time.perf_counter() - start) * 1000), "usage": data.get("usage", {})}


def collect(questions: list[dict], model: dict, out: Path, timeout: float = 120, temperature: float = 0.7) -> dict:
    """Append one JSON line per question. Already-answered ids are skipped, so an interrupted run can resume.

    Failures are recorded and retried on the next run; there is no automatic retry, to avoid duplicate charges.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("answer") and not row.get("error"):
                    done.add(row["id"])
    stats = {"model": model["name"], "skipped": len(done), "ok": 0, "failed": 0}
    with out.open("a", encoding="utf-8") as handle:
        for q in questions:
            if q["id"] in done:
                continue
            row = {"id": q["id"], "model": model["name"]}
            try:
                row.update(chat(model, q["prompt"], timeout, temperature))
                stats["ok"] += 1
            except (urllib.error.URLError, TimeoutError, KeyError, ValueError, RuntimeError) as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
                stats["failed"] += 1
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
    return stats
