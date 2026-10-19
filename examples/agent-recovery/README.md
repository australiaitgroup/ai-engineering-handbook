# Agent 断点恢复：Checkpoint 为什么仍会重复执行

> 公开教学案例 · 2026-10-19 · 虚构客服任务；真实本地子进程崩溃与 SQLite 提交。没有模型、真实 Agent、邮件发送、账单或外部服务调用。

**先看完整成果：[两种恢复轨迹、最终摘要与保存回执](RESULTS.md)。** [run.py](run.py) 可复现相同故障窗口；[result.json](result.json) 保存逐步事件。无需先运行才能看到结果。

## 故障发生在最容易被漏掉的位置

一个虚构客服工作流先准备 KB-1042 的处理摘要，再把它保存到另一个服务。最终成果内容是：

> AtlasDesk v2 E1042: use batches of at most 5000 rows.

我们让保存服务先提交成功，然后在工作流写入 complete 之前强制结束子进程。重新启动时，工作流只看见 prepared。它不知道上次请求是否已经成功，再执行就可能多保存一次。

这个窗口说明：**Checkpoint 保存了工作流已知进度，却不能自动把远端副作用和本地进度变成同一个事务。** 本案例用两个独立 SQLite 文件保留这个边界；没有用同一数据库事务把问题隐藏起来。

## 已执行结果

| 路径 | 首次进程 | 第二次运行 | 最终副作用记录 | 第三次运行 |
|---|---|---|---|---|
| naive | 服务已保存，进程以 23 退出 | 再保存，再记 complete | 2 条 | 读到 complete，无新增 |
| safe | 同一故障位置，以 23 退出 | 按同一 key 查到回执，再记 complete | 1 条 | 读到 complete，无新增 |

两条记录中的摘要文字相同。naive 并不是生成了两个不同成果，而是同一次逻辑操作被执行了两次。safe 的改进来自模拟服务保存的稳定键与回执，不是把重试次数减少为零。

## 两个存储分别负责什么

`workflow.sqlite` 保存 job 与 prepared/complete 状态；`provider.sqlite` 模拟外部保存服务，记录操作键、payload 和 receipt。它们在临时目录创建，结果提取后自动删除。

safe 的操作键由虚构 tenant、job、action、revision 组成。同一次逻辑操作重试时沿用同一个键；如果内容改变却复用旧键，示例会报错，避免把另一个 payload 当成旧操作成功。

示意路径：准备摘要 → 提交服务副作用 → **故障窗口** → 保存 complete。恢复路径：读取 prepared → 用稳定 key 查服务 → 复用已有 receipt → 保存 complete。

第三次运行检查的是“完成状态不会再执行”，第二次检查的是“未完成状态下如何处理已经发生的副作用”。这两件事需要分别验证。

## Checkpoint、队列与 Durable Workflow 怎么选

| 方式 | 能解决什么 | 仍需自己处理什么 |
|---|---|---|
| 内存循环 | 简单短任务的本次执行 | 进程退出后状态丢失 |
| 持久化 Checkpoint | 找到上次已记录的节点 | 节点内已发生但未记账的副作用 |
| 队列 Worker | 分发任务与重新投递 | 重复投递、幂等、完成确认 |
| Durable Workflow | 持久化编排与恢复历史 | Activity 的重试与外部系统幂等边界 |

本例只实现 Checkpoint 与服务回执的教学对照，没有使用队列或 Temporal，也没有实现可恢复的完整 Agent runtime。相关概念可继续阅读 [Temporal SDK 架构](https://docs.temporal.io/encyclopedia/architecture/temporal-sdks)；本例不是该产品的评测或代替实现。

## 状态未知时，不能直接当作失败

本次可查询到 provider.sqlite 中的操作回执，因此能确定是否已经保存。真实环境可能超时、服务暂时不可读，甚至没有查询接口。此时应保留 unknown，等待核对或交人处理，不能换一个 key 重新发送。

若真实服务完全不支持幂等键或操作查询，需要重新设计业务边界：例如服务端去重、事务 outbox 与消费者去重，或人工确认。本案例没有实现这些方案，也不承诺在所有服务上 exactly once。

代码串行执行，没有覆盖并发重试、键过期、键碰撞、存储故障或服务宕机。因此一条记录的结果，只证明当前人为故障窗口下的教学设计成立。

## 本地复现

Python 3.9+，仅标准库，在本目录运行：

```sh
python3 run.py
```

脚本为每种模式启动三个短时子进程，第一次故意退出 23，后两次应正常退出。它只在系统临时目录写 SQLite，并覆盖本目录两个派生结果文件。没有后台 worker、服务端口、调度器或 CI。

读者可以从代码中看到 `provider.commit()` 与工作流 checkpoint 的先后顺序，理解“已经做完”和“已经记录做完”之间的差异。后续接入真实产品之前，应为该产品实际副作用设计故障实验，而不是复用本案例的计数作为验收。

## 官网继续学习（尚未完成承接验收）

[Durable Agent 架构 Lab](https://jracademy.ai/system-design-lab/durable-agent-execution-architectures?utm_source=github&utm_medium=referral&utm_campaign=ai_engineering_handbook&utm_content=agent-recovery) 沿用现有专题路径，用于继续比较四种架构。此次仅整理本地公开内容草稿，没有把新摘要或轨迹写入正式产品。

编辑说明：参考现有长任务架构专题；实验代码、摘要、记录与解释为本任务新写，未复制第三方图像。技术适用范围与来源见仓库 SOURCES.md。
