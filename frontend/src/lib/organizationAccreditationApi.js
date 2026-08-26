import api from '@/lib/api';

/** Llamadas a /api/organizations/{id}/accreditation/review/* — revisión de
 * programas propios (owner_scope=ORGANIZATION), fase 9. Mismo estilo que
 * adminAccreditationApi.js, pero acotado a UNA organización — el comprador
 * dueño de sus propios programas.
 */

export async function listOwnReviewQueue(organizationId, reviewStatus) {
  const { data } = await api.get(`/organizations/${organizationId}/accreditation/review/queue`, {
    params: reviewStatus ? { review_status: reviewStatus } : undefined,
  });
  return data;
}

export async function reviewFulfillment(organizationId, fulfillmentId, { decision, observation }) {
  await api.post(
    `/organizations/${organizationId}/accreditation/review/fulfillments/${fulfillmentId}/review`,
    { decision, observation: observation || null },
  );
}

export async function decideEnrollment(organizationId, enrollmentId, { decision, reason }) {
  await api.post(
    `/organizations/${organizationId}/accreditation/review/enrollments/${enrollmentId}/decide`,
    { decision, reason: reason || null },
  );
}
