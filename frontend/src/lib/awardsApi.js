import api from '@/lib/api';

/** Adjudicación (fase 8.6/8.7).
 * Awards: /organizations/{id}/sourcing-events/{eventId}/awards
 * Bandeja de aprobaciones: /organizations/{id}/award-approvals
 * Políticas: /organizations/{id}/approval-policies
 */

export async function listAwards(organizationId, eventId) {
  const { data } = await api.get(`/organizations/${organizationId}/sourcing-events/${eventId}/awards`);
  return data;
}

export async function proposeAward(organizationId, eventId, payload) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/awards`,
    {
      awarded_organization_id: payload.awardedOrganizationId,
      quotation_revision_id: payload.quotationRevisionId,
      justification: payload.justification || null,
      items: (payload.items || []).map((i) => ({
        sourcing_event_item_id: i.sourcingEventItemId,
        quantity: i.quantity,
        unit_price: i.unitPrice,
      })),
    },
  );
  return data.id;
}

export async function publishAward(organizationId, eventId, awardId) {
  await api.post(`/organizations/${organizationId}/sourcing-events/${eventId}/awards/${awardId}/publish`);
}

export async function listMyPendingApprovals(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/award-approvals`);
  return data;
}

export async function decideApproval(organizationId, approvalId, decision, comment) {
  await api.post(`/organizations/${organizationId}/award-approvals/${approvalId}/decide`, {
    decision,
    comment: comment || null,
  });
}

export async function listApprovalPolicies(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/approval-policies`);
  return data;
}

export async function upsertApprovalPolicy(organizationId, payload) {
  const { data } = await api.post(`/organizations/${organizationId}/approval-policies`, {
    step_order: payload.stepOrder,
    required_role_code: payload.requiredRoleCode,
    min_amount: payload.minAmount ?? 0,
    max_amount: payload.maxAmount ?? null,
  });
  return data.id;
}
