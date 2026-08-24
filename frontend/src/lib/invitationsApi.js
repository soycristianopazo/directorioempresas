import api from '@/lib/api';

/** Invitaciones a proveedores y NDA del evento (fase 7.1/7.2).
 * Lado comprador: /organizations/{id}/sourcing-events/{eventId}/invitations
 * Lado proveedor: /organizations/{id}/sourcing-invitations (autoservicio) —
 * NO /organizations/{id}/invitations: ese path ya lo usa team.py para
 * invitaciones de miembros de equipo (choque de rutas real, encontrado en
 * vivo — ver el comentario en app/api/v1/invitations.py).
 */

// ─── Lado comprador ─────────────────────────────────────────────────────────

export async function listInvitations(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/invitations`,
  );
  return data;
}

export async function inviteSupplier(organizationId, eventId, payload) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/invitations`,
    {
      supplier_organization_id: payload.supplierOrganizationId,
      source: payload.source || 'MANUAL',
      match_score_snapshot: payload.matchScoreSnapshot ?? null,
    },
  );
  return data.id;
}

export async function disqualifyInvitation(organizationId, eventId, invitationId, reason) {
  await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/invitations/${invitationId}/disqualify`,
    { reason: reason || null },
  );
}

export async function getEventNda(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/invitations/nda`,
  );
  return data;
}

export async function upsertEventNda(organizationId, eventId, title, bodyText) {
  const { data } = await api.put(
    `/organizations/${organizationId}/sourcing-events/${eventId}/invitations/nda`,
    { title, body_text: bodyText },
  );
  return data.id;
}

// ─── Lado proveedor (autoservicio) ──────────────────────────────────────────

export async function listMyInvitations(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/sourcing-invitations`);
  return data;
}

export async function getInvitation(organizationId, invitationId) {
  const { data } = await api.get(`/organizations/${organizationId}/sourcing-invitations/${invitationId}`);
  return data;
}

export async function acceptNda(organizationId, invitationId) {
  await api.post(`/organizations/${organizationId}/sourcing-invitations/${invitationId}/accept-nda`);
}

export async function expressInterest(organizationId, invitationId) {
  await api.post(`/organizations/${organizationId}/sourcing-invitations/${invitationId}/interest`);
}

export async function confirmParticipation(organizationId, invitationId) {
  await api.post(
    `/organizations/${organizationId}/sourcing-invitations/${invitationId}/confirm-participation`,
  );
}

export async function declineInvitation(organizationId, invitationId, reasonCode) {
  await api.post(`/organizations/${organizationId}/sourcing-invitations/${invitationId}/decline`, {
    reason_code: reasonCode || null,
  });
}

export async function withdrawInvitation(organizationId, invitationId) {
  await api.post(`/organizations/${organizationId}/sourcing-invitations/${invitationId}/withdraw`);
}
