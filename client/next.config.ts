import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    let apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    
    // Si la URL no empieza con http o /, le añadimos http:// para evitar errores en Render/Vercel
    if (!apiUrl.startsWith('http') && !apiUrl.startsWith('/')) {
      apiUrl = `http://${apiUrl}`;
    }

    return [
      {
        source: "/backend/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
