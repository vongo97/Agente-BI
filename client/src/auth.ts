import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Credentials from "next-auth/providers/credentials"

const isProd = process.env.NODE_ENV === "production";

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  secret: process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET,
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID || process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.AUTH_GOOGLE_SECRET || process.env.GOOGLE_CLIENT_SECRET,
    }),
    ...(!isProd ? [
      Credentials({
        name: "Invitado",
        credentials: {},
        async authorize() {
          // En local, permitimos acceso como invitado
          return { 
            id: "guest-id", 
            name: "Usuario Invitado", 
            email: "invitado@agente-bi.local",
            image: "https://ui-avatars.com/api/?name=Invitado&background=0D8ABC&color=fff"
          }
        }
      })
    ] : [])
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async session({ session }) {
      if (session.user && session.user.email) {
        const envSecret = process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET;
        const isProd = process.env.NODE_ENV === "production";
        if (!envSecret && isProd) {
          throw new Error("Error de seguridad: Falta configurar AUTH_SECRET o NEXTAUTH_SECRET en producción.");
        }
        const secret = envSecret || "secreto-desarrollo-por-defecto";
        try {
          // Generar JWT HS256 simple firmado de forma nativa con Web Crypto API
          const header = { alg: "HS256", typ: "JWT" };
          const now = Math.floor(Date.now() / 1000);
          const payload = {
            user_id: session.user.email,
            iat: now,
            exp: now + 24 * 60 * 60, // 24 horas
          };

          const base64UrlEncode = (str: string) => {
            return btoa(unescape(encodeURIComponent(str)))
              .replace(/=/g, "")
              .replace(/\+/g, "-")
              .replace(/\//g, "_");
          };

          const headerStr = base64UrlEncode(JSON.stringify(header));
          const payloadStr = base64UrlEncode(JSON.stringify(payload));
          const dataToSign = `${headerStr}.${payloadStr}`;

          const enc = new TextEncoder();
          const key = await crypto.subtle.importKey(
            "raw",
            enc.encode(secret),
            { name: "HMAC", hash: "SHA-256" },
            false,
            ["sign"]
          );

          const signature = await crypto.subtle.sign("HMAC", key, enc.encode(dataToSign));
          const signatureBytes = new Uint8Array(signature);
          
          let binary = "";
          for (let i = 0; i < signatureBytes.byteLength; i++) {
            binary += String.fromCharCode(signatureBytes[i]);
          }
          const signatureBase64 = btoa(binary)
            .replace(/=/g, "")
            .replace(/\+/g, "-")
            .replace(/\//g, "_");

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (session as any).accessToken = `${dataToSign}.${signatureBase64}`;
        } catch (err) {
          console.error("Error al generar auth token:", err);
        }
      }
      return session;
    },
  },
})