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
