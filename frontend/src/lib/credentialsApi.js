import api from '@/lib/api';

/** Llamadas a /api/certification-types y
 * /api/organizations/{id}/certifications, /client-references, /case-studies.
 */

export async function getCertificationTypes() {
  const { data } = await api.get('/certification-types');
  return data;
}

export async function listCertifications(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/certifications`);
  return data;
}

export async function createCertification(organizationId, payload) {
  const { data } = await api.post(`/organizations/${organizationId}/certifications`, payload);
  return data.id;
}

export async function deleteCertification(organizationId, certificationId) {
  await api.delete(`/organizations/${organizationId}/certifications/${certificationId}`);
}

export async function listClientReferences(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/client-references`);
  return data;
}

export async function createClientReference(organizationId, payload) {
  const { data } = await api.post(`/organizations/${organizationId}/client-references`, payload);
  return data.id;
}

export async function deleteClientReference(organizationId, referenceId) {
  await api.delete(`/organizations/${organizationId}/client-references/${referenceId}`);
}

export async function listCaseStudies(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/case-studies`);
  return data;
}

export async function createCaseStudy(organizationId, payload) {
  const { data } = await api.post(`/organizations/${organizationId}/case-studies`, payload);
  return data.id;
}

export async function updateCaseStudy(organizationId, caseStudyId, payload) {
  await api.put(`/organizations/${organizationId}/case-studies/${caseStudyId}`, payload);
}

export async function deleteCaseStudy(organizationId, caseStudyId) {
  await api.delete(`/organizations/${organizationId}/case-studies/${caseStudyId}`);
}

export async function setCaseStudyTaxonomy(organizationId, caseStudyId, nodeIds) {
  await api.put(`/organizations/${organizationId}/case-studies/${caseStudyId}/taxonomy-nodes`, {
    node_ids: nodeIds,
  });
}

export async function listCaseStudyMedia(organizationId, caseStudyId) {
  const { data } = await api.get(`/organizations/${organizationId}/case-studies/${caseStudyId}/media`);
  return data;
}

export async function uploadCaseStudyMedia(organizationId, caseStudyId, { file, caption }) {
  const form = new FormData();
  if (caption) form.append('caption', caption);
  form.append('file', file);
  const { data } = await api.post(
    `/organizations/${organizationId}/case-studies/${caseStudyId}/media`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return data;
}

export async function deleteCaseStudyMedia(organizationId, caseStudyId, mediaId) {
  await api.delete(`/organizations/${organizationId}/case-studies/${caseStudyId}/media/${mediaId}`);
}
