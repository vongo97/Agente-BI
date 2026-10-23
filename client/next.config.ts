import type { NextConfig } from "next";

// El backend se conecta desde el navegador, asi que su URL debe estar permitida por
// la CSP. Se deriva de NEXT_PUBLIC_API_URL (la misma variable que usa el cliente) en
// lugar de escribirla a mano: Render anade sufijos aleatorios al nombre del servicio
// y un host fijo en la CSP se queda obsoleto en silencio, bloqueando TODAS las
// llamadas con "Refused to connect because it violates the document's Content
// Security Policy".
const apiBaseUrl = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
const apiUrlNoScheme = apiBaseUrl.replace(/^https?:\/\//, "");

const connectSources = [
  "'self'",
  "http://127.0.0.1:8000",
  "http://localhost:8000",
  "ws://localhost:8000",
  "wss://localhost:8000",
  apiBaseUrl,
];

// CSP (P-07): se permite 'unsafe-eval' y 'unsafe-inline' para el runtime de Next.js
// hasta que se migren los scripts inline a externos o se agreguen nonces/hashes.
const cspHeader = `
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  img-src 'self' blob: data: https://lh3.googleusercontent.com;
  font-src 'self' https://fonts.gstatic.com;
  connect-src ${[...new Set(connectSources)].join(" ")};
  frame-src 'none';
  object-src 'none';
`.replace(/\s{2,}/g, ' ').trim();

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: cspHeader,
          },
        ],
      },
    ];
  },
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
