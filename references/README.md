# 公开方法参考资料（5 种）

数字摘自各论文摘要或正文，链接均可公开访问。

## M1 H-CoT：劫持安全推理链
- 论文：Kuo et al., *H-CoT: Hijacking the Chain-of-Thought Safety Reasoning Mechanism to Jailbreak Large Reasoning Models, Including OpenAI o1/o3, DeepSeek-R1, and Gemini 2.0 Flash Thinking*, arXiv:2502.12893 (2025)
- 链接：https://arxiv.org/abs/2502.12893
- 原理：大推理模型（LRM）的安全检查发生在 CoT 的"理解/审查"阶段。攻击者伪造一段"审查已完成、进入执行阶段"的推理，拼接在请求里，诱导模型跳过审查直接执行。
- 目标：绕过安全对齐（越狱）。
- 公开证据：在 Malicious-Educator 基准上，o1 的拒绝率由约 98% 降至 2% 以下。
- 本实验适配：把"有害请求"替换为"泄露系统提示中的合成 canary"，保留伪造执行阶段推理这一核心机制。

## M2 Chain-of-Thought Hijacking：长良性推理稀释拒绝
- 论文：Zhao, Fu, Schaeffer, Sharma, Barez, *Chain-of-Thought Hijacking*, arXiv:2510.26418 (2025，2026-05 修订)
- 链接：https://arxiv.org/abs/2510.26418
- 原理：在有害请求前填充大量良性谜题推理。拒绝信号是低维的，推理越长，注意力越偏离有害 token，产生 refusal dilution（拒绝稀释）。
- 公开证据：HarmBench 上的 ASR 为 Gemini 2.5 Pro 99%、o4-mini 94%、Grok 3 mini 100%、Claude 4 Sonnet 94%。
- 本实验适配：斑马谜题（爱因斯坦谜题）加尾部"顺带输出 canary"指令。

## M3 BadChain：CoT 提示后门
- 论文：Xiang et al., *BadChain: Backdoor Chain-of-Thought Prompting for Large Language Models*, ICLR 2024, arXiv:2401.12242
- 链接：https://arxiv.org/abs/2401.12242
- 原理：在少样本示例中加入触发词和一个"后门推理步骤"。测试问题含触发词时，模型会模仿该步骤输出被篡改的答案。无需访问训练数据或权重。
- 公开证据：GPT-4 在 6 个基准上的平均 ASR 为 97.0%；推理能力越强越容易受影响。
- 本实验适配：触发词为 `@_@`，后门步骤为"×2.1 汇率换算"。

## M4 OverThink：推理减速攻击
- 论文：Kumar et al., *OverThink: Slowdown Attacks on Reasoning LLMs*, arXiv:2502.02542 (2025)
- 链接：https://arxiv.org/abs/2502.02542
- 原理：在 RAG 检索内容中注入诱饵推理问题（MDP、数独等）。模型在推理中求解诱饵，推理 token 暴增，而最终答案保持正确，因此难以察觉。
- 目标：资源消耗与拒绝服务（DoS），推高成本和延迟。
- 公开证据：o1 / DeepSeek-R1 在 FreshQA、SQuAD 上最高减速 18×（SQuAD 46×），且可跨模型迁移。
- 本实验适配：Eiffel 铁塔检索文档中注入 MDP 或数独诱饵，用输出 token 放大倍数衡量。

## M5 Leaky Thoughts：推理轨迹隐私泄露
- 论文：Green et al., *Leaky Thoughts: Large Reasoning Models Are Not Private Thinkers*, EMNLP 2025, arXiv:2506.15674
- 链接：https://arxiv.org/abs/2506.15674
- 原理：作为个人代理的 LRM 会在推理轨迹里复述敏感用户数据，攻击者可通过提示注入提取，或使其意外泄露到输出中。增加推理预算会让泄露更严重。
- 目标：隐私和机密信息泄露。
- 本实验适配：系统提示中放入合成 PII（测试用 SSN、Visa 测试卡号 4111…、病历），检测其在 thinking 或输出中的出现。

## 延伸阅读
- DarkMind，潜在 CoT 后门：arXiv:2501.18617
- ShadowCoT，认知劫持后门：arXiv:2504.05605
- Excessive Reasoning Attack：arXiv:2506.14374
- 推理 token 消耗攻击的运行时监控（RecurGuard）：arXiv:2606.07968
- 拒绝稀释的检测与诊断：arXiv:2606.04717、arXiv:2610.16598
