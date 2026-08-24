import api from '@/lib/api';

/** Llamadas a /api/discover/* — búsqueda pública y perfil de organización,
 * consumidas por la experiencia de comprador autenticado (/buscar,
 * /comparar). La misma lógica sirve las páginas Jinja2 públicas
 * (/discover, /proveedores/:slug), fuera de esta SPA.
 */

export async function searchOfferings(params = {}, { signal } = {}) {
  const { data } = await api.get('/discover/search', {
    params: {
      q: params.q || undefined,
      taxonomy_node_ids: params.taxonomyNodeIds?.length ? params.taxonomyNodeIds : undefined,
      industry_ids: params.industryIds?.length ? params.industryIds : undefined,
      admin_division_ids: params.adminDivisionIds?.length ? params.adminDivisionIds : undefined,
      offering_type: params.offeringType || undefined,
      availability_status: params.availabilityStatus || undefined,
      page: params.page || 1,
      page_size: params.pageSize || 20,
    },
    // FastAPI espera arrays como `ids=a&ids=b`, no `ids[]=a&ids[]=b`
    // (la notación con corchetes que usa axios por defecto).
    paramsSerializer: { indexes: null },
    signal,
  });
  return data;
}

export async function getPublicOrganization(slug, { signal } = {}) {
  const { data } = await api.get(`/discover/organizations/${slug}`, { signal });
  return data;
}
