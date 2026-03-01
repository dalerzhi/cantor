# CAStack IaaS API 完整文档摘要

## API 概览

**Base URL**: `https://castack-gncenter.cheersucloud.com/openapi`

**认证方式**:
- Header: `X-ak: {AccessKey}`
- URL 参数: `time={timestamp}&sign=HMAC-SHA256(SecretKey, timestamp)`

---

## 1. 区域和节点

### 1.1 节点列表
- **路径**: `POST /v1/node/list`
- **用途**: 获取所有可用节点

### 1.2 区域列表
- **路径**: `GET /v1/area/list`
- **用途**: 获取所有可用区域

---

## 2. 项目管理

### 2.1 项目列表
- **路径**: `POST /v1/project/list`
- **响应**: 项目列表，包含 uuid, name, cardNum, limitArmcard

### 2.2 创建项目
- **路径**: `POST /v1/project`
- **参数**: name, remark, standard (是否默认项目)

---

## 3. 板卡管理

### 3.1 申请板卡
- **路径**: `POST /v1/arm/card/apply/add`
- **参数**: nodeUuid, projectId, name, createType, armCardOfferingUuid, num

### 3.2 退订板卡
- **路径**: `POST /v1/arm/card/apply/unsubscribe`
- **参数**: nodeUuid, uuids

### 3.3 板卡列表
- **路径**: `POST /v1/arm/card/list`
- **参数**: pageNum, pageSize, projectId

### 3.4 可用板卡数量
- **路径**: `GET /v1/arm/card/available/count`
- **用途**: 获取可申请的板卡数量

---

## 4. 容器管理

### 4.1 容器分页列表
- **路径**: `POST /v2/instance/page/list`
- **参数**:
  - projectId (可选，默认当前用户的默认项目)
  - nodeUuids (节点 uuid 列表)
  - armCardSns (板卡 SN 列表)
  - instanceUuids (容器 uuid 列表)
  - pageNum, pageSize
- **响应字段**:
  - uuid: 容器 UUID
  - name: 容器名称
  - ip: 容器 IP
  - status: 容器状态 (0-创建中, 1-运行中, 2-已关机, 3-异常, 4-运行中)
  - cceStatus: CCE 运行状态 (Up/Exit/UnKnow)
  - armCardSn: 板卡 SN
  - armCardUuid: 板卡 UUID
  - nodeUuid: 节点 UUID
  - nodeName: 节点名称
  - projectId: 项目 ID
  - resolution: 分辨率
  - osVersion: 系统版本
  - level: 开数 (1-40)
  - instanceOffering: 计算规格对象

### 4.2 容器详情
- **路径**: `GET /v2/instance/details/{uuid}`
- **用途**: 获取单个容器详细信息

### 4.3 创建容器
- **路径**: `POST /v2/instance/create`
- **参数**: 
  - projectId, nodeUuid, armCardOfferingUuid
  - os, osVersion, offeringUuid, imageId
  - num (创建数量), createType (1-随机调度, 2-指定板卡)
  - snList (当 createType=2 时必填)
- **响应**: 返回 jobId 用于追踪任务

### 4.4 删除容器
- **路径**: `POST /v1/arm/card/apply/destroy/container`
- **参数**: nodeUuid, batchMap (板卡uuid/容器名称键值对), uuids

### 4.5 启动容器
- **路径**: `POST /v2/instance/start`
- **参数**: instanceUuids (容器 uuid 列表)

### 4.6 停止容器
- **路径**: `POST /v2/instance/stop`
- **参数**: instanceUuids (容器 uuid 列表)

### 4.7 重启容器
- **路径**: `POST /v2/instance/restart`
- **参数**: instanceUuids (容器 uuid 列表)

### 4.8 重置容器
- **路径**: `POST /v2/instance/reset`
- **参数**: instanceUuids, callbackUrl

### 4.9 容器镜像升级
- **路径**: `POST /v2/instance/image/upgrade`
- **参数**: instanceUuids, imageId

### 4.10 SSH 连接信息
- **路径**: `POST /v2/instance/ssh-info`
- **参数**: uuid, liveTime (有效期秒数)
- **响应**: SSH 连接信息 (host, port, user, password)

### 4.11 增量同步容器列表
- **路径**: `POST /v2/instance/sync/list`
- **参数**: updateTime (时间戳)

### 4.12 容器屏幕布局列表
- **路径**: `GET /v2/instance/layout/list`
- **响应**: 可用的屏幕布局配置

---

## 5. 计算规格

### 5.1 容器计算规格
- **路径**: `GET /v1/instance/offering/list`
- **响应**: 容器规格列表 (开数、CPU、内存等)

### 5.2 板卡计算规格
- **路径**: `GET /v1/arm/card/offering/list`
- **参数**: nodeUuid
- **响应**: 板卡规格列表

---

## 6. 镜像管理

### 6.1 镜像列表
- **路径**: `POST /v1/image/list`
- **参数**: projectId, os, osVersion

### 6.2 创建镜像
- **路径**: `POST /v1/image`

---

## 7. 云手机操控

### 7.1 执行异步命令
- **路径**: `POST /v2/command/instance`
- **参数**:
  - instanceUuids: 容器 uuid 列表
  - command: 命令类型 (download/write_file/shell)
  - content: 命令内容
  - callbackUrl: 回调地址

### 7.2 执行同步命令
- **路径**: `POST /v2/command/instance/sync`
- **参数**: 同上
- **响应**: 直接返回执行结果

### 命令类型:

#### download - 下载文件
```json
{
  "command": "download",
  "content": {
    "url": "http://xxx/file.apk",
    "dest": "/data/file.apk"
  }
}
```

#### write_file - 写文件
```json
{
  "command": "write_file",
  "content": {
    "dest": "/data/test.sh",
    "data": "文件内容",
    "chmod": "a+x",
    "chown": "root:root"
  }
}
```

#### shell - 执行 Shell
```json
{
  "command": "shell",
  "content": {
    "command": "pwd"
  }
}
```

---

## 8. 任务管理

### 8.1 查询子任务详情
- **路径**: `GET /v1/task/{jobId}`
- **响应**:
  - status: 任务状态 (-1,0-失败; 1-等待中; 2-成功; 3-进行中; 4-取消中; 5-已取消)
  - data.stdOut: 执行输出
  - data.stdErr: 错误输出
  - beginTime, endTime

### 8.2 查询子任务列表
- **路径**: `GET /v1/task/list`
- **参数**: traceId, jobId, status

---

## 9. 网络管理

### 9.1 业务网络列表
- **路径**: `GET /v1/network/list`

### 9.2 DNAT 配置
- **路径**: `POST /v1/dnat`

### 9.3 SNAT 配置
- **路径**: `POST /v1/snat`

---

## 10. 备份管理

### 10.1 创建备份
- **路径**: `POST /v1/backup`

### 10.2 恢复备份
- **路径**: `POST /v1/backup/restore`

---

## 11. 应用管理

### 11.1 安装应用
- **路径**: `POST /v2/app/install`
- **参数**: instanceUuids, apkUrl

### 11.2 卸载应用
- **路径**: `POST /v2/app/uninstall`
- **参数**: instanceUuids, packageName

### 11.3 启动应用
- **路径**: `POST /v2/app/start`
- **参数**: instanceUuids, packageName, activity

### 11.4 停止应用
- **路径**: `POST /v2/app/stop`
- **参数**: instanceUuids, packageName

---

## 容器状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 创建中 |
| 1 | 运行中 |
| 2 | 已关机 |
| 3 | 异常 |
| 4 | 运行中 (新状态) |

## 任务状态码

| 状态码 | 含义 |
|--------|------|
| -1, 0 | 执行失败 |
| 1 | 等待中 |
| 2 | 执行成功 |
| 3 | 进行中 |
| 4 | 取消中 |
| 5 | 已取消 |

---

## 回调通知

异步任务完成后会向 callbackUrl 发送 POST 请求:

```json
{
  "jobId": "任务ID",
  "status": 2,
  "message": "任务成功",
  "data": {
    "stdOut": ["输出"],
    "stdErr": []
  }
}
```
