import api from '@/lib/api';

/** Llamadas a /api/taxonomy/*, /api/industries/*, /api/admin/taxonomy/*,
 * /api/admin/industries/*.
 */

// ─── Lectura pública ─────────────────────────────────────────────────────────

export async function getTaxonomyTree() {
  const { data } = await api.get('/taxonomy/nodes');
  return data;
}

export async function getNodeAttributes(nodeId) {
  const { data } = await api.get(`/taxonomy/nodes/${nodeId}/attributes`);
  return data;
}

export async function getIndustries() {
  const { data } = await api.get('/industries');
  return data;
}

// ─── Administración (platform admin) ────────────────────────────────────────

export async function createTaxonomyNode(payload) {
  const { data } = await api.post('/admin/taxonomy/nodes', payload);
  return data.id;
}

export async function updateTaxonomyNode(nodeId, payload) {
  await api.put(`/admin/taxonomy/nodes/${nodeId}`, payload);
}

export async function deactivateTaxonomyNode(nodeId) {
  await api.post(`/admin/taxonomy/nodes/${nodeId}/deactivate`);
}

export async function linkAttributeToNode(nodeId, payload) {
  const { data } = await api.post(`/admin/taxonomy/nodes/${nodeId}/attributes`, payload);
  return data.id;
}

export async function createAttributeDefinition(payload) {
  const { data } = await api.post('/admin/taxonomy/attribute-definitions', payload);
  return data.id;
}

export async function createIndustry(payload) {
  const { data } = await api.post('/admin/industries', payload);
  return data.id;
}

export async function updateIndustry(industryId, payload) {
  await api.put(`/admin/industries/${industryId}`, payload);
}

export async function deactivateIndustry(industryId) {
  await api.post(`/admin/industries/${industryId}/deactivate`);
}
