import api from '@/lib/api';

/** Llamadas al motor de matching:
 * /api/organizations/{id}/sourcing-events/{id}/matching/* (fase 6.4-6.7).
 */

export async function runMatching(organizationId, eventId) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/matching/run`,
  );
  return data;
}

export async function previewMatching(organizationId, eventId, weights) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/matching/preview`,
    { weights: weights || null },
  );
  return data;
}

export async function getLatestResults(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/matching/results`,
  );
  return data;
}
