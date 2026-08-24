import api from '@/lib/api';

/** Cotizaciones (fase 7.5/7.6/7.7).
 * Lado comprador: /organizations/{id}/sourcing-events/{eventId}/quotations
 * Lado proveedor: /organizations/{id}/sourcing-events/{eventId}/my-quotation
 */

// ─── Lado comprador ─────────────────────────────────────────────────────────

export async function listQuotations(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/quotations`,
  );
  return data;
}

export async function openBids(organizationId, eventId) {
  await api.post(`/organizations/${organizationId}/sourcing-events/${eventId}/quotations/open-bids`);
}

// ─── Lado proveedor ─────────────────────────────────────────────────────────

export async function listMyRevisions(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/my-quotation/revisions`,
  );
  return data;
}

export async function submitRevision(organizationId, eventId, payload) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/my-quotation/revisions`,
    {
      currency_code: payload.currencyCode,
      valid_until: payload.validUntil || null,
      subtotal: payload.subtotal ?? null,
      tax_amount: payload.taxAmount ?? null,
      total_amount: payload.totalAmount,
      payment_terms: payload.paymentTerms || null,
      delivery_days: payload.deliveryDays ?? null,
      warranty_terms: payload.warrantyTerms || null,
      exclusions: payload.exclusions || null,
      notes: payload.notes || null,
      items: (payload.items || []).map((item) => ({
        sourcing_event_item_id: item.sourcingEventItemId,
        quantity: item.quantity,
        unit_code: item.unitCode || null,
        unit_price: item.unitPrice,
        discount_pct: item.discountPct ?? null,
        tax_rate: item.taxRate ?? null,
        lead_time_days: item.leadTimeDays ?? null,
        brand: item.brand || null,
        model: item.model || null,
        notes: item.notes || null,
      })),
      responses: (payload.responses || []).map((r) => ({
        sourcing_event_criterion_id: r.sourcingEventCriterionId,
        complies: r.complies ?? null,
        value_text: r.valueText || null,
        notes: r.notes || null,
      })),
    },
  );
  return data.id;
}

export async function uploadRevisionDocument(organizationId, eventId, revisionId, file) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/my-quotation/revisions/${revisionId}/documents`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return data;
}
