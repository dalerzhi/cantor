# IaaS 平台配置

## CAStack 云平台

- **平台地址**: https://castack-gncenter.cheersucloud.com/
- **API 前缀**: https://castack-gncenter.cheersucloud.com/openapi/
- **Access Key**: 91e28b4734d642b29c1ad64cbb44df8a
- **Secret Key**: a589615d6d144dd5aa3e776a9ac4f303

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

def sign(sk: str, timestamp: int) -> str:
    return hmac.new(
        sk.encode('utf-8'),
        str(timestamp).encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
```

### 示例
```
POST /openapi/v2/instance/page/list?time=1640494526&sign=xxx
X-ak: 91e28b4734d642b29c1ad64cbb44df8a
```

## 常用 API

| API | 方法 | 功能 |
|-----|------|------|
| `/v2/instance/page/list` | POST | 容器列表 |
| `/v2/instance/details/{uuid}` | GET | 容器详情 |
| `/v2/instance/start` | POST | 启动容器 |
| `/v2/instance/stop` | POST | 停止容器 |
| `/v2/instance/ssh-info` | POST | SSH 连接信息 |
| `/v2/command/instance` | POST | 异步执行命令 |
| `/v2/command/instance/sync` | POST | 同步执行命令 |

## 状态

✅ **已验证连接成功** (2026-03-01)
