import api from '@/lib/api';

/** Preguntas y respuestas del evento (fase 7.4). */

export async function listQuestions(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/questions`,
  );
  return data;
}

export async function askQuestion(organizationId, eventId, body) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/questions`,
    { body },
  );
  return data.id;
}

export async function answerQuestion(organizationId, eventId, questionId, body, visibility) {
  await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/questions/${questionId}/answer`,
    { body, visibility: visibility || 'ALL_PARTICIPANTS' },
  );
}

export async function publishAnswer(organizationId, eventId, questionId) {
  await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/questions/${questionId}/publish`,
  );
}
