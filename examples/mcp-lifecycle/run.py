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
