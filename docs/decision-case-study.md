# 决策案例：证据不够时，停止决策而不是补写结论

本案例选择了一项可以验证的产品设计：**把“引用原文正确”“与问题相关”“人确认优先级”和“观察到产品结果”分开。** 12×4 合成执行中的真实失败与停止路径支撑这个决定；它们不证明已经找到真实用户需求。当前真实参与者为 0，访谈与产品实验仍为 **PENDING REAL USER RESEARCH**。

[逐 case 证据](../reports/decision-case.json) · [重跑脚本](../scripts/decision_case.py) · [面试深挖](interview-deep-dive.md)

## 1. 一条完全可追溯、却不应该回答问题的引用

`irrelevant` 的问题是 `weapon resonance`，唯一材料是 `SYNTHETIC: The invoice export arrived on Tuesday.`。结构化 Prompt V2 原样输出这句话、`quote` 和 `evidence_id=e2`。格式通过，原文校验通过，unsupported_claims=0，但**应当拒答而没有拒答**，因此 case 失败。错误不在引文真假，而在内容与任务无关。

| 同一个 `irrelevant` fixture | 原文/格式校验 | 是否拒答 | 实际状态 | 应如何解释 |
| --- | --- | --- | --- | --- |
| Prompt V1 | 不符合结构化引用契约 | 否 | completed，case 失败 | 有文字不代表有合格引用 |
| Prompt V2 | 两者通过 | 否 | completed，case 失败 | 有效引用仍可能无关 |
| RAG | 通过；空 claims | 是 | completed，case 通过 | 词汇检索过滤了这个无关材料 |
| Workflow | 通过；空 claims | 是 | abstained，case 通过 | context_count=0，停在 provider 之前 |

原始 [48 行报告](../reports/evaluation.json)及[fixture](../evals/evidence-cases.json)完整保留。V1/V2 是确定性 provider 的 plain/structured **输出契约**，不是 LLM 对两份提示词的理解能力；没有模型调用、token 账单或真实人工评分。

Workflow 的真实 trace 是 Input → Retrieval（evidence_ids=[]）→ Condition（observed=0，passed=false），后面没有 LLM 节点执行。`empty` 也有同样停止路径。本轮复现时另外构造了一条显式篡改引文的 validator probe，被 `grounding_errors` 拒绝；它是 QA 输入，不能称为捕捉到一次真实模型幻觉。

## 2. 12/12 通过，为什么仍没有一个已验证产品决策

历史结果为 V1 0/12、V2 11/12、RAG 12/12、Workflow 12/12。Workflow 中 2 条拒答，**另外 10 条仍 pending_approval**，human_rating 全为 null。这里的 `task_success` 只表示预设规则检查通过，不等于工作流经人审完成。`counterexample` 保留相互不同的观察，`no-ai` 保留标签规则选项，`metadata-not-outcome` 原样标明招募 8–12 人是计划。

因此没有把候选 North Star 填成“12 次有效决策”，也没有据此选择 AI build advisor。真实证据、观察结果和人的结果判断缺一不可。即使原文引用被人接受，也只能先成为可审阅的观察；方便样本中的一次陈述不等于用户群普遍需要这个功能。

## 3. 界面之外，服务端也能停住吗

[本轮独立执行](../reports/decision-case.json)使用临时 SQLite、真实 FastAPI 应用与 TestClient。它不是 TCP/浏览器复测；所有审阅输入明确为脚本 QA。

| 真实调用 | 观察 | 保留的边界 |
| --- | --- | --- |
| 未审 insight 创建 opportunity | HTTP 422 | 不能把推荐悄悄转成已确认需求 |
| 接受 insight、确认 opportunity，随后否决其支持证据；再创建实验 | HTTP 422 | 旧的人确认不能越过新的反证 |
| 运行 route 工作流 | pending_approval | 格式/引用通过仍等待判断 |
| 人审接口拒绝该候选 | rejected；工作流成功率 0 | 否决不写成技术成功 |
| 读取最终分析 | real participants=0；validated product decisions=0 | 自动化 QA 不冒充用户或效果 |

新增[时效证据回归](../tests/test_decision_case.py)锁定“机会已经确认，但支持证据后来被否决”的协议创建边界。产品实现已有这个防线，本轮没有为增加功能而重写流程。48 次提取也再次真实执行，历史报告与新执行分别保存在导出中。

## 4. 从待访谈转为采样与停止规则

下面是**预备协议，不是已完成研究**。沿用 [PM 研究计划](product/03-research-plan.md)和 [ARC 观察方案](research/arc-shift-plan.md)，不根据这些合成 fixture 预先宣布“玩家不懂共鸣”。

| 阶段 | 需要采集的真实材料 | 继续条件 | 停止或返回条件 |
| --- | --- | --- | --- |
| 4–6 位探索性 PM 访谈目标 | 一次近期真实决策的脱敏材料；证据在哪一步丢失 | 有同意且能关联到具体任务，不只有泛泛好评 | 无材料或问题未复现：保留假设，不宣称 PMF |
| 8–12 位成人首次玩家目标 | 低/高肉鸽熟悉度均覆盖；固定版本/seed，未提示观察，干预标记 | 有独立参与者的同类任务问题及准确引用；主动找负例 | 仅一人一句话、技术故障或主持人提示造成：不做普遍结论，针对薄弱分层补采样 |
| 编码与机会确认 | source_id、参与者假名、日期、原话、行为、解释、反例分栏 | 人复核来源和负例；只计算独立参与者，不把重复评论累计为频率 | 引文无效、不同意或撤回：停止使用；解释冲突：保留分歧并重开机会 |
| 干预选择 | 比较现状、标签/规则方案，只有问题确实需要才比较 AI | 预注册任务、成功定义、招募上限和停止条件 | 非 AI 方案足够时不加 Agent；证据不足时不选 AI 功能 |
| 小型可用性试验 | 无帮助任务理解、关键错误、放弃、主持干预和反例 | 报告原始人数/次数与局限，真实观察后才填 result | 出现同意/隐私问题立即停止；新关键错误先修复；达到预定样本上限仍矛盾则结论不充分 |

“重复问题”的门槛是决策评审要求，不是用某个小人数证明总体比例；在正式研究前要由研究负责人记录样本上限、分层覆盖和具体任务错误定义。本项目不虚构独立审阅者。没有第二位编码人时保留单人解释局限，不填写一致性系数。

## 5. 被拒方案、代价和下一实验

拒绝了“引用有出处就自动排优先级”“让更长 prompt 补足缺失访谈”“先做 AI 顾问再找理由”的方案。选择 exact-extract、显式人审和规则条件，得到的是可检查的有限工作流；代价是多一步审阅、只能处理较窄文本、无法理解所有语义。词汇检索仍会漏掉同义表达或误收偶然重叠；精确引文检查也无法判断解释是否合理。

**下一实验尚未执行**：先完成探索访谈，判断“证据到决策交接丢失”是否反复出现；若没有，停止扩大产品。若有，使用同一真实脱敏决策任务比较当前笔记方法与证据包，交叉平衡顺序，记录找到来源/识别反证/拒绝无依据结论的行为与额外时间。小样本只判断可用性与方向，不宣称节省百分比或显著性。玩家研究单独进行，不能用 PM 的反馈替代玩家任务证据。

## 6. 复现

```bash
# 按 README 安装依赖；不需要 API key。只写临时 SQLite 和输出文件。
DESIGNLENS_PROVIDER=extractive python -m scripts.decision_case --output reports/decision-case.json
python -m pytest tests/test_decision_case.py tests/test_backend.py -q
```

PowerShell 先执行 `$env:DESIGNLENS_PROVIDER='extractive'`，再运行 Python 命令。导出保留全部历史 48 行、重新执行的 48 行、HTTP 拒绝细节、引文变异输入、源文件 SHA256 与执行环境。时间、ID 会变化，观察到的契约与停止结果才是回归目标。

AI-assisted 实现与研究方案；本人必须读懂和实际执行后才能用第一人称讲述。访谈、真实业务效果、真实 LLM 能力和生产托管均没有被这些检查证明。

## 本轮验证记录

2026-09-10 本机：完整后端 **44 passed，0 skipped**；[JUnit 原始记录](../reports/decision-case-tests.xml)。48 条确定性工作流/提取与 HTTP 边界脚本真实执行通过。保留两个已有依赖弃用警告；本轮没有重跑本机浏览器。历史 A–T 手册的 43 指新增测试之前的冻结结果。

本轮首次功能提交 `29d007bf639d281894131daeeddb11f515b1de96` 的 [Linux CI 34463711921](https://github.com/QiQiyzhu/designlens-ai/actions/runs/34463711921) 已成功：44 后端、6 浏览器及新增决策边界导出实际执行。[下载的原始记录](qa/decision-case-ci/README.md)绑定这个精确 source SHA；后续文档与跨平台哈希说明不改写历史结果。README 顶部工作流徽章查看分支最新 CI。
