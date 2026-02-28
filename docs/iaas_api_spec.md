# 云手机 IaaS 平台接口文档规范

本文档为云手机 IaaS 平台相关的【容器】与【云手机操控】API 接口规范整理。

## 1. 容器相关 API

### 1.1 创建/删除容器
*   **创建容器**: `/v2/instance/create` (`POST`)
    *   **描述**: 调度到已申请的板卡上创建容器。
    *   **请求参数**: `projectId`, `nodeUuid` (必填), `armCardOfferingUuid` (必填), `os`, `osVersion`, `offeringUuid` (必填), `imageId` (必填), `num` (必填) 等。
    *   **响应格式**: 返回 `jobId`, `uuid`, `sn` 以及相应的状态 `code` 等。
*   **删除容器**: `/v1/arm/card/apply/destroy/container` (`POST`)
    *   **描述**: 删除板卡的容器。
    *   **请求参数**: `nodeUuid` (必填), `batchMap` (必填), `uuids`, `callbackUrl` 等。

### 1.2 查询容器信息
*   **容器分页列表**: `/v2/instance/page/list` (`POST`)
    *   **描述**: 分页查询容器列表，返回镜像、分辨率等数据。
    *   **请求参数**: `instanceUuids`, `pageNum`, `pageSize`, `projectId` 等。
*   **容器详情**: `/v2/instance/details/{uuid}` (`GET`)
    *   **描述**: 查询单个容器的详情。
*   **增量同步容器列表**: `/v2/instance/sync` (`POST`)
    *   **描述**: 根据时间基线与id基线增量同步变更记录。
*   **容器ssh连接信息**: `/v2/instance/ssh-info` (`POST`)
    *   **请求参数**: `uuid` (容器uuid), `liveTime` (连接有效时间)。
    *   **响应格式**: 返回 `sshCommand`, `host`, `port`, `username`, `sshPwd`。

### 1.3 容器启停及状态管理
此类接口均为批量操作接口，请求参数为含有目标 `instanceUuids` 列表的 `POST` 请求：
*   **启动容器**: `/v2/instance/start` (`POST`)
*   **停止容器**: `/v2/instance/stop` (`POST`)
*   **重启容器**: `/v2/instance/restart` (`POST`)
*   **重置容器**: `/v2/instance/reset` (`POST`) - 包含参数 `appPersistedType`（是否保留预安装应用），将清空 data 分区。
*   **容器镜像升级**: `/v2/instance/upgradeImage` (`POST`) - 需指定新 `imageId` 和 `wipeData`。

### 1.4 网络与限速
*   **设置限速**: `/v1/arm/card/apply/network/limit` (`POST`)
    *   **描述**: 批量设置板卡/容器限速 (`type` 区分)。参数含 `txLimit`, `rxLimit`。
*   **查询限速**: `/v1/arm/card/apply/query/network/limit` (`POST`)

---

## 2. 云手机操控相关 API

云手机的操控主要通过统一下发的指令接口（包含异步和同步两种模式）。

### 2.1 异步指令执行 (`/v2/command/instance`)
*   **请求方式**: `POST`
*   **描述**: 批量操作容器执行文件下载、文件写入或 shell 命令，任务执行状态异步返回，可通过 `callbackUrl` 回调。
*   **公共请求参数**: 
    *   `instanceUuids`: 容器 uuid 列表 (List<string>)
    *   `command`: 操作命令字（`download` / `write_file` / `shell`）
    *   `content`: 操作内容对象（依指令变化）

#### 支持的指令类型：
1.  **下载文件 (`download`)**
    *   `content.url`: 容器下可访问到的下载源地址。
    *   `content.dest`: 目标存储地址（只能在 `/data/` 下已存在目录）。
2.  **写文件 (`write_file`)**
    *   `content.dest`: 目标存储地址（须在 `/data` 或 `/sdcard/` 目录下）。
    *   `content.data`: 写入的内容（不超过 64K）。
3.  **异步 Shell 命令 (`shell`)**
    *   `content.command`: 待执行的 shell 命令（最大 1024 字节）。输出结果最多支持 8K 字节，结果需异步查询或依赖回调。

### 2.2 同步 Shell 命令 (`/v2/command/instance/sync`)
*   **请求方式**: `POST`
*   **描述**: 容器同步执行 shell 命令。
*   **请求参数**:
    *   `instanceUuids`: 容器 uuid 列表
    *   `command`: `shell`
    *   `content.command`: 具体的 shell 命令
*   **响应格式**:
    直接在响应对象的 `data` 属性内返回标准输出 `stdOut` 和异常输出 `stdErr` 列表。
    ```json
    {
      "status": 2, // 1:执行中 2:执行成功 -1:执行失败
      "data": {
        "stdOut": ["/"],
        "stdErr": [""]
      }
    }
    ```