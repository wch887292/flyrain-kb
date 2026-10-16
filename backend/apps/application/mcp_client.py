"""MCP (Model Context Protocol) 客户端：连接 MCP 服务器，获取工具列表，调用工具。

支持 HTTP/SSE 传输方式。stdio 方式在 Web 环境下不常用，暂以 HTTP 为主。
"""
import json
import logging
from typing import List, Dict, Optional

import requests

from apps.application.models import MCPServer

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 客户端，通过 HTTP/SSE 与 MCP 服务器通信。"""

    def __init__(self, server: MCPServer):
        self.server = server
        self.base_url = server.url.rstrip('/')
        self.headers = {'Content-Type': 'application/json', **(server.headers or {})}
        self.session_id: Optional[str] = None

    def _post(self, method: str, params: Dict = None) -> Dict:
        """发送 JSON-RPC 请求。"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }
        if self.session_id:
            payload["params"]["_session_id"] = self.session_id

        try:
            resp = requests.post(
                f"{self.base_url}/mcp",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                logger.error("MCP 错误: server=%s, error=%s", self.server.name, data["error"])
                return {"error": data["error"]}
            return data.get("result", {})
        except Exception as e:
            logger.error("MCP 请求失败: server=%s, error=%s", self.server.name, e)
            return {"error": str(e)}

    def initialize(self) -> bool:
        """初始化 MCP 会话。"""
        result = self._post("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fhzsk", "version": "1.0"},
        })
        if "error" not in result:
            self.session_id = result.get("sessionId", "")
            return True
        return False

    def list_tools(self) -> List[Dict]:
        """获取工具列表。"""
        result = self._post("tools/list")
        if "error" in result:
            return []
        tools = result.get("tools", [])
        # 缓存工具列表
        if tools:
            self.server.tools_cache = tools
            self.server.save(update_fields=['tools_cache'])
        return tools

    def call_tool(self, tool_name: str, arguments: Dict) -> str:
        """调用工具，返回文本结果。"""
        result = self._post("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        if "error" in result:
            return f"工具调用失败: {result['error']}"

        content = result.get("content", [])
        texts = []
        for item in content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif item.get("type") == "image":
                texts.append(f"[图片: {item.get('data', '')[:50]}...]")
        return "\n".join(texts)[:3000]


def get_all_tools(agent) -> List[Dict]:
    """获取智能体关联的所有 MCP 服务器的工具列表。

    返回格式: [{name, display_name, description, server_id, mcp: true}]
    """
    tools = []
    for server in agent.mcp_servers.filter(is_active=True):
        try:
            client = MCPClient(server)
            # 优先用缓存，缓存为空时实时获取
            server_tools = server.tools_cache or client.list_tools()
            for t in server_tools:
                tools.append({
                    'name': f'mcp_{server.id}_{t.get("name", "")}',
                    'display_name': f"{server.name}/{t.get('name', '')}",
                    'description': t.get('description', '') or f'MCP工具: {t.get("name", "")}',
                    'server_id': server.id,
                    'mcp_tool_name': t.get('name', ''),
                    'input_schema': t.get('inputSchema', {}),
                    'mcp': True,
                })
        except Exception as e:
            logger.warning("MCP 服务器工具获取失败: server=%s, error=%s", server.id, e)
    return tools


def call_mcp_tool(server_id: int, tool_name: str, arguments: Dict) -> str:
    """调用 MCP 工具。"""
    try:
        server = MCPServer.objects.get(id=server_id, is_active=True)
        client = MCPClient(server)
        return client.call_tool(tool_name, arguments)
    except MCPServer.DoesNotExist:
        return f"MCP 服务器不存在: {server_id}"
    except Exception as e:
        logger.warning("MCP 工具调用失败: server=%s, tool=%s, error=%s", server_id, tool_name, e, exc_info=True)
        return f"MCP 工具调用失败: {str(e)}"
