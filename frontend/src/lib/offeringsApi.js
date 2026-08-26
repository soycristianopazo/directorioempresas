import api from '@/lib/api';

/** Llamadas a /api/organizations/{id}/offerings/* — el catálogo de oferta. */

export async function listOfferings(organizationId, { status } = {}) {
  const { data } = await api.get(`/organizations/${organizationId}/offerings`, {
    params: { offering_status: status || undefined },
  });
  return data;
}

export async function getOffering(organizationId, offeringId) {
  const { data } = await api.get(`/organizations/${organizationId}/offerings/${offeringId}`);
  return data;
}

export async function createOffering(organizationId, payload) {
  const { data } = await api.post(`/organizations/${organizationId}/offerings`, payload);
  return data.id;
}

export async function updateOffering(organizationId, offeringId, payload) {
  await api.put(`/organizations/${organizationId}/offerings/${offeringId}`, payload);
}

export async function publishOffering(organizationId, offeringId) {
  await api.post(`/organizations/${organizationId}/offerings/${offeringId}/publish`);
}

export async function setOfferingStatus(organizationId, offeringId, status) {
  await api.post(`/organizations/${organizationId}/offerings/${offeringId}/status`, { status });
}

export async function deleteOffering(organizationId, offeringId) {
  await api.delete(`/organizations/${organizationId}/offerings/${offeringId}`);
}

export async function getOfferingTaxonomyNodes(organizationId, offeringId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/offerings/${offeringId}/taxonomy-nodes`,
  );
  return data;
}

export async function setOfferingTaxonomyNodes(organizationId, offeringId, nodes) {
  await api.put(`/organizations/${organizationId}/offerings/${offeringId}/taxonomy-nodes`, { nodes });
}

export async function getOfferingIndustries(organizationId, offeringId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/offerings/${offeringId}/industries`,
  );
  return data;
}

export async function setOfferingIndustries(organizationId, offeringId, industryIds) {
  await api.put(`/organizations/${organizationId}/offerings/${offeringId}/industries`, {
    industry_ids: industryIds,
  });
}

export async function getOfferingTags(organizationId, offeringId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/offerings/${offeringId}/tags`,
  );
  return data;
}

export async function setOfferingTags(organizationId, offeringId, tags) {
  await api.put(`/organizations/${organizationId}/offerings/${offeringId}/tags`, { tags });
}

export async function getOfferingTerritories(organizationId, offeringId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/offerings/${offeringId}/territories`,
  );
  return data;
}

export async function addOfferingTerritory(organizationId, offeringId, payload) {
  const { data } = await api.post(
    `/organizations/${organizationId}/offerings/${offeringId}/territories`,
    payload,
  );
  return data.id;
}

export async function removeOfferingTerritory(organizationId, offeringId, territoryId) {
  await api.delete(`/organizations/${organizationId}/offerings/${offeringId}/territories/${territoryId}`);
}

export async function getOfferingPricing(organizationId, offeringId) {
  const { data } = await api.get(`/organizations/${organizationId}/offerings/${offeringId}/pricing`);
  return data;
}

export async function setOfferingPricing(organizationId, offeringId, payload) {
  await api.put(`/organizations/${organizationId}/offerings/${offeringId}/pricing`, payload);
}

export async function listOfferingMedia(organizationId, offeringId) {
  const { data } = await api.get(`/organizations/${organizationId}/offerings/${offeringId}/media`);
  return data;
}

export async function uploadOfferingMedia(organizationId, offeringId, file) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post(
    `/organizations/${organizationId}/offerings/${offeringId}/media`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return data;
}

export async function deleteOfferingMedia(organizationId, offeringId, mediaId) {
  await api.delete(`/organizations/${organizationId}/offerings/${offeringId}/media/${mediaId}`);
}

export async function listOfferingDocuments(organizationId, offeringId) {
  const { data } = await api.get(`/organizations/${organizationId}/offerings/${offeringId}/documents`);
  return data;
}

export async function uploadOfferingDocument(organizationId, offeringId, { name, file, isPublic = true }) {
  const form = new FormData();
  form.append('name', name);
  form.append('is_public', String(isPublic));
  form.append('file', file);
  const { data } = await api.post(
    `/organizations/${organizationId}/offerings/${offeringId}/documents`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return data;
}

export async function deleteOfferingDocument(organizationId, offeringId, documentId) {
  await api.delete(`/organizations/${organizationId}/offerings/${offeringId}/documents/${documentId}`);
}

// ─── Ofertas (deals) ──────────────────────────────────────────────────────

export async function listOrgDeals(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/deals`);
  return data;
}

export async function listDeals(organizationId, offeringId) {
  const { data } = await api.get(`/organizations/${organizationId}/offerings/${offeringId}/deals`);
  return data;
}

export async function createDeal(organizationId, offeringId, payload) {
  const { data } = await api.post(
    `/organizations/${organizationId}/offerings/${offeringId}/deals`,
    {
      deal_price: payload.dealPrice,
      original_price: payload.originalPrice || null,
      currency_code: payload.currencyCode,
      unit_code: payload.unitCode || null,
      stock_quantity: payload.stockQuantity || null,
      expires_at: payload.expiresAt || null,
    },
  );
  return data.id;
}

export async function updateDealStock(organizationId, offeringId, dealId, stockRemaining) {
  await api.put(
    `/organizations/${organizationId}/offerings/${offeringId}/deals/${dealId}/stock`,
    { stock_remaining: stockRemaining },
  );
}

export async function cancelDeal(organizationId, offeringId, dealId) {
  await api.post(
    `/organizations/${organizationId}/offerings/${offeringId}/deals/${dealId}/cancel`,
  );
}

export async function listOfferingAttributeValues(organizationId, offeringId) {
  const { data } = await api.get(`/organizations/${organizationId}/offerings/${offeringId}/attributes`);
  return data;
}

export async function setOfferingAttributeValue(organizationId, offeringId, payload) {
  const { data } = await api.put(
    `/organizations/${organizationId}/offerings/${offeringId}/attributes`,
    payload,
  );
  return data.id;
}
