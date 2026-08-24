import axios from 'axios';

/**
 * Cliente HTTP único de la aplicación.
 *
 * `REACT_APP_BACKEND_URL` es la convención de Emergent: en local apunta a
 * `http://localhost:8000`, y en despliegue la inyecta la plataforma. Todas
 * las rutas de la API cuelgan de `/api` — es el prefijo que el backend FastAPI
 * expone y que en desarrollo local además proxea craco.config.js.
 */
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  // true a propósito: el refresh token viaja en una cookie httpOnly que el
  // navegador no expone a JS. Sin withCredentials, el POST a /auth/refresh
  // saldría sin la cookie y el backend no tendría cómo identificar la sesión.
  withCredentials: true,
  timeout: 15000,
});

const ACCESS_TOKEN_KEY = 'directorio.access_token';

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token) {
  if (token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  }
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Refresco automático de sesión.
 *
 * El access token dura 15 minutos (ACCESS_TOKEN_MINUTES en el backend). Sin
 * esto, cualquier pantalla abierta más de 15 minutos empezaría a fallar con
 * 401 en la siguiente acción del usuario, que es la peor forma posible de
 * descubrir que la sesión expiró.
 *
 * El refresh token vive en una cookie httpOnly que pone el backend — nunca en
 * localStorage, para que un XSS que robe el access token de corta vida no
 * pueda además emitirse sesiones nuevas indefinidamente.
 *
 * `_retry` evita el bucle infinito si el propio /auth/refresh devuelve 401: en
 * ese caso la sesión de verdad terminó y hay que mandar a login, no reintentar
 * para siempre.
 */
/**
 * FastAPI/Pydantic manda `detail` como un array de objetos de validación
 * (`{type, loc, msg, ...}`) en un 422, no como string — a diferencia de
 * cualquier error de negocio (`HTTPException(detail="...")`), que siempre es
 * texto. Cada pantalla de la app lee `error.response?.data?.detail` como si
 * fuera texto (`{formError}`, `toast.error(...)`); pasarle el array crudo
 * revienta React con "Objects are not valid as a React child". Normalizar
 * acá, una vez, es más seguro que auditar cada uno de esos call sites.
 */
function normalizeErrorDetail(data) {
  if (!data || !Array.isArray(data.detail)) return;
  data.detail = data.detail
    .map((item) => {
      if (typeof item === 'string') return item;
      const field = Array.isArray(item?.loc) ? item.loc.filter((p) => p !== 'body').join('.') : null;
      const msg = item?.msg || 'Dato inválido';
      return field ? `${field}: ${msg}` : msg;
    })
    .join('; ');
}

let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;

    normalizeErrorDetail(response?.data);

    if (response?.status !== 401 || config._retry || config.url === '/auth/refresh') {
      return Promise.reject(error);
    }

    config._retry = true;

    try {
      refreshPromise ??= api
        .post('/auth/refresh')
        .then(({ data }) => {
          setAccessToken(data.access_token);
          return data.access_token;
        })
        .finally(() => {
          refreshPromise = null;
        });

      const newToken = await refreshPromise;
      config.headers.Authorization = `Bearer ${newToken}`;
      return api(config);
    } catch (refreshError) {
      setAccessToken(null);
      window.dispatchEvent(new CustomEvent('auth:session-expired'));
      return Promise.reject(refreshError);
    }
  },
);

export default api;
