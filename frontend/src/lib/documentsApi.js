import api from '@/lib/api';

/** Llamadas a /api/organizations/{id}/documents/* — repositorio único de
 * evidencia documental, fase 5.1/5.2.
 */

export async function listDocumentTypes() {
  const { data } = await api.get('/documents/types');
  return data;
}

export async function listDocuments(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/documents`);
  return data;
}

export async function listDocumentVersions(organizationId, documentId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/documents/${documentId}/versions`,
  );
  return data;
}

export async function uploadDocumentVersion(
  organizationId,
  { documentTypeId, file, issuedAt, validFrom, validUntil },
) {
  const form = new FormData();
  form.append('document_type_id', documentTypeId);
  if (issuedAt) form.append('issued_at', issuedAt);
  if (validFrom) form.append('valid_from', validFrom);
  if (validUntil) form.append('valid_until', validUntil);
  form.append('file', file);
  const { data } = await api.post(`/organizations/${organizationId}/documents/versions`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}
