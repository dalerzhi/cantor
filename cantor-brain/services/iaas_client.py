"""
CAStack IaaS Platform Client
云手机资源管理 API 客户端 (完整版)

API 文档: https://castack-gncenter.cheersucloud.com/docs/user-guide/
"""

import hashlib
import hmac
import time
from typing import Optional, Dict, Any, List
from enum import IntEnum

import httpx
from pydantic import BaseModel


class ContainerStatus(IntEnum):
    """容器状态"""
    CREATING = 0      # 创建中
    RUNNING = 1       # 运行中
    STOPPED = 2       # 已关机
    ERROR = 3         # 异常
    RUNNING_NEW = 4   # 运行中 (新状态)


class TaskStatus(IntEnum):
    """任务状态"""
    FAILED = 0        # 执行失败
    PENDING = 1       # 等待中
    SUCCESS = 2       # 执行成功
    RUNNING = 3       # 进行中
    CANCELING = 4     # 取消中
    CANCELED = 5      # 已取消


class CreateType(IntEnum):
    """创建类型"""
    RANDOM = 1        # 随机调度
    SPECIFIED = 2     # 指定板卡


class StoreType(IntEnum):
    """存储类型"""
    LOCAL = 1         # 本地盘
    CLOUD = 2         # 云盘


# ==================== Models ====================

class CloudPhoneInstance(BaseModel):
    """云手机实例"""
    uuid: str
    name: str
    ip: Optional[str] = None
    status: int
    resolution: Optional[str] = None
    os_version: Optional[str] = None
    level: Optional[int] = None  # 开数
    root: Optional[int] = None
    arm_card_sn: Optional[str] = None
    arm_card_ip: Optional[str] = None
    node_uuid: Optional[str] = None
    node_name: Optional[str] = None
    project_id: Optional[str] = None
    image_name: Optional[str] = None
    cce_status: Optional[str] = None
    create_time: Optional[str] = None


class Project(BaseModel):
    """项目"""
    uuid: str
    name: str
    owner: int
    owner_name: Optional[str] = None
    card_num: int = 0
    limit_arm_card: int = 0
    status: int = 1
    standard: bool = False
    create_time: Optional[str] = None


class Node(BaseModel):
    """节点"""
    uuid: str
    name: str
    ip: Optional[str] = None
    port: Optional[int] = None
    area_uuid: Optional[str] = None
    area_name: Optional[str] = None
    status: Optional[int] = None


class TaskResult(BaseModel):
    """任务结果"""
    job_id: str
    status: int
    message: str
    uuid: Optional[str] = None
    sn: Optional[str] = None
    method: Optional[str] = None
    begin_time: Optional[str] = None
    end_time: Optional[str] = None
    std_out: Optional[List[str]] = None
    std_err: Optional[List[str]] = None


# ==================== Client ====================

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
        """生成签名: sign = HMAC-SHA256(SK, timestamp)"""
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
        body: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送签名请求"""
        timestamp = int(time.time())
        sign = self._sign(timestamp)
        
        # 构建 URL
        url = f"{self.base_url}{path}?time={timestamp}&sign={sign}"
        if params:
            for key, value in params.items():
                url += f"&{key}={value}"
        
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
        """获取项目列表"""
        data = self._request("POST", "/v1/project/list", {})
        return data.get('body', {}).get('result', [])
    
    def create_project(
        self,
        name: str,
        remark: str = None,
        standard: bool = False
    ) -> Dict[str, Any]:
        """创建项目"""
        body = {"name": name, "standard": standard}
        if remark:
            body["remark"] = remark
        return self._request("POST", "/v1/project", body)
    
    # ==================== 节点管理 ====================
    
    def list_nodes(self) -> List[Dict[str, Any]]:
        """获取节点列表"""
        data = self._request("POST", "/v1/node/list", {})
        return data.get('body', {}).get('result', [])
    
    def list_areas(self) -> List[Dict[str, Any]]:
        """获取区域列表"""
        data = self._request("GET", "/v1/area/list", {})
        return data.get('body', {}).get('result', [])
    
    # ==================== 板卡管理 ====================
    
    def list_arm_cards(
        self,
        project_id: str = None,
        page_num: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """获取板卡列表"""
        body = {"pageNum": page_num, "pageSize": page_size}
        if project_id:
            body["projectId"] = project_id
        return self._request("POST", "/v1/arm/card/list", body)
    
    def get_available_card_count(self, node_uuid: str) -> int:
        """获取可用板卡数量"""
        data = self._request("GET", "/v1/arm/card/available/count", params={"nodeUuid": node_uuid})
        return data.get('body', {}).get('result', 0)
    
    def apply_arm_cards(
        self,
        node_uuid: str,
        name: str,
        arm_card_offering_uuid: str,
        num: int,
        create_type: int = 1,
        project_id: str = None,
        sn_list: List[str] = None,
        os: str = "Android",
        os_version: str = "10",
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        申请板卡
        
        create_type: 1=板卡&容器, 2=裸板卡
        """
        body = {
            "nodeUuid": node_uuid,
            "name": name,
            "createType": create_type,
            "armCardOfferingUuid": arm_card_offering_uuid,
            "num": num,
            "os": os,
            "osVersion": os_version
        }
        if project_id:
            body["projectId"] = project_id
        if sn_list:
            body["snList"] = sn_list
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v1/arm/card/apply/add", body)
    
    def unsubscribe_arm_cards(
        self,
        node_uuid: str,
        uuids: List[str],
        callback_url: str = None
    ) -> Dict[str, Any]:
        """退订板卡"""
        body = {"nodeUuid": node_uuid, "uuids": uuids}
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v1/arm/card/apply/unsubscribe", body)
    
    # ==================== 容器管理 ====================
    
    def list_instances(
        self,
        page_num: int = 1,
        page_size: int = 20,
        project_id: str = None,
        node_uuids: List[str] = None,
        arm_card_sns: List[str] = None,
        instance_uuids: List[str] = None,
        levels: List[int] = None,
        status: List[int] = None
    ) -> Dict[str, Any]:
        """
        获取容器分页列表
        
        返回容器镜像、分辨率等数据
        """
        body = {"pageNum": page_num, "pageSize": page_size}
        if project_id:
            body["projectId"] = project_id
        if node_uuids:
            body["nodeUuids"] = node_uuids
        if arm_card_sns:
            body["armCardSns"] = arm_card_sns
        if instance_uuids:
            body["instanceUuids"] = instance_uuids
        if levels:
            body["levels"] = levels
        if status:
            body["status"] = status
        return self._request("POST", "/v2/instance/page/list", body)
    
    def get_instance(self, uuid: str) -> Dict[str, Any]:
        """获取容器详情"""
        return self._request("GET", f"/v2/instance/details/{uuid}")
    
    def create_instances(
        self,
        node_uuid: str,
        arm_card_offering_uuid: str,
        os: str,
        os_version: str,
        offering_uuid: str,
        image_id: str,
        num: int,
        create_type: int = 1,
        sn_list: List[str] = None,
        project_id: str = None,
        layout_uuid: str = None,
        network_uuid: str = None,
        subnet_uuid: str = None,
        root: int = 0,
        stop_status: bool = False,
        environment: Dict[str, str] = None,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        创建容器
        
        create_type: 1=随机调度, 2=指定板卡
        实际创建容器数量 = num * 开数
        """
        body = {
            "nodeUuid": node_uuid,
            "armCardOfferingUuid": arm_card_offering_uuid,
            "os": os,
            "osVersion": os_version,
            "offeringUuid": offering_uuid,
            "imageId": image_id,
            "num": num,
            "createType": create_type,
            "root": root,
            "stopStatus": stop_status
        }
        if sn_list:
            body["snList"] = sn_list
        if project_id:
            body["projectId"] = project_id
        if layout_uuid:
            body["layoutUuid"] = layout_uuid
        if network_uuid:
            body["networkUuid"] = network_uuid
        if subnet_uuid:
            body["subnetUuid"] = subnet_uuid
        if environment:
            body["environment"] = environment
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v2/instance/create", body)
    
    def delete_instances(
        self,
        node_uuid: str,
        batch_map: Dict[str, str],
        uuids: List[str],
        callback_url: str = None
    ) -> Dict[str, Any]:
        """删除容器"""
        body = {
            "nodeUuid": node_uuid,
            "batchMap": batch_map,
            "uuids": uuids
        }
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v1/arm/card/apply/destroy/container", body)
    
    def start_instances(
        self,
        instance_uuids: List[str],
        callback_url: str = None
    ) -> Dict[str, Any]:
        """启动容器"""
        body = {"instanceUuids": instance_uuids}
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v2/instance/start", body)
    
    def stop_instances(
        self,
        instance_uuids: List[str],
        callback_url: str = None
    ) -> Dict[str, Any]:
        """停止容器"""
        body = {"instanceUuids": instance_uuids}
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v2/instance/stop", body)
    
    def restart_instances(
        self,
        instance_uuids: List[str],
        callback_url: str = None
    ) -> Dict[str, Any]:
        """重启容器"""
        body = {"instanceUuids": instance_uuids}
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v2/instance/restart", body)
    
    def reset_instances(
        self,
        instance_uuids: List[str],
        callback_url: str = None
    ) -> Dict[str, Any]:
        """重置容器"""
        body = {"instanceUuids": instance_uuids}
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v2/instance/reset", body)
    
    def get_ssh_info(
        self,
        uuid: str,
        live_time: int = 3600
    ) -> Dict[str, Any]:
        """获取 SSH 连接信息"""
        return self._request("POST", "/v2/instance/ssh-info", {
            "uuid": uuid,
            "liveTime": live_time
        })
    
    def get_instance_layouts(self) -> List[Dict[str, Any]]:
        """获取容器屏幕布局列表"""
        data = self._request("GET", "/v2/instance/layout/list", {})
        return data.get('body', {}).get('result', [])
    
    def get_card_instance_status(
        self,
        node_uuid: str,
        arm_card_uuids: List[str]
    ) -> Dict[str, Any]:
        """获取板卡上容器启停状态列表"""
        return self._request("POST", "/v2/instance/card/status", {
            "nodeUuid": node_uuid,
            "armCardUuids": arm_card_uuids
        })
    
    # ==================== 云手机操控 ====================
    
    def execute_command(
        self,
        instance_uuids: List[str],
        command: str,
        content: Dict[str, Any],
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        异步执行命令
        
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
    
    def execute_command_sync(
        self,
        instance_uuids: List[str],
        command: str,
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """同步执行命令"""
        return self._request("POST", "/v2/command/instance/sync", {
            "instanceUuids": instance_uuids,
            "command": command,
            "content": content
        })
    
    def download_file(
        self,
        instance_uuids: List[str],
        url: str,
        dest: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """下载文件到容器"""
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
        chmod: str = None,
        chown: str = None,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """写文件到容器"""
        content = {"dest": dest, "data": data}
        if chmod:
            content["chmod"] = chmod
        if chown:
            content["chown"] = chown
        return self.execute_command(
            instance_uuids,
            "write_file",
            content,
            callback_url
        )
    
    def execute_shell(
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
        """同步执行 Shell 命令"""
        return self.execute_command_sync(
            instance_uuids,
            "shell",
            {"command": shell_command}
        )
    
    # ==================== 任务管理 ====================
    
    def get_task(self, job_id: str) -> Dict[str, Any]:
        """查询子任务详情"""
        return self._request("GET", f"/v1/task/{job_id}")
    
    def list_tasks(
        self,
        trace_id: str = None,
        job_id: str = None,
        status: int = None
    ) -> List[Dict[str, Any]]:
        """查询子任务列表"""
        params = {}
        if trace_id:
            params["traceId"] = trace_id
        if job_id:
            params["jobId"] = job_id
        if status is not None:
            params["status"] = status
        data = self._request("GET", "/v1/task/list", params=params)
        return data.get('body', {}).get('result', [])
    
    # ==================== 计算规格 ====================
    
    def list_instance_offerings(self) -> List[Dict[str, Any]]:
        """获取容器计算规格列表"""
        data = self._request("GET", "/v1/instance/offering/list", {})
        return data.get('body', {}).get('result', [])
    
    def list_arm_card_offerings(self, node_uuid: str) -> List[Dict[str, Any]]:
        """获取板卡计算规格列表"""
        data = self._request("GET", "/v1/arm/card/offering/list", params={"nodeUuid": node_uuid})
        return data.get('body', {}).get('result', [])
    
    # ==================== 镜像管理 ====================
    
    def list_images(
        self,
        project_id: str = None,
        os: str = None,
        os_version: str = None
    ) -> List[Dict[str, Any]]:
        """获取镜像列表"""
        body = {}
        if project_id:
            body["projectId"] = project_id
        if os:
            body["os"] = os
        if os_version:
            body["osVersion"] = os_version
        data = self._request("POST", "/v1/image/list", body)
        return data.get('body', {}).get('result', [])
    
    # ==================== 网络管理 ====================
    
    def list_networks(self) -> List[Dict[str, Any]]:
        """获取业务网络列表"""
        data = self._request("GET", "/v1/network/list", {})
        return data.get('body', {}).get('result', [])
    
    def get_available_ip_count(self, subnet_uuid: str = None) -> int:
        """获取可用 IP 数量"""
        params = {}
        if subnet_uuid:
            params["subnetUuid"] = subnet_uuid
        data = self._request("GET", "/v1/ip/available/count", params=params)
        return data.get('body', {}).get('result', 0)
    
    # ==================== 应用管理 ====================
    
    def install_app(
        self,
        instance_uuids: List[str],
        apk_url: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """安装应用"""
        body = {"instanceUuids": instance_uuids, "apkUrl": apk_url}
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v2/app/install", body)
    
    def uninstall_app(
        self,
        instance_uuids: List[str],
        package_name: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """卸载应用"""
        body = {"instanceUuids": instance_uuids, "packageName": package_name}
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v2/app/uninstall", body)
    
    def start_app(
        self,
        instance_uuids: List[str],
        package_name: str,
        activity: str = None,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """启动应用"""
        body = {"instanceUuids": instance_uuids, "packageName": package_name}
        if activity:
            body["activity"] = activity
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v2/app/start", body)
    
    def stop_app(
        self,
        instance_uuids: List[str],
        package_name: str,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """停止应用"""
        body = {"instanceUuids": instance_uuids, "packageName": package_name}
        if callback_url:
            body["callbackUrl"] = callback_url
        return self._request("POST", "/v2/app/stop", body)
    
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
        return data.get('body', {}).get('result', [])
    
    async def list_instances(
        self,
        page_num: int = 1,
        page_size: int = 20,
        project_id: str = None
    ) -> Dict[str, Any]:
        body = {"pageNum": page_num, "pageSize": page_size}
        if project_id:
            body["projectId"] = project_id
        return await self._request("POST", "/v2/instance/page/list", body)
    
    async def execute_shell_sync(
        self,
        instance_uuids: List[str],
        shell_command: str
    ) -> Dict[str, Any]:
        return await self._request("POST", "/v2/command/instance/sync", {
            "instanceUuids": instance_uuids,
            "command": "shell",
            "content": {"command": shell_command}
        })
    
    async def download_file(
        self,
        instance_uuids: List[str],
        url: str,
        dest: str
    ) -> Dict[str, Any]:
        return await self._request("POST", "/v2/command/instance", {
            "instanceUuids": instance_uuids,
            "command": "download",
            "content": {"url": url, "dest": dest}
        })
    
    async def close(self):
        await self.client.aclose()
