"""
CAStack IaaS Platform Client
云手机资源管理 API 客户端
"""

import hashlib
import hmac
import base64
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode, quote

import httpx
from pydantic import BaseModel


class CloudPhone(BaseModel):
    """云手机实例"""
    id: str
    name: str
    status: str  # running, stopped, error
    ip: Optional[str] = None
    adb_port: Optional[int] = None
    region: Optional[str] = None
    spec: Optional[str] = None  # 规格
    created_at: Optional[datetime] = None


class IaaSClient:
    """
    CAStack IaaS 平台客户端
    
    使用 AK/SK 签名认证
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
    
    def _sign(self, method: str, path: str, query_params: Dict[str, Any] = None) -> Dict[str, str]:
        """
        生成签名请求头
        
        签名算法：
        1. 构造签名字符串: METHOD\nPATH\nTIMESTAMP\nQUERY
        2. 使用 SK 进行 HMAC-SHA256 签名
        3. Base64 编码
        """
        timestamp = str(int(time.time() * 1000))
        
        # 构造查询字符串
        query_str = ""
        if query_params:
            sorted_params = sorted(query_params.items())
            query_str = urlencode(sorted_params)
        
        # 签名字符串
        string_to_sign = f"{method.upper()}\n{path}\n{timestamp}\n{query_str}"
        
        # HMAC-SHA256 签名
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return {
            "X-Access-Key": self.access_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature_b64,
            "Content-Type": "application/json"
        }
    
    async def _request(
        self,
        method: str,
        path: str,
        query_params: Dict[str, Any] = None,
        body: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送签名请求"""
        headers = self._sign(method, path, query_params)
        url = f"{self.base_url}{path}"
        
        response = await self.client.request(
            method=method,
            url=url,
            headers=headers,
            params=query_params,
            json=body
        )
        
        if response.status_code == 401:
            raise PermissionError("IaaS API 认证失败，请检查 AK/SK")
        
        response.raise_for_status()
        return response.json()
    
    # ==================== 云手机管理 ====================
    
    async def list_phones(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str = None
    ) -> Dict[str, Any]:
        """
        获取云手机列表
        
        Args:
            page: 页码
            page_size: 每页数量
            status: 状态过滤 (running, stopped, error)
        """
        params = {"page": page, "pageSize": page_size}
        if status:
            params["status"] = status
        
        return await self._request("GET", "/api/v1/phones", params)
    
    async def get_phone(self, phone_id: str) -> Dict[str, Any]:
        """获取云手机详情"""
        return await self._request("GET", f"/api/v1/phones/{phone_id}")
    
    async def create_phone(
        self,
        name: str,
        spec: str = "standard",
        region: str = "default",
        image: str = None
    ) -> Dict[str, Any]:
        """
        创建云手机
        
        Args:
            name: 实例名称
            spec: 规格 (standard, premium, ultra)
            region: 区域
            image: 镜像 ID
        """
        body = {
            "name": name,
            "spec": spec,
            "region": region
        }
        if image:
            body["image"] = image
        
        return await self._request("POST", "/api/v1/phones", body=body)
    
    async def start_phone(self, phone_id: str) -> Dict[str, Any]:
        """启动云手机"""
        return await self._request("POST", f"/api/v1/phones/{phone_id}/start")
    
    async def stop_phone(self, phone_id: str, force: bool = False) -> Dict[str, Any]:
        """停止云手机"""
        params = {"force": "true"} if force else None
        return await self._request("POST", f"/api/v1/phones/{phone_id}/stop", params)
    
    async def reboot_phone(self, phone_id: str) -> Dict[str, Any]:
        """重启云手机"""
        return await self._request("POST", f"/api/v1/phones/{phone_id}/reboot")
    
    async def delete_phone(self, phone_id: str) -> Dict[str, Any]:
        """删除云手机"""
        return await self._request("DELETE", f"/api/v1/phones/{phone_id}")
    
    # ==================== ADB 连接 ====================
    
    async def get_adb_connection(self, phone_id: str) -> Dict[str, Any]:
        """
        获取 ADB 连接信息
        
        Returns:
            { "host": "xxx", "port": 5555, "connection_string": "xxx:5555" }
        """
        return await self._request("GET", f"/api/v1/phones/{phone_id}/adb")
    
    # ==================== 截图/录屏 ====================
    
    async def get_screenshot(self, phone_id: str) -> bytes:
        """获取手机截图"""
        headers = self._sign("GET", f"/api/v1/phones/{phone_id}/screenshot")
        url = f"{self.base_url}/api/v1/phones/{phone_id}/screenshot"
        
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        return response.content
    
    # ==================== 区域/规格 ====================
    
    async def list_regions(self) -> Dict[str, Any]:
        """获取可用区域列表"""
        return await self._request("GET", "/api/v1/regions")
    
    async def list_specs(self) -> Dict[str, Any]:
        """获取可用规格列表"""
        return await self._request("GET", "/api/v1/specs")
    
    # ==================== 资源统计 ====================
    
    async def get_quota(self) -> Dict[str, Any]:
        """获取资源配额"""
        return await self._request("GET", "/api/v1/quota")
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 同步包装器
class IaaSClientSync:
    """同步客户端包装器"""
    
    def __init__(self, base_url: str, access_key: str, secret_key: str, timeout: int = 30):
        self._async_client = IaaSClient(base_url, access_key, secret_key, timeout)
        self._sync_client = httpx.Client(timeout=timeout)
    
    def _sign(self, method: str, path: str, query_params: Dict[str, Any] = None) -> Dict[str, str]:
        return self._async_client._sign(method, path, query_params)
    
    def _request(self, method: str, path: str, query_params: Dict[str, Any] = None, body: Dict[str, Any] = None) -> Dict[str, Any]:
        headers = self._sign(method, path, query_params)
        url = f"{self._async_client.base_url}{path}"
        
        response = self._sync_client.request(
            method=method,
            url=url,
            headers=headers,
            params=query_params,
            json=body
        )
        
        if response.status_code == 401:
            raise PermissionError("IaaS API 认证失败，请检查 AK/SK")
        
        response.raise_for_status()
        return response.json()
    
    def list_phones(self, page: int = 1, page_size: int = 20, status: str = None) -> Dict[str, Any]:
        params = {"page": page, "pageSize": page_size}
        if status:
            params["status"] = status
        return self._request("GET", "/api/v1/phones", params)
    
    def get_phone(self, phone_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/v1/phones/{phone_id}")
    
    def close(self):
        self._sync_client.close()
