import LoginForm from "./LoginForm";

// P-44: se comprueba la configuración en el servidor (las variables no son
// NEXT_PUBLIC), para no mandar al usuario a Google con client_id=undefined.
// force-dynamic: el valor debe leerse en cada petición, no quedar horneado en
// el build (si alguien añade las credenciales, no hace falta reconstruir).
export const dynamic = "force-dynamic";

export default function LoginPage() {
    // Se exigen AMBOS valores: con solo el id, Google rechaza el intercambio.
    const googleEnabled = Boolean(
        (process.env.AUTH_GOOGLE_ID || process.env.GOOGLE_CLIENT_ID) &&
        (process.env.AUTH_GOOGLE_SECRET || process.env.GOOGLE_CLIENT_SECRET)
    );
    const guestEnabled =
        process.env.NODE_ENV === "development" &&
        process.env.NEXT_PUBLIC_VERCEL_ENV !== "production";

    return <LoginForm googleEnabled={googleEnabled} guestEnabled={guestEnabled} />;
}
