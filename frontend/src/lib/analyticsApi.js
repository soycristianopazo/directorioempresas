import api from '@/lib/api';

/** Analítica agregada del marketplace (fase 8.9). */

export async function getBuyerSummary(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/analytics/buyer-summary`);
  return data;
}

export async function getSupplierSummary(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/analytics/supplier-summary`);
  return data;
}
