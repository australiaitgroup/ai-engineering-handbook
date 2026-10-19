# 来源、方法与内容边界

2026-10-19 核对。此文件提供归因与技术依据，不授予第三方材料的再许可。

| 材料 | 本案例如何使用 | 未实现／不能证明 |
|---|---|---|
| JR Academy 现有《六类 RAG 系统架构》 | 确定检索、候选、证据的教学问题；本次重新写虚构数据与解释 | 未复制全章与上游图像，旧章权利需单独确认 |
| JR Academy 现有《MCP 工具平台》 | 确定身份、session 与工具权限的边界 | 未复用生产服务、凭据、客户数据 |
| JR Academy 现有《Durable Agent》 | 确定故障位置与恢复问题 | 未实现原 Lab 或任何模型 runtime |
| [Microsoft RRF](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking) | 对多路名次做倒数名次融合，常数与候选数分开 | 未调用 Azure Search；不是其性能评测 |
| [MCP Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) | 固定版本的传输、请求头与响应类型参考 | 不是最新版本声明或互通认证 |
| [MCP Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle) | initialize 与 initialized、能力协商 | 模拟报文不是实测网络抓包 |
| [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) | 远程服务身份与 token 受众边界 | 未实现 OAuth、签名、过期或吊销 |
| [MCP Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) | 工具描述、schema、调用和 content 结构 | 未做 SDK／客户端验证 |
| [Python sqlite3](https://docs.python.org/3/library/sqlite3.html) | 本地事务存储 | 不是生产分布式事务实验 |
| [Temporal SDK 架构](https://docs.temporal.io/encyclopedia/architecture/temporal-sdks) | 持久化编排的继续阅读 | 未运行 Temporal、队列或后台 worker |

AtlasDesk、HarborCRM、KB-1042、错误码、题目、操作键和摘要均为本次编写的教学材料。所有新测试问题及数据答案为英文，数据文件注明 language=en。人工向量与元数据规则直接暴露，避免伪装成模型结果。

本仓库由 JR Academy 发布。公开可读不等于授予开源许可；本仓库未选择 MIT、CC 或其他开源许可证。引用材料的权利仍属于原权利人。此次未复制旧资料全文或第三方图像，没有虚构个人作者或真实专家审阅记录。
