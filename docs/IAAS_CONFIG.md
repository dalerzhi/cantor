# IaaS 平台配置

## CAStack 云平台

- **平台地址**: http://43.139.47.124:1800/
- **Access Key**: 91e28b4734d642b29c1ad64cbb44df8a
- **Secret Key**: a589615d6d144dd5aa3e776a9ac4f303

## API 探索结果

### 已确认信息
- 平台名称: CAStack 云平台
- 技术栈: Spring Boot (Java)
- API 前缀: `/api/v1/*`
- 认证端点: `/auth/oauth/token`

### 端点列表 (需认证)
- `GET /api/v1/phones` - 云手机列表
- `GET /api/v1/regions` - 区域列表
- `GET /api/v1/specs` - 规格列表
- `GET /api/v1/quota` - 配额查询

### 认证方式
❓ 待确认 - 可能是自定义签名算法

### 下一步
需要 IaaS 平台提供方提供：
1. API 文档 (Swagger/OpenAPI)
2. 认证方式说明 (签名算法)
3. 示例代码
