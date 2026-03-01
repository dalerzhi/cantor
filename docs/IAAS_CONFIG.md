# IaaS 平台配置

## CAStack 云平台

- **平台地址**: https://castack-gncenter.cheersucloud.com/
- **API 地址**: https://castack-gncenter.cheersucloud.com/openapi
- **Access Key**: 91e28b4734d642b29c1ad64cbb44df8a
- **Secret Key**: a589615d6d144dd5aa3e776a9ac4f303
- **状态**: ✅ **已验证连通** (2026-03-01)

## 鉴权方式

### 请求头
```
X-ak: {AK}
Content-Type: application/json
cache-control: no-cache
```

### URL 参数
```
?time={秒级时间戳}&sign=HMAC-SHA256(SK, time)
```

### 签名算法
```python
import hmac
import hashlib
import time

ts = int(time.time())
sign = hmac.new(
    SK.encode('utf-8'),
    str(ts).encode('utf-8'),
    hashlib.sha256
).hexdigest()

url = f"{BASE_URL}/v1/project/list?time={ts}&sign={sign}"
headers = {
    "X-ak": AK,
    "Content-Type": "application/json",
    "cache-control": "no-cache"
}
```

### 示例请求
```
POST /openapi/v1/project/list?time=1640494526&sign=xxx
X-ak: 91e28b4734d642b29c1ad64cbb44df8a
Content-Type: application/json
cache-control: no-cache
```

## 当前资源

| 资源类型 | 数量 |
|----------|------|
| 项目 | 4 个 |
| 板卡 | 17 张 |
| 容器实例 | 0 个 |

### 项目详情

| 项目 | 板卡数 |
|------|--------|
| default | 0 |
| 865 | 9 |
| 3588 | 5 |
| 8550 | 3 |

## 常用 API

| API | 方法 | 功能 | 状态 |
|-----|------|------|------|
| `/v1/project/list` | POST | 项目列表 | ✅ 已验证 |
| `/v2/instance/page/list` | POST | 容器列表 | ✅ 已验证 |
| `/v2/instance/create` | POST | 创建容器 | 可用 |
| `/v2/instance/start` | POST | 启动容器 | 可用 |
| `/v2/instance/stop` | POST | 停止容器 | 可用 |
| `/v2/instance/ssh-info` | POST | SSH 连接信息 | 可用 |
| `/v2/command/instance` | POST | 异步执行命令 | 可用 |
| `/v2/command/instance/sync` | POST | 同步执行命令 | 可用 |
