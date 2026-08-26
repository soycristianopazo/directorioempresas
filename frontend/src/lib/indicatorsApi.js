/** Indicadores económicos públicos de Chile — mindicador.cl, sin API key,
 * CORS habilitado para consumo directo desde el navegador. A diferencia del
 * resto de las llamadas del proyecto, esto NO pasa por el backend propio:
 * es un dato público sin relación con la sesión del usuario ni con RLS, y
 * mindicador.cl ya resuelve la caché/actualización diaria por su cuenta —
 * proxyearlo por FastAPI solo agregaría un salto de red sin ganar nada. */

const INDICATORS_URL = 'https://mindicador.cl/api';

export async function getIndicators({ signal } = {}) {
  const response = await fetch(INDICATORS_URL, { signal });
  if (!response.ok) {
    throw new Error(`mindicador.cl respondió ${response.status}`);
  }
  const data = await response.json();
  return {
    uf: data.uf?.valor ?? null,
    dolar: data.dolar?.valor ?? null,
    euro: data.euro?.valor ?? null,
  };
}
