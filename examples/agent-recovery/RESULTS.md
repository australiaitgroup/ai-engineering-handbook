# Agent 断点恢复：完整结果

> 真实子进程崩溃，两个本地 SQLite 文件模拟工作流与独立服务。无真实 Agent、模型或发送。

| Mode | First exit | Retry exit | Final step | Committed effects |
|---|---|---|---|---|
| naive | 23 | 0 | complete | 2 |
| safe | 23 | 0 | complete | 1 |

## 最终保存的完整成果

AtlasDesk v2 E1042: use batches of at most 5000 rows.

naive 把同一成果保存两次；safe 通过同一个 operation key 查询到已有回执，只保存一次。第三次运行读取 complete 后退出，两种模式都不再新增记录。

## 逐步执行轨迹与回执

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

## 不能外推的结论

Provider store is local SQLite; not a distributed exactly-once proof. No timeout, concurrent retry, expiry or provider outage is modeled.

真实服务必须支持稳定幂等键或可核对的操作回执。状态未知时保留 unknown 并先查回执；没有查询能力就暂停并交人处理，不能换键盲重试。
