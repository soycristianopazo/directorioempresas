import api from '@/lib/api';

/** Llamadas a /api/reference/* — catálogos públicos, sin autenticación. */

export async function getCountries() {
  const { data } = await api.get('/reference/countries');
  return data;
}

export async function getCurrencies() {
  const { data } = await api.get('/reference/currencies');
  return data;
}

export async function getUnitsOfMeasure() {
  const { data } = await api.get('/reference/units-of-measure');
  return data;
}

export async function getLanguages() {
  const { data } = await api.get('/reference/languages');
  return data;
}

export async function getAdminDivisions({ country = 'CL', parentId = null } = {}) {
  const { data } = await api.get('/reference/admin-divisions', {
    params: { country, parent_id: parentId ?? undefined },
  });
  return data;
}

export async function searchSiiEconomicActivities(q, { limit = 30 } = {}) {
  const { data } = await api.get('/reference/sii-economic-activities', {
    params: { q, limit },
  });
  return data;
}
