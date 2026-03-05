import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // 移除 basePath，让 Nginx 处理路径路由
  // basePath: '/dashboard',
};

export default nextConfig;
