"""
RTC Signaling Client for Cheersu Cloud
调用信令后台 API 获取加密串 (encryptedKey)
"""
import base64
import hmac
import hashlib
import json
import time
import random
from typing import Optional, Dict, Any
import httpx
from core.config import settings


class RTCSignalingClient:
    """
    RTC 信令后台客户端
    
    用于获取云手机实时视频流的加密串
    文档: /workspace/aiwork/cheersu-rtc/RTC-STREAMING-INTEGRATION-GUIDE.md
    """
    
    def __init__(
        self,
        base_url: str = None,
        access_key: str = None,
        secret_key: str = None,
        timeout: int = 30
    ):
        # 使用环境变量或传入的参数
        self.base_url = (base_url or settings.SIGNALING_BASE_URL).rstrip('/')
        self.access_key = access_key or settings.SIGNALING_ACCESS_KEY
        self.secret_key = secret_key or settings.SIGNALING_SECRET_KEY
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        生成 HMAC-SHA1 签名
        
        签名算法:
        1. 拼接参数: key1=value1&key2=value2 (按 key 排序)
        2. HMAC-SHA1 签名，使用 SK
        3. Base64 编码
        """
        # 按 key 排序并拼接
        sorted_items = sorted(params.items())
        plain_str = '&'.join([f"{k}={v}" for k, v in sorted_items])
        
        # HMAC-SHA1 签名
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            plain_str.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        # Base64 编码
        return base64.b64encode(signature).decode('utf-8')
    
    async def get_encrypted_key_v4(
        self,
        instance_id: str,
        region: str = "cn-east-1",
        image_quality: int = 1,
        mode: int = 1,
        timeout: int = 3600
    ) -> Dict[str, Any]:
        """
        获取加密串 (V4 接口 - 推荐)
        
        Args:
            instance_id: 云手机实例 ID
            region: 区域代码
            image_quality: 画质等级 (1=高清, 2=普通, 3=高速, 4=急速)
            mode: 模式 (1=保持帧率, 2=保持分辨率, 3=平衡)
            timeout: 连接超时时间(秒)
        
        Returns:
            {
                "base64Str": "加密串...",
                "lineInformation": {
                    "ipPortMappings": {...},
                    "perfect": "最优线路ID"
                }
            }
        """
        # 准备 data 参数
        data = {
            "instanceId": instance_id,
            "ipPorts": [],  # 可选，不传则自动分配
            "region": region,
            "timeout": timeout,
            "mappingType": 1,
            "imageQuality": image_quality,
            "mode": mode
        }
        
        # 生成时间戳和随机数
        timestamp = int(time.time())
        nonce = random.randint(100, 999)
        
        # 准备参数
        params = {
            "appId": self.access_key,
            "data": json.dumps(data),
            "nonce": nonce,
            "timestamp": timestamp
        }
        
        # 生成签名
        params["signature"] = self._generate_signature(params)
        
        # 发送请求
        url = f"{self.base_url}/coordinate/api/v4/room"
        response = await self.client.post(url, json=params)
        response.raise_for_status()
        
        return response.json()
    
    async def get_encrypted_key_v3(
        self,
        instance_id: str,
        ip: str,
        port: int,
        image_quality: int = 1,
        mode: int = 1
    ) -> Dict[str, Any]:
        """
        获取加密串 (V3 接口)
        
        Args:
            instance_id: 云手机实例 ID
            ip: 实例 IP
            port: 实例端口
            image_quality: 画质等级
            mode: 模式
        
        Returns:
            {"base64Str": "加密串..."}
        """
        data = {
            "instanceId": instance_id,
            "ipPort": {
                "ip": ip,
                "port": port
            },
            "imageQuality": image_quality,
            "mode": mode
        }
        
        timestamp = int(time.time())
        nonce = random.randint(100, 999)
        
        params = {
            "appId": self.access_key,
            "data": json.dumps(data),
            "nonce": nonce,
            "timestamp": timestamp
        }
        
        params["signature"] = self._generate_signature(params)
        
        url = f"{self.base_url}/coordinate/api/v3/room"
        response = await self.client.post(url, json=params)
        response.raise_for_status()
        
        return response.json()
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()


# 全局客户端实例
_rtc_signaling_client: Optional[RTCSignalingClient] = None


def get_rtc_signaling_client() -> RTCSignalingClient:
    """获取 RTC Signaling Client 实例 (单例)"""
    global _rtc_signaling_client
    if _rtc_signaling_client is None:
        _rtc_signaling_client = RTCSignalingClient()
    return _rtc_signaling_client
