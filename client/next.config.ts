import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/backend/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
  // Increase timeout for long-running AI requests
  experimental: {
    proxyTimeout: 300000, // 5 minutes
  },
};

export default nextConfig;
