# Cantor Worker

运行在云手机上的 Cantor 客户端，负责执行自动化任务。

## 功能

- **WebSocket 连接**: 连接 Gateway，注册设备，维持心跳
- **任务执行**: 执行 Shell 命令、ADB 操作、脚本
- **屏幕操作**: 截图、点击、滑动、输入
- **状态上报**: 实时上报任务进度和设备状态

## 构建

### Android (主要目标)

```bash
# 构建 Android ARM64
make build-android

# 输出文件
bin/cantor-worker-android-arm64
bin/cantor-worker-android-arm
```

### 其他平台

```bash
make build-linux   # Linux
make build-darwin  # macOS
make build-all     # 全平台
```

## 部署到云手机

### 方式1: 通过 IaaS API

```bash
# 上传到可访问的服务器
scp bin/cantor-worker-android-arm64 user@server:/path/

# 通过 IaaS API 下发到云手机
POST /v2/command/instance
{
  "instanceUuids": ["xxx"],
  "command": "download",
  "content": {
    "url": "http://server/cantor-worker",
    "dest": "/data/local/tmp/"
  }
}
```

### 方式2: ADB 推送

```bash
make install-android
# 或手动
adb push bin/cantor-worker-android-arm64 /data/local/tmp/cantor-worker
adb shell chmod +x /data/local/tmp/cantor-worker
```

## 运行

```bash
# 设置环境变量
export CANTOR_DEVICE_ID=device-001
export CANTOR_DEVICE_NAME="云手机 #1"
export CANTOR_DEVICE_TOKEN=your-api-key
export CANTOR_GATEWAY_URL=ws://your-server:8766/ws

# 运行
./cantor-worker
```

## 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `CANTOR_DEVICE_ID` | 设备唯一 ID | device-001 |
| `CANTOR_DEVICE_NAME` | 设备名称 | Cloud Phone |
| `CANTOR_DEVICE_TOKEN` | API Key (认证) | - |
| `CANTOR_GATEWAY_URL` | Gateway WebSocket 地址 | ws://localhost:8766/ws |
| `CANTOR_BRAIN_URL` | Brain API 地址 | http://localhost:8000 |
| `CANTOR_MAX_TASKS` | 最大并发任务数 | 10 |
| `CANTOR_TASK_TIMEOUT` | 任务超时 (秒) | 300 |

## 支持的任务类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `shell` | Shell 命令 | `ls -la` |
| `adb` | ADB/Android 命令 | `input tap 100 200` |
| `script` | 脚本执行 | Lua/Python/Shell |
| `click` | 点击屏幕 | `{x: 100, y: 200}` |
| `input` | 输入文本 | `{text: "hello"}` |
| `swipe` | 滑动屏幕 | `{x1, y1, x2, y2, duration}` |
| `screenshot` | 截屏 | - |

## 架构

```
┌─────────────────────────────────────┐
│          cantor-worker              │
├─────────────────────────────────────┤
│  ┌─────────┐    ┌─────────────┐    │
│  │   WS    │◄──►│  Executor   │    │
│  │ Client  │    │  (Task Run) │    │
│  └────┬────┘    └──────┬──────┘    │
│       │                │            │
│       │         ┌──────┴──────┐    │
│       │         │             │    │
│       ▼         ▼             ▼    │
│  Gateway    Shell Exec   ADB Exec  │
│                                    │
└─────────────────────────────────────┘
```

## 开发

```bash
# 依赖
go mod download

# 测试
make test

# 运行
make build
./bin/cantor-worker
```
