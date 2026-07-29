import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react'
import { ApiRequestError, api } from './api'
import type { DocumentRecord, Evaluation, KnowledgeQuality, KnowledgeSearchResponse, Match, Plan, Session, User } from './types'

type Tab = 'dashboard' | 'materials' | 'match' | 'interview' | 'knowledge' | 'progress'

const tabs: Array<[Tab, string]> = [
  ['dashboard', '总览'], ['materials', '简历与 JD'], ['match', '岗位匹配'],
  ['interview', '模拟面试'], ['knowledge', '项目知识库'], ['progress', '训练进度'],
]

const jobTemplates = [
  {
    id: 'ai-app-junior', title: 'AI 应用开发工程师（初级）',
    text: '岗位：AI 应用开发工程师（初级）\n职责：使用 Python 开发 LLM、RAG 与 Agent 应用；完成 API 集成、提示词设计、评估与部署。\n要求：Python、FastAPI、SQL、Git 基础扎实；理解大语言模型、向量检索、RAG 和工具调用；能清晰介绍个人项目。\n加分：LangChain/LangGraph、PostgreSQL/pgvector、Docker、React。\n级别：初级。',
  },
  {
    id: 'rag-engineer', title: 'RAG / LLM 应用工程师',
    text: '岗位：RAG / LLM 应用工程师\n职责：建设文档解析、向量检索、混合召回、RAG 评估与大模型应用服务。\n要求：Python、FastAPI、PostgreSQL、Embedding、向量数据库；理解 chunking、召回、重排序、幻觉控制和离线评估。\n加分：LangChain/LangGraph、pgvector、Docker、可观测性。\n级别：中级。',
  },
  {
    id: 'python-backend', title: 'Python 后端开发工程师',
    text: '岗位：Python 后端开发工程师\n职责：设计并开发稳定的 Web API、异步任务和数据服务，参与数据库设计、测试及部署。\n要求：Python、FastAPI 或 Django、PostgreSQL、Redis、RESTful API、单元测试、Git。\n加分：Docker、消息队列、性能优化、云服务经验。\n级别：初级。',
  },
] as const

function App() {
  const [tab, setTab] = useState<Tab>('dashboard')
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('interview-copilot-user')
    return saved ? JSON.parse(saved) : null
  })
  const [notice, setNotice] = useState('')
  const [ids, setIds] = useState(() => JSON.parse(localStorage.getItem('interview-copilot-ids') ?? '{}') as Record<string, string>)

  const saveIds = (next: Record<string, string>) => {
    setIds(next)
    localStorage.setItem('interview-copilot-ids', JSON.stringify(next))
  }
  const show = (message: string) => setNotice(message)
  const requireUser = () => {
    if (!user) throw new Error('请先在总览中创建本地用户')
    return user.id
  }

  const createUser = async (displayName: string) => {
    const created = await api<User>('/api/v1/users', { method: 'POST', body: JSON.stringify({ display_name: displayName }) })
    localStorage.setItem('interview-copilot-user', JSON.stringify(created))
    setUser(created)
    show(`已创建用户：${created.display_name}`)
  }

  return <div className="shell">
    <aside>
      <div className="brand"><span>IC</span><div>Interview<br /><b>Copilot</b></div></div>
      <nav>{tabs.map(([key, label]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}</nav>
      <div className="identity">{user ? <>本地用户<br /><b>{user.display_name}</b></> : '尚未创建本地用户'}</div>
    </aside>
    <main>
      <header><div><p className="eyebrow">AI 应用开发 · 文字模拟训练</p><h1>{tabs.find(([key]) => key === tab)?.[1]}</h1></div><span className="health">● 服务已连接</span></header>
      {notice && <div className="notice">{notice}<button onClick={() => setNotice('')}>×</button></div>}
      {tab === 'dashboard' && <Dashboard user={user} onCreate={createUser} userId={user?.id} show={show} />}
      {tab === 'materials' && <Materials userId={user?.id} ids={ids} saveIds={saveIds} show={show} requireUser={requireUser} />}
      {tab === 'match' && <MatchPanel userId={user?.id} ids={ids} saveIds={saveIds} show={show} requireUser={requireUser} />}
      {tab === 'interview' && <InterviewPanel userId={user?.id} ids={ids} saveIds={saveIds} show={show} requireUser={requireUser} />}
      {tab === 'knowledge' && <KnowledgePanel userId={user?.id} show={show} requireUser={requireUser} />}
      {tab === 'progress' && <ProgressPanel userId={user?.id} show={show} />}
    </main>
  </div>
}

function Dashboard({ user, onCreate, userId, show }: { user: User | null; onCreate: (name: string) => Promise<void>; userId?: string; show: (s: string) => void }) {
  const [name, setName] = useState('本地求职者')
  const [overview, setOverview] = useState<{ completed_interviews: number; evaluated_answers: number; weakest_topics: string[] } | null>(null)
  useEffect(() => { if (userId) api<typeof overview>('/api/v1/progress/overview', {}, userId).then(setOverview).catch(() => undefined) }, [userId])
  return <section className="stack">
    {!user ? <div className="card hero"><h2>开始你的第一场个性化模拟</h2><p>先创建一个仅保存在本地的用户身份，再导入简历和目标 JD。</p><form onSubmit={(e) => { e.preventDefault(); onCreate(name).catch(e => show(e.message)) }}><input value={name} onChange={e => setName(e.target.value)} /><button className="primary">创建本地用户</button></form></div> : <>
      <div className="grid three"><Metric label="已完成面试" value={overview?.completed_interviews ?? 0} /><Metric label="已评价回答" value={overview?.evaluated_answers ?? 0} /><Metric label="当前薄弱主题" value={overview?.weakest_topics?.length ?? 0} /></div>
      <div className="card"><h2>训练路径</h2><ol className="path"><li>导入简历与 JD，生成结构化画像</li><li>检查能力差距，确认复习优先级</li><li>生成计划，完成文字模拟与复盘</li></ol></div>
    </>}
  </section>
}

function Materials({ userId, ids, saveIds, show, requireUser }: PanelProps) {
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [roleId, setRoleId] = useState<(typeof jobTemplates)[number]['id'] | 'custom'>('ai-app-junior')
  const [customJobText, setCustomJobText] = useState('')
  const [customJobTitle, setCustomJobTitle] = useState('')
  const selectedRole = jobTemplates.find(role => role.id === roleId) ?? jobTemplates[0]
  const uploadResume = async () => {
    if (!resumeFile) throw new Error('请选择 PDF、DOCX、Markdown 或 TXT 格式的简历')
    const id = requireUser(); const form = new FormData(); form.append('file', resumeFile); form.append('name', resumeFile.name.replace(/\.[^.]+$/, ''))
    const result = await api<DocumentRecord>('/api/v1/resumes/upload', { method: 'POST', body: form }, id)
    saveIds({ ...ids, resumeId: result.id })
    try {
      await api(`/api/v1/resumes/${result.id}/analyze`, { method: 'POST' }, id)
      show('简历已上传、解析并设为当前版本')
    } catch (error) {
      show(`简历文件已上传，但结构化分析失败：${error instanceof Error ? error.message : '请检查模型配置'}`)
    }
  }
  const chooseJob = async () => {
    const id = requireUser()
    const isCustom = roleId === 'custom'
    const title = isCustom ? customJobTitle.trim() : selectedRole.title
    const rawText = isCustom ? customJobText.trim() : selectedRole.text
    if (!title || !rawText) throw new Error('请先补充自定义岗位名称和职位描述')
    const result = await api<DocumentRecord>('/api/v1/jobs', { method: 'POST', body: JSON.stringify({ title, raw_text: rawText, is_current: true }) }, id)
    await api(`/api/v1/jobs/${result.id}/analyze`, { method: 'POST' }, id)
    saveIds({ ...ids, jobId: result.id }); show(`已选择并解析：${title}`)
  }
  const isCustom = roleId === 'custom'
  return <section className="grid two"><div className="card"><h2>上传简历</h2><p>请上传原始简历，系统会提取文本后再生成结构化候选人画像。</p><input type="file" accept=".pdf,.docx,.md,.txt" onChange={(e: ChangeEvent<HTMLInputElement>) => setResumeFile(e.target.files?.[0] ?? null)} /><button className="primary" disabled={!resumeFile} onClick={() => uploadResume().catch(e => show(e.message))}>上传并解析简历</button><small>{ids.resumeId ? '已存在当前简历，可重新上传覆盖' : '支持 PDF、DOCX、Markdown 与 TXT'}</small></div><div className="card"><h2>选择目标岗位</h2><p>先使用岗位模板训练；只有实际投递特定岗位时，才需要补充自定义 JD。</p><select value={roleId} onChange={e => setRoleId(e.target.value as typeof roleId)}>{jobTemplates.map(role => <option value={role.id} key={role.id}>{role.title}</option>)}<option value="custom">自定义岗位 / 粘贴 JD</option></select>{isCustom ? <><input value={customJobTitle} onChange={e => setCustomJobTitle(e.target.value)} placeholder="岗位名称" /><textarea value={customJobText} onChange={e => setCustomJobText(e.target.value)} placeholder="粘贴具体职位描述…" /></> : <p className="template-preview">{selectedRole.text}</p>}<button className="primary" onClick={() => chooseJob().catch(e => show(e.message))}>确认目标岗位并解析</button><small>{ids.jobId ? '已设为当前目标岗位' : '请选择一个岗位模板'}</small></div></section>
}

function MatchPanel({ userId, ids, saveIds, show, requireUser }: PanelProps) {
  const [match, setMatch] = useState<Match | null>(null)
  const run = async () => { const result = await api<Match>('/api/v1/matches', { method: 'POST', body: JSON.stringify({ resume_id: ids.resumeId, job_id: ids.jobId }) }, requireUser()); setMatch(result); saveIds({ ...ids, matchId: result.id }); show('已生成能力差距报告') }
  return <section className="stack"><div className="card hero"><h2>岗位匹配不是录取预测</h2><p>它只用于安排你的面试准备优先级，并能展示可复算的规则与证据。</p><button className="primary" disabled={!ids.resumeId || !ids.jobId} onClick={() => run().catch(e => show(e.message))}>分析当前简历与 JD</button></div>{match && <><div className="grid two"><Metric label="准备指数" value={`${match.report.readiness_index}/100`} /><div className="card"><h3>优先复习</h3><Tags items={match.report.priority_topics} /><h3>证据不足</h3><Tags items={match.report.evidence_gaps} /></div></div><div className="card"><h3>可解释匹配规则</h3><p>{match.report.matching_rule_version}：必备技能 {Math.round(match.report.weight_config.must_have * 100)}% · 加分技能 {Math.round(match.report.weight_config.nice_to_have * 100)}% · 项目证据 {Math.round(match.report.weight_config.project_evidence * 100)}%</p><p>覆盖率：必备 {Math.round(match.report.score_breakdown.must_have_score * 100)}% · 加分 {Math.round(match.report.score_breakdown.nice_to_have_score * 100)}% · 项目证据 {Math.round(match.report.score_breakdown.project_evidence_score * 100)}%</p><h3>逐项判定</h3><ul className="path">{match.report.skill_coverage.map(item => <li key={`${item.requirement}-${item.skill}`}><b>{item.skill}</b> · {item.status === 'covered' ? '已覆盖' : item.status === 'missing' ? '缺失' : '证据不足'}：{item.reason}{item.evidence_refs.length ? `（来源：${item.evidence_refs.map(ref => ref.source_name).join('、')}）` : ''}</li>)}</ul></div></>}</section>
}

function InterviewPanel({ userId, ids, saveIds, show, requireUser }: PanelProps) {
  const [plan, setPlan] = useState<Plan | null>(null); const [session, setSession] = useState<Session | null>(null); const [question, setQuestion] = useState(''); const [questionId, setQuestionId] = useState(''); const [questionSources, setQuestionSources] = useState<Array<{ source_name: string; quote: string }>>([]); const [answer, setAnswer] = useState(''); const [evaluation, setEvaluation] = useState<Evaluation | null>(null); const [reportData, setReportData] = useState<{ summary: { overall_score: number; evaluated_question_count: number; strong_skills: string[]; weak_topics: string[]; dimension_scores: Record<string, number>; average_confidence?: number; low_confidence_answer_count?: number; manual_review_recommended?: boolean }; weak_topics: string[]; recommended_actions: string[] } | null>(null)
  const pendingEvaluation = session?.status === 'ANSWER_SAVED' || session?.status === 'EVALUATING'
  const createPlan = async () => { const p = await api<Plan>('/api/v1/interview-plans', { method: 'POST', body: JSON.stringify({ resume_id: ids.resumeId, job_id: ids.jobId }) }, requireUser()); const nextIds: Record<string, string> = { ...ids, planId: p.id }; delete nextIds.sessionId; setPlan(p); setSession(null); setQuestion(''); setAnswer(''); setEvaluation(null); setReportData(null); saveIds(nextIds); show('新面试计划已生成，可以开始一场新的模拟面试') }
  const loadQuestion = async (sessionId = session?.id) => { if (!sessionId) return; const q = await api<{ id: string; question_text: string; source_refs: Array<{ source_name: string; quote: string }> }>(`/api/v1/interviews/${sessionId}/question`, {}, requireUser()); setQuestionId(q.id); setQuestionSources(q.source_refs); setQuestion(q.question_text); setAnswer(''); setEvaluation(null) }
  useEffect(() => { if (userId && ids.planId) api<Plan>(`/api/v1/interview-plans/${ids.planId}`, {}, userId).then(setPlan).catch(() => undefined) }, [userId, ids.planId])
  useEffect(() => { if (userId && ids.sessionId) api<Session>(`/api/v1/interviews/${ids.sessionId}`, {}, userId).then(s => { setSession(s); if (s.status !== 'COMPLETED') return loadQuestion(s.id); setQuestion(''); return api<NonNullable<typeof reportData>>(`/api/v1/interviews/${s.id}/report`, {}, userId).then(setReportData).catch(() => undefined) }).catch(() => undefined) }, [userId, ids.sessionId])
  const start = async () => { const activePlanId = plan?.id ?? ids.planId; if (!activePlanId) throw new Error('请先生成面试计划'); if (session && session.plan_id === activePlanId) { if (session.status === 'COMPLETED') return show('本场面试已完成，请先生成新计划再开始下一场'); if (session.status !== 'CREATED') return loadQuestion(session.id) } const s = await api<Session>('/api/v1/interviews', { method: 'POST', body: JSON.stringify({ plan_id: activePlanId }) }, requireUser()); const active = await api<Session>(`/api/v1/interviews/${s.id}/start`, { method: 'POST' }, requireUser()); setSession(active); saveIds({ ...ids, sessionId: s.id }); await loadQuestion(s.id) }
  const submit = async () => { if (!session) return; if (!pendingEvaluation) { const storageKey = `interview-copilot-answer-key:${session.id}:${questionId}`; const idempotencyKey = localStorage.getItem(storageKey) ?? crypto.randomUUID(); localStorage.setItem(storageKey, idempotencyKey); try { await api<{ id: string }>(`/api/v1/interviews/${session.id}/answers`, { method: 'POST', body: JSON.stringify({ answer_text: answer, idempotency_key: idempotencyKey }) }, requireUser()); localStorage.removeItem(storageKey) } catch (error) { if (!(error instanceof ApiRequestError) || error.status !== 409) throw error; localStorage.removeItem(storageKey) } } const ev = await api<Evaluation>(`/api/v1/interviews/${session.id}/evaluate`, { method: 'POST' }, requireUser()); const refreshed = await api<Session>(`/api/v1/interviews/${session.id}`, {}, requireUser()); setEvaluation(ev); setSession(refreshed); if (refreshed.status === 'COMPLETED') { setQuestion(''); setQuestionId(''); show(`本场面试已完成，最后一题得分 ${ev.overall_score}/100`) } else show(`已评分：${ev.overall_score}/100`) }
  const report = async () => { if (!session) return; const r = await api<NonNullable<typeof reportData>>(`/api/v1/interviews/${session.id}/report/regenerate`, { method: 'POST' }, requireUser()); setReportData(r); show(`整场报告已生成，总分 ${r.summary.overall_score}`) }
  return <section className="stack"><div className="card actions"><div><h2>面试控制台</h2><p>计划由 Interview Agent 生成；刷新页面后会恢复到已保存的会话。</p></div><div><button className="secondary" disabled={!ids.resumeId || !ids.jobId} onClick={() => createPlan().catch(e => show(e.message))}>生成计划</button><button className="primary" disabled={!plan && !ids.planId} onClick={() => start().catch(e => show(e.message))}>{session ? '继续面试' : '开始面试'}</button></div></div>{session?.status === 'COMPLETED' && <div className="card hero"><h2>本场面试已完成</h2><p>所有计划题与追问均已结束，现在可以生成整场复盘报告。</p><button className="primary" onClick={() => report().catch(e => show(e.message))}>{reportData ? '重新生成整场报告' : '生成整场报告'}</button></div>}{reportData && <div className="card stack"><div className="grid three"><Metric label="总体评分" value={`${reportData.summary.overall_score}/100`} /><Metric label="已评价题数" value={reportData.summary.evaluated_question_count} /><Metric label="薄弱主题" value={reportData.weak_topics.length} /></div><h2>整场面试报告</h2>{reportData.summary.manual_review_recommended && <p>本场有 {reportData.summary.low_confidence_answer_count} 题评价置信度偏低，建议结合原回答和资料进行人工复核。</p>}<h3>优势能力</h3><Tags items={reportData.summary.strong_skills} /><h3>优先复习</h3><Tags items={reportData.weak_topics} /><h3>下一次训练建议</h3><ul className="path">{reportData.recommended_actions.map(action => <li key={action}>{action}</li>)}</ul></div>}{question && <div className="card question"><span className="pill">当前问题</span><h2>{question}</h2>{questionSources.length > 0 && <div className="stack"><small>本题引用的项目资料（评价时将作为事实边界）：</small>{questionSources.map((source, index) => <p className="muted" key={`${source.source_name}-${index}`}>引用 [{index + 1}] · {source.source_name} · {source.quote.slice(0, 160)}…</p>)}</div>}<textarea value={answer} disabled={pendingEvaluation} onChange={e => setAnswer(e.target.value)} placeholder={pendingEvaluation ? '回答已保存，正在等待评价…' : '输入你的回答，尽量结构化表达…'} /><button className="primary" disabled={!pendingEvaluation && !answer} onClick={() => submit().catch(e => show(e.message))}>{pendingEvaluation ? '重新尝试评价' : '提交并评价'}</button></div>}{evaluation && <div className="card evaluation"><div className="score">{evaluation.overall_score}</div><div><h2>本题复盘</h2>{evaluation.confidence < 0.6 && <p>本题模型评价置信度偏低，建议结合原回答与资料人工复核。</p>}<Tags items={evaluation.strengths} /><p>{evaluation.improved_answer}</p>{session?.status !== 'COMPLETED' && <button className="secondary" onClick={() => loadQuestion().catch(e => show(e.message))}>下一题</button>}<button className="secondary" onClick={() => report().catch(e => show(e.message))}>生成报告</button></div></div>}</section>
}

function KnowledgePanel({ userId, show, requireUser }: Pick<PanelProps, 'userId' | 'show' | 'requireUser'>) {
  const [file, setFile] = useState<File | null>(null); const [searchData, setSearchData] = useState<KnowledgeSearchResponse | null>(null); const [quality, setQuality] = useState<KnowledgeQuality | null>(null); const [embedding, setEmbedding] = useState<{ configured: boolean; model: string; dimensions: number; indexed_document_count: number; pending_document_count: number } | null>(null); const [feedback, setFeedback] = useState<Record<string, string>>({}); const [query, setQuery] = useState('')
  const upload = async () => { if (!file) return; const form = new FormData(); form.append('file', file); form.append('source_type', 'project_docs'); await api('/api/v1/knowledge/documents', { method: 'POST', body: form }, requireUser()); show('文档已上传；如已配置 Embedding，可在 Swagger 中调用 reindex 建立向量索引') }
  const loadQuality = async () => { if (userId) setQuality(await api<KnowledgeQuality>('/api/v1/knowledge/quality', {}, userId)) }
  const loadEmbedding = async () => { if (userId) setEmbedding(await api<{ configured: boolean; model: string; dimensions: number; indexed_document_count: number; pending_document_count: number }>('/api/v1/knowledge/embedding-status', {}, userId)) }
  useEffect(() => { loadQuality().catch(() => undefined); loadEmbedding().catch(() => undefined) }, [userId])
  const reindexAll = async () => { const result = await api<{ total_document_count: number; indexed_document_count: number; failed_document_count: number }>('/api/v1/knowledge/documents/rechunk-and-reindex-all', { method: 'POST' }, requireUser()); await loadEmbedding(); show(`重新切分并建立向量完成：${result.indexed_document_count}/${result.total_document_count}，失败 ${result.failed_document_count}`) }
  const search = async () => { const data = await api<KnowledgeSearchResponse>('/api/v1/knowledge/search', { method: 'POST', body: JSON.stringify({ query }) }, requireUser()); setSearchData(data); setFeedback({}); await loadQuality() }
  const rateCitation = async (chunkId: string, relevance: 'helpful' | 'not_helpful') => { if (!searchData) return; await api(`/api/v1/knowledge/search/${searchData.search_id}/feedback`, { method: 'POST', body: JSON.stringify({ chunk_id: chunkId, relevance }) }, requireUser()); setFeedback({ ...feedback, [chunkId]: relevance }); await loadQuality() }
  return <section className="stack"><div className="card"><h2>项目资料</h2><p>支持 PDF、DOCX、Markdown 与 TXT。所有资料只在当前用户范围内检索。</p><input type="file" accept=".pdf,.docx,.md,.txt" onChange={(e: ChangeEvent<HTMLInputElement>) => setFile(e.target.files?.[0] ?? null)} /><button className="primary" disabled={!file} onClick={() => upload().catch(e => show(e.message))}>上传项目资料</button><p className="muted">Embedding：{embedding?.configured ? `${embedding.model}（${embedding.dimensions} 维）` : '未配置'} · 已索引 {embedding?.indexed_document_count ?? 0} 篇 · 待建立 {embedding?.pending_document_count ?? 0} 篇</p><button className="secondary" disabled={!embedding?.configured || !((embedding?.indexed_document_count ?? 0) + (embedding?.pending_document_count ?? 0))} onClick={() => reindexAll().catch(e => show(e.message))}>重新切分并重建全部索引</button></div><div className="grid three"> <Metric label="检索次数" value={quality?.search_count ?? 0} /><Metric label="零结果率" value={`${Math.round((quality?.zero_result_rate ?? 0) * 100)}%`} /><Metric label="引用有帮助率" value={quality?.helpful_rate == null ? '待反馈' : `${Math.round(quality.helpful_rate * 100)}%`} /></div><div className="card"><h2>检索你的资料</h2><div className="inline"><input value={query} onChange={e => setQuery(e.target.value)} placeholder="例如：项目中的 RAG 评估指标" /><button className="secondary" disabled={!query} onClick={() => search().catch(e => show(e.message))}>检索</button></div>{searchData && <p className="muted">召回：{String(searchData.retrieval_config.lexical_retriever)} · 向量检索：{searchData.retrieval_config.vector_retriever ? '已启用' : '未配置（语义相近的同义改写仍需配置 Embedding）'} · 融合：RRF · 平均历史耗时 {Math.round(quality?.average_latency_ms ?? 0)}ms</p>}{searchData?.results.map((r, i) => <article className="result" key={r.chunk_id}><b>引用 [{i + 1}] · {r.source_name}</b><span>{r.score.toFixed(3)}</span><p>{r.content}</p><small>来源类型：{r.source_type} · 片段：{r.chunk_id.slice(0, 8)}</small><div className="inline"><button className="secondary" disabled={feedback[r.chunk_id] === 'helpful'} onClick={() => rateCitation(r.chunk_id, 'helpful').catch(e => show(e.message))}>有帮助</button><button className="secondary" disabled={feedback[r.chunk_id] === 'not_helpful'} onClick={() => rateCitation(r.chunk_id, 'not_helpful').catch(e => show(e.message))}>不相关</button></div></article>)}</div></section>
}

function ProgressPanel({ userId, show }: Pick<PanelProps, 'userId' | 'show'>) {
  const [data, setData] = useState<{ weakest_topics: string[]; next_reviews: Array<{ skill_name: string; mastery_score: number; next_review_at: string; consecutive_correct_count: number; consecutive_incorrect_count: number }> } | null>(null)
  useEffect(() => { if (userId) api<typeof data>('/api/v1/progress/overview', {}, userId).then(setData).catch(e => show(e.message)) }, [userId])
  return <section className="grid two"><div className="card"><h2>薄弱主题</h2><Tags items={data?.weakest_topics ?? []} /></div><div className="card"><h2>动态复习计划</h2>{data?.next_reviews.map(item => <div className="review" key={item.skill_name}><b>{item.skill_name}</b><span>{item.mastery_score.toFixed(0)} 分 · {new Date(item.next_review_at).toLocaleDateString()} · 连续答对 {item.consecutive_correct_count} 次 / 答错 {item.consecutive_incorrect_count} 次</span></div>)}</div></section>
}

type PanelProps = { userId?: string; ids: Record<string, string>; saveIds: (x: Record<string, string>) => void; show: (s: string) => void; requireUser: () => string }
function Metric({ label, value }: { label: string; value: string | number }) { return <div className="metric"><span>{label}</span><b>{value}</b></div> }
function Tags({ items }: { items: string[] }) { return items.length ? <div className="tags">{items.map(item => <span key={item}>{item}</span>)}</div> : <p className="muted">暂无数据</p> }
export default App
