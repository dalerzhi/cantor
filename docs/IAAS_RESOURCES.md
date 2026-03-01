# IaaS 平台资源查询结果

## 状态: ✅ 已验证连通

## 查询时间: 2026-03-01 20:25

## API 凭证

| 配置项 | 值 |
|--------|-----|
| BASE_URL | https://castack-gncenter.cheersucloud.com/openapi |
| Access Key | 91e28b4734d642b29c1ad64cbb44df8a |
| Secret Key | a589615d6d144dd5aa3e776a9ac4f303 |
| 状态 | ✅ 已验证 |

## 项目列表

| 项目名 | 板卡数 | UUID |
|--------|--------|------|
| default | 0 | 56af0e3d73733d7eaf73a9774e34b731 |
| 865 | 9 | fc03fd009526878939d72a73fe06fcd0 |
| 3588 | 5 | 9b827d2887c060da69028d0aa7c510ee |
| 8550 | 3 | 3a9caace82b03f0d3f8bd5d4b42cd325 |

**总计: 4 个项目，17 张板卡**

## 云手机实例

**当前实例数: 0**

板卡已分配但尚未创建容器实例。需要在 CAStack 控制台或通过 API 创建。

## 认证方式

```python
import hmac
import hashlib
import time

ts = int(time.time())
sign = hmac.new(SK.encode('utf-8'), str(ts).encode('utf-8'), hashlib.sha256).hexdigest()

url = f"{BASE_URL}/v1/project/list?time={ts}&sign={sign}"
headers = {
    "X-ak": AK,
    "Content-Type": "application/json",
    "cache-control": "no-cache"
}
```

## 可用 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/project/list` | POST | 项目列表 ✅ |
| `/v2/instance/page/list` | POST | 容器分页列表 ✅ |
| `/v2/instance/create` | POST | 创建容器 |
| `/v2/instance/start` | POST | 启动容器 |
| `/v2/instance/stop` | POST | 停止容器 |
| `/v2/instance/ssh-info` | POST | SSH 连接信息 |
| `/v2/command/instance` | POST | 异步命令 |
| `/v2/command/instance/sync` | POST | 同步命令 |

## 下一步

1. 在 CAStack 控制台创建云手机容器
2. 部署 cantor-worker 到容器
3. 连接 Cantor Gateway 测试
