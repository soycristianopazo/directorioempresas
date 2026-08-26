import api from '@/lib/api';

/** Llamadas a /api/auth/me (perfil propio) y /api/auth/change-password. */

export async function updateProfile({ firstName, lastName }) {
  const { data } = await api.patch('/auth/me', {
    first_name: firstName,
    last_name: lastName,
  });
  return data;
}

export async function changePassword({ currentPassword, newPassword }) {
  await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
}
