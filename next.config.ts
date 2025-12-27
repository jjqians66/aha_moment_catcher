import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Allow Python API routes to work alongside Next.js
  async rewrites() {
    return [];
  },
};

export default nextConfig;
