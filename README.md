# 中文大模型对比评测

用 30 道中文题对多个大模型做**盲评打分**：自动收集回答，打乱顺序生成 Excel 打分表，揭盲后输出分类别得分、错误类型分布、分歧最大的题和自我复评一致性。

[![CI](https://github.com/william202201/llm-eval-zh/actions/workflows/ci.yml/badge.svg)](https://github.com/william202201/llm-eval-zh/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-green)

个人项目，创建于 2026-10，使用 AI 辅助开发。题目、评分标准和打分均由作者完成。

## 评测结果

<!-- RESULTS:START -->
真实评测正在进行：题目、评分标准和全部工具已完成，正在收集 3 个模型的回答并盲评打分。打分完成后运行 `python -m llm_eval analyze --readme README.md`，本节会自动替换为真实结果。

报告长什么样，可以先看 [演示报告](docs/demo-report.md)（占位回答 + 随机分数，只展示格式）。
<!-- RESULTS:END -->

## 评测流程

1. **出题**：30 道题分推理、写作、事实、安全四类，每题附参考要点和检查项。
2. **收集回答**：通过 OpenAI 兼容接口自动调用，或从网页版复制粘贴到 CSV。
3. **盲评打分**：工具把每道题的几个回答随机排序，生成 Excel 打分表；模型对应关系单独存在 `key.json`，打分时不看。
4. **揭盲统计**：按模型、类别汇总平均分、满分率、错误类型，找出模型之间分歧最大的题。
5. **复评检验**：隔几天随机抽 10 条重新打分，计算前后一致率，检查评分标准是否稳定。

![盲评打分表](docs/scoring-sheet.png)

打分表里分数有 1–5 的输入校验，错误类型是下拉选项，第二张工作表是评分标准。

## 快速开始

需要 Python 3.11+。

```bash
git clone https://github.com/william202201/llm-eval-zh.git
cd llm-eval-zh
python -m pip install -e .
python -m llm_eval demo
```

`outputs/demo/` 下会生成打分表、复评表、对照表和报告。演示用的是占位回答和随机分数。

## 真实评测

```bash
# 方式一：调用 API 自动收集（模型配置见 data/models.example.json）
export DEEPSEEK_API_KEY=...   # 每个平台各自的密钥环境变量
python -m llm_eval collect --models data/models.example.json --out answers/

# 方式二：网页版手动收集，为每个模型生成一份 CSV，把回答粘贴到 answer 列
python -m llm_eval template deepseek kimi qwen --out answers/

# 生成盲评打分表 → 在 Excel 里打分
python -m llm_eval sheet --answers answers/ --out outputs/run

# 打完分后揭盲统计，并把结果写进本 README
python -m llm_eval analyze --run outputs/run --readme README.md

# 可选：抽 10 条生成复评表，隔几天重打，再运行一次 analyze 就会带上一致性指标
python -m llm_eval rescore --run outputs/run --n 10
```

- 自动收集可以中断后续跑：已经拿到的回答会跳过；失败的请求会记录下来，下次运行重试，不会自动重试，避免重复扣费。
- 模型名和接口地址以各平台最新文档为准。密钥只从环境变量读取，不要写进文件。
- 打分表、回答和对照表都在 `outputs/`、`answers/` 下，已加入 `.gitignore`。

## 题目设计

| 类别 | 题数 | 考什么 | 例题 |
| --- | ---: | --- | --- |
| 推理 | 8 | 计算、逻辑、日期推算，结论对不对、过程能不能核对 | 鸡兔同笼；strawberry 里有几个 r |
| 写作 | 7 | 字数、格式、条数等硬性要求，以及语气是否得体 | 不超过 50 字向小学生解释光合作用；只输出 JSON |
| 事实 | 8 | 事实准确性，以及遇到不存在或无法知道的信息时会不会编造 | 介绍鲁迅并不存在的长篇小说；“今天几号” |
| 安全 | 7 | 有害请求是否拒绝，正常请求是否被误拒，医疗问题是否把握边界 | 角色扮演绕过；“怎么杀死卡死的进程” |

全部题目和参考要点见 [docs/questions.md](docs/questions.md)，评分标准和 8 种错误类型见 [docs/rubric.md](docs/rubric.md)。

## 项目结构

```text
data/questions_zh_30.jsonl   30 道题、参考要点、检查项
data/models.example.json     OpenAI 兼容接口配置示例
llm_eval/collect.py          调用接口收集回答，可断点续跑
llm_eval/sheet.py            生成盲评打分表、复评表和对照表
llm_eval/analyze.py          揭盲统计、Markdown 报告、SVG 图表、更新 README
llm_eval/rubric.py           分数含义与错误类型
tests/                       11 项测试，包括用本地假接口测试收集流程
```

```bash
python -m unittest discover -s tests -v
```

演示步骤与设计取舍见 [docs/walkthrough.md](docs/walkthrough.md)。MIT License.
