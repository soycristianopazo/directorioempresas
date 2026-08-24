import api from '@/lib/api';

/** Mensajería (fase 7.8). Actualizaciones en vivo por POLLING — no Realtime
 * (el proyecto no usa Supabase en el navegador). listMessages(after) es el
 * contrato de polling: el llamador reintenta cada pocos segundos pasando el
 * cursor `after` = created_at del último mensaje recibido.
 */

export async function listConversations(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/conversations`);
  return data;
}

export async function getOrCreateConversation(organizationId, contextType, contextId, participantOrganizationIds) {
  const { data } = await api.post(`/organizations/${organizationId}/conversations`, {
    context_type: contextType,
    context_id: contextId,
    participant_organization_ids: participantOrganizationIds || [],
  });
  return data.id;
}

export async function listMessages(organizationId, conversationId, after) {
  const { data } = await api.get(
    `/organizations/${organizationId}/conversations/${conversationId}/messages`,
    { params: after ? { after } : {} },
  );
  return data;
}

export async function sendMessage(organizationId, conversationId, body) {
  const { data } = await api.post(
    `/organizations/${organizationId}/conversations/${conversationId}/messages`,
    { body },
  );
  return data;
}

export async function markConversationRead(organizationId, conversationId) {
  await api.post(`/organizations/${organizationId}/conversations/${conversationId}/read`);
}

export async function uploadAttachment(organizationId, conversationId, messageId, file) {
  const form = new FormData();
  form.append('file', file);
  form.append('message_id', messageId);
  const { data } = await api.post(
    `/organizations/${organizationId}/conversations/${conversationId}/attachments`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return data;
}
