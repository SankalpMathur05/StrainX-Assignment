import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";

const nextConfig: NextConfig = {
  // Dev only: forward /api/py/* to the local FastAPI server (npm run dev starts both).
  // In production, vercel.json routes /api/py/* to the Python function instead.
  async rewrites() {
    if (!isDev) return [];
    return [
      {
        source: "/api/py/:path*",
        destination: "http://127.0.0.1:8000/api/py/:path*",
      },
    ];
  },
};

export default nextConfig;
