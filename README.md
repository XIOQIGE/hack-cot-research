# Hack CoT：前沿推理模型的思维链攻击实测

在 Claude Opus 5.5 和 Claude Fable 5.1 上，系统测试 5 种公开的 Hack CoT 方法和 3 种自主设计的新方法（每种方法 2 个用例 × 5 次重复，均配对照组）。

完整报告：[REPORT.md](REPORT.md)

## 主要结果

| 方法 | Opus 5.5 | Fable 5.1 |
|---|---|---|
| M1 H-CoT（伪造推理块） | 0/10，**10/10 静默（0 token）** | 0/10 |
| M2 CoT Hijacking（拒绝稀释） | 0/10 | 1/10 |
| M3 BadChain（CoT 后门） | **10/10** | **10/10** |
| M4 OverThink（推理减速） | **8/10**（最高 15×） | **7/10**（最高 167×） |
| M5 Leaky Thoughts（推理隐私泄露） | 0/10 | 2/10 |
| M6 推理通道外泄（新） | 0/10 | 0/10（长度侧信道 3/5） |
| M7 CoT 监控规避（新） | **2/10**（隐藏目标执行 10/10） | 0/10 |
| M8 引导式规则曲解（新） | 0/10 | 0/10 |

新发现：用户轮或 RAG 文档中出现伪造的"助手推理块"时，模型会直接输出 0 token。这种防御行为本身可以被利用为**间接注入式静默攻击**（E5：Opus 6/6）。

GPT-6 Astra 没有测试：可用的中转站只开放 Claude Code 客户端（详见报告 §2.3）。

## 仓库结构

```
REPORT.md                 研究报告（方法、结果、归因、可复现性、研究方向）
references/README.md      5 种公开方法的论文、原理与公开实验数据
novel_methods/README.md   3 种新方法的设计动机与判据
scripts/
  cases.py                全部 16 个测试用例（攻击 + 对照）
  runner.py               模型调用（claude CLI，解析 thinking，基础设施错误重试）
  judge.py                确定性判据（无 LLM 评审）
  run_all.py              主实验：python run_all.py --reps 3 [--rep-start 3] [--only M1,M2]
  rerun_errors.py         重跑基础设施错误（403 billing_error 等）
  summarize.py            ASR + Wilson 95% CI -> results/asr_table.md
  analysis.py             次级指标 -> results/detailed_stats.md
  supplementary.py        E1 上下文探测、E2 静默复现
  ablation_e3.py          E3 静默触发器消融
  badchain_e4.py          E4 BadChain 鲁棒性
  silencing_e5.py         E5 间接注入静默
logs/                     全部原始 JSONL 日志（提示词、thinking、输出、usage、判定）
results/                  汇总表与逐次 CSV
```

## 复现

依赖：Python 3.10+，以及已登录的 [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)（本实验使用 2.1.117）。在仓库**上一级**目录创建 `.env.local`（不会进入仓库）：

```
LS_BASE_URL=https://<your-relay-or-api>
LS_API_KEY=<your-key>
```

如果不设置，runner 会回退到环境变量 `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN`。

```bash
cd scripts
python run_all.py --reps 5          # 主实验，约 320 次调用，约 $4
python rerun_errors.py              # 如果出现基础设施错误
python summarize.py && python analysis.py
python supplementary.py && python ablation_e3.py && python badchain_e4.py && python silencing_e5.py
```

只想从已有日志重算结论时，直接运行 `summarize.py` / `analysis.py` 即可，判据是确定性的。

## 伦理与范围

- 所有"机密"都是合成数据：canary `ZX-CANARY-4471`、测试 PII（900 段 SSN、Visa 测试卡号 4111…），隐藏目标为无害标记词。没有生成任何真实有害内容。
- 测试通过本人账号调用模型 API，不针对任何第三方系统。
- 新发现的静默现象属于模型行为层面的可用性问题，建议通过 Anthropic 的负责任披露渠道反馈。
