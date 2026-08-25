import api from '@/lib/api';

/** Plantillas, comité, evaluaciones y comparador (fase 8.1-8.4).
 * Plantillas: /organizations/{id}/evaluation-templates (nivel organización)
 * Setup/comité/comparador: /organizations/{id}/sourcing-events/{eventId}/evaluations/*
 */

// ─── Plantillas ─────────────────────────────────────────────────────────────

export async function listTemplates(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/evaluation-templates`);
  return data;
}

export async function getTemplate(organizationId, templateId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/evaluation-templates/${templateId}`,
  );
  return data;
}

export async function createTemplate(organizationId, { name, description, criteria }) {
  const { data } = await api.post(`/organizations/${organizationId}/evaluation-templates`, {
    name,
    description: description || null,
    criteria: (criteria || []).map((c, i) => ({
      dimension: c.dimension,
      name: c.name,
      description: c.description || null,
      weight: c.weight ?? 1,
      sort_order: c.sortOrder ?? i,
    })),
  });
  return data.id;
}

// ─── Setup del evento ───────────────────────────────────────────────────────

export async function getSetup(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/evaluations/setup`,
  );
  return data;
}

export async function applyTemplate(organizationId, eventId, templateId) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/evaluations/setup`,
    { template_id: templateId },
  );
  return data.id;
}

// ─── Comité ──────────────────────────────────────────────────────────────────

export async function listCommittee(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/evaluations/committee`,
  );
  return data;
}

export async function assignCommittee(organizationId, eventId, assignments) {
  await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/evaluations/committee`,
    {
      assignments: assignments.map((a) => ({
        organization_member_id: a.organizationMemberId,
        dimension: a.dimension,
        can_view_commercial: !!a.canViewCommercial,
      })),
    },
  );
}

// ─── Comparador ──────────────────────────────────────────────────────────────

export async function getComparator(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/evaluations/comparator`,
  );
  return data;
}

export async function runComparator(organizationId, eventId) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/evaluations/comparator/run`,
  );
  return data;
}

// ─── Autoservicio del evaluador ─────────────────────────────────────────────

export async function getMyEvaluationView(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/evaluations/mine`,
  );
  return data;
}

export async function submitScore(organizationId, eventId, payload) {
  await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/evaluations/mine/scores`,
    {
      quotation_id: payload.quotationId,
      evaluation_criterion_id: payload.evaluationCriterionId,
      score: payload.score,
      comment: payload.comment || null,
      evidence_document_id: payload.evidenceDocumentId || null,
    },
  );
}

export async function submitEvaluation(organizationId, eventId, quotationId, overallComment) {
  await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/evaluations/mine/submit`,
    { quotation_id: quotationId, overall_comment: overallComment || null },
  );
}
