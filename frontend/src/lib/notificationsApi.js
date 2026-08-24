import api from '@/lib/api';

/** Notificaciones in-app (fase 7.9). Sin prefijo de organización — es
 * per-usuario. */

export async function listNotifications(unreadOnly = false) {
  const { data } = await api.get('/notifications', { params: { unread_only: unreadOnly } });
  return data;
}

export async function markNotificationRead(notificationId) {
  await api.post(`/notifications/${notificationId}/read`);
}

export async function markAllNotificationsRead() {
  await api.post('/notifications/read-all');
}

export async function listNotificationPreferences() {
  const { data } = await api.get('/notifications/preferences');
  return data;
}

export async function setNotificationPreference(channel, eventType, enabled) {
  await api.put('/notifications/preferences', {
    channel,
    event_type: eventType,
    enabled,
  });
}
