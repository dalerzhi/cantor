"""
CAStack IaaS Platform Client
云手机资源管理 API 客户端 (修正版)
"""

import hashlib
import hmac
import time
from typing import Optional, Dict, Any, List

import httpx
from pydantic import BaseModel


class CloudPhone(BaseModel):
    """云手机实例"""
    id: str
    name: str
    status: str
    ip: Optional[str] = None
    adb_port: Optional[int] = None
    region: Optional[str] = None
    spec: Optional[str] = None
    created_at: Optional[str] = None


class IaaSClient:
    """
    CAStack IaaS 平台客户端
    
    鉴权方式:
    - Header: X-ak: {AK}
    - URL 参数: time={timestamp}&sign=HMAC-SHA256(SK, time)
    """
    
    def __init__(
        self,
        base_url: str,
        access_key: str,
        secret_key: str,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.access_key = access_key
        self.secret_key = secret_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    def _sign(self, timestamp: int) -> str:
        """
        生成签名
        
        sign = HMAC-SHA256(SK, timestamp)
        返回十六进制字符串
        """
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            str(timestamp).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _build_url(self, path: str) -> str:
        """构建带签名的完整 URL"""
        timestamp = int(time.time())
        sign = self._sign(timestamp)
        
        separator = '&' if '?' in path else '?'
        return f"{self.base_url}{path}{separator}time={timestamp}&sign={sign}"
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "X-ak": self.access_key,
            "Content-Type": "application/json",
            "cache-control": "no-cache"
        }
    
    async def _request(
        self,
        method: str,
        path: str,
        body: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送签名请求"""
        url = self._build_url(path)
        headers = self._get_headers()
        
        response = await self.client.request(
            method=method,
            url=url,
            headers=headers,
            json=body
        )
        
        if response.status_code == 401:
            raise PermissionError("IaaS API 认证失败，请检查 AK/SK")
        
        response.raise_for_status()
        return response.json()
    
    # ==================== 容器管理 ====================
    
    async def list_instances(
        self,
        page_num: int = 1,
        page_size: int = 20,
        instance_uuids: List[str] = None
    ) -> Dict[str, Any]:
        """
        获取容器列表
        
        POST /openapi/v2/instance/page/list
        """
        body = {
            "pageNum": page_num,
            "pageSize": page_size
        }
        if instance_uuids:
            body["instanceUuids"] = instance_uuids
        
        return await self._request("POST", "/openapi/v2/instance/page/list", body)
    
    async def get_instance(self, uuid: str) -> Dict[str, Any]:
        """
        获取容器详情
        
        GET /openapi/v2/instance/details/{uuid}
        """
        return await self._request("GET", f"/openapi/v2/instance/details/{uuid}")
    
    async def start_instances(self, instance_uuids: List[str]) -> Dict[str, Any]:
        """
        启动容器
        
        POST /openapi/v2/instance/start
        """
        return await self._request("POST", "/openapi/v2/instance/start", {
            "instanceUuids": instance_uuids
        })
    
    async def stop_instances(self, instance_uuids: List[str]) -> Dict[str, Any]:
        """
        停止容器
        
        POST /openapi/v2/instance/stop
        """
        return await self._request("POST", "/openapi/v2/instance/stop", {
            "instanceUuids": instance_uuids
        })
    
    async def restart_instances(self, instance_uuids: List[str]) -> Dict[str, Any]:
        """
        重启容器
        
        POST /openapi/v2/instance/restart
        """
        return await self._request("POST", "/openapi/v2/instance/restart", {
            "instanceUuids": instance_uuids
        })
    
    async def get_ssh_info(self, uuid: str, live_time: int = 3600) -> Dict[str, Any]:
        """
        获取 SSH 连接信息
        
        POST /openapi/v2/instance/ssh-info
        """
        return await self._request("POST", "/openapi/v2/instance/ssh-info", {
            "uuid": uuid,
            "liveTime": live_time
        })
    
    # ==================== 命令执行 ====================
    
    async def execute_command(
        self,
        instance_uuids: List[str],
        command: str,
        content: Dict[str, Any],
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        异步执行命令
        
        POST /openapi/v2/command/instance
        
        command: download / write_file / shell
        """
        body = {
            "instanceUuids": instance_uuids,
            "command": command,
            "content": content
        }
        if callback_url:
            body["callbackUrl"] = callback_url
        
        return await self._request("POST", "/openapi/v2/command/instance", body)
    
    async def execute_shell_async(
        self,
        instance_uuids: List[str],
        shell_command: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """异步执行 Shell 命令"""
        return await self.execute_command(
            instance_uuids,
            "shell",
            {"command": shell_command},
            callback_url
        )
    
    async def execute_shell_sync(
        self,
        instance_uuids: List[str],
        shell_command: str
    ) -> Dict[str, Any]:
        """
        同步执行 Shell 命令
        
        POST /openapi/v2/command/instance/sync
        """
        return await self._request("POST", "/openapi/v2/command/instance/sync", {
            "instanceUuids": instance_uuids,
            "command": "shell",
            "content": {"command": shell_command}
        })
    
    async def download_file(
        self,
        instance_uuids: List[str],
        url: str,
        dest: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        下载文件到容器
        
        POST /openapi/v2/command/instance (command=download)
        """
        return await self.execute_command(
            instance_uuids,
            "download",
            {"url": url, "dest": dest},
            callback_url
        )
    
    async def write_file(
        self,
        instance_uuids: List[str],
        dest: str,
        data: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        写文件到容器
        
        POST /openapi/v2/command/instance (command=write_file)
        """
        return await self.execute_command(
            instance_uuids,
            "write_file",
            {"dest": dest, "data": data},
            callback_url
        )
    
    # ==================== 资源管理 ====================
    
    async def get_quota(self) -> Dict[str, Any]:
        """获取资源配额"""
        return await self._request("GET", "/openapi/v1/quota")
    
    async def list_regions(self) -> Dict[str, Any]:
        """获取可用区域"""
        return await self._request("GET", "/openapi/v1/regions")
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 同步客户端
class IaaSClientSync:
    """同步客户端"""
    
    def __init__(self, base_url: str, access_key: str, secret_key: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.access_key = access_key
        self.secret_key = secret_key
        self.client = httpx.Client(timeout=timeout)
    
    def _sign(self, timestamp: int) -> str:
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            str(timestamp).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _build_url(self, path: str) -> str:
        timestamp = int(time.time())
        sign = self._sign(timestamp)
        separator = '&' if '?' in path else '?'
        return f"{self.base_url}{path}{separator}time={timestamp}&sign={sign}"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-ak": self.access_key,
            "Content-Type": "application/json",
            "cache-control": "no-cache"
        }
    
    def _request(self, method: str, path: str, body: Dict[str, Any] = None) -> Dict[str, Any]:
        url = self._build_url(path)
        headers = self._get_headers()
        
        response = self.client.request(
            method=method,
            url=url,
            headers=headers,
            json=body
        )
        
        if response.status_code == 401:
            raise PermissionError("IaaS API 认证失败")
        
        response.raise_for_status()
        return response.json()
    
    def list_instances(self, page_num: int = 1, page_size: int = 20) -> Dict[str, Any]:
        return self._request("POST", "/openapi/v2/instance/page/list", {
            "pageNum": page_num,
            "pageSize": page_size
        })
    
    def get_instance(self, uuid: str) -> Dict[str, Any]:
        return self._request("GET", f"/openapi/v2/instance/details/{uuid}")
    
    def execute_shell_sync(self, instance_uuids: List[str], shell_command: str) -> Dict[str, Any]:
        return self._request("POST", "/openapi/v2/command/instance/sync", {
            "instanceUuids": instance_uuids,
            "command": "shell",
            "content": {"command": shell_command}
        })
    
    def download_file(self, instance_uuids: List[str], url: str, dest: str) -> Dict[str, Any]:
        return self._request("POST", "/openapi/v2/command/instance", {
            "instanceUuids": instance_uuids,
            "command": "download",
            "content": {"url": url, "dest": dest}
        })
    
    def close(self):
        self.client.close()
