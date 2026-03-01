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
    - URL 参数: time={秒级时间戳}&sign=HMAC-SHA256(SK, time)
    - Header: X-ak: {AK}
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
        self.client = httpx.Client(timeout=timeout)
    
    def _sign(self, timestamp: int) -> str:
        """
        生成签名
        
        sign = HMAC-SHA256(SK, timestamp) -> hex string
        """
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            str(timestamp).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "X-ak": self.access_key,
            "Content-Type": "application/json",
            "cache-control": "no-cache"
        }
    
    def _request(
        self,
        method: str,
        path: str,
        body: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送签名请求"""
        timestamp = int(time.time())
        sign = self._sign(timestamp)
        
        url = f"{self.base_url}{path}?time={timestamp}&sign={sign}"
        headers = self._get_headers()
        
        response = self.client.request(
            method=method,
            url=url,
            headers=headers,
            json=body or {}
        )
        
        if response.status_code == 401:
            raise PermissionError("IaaS API 认证失败，请检查 AK/SK")
        
        response.raise_for_status()
        return response.json()
    
    # ==================== 项目管理 ====================
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        获取项目列表
        
        POST /v1/project/list
        """
        data = self._request("POST", "/v1/project/list", {})
        return data.get('result', [])
    
    # ==================== 容器管理 ====================
    
    def list_instances(
        self,
        page_num: int = 1,
        page_size: int = 20,
        project_uuid: str = None,
        instance_uuids: List[str] = None
    ) -> Dict[str, Any]:
        """
        获取容器列表
        
        POST /v2/instance/page/list
        """
        body = {
            "pageNum": page_num,
            "pageSize": page_size
        }
        if project_uuid:
            body["projectUuid"] = project_uuid
        if instance_uuids:
            body["instanceUuids"] = instance_uuids
        
        return self._request("POST", "/v2/instance/page/list", body)
    
    def get_instance(self, uuid: str) -> Dict[str, Any]:
        """
        获取容器详情
        
        GET /v2/instance/details/{uuid}
        """
        return self._request("GET", f"/v2/instance/details/{uuid}")
    
    def start_instances(self, instance_uuids: List[str]) -> Dict[str, Any]:
        """
        启动容器
        
        POST /v2/instance/start
        """
        return self._request("POST", "/v2/instance/start", {
            "instanceUuids": instance_uuids
        })
    
    def stop_instances(self, instance_uuids: List[str]) -> Dict[str, Any]:
        """
        停止容器
        
        POST /v2/instance/stop
        """
        return self._request("POST", "/v2/instance/stop", {
            "instanceUuids": instance_uuids
        })
    
    def restart_instances(self, instance_uuids: List[str]) -> Dict[str, Any]:
        """
        重启容器
        
        POST /v2/instance/restart
        """
        return self._request("POST", "/v2/instance/restart", {
            "instanceUuids": instance_uuids
        })
    
    def get_ssh_info(self, uuid: str, live_time: int = 3600) -> Dict[str, Any]:
        """
        获取 SSH 连接信息
        
        POST /v2/instance/ssh-info
        """
        return self._request("POST", "/v2/instance/ssh-info", {
            "uuid": uuid,
            "liveTime": live_time
        })
    
    # ==================== 命令执行 ====================
    
    def execute_command(
        self,
        instance_uuids: List[str],
        command: str,
        content: Dict[str, Any],
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        异步执行命令
        
        POST /v2/command/instance
        
        command: download / write_file / shell
        """
        body = {
            "instanceUuids": instance_uuids,
            "command": command,
            "content": content
        }
        if callback_url:
            body["callbackUrl"] = callback_url
        
        return self._request("POST", "/v2/command/instance", body)
    
    def execute_shell_async(
        self,
        instance_uuids: List[str],
        shell_command: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """异步执行 Shell 命令"""
        return self.execute_command(
            instance_uuids,
            "shell",
            {"command": shell_command},
            callback_url
        )
    
    def execute_shell_sync(
        self,
        instance_uuids: List[str],
        shell_command: str
    ) -> Dict[str, Any]:
        """
        同步执行 Shell 命令
        
        POST /v2/command/instance/sync
        """
        return self._request("POST", "/v2/command/instance/sync", {
            "instanceUuids": instance_uuids,
            "command": "shell",
            "content": {"command": shell_command}
        })
    
    def download_file(
        self,
        instance_uuids: List[str],
        url: str,
        dest: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        下载文件到容器
        
        POST /v2/command/instance (command=download)
        """
        return self.execute_command(
            instance_uuids,
            "download",
            {"url": url, "dest": dest},
            callback_url
        )
    
    def write_file(
        self,
        instance_uuids: List[str],
        dest: str,
        data: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        写文件到容器
        
        POST /v2/command/instance (command=write_file)
        """
        return self.execute_command(
            instance_uuids,
            "write_file",
            {"dest": dest, "data": data},
            callback_url
        )
    
    # ==================== 资源管理 ====================
    
    def get_quota(self) -> Dict[str, Any]:
        """获取资源配额"""
        return self._request("GET", "/v1/quota")
    
    def list_regions(self) -> Dict[str, Any]:
        """获取可用区域"""
        return self._request("GET", "/v1/area/list")
    
    def close(self):
        """关闭客户端"""
        self.client.close()


# 异步客户端
class IaaSClientAsync:
    """异步客户端"""
    
    def __init__(self, base_url: str, access_key: str, secret_key: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.access_key = access_key
        self.secret_key = secret_key
        self.client = httpx.AsyncClient(timeout=timeout)
    
    def _sign(self, timestamp: int) -> str:
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            str(timestamp).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-ak": self.access_key,
            "Content-Type": "application/json",
            "cache-control": "no-cache"
        }
    
    async def _request(self, method: str, path: str, body: Dict[str, Any] = None) -> Dict[str, Any]:
        timestamp = int(time.time())
        sign = self._sign(timestamp)
        
        url = f"{self.base_url}{path}?time={timestamp}&sign={sign}"
        headers = self._get_headers()
        
        response = await self.client.request(
            method=method,
            url=url,
            headers=headers,
            json=body or {}
        )
        
        if response.status_code == 401:
            raise PermissionError("IaaS API 认证失败")
        
        response.raise_for_status()
        return response.json()
    
    async def list_projects(self) -> List[Dict[str, Any]]:
        data = await self._request("POST", "/v1/project/list", {})
        return data.get('result', [])
    
    async def list_instances(self, page_num: int = 1, page_size: int = 20, project_uuid: str = None) -> Dict[str, Any]:
        body = {"pageNum": page_num, "pageSize": page_size}
        if project_uuid:
            body["projectUuid"] = project_uuid
        return await self._request("POST", "/v2/instance/page/list", body)
    
    async def execute_shell_sync(self, instance_uuids: List[str], shell_command: str) -> Dict[str, Any]:
        return await self._request("POST", "/v2/command/instance/sync", {
            "instanceUuids": instance_uuids,
            "command": "shell",
            "content": {"command": shell_command}
        })
    
    async def download_file(self, instance_uuids: List[str], url: str, dest: str) -> Dict[str, Any]:
        return await self._request("POST", "/v2/command/instance", {
            "instanceUuids": instance_uuids,
            "command": "download",
            "content": {"url": url, "dest": dest}
        })
    
    async def close(self):
        await self.client.aclose()
