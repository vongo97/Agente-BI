import Credentials from "next-auth/providers/credentials"

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  secret: process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET,
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID || process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.AUTH_GOOGLE_SECRET || process.env.GOOGLE_CLIENT_SECRET,
      checks: ['none'],
    }),
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
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async session({ session, token }) {
      return session;
    },
  },
})