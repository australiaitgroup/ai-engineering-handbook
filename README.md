# AI 工程架构实战手册 · JR Academy

> JR Academy 公开教学资料。虚构案例、离线实验；不代表真实客户成果。三份完整结果可直接阅读，无需账号或 API key。

[English overview](README.en.md) · [JR Academy 匠人学院](https://jracademy.ai/?utm_source=github&utm_medium=referral&utm_campaign=ai_engineering_handbook&utm_content=readme)

你已经知道 RAG、MCP、Agent 的名称，但项目出错时，不知道该查检索、权限还是状态。本手册先给完整结果，再解释输入、实现与失败路径。

## 直接看三个完整成果

| 你遇到的问题 | 完整成果 | 阅读案例 |
|---|---|---|
| RAG 用错产品或版本的文档 | [七题检索对照与带引用答案](examples/rag-retrieval/RESULTS.md) | [诊断检索不准](examples/rag-retrieval/README.md) |
| MCP 能连上，但调用被拒绝 | [完整请求与六种拦截结果](examples/mcp-lifecycle/RESULTS.md) | [定位传输、初始化与权限](examples/mcp-lifecycle/README.md) |
| Agent 重启后重复执行动作 | [崩溃、恢复与回执对照](examples/agent-recovery/RESULTS.md) | [Checkpoint 与幂等](examples/agent-recovery/README.md) |

## 适合谁

有基础 Python、能阅读 JSON 与 HTTP 的开发者；希望理解 AI 系统工程边界的学习者。没有编程基础的读者可以先看结果和解释，不要求先装环境。

三套脚本均使用 Python 3.9+ 标准库，无需第三方依赖、API key、模型下载、Docker 或数据库服务。每套运行方式写在对应案例中。结果已随资料提供，复现不是阅读前置条件。

## 如何继续

每篇文章末尾对应 [JR Academy 官网](https://jracademy.ai/)现有专题与 Lab 目标。官网承接尚未验收，新案例未注入正式产品；不能把这些链接视为案例已上线的证明。

资料为本任务新写案例与代码，不含付费题库、真实学员记录、生产凭据或第三方配图。来源与限制见 [SOURCES.md](SOURCES.md)。资料范围见 [PUBLICATION.md](PUBLICATION.md)。
