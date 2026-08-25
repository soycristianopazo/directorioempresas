import api from '@/lib/api';

/** Planes y facturación (fase 8.10). Sin flujo de pago — solo lectura. */

export async function listPlans(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/billing/plans`);
  return data;
}

export async function getSubscription(organizationId) {
  const { data } = await api.get(`/organizations/${organizationId}/billing/subscription`);
  return data;
}
