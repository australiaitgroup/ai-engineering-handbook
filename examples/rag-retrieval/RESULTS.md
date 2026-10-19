# RAG 检索实验：完整结果

> 确定性教学数据；人工向量；无模型、无生产性能结论。

| Question | Gold | Dense top 1 | Lexical top 1 | RRF top 3 | Policy selected |
|---|---|---|---|---|---|
| Q1 | D2 | D1 | D2 | D1, D2, D4 | D2 |
| Q2 | D4 | D4 | D4 | D4, D1, D7 | D4 |
| Q3 | D3 | D3 | D3 | D3, D2, D1 | D3 |
| Q4 | D5 | D5 | D5 | D5, D1, D2 | D5 |
| Q5 | D6 | D6 | D6 | D6, D1, D4 | D6 |
| Q6 | none | D3 | D3 | D3, D4, D2 | abstain |
| Q7 | none | D1 | D4 | D1, D4, D2 | abstain |

## 逐题问题、答案与证据

### Q1

How do I resolve AtlasDesk v2 export error E1042?

**Evidence:** D2

AtlasDesk v2 export error E1042: split exports above 5000 rows into batches of at most 5000 rows. Increasing the timeout does not resolve this version's row limit.

Candidate loss: False; policy correct: True.

### Q2

What should I do about HarborCRM v2 export error E1042?

**Evidence:** D4

HarborCRM v2 export error E1042: reconnect the storage destination. AtlasDesk instructions do not apply to HarborCRM.

Candidate loss: False; policy correct: True.

### Q3

Who can fix AtlasDesk v2 sign-in error E2041?

**Evidence:** D3

AtlasDesk v2 sign-in error E2041: ask the workspace administrator to renew the expired SSO certificate, then retry sign-in.

Candidate loss: False; policy correct: True.

### Q4

Should I pay the AtlasDesk v2 duplicate invoice INV-204 twice?

**Evidence:** D5

AtlasDesk v2 billing duplicate invoice INV-204: do not pay twice. Give both invoice references to the billing administrator for reconciliation.

Candidate loss: False; policy correct: True.

### Q5

How do I fix AtlasDesk v2 CSV import error I3090?

**Evidence:** D6

AtlasDesk v2 import error I3090: save the CSV file as UTF-8 and include the required customer_id column before retrying the import.

Candidate loss: False; policy correct: True.

### Q6

How do I enable biometric login in AtlasDesk v9?

**Evidence:** none

INSUFFICIENT_EVIDENCE

Candidate loss: False; policy correct: True.

### Q7

How do I fix AtlasDesk v2 export error E9999?

**Evidence:** none

INSUFFICIENT_EVIDENCE

Candidate loss: False; policy correct: True.

## 结果口径

{"answerable_questions": 5, "dense_hit_at_1": 4, "rrf_recall_at_3": 5, "policy_correct_answerable": 5, "unanswerable_questions": 2}

Hit@1 只统计有答案问题；Recall@3 统计正确文档是否进入候选。拒答题单列。人工规则无法挽救已被候选裁剪移除的证据；这些计数不代表真实 embedding 或神经重排性能。
