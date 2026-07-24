# Interview Copilot Agent 系统规格说明

## 1. 文档信息

- 项目名称：Interview Copilot Agent
- 版本：v0.2
- 阶段：Phase 1
- 产品类型：个人面试准备与模拟训练系统
- 核心架构：双 Agent + Knowledge Service + 状态机
- 首要岗位：AI 应用开发 / 智能体应用开发
- 首要交互方式：文字
- 默认部署方式：本地优先、Docker Compose

---

## 2. 项目目标

系统根据用户简历、项目资料和目标职位描述，提供有状态、可评估、个性化的面试训练流程。

Phase 1 应完成：

1. 简历结构化解析；
2. JD 结构化解析；
3. 岗位匹配与能力差距分析；
4. 个性化面试计划；
5. 多轮文字模拟面试；
6. 动态追问；
7. 单题结构化评价；
8. 改进回答与知识讲解；
9. 整场面试复盘；
10. 历史成绩与薄弱项跟踪；
11. 基于个人资料的 RAG 检索。

系统核心价值：

> 将一次性的大模型问答，转化为可持续训练、可追溯评价和可恢复状态的面试准备系统。

---

## 3. 非目标

Phase 1 不实现：

- 面试现场隐蔽代答；
- 自动加入真实面试会议；
- 自动替用户回答面试问题；
- 自动投递简历；
- 企业招聘管理系统；
- 候选人筛选；
- 视频表情识别；
- 眼动分析；
- 实时语音；
- 移动端 App；
- 微服务集群；
- 多 Agent 自由协商；
- 多模型投票；
- 复杂商业计费。

---

## 4. 用户角色

## 4.1 求职者

可执行：

- 上传和管理简历；
- 添加目标 JD；
- 上传项目资料；
- 查看能力差距；
- 创建面试计划；
- 参加模拟面试；
- 查看单题评价；
- 查看整场报告；
- 查看历史进步；
- 删除或导出个人数据。

## 4.2 本地管理员

Phase 1 仅提供：

- 模型配置；
- 服务健康检查；
- 系统题库模板管理；
- 错误日志查看；
- Prompt 版本管理。

管理员不得默认读取用户原始资料。

---

## 5. 总体架构

```text
┌───────────────────────────────────────────────┐
│            React + TypeScript Frontend        │
│                                               │
│ Resume / JD / Interview / Evaluation / Report │
└───────────────────────┬───────────────────────┘
                        │ REST + SSE
┌───────────────────────▼───────────────────────┐
│                 FastAPI Application           │
│                                               │
│  API Layer                                    │
│      │                                        │
│  Interview Workflow / State Machine           │
│      │                                        │
│      ├──────── Interview Agent                │
│      └──────── Evaluation Agent               │
│                       │                       │
│              Knowledge Service                │
│                       │                       │
│  Resume / Job / Progress / Report Services    │
│                       │                       │
│                 Model Gateway                 │
└───────────────────────┬───────────────────────┘
                        │
       ┌────────────────┼─────────────────┐
       ▼                ▼                 ▼
 PostgreSQL          pgvector        Local Storage
```

---

## 6. 架构约束

1. Phase 1 使用模块化单体。
2. 只有 Interview Agent 和 Evaluation Agent 被定义为 Agent。
3. Knowledge Service、Progress Service 和文档解析均为普通服务。
4. Agent 是逻辑角色，不要求独立进程。
5. Agent 之间不进行自由对话，只通过状态机和结构化数据协作。
6. 核心状态必须持久化到 PostgreSQL。
7. LLM 不得直接执行 SQL。
8. LLM 不得直接访问任意本地文件路径。
9. 所有核心模型输出必须经过 Pydantic 校验。
10. 所有用户数据请求必须带 `user_id` 过滤。
11. 模型失败不得破坏已经保存的面试状态。
12. RAG 返回的项目事实必须保留来源。

---

## 7. 核心组件规格

## 7.1 Interview Agent

### 目标

根据候选人画像、目标岗位、面试配置和当前会话状态，决定面试接下来应该做什么。

### 主要职责

- 生成面试计划；
- 选择下一道题；
- 调整题目难度；
- 根据用户回答决定是否追问；
- 控制面试节奏；
- 避免重复问题；
- 判断何时结束面试。

### 输入

```json
{
  "candidate_profile": {},
  "job_profile": {},
  "interview_config": {
    "duration_minutes": 45,
    "difficulty": "medium",
    "style": "standard",
    "max_follow_ups": 2
  },
  "session_state": {
    "asked_question_ids": [],
    "current_question": {},
    "follow_up_count": 0,
    "remaining_minutes": 30
  },
  "latest_answer_summary": {},
  "retrieved_context": []
}
```

### 输出

```json
{
  "action": "ask|follow_up|next|finish",
  "question": {
    "question_id": "uuid",
    "text": "string",
    "type": "technical|project|behavioral|coding|system_design",
    "difficulty": "easy|medium|hard",
    "skill_tags": [],
    "expected_points": [],
    "source_refs": []
  },
  "reason": "string"
}
```

### 行为规则

- 不提前显示完整参考答案；
- 同一问题默认最多追问 2 次；
- 不得重复已问题目；
- 项目问题必须基于用户资料；
- 资料不足时不得假设用户做过某项工作；
- 连续无法回答时可以降低难度；
- 只允许返回规定动作；
- 不负责给用户回答打最终分；
- 不负责写数据库。

---

## 7.2 Evaluation Agent

### 目标

对用户回答进行可解释、结构化、可追溯的评价，并生成改进建议。

### 主要职责

- 判断是否回答了问题；
- 判断技术内容是否正确；
- 检查关键点是否完整；
- 判断表达是否清晰；
- 检查项目经历是否与资料一致；
- 输出维度评分；
- 生成改进建议；
- 生成更优回答；
- 生成知识讲解和练习题；
- 汇总整场面试报告。

### 输入

```json
{
  "question": {},
  "expected_points": [],
  "user_answer": "string",
  "candidate_profile": {},
  "retrieved_context": [],
  "evaluation_rubric": {},
  "interview_level": "intern"
}
```

### 输出

```json
{
  "overall_score": 78,
  "dimension_scores": {
    "correctness": 80,
    "completeness": 70,
    "relevance": 90,
    "depth": 72,
    "clarity": 84,
    "project_grounding": 75,
    "credibility": 80
  },
  "strengths": [],
  "errors": [],
  "missing_points": [],
  "improvement_advice": [],
  "answer_framework": [],
  "improved_answer": "string",
  "practice_questions": [],
  "confidence": 0.86
}
```

### 行为规则

- 所有分数范围为 0—100；
- 每项扣分必须给出具体理由；
- 开放问题不能只按固定答案机械评分；
- 无法可靠评价时降低 `confidence`；
- 涉及用户项目时必须检查资料一致性；
- 改进回答不能编造经历；
- 区分“通用示例”和“基于用户经历的回答”；
- 不决定下一道题；
- 不直接修改面试状态；
- 不直接写数据库。

---

## 7.3 Knowledge Service

### 目标

为 Interview Agent 和 Evaluation Agent 提供可信、受权限控制的用户资料与知识上下文。

### 主要职责

- 解析简历、JD 和项目文件；
- 文档切分；
- Embedding；
- 向量检索；
- 关键词检索；
- RRF 融合；
- 元数据过滤；
- 返回来源；
- 删除和重建索引。

### 输入

```json
{
  "user_id": "uuid",
  "query": "string",
  "scope": ["resume", "job", "project_docs", "knowledge_base"],
  "filters": {},
  "top_k": 8
}
```

### 输出

```json
{
  "results": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "content": "string",
      "source_type": "project_docs",
      "source_name": "README.md",
      "score": 0.91
    }
  ]
}
```

### 规则

- 每次查询必须带 `user_id`；
- 不得跨用户检索；
- 无结果时返回空数组；
- 不伪造来源；
- 删除文档后必须同步删除索引；
- 项目事实应返回文档名和片段 ID。

---

## 7.4 Interview State Machine

### 状态

```text
CREATED
PREPARING
QUESTION_READY
WAITING_ANSWER
ANSWER_SAVED
EVALUATING
FOLLOW_UP_READY
NEXT_QUESTION_READY
PAUSED
COMPLETED
REPORT_GENERATING
REPORT_READY
FAILED
```

### 正常流程

```text
CREATED
  ↓
PREPARING
  ↓
QUESTION_READY
  ↓
WAITING_ANSWER
  ↓
ANSWER_SAVED
  ↓
EVALUATING
  ↓
FOLLOW_UP_READY / NEXT_QUESTION_READY / COMPLETED
  ↓
REPORT_GENERATING
  ↓
REPORT_READY
```

### 状态约束

- 未保存回答时不得进入 `EVALUATING`；
- 相同幂等键不得重复保存回答；
- `COMPLETED` 后不能追加普通回答；
- `PAUSED` 可以恢复到暂停前状态；
- 每次状态变更记录时间和触发原因；
- Agent 失败时保留最近一次有效状态；
- 报告生成失败不影响已完成的面试记录。

---

## 7.5 Progress Service

### 目标

使用确定性规则聚合用户历史表现。

### 主要职责

- 统计历史分数；
- 维护技能掌握度；
- 记录已问题目；
- 识别重复错误；
- 生成薄弱项；
- 计算下一次复习时间；
- 为 Interview Agent 提供难度建议。

### 规则

- 长期记忆保存结构化指标与摘要；
- 不保存模型私有推理；
- 用户可删除全部长期记录；
- 历史低分不永久锁定用户水平；
- 新评价应按时间衰减更新掌握度。

---

## 8. 核心使用场景

## UC-01：简历分析

输入：

- PDF、DOCX、Markdown、TXT 或纯文本简历。

输出：

- 教育经历；
- 技能；
- 项目；
- 实习或工作经历；
- 证书；
- 项目成果；
- 证据映射；
- 简历风险项；
- 可能的项目追问。

约束：

- 不得添加原文不存在的项目；
- 不确定信息返回空值；
- 不根据姓名推断敏感属性。

## UC-02：JD 分析

输出：

- 岗位名称；
- 职责；
- 必备技能；
- 加分技能；
- 经验要求；
- 软技能；
- 面试重点；
- 岗位级别。

约束：

- 必备和加分项必须区分；
- 未明确写出的要求不得强行推断为硬要求。

## UC-03：岗位差距分析

输出：

- 技能覆盖情况；
- 明显缺口；
- 证据不足项；
- 高优先级复习主题；
- 推荐准备顺序；
- 匹配度说明。

匹配度只用于训练优先级，不代表真实录取概率。

## UC-04：创建面试计划

配置：

- 面试时长；
- 面试难度；
- 面试风格；
- 技术题比例；
- 项目题比例；
- 行为题比例；
- 是否包含编码题；
- 是否即时展示评分；
- 最大追问次数。

输出：

- 面试章节；
- 预计题数；
- 题型权重；
- 技能覆盖；
- 项目深挖路径。

## UC-05：模拟面试

用户可以：

- 开始；
- 提交回答；
- 请求提示；
- 跳过；
- 暂停；
- 恢复；
- 提前结束。

系统必须：

- 保存每次回答；
- 根据回答动态追问；
- 控制最大追问次数；
- 记录当前状态；
- 避免重复题；
- 支持页面刷新后恢复。

## UC-06：单题评价

输出：

- 总分；
- 分项得分；
- 正确点；
- 错误点；
- 遗漏点；
- 表达问题；
- 改进建议；
- 回答框架；
- 改进回答；
- 练习题；
- 评价置信度。

## UC-07：整场复盘

报告包含：

- 面试信息；
- 总体评分；
- 分项评分；
- 各题问答；
- 单题评价；
- 最强能力；
- 最弱能力；
- 高频错误；
- 项目表达问题；
- 推荐复习主题；
- 下一场面试建议。

## UC-08：长期训练

系统根据历史数据：

- 调整后续难度；
- 降低已掌握基础题比例；
- 提高反复错误主题频率；
- 生成复习计划；
- 展示成绩趋势。

---

## 9. 功能需求

## FR-001 用户与设置

系统应支持：

- 本地单用户模式；
- 用户偏好；
- 模型配置；
- 数据导出；
- 数据删除；
- API Key 安全配置。

数据模型保留 `user_id`，便于后续扩展。

## FR-002 简历管理

系统应支持：

- 上传 PDF；
- 上传 DOCX；
- 上传 Markdown；
- 上传 TXT；
- 粘贴文本；
- 查看解析结果；
- 手动修正字段；
- 设置当前简历；
- 删除简历。

## FR-003 JD 管理

系统应支持：

- 粘贴 JD；
- 上传 JD；
- 保存多个目标岗位；
- 设置当前目标岗位；
- 查看结构化要求；
- 删除 JD。

## FR-004 项目资料管理

系统应支持：

- 上传 README；
- 上传设计文档；
- 上传项目说明；
- 查看索引状态；
- 删除文档；
- 重建索引；
- 查看引用来源。

## FR-005 面试计划

系统应支持：

- 创建计划；
- 查看计划；
- 修改可配置参数；
- 根据历史薄弱项重新生成；
- 查看每个章节的考察目标。

## FR-006 模拟面试

系统应支持：

- 开始；
- 暂停；
- 恢复；
- 结束；
- 跳过；
- 请求提示；
- 提交回答；
- 查看当前进度；
- 查看剩余题数。

## FR-007 回答评价

系统应支持：

- 即时评价；
- 面试后统一评价；
- 查看评分维度；
- 查看错误和遗漏；
- 查看改进回答；
- 将知识点加入复习计划。

## FR-008 面试报告

系统应支持：

- 查看报告；
- 导出 Markdown；
- 查看题目和回答；
- 查看能力分布；
- 查看下一步建议。

## FR-009 历史进度

系统应支持：

- 历史面试列表；
- 技能掌握度；
- 得分趋势；
- 已练习题数；
- 薄弱知识点；
- 复习计划。

---

## 10. 数据模型

## 10.1 User

```text
id
email
display_name
preferences_json
created_at
updated_at
deleted_at
```

## 10.2 Resume

```text
id
user_id
name
file_path
file_type
raw_text
parsed_profile_json
evidence_map_json
is_current
created_at
updated_at
```

## 10.3 JobDescription

```text
id
user_id
title
company
raw_text
parsed_requirements_json
is_current
created_at
updated_at
```

## 10.4 KnowledgeDocument

```text
id
user_id
name
source_type
file_path
parse_status
index_status
created_at
updated_at
```

## 10.5 DocumentChunk

```text
id
document_id
user_id
content
metadata_json
embedding
created_at
```

## 10.6 InterviewPlan

```text
id
user_id
resume_id
job_id
config_json
plan_json
status
created_at
updated_at
```

## 10.7 InterviewSession

```text
id
user_id
plan_id
status
current_question_index
follow_up_count
last_valid_state
started_at
paused_at
completed_at
created_at
updated_at
```

## 10.8 InterviewQuestion

```text
id
session_id
parent_question_id
question_text
question_type
difficulty
skill_tags_json
expected_points_json
source_refs_json
question_fingerprint
order_index
created_at
```

## 10.9 InterviewAnswer

```text
id
question_id
user_id
answer_text
duration_seconds
hint_used
idempotency_key
submitted_at
```

## 10.10 AnswerEvaluation

```text
id
answer_id
overall_score
dimension_scores_json
strengths_json
errors_json
missing_points_json
advice_json
answer_framework_json
improved_answer
confidence
model_name
prompt_version
created_at
```

## 10.11 InterviewReport

```text
id
session_id
summary_json
weak_topics_json
recommended_actions_json
model_name
prompt_version
created_at
```

## 10.12 SkillMastery

```text
id
user_id
skill_name
mastery_score
attempt_count
last_score
last_practiced_at
next_review_at
evidence_json
updated_at
```

---

## 11. API 规格

## 11.1 简历

```text
POST   /api/v1/resumes
GET    /api/v1/resumes
GET    /api/v1/resumes/{resume_id}
DELETE /api/v1/resumes/{resume_id}
POST   /api/v1/resumes/{resume_id}/analyze
PATCH  /api/v1/resumes/{resume_id}/profile
```

## 11.2 JD

```text
POST   /api/v1/jobs
GET    /api/v1/jobs
GET    /api/v1/jobs/{job_id}
DELETE /api/v1/jobs/{job_id}
POST   /api/v1/jobs/{job_id}/analyze
```

## 11.3 差距分析

```text
POST /api/v1/matches
GET  /api/v1/matches/{match_id}
```

## 11.4 知识库

```text
POST   /api/v1/knowledge/documents
GET    /api/v1/knowledge/documents
GET    /api/v1/knowledge/documents/{document_id}
DELETE /api/v1/knowledge/documents/{document_id}
POST   /api/v1/knowledge/documents/{document_id}/reindex
```

## 11.5 面试计划

```text
POST /api/v1/interview-plans
GET  /api/v1/interview-plans
GET  /api/v1/interview-plans/{plan_id}
```

## 11.6 面试会话

```text
POST /api/v1/interviews
GET  /api/v1/interviews/{session_id}
POST /api/v1/interviews/{session_id}/start
POST /api/v1/interviews/{session_id}/pause
POST /api/v1/interviews/{session_id}/resume
POST /api/v1/interviews/{session_id}/answers
POST /api/v1/interviews/{session_id}/skip
POST /api/v1/interviews/{session_id}/finish
GET  /api/v1/interviews/{session_id}/events
```

`events` 使用 SSE 推送：

- Agent 状态；
- 流式问题；
- 评价状态；
- 报告生成状态；
- 错误事件。

## 11.7 评价与报告

```text
GET  /api/v1/answers/{answer_id}/evaluation
GET  /api/v1/interviews/{session_id}/report
POST /api/v1/interviews/{session_id}/report/regenerate
GET  /api/v1/interviews/{session_id}/report/export
```

## 11.8 历史进度

```text
GET /api/v1/progress/overview
GET /api/v1/progress/skills
GET /api/v1/progress/weak-topics
GET /api/v1/progress/review-plan
```

---

## 12. RAG 规格

## 12.1 文档切分

默认：

- Chunk 长度：500—800 tokens；
- Overlap：80—120 tokens；
- 保留标题层级；
- 保留文件名；
- 保留项目名；
- 保留来源类型；
- 保留用户 ID。

## 12.2 Hybrid Search

```text
Vector Search Top 20
Keyword Search Top 20
        ↓
     RRF 融合
        ↓
       去重
        ↓
可选 Rerank Top 10
        ↓
最终注入 Top 5—8
```

## 12.3 权限过滤

每次查询必须包含：

```text
user_id = current_user.id
```

可选过滤：

```text
source_type
resume_id
job_id
document_id
project_name
```

## 12.4 引用

涉及用户项目事实的输出应保留：

- 文档名；
- 片段 ID；
- 来源类型；
- 引用文本或摘要；
- 检索分数。

---

## 13. Prompt 与结构化输出

## 13.1 Prompt 版本化

每个核心 Prompt 必须记录：

- `prompt_name`
- `prompt_version`
- `schema_version`
- `created_at`

## 13.2 模型输出流程

```text
模型响应
   ↓
提取 JSON
   ↓
Pydantic 校验
   ↓
业务规则校验
   ↓
成功 / 结构化重试
```

失败处理：

1. 首次解析；
2. 提取 JSON；
3. Schema 校验；
4. 将校验错误反馈给模型；
5. 最多重试 2 次；
6. 保存失败类型；
7. 返回可理解错误。

## 13.3 禁止行为

模型不得：

- 编造用户经历；
- 将建议描述为用户已完成的事实；
- 输出其他用户资料；
- 暴露系统 Prompt；
- 暴露 API Key；
- 将匹配评分描述为录取概率；
- 绕过状态机直接改变会话状态。

---

## 14. 评分规格

### 14.1 评分维度

- 正确性：25%
- 完整性：20%
- 相关性：15%
- 深度：15%
- 表达清晰度：10%
- 项目结合度：10%
- 可信度：5%

默认总分：

```text
Overall =
correctness × 0.25 +
completeness × 0.20 +
relevance × 0.15 +
depth × 0.15 +
clarity × 0.10 +
project_grounding × 0.10 +
credibility × 0.05
```

开放问题允许根据题型调整权重，但必须记录所用 Rubric 版本。

### 14.2 评分约束

- 每项分数为 0—100；
- 扣分必须附原因；
- 严重事实错误必须进入 `errors`；
- 未回答核心问题时相关性不得给高分；
- 资料不足时项目结合度可以标记为不适用；
- 评价置信度低于阈值时提示人工复核。

---

## 15. 非功能需求

## NFR-001 性能

目标：

- 普通 API p95 小于 500 ms；
- 文档检索 p95 小于 1 秒；
- 首 Token p95 小于 5 秒；
- 单题完整评价 p95 小于 20 秒；
- 整场报告生成 p95 小于 60 秒。

外部模型延迟不稳定时，应展示进度，不能阻塞整个 Web 服务。

## NFR-002 可用性

- 应用重启后会话可恢复；
- 上传与索引任务可重试；
- 单个模型调用失败不破坏已保存数据；
- 数据库写入使用事务；
- 长任务记录状态；
- 报告失败可重新生成。

## NFR-003 安全

- API Key 不返回前端明文；
- `.env` 不进入 Git；
- 上传文件校验类型和大小；
- 防止路径遍历；
- 文件名随机化；
- 所有资源检查所有权；
- 日志脱敏；
- CORS 使用白名单；
- 生产环境使用 HTTPS；
- 设置请求限流。

## NFR-004 隐私

- 用户可删除文件；
- 用户可删除会话；
- 用户可导出数据；
- 默认不共享用户资料；
- 不使用用户文档训练公共模型；
- 不保存不必要的模型私有推理。

## NFR-005 可观测性

记录：

- `request_id`
- `user_id`
- `session_id`
- `agent_name`
- `prompt_version`
- `model_name`
- 延迟
- Token 使用量
- 重试次数
- 错误类型
- Schema 校验结果

不得记录：

- 完整 API Key；
- 密码；
- 未脱敏认证头。

## NFR-006 可测试性

- Agent 支持 Mock LLM；
- 状态机可独立测试；
- 检索层可替换；
- Prompt 有固定回归集；
- 数据库测试使用隔离事务；
- 外部模型调用可模拟。

---

## 16. 评估体系

## 16.1 简历和 JD 解析

- 字段提取准确率；
- 项目遗漏率；
- 项目事实幻觉率；
- 必备技能识别准确率；
- 来源映射正确率。

## 16.2 Interview Agent

- 问题与 JD 相关性；
- 问题与简历相关性；
- 重复率；
- 难度适配度；
- 追问合理性；
- 动作 Schema 成功率。

## 16.3 Evaluation Agent

- 与人工评分相关性；
- 重复评分稳定性；
- 技术错误识别率；
- 遗漏点识别率；
- 错误建议率；
- 经历幻觉率。

## 16.4 RAG

- Recall@K；
- MRR；
- nDCG；
- 引用正确率；
- 无答案拒答率；
- 跨用户泄漏率，目标必须为 0。

## 16.5 产品指标

- 面试完成率；
- 平均训练时长；
- 复盘查看率；
- 二次模拟得分提升；
- 薄弱项复习完成率。

---

## 17. 错误处理

错误类型：

```text
VALIDATION_ERROR
AUTH_ERROR
PERMISSION_ERROR
FILE_PARSE_ERROR
INDEX_ERROR
MODEL_TIMEOUT
MODEL_RATE_LIMIT
MODEL_OUTPUT_INVALID
RETRIEVAL_ERROR
DATABASE_ERROR
WORKFLOW_STATE_ERROR
INTERNAL_ERROR
```

统一错误响应：

```json
{
  "error": {
    "code": "MODEL_OUTPUT_INVALID",
    "message": "模型输出格式校验失败",
    "request_id": "uuid",
    "retryable": true
  }
}
```

---

## 18. 配置规格

`.env.example`：

```env
APP_ENV=development
APP_SECRET_KEY=

DATABASE_URL=postgresql+asyncpg://user:password@postgres/interview_agent

CHAT_PROVIDER=openai_compatible
CHAT_BASE_URL=
CHAT_API_KEY=
CHAT_MODEL=deepseek-chat
CHAT_TEMPERATURE=0.2

EMBEDDING_PROVIDER=dashscope
EMBEDDING_API_KEY=
EMBEDDING_MODEL=text-embedding-v4

VECTOR_BACKEND=pgvector
MAX_UPLOAD_MB=20
LLM_TIMEOUT_SECONDS=90
LLM_MAX_RETRIES=2
MAX_FOLLOW_UPS=2
```

要求：

- `.env` 加入 `.gitignore`；
- 提供 `.env.example`；
- 日志屏蔽 Secret；
- 启动时校验必填项；
- 前端只显示 Key 是否已配置，不显示明文。

---

## 19. 部署规格

## 19.1 本地开发

```text
Docker Compose
  ├── backend
  ├── frontend
  └── postgres + pgvector
```

## 19.2 Phase 1 生产部署

```text
Nginx
  ├── Frontend
  └── FastAPI
          ↓
 PostgreSQL + pgvector
```

Phase 1 不强制使用 Redis。

满足以下条件后再考虑 Redis：

- 多后端实例；
- 大量后台任务；
- 跨进程事件；
- 分布式锁；
- 独立任务队列。

---

## 20. 测试要求

### 20.1 单元测试

- Pydantic Schema；
- 评分聚合；
- 题目去重；
- 状态转换；
- 文档切分；
- RRF 融合；
- ACL 过滤；
- 技能掌握度更新。

### 20.2 集成测试

- 上传到解析；
- 简历和 JD 到差距分析；
- 计划到面试；
- 回答到评价；
- 评价到报告；
- 文档上传到检索；
- 暂停后恢复；
- 模型失败后重试。

### 20.3 E2E 测试

完整流程：

```text
上传简历
  ↓
添加 JD
  ↓
上传项目资料
  ↓
生成面试计划
  ↓
完成模拟面试
  ↓
查看评价和报告
  ↓
查看薄弱项
```

### 20.4 Prompt 回归测试

至少覆盖：

- Python；
- FastAPI；
- Docker；
- LangChain；
- LangGraph；
- RAG；
- Hybrid Search；
- ACL；
- Function Calling；
- MCP；
- Agent 评估；
- 项目深挖；
- 行为面试；
- 系统设计；
- Debug 问题。

---

## 21. Phase 1 完成标准

满足以下条件时可标记为 v1.0：

1. 用户可以上传简历、JD 和项目资料；
2. 系统可以生成结构化候选人画像；
3. 系统可以生成岗位要求与差距分析；
4. Interview Agent 可以生成个性化计划；
5. 用户可以完成一场文字模拟面试；
6. Interview Agent 可以合理追问；
7. Evaluation Agent 可以输出结构化评分；
8. 系统可以生成改进回答；
9. 系统可以生成整场复盘报告；
10. 系统可以记录历史成绩和薄弱项；
11. 项目事实可以追溯到用户资料；
12. 不同用户数据实现权限隔离；
13. 会话中断后可以恢复；
14. 核心流程具有自动化测试；
15. Docker Compose 可以一键启动；
16. API Key 和用户文件不会进入 Git；
17. 模型输出异常有校验、重试和错误提示。
