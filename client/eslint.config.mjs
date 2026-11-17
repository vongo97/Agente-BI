import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // `no-unused-vars` con `ignoreRestSiblings`: el patron idiomatico
    // `const { clave, ...resto } = obj` se usa para OMITIR una clave, asi que
    // el binding de la clave omitida es intencionalmente no usado (p. ej. en
    // Sidebar.tsx, que quita el campo `audit` del historial). Sin esta opcion
    // ESLint marca ese binding como variable sin usar.
    rules: {
      "@typescript-eslint/no-unused-vars": ["warn", { ignoreRestSiblings: true }],
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
