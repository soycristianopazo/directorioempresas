import api from '@/lib/api';

/** Llamadas a /api/organizations/{id}/requirements/* — la necesidad de
 * compra (fase 6.1), previa a un sourcing_event formal.
 */

export async function listRequirements(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/requirements`);
  return data;
}

export async function getRequirement(organizationId, requirementId) {
  const { data } = await api.get(`/organizations/${organizationId}/requirements/${requirementId}`);
  return data;
}

export async function createRequirement(organizationId, payload) {
  const { data } = await api.post(`/organizations/${organizationId}/requirements`, {
    name: payload.name,
    description: payload.description || null,
    primary_taxonomy_node_id: payload.primaryTaxonomyNodeId || null,
    industry_id: payload.industryId || null,
    needed_from: payload.neededFrom || null,
    needed_until: payload.neededUntil || null,
    duration_months: payload.durationMonths || null,
    estimated_budget: payload.estimatedBudget || null,
    currency_code: payload.currencyCode || null,
    commercial_terms: payload.commercialTerms || null,
    payment_terms: payload.paymentTerms || null,
    source: payload.source || 'FORM',
    raw_input_text: payload.rawInputText || null,
  });
  return data.id;
}

export async function addRequirementItem(organizationId, requirementId, item) {
  const { data } = await api.post(
    `/organizations/${organizationId}/requirements/${requirementId}/items`,
    {
      description: item.description,
      quantity: item.quantity,
      unit_code: item.unitCode || null,
      specifications: item.specifications || null,
      sort_order: item.sortOrder || 0,
    },
  );
  return data.id;
}

export async function addRequirementLocation(organizationId, requirementId, adminDivisionId) {
  const { data } = await api.post(
    `/organizations/${organizationId}/requirements/${requirementId}/locations`,
    null,
    { params: { admin_division_id: adminDivisionId } },
  );
  return data.id;
}
