import api from '@/lib/api';

/** Llamadas a /api/admin/accreditation/* — backoffice de revisión y
 * autoría de programas, fase 5.5/5.6.
 */

export async function listReviewQueue(reviewStatus) {
  const { data } = await api.get('/admin/accreditation/queue', {
    params: reviewStatus ? { review_status: reviewStatus } : undefined,
  });
  return data;
}

export async function reviewFulfillment(fulfillmentId, { decision, observation }) {
  await api.post(`/admin/accreditation/fulfillments/${fulfillmentId}/review`, {
    decision,
    observation: observation || null,
  });
}

export async function decideEnrollment(enrollmentId, { decision, reason }) {
  await api.post(`/admin/accreditation/enrollments/${enrollmentId}/decide`, {
    decision,
    reason: reason || null,
  });
}

export async function createProgram({ code, name, description, validityMonths = 12 }) {
  const { data } = await api.post('/admin/accreditation/programs', {
    code,
    name,
    description: description || null,
    validity_months: validityMonths,
  });
  return data.id;
}

export async function createRequirementGroup(programId, { name, weight = 1, sortOrder = 0 }) {
  const { data } = await api.post(`/admin/accreditation/programs/${programId}/groups`, {
    name,
    weight,
    sort_order: sortOrder,
  });
  return data.id;
}

export async function createRequirement(programId, requirement) {
  const { data } = await api.post(`/admin/accreditation/programs/${programId}/requirements`, {
    group_id: requirement.groupId,
    requirement_kind: requirement.requirementKind,
    name: requirement.name,
    description: requirement.description || null,
    is_mandatory: requirement.isMandatory ?? true,
    weight: requirement.weight ?? 1,
    document_type_id: requirement.documentTypeId || null,
    certification_type_id: requirement.certificationTypeId || null,
    attribute_definition_id: requirement.attributeDefinitionId || null,
    sort_order: requirement.sortOrder ?? 0,
  });
  return data.id;
}
