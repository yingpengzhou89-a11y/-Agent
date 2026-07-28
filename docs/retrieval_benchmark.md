# 知识库检索评测集

这是面向个人资料的离线 RAG 回归工具。每个样例由一个问题，以及该问题应命中的文档名或片段 ID 组成；它不调用 LLM，因此在更换 FTS、n-gram、Embedding 或 Rerank 策略后可稳定对比。

复制 `backend/benchmarks/retrieval_cases.example.json` 为本地文件，将 `expected_source_names` 改为你已经上传的资料文件名。需要精确到某一片段时，可将检索结果中显示的片段 ID 写入 `expected_chunk_ids`。

```powershell
cd backend
python scripts/run_retrieval_benchmark.py --user-id <你的用户ID> --dataset benchmarks/retrieval_cases.local.json --top-k 5
```

输出指标：

- `Recall@K`：期望引用中被 Top K 召回的比例；
- `MRR`：第一个正确引用越靠前越高；
- `nDCG@K`：考虑正确引用排序位置的归一化分数；
- `citation_correct_rate`：所有展示引用中、被标注为正确的比例；
- `zero_result_rate`：没有任何候选结果的问题占比。

建议先积累 10—20 个覆盖项目架构、技术选型、职责边界和结果指标的问题；每次调整检索策略后运行同一个数据集，并记录指标变化。
