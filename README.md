# AI 工程架构实战手册 · JR Academy

从 RAG 检索不准，到 MCP 工具权限，再到 Agent 断点恢复：用一个客服知识助手，讲清楚证据、调用与状态。

[JR Academy 匠人学院](https://jracademy.ai/?utm_source=github&utm_medium=referral&utm_campaign=ai_engineering_handbook&utm_content=long_readme) · [English overview](README.en.md)

> 本文是可连续阅读的完整长文。公司、产品、业务记录和测试问题均为虚构。检索使用人工教学向量，MCP 使用离线模拟，恢复实验实际结束并重启本地子进程。没有调用模型 API 或真实业务服务。MCP 参考固定为 2025-11-25，不宣称是最新版本。整理日期：2026-10-19。

我们建议先拆开失败链路，再决定是否换模型。客服助手引用错文档，可能是召回或版本管理的问题；工具调用失败，可能是初始化或权限的问题；任务重启后重复写入，则涉及副作用和执行状态。把这些情况都归到“模型不够聪明”，会让排查方向越来越偏。

本文从同一个虚构业务出发，把三套完整数据、代码和结果放在一页里。你可以直接读，也可以按步骤在本地复现。原来的示例文件仍然保留，方便下载，但不需要来回打开多个文件才能理解正文。

## 直接看三个完整成果

| 链路 | 具体成果 | 实验中实际发生了什么 |
|---|---|---|
| 知识检索 | 七个问题的排序、证据与完整摘录 | Q1 首先找到旧版说明，保留候选后选中当前证据；两道缺证据问题拒答 |
| 工具调用 | 初始化、工具发现、调用报文及七个策略场景 | 一个只读查询允许执行，六种错误在工具执行前被拒绝 |
| 长任务恢复 | 两种恢复方式的完整轨迹、保存记录与回执 | 同一崩溃位置，普通重试保存两次，稳定操作键恢复保存一次 |

三份成果分别回答：答案依据从哪里来、谁允许工具执行、动作成功后怎样记账。缺少任何一个，系统都可能在局部看起来正常，却在完整业务路径上失败。

## 适合谁

本文适合能读基础 Python、JSON 和 HTTP 的开发者，也适合正在从 AI 工具使用转向 AI 应用开发的学习者。没有编程基础的读者可以先看场景、表格和结果，代码用于核对过程。

三套示例只需要 Python 3.9+ 标准库，不需要依赖安装、API key、模型下载、GPU、Docker、向量数据库或后台服务。已有完整结果也随正文展示，运行不是阅读前置条件。

正在处理知识库错误，可以先看第二部分；正在排查 MCP 连接，可以先看第三部分；正在设计重试，可以先看第四部分。第五部分把它们放回同一条用户路径。

## 一、先定义客服助手应该交付什么

虚构产品 AtlasDesk 提供数据导出、账号登录、账单和 CSV 导入功能。知识库保存着不同版本的说明。另一个产品 HarborCRM 恰好使用相同导出错误码，这让“只凭错误码找到文章”变得不可靠。

使用 AtlasDesk v2 的用户遇到 E1042。助手需要找到当前版本的有效说明，获得读取知识文章的权限，再把核对过的摘要保存到独立服务。完整有用的成果是一段带依据的处理建议，以及一条可以核对的保存回执。

| 需要确认的事实 | 依据 | 不能用什么代替 |
|---|---|---|
| 文档适用于当前问题 | 产品、版本、状态、错误码与正文 | 相似度高，或者标题接近 |
| 当前调用者有权读文章 | 已验证身份、目标服务、scope 与策略 | 能连接服务，或者知道 session id |
| 同一次保存已经发生 | 稳定操作键、服务回执与工作流状态 | 客户端没收到响应，或者页面显示失败 |

本例固定摘要为：

> AtlasDesk v2 E1042: use batches of at most 5000 rows.

这不是模型生成的客服回答，而是从虚构资料中得到的确定性输出。这样可以把重点放在工程链路，避免把答案措辞变化混进比较。

### 1.1 把输入、决策和副作用分开

输入包括问题正文、已知产品版本、允许访问的知识文档和身份上下文。决策包括检索排序、候选筛选、工具授权和恢复位置。副作用指保存、发送、删除等会改变外部状态的动作。

一段自然语言解释无法证明外部状态。助手可以正确说出处理方法，却没有保存成功；也可以保存成功，却在本地记录完成前崩溃。验收要分别检查内容与动作。

用户输入、管理员维护的元数据、工具返回内容和模型建议，也不是同一种来源。文档里写着“忽略前面的规则”，只是待阅读材料中的文字，不能因此获得更高权限。

### 1.2 记录中间过程，才能从症状找到原因

适合排查的记录应该说明：原始问题是什么，已知上下文是什么，召回过哪些候选，最终用了哪份证据，工具在哪一层放行，保存返回了什么回执。

只留下最终回答和一行 success 很难排查。回答无法说明正确文档是否进过候选；success 也可能只表示某个请求被接受。后面三套实验都会保留中间状态。

## 二、RAG 检索不准：相似资料怎样变成错误答案

RAG 先检索资料，再用资料支持回答。被检索到的片段必须支持当前问题，不能只是在词语或主题上接近。

AtlasDesk v1 与 v2 都有 E1042，但处理方式不同。v1 的旧方案是延长超时，v2 的当前限制是每批最多 5000 行。HarborCRM 的同码问题指向存储连接。再加上一份 v3 草案，就同时有了版本冲突、同码异产品和未发布能力三个干扰来源。

### 2.1 七份文档及其回答资格

| 文档 | 产品与版本 | 状态 | 内容 | 用途 |
|---|---|---|---|---|
| D1 | AtlasDesk v1 | archived | E1042：超时改为 120 秒 | 旧版干扰 |
| D2 | AtlasDesk v2 | current | E1042：每批最多 5000 行 | 当前问题正确证据 |
| D3 | AtlasDesk v2 | current | E2041：更新过期 SSO 证书 | 登录问题证据 |
| D4 | HarborCRM v2 | current | E1042：重新连接存储 | 同码异产品 |
| D5 | AtlasDesk v2 | current | INV-204：不要重复付款，核对账单 | 账单问题证据 |
| D6 | AtlasDesk v2 | current | I3090：UTF-8 与 customer_id | 导入问题证据 |
| D7 | AtlasDesk v3 | draft | 自动分页的未发布提议 | 未来版本干扰 |

产品、版本和状态是已给定的结构化字段，不是由模型猜出来的。真实系统中，这些信息可能来自当前工作区、已确认工单或管理员维护的元数据。无法确定版本时，应先补信息，不能偷偷选一个版本套说明。

### 2.2 为什么只改 Prompt 不够

如果候选只有 D1，要求“请准确一些”不会凭空产生 D2。即使模型完全忠实于给定资料，也只能复述错误版本的说明。

如果候选包含 D2，但最终上下文只保留 D1，问题在裁剪或组装。只有上下文已经包含正确证据，回答仍偏离时，才需要继续检查回答是否忠实使用资料。

因此要按证据路径排查：文档是否存在，切分后是否保留适用条件，正确片段是否被召回，是否在过滤或重排时被移除，最后有没有进入回答上下文。

### 2.3 Dense、Lexical、Hybrid 和 Reranker 的区别

| 方法 | 本文实现 | 用来观察 | 不能据此宣称 |
|---|---|---|---|
| Dense retrieval | 人工四维向量的余弦排序 | 相似性可能把旧文档排前面 | 真实 embedding 模型的优劣 |
| Lexical retrieval | 英文 token 集合的交集计数 | 精确产品名、错误码的帮助 | 已实现 BM25 或成熟搜索引擎 |
| Hybrid retrieval | RRF 融合两路排序 | 正确证据是否留在候选 | 混合检索永远更好 |
| Metadata filtering | 产品、版本、状态与错误码规则 | 明确适用条件是否满足 | 已完成租户权限隔离 |
| Neural reranking | 本文未运行 | 只说明其可能的位置 | 已评测 cross-encoder |

词交集不是 BM25，一个 if 条件不是神经重排器，人工向量也不是某个模型的 embedding。把替代实现讲清楚，读者才知道结论可以迁移到哪里。

### 2.4 RRF 计算什么，不计算什么

本例分别对同一批文档做 dense 与 lexical 排序，再把两路的 `1 / (60 + rank)` 相加。rank 从 1 开始，60 是融合常数。最后保留前三个候选。

这里没有直接相加两种不可比的原始分数。融合的是名次，但名次本身仍不理解产品版本。方法背景见 [Microsoft RRF 说明](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)。

融合常数与候选数量不同。前者改变名次分差的影响，后者决定下游还能看到多少证据。把候选数改成 1，可能让正确资料在进入判断前就丢失。

### 2.5 完整数据：文档、问题和评估标签

下面是实际使用的全部数据。问题、文档和答案为英文，解释为中文。向量为人工教学数据。gold_document 只用于计分，不参与候选选择。

```json
{
  "language": "en",
  "fictional": true,
  "vector_provenance": "Hand-authored four-dimensional teaching vectors; not model embeddings. Dimensions loosely represent export, identity, billing and import.",
  "documents": [
    {
      "id": "D1",
      "product": "AtlasDesk",
      "version": "1",
      "status": "archived",
      "text": "AtlasDesk v1 export error E1042: increase the export timeout to 120 seconds. This instruction is archived and must not be applied to v2.",
      "teaching_vector": [
        1,
        0.01,
        0,
        0
      ]
    },
    {
      "id": "D2",
      "product": "AtlasDesk",
      "version": "2",
      "status": "current",
      "text": "AtlasDesk v2 export error E1042: split exports above 5000 rows into batches of at most 5000 rows. Increasing the timeout does not resolve this version's row limit.",
      "teaching_vector": [
        0.9,
        0.3,
        0,
        0
      ]
    },
    {
      "id": "D3",
      "product": "AtlasDesk",
      "version": "2",
      "status": "current",
      "text": "AtlasDesk v2 sign-in error E2041: ask the workspace administrator to renew the expired SSO certificate, then retry sign-in.",
      "teaching_vector": [
        0.05,
        1,
        0,
        0
      ]
    },
    {
      "id": "D4",
      "product": "HarborCRM",
      "version": "2",
      "status": "current",
      "text": "HarborCRM v2 export error E1042: reconnect the storage destination. AtlasDesk instructions do not apply to HarborCRM.",
      "teaching_vector": [
        1,
        0.05,
        0,
        0
      ]
    },
    {
      "id": "D5",
      "product": "AtlasDesk",
      "version": "2",
      "status": "current",
      "text": "AtlasDesk v2 billing duplicate invoice INV-204: do not pay twice. Give both invoice references to the billing administrator for reconciliation.",
      "teaching_vector": [
        0,
        0,
        1,
        0
      ]
    },
    {
      "id": "D6",
      "product": "AtlasDesk",
      "version": "2",
      "status": "current",
      "text": "AtlasDesk v2 import error I3090: save the CSV file as UTF-8 and include the required customer_id column before retrying the import.",
      "teaching_vector": [
        0,
        0,
        0,
        1
      ]
    },
    {
      "id": "D7",
      "product": "AtlasDesk",
      "version": "3",
      "status": "draft",
      "text": "AtlasDesk v3 export error E1042 draft proposal: automatic pagination may remove the manual batch requirement. This feature is not released.",
      "teaching_vector": [
        1,
        0.02,
        0,
        0
      ]
    }
  ],
  "questions": [
    {
      "id": "Q1",
      "question": "How do I resolve AtlasDesk v2 export error E1042?",
      "product": "AtlasDesk",
      "version": "2",
      "teaching_vector": [
        1,
        0,
        0,
        0
      ],
      "gold_document": "D2"
    },
    {
      "id": "Q2",
      "question": "What should I do about HarborCRM v2 export error E1042?",
      "product": "HarborCRM",
      "version": "2",
      "teaching_vector": [
        1,
        0.05,
        0,
        0
      ],
      "gold_document": "D4"
    },
    {
      "id": "Q3",
      "question": "Who can fix AtlasDesk v2 sign-in error E2041?",
      "product": "AtlasDesk",
      "version": "2",
      "teaching_vector": [
        0,
        1,
        0,
        0
      ],
      "gold_document": "D3"
    },
    {
      "id": "Q4",
      "question": "Should I pay the AtlasDesk v2 duplicate invoice INV-204 twice?",
      "product": "AtlasDesk",
      "version": "2",
      "teaching_vector": [
        0,
        0,
        1,
        0
      ],
      "gold_document": "D5"
    },
    {
      "id": "Q5",
      "question": "How do I fix AtlasDesk v2 CSV import error I3090?",
      "product": "AtlasDesk",
      "version": "2",
      "teaching_vector": [
        0,
        0,
        0,
        1
      ],
      "gold_document": "D6"
    },
    {
      "id": "Q6",
      "question": "How do I enable biometric login in AtlasDesk v9?",
      "product": "AtlasDesk",
      "version": "9",
      "teaching_vector": [
        0,
        1,
        0,
        0
      ],
      "gold_document": null
    },
    {
      "id": "Q7",
      "question": "How do I fix AtlasDesk v2 export error E9999?",
      "product": "AtlasDesk",
      "version": "2",
      "teaching_vector": [
        1,
        0,
        0,
        0
      ],
      "gold_document": null
    }
  ]
}
```

### 2.6 完整检索代码

把 JSON 保存为 dataset.json，把下面代码保存为同目录的 run.py，使用 Python 3.9+ 执行。代码只读取本地数据并写派生结果，不访问网络。

```python
"""Offline retrieval teaching experiment. No embedding model, network or generation."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def cosine(a, b):
    return sum(x*y for x, y in zip(a, b)) / (
        math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(x*x for x in b)))


def run():
    data = json.loads((ROOT / "dataset.json").read_text())
    docs = data["documents"]
    results = []
    for q in data["questions"]:
        dense = sorted(docs, key=lambda d: (-cosine(q["teaching_vector"], d["teaching_vector"]), d["id"]))
        lexical = sorted(docs, key=lambda d: (-len(tokens(q["question"]) & tokens(d["text"])), d["id"]))
        ranks = [{d["id"]: i+1 for i, d in enumerate(order)} for order in (dense, lexical)]
        rrf = {d["id"]: sum(1/(60+r[d["id"]]) for r in ranks) for d in docs}
        fused = sorted(docs, key=lambda d: (-rrf[d["id"]], d["id"]))
        candidates = fused[:3]
        # A hand-written metadata policy, NOT a learned reranker; no gold-label access.
        identifiers = set(re.findall(r"\b(?:[ei]\d{4}|inv-\d+)\b", q["question"].lower()))
        eligible = [d for d in candidates if (not identifiers or identifiers <= set(re.findall(r"\b(?:[ei]\d{4}|inv-\d+)\b", d["text"].lower()))) and d["product"] == q["product"]
                    and d["version"] == q["version"] and d["status"] == "current"]
        chosen = eligible[0] if eligible else None
        results.append({
            "id": q["id"], "question": q["question"], "gold_document": q["gold_document"],
            "dense_top3": [d["id"] for d in dense[:3]],
            "lexical_top3": [d["id"] for d in lexical[:3]],
            "rrf_top3": [d["id"] for d in candidates],
            "policy_selected": chosen["id"] if chosen else None,
            "extractive_answer": chosen["text"] if chosen else "INSUFFICIENT_EVIDENCE",
            "dense_hit_at_1": dense[0]["id"] == q["gold_document"],
            "rrf_recall_at_3": q["gold_document"] in [d["id"] for d in candidates],
            "policy_correct": (chosen["id"] if chosen else None) == q["gold_document"],
            "rrf_top1_contains_gold": candidates[0]["id"] == q["gold_document"],
            "candidate_loss": q["gold_document"] is not None and q["gold_document"] not in [d["id"] for d in candidates]
        })
    answerable = [r for r in results if r["gold_document"] is not None]
    report = {"evidence_type": "deterministic_toy_experiment", "embedding_model": None,
              "reranker_model": None, "generated_answers": False,
              "summary": {"answerable_questions": len(answerable),
                          "dense_hit_at_1": sum(r["dense_hit_at_1"] for r in answerable),
                          "rrf_recall_at_3": sum(r["rrf_recall_at_3"] for r in answerable),
                          "policy_correct_answerable": sum(r["policy_correct"] for r in answerable),
                          "unanswerable_questions": len(results)-len(answerable)},
              "results": results}
    (ROOT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    lines = ["# RAG 检索实验：完整结果", "", "> 确定性教学数据；人工向量；无模型、无生产性能结论。", "",
             "| Question | Gold | Dense top 1 | Lexical top 1 | RRF top 3 | Policy selected |", "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f'| {r["id"]} | {r["gold_document"] or "none"} | {r["dense_top3"][0]} | {r["lexical_top3"][0]} | {", ".join(r["rrf_top3"])} | {r["policy_selected"] or "abstain"} |')
    lines += ["", "## 逐题问题、答案与证据", ""]
    for r in results:
        lines += [f'### {r["id"]}', "", r["question"], "", f'**Evidence:** {r["policy_selected"] or "none"}', "", r["extractive_answer"], "",
                  f'Candidate loss: {r["candidate_loss"]}; policy correct: {r["policy_correct"]}.', ""]
    lines += ["## 结果口径", "", json.dumps(report["summary"], ensure_ascii=False), "",
              "Hit@1 只统计有答案问题；Recall@3 统计正确文档是否进入候选。拒答题单列。人工规则无法挽救已被候选裁剪移除的证据；这些计数不代表真实 embedding 或神经重排性能。", ""]
    (ROOT / "RESULTS.md").write_text("\n".join(lines))
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    run()
```

需要仔细看三处：RRF 后才做本例筛选，所以候选损失可见；错误码由明确正则提取，不能处理任意表达；返回整段证据摘录，没有生成式模型。

真实系统的硬权限边界不能依赖这种教学后置规则。本例后置筛选用于观察证据损失，不能作为多租户隔离方案。

### 2.7 七道问题的完整结果

以下是已运行后保存的输入、排序、引用与答案。无需运行即可读完。

| Question | Gold | Dense top 1 | Lexical top 1 | RRF top 3 | Policy selected |
|---|---|---|---|---|---|
| Q1 | D2 | D1 | D2 | D1, D2, D4 | D2 |
| Q2 | D4 | D4 | D4 | D4, D1, D7 | D4 |
| Q3 | D3 | D3 | D3 | D3, D2, D1 | D3 |
| Q4 | D5 | D5 | D5 | D5, D1, D2 | D5 |
| Q5 | D6 | D6 | D6 | D6, D1, D4 | D6 |
| Q6 | none | D3 | D3 | D3, D4, D2 | abstain |
| Q7 | none | D1 | D4 | D1, D4, D2 | abstain |

#### 逐题问题、答案与证据

##### Q1

How do I resolve AtlasDesk v2 export error E1042?

**Evidence:** D2

AtlasDesk v2 export error E1042: split exports above 5000 rows into batches of at most 5000 rows. Increasing the timeout does not resolve this version's row limit.

Candidate loss: False; policy correct: True.

##### Q2

What should I do about HarborCRM v2 export error E1042?

**Evidence:** D4

HarborCRM v2 export error E1042: reconnect the storage destination. AtlasDesk instructions do not apply to HarborCRM.

Candidate loss: False; policy correct: True.

##### Q3

Who can fix AtlasDesk v2 sign-in error E2041?

**Evidence:** D3

AtlasDesk v2 sign-in error E2041: ask the workspace administrator to renew the expired SSO certificate, then retry sign-in.

Candidate loss: False; policy correct: True.

##### Q4

Should I pay the AtlasDesk v2 duplicate invoice INV-204 twice?

**Evidence:** D5

AtlasDesk v2 billing duplicate invoice INV-204: do not pay twice. Give both invoice references to the billing administrator for reconciliation.

Candidate loss: False; policy correct: True.

##### Q5

How do I fix AtlasDesk v2 CSV import error I3090?

**Evidence:** D6

AtlasDesk v2 import error I3090: save the CSV file as UTF-8 and include the required customer_id column before retrying the import.

Candidate loss: False; policy correct: True.

##### Q6

How do I enable biometric login in AtlasDesk v9?

**Evidence:** none

INSUFFICIENT_EVIDENCE

Candidate loss: False; policy correct: True.

##### Q7

How do I fix AtlasDesk v2 export error E9999?

**Evidence:** none

INSUFFICIENT_EVIDENCE

Candidate loss: False; policy correct: True.

#### 结果口径

{"answerable_questions": 5, "dense_hit_at_1": 4, "rrf_recall_at_3": 5, "policy_correct_answerable": 5, "unanswerable_questions": 2}

Hit@1 只统计有答案问题；Recall@3 统计正确文档是否进入候选。拒答题单列。人工规则无法挽救已被候选裁剪移除的证据；这些计数不代表真实 embedding 或神经重排性能。

### 2.8 Q1 为什么最终选对

Q1 的 dense 第一名为 D1，lexical 第一名为 D2，RRF 前三名为 D1、D2、D4。最终选择 D2，是因为产品、版本、current 状态和错误码规则排除了其他候选。

结果来自几项条件共同成立：正确证据确实存在，关键词使它进入候选，候选数量保留它，元数据正确表达适用范围。不能只看最终选对，就写成“RRF 解决了版本问题”。

若只保留 RRF 第一名，D2 已经被裁掉。后面的规则只能在 D1 上工作。这是上下文压缩和候选裁剪需要单独评估的原因。

### 2.9 拒答要有单独的负例

Q6 询问不存在的 v9，Q7 询问当前版本没有证据支持的 E9999。它们分别检查没有这个版本，以及有相关文档但没有对应错误码。两种情况都不能拿最接近的文章充当答案。

本例拒答由显式规则产生，不具备通用的证据支持关系判断。如果一个问题没有明确错误码，却与某篇文章表面接近，简单规则仍可能选择过宽的资料。真实应用需要补充支持关系评估，不能把两个负例通过当作拒答能力完备。

### 2.10 三个已执行的反例检查

| 改动 | 应观察的现象 | 检查什么 |
|---|---|---|
| 全部 gold_document 改为空 | 选择不变，计分改变 | 标签不能泄漏进选择逻辑 |
| D2 状态改为 archived | Q1 失去有效证据并拒答 | 资料状态必须影响使用资格 |
| 只看 Q1 的 RRF 第一名 | 正确证据被排除 | 过早裁剪让下游无能为力 |

这些定向检查证明教学代码遵守声明的规则，不是生产检索性能评测。

### 2.11 切分、更新和权限怎样影响真实知识库

长文切分时，如果“仅适用于 v1”在前一段，而操作步骤独立成 chunk，检索就可能失去适用条件。片段应带来源、版本、章节与父文档信息，能回到完整上下文。

更新时，正文、索引和缓存也可能处于不同版本。正文已经撤销，旧索引仍可能继续召回。应关联文档修订与索引构建版本，不能只观察文件修改时间。

多租户场景的 tenant 与权限属于硬边界。检索应只返回允许访问的材料，输出前再核对。不能先把其他租户正文送进模型，再要求模型别说出来。本文没有实现该能力。

评估集应包含同义表达、上下文缺失、旧文档、撤权文档、相似错误码、跨文档组合与无答案问题。按类型分别记录结果，才能知道损失来自覆盖、排序、权限还是回答。

### 2.12 RAG 架构选型从证据结构开始

单篇说明能回答的问题，可以先采用较固定的检索路径。涉及实体关系的问题，可能需要显式关系结构；需要先查一个结果再决定下一步的问题，更接近动态检索和工具编排。

不要因为 GraphRAG 或 Agentic RAG 名称更复杂，就跳过文档质量、版本治理和基础检索覆盖。索引没有更新的问题，不会因为增加 Agent 循环自动消失，反而可能反复使用同一份旧证据。

本文没有运行 GraphRAG、真实 Agentic RAG 或多模态检索。这些是围绕证据结构的设计起点，需要在自己的问题集上验证。

## 三、MCP 工具调用：连接成功之后还要检查什么

知识库已经找到正确文章，下一步让客户端读取它。此时重点转向协议与权限。URL 能访问，不代表工具可用；初始化成功，也不意味着所有工具都被允许。

本例只读工具为 lookup_article，输入 article_id=KB-1042，返回当前版本说明。域名使用 .invalid，不会连接真实服务。所有 token 标记都是无效教学占位值。

### 3.1 一次调用经过的五层边界

| 边界 | 检查内容 | 本例如何处理 |
|---|---|---|
| 传输 | 消息能否抵达服务 | 比较本地 stdio 与远程 HTTP |
| 初始化 | 版本和能力是否协商 | initialize 后发送 initialized |
| 身份 | 凭证是否验证 | 把 claims 当作已验证的模拟输入 |
| 授权 | 是否具备工具权限 | articles:read 与 articles:write 分开 |
| 业务策略 | 是否还需额外条件 | 删除分支要求人工确认 |

真实身份验证还要考虑签名、issuer、有效期和具体认证约定。模拟字典检查不能冒充 OAuth 实现。接入参考见 [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)。

### 3.2 stdio 与 HTTP 的排查重点

stdio 常见于客户端启动本地子进程的场景，消息走标准输入输出。需要观察程序是否启动，以及普通日志是否混入 stdout；stderr 可以承担日志用途。

远程 HTTP 服务增加了网络、代理和身份边界。排查要看实际方法、请求头、版本与响应内容。本文只生成报文，没有启动真实 HTTP Server，也没有验证某个客户端互通。

本例中 GET 返回 405 与 POST 工具调用成功同时成立。服务不提供独立 GET SSE 监听时，浏览器地址栏的结果不足以判断 MCP 整体坏了。传输依据见 [MCP Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)。

### 3.3 正常流程得到的完整内容

流程先协商版本与 tools 能力，发送初始化完成通知，读取工具列表，再调用文章查询。完整工具结果是：

> Split AtlasDesk v2 exports into batches of at most 5000 rows.

文字与前一部分的当前版本证据一致，但它不意味着用户导出已经修复，也不意味着工单已保存。读取资料、执行动作和保存结果是三个事实。

### 3.4 全部五步请求与响应

请求 id 匹配响应，通知没有 id。固定请求头和无效 token 用于阅读，不能当作真实凭证。

```json
[
  {
    "request": {
      "method": "POST",
      "url": "https://mcp.example.invalid/mcp",
      "headers": {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Origin": "https://client.example.invalid",
        "Authorization": "Bearer FICTIONAL-NOT-A-TOKEN"
      },
      "body": {
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1,
        "params": {
          "protocolVersion": "2025-11-25",
          "capabilities": {},
          "clientInfo": {
            "name": "offline-review",
            "version": "1.0"
          }
        }
      }
    },
    "response": {
      "status": 200,
      "headers": {
        "Content-Type": "application/json"
      },
      "body": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
          "protocolVersion": "2025-11-25",
          "capabilities": {
            "tools": {}
          },
          "serverInfo": {
            "name": "fictional-support",
            "version": "1.0"
          }
        }
      }
    }
  },
  {
    "request": {
      "method": "POST",
      "headers": {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Origin": "https://client.example.invalid",
        "Authorization": "Bearer FICTIONAL-NOT-A-TOKEN",
        "MCP-Protocol-Version": "2025-11-25"
      },
      "body": {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
      },
      "url": "https://mcp.example.invalid/mcp"
    },
    "response": {
      "status": 202,
      "body": null
    }
  },
  {
    "request": {
      "method": "POST",
      "headers": {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Origin": "https://client.example.invalid",
        "Authorization": "Bearer FICTIONAL-NOT-A-TOKEN",
        "MCP-Protocol-Version": "2025-11-25"
      },
      "body": {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
      },
      "url": "https://mcp.example.invalid/mcp"
    },
    "response": {
      "status": 200,
      "body": {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
          "tools": [
            {
              "name": "lookup_article",
              "description": "Read a fictional support article.",
              "inputSchema": {
                "type": "object",
                "properties": {
                  "article_id": {
                    "type": "string"
                  }
                },
                "required": [
                  "article_id"
                ]
              }
            }
          ]
        }
      }
    }
  },
  {
    "request": {
      "method": "POST",
      "headers": {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Origin": "https://client.example.invalid",
        "Authorization": "Bearer FICTIONAL-NOT-A-TOKEN",
        "MCP-Protocol-Version": "2025-11-25"
      },
      "body": {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 3,
        "params": {
          "name": "lookup_article",
          "arguments": {
            "article_id": "KB-1042"
          }
        }
      },
      "url": "https://mcp.example.invalid/mcp"
    },
    "response": {
      "status": 200,
      "body": {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {
          "content": [
            {
              "type": "text",
              "text": "Split AtlasDesk v2 exports into batches of at most 5000 rows."
            }
          ],
          "isError": false
        }
      }
    }
  },
  {
    "request": {
      "method": "GET",
      "headers": {
        "Accept": "text/event-stream",
        "Origin": "https://client.example.invalid",
        "Authorization": "Bearer FICTIONAL-NOT-A-TOKEN",
        "MCP-Protocol-Version": "2025-11-25"
      },
      "url": "https://mcp.example.invalid/mcp"
    },
    "response": {
      "status": 405,
      "body": null
    }
  }
]
```

通知得到 202 且无响应体，工具响应包含 content。本服务选择无状态模式，没有分配 MCP-Session-Id。固定选择不能代替对其他服务能力、版本和会话策略的协商。

### 3.5 session id 为什么不能证明身份

session 关联交互，身份回答调用者是谁。知道一个 session 标识，不能自动得到读取或删除资格。把两者混合，会让一个状态关联值承担过多权限。

本例 session_id_without_token 场景只验证缺少认证输入时被拒绝，没有建立真实 session 存储，也没有进行会话劫持攻击测试。名称是教学边界提示，不是真实安全测试报告。

### 3.6 audience、scope 与人工批准分别做什么

audience 表达凭证给哪个服务使用。给其他服务的凭证，不能因为含相同 scope 字符串就在本服务被接受。scope 再说明允许哪些操作。

人工批准则可以是应用的另一层要求。即便拥有写权限，一次具体删除仍可能需要确认。相反，用户同意某个动作，也不能凭空给一个无权限身份补出服务端 scope。

这些判断应在可信服务边界执行，不能只靠模型阅读工具说明后自行遵守。

### 3.7 七个场景的实际结果

| 场景 | 响应 | 工具执行 | 定位方向 |
|---|---|---|---|
| read_ok | 200 / allowed_simulated | 是，模拟只读 | 正常路径 |
| session_id_without_token | 401 / missing_token | 否 | 缺少认证输入 |
| wrong_audience | 401 / wrong_audience | 否 | 凭证目标服务不符 |
| read_token_cannot_delete | 403 / insufficient_scope | 否 | 只读身份不能删除 |
| write_scope_without_confirmation | 403 / confirmation_required_application_policy | 否 | 应用要求确认 |
| untrusted_origin | 403 / untrusted_origin | 否 | 来源不受信任 |
| call_before_initialize | 400 / not_initialized_application_policy | 否 | 初始化不满足 |

未初始化的 400、人工确认的 403 为本教学应用选择，不宣称规范规定了这些错误码。删除分支只演示拒绝条件，没有真实删除实现。

### 3.8 完整离线模拟器

将以下代码保存为独立目录中的 run.py。不需要前一套检索数据，不向示例地址发请求。

```python
"""Offline policy/lifecycle simulator, not an MCP server or OAuth implementation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = "2025-11-25"
SERVER = "https://mcp.example.invalid/mcp"


def rpc(method, request_id=None, params=None):
    result = {"jsonrpc": "2.0", "method": method}
    if request_id is not None:
        result["id"] = request_id
    if params is not None:
        result["params"] = params
    return result


def response(request_id, value):
    return {"jsonrpc": "2.0", "id": request_id, "result": value}


def simulate(name, token=None, origin="https://client.example.invalid", initialized=True,
             tool="lookup_article", confirmed=False):
    # Claims are test data already assumed verified by an auth boundary.
    # Real JWT signature/issuer/expiry/discovery/PKCE validation is out of scope.
    checks = []
    def reject(status, reason):
        return {"scenario": name, "status": status, "reason": reason,
                "checks": checks, "tool_executed": False}
    checks.append("origin")
    if origin != "https://client.example.invalid":
        return reject(403, "untrusted_origin")
    checks.append("authentication")
    if token is None:
        return reject(401, "missing_token")
    checks.append("audience")
    if token["aud"] != SERVER:
        return reject(401, "wrong_audience")
    checks.append("lifecycle")
    if not initialized:
        return reject(400, "not_initialized_application_policy")
    checks.append("scope")
    required = "articles:write" if tool == "delete_article" else "articles:read"
    if required not in token["scope"]:
        return reject(403, "insufficient_scope")
    if tool == "delete_article":
        checks.append("human_confirmation")
        if not confirmed:
            return reject(403, "confirmation_required_application_policy")
    return {"scenario": name, "status": 200, "reason": "allowed_simulated",
            "checks": checks, "tool_executed": True,
            "result": {"article_id": "KB-1042", "text": "Split AtlasDesk v2 exports into batches of at most 5000 rows."}}


def run():
    read = {"aud": SERVER, "scope": ["articles:read"]}
    write = {"aud": SERVER, "scope": ["articles:read", "articles:write"]}
    tools = [{"name": "lookup_article", "description": "Read a fictional support article.",
              "inputSchema": {"type": "object", "properties": {"article_id": {"type": "string"}}, "required": ["article_id"]}}]
    init = rpc("initialize", 1, {"protocolVersion": VERSION, "capabilities": {}, "clientInfo": {"name": "offline-review", "version": "1.0"}})
    transcript = [
        {"request": {"method": "POST", "url": SERVER, "headers": {"Accept": "application/json, text/event-stream", "Content-Type": "application/json", "Origin": "https://client.example.invalid", "Authorization": "Bearer FICTIONAL-NOT-A-TOKEN"}, "body": init},
         "response": {"status": 200, "headers": {"Content-Type": "application/json"}, "body": response(1, {"protocolVersion": VERSION, "capabilities": {"tools": {}}, "serverInfo": {"name": "fictional-support", "version": "1.0"}})}},
        {"request": {"method": "POST", "headers": {"MCP-Protocol-Version": VERSION}, "body": rpc("notifications/initialized")}, "response": {"status": 202, "body": None}},
        {"request": {"method": "POST", "headers": {"MCP-Protocol-Version": VERSION}, "body": rpc("tools/list", 2)}, "response": {"status": 200, "body": response(2, {"tools": tools})}},
        {"request": {"method": "POST", "headers": {"MCP-Protocol-Version": VERSION}, "body": rpc("tools/call", 3, {"name": "lookup_article", "arguments": {"article_id": "KB-1042"}})}, "response": {"status": 200, "body": response(3, {"content": [{"type": "text", "text": "Split AtlasDesk v2 exports into batches of at most 5000 rows."}], "isError": False})}},
        {"request": {"method": "GET", "headers": {"Accept": "text/event-stream", "MCP-Protocol-Version": VERSION}}, "response": {"status": 405, "body": None}}
    ]
    common = transcript[0]["request"]["headers"]
    for entry in transcript[1:]:
        entry["request"]["url"] = SERVER
        # POST requests share Accept, Origin, Content-Type, Authorization; GET has no JSON body.
        entry["request"]["headers"] = {**common, **entry["request"]["headers"]}
        if entry["request"]["method"] == "GET":
            entry["request"]["headers"].pop("Content-Type", None)
    cases = [simulate("read_ok", read), simulate("session_id_without_token", None),
             simulate("wrong_audience", {"aud": "https://other.example.invalid", "scope": ["articles:read"]}),
             simulate("read_token_cannot_delete", read, tool="delete_article"),
             simulate("write_scope_without_confirmation", write, tool="delete_article"),
             simulate("untrusted_origin", read, origin="https://evil.example.invalid"),
             simulate("call_before_initialize", read, initialized=False)]
    report = {"evidence_type": "offline_simulator", "protocol_reference": VERSION,
              "session_mode": "stateless; no MCP-Session-Id assigned",
              "real_network_requests": 0, "transcript": transcript, "policy_cases": cases}
    (ROOT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    lines = ["# MCP 请求生命周期与权限：完整结果", "", "> 离线模拟；没有真实 MCP/OAuth 服务、token 或删除操作。", "",
             "## 正常只读流程", "", "| Step | Request | Response |", "|---|---|---|"]
    for i, entry in enumerate(transcript, 1):
        lines.append(f'| {i} | {entry["request"]["method"]} {entry["request"].get("body", {}).get("method", "SSE stream")} | {entry["response"]["status"]} |')
    lines += ["", "完整工具结果：Split AtlasDesk v2 exports into batches of at most 5000 rows.", "",
              "## 拦截结果", "", "| Scenario | Status | Reason | Tool executed |", "|---|---|---|---|"]
    for case in cases:
        lines.append(f'| {case["scenario"]} | {case["status"]} | {case["reason"]} | {case["tool_executed"]} |')
    lines += ["", "## 完整报文", "", "```json", json.dumps(transcript, ensure_ascii=False, indent=2), "```", "",
              "通知返回 202 且无响应体；GET 405 在本示例表示未提供独立 SSE 监听。未初始化和人工确认的 400/403 是本教学应用策略，不宣称协议规定了这些错误码。", ""]
    (ROOT / "RESULTS.md").write_text("\n".join(lines))
    print(json.dumps({"scenarios": len(cases), "denied": sum(not c["tool_executed"] for c in cases), "network_requests": 0}))


if __name__ == "__main__":
    run()
```

要核对 reject 是否发生在工具执行前。如果先删除再检查 scope，即使最终返回 403，也没有保护业务状态。授权结果与工具是否已执行必须同时记录。

代码是固定教学分支，不是通用路由器。真实服务还需验证工具名、参数 schema、资源权限、输出结构和异常处理。一个查询成功，不代表支持任意工具。

### 3.9 不要看到 403 就扩大权限

| 现象 | 先核对 | 不应直接断言 |
|---|---|---|
| 初始化前失败 | URL、方法、版本、认证响应 | 工具业务代码一定有 bug |
| 初始化成功但列工具失败 | 能力、权限、请求状态 | 模型没理解工具 |
| 列得出工具但调用失败 | 参数、工具权限、资源权限 | 能列出就必须能执行 |
| HTTP 200 但动作未完成 | 工具内容与业务回执 | 200 就是业务成功 |
| GET405、POST 正常 | 独立 SSE 监听是否存在 | MCP 整体故障 |
| 超时且服务状态未知 | 请求关联、操作查询 | 超时就是没有执行 |

最后一种情况会连接到下一部分。产生副作用的工具遇到网络失败，需要核对操作状态，不能只增加重试次数。

### 3.10 工具说明与返回内容的信任边界

工具描述帮助客户端理解用途，不能成为权限来源。即使注解写着只读，实际实现仍可能写数据；应用应依据可信策略决定确认要求，并核对服务行为。

文章正文也不能改变调用者权限。内容可以提供操作建议，但不能通过自然语言把只读查询升级为批量删除。RAG 的内容可信度与 MCP 的执行授权要分别处理。

## 四、Agent 断点恢复：Checkpoint 仍然可能重复执行

前面已经得到正确建议，也知道谁能读取资料。现在把摘要保存到独立服务。保存成功后进程崩溃，重启时从哪里继续？

本例实际启动并结束子进程，不只是把 JSON 标成 failed。工作流和保存服务使用两个 SQLite 文件，提交边界独立，避免用同一个本地事务把核心问题藏起来。

### 4.1 让故障发生在正确位置

工作流先记录 prepared，再让模拟服务保存摘要，最后写 complete。我们在服务提交后、complete 之前退出子进程，退出码为 23。

重启时本地仍为 prepared，无法仅凭它判断保存是否已经发生。直接再保存一次，就会重复。每个组件自己的代码都可以完成，但共同业务结果仍然出错。

除非两种状态共享可靠事务，否则远端已提交和本地已确认之间需要明确协调方式。Checkpoint 本身并不会把外部副作用也自动纳入事务。

### 4.2 按故障位置确定恢复策略

| 故障位置 | 外部动作状态 | 恢复需要什么 |
|---|---|---|
| 准备之前 | 未发生 | 重新准备 |
| 已准备，未发请求 | 未发生 | 从待执行动作继续 |
| 已发请求，没拿到响应 | 不确定 | 保留 unknown，查询操作 |
| 服务已提交，本地未记完成 | 已发生 | 同一操作的回执对账 |
| 本地已记 complete | 已发生并已确认 | 不重复执行 |

本文实际注入第四种故障。其他行是设计需要考虑的状态，不是本次全部执行过的实验。并发和真实网络超时也没有覆盖。

### 4.3 两个数据库怎样分工

progress 表保存 job 与 step，effects 表保存 operation_key、payload 和 receipt。naive 不给稳定 key，重试会产生新记录。safe 用同一个 key 查询已经发生的动作。

示例键由 tenant、job、action、revision 组成：

```text
fictional-tenant:support-summary-1042:save-summary:v1
```

它代表一次逻辑动作。进程 id、当前时间或随机请求 id 可以用于追踪某次传输，但重试时可能改变，不适合直接作为相同业务动作的去重身份。

同一 key 也不能对应任意内容。payload 改变却复用旧键，代码会报错，避免把新动作误认为旧动作成功。真实服务还需定义有效期、租户隔离和并发行为。

### 4.4 实际得到的成果与记录

最终摘要为：

> AtlasDesk v2 E1042: use batches of at most 5000 rows.

| 模式 | 第一次 | 第二次 | 第三次 | 保存条数 |
|---|---|---|---|---|
| naive | 提交后退出 23 | 再保存，再记 complete | 已完成，退出 | 2 |
| safe | 相同位置退出 23 | 查到旧回执，记 complete | 已完成，退出 | 1 |

naive 没得到更多内容，只把同一成果做了两次。safe 的改进不是禁止重试，而是重试沿用原操作身份，并核对发生过的事实。

### 4.5 完整代码：真实崩溃与恢复

保存为第三个目录的 run.py。运行时创建临时 SQLite，提取结果后清理。没有邮件、订单、真实数据库写入或后台 worker。

```python
"""Real child-process crash + two local SQLite stores. No actual agent or provider."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = "support-summary-1042"


def worker(directory, mode, crash):
    work = sqlite3.connect(str(directory / "workflow.sqlite"))
    provider = sqlite3.connect(str(directory / "provider.sqlite"))
    work.execute("CREATE TABLE IF NOT EXISTS progress (job TEXT PRIMARY KEY, step TEXT)")
    provider.execute("CREATE TABLE IF NOT EXISTS effects (id INTEGER PRIMARY KEY, operation_key TEXT UNIQUE, payload TEXT)")
    row = work.execute("SELECT step FROM progress WHERE job=?", (JOB,)).fetchone()
    if row and row[0] == "complete":
        print(json.dumps({"event": "already_complete"}), flush=True)
        return
    if not row:
        work.execute("INSERT INTO progress VALUES (?, 'prepared')", (JOB,))
        work.commit()
    # Simulated remote provider commits independently of the workflow checkpoint.
    # NULL allows duplicate rows in naive mode. Stable key is tenant/job/action/version scoped.
    key = "fictional-tenant:" + JOB + ":save-summary:v1" if mode == "safe" else None
    payload = json.dumps({"article": "KB-1042", "summary": "AtlasDesk v2 E1042: use batches of at most 5000 rows."}, sort_keys=True)
    existing = provider.execute("SELECT id,payload FROM effects WHERE operation_key=?", (key,)).fetchone() if key else None
    if existing and existing[1] != payload:
        raise ValueError("Idempotency key reused with a different payload")
    if existing:
        receipt = existing[0]
        event = "reconciled_existing_receipt"
    else:
        cursor = provider.execute("INSERT INTO effects(operation_key,payload) VALUES (?,?)", (key, payload))
        receipt = cursor.lastrowid
        provider.commit()
        event = "effect_committed"
    print(json.dumps({"event": event, "receipt": receipt, "operation_key": key}), flush=True)
    if crash:
        print(json.dumps({"event": "crash_after_provider_commit_before_checkpoint"}), flush=True)
        os._exit(23)
    work.execute("UPDATE progress SET step='complete' WHERE job=?", (JOB,))
    work.commit()
    print(json.dumps({"event": "workflow_complete", "receipt": receipt}), flush=True)
    work.close()
    provider.close()


def run():
    scenarios = []
    for mode in ("naive", "safe"):
        with tempfile.TemporaryDirectory(prefix="jr-agent-teaching-") as temp:
            directory = Path(temp)
            runs = []
            for crash in (True, False, False):
                process = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", temp, mode, str(int(crash))], capture_output=True, text=True)
                expected = 23 if crash else 0
                if process.returncode != expected:
                    raise RuntimeError(process.stderr or str(process.returncode))
                runs.append({"exit_code": process.returncode, "events": [json.loads(line) for line in process.stdout.splitlines()]})
            with sqlite3.connect(str(directory / "provider.sqlite")) as connection:
                effects = [dict(zip(("receipt", "operation_key", "payload"), row)) for row in connection.execute("SELECT id,operation_key,payload FROM effects ORDER BY id")]
            with sqlite3.connect(str(directory / "workflow.sqlite")) as connection:
                step = connection.execute("SELECT step FROM progress WHERE job=?", (JOB,)).fetchone()[0]
            scenarios.append({"mode": mode, "runs": runs, "effect_count": len(effects), "effects": effects, "final_step": step})
    report = {"evidence_type": "local_sqlite_process_crash_experiment", "fictional": True,
              "real_external_effects": 0, "model_calls": 0, "scenarios": scenarios,
              "limits": "Provider store is local SQLite; not a distributed exactly-once proof. No timeout, concurrent retry, expiry or provider outage is modeled."}
    (ROOT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    lines = ["# Agent 断点恢复：完整结果", "", "> 真实子进程崩溃，两个本地 SQLite 文件模拟工作流与独立服务。无真实 Agent、模型或发送。", "",
             "| Mode | First exit | Retry exit | Final step | Committed effects |", "|---|---|---|---|---|"]
    for s in scenarios:
        lines.append(f'| {s["mode"]} | {s["runs"][0]["exit_code"]} | {s["runs"][1]["exit_code"]} | {s["final_step"]} | {s["effect_count"]} |')
    lines += ["", "## 最终保存的完整成果", "", "AtlasDesk v2 E1042: use batches of at most 5000 rows.", "",
              "naive 把同一成果保存两次；safe 通过同一个 operation key 查询到已有回执，只保存一次。第三次运行读取 complete 后退出，两种模式都不再新增记录。", "",
              "## 逐步执行轨迹与回执", "", "```json", json.dumps(scenarios, ensure_ascii=False, indent=2), "```", "",
              "## 不能外推的结论", "", report["limits"], "",
              "真实服务必须支持稳定幂等键或可核对的操作回执。状态未知时保留 unknown 并先查回执；没有查询能力就暂停并交人处理，不能换键盲重试。", ""]
    (ROOT / "RESULTS.md").write_text("\n".join(lines))
    print(json.dumps({s["mode"]: s["effect_count"] for s in scenarios}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker(Path(sys.argv[2]), sys.argv[3], bool(int(sys.argv[4])))
    else:
        run()
```

provider.commit() 在故障点之前，complete 提交在之后。若两次提交都放在故障点前面，就不再覆盖外部成功、本地未知的窗口。

safe 查询的是独立模拟服务中的回执，不是只在工作流里多记一个标志。服务对稳定 key 的支持，让恢复有了可核对的依据。

### 4.6 两种模式的全部执行轨迹

下面记录各三次运行。第一次退出 23 是人为故障，后两次应为 0。这是本地实验，没有伪装成线上 Agent 记录。

```json
[
  {
    "mode": "naive",
    "runs": [
      {
        "exit_code": 23,
        "events": [
          {
            "event": "effect_committed",
            "receipt": 1,
            "operation_key": null
          },
          {
            "event": "crash_after_provider_commit_before_checkpoint"
          }
        ]
      },
      {
        "exit_code": 0,
        "events": [
          {
            "event": "effect_committed",
            "receipt": 2,
            "operation_key": null
          },
          {
            "event": "workflow_complete",
            "receipt": 2
          }
        ]
      },
      {
        "exit_code": 0,
        "events": [
          {
            "event": "already_complete"
          }
        ]
      }
    ],
    "effect_count": 2,
    "effects": [
      {
        "receipt": 1,
        "operation_key": null,
        "payload": "{\"article\": \"KB-1042\", \"summary\": \"AtlasDesk v2 E1042: use batches of at most 5000 rows.\"}"
      },
      {
        "receipt": 2,
        "operation_key": null,
        "payload": "{\"article\": \"KB-1042\", \"summary\": \"AtlasDesk v2 E1042: use batches of at most 5000 rows.\"}"
      }
    ],
    "final_step": "complete"
  },
  {
    "mode": "safe",
    "runs": [
      {
        "exit_code": 23,
        "events": [
          {
            "event": "effect_committed",
            "receipt": 1,
            "operation_key": "fictional-tenant:support-summary-1042:save-summary:v1"
          },
          {
            "event": "crash_after_provider_commit_before_checkpoint"
          }
        ]
      },
      {
        "exit_code": 0,
        "events": [
          {
            "event": "reconciled_existing_receipt",
            "receipt": 1,
            "operation_key": "fictional-tenant:support-summary-1042:save-summary:v1"
          },
          {
            "event": "workflow_complete",
            "receipt": 1
          }
        ]
      },
      {
        "exit_code": 0,
        "events": [
          {
            "event": "already_complete"
          }
        ]
      }
    ],
    "effect_count": 1,
    "effects": [
      {
        "receipt": 1,
        "operation_key": "fictional-tenant:support-summary-1042:save-summary:v1",
        "payload": "{\"article\": \"KB-1042\", \"summary\": \"AtlasDesk v2 E1042: use batches of at most 5000 rows.\"}"
      }
    ],
    "final_step": "complete"
  }
]
```

第三次验证完成后不重复，第二次验证缺少完成标记时怎样处理已发生副作用。两个验证不能互相代替。

### 4.7 unknown 应该是实际状态

超时只表示调用方没有及时拿到结果。请求可能没到，也可能已经执行但响应丢失。把二者都记为 failed，会诱导再次发送。

能查询时，沿用原 operation key 或业务标识核对；暂时不能查询时，保留 unknown 并稍后处理；完全没有去重与查询能力时，要调整业务边界或交人确认。不能为了流程继续，把未知改写成肯定没做。

只读重试主要影响成本、延迟或一致性；发送、支付、删除、报名的重复执行则会改变业务结果。重试策略必须认识动作类别，不能对所有工具使用同一种循环。

### 4.8 Checkpoint、队列和持久化编排的职责

Checkpoint 保存进度，队列分发和重新投递，持久化编排保留流程历史并协调恢复。这些机制帮助执行继续，但不自动替所有外部服务提供业务幂等。

如果一个 Activity 向没有去重能力的服务发消息，重新调度仍要处理重复发送。选用 Durable Workflow 不能取消副作用设计。继续阅读可参考 [Temporal SDK 架构](https://docs.temporal.io/encyclopedia/architecture/temporal-sdks)。

本文未运行 Temporal，也未比较编排引擎性能。两个 SQLite 的目的，是把一个特定故障窗口讲清楚。

### 4.9 safe 模式不等于并发安全与 exactly once

串行先查再插，不等于完成并发去重。两个 worker 可能同时查不到记录，再同时创建操作。实际服务需要通过唯一约束、事务或原子接口处理，本例没有进行该实验。

键过期、服务恢复丢记录、跨租户碰撞、内容变化后复用旧键，也需要定义行为。不能把所有分歧都包装成稍后再试。

本文只确认：在指定串行故障窗口中，稳定 key 和回执避免了重复记录，没有声称完成分布式 exactly once。

## 五、将三部分放回完整用户路径

用户关心的是拿到适用说明，并可靠保存后续记录。系统分别确认 D2 是正确证据，当前身份可读 KB-1042，同一次摘要保存已经发生。

组合时应该传递结构化证据与状态，而不只是一段对话。产品版本关联已确认上下文，引用关联文档修订，调用关联身份，保存关联稳定逻辑操作。

### 5.1 一份建议的可追踪记录

下面是字段设计示例，不是额外运行过的集成结果。真实项目应按隐私和保留政策确定日志，避免写入 token 或敏感原文。

```json
{
  "evidence_type": "proposed_integration_record_not_a_live_run",
  "request_id": "fictional-request-1042",
  "context": {"product": "AtlasDesk", "version": "2", "source": "confirmed_user_context"},
  "retrieval": {
    "candidate_ids": ["D1", "D2", "D4"],
    "selected_document": "D2",
    "document_status": "current",
    "answer_mode": "extractive"
  },
  "tool": {"name": "lookup_article", "resource": "KB-1042", "required_scope": "articles:read"},
  "save_operation": {
    "logical_key": "fictional-tenant:support-summary-1042:save-summary:v1",
    "state": "reconciled",
    "receipt": 1
  }
}
```

request_id 关联一次请求，logical_key 关联一次逻辑动作。一项动作可以经历多次请求，仍只应产生一个预期副作用。二者相关但不应默认相同。

### 5.2 联合诊断表

| 用户症状 | 起点 | 应保留的证据 | 下一步 |
|---|---|---|---|
| 建议属于旧版本 | 文档与候选 | 版本、状态、候选名次 | 修复资料适用资格 |
| 引用了其他产品 | 上下文与精确词 | 产品、错误码、文章 | 补上下文或修复召回 |
| 没资料却确定回答 | 拒答与支持关系 | 负例、可用证据、引用 | 完善证据不足处理 |
| 工具能连不能用 | 初始化、身份、参数 | 响应、拒绝层、是否执行 | 修复对应边界 |
| 页面失败却保存两次 | 回执与 checkpoint | 操作键、回执、故障点 | 对账与幂等修复 |
| 显示完成却没成果 | 成果与完成状态 | 可读内容、保存位置、回执 | 区分流程与成果交付 |

完成标记、调用次数和成功提示不能代替成果。客服要能读到建议，操作者要能找到摘要，并理解依据在哪里。

### 5.3 迁移到真实项目时的顺序

先选明确的小场景，取得有权使用的资料，写清输入与预期成果。问题集包含正常、冲突和无答案情况。先记录候选与引用，再评估回答。

接下来只接一个受限只读工具，验证真实客户端的初始化和权限。需要写入时，先定义动作身份、回执与 unknown，再做故障注入。最后根据实际复杂度决定是否需要更复杂的编排。

这样每一步都能看到成果，也能知道失败归属。它不保证项目一定成功，但能减少同时更换模型、框架、索引和工作流后无法判断哪一项有效的问题。

## 六、本地复现与排错

从本文复制时，建立三个目录，避免同名 run.py 和派生文件互相覆盖。RAG 额外放 dataset.json。各目录运行：

```sh
python3 run.py
```

下载整个仓库后，也可以直接运行：

```sh
python3 examples/rag-retrieval/run.py
python3 examples/mcp-lifecycle/run.py
python3 examples/agent-recovery/run.py
```

各脚本覆盖自己目录中的 result.json 和 RESULTS.md，不修改输入。Agent 只在系统临时目录创建和清理 SQLite，不改账号、生产服务或其他项目。

已保存的命令行摘要如下：

```jsonl
{"answerable_questions": 5, "dense_hit_at_1": 4, "rrf_recall_at_3": 5, "policy_correct_answerable": 5, "unanswerable_questions": 2}
{"scenarios": 7, "denied": 6, "network_requests": 0}
{"naive": 2, "safe": 1}
```

Agent 首次子进程退出 23 是指定故障，不要将它改成忽略错误。父进程应检查这个退出码，再继续恢复。父进程正常退出，才表示整套实验跑完。

| 复现现象 | 先检查 |
|---|---|
| dataset.json 找不到 | 数据和 RAG 代码是否同目录 |
| 语法或类型错误 | Python 是否为 3.9+，复制是否完整 |
| 结果被覆盖 | 三个实验是否误用同一目录 |
| Agent 子进程无法启动 | Python 路径、临时目录权限 |
| 计数不同 | 文档、向量、版本、状态或规则是否改动 |
| 想连接真实模型或 MCP | 本文未实现，需要独立接入验证 |

复现目标是得到同样结果，并解释过程。连接真实模型会引入费用、权限和输出变化，不是理解本实验的必要步骤。

## 七、验证结论应该怎样写

本地验证包括：三个示例重跑结果一致，gold 标签扰动不影响选择，正确资料归档后拒答，协议 id 对应，拒绝时未执行工具，以及真实崩溃后核对保存记录。

每个结论都有范围。模拟场景通过不等于 OAuth 安全审计；safe 保存一次不等于覆盖分布式故障；五道有答案题正确不等于可以对外承诺的准确率。

报告应同时写做了什么、看到了什么、能证明什么。别人应能找到对应输入与结果，而不只是相信一句测试全过。

### 7.1 这篇长文的实现边界

没有运行真实 embedding、神经 reranker、MCP Server、OAuth、客户端互通、线上 Agent 或并发 worker；没有发送、支付、删除或连接生产数据。

这些边界不意味着没有成果：数据、完整代码、逐题答案、协议报文与恢复回执都已给出。它们用于理解可核对的机制，不冒充已经上线的完整系统。

## 如何继续

理解这三条链路后，可以在 JR Academy 查看对应架构专题：

| 目标 | 入口 | 与本文关系 |
|---|---|---|
| RAG 检索拓扑 | [RAG 架构 Lab](https://jracademy.ai/system-design-lab/rag-architecture-families?utm_source=github&utm_medium=referral&utm_campaign=ai_engineering_handbook&utm_content=long_readme_rag) | 比较证据经过哪些节点 |
| MCP 服务与网关 | [MCP 工具平台 Lab](https://jracademy.ai/system-design-lab/mcp-tool-platform-architectures?utm_source=github&utm_medium=referral&utm_campaign=ai_engineering_handbook&utm_content=long_readme_mcp) | 继续理解认证与执行位置 |
| 长任务恢复 | [Durable Agent Lab](https://jracademy.ai/system-design-lab/durable-agent-execution-architectures?utm_source=github&utm_medium=referral&utm_campaign=ai_engineering_handbook&utm_content=long_readme_agent) | 比较状态、队列与编排 |

这些是已有专题入口。本文新数据、报文和回执没有注入正式 Lab，不能用链接存在来宣称产品已经提供同一套实验。访问和权限以对应页面实际状态为准。

## 来源与内容性质

本文由 JR Academy 整理。选题参考既有 RAG、MCP 工具平台和 Durable Agent 资料，虚构场景、数据、代码与解释为本次重新编写，没有复制第三方配图或旧资料全文。

- [Microsoft：RRF 名次融合](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)
- [MCP 2025-11-25：Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP 2025-11-25：Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP 2025-11-25：Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- [MCP 2025-11-25：Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Python：sqlite3 标准库](https://docs.python.org/3/library/sqlite3.html)
- [Temporal：SDK 架构](https://docs.temporal.io/encyclopedia/architecture/temporal-sdks)

本仓库公开可读，未选择 MIT、CC 或其他开源许可证。引用材料权利属于相应权利人。可在 Issues 提供可复现的技术错误，不要提交凭据、个人资料或真实客户文档。
