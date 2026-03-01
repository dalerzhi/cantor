# IaaS 平台资源查询结果

## 状态: ✅ 已验证连通

## 查询时间: 2026-03-01 20:30

## API 凭证

| 配置项 | 值 |
|--------|-----|
| BASE_URL | https://castack-gncenter.cheersucloud.com/openapi |
| Access Key | 91e28b4734d642b29c1ad64cbb44df8a |
| Secret Key | a589615d6d144dd5aa3e776a9ac4f303 |
| 状态 | ✅ 已验证 |

## 资源总览

| 资源类型 | 数量 |
|----------|------|
| 项目 | 4 个 |
| 节点 | 1 个 (qishuo-jinhua-1) |
| 板卡 | 6 张 |
| 云手机实例 | 21 个 |

## 节点分布

### qishuo-jinhua-1

| 指标 | 数量 |
|------|------|
| 板卡 | 6 张 |
| 实例 | 21 个 |
| 运行中 | 10 个 |
| 已关机 | 11 个 |

## 项目分布

| 项目 | 板卡 | 实例 | 运行 | 关机 |
|------|------|------|------|------|
| 865 | 2 | 10 | 5 | 5 |
| 3588 | 1 | 5 | 5 | 0 |
| 8550 | 3 | 6 | 0 | 6 |
| default | 0 | 0 | 0 | 0 |

## 板卡分布

| 板卡 SN | 实例数 |
|---------|--------|
| OR65M62QC2S243801867 | 5 |
| OR65M62QC2S243802484 | 5 |
| CR10M22RK2M243002877 | 5 |
| ORG2Q32QC2P242402291 | 2 |
| ORG2Q32QC2P242403031 | 2 |
| ORG2Q32QC2P242401942 | 2 |

## Cantor 平台集成

### 后端 API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/cloud-phones/sync` | POST | 同步云手机 |
| `/api/cloud-phones/dashboard` | GET | 仪表盘数据 |
| `/api/cloud-phones` | GET | 实例列表 |
| `/api/cloud-phones/{id}` | GET | 实例详情 |
| `/api/cloud-phones/{id}/start` | POST | 启动实例 |
| `/api/cloud-phones/{id}/stop` | POST | 停止实例 |
| `/api/cloud-phones/{id}/restart` | POST | 重启实例 |

### 前端页面

- **路径**: `/cloud-phones`
- **功能**:
  - 一键同步云手机
  - 统计卡片 (总数/运行/关机/创建中/异常)
  - 节点分布视图
  - 项目分布视图
  - 实例列表 (支持过滤)
  - 实例操作 (启动/停止/重启)
