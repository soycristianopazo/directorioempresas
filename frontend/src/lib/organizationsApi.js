import api from '@/lib/api';

/** Llamadas a /api/organizations/* y /api/invitations/*, /api/members/*. */

export async function createOrganization(payload) {
  const { data } = await api.post('/organizations', payload);
  return data.organization_id;
}

export async function getOrganization(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}`);
  return data;
}

export async function updateOrganization(organizationId, payload) {
  await api.put(`/organizations/${organizationId}`, payload);
}

export async function publishOrganization(organizationId) {
  await api.post(`/organizations/${organizationId}/publish`);
}

export async function switchOrganization(organizationId) {
  await api.post('/organizations/switch', { organization_id: organizationId });
}

export async function listTeam(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/team`);
  return data;
}

export async function listAssignableRoles(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/roles`);
  return data;
}

export async function listPendingInvitations(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/invitations`);
  return data;
}

export async function inviteMember({ organizationId, email, roleCode }) {
  const { data } = await api.post('/invitations', {
    organization_id: organizationId,
    email,
    role_code: roleCode,
  });
  return data;
}

export async function revokeInvitation(organizationId, invitationId) {
  await api.delete(`/invitations/${invitationId}`, { params: { organization_id: organizationId } });
}

export async function removeMember(organizationId, memberId) {
  await api.delete(`/members/${memberId}`, { params: { organization_id: organizationId } });
}

export async function changeMemberRoles(organizationId, memberId, roleCodes) {
  await api.put(`/members/${memberId}/roles`, {
    organization_id: organizationId,
    role_codes: roleCodes,
  });
}

export async function acceptInvitation(token) {
  const { data } = await api.post(`/invitations/${token}/accept`);
  return data.organization_id;
}
