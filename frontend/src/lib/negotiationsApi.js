import api from '@/lib/api';

/** Rondas de negociación (fase 8.5).
 * Lado comprador: /organizations/{id}/sourcing-events/{eventId}/negotiation-rounds
 * Lado proveedor: /organizations/{id}/sourcing-events/{eventId}/my-negotiation
 */

// ─── Lado comprador ─────────────────────────────────────────────────────────

export async function listRounds(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/negotiation-rounds`,
  );
  return data;
}

export async function openRound(organizationId, eventId, payload) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/negotiation-rounds`,
    {
      round_type: payload.roundType,
      participant_supplier_organization_ids: payload.participantSupplierOrganizationIds,
      deadline: payload.deadline || null,
      target_reduction_pct: payload.targetReductionPct ?? null,
      instructions: payload.instructions || null,
    },
  );
  return data.id;
}

export async function closeRound(organizationId, eventId, roundId) {
  await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/negotiation-rounds/${roundId}/close`,
  );
}

// ─── Lado proveedor ─────────────────────────────────────────────────────────

export async function listMyRound(organizationId, eventId) {
  const { data } = await api.get(
    `/organizations/${organizationId}/sourcing-events/${eventId}/my-negotiation`,
  );
  return data;
}

export async function submitCounter(organizationId, eventId, roundId, payload) {
  const { data } = await api.post(
    `/organizations/${organizationId}/sourcing-events/${eventId}/my-negotiation/${roundId}/respond`,
    {
      negotiation_round_id: roundId,
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
