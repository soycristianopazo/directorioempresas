import api from '@/lib/api';

/** Vendor List / AVL (fase 8.8). Nunca visible al proveedor. */

export async function listRelationships(organizationId, statusFilter) {
  const { data } = await api.get(`/organizations/${organizationId}/vendor-list`, {
    params: statusFilter ? { status: statusFilter } : {},
  });
  return data;
}

export async function setRelationshipStatus(organizationId, supplierOrganizationId, status) {
  const { data } = await api.put(`/organizations/${organizationId}/vendor-list/relationships`, {
    supplier_organization_id: supplierOrganizationId,
    status,
  });
  return data.id;
}

export async function listNotes(organizationId, relationshipId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/vendor-list/relationships/${relationshipId}/notes`,
  );
  return data;
}

export async function addNote(organizationId, relationshipId, body) {
  const { data } = await api.post(
    `/organizations/${organizationId}/vendor-list/relationships/${relationshipId}/notes`,
    { body },
  );
  return data.id;
}
