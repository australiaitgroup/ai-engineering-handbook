# MCP 请求生命周期：能连上，不代表有权调用

> 公开教学案例 · 2026-10-19 · 离线协议与策略模拟。规范基线固定为 2025-11-25，不声称它是最新版本。没有真实网络服务、OAuth 登录或有效 token。

**先看完整成果：[正常报文、工具结果与六种拒绝路径](RESULTS.md)。** [run.py](run.py) 可以离线重现 [result.json](result.json)，无需 API key。读者最终得到一份可核对的请求生命周期与权限检查表。

## 用同一条客服知识查询贯穿流程

虚构客服客户端请求 `lookup_article`，参数为 `article_id=KB-1042`。允许的工具结果是：

> Split AtlasDesk v2 exports into batches of at most 5000 rows.

用户应看见当前版本的完整处理建议。工具只读，不发送消息、不删除文档，也不调用模型。另设 `delete_article` 策略分支，只验证拒绝条件；没有真实删除实现。

这个案例适合能读 HTTP 与 JSON 的开发者。它补充产品架构知识，但没有交付可部署的 MCP Server。

## 本地 stdio 与远程 HTTP 改变了什么

| 维度 | stdio | Streamable HTTP |
|---|---|---|
| 进程 | 客户端通常启动服务子进程 | 服务作为独立进程处理请求 |
| 消息 | stdin/stdout 的逐行 JSON-RPC | MCP endpoint 的 HTTP POST；可选 SSE |
| 日志 | 日志写 stderr，stdout 留给协议消息 | 使用服务日志，不破坏协议响应 |
| 认证边界 | 使用本地进程与环境权限边界 | 远程服务按自身认证与授权策略保护访问 |
| 常见误判 | 一行普通日志破坏 JSON 读取 | 只看 GET 状态，没有做初始化或鉴权 |

这些传输规则依据 [MCP Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)。本仓库只模拟 HTTP 报文，没有执行 stdio 子进程互通或 HTTP 服务测试。

## 正常只读请求的完整顺序

1. `initialize` 协商版本与 capabilities，返回 serverInfo 与 tools 能力。
2. 客户端发送 `notifications/initialized`；示例响应 202，无响应体。
3. `tools/list` 返回工具名称、说明和 inputSchema。
4. `tools/call` 携带文章编号，返回文本 content。
5. 客户端尝试 GET SSE 监听，示例响应 405，表示此端点未提供独立 SSE 流。

结果文件包含每步的请求头、JSON-RPC id、参数与响应，通知没有 id。POST 的 Accept 同时列出 JSON 与 SSE；初始化后的请求带协商版本头。使用无状态模式，未分配 MCP-Session-Id。

初始化流程见 [MCP Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)。实际客户端仍需处理服务返回的版本、能力及可选 session。本例的固定报文不能代替兼容性测试。

## 六种失败路径与具体处理

| 触发条件 | 模拟结果 | 应检查什么 |
|---|---|---|
| 只有 session id，没有访问凭证 | 401 | session 不能替代身份 |
| token audience 属于另一服务 | 401 | 不能把任意 token 当成本服务凭证 |
| 只读 scope 调用删除工具 | 403 | 工具级权限必须由服务执行 |
| 有写 scope，但没有人工确认 | 403 | 人工批准是本应用的额外策略 |
| 请求带不可信 Origin | 403 | 服务必须检查传入 Origin |
| 在初始化前执行工具 | 400 | 本教学应用拒绝未完成生命周期的调用 |

最后两类中的未初始化 400、人工确认 403 是本例选择的应用行为，不宣称规范强制要求这些错误码。token claims 在模拟中被视为已经由认证边界验证；签名、issuer、过期时间、OAuth discovery、PKCE、吊销等均未实现。真实接入需参考 [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)。

工具说明和 annotations 是提示，不能覆盖权限策略。工具返回内容也可能包含不可信指令；真实 AI 客户端需要自己的信任边界。工具接口结构见 [MCP Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)。

## 为何 GET 405 不足以判定服务故障

Streamable HTTP 可以在工具请求中返回 JSON，也可以使用 SSE。没有独立 GET SSE 监听时，GET 可以返回 405。本例的 POST 初始化与调用仍然有完整结果。因此排查应从 POST 初始化、Accept、版本协商、认证开始。

这不意味着所有 405 都正常：若 POST 初始化也被代理拒绝，或应用原本依赖 GET 通知，仍然需要修复对应路径。

## 本地复现与适用范围

```sh
python3 run.py
```

Python 3.9+，仅标准库。覆盖本目录两个派生结果文件，不访问 `.invalid` 地址，不启动监听端口。报文中的 `FICTIONAL-NOT-A-TOKEN` 是显式无效占位标记，不是凭据。

此次执行得到七个策略场景：一个允许只读查询，六个在工具执行前拒绝。这个结果验证了教学模拟器的分支，不是 OAuth 安全审计、真实 MCP 握手或客户端验收。

读完后，读者应能区分传输、初始化、身份、scope 与人工批准，并指出失败在哪一层；不能据此宣称自己已经完成生产 MCP 部署。

## 官网继续学习（尚未完成承接验收）

[MCP 工具平台 Lab](https://jracademy.ai/system-design-lab/mcp-tool-platform-architectures?utm_source=github&utm_medium=referral&utm_campaign=ai_engineering_handbook&utm_content=mcp-lifecycle) 是现有专题的目标入口。案例尚未注入正式 Lab，没有新增登录、权限或业务写入。

编辑说明：使用现有 MCP 工具平台专题确定教学问题；报文与虚构策略为本次新写，无第三方图像复制。规范基线及来源见仓库 SOURCES.md。
