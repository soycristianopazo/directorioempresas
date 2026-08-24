# Frontend — Directorio de Empresas

App autenticada del proyecto (dashboard, empresa, equipo). Las páginas
públicas indexables (`/proveedores/[slug]`, `/discover`) las sirve el backend
con Jinja2 — ver `../docs/01-ARQUITECTURA.md` y la decisión registrada en
`../CHANGELOG.md`.

## Stack

CRA 5 + Craco · JavaScript (sin TypeScript) · Tailwind 3.4 + shadcn/ui sobre
Radix · React Router 7 · React Hook Form + Zod · Axios · Leaflet/React-Leaflet
· Recharts · date-fns · Yarn 1.22 (nunca npm).

## Arranque

```bash
yarn install
cp .env.example .env
yarn start
```

Requiere el backend corriendo en `REACT_APP_BACKEND_URL` (por defecto
`http://localhost:8000`). En desarrollo, `craco.config.js` proxea `/api` hacia
esa URL para evitar CORS.

## Estructura

```
src/
├── App.jsx                 orden de providers + router
├── index.js                punto de entrada
├── components/ui/          primitivos shadcn/ui (button, input, card, …)
├── context/
│   ├── AuthContext.jsx     sesión: login, registro, refresh, organización activa
│   └── I18nContext.jsx     i18n propio (sin librería externa)
├── hooks/                  hooks compartidos
├── lib/
│   ├── api.js               cliente Axios único, con refresh automático de token
│   └── utils.js             cn() — merge de clases Tailwind
├── pages/                  una página por ruta
├── router/
│   ├── index.jsx            definición de rutas
│   └── ProtectedRoute.jsx   puerta de las rutas privadas
└── styles/globals.css      tokens de diseño (convención shadcn, HSL)
```

## Autenticación

El access token vive en memoria/`localStorage` y expira en 15 minutos. El
refresh token vive en una cookie `httpOnly` que pone el backend — nunca en
`localStorage`, para que un XSS que robe el access token de corta vida no
pueda además emitir sesiones nuevas indefinidamente.

`src/lib/api.js` reintenta automáticamente una petición que falló con 401,
refrescando el token primero. Si el refresh también falla, dispara el evento
`auth:session-expired`, que `AuthContext` escucha para limpiar la sesión.

## Convenciones

- **Nunca `npm`.** El lockfile es `yarn.lock`; mezclar gestores produce dos
  árboles de dependencias inconsistentes.
- **Alias `@/`** apunta a `src/`. Configurado en `craco.config.js` (webpack) y
  `jsconfig.json` (autocompletado del editor) — hay que mantener los dos en
  sincronía si cambia.
- Componentes de UI genéricos van en `components/ui/`; los específicos de una
  página, junto a la página que los usa.
