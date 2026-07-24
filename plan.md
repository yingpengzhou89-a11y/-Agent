# Interview Copilot Agent 开发计划

## 1. 项目定位

Interview Copilot Agent 是一套面向求职者的个性化面试准备系统，第一阶段聚焦以下岗位：

- AI 应用开发
- 智能体应用开发
- Python 后端开发
- RAG / LangChain / LangGraph
- FastAPI 与大模型工程化

系统根据用户的简历、项目资料和目标职位描述，生成个性化面试计划，组织多轮模拟面试，对回答进行结构化评价，并持续记录薄弱知识点。

项目定位为：

> 面试前准备、模拟训练、项目表达优化、知识补强与复盘提升工具。

项目不用于真实面试中的隐蔽代答，也不自动替用户参加面试。

---

## 2. Phase 1 产品目标

第一阶段完成一个可实际使用的文字版 MVP：

1. 上传或粘贴简历。
2. 输入目标职位 JD。
3. 解析简历与 JD，形成结构化画像。
4. 识别候选人与岗位之间的能力差距。
5. 自动生成个性化面试计划。
6. 开展文字模拟面试。
7. 根据回答动态追问。
8. 对每个回答进行结构化评分。
9. 生成更优回答与知识讲解。
10. 输出整场面试复盘报告。
11. 保存历史成绩、已问题目和薄弱知识点。
12. 基于个人项目资料进行 RAG 检索，避免编造经历。

---

## 3. MVP 范围

### 3.1 MVP 必须包含

- 单用户本地模式；
- 一份当前简历；
- 一个目标 JD；
- AI/智能体应用开发岗位模板；
- 技术面试；
- 项目深挖；
- 行为面试；
- 文字回答；
- 动态追问；
- 单题评分；
- 整场复盘报告；
- 历史面试记录；
- 简历与项目资料检索。

### 3.2 MVP 暂不包含

- 实时语音面试；
- 视频和表情识别；
- 面试现场隐蔽代答；
- 企业招聘端；
- 自动投递简历；
- 浏览器插件；
- 移动端 App；
- 多租户 SaaS；
- 多模型投票；
- 微服务拆分；
- Redis、Celery 等分布式组件；
- 复杂计费系统。

---

## 4. 核心设计原则

### 4.1 只保留两个核心 Agent

MVP 只设置两个真正需要大模型自主决策的 Agent：

1. **Interview Agent**
   - 制订面试计划；
   - 选择下一道题；
   - 控制题目难度；
   - 根据回答决定是否追问；
   - 控制面试节奏与结束条件。

2. **Evaluation Agent**
   - 评价用户回答；
   - 识别正确点、错误点和遗漏点；
   - 输出结构化评分；
   - 生成改进建议和参考回答；
   - 汇总整场面试报告。

以下能力不定义为 Agent：

- 简历解析；
- JD 解析；
- 文档切分；
- 向量检索；
- BM25 检索；
- 用户权限控制；
- 面试状态机；
- 数据库存储；
- 分数统计；
- 薄弱项聚合。

这些能力由确定性的业务模块和服务完成。

### 4.2 先形成闭环，再扩展功能

第一版优先完成：

```text
简历 + JD + 项目资料
          ↓
结构化解析与差距分析
          ↓
Interview Agent 生成计划并提问
          ↓
用户回答
          ↓
Evaluation Agent 评分与讲解
          ↓
复盘报告与薄弱项记录
          ↓
下一次自适应训练
```

### 4.3 模型与程序分工

LLM 负责：

- 语义理解；
- 生成问题；
- 动态追问；
- 技术回答评价；
- 开放问题评价；
- 解释和总结。

程序负责：

- 工作流状态；
- 题目去重；
- 最大追问次数；
- 权限隔离；
- 数据持久化；
- 分数计算；
- 输出校验；
- 失败重试；
- Token 和成本统计。

### 4.4 用户资料必须有依据

涉及用户经历时：

- 优先使用用户上传的简历和项目资料；
- 每项项目事实保留来源；
- 无资料支持时明确说明未知；
- 不能把建议写成用户已经做过的事情；
- 改进回答不得虚构项目成果。

---

## 5. 简化后的系统架构

Phase 1 使用模块化单体，不拆微服务。

```text
┌─────────────────────────────────────────────┐
│           React + TypeScript 前端            │
│ 简历 / JD / 面试 / 评价 / 报告 / 历史记录     │
└────────────────────┬────────────────────────┘
                     │ REST + SSE
┌────────────────────▼────────────────────────┐
│                FastAPI Backend              │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ Interview Workflow / State Machine    │  │
│  └───────────────────────────────────────┘  │
│             │                    │          │
│             ▼                    ▼          │
│      Interview Agent      Evaluation Agent  │
│             │                    │          │
│             └─────────┬──────────┘          │
│                       ▼                     │
│              Knowledge Service              │
│     文档解析 / Hybrid Search / 用户资料检索   │
│                                             │
│  Resume Service / Job Service / Report      │
│  Progress Service / Model Gateway           │
└────────────────────┬────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
 PostgreSQL       pgvector       本地文件存储
```

---

## 6. 核心模块职责

## 6.1 Interview Agent

职责：

- 读取候选人画像和 JD 要求；
- 生成面试计划；
- 选择题型和难度；
- 从题库模板、用户项目和模型生成题中选题；
- 按当前回答决定追问、下一题或结束；
- 避免重复问题；
- 模拟不同面试风格。

支持的面试风格：

- 友好引导型；
- 标准技术面；
- 项目深挖型；
- 压力追问型。

不负责：

- 给回答打最终分；
- 向用户泄露完整参考答案；
- 直接修改数据库；
- 任意读取本地文件。

## 6.2 Evaluation Agent

职责：

- 根据问题、预期关键点和用户回答进行评价；
- 识别事实错误、概念混淆和遗漏；
- 给出维度评分；
- 判断项目经历是否与资料一致；
- 输出回答框架；
- 生成改进回答；
- 生成知识讲解和练习题；
- 汇总整场面试报告。

不负责：

- 决定下一道题；
- 修改面试状态；
- 直接操作数据库；
- 编造用户经历。

## 6.3 Knowledge Service

职责：

- 解析 PDF、DOCX、Markdown 和 TXT；
- 保存简历、JD 和项目资料；
- 文档切分；
- Embedding；
- 向量检索；
- BM25 / 全文检索；
- RRF 融合；
- 用户 ACL 过滤；
- 返回引用来源。

Knowledge Service 是普通服务，不是 Agent。

## 6.4 Interview State Machine

职责：

- 控制面试生命周期；
- 保存当前问题和追问次数；
- 防止状态跳转错误；
- 支持暂停、恢复和结束；
- 保证回答先保存、再评价；
- 防止重复提交。

## 6.5 Progress Service

职责：

- 聚合历史分数；
- 记录已问题目；
- 统计薄弱知识点；
- 计算技能掌握度；
- 生成复习计划；
- 为 Interview Agent 提供下一次训练上下文。

Progress Service 使用确定性统计规则，不定义为 Agent。

---

## 7. 推荐技术栈

### 7.1 后端

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- pgvector
- OpenAI-compatible SDK
- LangGraph 或自研有限状态机

建议：

- MVP 可使用 LangGraph 展示 Agent 工作流能力；
- 面试状态仍需持久化到数据库；
- 不允许只依赖 LangGraph 内存状态。

### 7.2 模型

- 对话模型：DeepSeek 或其他 OpenAI-compatible 模型
- Embedding：DashScope `text-embedding-v4`
- 可选 Reranker：后续按检索效果添加

### 7.3 前端

- React
- TypeScript
- Vite
- TanStack Query
- Zustand
- SSE 流式输出
- Markdown 渲染

### 7.4 文档处理

- PDF：PyMuPDF
- DOCX：python-docx
- Markdown / TXT：原生文本解析
- 文档切分：自定义标题感知切分器

### 7.5 测试与质量

- pytest
- pytest-asyncio
- Hypothesis
- Ruff
- Black
- MyPy
- Playwright
- Prompt 回归测试集

### 7.6 部署

MVP：

- 本地运行；
- Docker Compose；
- PostgreSQL + pgvector；
- 本地文件存储。

Phase 1 不强制引入 Redis、Celery、消息队列和微服务。

---

## 8. 建议目录结构

```text
interview-copilot-agent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── agents/
│   │   │   ├── interview_agent.py
│   │   │   └── evaluation_agent.py
│   │   ├── workflows/
│   │   │   └── interview_workflow.py
│   │   ├── services/
│   │   │   ├── resume_service.py
│   │   │   ├── job_service.py
│   │   │   ├── knowledge_service.py
│   │   │   ├── progress_service.py
│   │   │   ├── report_service.py
│   │   │   └── model_gateway.py
│   │   ├── retrieval/
│   │   │   ├── chunker.py
│   │   │   ├── vector_search.py
│   │   │   ├── keyword_search.py
│   │   │   └── fusion.py
│   │   ├── prompts/
│   │   ├── schemas/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── core/
│   │   └── main.py
│   ├── tests/
│   ├── alembic/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   └── package.json
├── data/
├── docs/
├── docker-compose.yml
├── .env.example
├── README.md
├── plan.md
└── spec.md
```

---

## 9. 分阶段开发计划

## Stage 0：项目初始化（1—2 天）

任务：

- 创建仓库；
- 初始化前后端目录；
- 配置 Python、TypeScript 和代码检查；
- 创建 `.env.example`；
- 配置 Docker Compose；
- 定义核心 Schema；
- 建立基础 CI。

首批 Schema：

- `CandidateProfile`
- `JobProfile`
- `InterviewPlan`
- `InterviewQuestion`
- `InterviewDecision`
- `AnswerEvaluation`
- `InterviewReport`

完成标准：

- 后端可以启动；
- 前端可以启动；
- 数据库连接正常；
- API Key 不进入 Git；
- CI 能执行基础检查。

---

## Stage 1：数据模型与基础服务（3—5 天）

任务：

- 搭建 FastAPI；
- 配置 SQLAlchemy 和 Alembic；
- 创建简历、JD、文档、面试、问题、回答、评价和技能表；
- 实现统一错误响应；
- 实现请求 ID；
- 实现模型调用网关；
- 实现健康检查。

主要接口：

```text
GET  /health
POST /api/v1/resumes
POST /api/v1/jobs
GET  /api/v1/resumes/{id}
GET  /api/v1/jobs/{id}
```

完成标准：

- 数据库迁移可重复执行；
- 文件元数据可保存；
- API 文档可访问；
- 错误响应格式统一。

---

## Stage 2：简历与 JD 结构化解析（4—6 天）

任务：

- 实现 PDF、DOCX、Markdown、TXT 解析；
- 实现简历结构化提取；
- 实现 JD 结构化提取；
- 建立证据映射；
- 生成候选人能力矩阵；
- 生成岗位要求矩阵；
- 实现差距分析；
- 增加 Pydantic 校验和最多两次重试。

说明：

- 这里使用普通 LLM 调用，不单独定义 Profile Agent 和 JD Agent；
- 提取任务通过 Service + Prompt 完成。

完成标准：

- 不添加简历中不存在的经历；
- 每项项目结论可以关联原文；
- JSON 最终解析成功率不低于 99%；
- 必备技能和加分技能能够区分。

---

## Stage 3：Knowledge Service 与 RAG（4—6 天）

任务：

- 上传项目 README、设计文档和复盘记录；
- 文档切分；
- Embedding；
- pgvector 检索；
- PostgreSQL 全文检索或 BM25；
- RRF 融合；
- 去重；
- 元数据过滤；
- 引用来源；
- 用户 ACL 隔离。

默认召回流程：

```text
Query
  ├── Vector Search Top 20
  └── Keyword Search Top 20
              ↓
          RRF Fusion
              ↓
            去重
              ↓
         Final Top 5—8
```

完成标准：

- 项目问题可以返回来源；
- 不同用户资料不能相互检索；
- 无相关资料时返回空结果而不是伪造；
- 检索延迟 p95 小于 1 秒。

---

## Stage 4：Interview Agent 与面试计划（4—6 天）

任务：

- 实现 Interview Agent；
- 生成面试计划；
- 支持技术、项目和行为题；
- 根据 JD 权重分配题目；
- 根据简历项目生成深挖路径；
- 支持面试风格和难度；
- 实现题目指纹与去重；
- 实现最大追问次数；
- 输出结构化 `InterviewDecision`。

完成标准：

- 每道题有明确考察目标；
- 问题与 JD 或用户项目有关联；
- 同场面试无明显重复；
- Interview Agent 不输出评分；
- Interview Agent 不提前泄露参考答案。

---

## Stage 5：面试状态机与文字闭环（4—6 天）

任务：

- 实现面试状态机；
- 支持开始、暂停、恢复、跳过和结束；
- 保存当前问题；
- 保存每轮回答；
- 根据 Interview Agent 决定追问或下一题；
- 使用 SSE 推送流式问题和状态；
- 实现幂等提交；
- 实现上下文摘要。

状态示例：

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
FOLLOW_UP / NEXT_QUESTION / FINISH
  ↓
COMPLETED
```

完成标准：

- 页面刷新后可以恢复会话；
- 同一回答不会重复保存；
- 每题追问不超过配置限制；
- 状态不能非法跳转；
- 已保存数据不会因模型失败丢失。

---

## Stage 6：Evaluation Agent 与复盘报告（5—7 天）

任务：

- 实现 Evaluation Agent；
- 定义评分 Rubric；
- 实现正确性、完整性、相关性、深度、表达、项目结合和可信度评分；
- 输出错误点与遗漏点；
- 生成回答框架；
- 生成改进回答；
- 生成知识讲解和练习题；
- 汇总整场报告。

完成标准：

- 每次扣分都有具体理由；
- 相同回答重复评分波动可控；
- 项目改进回答不编造经历；
- 无法可靠判断时降低评价置信度；
- 整场报告可以追溯到单题评价。

---

## Stage 7：历史进度与自适应训练（3—5 天）

任务：

- 实现 Progress Service；
- 聚合历史评价；
- 维护技能掌握度；
- 记录已问题目；
- 记录重复错误；
- 生成薄弱项列表；
- 生成复习计划；
- 为下一场面试提供难度建议。

完成标准：

- 已熟练基础题出现频率降低；
- 多次错误主题出现频率提高；
- 用户可以查看得分趋势；
- 历史低分不会永久锁定用户水平。

---

## Stage 8：前端与体验完善（4—7 天）

页面：

- Dashboard；
- 简历管理；
- JD 管理；
- 匹配分析；
- 面试计划；
- 模拟面试；
- 单题评价；
- 面试报告；
- 历史记录；
- 薄弱项；
- 项目知识库；
- 设置。

完成标准：

- 核心流程不依赖 Swagger；
- SSE 流式输出稳定；
- 页面刷新可恢复状态；
- 长回答不会阻塞页面；
- 错误信息对用户可理解。

---

## Stage 9：测试、评估与发布（5—8 天）

任务：

- 单元测试；
- API 集成测试；
- 面试状态机测试；
- RAG 检索评估；
- Prompt 回归测试；
- 权限隔离测试；
- E2E 测试；
- 模型超时和失败恢复测试；
- Docker Compose 启动验证；
- README 和使用文档。

完成标准：

- 核心流程自动化测试通过；
- 跨用户检索泄漏为 0；
- 模型失败不破坏会话；
- Docker Compose 可一键启动；
- Prompt 和模型版本可追踪；
- 可以完成一次完整模拟面试。

---

## 10. 时间预估

### 全职开发

- 最小闭环 MVP：5—7 周
- 完整 Phase 1：8—11 周

### 兼职开发

- 最小闭环 MVP：8—12 周
- 完整 Phase 1：12—18 周

最小闭环优先顺序：

```text
简历与 JD 解析
    ↓
Interview Agent
    ↓
文字面试状态机
    ↓
Evaluation Agent
    ↓
复盘报告
```

RAG、长期进度和复杂前端可以在闭环跑通后增强。

---

## 11. 测试与评估指标

### 11.1 解析质量

- 简历字段提取准确率；
- 项目遗漏率；
- 项目事实幻觉率；
- JD 必备技能识别准确率；
- 来源映射正确率。

### 11.2 面试质量

- 问题与 JD 相关性；
- 问题与简历相关性；
- 问题重复率；
- 难度合适度；
- 追问合理性；
- 面试完成率。

### 11.3 评价质量

- 与人工评分相关性；
- 重复评分稳定性；
- 技术错误识别率；
- 遗漏点识别率；
- 错误建议率；
- 经历幻觉率。

### 11.4 RAG 质量

- Recall@K；
- MRR；
- nDCG；
- 引用正确率；
- 无答案拒答率；
- 跨用户泄漏率，目标为 0。

### 11.5 工程指标

- 首 Token 延迟；
- 完整响应延迟；
- 结构化输出成功率；
- 模型重试率；
- 单场面试 Token 成本；
- 服务错误率。

---

## 12. 主要风险与应对

### 12.1 LLM 编造用户经历

应对：

- 建立证据映射；
- 项目问题强制检索；
- 无资料时明确说明未知；
- Evaluation Agent 检查回答与资料一致性。

### 12.2 评分不稳定

应对：

- 固定 Rubric；
- 固定关键点；
- 降低温度；
- 保存 Prompt 和模型版本；
- 建立标准回答回归集。

### 12.3 上下文过长

应对：

- 只注入当前问题所需信息；
- 历史内容结构化摘要；
- RAG 按需检索；
- 设置 Token 预算；
- 不重放全部聊天记录。

### 12.4 题目重复或追问失控

应对：

- 题目指纹；
- 已问题目集合；
- 最大追问次数；
- 状态机控制；
- Interview Agent 只返回有限动作。

### 12.5 范围膨胀

应对：

- Phase 1 只做文字；
- 只保留两个 Agent；
- 先支持一个主要岗位；
- 不提前拆微服务；
- 每个阶段设置明确验收标准。

### 12.6 用户隐私

应对：

- 文件默认私有；
- API Key 加密或仅通过环境变量配置；
- 日志脱敏；
- 支持删除全部数据；
- 不将用户资料用于公共模型训练；
- 检索必须包含用户权限过滤。

---

## 13. 版本路线

### v0.1

- 简历和 JD 上传；
- 结构化解析；
- 基础差距分析。

### v0.2

- Interview Agent；
- 面试计划；
- 文字模拟；
- 动态追问。

### v0.3

- Evaluation Agent；
- 单题评分；
- 改进回答；
- 面试复盘。

### v0.4

- 项目资料 RAG；
- 引用来源；
- 项目深挖。

### v0.5

- 历史进度；
- 薄弱项；
- 自适应题目。

### v1.0

- 完整文字面试闭环；
- 稳定部署；
- 完整测试；
- 用户数据管理；
- 可作为求职作品集公开展示。

---

## 14. 立即行动清单

1. 创建仓库 `interview-copilot-agent`。
2. 初始化 `backend/` 与 `frontend/`。
3. 定义七个核心 Pydantic Schema。
4. 搭建 FastAPI、PostgreSQL、pgvector 和 Alembic。
5. 完成简历与 JD 上传和解析。
6. 实现 Interview Agent 最小版本。
7. 实现文字面试状态机。
8. 实现 Evaluation Agent 最小版本。
9. 准备 20—30 条 AI/智能体应用开发面试测试样例。
10. 先跑通完整闭环，再增加 RAG 和长期记忆。
