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
