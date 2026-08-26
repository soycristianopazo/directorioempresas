import api from '@/lib/api';

/** Llamadas a /api/accreditation/programs/* y
 * /api/organizations/{id}/accreditation/* — postulación y estado de
 * acreditación del proveedor, fase 5.3-5.7.
 */

export async function listPrograms({ forOrganizationId } = {}) {
  const { data } = await api.get('/accreditation/programs', {
    params: forOrganizationId ? { for_organization_id: forOrganizationId } : undefined,
  });
  return data;
}

export async function getProgramDetail(programId) {
  const { data } = await api.get(`/accreditation/programs/${programId}`);
  return data;
}

export async function listEnrollments(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/accreditation/enrollments`);
  return data;
}

export async function getEnrollmentDetail(organizationId, enrollmentId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/accreditation/enrollments/${enrollmentId}`,
  );
  return data;
}

export async function enroll(organizationId, programId) {
  const { data } = await api.post(`/organizations/${organizationId}/accreditation/enrollments`, {
    program_id: programId,
  });
  return data.id;
}

export async function submitEvidence(
  organizationId,
  enrollmentId,
  { requirementId, documentVersionId, certificationId, declaredValue },
) {
  await api.post(
    `/organizations/${organizationId}/accreditation/enrollments/${enrollmentId}/evidence`,
    {
      requirement_id: requirementId,
      document_version_id: documentVersionId || null,
      certification_id: certificationId || null,
      declared_value: declaredValue || null,
    },
  );
}

export async function submitForReview(organizationId, enrollmentId) {
  await api.post(
    `/organizations/${organizationId}/accreditation/enrollments/${enrollmentId}/submit-for-review`,
  );
}

export async function respondToObservation(organizationId, enrollmentId) {
  await api.post(
    `/organizations/${organizationId}/accreditation/enrollments/${enrollmentId}/respond-to-observation`,
  );
}

export async function renewEnrollment(organizationId, enrollmentId) {
  await api.post(
    `/organizations/${organizationId}/accreditation/enrollments/${enrollmentId}/renew`,
  );
}

export async function getCertificate(organizationId, enrollmentId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/accreditation/enrollments/${enrollmentId}/certificate`,
  );
  return data;
}
