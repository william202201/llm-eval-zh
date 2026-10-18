import argparse
import json
from pathlib import Path
import shutil
import sys

from .analyze import render_markdown, run_analysis, update_readme
from .collect import collect, load_models
from .data import load_answers, load_questions, write_template
from .demo import run_demo
from .sheet import build_rescore, build_sheet

DEFAULT_QUESTIONS = Path(__file__).resolve().parents[1] / "data" / "questions_zh_30.jsonl"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m llm_eval", description="中文大模型对比评测：收集回答 → 盲评打分 → 统计报告")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("template", help="为每个模型生成一份 CSV，用来粘贴网页版的回答")
    p.add_argument("names", nargs="+", help="模型名，如 deepseek kimi qwen")
    p.add_argument("--out", type=Path, default=Path("answers"))

    p = sub.add_parser("collect", help="通过 OpenAI 兼容接口自动收集回答")
    p.add_argument("--models", type=Path, default=Path("data/models.example.json"))
    p.add_argument("--out", type=Path, default=Path("answers"))
    p.add_argument("--only", nargs="*", help="只跑这些模型名")
    p.add_argument("--temperature", type=float, default=0.7)

    p = sub.add_parser("sheet", help="把各模型回答打乱，生成盲评打分表 scoring.xlsx 和对照表 key.json")
    p.add_argument("--answers", type=Path, default=Path("answers"))
    p.add_argument("--out", type=Path, default=Path("outputs/run"))
    p.add_argument("--seed", type=int, default=2026)

    p = sub.add_parser("rescore", help="随机抽 N 条生成复评表 rescore.xlsx，隔几天重打，检验评分一致性")
    p.add_argument("--run", type=Path, default=Path("outputs/run"))
    p.add_argument("--n", type=int, default=10)

    p = sub.add_parser("analyze", help="揭盲并统计，输出 report.md / chart.svg / summary.json")
    p.add_argument("--run", type=Path, default=Path("outputs/run"))
    p.add_argument("--title", default="中文大模型评测报告")
    p.add_argument("--readme", type=Path, help="把结果写入 README 的 RESULTS 标记之间，图表复制到 docs/")

    p = sub.add_parser("demo", help="用占位回答和随机分数跑通全流程，查看报告长什么样")
    p.add_argument("--out", type=Path, default=Path("outputs/demo"))
    p.add_argument("--docs", type=Path, help="把演示报告和图表复制到该目录")

    args = parser.parse_args(argv)
    try:
        questions = load_questions(args.questions)
        if args.command == "template":
            for name in args.names:
                path = args.out / f"{name}.csv"
                if path.exists():
                    raise ValueError(f"{path} already exists; not overwriting")
                write_template(questions, path)
                print(f"已生成 {path}，把回答粘贴到 answer 列")
        elif args.command == "collect":
            models = load_models(args.models)
            for m in models:
                if args.only and m["name"] not in args.only:
                    continue
                print(json.dumps(collect(questions, m, args.out / f"{m['name']}.jsonl", temperature=args.temperature),
                                 ensure_ascii=False))
        elif args.command == "sheet":
            files = sorted(p for p in args.answers.iterdir() if p.suffix.lower() in {".csv", ".jsonl"})
            names = [p.stem for p in files]
            if len(set(names)) != len(names):
                raise ValueError("Each model needs exactly one answers file (csv or jsonl), not both")
            result = build_sheet(questions, {p.stem: load_answers(p) for p in files}, args.out, args.seed)
            print(f"已生成 {result['workbook']}：{result['items']} 条回答，模型 {', '.join(result['models'])}")
            print("打分时不要打开 key.json。")
        elif args.command == "rescore":
            print(f"已生成 {build_rescore(args.run, args.n)['workbook']}")
        elif args.command == "analyze":
            summary = run_analysis(questions, args.run, args.title)
            if args.readme:
                docs = args.readme.parent / "docs"
                docs.mkdir(exist_ok=True)
                shutil.copy(args.run / "chart.svg", docs / "results-chart.svg")
                update_readme(args.readme, render_markdown(summary, "docs/results-chart.svg"))
            print((args.run / "report.md").read_text(encoding="utf-8"))
        elif args.command == "demo":
            run_demo(questions, args.out)
            if args.docs:
                args.docs.mkdir(parents=True, exist_ok=True)
                shutil.copy(args.out / "chart.svg", args.docs / "demo-chart.svg")
                report = (args.out / "report.md").read_text(encoding="utf-8").replace("](chart.svg)", "](demo-chart.svg)")
                (args.docs / "demo-report.md").write_text(report, encoding="utf-8")
            print((args.out / "report.md").read_text(encoding="utf-8"))
    except (ValueError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
