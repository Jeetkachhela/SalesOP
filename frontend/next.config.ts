import type { NextConfig } from "next";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
let backendOrigin = "";
if (apiUrl) {
  try {
    const parsed = new URL(apiUrl);
    backendOrigin = ` ${parsed.origin}`;
  } catch (e) {
    backendOrigin = ` ${apiUrl.split("/api")[0]}`;
  }
}

const connectSrc = `connect-src 'self' https://sales-op-68o2.vercel.app https://sales-op-6802.vercel.app https://sales-op-6802-3uuzfff4u-jeetkachhelas-projects.vercel.app https://*.vercel.app http://localhost:3000 http://localhost:8000 http://127.0.0.1:8000 https://*.onrender.com${backendOrigin};`;

const nextConfig: NextConfig = {
  productionBrowserSourceMaps: false, // Completely disable source maps exposure in production
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; ${connectSrc} frame-ancestors 'none';`
          },
          {
            key: "X-Frame-Options",
            value: "DENY"
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff"
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin"
          }
        ]
      }
    ];
  }
};

export default nextConfig;
