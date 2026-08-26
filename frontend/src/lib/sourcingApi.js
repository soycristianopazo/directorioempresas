import api from '@/lib/api';

/** Llamadas a /api/organizations/{id}/sourcing-events/* — el proceso de
 * sourcing y su estructura (fase 6.2/6.3).
 */

export async function listEvents(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/sourcing-events`);
  return data;
}

export async function getEvent(organizationId, eventId) {
  const { data } = await api.get(`/organizations/${organizationId}/sourcing-events/${eventId}`);
  return data;
}

export async function createEvent(organizationId, payload) {
  const { data } = await api.post(`/organizations/${organizationId}/sourcing-events`, {
    name: payload.name,
    description: payload.description || null,
    event_type: payload.eventType || 'RFQ',
    requirement_id: payload.requirementId || null,
    visibility: payload.visibility || 'PRIVATE',
    bid_mode: payload.bidMode || 'OPEN',
    currency_code: payload.currencyCode || null,
    estimated_amount: payload.estimatedAmount || null,
    requires_nda: payload.requiresNda || false,
    requires_accreditation_program_id: payload.requiresAccreditationProgramId || null,
    max_invitations: payload.maxInvitations || null,
    matching_weights: payload.matchingWeights || null,
  });
  return data.id;
}

/** PUT reemplaza el evento completo (UpdateSourcingEventRequest no es
 * parcial) — `event` es el objeto ya cargado por getEvent(), `overrides`
 * solo los campos que cambian. */
export async function updateEvent(organizationId, eventId, event, overrides = {}) {
  const merged = { ...event, ...overrides };
  await api.put(`/organizations/${organizationId}/sourcing-events/${eventId}`, {
    name: merged.name,
    description: merged.description || null,
    visibility: merged.visibility,
    bid_mode: merged.bid_mode,
    currency_code: merged.currency_code || null,
    estimated_amount: merged.estimated_amount || null,
    requires_nda: merged.requires_nda || false,
    requires_accreditation_program_id: merged.requires_accreditation_program_id || null,
    max_invitations: merged.max_invitations || null,
    matching_weights: merged.matching_weights || null,
  });
}

export async function publishEvent(organizationId, eventId) {
  await api.post(`/organizations/${organizationId}/sourcing-events/${eventId}/publish`);
}

export async function cancelEvent(organizationId, eventId) {
  await api.post(`/organizations/${organizationId}/sourcing-events/${eventId}/cancel`);
}

export async function declareVoid(organizationId, eventId, reason) {
  await api.post(`/organizations/${organizationId}/sourcing-events/${eventId}/void`, {
    reason: reason || null,
  });
}

export async function addItem(organizationId, eventId, item) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/items`,
    {
      description: item.description,
      quantity: item.quantity,
      unit_code: item.unitCode || null,
      taxonomy_node_id: item.taxonomyNodeId || null,
      lot_id: item.lotId || null,
      is_optional: item.isOptional || false,
      sort_order: item.sortOrder || 0,
    },
  );
  return data.id;
}

export async function addCriterion(organizationId, eventId, criterion) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/criteria`,
    {
      criterion_type: criterion.criterionType,
      requirement_level: criterion.requirementLevel || 'MUST_HAVE',
      is_blocking: criterion.isBlocking ?? true,
      weight: criterion.weight ?? 1,
      sort_order: criterion.sortOrder || 0,
      description: criterion.description || null,
      attribute_definition_id: criterion.attributeDefinitionId || null,
      operator: criterion.operator || null,
      value_text: criterion.valueText || null,
      value_number: criterion.valueNumber ?? null,
      value_number_max: criterion.valueNumberMax ?? null,
      value_boolean: criterion.valueBoolean ?? null,
      value_date: criterion.valueDate || null,
      value_date_max: criterion.valueDateMax || null,
      value_options: criterion.valueOptions || null,
      certification_type_id: criterion.certificationTypeId || null,
      accreditation_program_id: criterion.accreditationProgramId || null,
      admin_division_id: criterion.adminDivisionId || null,
      max_mobilization_days: criterion.maxMobilizationDays ?? null,
      industry_id: criterion.industryId || null,
      min_years: criterion.minYears ?? null,
      min_capacity: criterion.minCapacity ?? null,
    },
  );
  return data.id;
}

export async function deleteCriterion(organizationId, eventId, criterionId) {
  await api.delete(
    `/organizations/${organizationId}/sourcing-events/${eventId}/criteria/${criterionId}`,
  );
}
