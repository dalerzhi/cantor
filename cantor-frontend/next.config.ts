import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // 移除 basePath，让 Nginx 处理路径路由
  // basePath: '/dashboard',
  
  // 重写 API 请求到后端
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://cantor-brain:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
