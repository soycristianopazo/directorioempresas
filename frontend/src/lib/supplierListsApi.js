import api from '@/lib/api';

/** Llamadas a /api/organizations/{id}/supplier-lists/* — listas de
 * proveedores guardadas (favoritos), fase 4.9.
 */

export async function listSupplierLists(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/supplier-lists`);
  return data;
}

export async function createSupplierList(organizationId, { name, isSharedWithOrg = true }) {
  const { data } = await api.post(`/organizations/${organizationId}/supplier-lists`, {
    name,
    is_shared_with_org: isSharedWithOrg,
  });
  return data.id;
}

export async function deleteSupplierList(organizationId, listId) {
  await api.delete(`/organizations/${organizationId}/supplier-lists/${listId}`);
}

export async function listSupplierListItems(organizationId, listId) {
  const { data } = await api.get(`/organizations/${organizationId}/supplier-lists/${listId}/items`);
  return data;
}

export async function addSupplierListItem(organizationId, listId, { targetOrganizationId, note }) {
  const { data } = await api.post(`/organizations/${organizationId}/supplier-lists/${listId}/items`, {
    target_organization_id: targetOrganizationId,
    note: note || null,
  });
  return data.id;
}

export async function removeSupplierListItem(organizationId, listId, itemId) {
  await api.delete(`/organizations/${organizationId}/supplier-lists/${listId}/items/${itemId}`);
}
