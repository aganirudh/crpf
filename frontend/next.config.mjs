import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  typedRoutes: true,
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
    return [
      // Backend mounts routers under `/api/v1/*`; keep `/api/*` on the frontend
      // and forward it as-is to the backend.
      { source: "/api/:path*", destination: `${api}/api/:path*` },
    ];
  },
};

export default nextConfig;
