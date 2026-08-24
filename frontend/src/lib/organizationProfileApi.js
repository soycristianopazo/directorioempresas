import api from '@/lib/api';

/** Llamadas a /api/organizations/{id}/locations, /contacts, /media,
 * /industries, /territories.
 */

// ─── Ubicaciones ─────────────────────────────────────────────────────────────

export async function getLocations(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/locations`);
  return data;
}

export async function createLocation(organizationId, payload) {
  const { data } = await api.post(`/organizations/${organizationId}/locations`, payload);
  return data.id;
}

export async function updateLocation(organizationId, locationId, payload) {
  await api.put(`/organizations/${organizationId}/locations/${locationId}`, payload);
}

export async function deactivateLocation(organizationId, locationId) {
  await api.post(`/organizations/${organizationId}/locations/${locationId}/deactivate`);
}

// ─── Contactos ───────────────────────────────────────────────────────────────

export async function getContacts(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/contacts`);
  return data;
}

export async function createContact(organizationId, payload) {
  const { data } = await api.post(`/organizations/${organizationId}/contacts`, payload);
  return data.id;
}

export async function updateContact(organizationId, contactId, payload) {
  await api.put(`/organizations/${organizationId}/contacts/${contactId}`, payload);
}

export async function deactivateContact(organizationId, contactId) {
  await api.post(`/organizations/${organizationId}/contacts/${contactId}/deactivate`);
}

// ─── Media (logo / banner) ────────────────────────────────────────────────────

export async function getMedia(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/media`);
  return data;
}

export async function uploadMedia(organizationId, { mediaType, file, altText }) {
  const form = new FormData();
  form.append('media_type', mediaType);
  if (altText) form.append('alt_text', altText);
  form.append('file', file);
  const { data } = await api.post(`/organizations/${organizationId}/media`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function deleteMedia(organizationId, mediaId) {
  await api.delete(`/organizations/${organizationId}/media/${mediaId}`);
}

// ─── Industrias ──────────────────────────────────────────────────────────────

export async function getOrganizationIndustries(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/industries`);
  return data;
}

export async function setOrganizationIndustry(organizationId, payload) {
  await api.put(`/organizations/${organizationId}/industries`, payload);
}

export async function removeOrganizationIndustry(organizationId, industryId) {
  await api.delete(`/organizations/${organizationId}/industries/${industryId}`);
}

// ─── Territorios ─────────────────────────────────────────────────────────────

export async function getOrganizationTerritories(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/territories`);
  return data;
}

export async function addOrganizationTerritory(organizationId, adminDivisionId) {
  const { data } = await api.post(`/organizations/${organizationId}/territories`, {
    admin_division_id: adminDivisionId,
  });
  return data.id;
}

export async function removeOrganizationTerritory(organizationId, territoryId) {
  await api.delete(`/organizations/${organizationId}/territories/${territoryId}`);
}
