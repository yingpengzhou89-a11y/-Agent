# Interview Copilot Agent 设计稿（Phase 2）

## 1. 设计结论

Phase 1 只定义两个真正的 Agent：

1. **Interview Agent**：计划、选题、追问、节奏和结束决策；
2. **Evaluation Agent**：评分、纠错、讲解、改进回答和整场复盘。

简历/JD 解析、匹配分析、知识库检索、会话状态、报告持久化、进度聚合全部是普通服务或确定性规则。这样可以将大模型的自主决策严格收敛在“如何问”和“如何评”两个最需要语义判断的场景。

```text
Frontend
  ↓ REST + SSE
FastAPI
  ↓
Interview Workflow / Persistent State Machine
  ├── InterviewAgent
  ├── EvaluationAgent
  ├── KnowledgeService
  ├── ResumeService / JobService / MatchService
  ├── ProgressService / ReportService
  └── ModelGateway
  ↓
PostgreSQL + pgvector + local object storage
```

## 2. 共同运行边界

### 2.1 模型只做受控的结构化决策

所有 Agent 调用均采用同一链路：服务端构造最小输入 → 模型返回 JSON → Pydantic 校验 → 业务守卫 → 持久化。

```python
class AgentContext(BaseModel):
    request_id: UUID
    user_id: UUID
    session_id: UUID | None = None
    model_name: str
    prompt_name: str
    prompt_version: str
    token_budget: int

class BaseAgent[InputT, OutputT]:
    async def run(self, ctx: AgentContext, payload: InputT) -> OutputT: ...
```

约束：

- Agent 不直接操作数据库、文件路径或 SQL；
- Agent 不能自行变更会话状态；
- 用户资料、检索范围、模型参数和 Prompt 版本均由后端注入；
- 输出必须经 Pydantic 和业务规则校验，最多两次结构化修复重试；
- 失败时保留最后一个有效持久化状态，并返回可理解错误。

### 2.2 用户事实必须可溯源

项目事实或候选人经历统一附带来源。无来源时只能表达为通用建议或未知，不能写成用户事实。

```python
class SourceRef(BaseModel):
    document_id: UUID
    chunk_id: UUID
    source_type: Literal["resume", "job", "project_docs", "knowledge_base"]
    source_name: str
    quote: str
    score: float = Field(ge=0, le=1)
```

`KnowledgeService` 在执行 Hybrid Search 前强制加入 `user_id` 条件；模型从不获得跨用户资料。

## 3. Interview Agent

### 3.1 职责

- 在创建计划时，依据候选人画像、JD、配置和历史薄弱项生成面试章节与题目蓝图；
- 在面试中，针对当前状态决定 `ask`、`follow_up`、`next` 或 `finish`；
- 调整难度、控制时间、避免题目重复；
- 仅在资料充分时提出项目深挖问题。

不负责评分、给出完整参考答案、写数据库或改变状态机状态。

### 3.2 输入与输出

```python
class InterviewAgentInput(BaseModel):
    candidate_profile: CandidateProfile
    job_profile: JobProfile
    interview_config: InterviewConfig
    session_state: SessionSnapshot
    latest_answer_summary: AnswerSummary | None
    retrieved_context: list[SourceRef]

class InterviewDecision(BaseModel):
    action: Literal["ask", "follow_up", "next", "finish"]
    question: InterviewQuestionDraft | None = None
    reason: str

class InterviewQuestionDraft(BaseModel):
    text: str
    type: Literal["technical", "project", "behavioral", "coding", "system_design"]
    difficulty: Literal["easy", "medium", "hard"]
    skill_tags: list[str]
    expected_points: list[str]
    source_refs: list[SourceRef]
```

`question` 仅当动作是 `ask` 或 `follow_up` 时必填。服务端生成 Question UUID、计算题目指纹、保存问题后，才能将其展示给用户。

### 3.3 Prompt 的核心规则

```text
你是技术模拟面试官。仅决定下一步面试动作。
只能使用当前输入提供的候选人资料与检索资料；无来源的经历不可假设。
不要评价用户回答，不要透露完整参考答案。
只能返回 ask、follow_up、next 或 finish。
同一题的追问由服务端限制；不得以模型文字绕过该限制。
仅输出符合 schema_version 的 JSON。
```

## 4. Evaluation Agent

### 4.1 职责

- 判断用户是否回应了问题以及内容是否准确、完整、相关、清晰；
- 对项目陈述检查资料一致性；
- 输出可解释的分项评分、错误点和遗漏点；
- 给出回答框架、改进建议、改进回答、知识讲解与练习题；
- 汇总已经保存的单题评价，生成整场报告草稿。

不负责决定下一题、直接修改会话状态、写数据库或虚构用户经历。

### 4.2 输入与输出

```python
class EvaluationAgentInput(BaseModel):
    question: InterviewQuestion
    expected_points: list[str]
    user_answer: str
    candidate_profile: CandidateProfile
    retrieved_context: list[SourceRef]
    evaluation_rubric: EvaluationRubric
    interview_level: Literal["intern", "junior", "mid", "senior"]

class AnswerEvaluation(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    dimension_scores: DimensionScores
    strengths: list[str]
    errors: list[EvaluationIssue]
    missing_points: list[str]
    improvement_advice: list[str]
    answer_framework: list[str]
    improved_answer: str
    practice_questions: list[str]
    confidence: float = Field(ge=0, le=1)
```

默认 Rubric 为：正确性 25%、完整性 20%、相关性 15%、深度 15%、清晰度 10%、项目结合度 10%、可信度 5%。开放题可调整权重，但必须保存 Rubric 版本。评分分为三层：后端先记录非空、长度、预期要点命中和项目证据等确定性检查；Evaluation Agent 仅输出维度判断；后端按存档 Rubric 复算最终总分并持久化检查结果与调用配置。

### 4.3 输出守卫

- 每项分数限定在 0—100；
- 总分由后端按存档 Rubric 复算，避免模型算术漂移；
- `errors` 必须包含具体问题和扣分依据；
- 对资料不足的项目问题，`project_grounding` 标为不适用或降低置信度，不能臆测扣分；
- `improved_answer` 中若没有来源佐证的项目表述，后端降级为“通用示例”；
- `confidence` 低于策略阈值时，报告不得下强结论。

## 5. 服务分工

| 模块 | 是否 Agent | 关键职责 |
|---|---:|---|
| ResumeService | 否 | 文件解析、简历结构化提取、证据映射与人工修正 |
| JobService | 否 | JD 结构化提取、必备/加分技能识别 |
| MatchService | 否 | 标准化技能匹配、差距与复习优先级计算 |
| KnowledgeService | 否 | 切分、Embedding、关键词召回、RRF、ACL、引用返回 |
| InterviewWorkflow | 否 | 状态迁移、追问上限、幂等、事件推送与恢复 |
| ProgressService | 否 | 分数聚合、掌握度、遗忘/复习计算、难度建议 |
| ReportService | 否 | 聚合持久化评价，格式化 Markdown/前端报告 |
| ModelGateway | 否 | 模型调用、超时、重试、JSON 提取、审计与脱敏 |

简历和 JD 的结构化提取可以调用模型，但属于服务内受控 Prompt 任务，不增加新的 Agent。

## 6. 状态机与 Agent 编排

```text
CREATED → PREPARING → QUESTION_READY → WAITING_ANSWER
  → ANSWER_SAVED → EVALUATING
      ├─ InterviewAgent 决定追问 → FOLLOW_UP_READY → WAITING_ANSWER
      ├─ InterviewAgent 决定下一题 → NEXT_QUESTION_READY → QUESTION_READY
      └─ InterviewAgent 决定完成 → COMPLETED
  → REPORT_GENERATING → REPORT_READY
```

一次提交回答的受控顺序：

1. API 验证会话归属和幂等键；
2. 保存 `InterviewAnswer`，状态转为 `ANSWER_SAVED`；
3. 调用 Evaluation Agent，校验并保存 `AnswerEvaluation`；
4. 调用 ProgressService 更新结构化指标；
5. 对当前题按需检索，调用 Interview Agent；
6. 状态机校验动作、追问上限、时间预算和题目指纹；
7. 保存下一题或完成会话，并通过 SSE 发布事件。

评价失败不会丢失答案；Interviewer 失败不会破坏上一题评价。`PAUSED` 保存暂停前状态，并仅能恢复到该状态。

## 7. 关键守卫

| 风险 | 后端规则 |
|---|---|
| 题目重复 | `normalized_text + type + skill_tags` 计算 `question_fingerprint` |
| 无限追问 | `follow_up_count < config.max_follow_ups`，默认 1 |
| 越权检索 | 每个查询第一条件为 `user_id = current_user.id` |
| 经历幻觉 | 项目问题与项目改进回答须有 `SourceRef`；否则改用通用表达 |
| 非法状态 | 仅允许已定义的转换，并在事务中更新状态/时间/原因 |
| 重复答案 | `(question_id, idempotency_key)` 唯一约束 |
| 模型输出失效 | JSON 提取 → Pydantic → 业务验证 → 最多 2 次修复重试 |
| 上下文失控 | 仅注入当前题、答案摘要、会话摘要与 Top 5—8 检索块 |

## 8. Prompt 与可观测性

Prompt 按版本文件管理：

```text
backend/app/prompts/
  interview_agent/v1.md
  evaluation_agent/v1.md
  resume_extract/v1.md
  job_extract/v1.md
  report_summary/v1.md
```

每次模型调用审计：`request_id`、`user_id`、`session_id`、模块名、Prompt 版本、模型、耗时、Token、重试次数和校验结果。日志不可记录 API Key、密码、认证头或未经脱敏的完整用户资料。

第二阶段在 `agent_decision_logs` 保存 Agent 级决策审计：`agent_name`、动作、执行模式（模型或降级）、输入/输出摘要、模型名和 Prompt 版本。它把模型语义判断与后端状态迁移分开，使同一会话的计划、评分、下一题/结束决定均可复盘。

## 9. 最小实现顺序

1. 建立 Pydantic Schema、ModelGateway、数据库模型与统一错误模型；
2. 完成 ResumeService、JobService、MatchService，确保所有项目事实有来源；
3. 实现 Interview Agent 的计划与选题能力、题目指纹及持久化；
4. 实现可恢复状态机、回答幂等保存和 SSE；
5. 实现 Evaluation Agent、Rubric 复算和单题评价；
6. 完成 ReportService 与 ProgressService；
7. 接入 KnowledgeService 的 Hybrid Search 并增加 Prompt/RAG/E2E 回归测试。

此顺序优先交付“简历 + JD → 面试计划 → 文字模拟 → 可解释评价 → 复盘”的完整闭环。

## 10. MVP 验收用例

- 简历未出现的项目不得被生成到项目追问或改进回答中；
- 两个用户拥有同关键词资料时，检索只能返回当前用户的片段；
- 同题达到最大追问次数后，系统不能再次请求追问；
- 以相同幂等键重复提交答案，不会产生第二条回答或评价；
- 模型输出不合法时，已保存答案仍可重新评价；
- 暂停、服务重启、恢复后，会话从最后一个有效状态继续；
- 评价总分等于后端按存档 Rubric 的计算结果；
- 报告中的项目事实均可追溯至简历或项目文档片段。
